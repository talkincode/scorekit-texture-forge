import json
from pathlib import Path
import pytest
from texture_forge.cli import main


def test_cli_build_mock(tmp_path: Path, monkeypatch, capsys):
    recipe_content = """schema_version: 1
name: test-cli-lib
description: CLI Test
library: test@1.0.0
engine: mock
items:
  - id: ambient_wind
    prompt: "gentle forest breeze"
    category: ambience
    tags: [wind, breeze]
    playback:
      modes: [loop]
      default_mode: loop
    use_cases: [forest]
    duration_sec: 2.0
"""
    recipe_file = tmp_path / "recipe.yaml"
    recipe_file.write_text(recipe_content, encoding="utf-8")
    out_dir = tmp_path / "out"

    # Run build with --json
    monkeypatch.setattr("sys.argv", ["texture-forge", "build", str(recipe_file), "-o", str(out_dir), "--json"])

    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0

    captured = capsys.readouterr()
    res = json.loads(captured.out)
    assert res["status"] == "success"
    assert res["item_count"] == 1
    assert (out_dir / "textures.yaml").exists()
    assert (out_dir / "ambient_wind.wav").exists()
    assert (out_dir / "SHA256SUMS").exists()
    assert (out_dir / "generator.json").exists()


def test_cli_inspect_and_lint(tmp_path: Path, monkeypatch, capsys):
    # 1. Init
    rec_path = tmp_path / "recipe.yaml"
    monkeypatch.setattr("sys.argv", ["texture-forge", "init", "-o", str(rec_path)])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    capsys.readouterr()  # Flush stdout from init

    # 2. Inspect with --json
    monkeypatch.setattr("sys.argv", ["texture-forge", "inspect", str(rec_path), "--json"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    captured = capsys.readouterr()
    inspected = json.loads(captured.out)
    assert inspected["item_count"] == 2

    # 3. Build with mock engine
    out_dir = tmp_path / "dist"
    monkeypatch.setattr("sys.argv", ["texture-forge", "build", str(rec_path), "-o", str(out_dir), "--engine", "mock", "--json"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    capsys.readouterr()  # Flush stdout from build

    # 4. Lint
    monkeypatch.setattr("sys.argv", ["texture-forge", "lint", str(out_dir), "--json"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    captured = capsys.readouterr()
    lint_report = json.loads(captured.out)
    assert lint_report["status"] == "success"
    assert len(lint_report["issues"]) == 0
