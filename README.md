# scorekit-texture-forge

[![CI](https://github.com/talkincode/scorekit-texture-forge/actions/workflows/ci.yml/badge.svg)](https://github.com/talkincode/scorekit-texture-forge/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Neural sound-texture foundry for [scorekit](https://github.com/talkincode/scorekit) powered by [Magenta RealTime 2](https://github.com/magenta/magenta-realtime) (MRT2).**

`scorekit-texture-forge` compiles declarative sound-texture recipes into certified, ready-to-consume **`textures.yaml` profiles + 48kHz stereo WAV assets** conforming strictly to `scorekit`'s M14 discovery contract.

```text
recipe.yaml ──► texture-forge build ──► textures.yaml + *.wav ──► scorekit build --texture-profile ...
```

---

## Why this exists

`scorekit` is a deterministic game music compiler with an iron rule: **no in-house creative DSP or neural generation inside the compiler**.

However, video games frequently require atmospheric texture beds (space station engine drones, subterranean room tones, alien winds, or mechanical impacts) that cannot be synthesized by General MIDI or standard acoustic SoundFonts.

`scorekit-texture-forge` acts as the **external asset foundry** (analogous to `scoredata-forge` for SFZ instruments):
1. **Generative Neural Audio**: Uses Magenta RealTime 2 (MRT2) to synthesize organic, complex, and immersive textures from text prompts.
2. **Strict Discovery Contract**: Automatically structures and certifies the output into `textures.yaml` with explicit categories, tags, playback constraints, and SHA-256 checksums.
3. **Deterministic Assembly**: Passes the resulting library to `scorekit`, which handles sample-exact timeline placement, seamless loop sealing, and stem alignment.

---

## Features

- **Declarative Recipes**: Define your sound library in concise YAML (`recipes/*.yaml`).
- **Magenta RealTime 2 Integration**: Native support for Apple Silicon MLX, JAX, and C++ CLI (`hello_mrt2`).
- **Deterministic Synthetic Fallback**: Built-in `mock` engine for instant local prototyping and CI testing without multi-gigabyte neural checkpoints.
- **scorekit M14 Compliance**: Emits `schema_version: 1` profiles, verified directly via `scorekit texture check`.
- **Agent-Ready**: Machine-readable `--json` modes, clean exit codes, and a bundled Agent Skill for autonomous composing workflows.

---

## Installation

```bash
# Clone the repository
git clone https://github.com/talkincode/scorekit-texture-forge.git
cd scorekit-texture-forge

# Standard installation (supports CLI & synthetic mock engine)
pip install -e .

# With Magenta RealTime 2 support (Apple Silicon / MLX)
pip install -e ".[mrt2]"
```

---

## Quickstart

### 1. Build a sound-texture library

```bash
# Build from a bundled recipe
texture-forge build recipes/scifi-station.yaml -o out/scifi --verify --json
```

Output directory structure:
```text
out/scifi/
├── textures.yaml          # scorekit M14 texture profile
├── reactor_hum.wav        # 48kHz 16-bit PCM stereo audio
├── airlock_hiss.wav       # 48kHz 16-bit PCM stereo audio
├── SHA256SUMS             # Cryptographic checksums
├── generator.json         # Provenance and physical metrics
└── README.md              # Library usage documentation
```

### 2. Inspect a recipe

```bash
texture-forge inspect recipes/scifi-station.yaml
```

### 3. Lint an existing library

```bash
texture-forge lint out/scifi --json
```

---

## Using with scorekit

In your `scene.yaml`:

```yaml
title: Abandoned Station Core
tempo: 90
key: C_minor
time_signature: "4/4"
bars: 8
loop: true

textures:
  # Continuous ambient loop
  - source: reactor_hum
    mode: loop
    gain: 0.35
  # Triggered event scheduled on beat 4 and beat 20
  - source: airlock_hiss
    mode: one_shot
    at: [4.0, 20.0]
    gain: 0.5

tracks:
  - id: pad
    instrument: choir_pad
    pattern: sustain
    intensity: 0.5
  - id: bass
    instrument: synth_bass
    pattern: bass
    intensity: 0.6
```

Build game-ready audio assets:

```bash
scorekit build scene.yaml --texture-profile out/scifi/textures.yaml -o station.ogg --stems
```

---

## Bundled Agent Skill

This repository includes an Agent Skill at [`skills/scorekit-texture-forge/`](skills/scorekit-texture-forge/SKILL.md) that teaches AI coding assistants how to:
- Formulate sound recipes adhering to the 8 closed categories (`ambience`, `foley`, `impact`, `transition`, `tonal`, `industrial`, `organic`, `sound_design`).
- Trigger automated forge builds and inspect validation errors.
- Seamlessly wire generated texture profiles into game scoring scenes.

Install the skill for Claude Code / Antigravity / Cursor:
```bash
cp -r skills/scorekit-texture-forge ~/.claude/skills/
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.
