"""
Media discovery, resolution, and Gemini Files API upload service (Phase 2).

Discovers case source media from manifest metadata, caches downloads locally
under tracks/track-a/data/.cache/, and handles Gemini Files API uploads and polling.
"""

from __future__ import annotations

import logging
import time
import urllib.request
from pathlib import Path
from typing import Any, Optional

from case_registry import CaseManifest, SourceMediaDescriptor, load_manifest
from models import FailureCategory, TrackAFailure

logger = logging.getLogger(__name__)


class MediaService:
    """Discovers, caches, and uploads case source media for multimodal processing."""

    def __init__(self, cases_root: Path, client: Optional[Any] = None) -> None:
        self.cases_root = cases_root
        self.client = client
        self.cache_dir = cases_root.parent / "track-a" / "data" / ".cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def discover_media(self, case_id: str) -> SourceMediaDescriptor:
        """Discover media descriptor from case manifest."""
        manifest = load_manifest(self.cases_root, case_id)
        if not manifest.source_media:
            raise TrackAFailure(
                FailureCategory.INVALID_INPUT,
                f"No source media configured in manifest for case '{case_id}'.",
                {"case_id": case_id},
            )
        return manifest.source_media

    def resolve_media_path(self, case_id: str, descriptor: SourceMediaDescriptor) -> Path:
        """
        Resolve media to a local filesystem path.
        If descriptor is local_file, verifies and returns path.
        If descriptor is URL, downloads to cache directory.
        """
        if descriptor.type == "local_file":
            if not descriptor.path:
                raise TrackAFailure(
                    FailureCategory.INVALID_INPUT,
                    f"Local file descriptor for '{case_id}' missing 'path'.",
                )
            media_path = self.cases_root / case_id / descriptor.path
            if not media_path.exists():
                raise TrackAFailure(
                    FailureCategory.MISSING_EVIDENCE,
                    f"Local source media file not found: {media_path}",
                    {"path": str(media_path)},
                )
            return media_path

        elif descriptor.type == "url":
            if not descriptor.url:
                raise TrackAFailure(
                    FailureCategory.INVALID_INPUT,
                    f"URL descriptor for '{case_id}' missing 'url'.",
                )
            case_cache = self.cache_dir / case_id
            case_cache.mkdir(parents=True, exist_ok=True)

            # Determine filename from URL or mime type
            url_filename = descriptor.url.split("/")[-1].split("?")[0]
            if not url_filename or "." not in url_filename:
                ext = ".mp4"
                if descriptor.mime_type and "webm" in descriptor.mime_type:
                    ext = ".webm"
                elif descriptor.mime_type and "image" in descriptor.mime_type:
                    ext = ".png"
                url_filename = f"source_media{ext}"

            local_path = case_cache / url_filename

            # If already downloaded and non-empty, use cached version
            if local_path.exists() and local_path.stat().st_size > 0:
                logger.info("Using cached media for %s: %s", case_id, local_path)
                return local_path

            logger.info("Downloading source media from %s to %s", descriptor.url, local_path)
            try:
                # Add a realistic User-Agent for Wikimedia / external CDNs
                req = urllib.request.Request(
                    descriptor.url,
                    headers={"User-Agent": "Anveshan-Media-Downloader/1.0 (Research prototype)"},
                )
                with urllib.request.urlopen(req, timeout=45) as response, open(local_path, "wb") as out_file:
                    out_file.write(response.read())
            except Exception as exc:
                if local_path.exists():
                    local_path.unlink(missing_ok=True)
                raise TrackAFailure(
                    FailureCategory.INVALID_INPUT,
                    f"Failed to download source media from {descriptor.url}: {exc}",
                    {"url": descriptor.url, "error": str(exc)},
                ) from exc

            return local_path

        else:
            raise TrackAFailure(
                FailureCategory.INVALID_INPUT,
                f"Unknown media descriptor type: {descriptor.type}",
            )

    def upload_to_gemini(
        self,
        media_path: Path,
        mime_type: Optional[str] = None,
        timeout_sec: float = 120.0,
    ) -> Any:
        """
        Uploads local media to Gemini Files API and polls until state is ACTIVE.
        Raises TrackAFailure on failure or timeout.
        """
        if self.client is None:
            raise TrackAFailure(
                FailureCategory.MODEL_FAILURE,
                "Gemini client is not initialized in MediaService.",
            )

        if not media_path.exists() or media_path.stat().st_size == 0:
            raise TrackAFailure(
                FailureCategory.INVALID_INPUT,
                f"Media file empty or does not exist: {media_path}",
            )

        try:
            logger.info("Uploading %s to Gemini Files API...", media_path.name)
            file_ref = self.client.files.upload(
                file=str(media_path),
                config={"mime_type": mime_type} if mime_type else None,
            )
        except Exception as exc:
            raise TrackAFailure(
                FailureCategory.MODEL_FAILURE,
                f"Gemini files.upload failed for {media_path.name}: {exc}",
            ) from exc

        # Poll file state until ACTIVE or timeout
        start_time = time.monotonic()
        while getattr(file_ref, "state", None) and file_ref.state.name == "PROCESSING":
            elapsed = time.monotonic() - start_time
            if elapsed > timeout_sec:
                self.cleanup(file_ref.name)
                raise TrackAFailure(
                    FailureCategory.MODEL_TIMEOUT,
                    f"Gemini file processing timed out after {elapsed:.1f}s for {file_ref.name}",
                )
            time.sleep(3.0)
            try:
                file_ref = self.client.files.get(name=file_ref.name)
            except Exception as exc:
                raise TrackAFailure(
                    FailureCategory.MODEL_FAILURE,
                    f"Error polling Gemini file status {file_ref.name}: {exc}",
                ) from exc

        if getattr(file_ref, "state", None) and file_ref.state.name != "ACTIVE":
            self.cleanup(file_ref.name)
            raise TrackAFailure(
                FailureCategory.MODEL_FAILURE,
                f"Gemini file processing failed with state {file_ref.state.name} for {file_ref.name}",
            )

        logger.info("Gemini file %s is ACTIVE.", file_ref.name)
        return file_ref

    def cleanup(self, file_name: Optional[str]) -> None:
        """Delete uploaded file from Gemini Files API."""
        if not file_name or not self.client:
            return
        try:
            self.client.files.delete(name=file_name)
            logger.info("Cleaned up Gemini file: %s", file_name)
        except Exception as exc:
            logger.warning("Could not delete Gemini file %s: %exc", file_name, exc)
