from pathlib import Path
import shutil
import pytest
from texture_forge.recipe import Recipe
from texture_forge.engine.mock import MockSyntheticEngine
from texture_forge.manifest import generate_textures_profile
from texture_forge.verifier import verify_with_scorekit


def test_scorekit_verification_integration(tmp_path: Path):
    recipe_content = """schema_version: 1
name: integration-test-profile
description: Profile for scorekit verification test
library: test-lib@1.0.0
engine: mock
items:
  - id: ambient_river
    prompt: "gentle flowing river water stream"
    category: organic
    tags: [water, stream, flowing]
    playback:
      modes: [loop]
      default_mode: loop
    use_cases: [forest, travel]
    duration_sec: 4.0
    gain: 0.8
"""
    recipe_file = tmp_path / "recipe.yaml"
    recipe_file.write_text(recipe_content, encoding="utf-8")
    recipe = Recipe.load(recipe_file)

    engine = MockSyntheticEngine()
    out_dir = tmp_path / "out"
    metrics_map = {}
    for item in recipe.items:
        m = engine.generate(item, out_dir / f"{item.id}.wav")
        metrics_map[item.id] = m

    profile_path = generate_textures_profile(recipe, out_dir, metrics_map, engine.name)

    # Run verification
    report = verify_with_scorekit(profile_path)
    assert report.check_passed
    if report.scorekit_available:
        assert report.details.get("failed") == 0
        assert report.details.get("passed", 0) >= 1
