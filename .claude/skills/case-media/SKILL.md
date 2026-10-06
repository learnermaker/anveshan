---
name: case-media
description: Add or replace source/attempt media for an Anveshan case pack (internet downloads or user uploads) with license, attribution, sha256, size and git rules. Use when touching tracks/cases/<id>/source, media manifests, tools/fetch_media.py, or test media.
---

# Case media rules

1. **License first.** Only use media whose license allows our use: public domain, CC0, CC BY, CC BY-SA (Wikimedia Commons preferred). Record creator, license, source URL. Non-commercial (NC) or "all rights reserved" media may be used only for local testing and must never be committed or deployed.
2. **Register** every source in `tracks/cases/<id>/source/source.json` (`source_id`, `role`, `url`, `path`, `mime_type`, `sha256`, `bytes`, `dimensions`/`duration_sec`, `creator`, `license`, `attribution`, `access_level`, `runtime_label`). Internet media used without a real expert is `runtime_label: "INTERNET_REFERENCE"` — never call it an authentic expert.
3. **Size rule.** Commit files ≤ 2 MB (e.g. a target image). Larger media (video/audio) is **not committed**: list it in `source.json` with `url` + `sha256`, and `tools/fetch_media.py` downloads it into the gitignored `tracks/cases/<id>/media/cache/`, verifying sha256.
4. **Synthetic attempts** (generated perturbations for testing) live under `tracks/track-b/eval/` with a generator script and `runtime_label: "SYNTHETIC"`; never present them as real learners.
5. **Uploads** at runtime are stored by the service under `var/uploads/<sha256>.<ext>` (gitignored) and get a source_id `upload.<sha256[:12]>`.
6. After changes run `.github/scripts/check_case_packs.py` and the `anveshan-verify` skill.
