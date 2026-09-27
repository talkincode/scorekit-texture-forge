"""
Command-line interface for scorekit-texture-forge.
Designed to be friendly to both humans and AI Agents (with --json and strict exit codes).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict

from texture_forge import __version__
from texture_forge.engine import get_engine, EngineError
from texture_forge.manifest import generate_textures_profile
from texture_forge.processor import measure_wav
from texture_forge.recipe import Recipe, RecipeError
from texture_forge.verifier import verify_with_scorekit

# Exit codes following scorekit convention
EXIT_OK = 0
EXIT_IO = 1
EXIT_VALIDATION = 2
EXIT_DEPENDENCY = 3
EXIT_TOOL_FAILED = 4


def cmd_build(args: argparse.Namespace) -> int:
    try:
        recipe = Recipe.load(args.recipe)
    except RecipeError as e:
        if args.json:
            print(json.dumps({"status": "error", "exit_code": EXIT_VALIDATION, "detail": e.to_dict()}))
        else:
            print(f"Error: Invalid recipe: {e.message}", file=sys.stderr)
            if e.field_path:
                print(f"  Field: {e.field_path}", file=sys.stderr)
        return EXIT_VALIDATION
    except Exception as e:
        if args.json:
            print(json.dumps({"status": "error", "exit_code": EXIT_IO, "detail": {"error": str(e)}}))
        else:
            print(f"I/O Error: {e}", file=sys.stderr)
        return EXIT_IO

    engine_name = args.engine or recipe.engine or "auto"
    try:
        engine = get_engine(engine_name)
    except EngineError as e:
        if args.json:
            print(json.dumps({"status": "error", "exit_code": EXIT_DEPENDENCY, "detail": {"error": str(e)}}))
        else:
            print(f"Dependency Error: {e}", file=sys.stderr)
        return EXIT_DEPENDENCY

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not args.json:
        print(f"Building sound texture library '{recipe.name}' with engine '{engine.name}'...")
        print(f"Output directory: {out_dir}")

    metrics_map = {}
    generated_items = []

    for idx, item in enumerate(recipe.items):
        item_wav = out_dir / f"{item.id}.wav"
        if not args.json:
            print(f"[{idx+1}/{len(recipe.items)}] Generating '{item.id}' ({item.duration_sec}s, {item.category})...")

        try:
            metrics = engine.generate(item, item_wav)
            metrics_map[item.id] = metrics
            generated_items.append({
                "id": item.id,
                "category": item.category,
                "duration_seconds": metrics.duration_seconds,
                "peak_abs": metrics.peak_abs,
                "rms": metrics.rms,
                "sha256": metrics.sha256,
            })
        except Exception as e:
            if args.json:
                print(json.dumps({
                    "status": "error",
                    "exit_code": EXIT_TOOL_FAILED,
                    "detail": {"item_id": item.id, "error": str(e)},
                }))
            else:
                print(f"Error generating item '{item.id}': {e}", file=sys.stderr)
            return EXIT_TOOL_FAILED

    profile_path = generate_textures_profile(recipe, out_dir, metrics_map, engine.name)

    verify_report = None
    if args.verify:
        if not args.json:
            print("Verifying generated profile against scorekit...")
        report = verify_with_scorekit(profile_path)
        verify_report = report.to_dict()
        if not report.check_passed:
            if args.json:
                print(json.dumps({
                    "status": "error",
                    "exit_code": EXIT_TOOL_FAILED,
                    "detail": {"verification": verify_report},
                }))
            else:
                print(f"Verification failed: {report.raw_output}", file=sys.stderr)
            return EXIT_TOOL_FAILED

    if args.json:
        res = {
            "status": "success",
            "exit_code": EXIT_OK,
            "library": recipe.library,
            "profile_path": str(profile_path),
            "engine": engine.name,
            "item_count": len(recipe.items),
            "items": generated_items,
        }
        if verify_report:
            res["verification"] = verify_report
        print(json.dumps(res, indent=2))
    else:
        print(f"Successfully generated {len(recipe.items)} sound textures!")
        print(f"Profile written to: {profile_path}")
        print(f"Next step: in your scene.yaml, add '--texture-profile {profile_path}'")

    return EXIT_OK


def cmd_inspect(args: argparse.Namespace) -> int:
    try:
        recipe = Recipe.load(args.recipe)
    except RecipeError as e:
        if args.json:
            print(json.dumps({"status": "error", "exit_code": EXIT_VALIDATION, "detail": e.to_dict()}))
        else:
            print(f"Invalid recipe: {e.message}", file=sys.stderr)
        return EXIT_VALIDATION

    data = {
        "name": recipe.name,
        "library": recipe.library,
        "description": recipe.description,
        "engine": recipe.engine,
        "item_count": len(recipe.items),
        "items": [
            {
                "id": it.id,
                "category": it.category,
                "tags": it.tags,
                "playback": {"modes": it.playback.modes, "default_mode": it.playback.default_mode},
                "use_cases": it.use_cases,
                "duration_sec": it.duration_sec,
                "prompt": it.prompt,
            }
            for it in recipe.items
        ],
    }

    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print(f"Recipe: {recipe.name} ({recipe.library})")
        print(f"Description: {recipe.description}")
        print(f"Items ({len(recipe.items)}):")
        for it in recipe.items:
            print(f"  - {it.id} [{it.category}]: {it.description} ({it.duration_sec}s, modes: {it.playback.modes})")

    return EXIT_OK


def cmd_lint(args: argparse.Namespace) -> int:
    profile_dir = Path(args.profile_dir)
    textures_yaml = profile_dir / "textures.yaml"
    if not textures_yaml.exists():
        msg = f"textures.yaml not found in {profile_dir}"
        if args.json:
            print(json.dumps({"status": "error", "exit_code": EXIT_IO, "error": msg}))
        else:
            print(f"Error: {msg}", file=sys.stderr)
        return EXIT_IO

    import yaml
    with open(textures_yaml, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    sources = data.get("sources", {})
    issues = []
    checked_sources = []

    for name, sdata in sources.items():
        if isinstance(sdata, str):
            rel_path = sdata
        else:
            rel_path = sdata.get("path")
        audio_file = profile_dir / rel_path
        if not audio_file.exists():
            issues.append(f"Source '{name}': file not found at {audio_file}")
            continue

        try:
            m = measure_wav(audio_file)
            if m.is_silent:
                issues.append(f"Source '{name}': audio is silent (peak < 1e-4)")
            checked_sources.append({"id": name, "metrics": m.to_dict()})
        except Exception as e:
            issues.append(f"Source '{name}': failed to read WAV: {e}")

    passed = len(issues) == 0
    if args.json:
        print(json.dumps({
            "status": "success" if passed else "failed",
            "exit_code": EXIT_OK if passed else EXIT_VALIDATION,
            "issues": issues,
            "sources": checked_sources,
        }, indent=2))
    else:
        if passed:
            print(f"Lint passed: {len(checked_sources)} sources checked cleanly.")
        else:
            print(f"Lint failed with {len(issues)} issue(s):", file=sys.stderr)
            for iss in issues:
                print(f"  - {iss}", file=sys.stderr)

    return EXIT_OK if passed else EXIT_VALIDATION


def cmd_init(args: argparse.Namespace) -> int:
    template = """# Recipe for scorekit-texture-forge
schema_version: 1
name: sci-fi-station-ambience
description: Neural sound textures for abandoned sci-fi space station exploration
library: mrt2-scifi-station@1.0.0
engine: auto

items:
  - id: reactor_hum
    prompt: "deep continuous sub drone, dark industrial space station engine rumble"
    description: "Low-frequency steady reactor rumble"
    category: industrial
    tags: [drone, engine, low_end, continuous]
    playback:
      modes: [loop]
      default_mode: loop
    use_cases: [space, station, tension]
    duration_sec: 16.0
    gain: 0.8

  - id: airlock_hiss
    prompt: "sudden pneumatic airlock pressure release hiss and metallic clamp latch"
    description: "Pneumatic air pressure release"
    category: impact
    tags: [pneumatic, hiss, mechanical]
    playback:
      modes: [one_shot]
      default_mode: one_shot
    use_cases: [space, door, transition]
    duration_sec: 4.0
    gain: 0.7
"""
    out_file = Path(args.output)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(template)
    print(f"Template recipe created at: {out_file}")
    return EXIT_OK


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="texture-forge",
        description="scorekit-texture-forge: Neural sound-texture foundry for scorekit powered by Magenta RealTime 2",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # build
    p_build = subparsers.add_parser("build", help="Build sound textures from a recipe")
    p_build.add_argument("recipe", help="Path to recipe YAML file")
    p_build.add_argument("-o", "--output", required=True, help="Output directory for generated library")
    p_build.add_argument("--engine", choices=["auto", "mrt2", "mock"], default=None, help="Generation engine override")
    p_build.add_argument("--verify", action="store_true", help="Run 'scorekit texture check' on emitted profile")
    p_build.add_argument("--json", action="store_true", help="Emit machine-readable JSON output")
    p_build.set_defaults(func=cmd_build)

    # inspect
    p_inspect = subparsers.add_parser("inspect", help="Inspect and validate a recipe file")
    p_inspect.add_argument("recipe", help="Path to recipe YAML file")
    p_inspect.add_argument("--json", action="store_true", help="Emit machine-readable JSON output")
    p_inspect.set_defaults(func=cmd_inspect)

    # lint
    p_lint = subparsers.add_parser("lint", help="Lint an existing generated library directory")
    p_lint.add_argument("profile_dir", help="Path to directory containing textures.yaml")
    p_lint.add_argument("--json", action="store_true", help="Emit machine-readable JSON output")
    p_lint.set_defaults(func=cmd_lint)

    # init
    p_init = subparsers.add_parser("init", help="Create a starter recipe template")
    p_init.add_argument("-o", "--output", default="recipe.yaml", help="Destination recipe file")
    p_init.set_defaults(func=cmd_init)

    args = parser.parse_args()
    code = args.func(args)
    sys.exit(code)


if __name__ == "__main__":
    main()
