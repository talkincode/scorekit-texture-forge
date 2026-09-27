import pytest
from pathlib import Path
from texture_forge.recipe import Recipe, RecipeError


def test_valid_recipe(tmp_path: Path):
    yaml_content = """schema_version: 1
name: test-ambience
description: Test library
library: test-lib@1.0.0
engine: mock
items:
  - id: low_drone
    prompt: "deep sub bass drone"
    category: industrial
    tags: [drone, sub, low_end]
    playback:
      modes: [loop]
      default_mode: loop
    use_cases: [space, tension]
    duration_sec: 10.0
"""
    recipe_file = tmp_path / "recipe.yaml"
    recipe_file.write_text(yaml_content, encoding="utf-8")

    recipe = Recipe.load(recipe_file)
    assert recipe.name == "test-ambience"
    assert recipe.library == "test-lib@1.0.0"
    assert len(recipe.items) == 1
    assert recipe.items[0].id == "low_drone"
    assert recipe.items[0].category == "industrial"
    assert recipe.items[0].playback.default_mode == "loop"


def test_invalid_category(tmp_path: Path):
    yaml_content = """schema_version: 1
name: bad-cat
library: test@1.0.0
items:
  - id: sound1
    prompt: "something"
    category: fantasy_magic # Illegal category
    tags: [magic]
    use_cases: [battle]
"""
    recipe_file = tmp_path / "recipe.yaml"
    recipe_file.write_text(yaml_content, encoding="utf-8")

    with pytest.raises(RecipeError) as exc:
        Recipe.load(recipe_file)
    assert "Invalid category" in str(exc.value)
    assert exc.value.field_path == "items[0].category"


def test_invalid_tag_format(tmp_path: Path):
    yaml_content = """schema_version: 1
name: bad-tag
library: test@1.0.0
items:
  - id: sound1
    prompt: "something"
    category: ambience
    tags: ["Bad Tag with Space!"]
    use_cases: [calm]
"""
    recipe_file = tmp_path / "recipe.yaml"
    recipe_file.write_text(yaml_content, encoding="utf-8")

    with pytest.raises(RecipeError) as exc:
        Recipe.load(recipe_file)
    assert "must match" in str(exc.value)
