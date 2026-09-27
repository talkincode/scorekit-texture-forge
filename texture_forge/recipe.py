"""
Recipe definition, validation, and parsing.
Enforces scorekit M14 discovery contract rules strictly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional
import yaml

VALID_CATEGORIES = {
    "ambience",
    "foley",
    "impact",
    "transition",
    "tonal",
    "industrial",
    "organic",
    "sound_design",
}

VALID_MODES = {"loop", "one_shot"}
TOKEN_REGEX = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
ID_REGEX = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")


class RecipeError(Exception):
    """Raised when a recipe violates validation rules."""

    def __init__(self, message: str, field_path: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.field_path = field_path

    def to_dict(self) -> dict[str, Any]:
        result = {"error": self.message}
        if self.field_path:
            result["field"] = self.field_path
        return result


@dataclass
class PlaybackSpec:
    modes: List[str]
    default_mode: str

    @classmethod
    def from_dict(cls, data: Any, field_prefix: str) -> PlaybackSpec:
        if not isinstance(data, dict):
            raise RecipeError(
                f"playback must be a mapping with 'modes' and 'default_mode'",
                field_prefix,
            )
        modes = data.get("modes", [])
        if not isinstance(modes, list) or not modes:
            raise RecipeError(
                "playback.modes must be a non-empty list of 'loop' or 'one_shot'",
                f"{field_prefix}.modes",
            )
        for m in modes:
            if m not in VALID_MODES:
                raise RecipeError(
                    f"Invalid playback mode '{m}'. Must be one of: {sorted(VALID_MODES)}",
                    f"{field_prefix}.modes",
                )
        default_mode = data.get("default_mode")
        if not default_mode or default_mode not in modes:
            raise RecipeError(
                f"playback.default_mode '{default_mode}' must appear in playback.modes",
                f"{field_prefix}.default_mode",
            )
        return cls(modes=modes, default_mode=default_mode)


@dataclass
class RecipeItem:
    id: str
    prompt: str
    description: str
    category: str
    tags: List[str]
    playback: PlaybackSpec
    use_cases: List[str]
    duration_sec: float = 16.0
    gain: float = 1.0
    seed: Optional[int] = None
    temperature: Optional[float] = None
    cfg_musiccoca: Optional[float] = None

    @classmethod
    def from_dict(cls, data: Any, index: int) -> RecipeItem:
        prefix = f"items[{index}]"
        if not isinstance(data, dict):
            raise RecipeError(f"Recipe item must be a dictionary", prefix)

        item_id = data.get("id")
        if not item_id or not isinstance(item_id, str) or not ID_REGEX.match(item_id):
            raise RecipeError(
                f"Item id '{item_id}' must match ^[a-z][a-z0-9_-]{{0,63}}$",
                f"{prefix}.id",
            )

        prompt = data.get("prompt")
        if not prompt or not isinstance(prompt, str) or not prompt.strip():
            raise RecipeError("prompt is required and cannot be empty", f"{prefix}.prompt")

        description = data.get("description", prompt)
        if not isinstance(description, str) or not description.strip():
            raise RecipeError("description must be a non-empty string", f"{prefix}.description")

        category = data.get("category")
        if not category or category not in VALID_CATEGORIES:
            raise RecipeError(
                f"Invalid category '{category}'. Must be one of: {sorted(VALID_CATEGORIES)}",
                f"{prefix}.category",
            )

        tags = data.get("tags", [])
        if not isinstance(tags, list) or not (1 <= len(tags) <= 16):
            raise RecipeError("tags must be a list containing 1 to 16 tags", f"{prefix}.tags")
        seen_tags = set()
        for t in tags:
            if not isinstance(t, str) or not TOKEN_REGEX.match(t):
                raise RecipeError(
                    f"tag '{t}' must match ^[a-z][a-z0-9_-]{{0,31}}$",
                    f"{prefix}.tags",
                )
            if t in seen_tags:
                raise RecipeError(f"Duplicate tag '{t}' in item '{item_id}'", f"{prefix}.tags")
            seen_tags.add(t)

        playback_data = data.get("playback")
        if playback_data is None:
            # Default to loop if unspecified
            playback = PlaybackSpec(modes=["loop"], default_mode="loop")
        else:
            playback = PlaybackSpec.from_dict(playback_data, f"{prefix}.playback")

        use_cases = data.get("use_cases", [])
        if not isinstance(use_cases, list) or not (1 <= len(use_cases) <= 16):
            raise RecipeError(
                "use_cases must be a list containing 1 to 16 use cases",
                f"{prefix}.use_cases",
            )
        seen_cases = set()
        for u in use_cases:
            if not isinstance(u, str) or not TOKEN_REGEX.match(u):
                raise RecipeError(
                    f"use_case '{u}' must match ^[a-z][a-z0-9_-]{{0,31}}$",
                    f"{prefix}.use_cases",
                )
            if u in seen_cases:
                raise RecipeError(
                    f"Duplicate use_case '{u}' in item '{item_id}'",
                    f"{prefix}.use_cases",
                )
            seen_cases.add(u)

        duration = float(data.get("duration_sec", 16.0))
        if duration < 0.1 or duration > 300.0:
            raise RecipeError("duration_sec must be between 0.1 and 300.0", f"{prefix}.duration_sec")

        gain = float(data.get("gain", 1.0))
        if not (0.0 <= gain <= 1.0):
            raise RecipeError("gain must be between 0.0 and 1.0", f"{prefix}.gain")

        seed = data.get("seed")
        if seed is not None and not isinstance(seed, int):
            raise RecipeError("seed must be an integer if provided", f"{prefix}.seed")

        return cls(
            id=item_id,
            prompt=prompt.strip(),
            description=description.strip(),
            category=category,
            tags=tags,
            playback=playback,
            use_cases=use_cases,
            duration_sec=duration,
            gain=gain,
            seed=seed,
            temperature=data.get("temperature"),
            cfg_musiccoca=data.get("cfg_musiccoca"),
        )


@dataclass
class Recipe:
    schema_version: int
    name: str
    description: str
    library: str
    engine: str
    items: List[RecipeItem]
    defaults: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path | str) -> Recipe:
        path = Path(path)
        if not path.exists():
            raise RecipeError(f"Recipe file does not exist: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            raise RecipeError(f"YAML parse error in {path}: {e}")

        if not isinstance(data, dict):
            raise RecipeError("Recipe YAML root must be a mapping")

        schema_version = data.get("schema_version", 1)
        if schema_version != 1:
            raise RecipeError(f"Unsupported schema_version {schema_version}, only 1 is supported", "schema_version")

        name = data.get("name")
        if not name or not isinstance(name, str):
            raise RecipeError("Recipe requires a non-empty 'name' string", "name")

        description = data.get("description", "")
        library = data.get("library")
        if not library or not isinstance(library, str):
            raise RecipeError("Recipe requires a 'library' identifier (e.g. name@version)", "library")

        engine = data.get("engine", "auto")
        defaults = data.get("defaults", {})

        raw_items = data.get("items", [])
        if not isinstance(raw_items, list) or not raw_items:
            raise RecipeError("Recipe must contain a non-empty 'items' list", "items")

        items: List[RecipeItem] = []
        seen_ids = set()
        for idx, item_data in enumerate(raw_items):
            item = RecipeItem.from_dict(item_data, idx)
            if item.id in seen_ids:
                raise RecipeError(f"Duplicate item id '{item.id}' across recipe", f"items[{idx}].id")
            seen_ids.add(item.id)
            items.append(item)

        return cls(
            schema_version=schema_version,
            name=name,
            description=description,
            library=library,
            engine=engine,
            items=items,
            defaults=defaults,
        )
