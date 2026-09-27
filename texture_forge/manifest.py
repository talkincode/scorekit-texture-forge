"""
Manifest and profile generator.
Emits schema-compliant scorekit M14 textures.yaml profiles and provenance records.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Dict
import yaml

from texture_forge.processor import AudioMetrics
from texture_forge.recipe import Recipe


def generate_textures_profile(
    recipe: Recipe,
    output_dir: Path,
    metrics_map: Dict[str, AudioMetrics],
    engine_name: str,
) -> Path:
    """
    Writes textures.yaml, SHA256SUMS, generator.json, and README.md into output_dir.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Build sources dictionary conforming to scorekit schema_version 1
    sources: Dict[str, Any] = {}
    for item in recipe.items:
        sources[item.id] = {
            "path": f"{item.id}.wav",
            "description": item.description,
            "category": item.category,
            "tags": item.tags,
            "playback": {
                "modes": item.playback.modes,
                "default_mode": item.playback.default_mode,
            },
            "use_cases": item.use_cases,
            "provenance": {
                "library": recipe.library,
            },
        }

    profile_data = {
        "schema_version": 1,
        "name": recipe.name,
        "description": recipe.description,
        "root": "./",
        "sources": sources,
    }

    textures_yaml_path = output_dir / "textures.yaml"
    with open(textures_yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(profile_data, f, sort_keys=False, allow_unicode=True)

    # 2. SHA256SUMS
    sha_lines = []
    for item in recipe.items:
        metrics = metrics_map.get(item.id)
        if metrics:
            sha_lines.append(f"{metrics.sha256}  {item.id}.wav")

    # Add hash of textures.yaml itself
    from texture_forge.processor import compute_file_sha256
    profile_hash = compute_file_sha256(textures_yaml_path)
    sha_lines.append(f"{profile_hash}  textures.yaml")

    with open(output_dir / "SHA256SUMS", "w", encoding="utf-8") as f:
        f.write("\n".join(sha_lines) + "\n")

    # 3. generator.json
    generator_meta = {
        "generator": "scorekit-texture-forge",
        "engine": engine_name,
        "library": recipe.library,
        "python_version": sys.version,
        "platform": sys.platform,
        "items": {item_id: m.to_dict() for item_id, m in metrics_map.items()},
    }
    with open(output_dir / "generator.json", "w", encoding="utf-8") as f:
        json.dump(generator_meta, f, indent=2)

    # 4. README.md
    readme_content = f"""# {recipe.name}

{recipe.description}

- **Library ID**: `{recipe.library}`
- **Engine**: `{engine_name}`
- **Total Sources**: {len(recipe.items)}

## Usage with scorekit

In your `scene.yaml`:

```yaml
textures:
"""
    for item in recipe.items[:2]:
        if item.playback.default_mode == "loop":
            readme_content += f"  - source: {item.id}\n    mode: loop\n    gain: 0.3\n"
        else:
            readme_content += f"  - source: {item.id}\n    mode: one_shot\n    at: [4.0, 12.0]\n    gain: 0.4\n"

    readme_content += f"""```

Build command:

```bash
scorekit build scene.yaml --texture-profile {output_dir}/textures.yaml -o scene.ogg --stems
```
"""
    with open(output_dir / "README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)

    return textures_yaml_path
