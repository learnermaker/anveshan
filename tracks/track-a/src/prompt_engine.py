"""
Prompt loading and templating engine for Track A model interactions (Phase 3).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from case_registry import CaseManifest


class PromptEngine:
    """Loads and renders versioned prompt templates with case metadata."""

    def __init__(self, prompts_dir: Optional[Path] = None) -> None:
        if prompts_dir is None:
            prompts_dir = Path(__file__).resolve().parent.parent / "prompts"
        self.prompts_dir = prompts_dir

    def load_extraction_prompt(self, manifest: CaseManifest, version: str = "v1") -> str:
        """Load and render prompt according to transmission mode."""
        mode = manifest.transmission_mode
        if mode == "goal-conditioned":
            filename = f"goal_conditioned_extraction_{version}.txt"
        elif mode == "corrective":
            filename = f"corrective_extraction_{version}.txt"
        else:
            filename = f"expert_extraction_{version}.txt"

        prompt_path = self.prompts_dir / filename
        if not prompt_path.exists():
            # Fallback to expert extraction template
            prompt_path = self.prompts_dir / f"expert_extraction_{version}.txt"

        raw_template = prompt_path.read_text(encoding="utf-8")
        return self.render(raw_template, manifest)

    def load_query_prompt(self, version: str = "v1") -> str:
        """Load adversarial query prompt template."""
        prompt_path = self.prompts_dir / f"adversarial_query_{version}.txt"
        return prompt_path.read_text(encoding="utf-8")

    def render(self, template: str, manifest: CaseManifest) -> str:
        """Substitute case variables into prompt template."""
        return (
            template.replace("{case_domain}", manifest.domain)
            .replace("{case_title}", manifest.title)
            .replace("{transmission_mode}", manifest.transmission_mode)
        )
