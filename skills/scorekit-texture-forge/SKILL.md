---
name: scorekit-texture-forge
description: >
  Generate neural sound-texture libraries (ambience, environmental beds, drones, risers, impacts, SFX)
  for scorekit using Magenta RealTime 2 (MRT2) recipes. Use when the user's scene requires custom atmospheric audio,
  texture profiles, environmental loops, or sound effect stems that cannot be met by conventional instrument
  SoundFonts/SFZs. Also use to inspect, lint, and verify texture profiles for scorekit M14 discovery compliance.
---

# scorekit-texture-forge — Neural Sound-Texture Foundry

`scorekit-texture-forge` is an external asset foundry that compiles declarative sound-texture **recipes** into certified, ready-to-consume **`textures.yaml` profiles + 48kHz stereo WAV libraries** for `scorekit`.

It bridges generative neural audio (Magenta RealTime 2 / MRT2) with `scorekit`'s deterministic compiler:
* **Neural Generation (MRT2)**: Freeform text prompts synthesize realistic space drones, cavern echoes, weather beds, and pneumatic impacts.
* **Deterministic Compiler (scorekit)**: `scorekit` schedules, cuts, loop-seals, and sums the generated textures into seamless loops and sample-aligned stems alongside MIDI tracks.

```text
recipe.yaml ──► texture-forge build ──► textures.yaml + *.wav ──► scorekit build --texture-profile ...
```

---

## 1. Quick CLI Reference

```bash
# Build texture library from a recipe
texture-forge build recipe.yaml -o out/scifi --verify --json

# Inspect and validate recipe syntax
texture-forge inspect recipe.yaml --json

# Lint an existing built texture library directory
texture-forge lint out/scifi --json

# Generate a starter recipe template
texture-forge init -o my_recipe.yaml
```

### Exit Codes for Agents
* `0`: Success.
* `1`: File I/O error.
* `2`: Validation error (invalid category, duplicate ID, bad tag format).
* `3`: Missing dependency (e.g. MRT2 requested but not installed; fallback to `--engine mock`).
* `4`: Audio generation or external tool verification failed.

---

## 2. Recipe Authoring Contract (MUST FOLLOW)

When creating a `recipe.yaml`, adhere strictly to these rules:

1. **`category` MUST be one of the 8 fixed keywords**:
   * `ambience`: Continuous environmental beds (wind, rain, cavern, room tone).
   * `foley`: Human-scale performed sounds (footsteps, cloth, handling).
   * `impact`: Short percussive events (hits, breaks, slams, crashes).
   * `transition`: Sweeps, risers, and falls connecting sections.
   * `tonal`: Resonant pitched material (bowed glass, metal chimes).
   * `industrial`: Machinery, motors, engines, mechanisms, vents.
   * `organic`: Water, fire, earth, creatures, nature.
   * `sound_design`: Synthesized or heavily processed abstract sci-fi/horror material.

2. **`tags` and `use_cases`**:
   * Must contain 1 to 16 tokens each.
   * Token regex: `^[a-z][a-z0-9_-]{0,31}$` (lowercase letters, numbers, underscores, hyphens).
   * No duplicates within the same item.

3. **`playback` modes**:
   * Supported modes: `loop`, `one_shot`.
   * `default_mode` must be listed in `modes`.
   * Background noise/drones should use `loop`; transient events (hits/splashes) should use `one_shot`.

4. **`id`**:
   * Token regex: `^[a-z][a-z0-9_-]{0,63}$`.

### Recipe Example

```yaml
# recipes/scifi-station.yaml
schema_version: 1
name: scifi-station-ambience
description: Atmospheric textures for abandoned space station exploration
library: mrt2-scifi-station@1.0.0
engine: auto # "auto", "mrt2", or "mock"

defaults:
  temperature: 0.9
  cfg_musiccoca: 4.0

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
    seed: 101

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
    seed: 102
```

---

## 3. End-to-End Agent Workflow

Follow this 4-step loop when authoring scenes with sound textures:

### Step 1: Write the Recipe
Create `my_textures.yaml` describing the required sound effects or environmental beds.

### Step 2: Build the Texture Library
Run the forge compiler with `--verify` to ensure it passes `scorekit texture check`:
```bash
texture-forge build my_textures.yaml -o dist/my_textures --verify --json
```
If working in an environment without GPU/MLX weights installed, pass `--engine mock` to produce synthetically shaped placeholder WAVs that satisfy all physics and schema assertions.

### Step 3: Reference in `scene.yaml`
In your `scene.yaml`, add the `textures:` block:
```yaml
title: Space Station Corridors
tempo: 88
key: D_minor
time_signature: "4/4"
bars: 8
loop: true

textures:
  # Continuous background bed
  - source: reactor_hum
    mode: loop
    gain: 0.35
  # Triggered impacts scheduled in quarter-note beats
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

### Step 4: Compile Final Game Audio
```bash
scorekit build scene.yaml --texture-profile dist/my_textures/textures.yaml -o scene.ogg --stems
```
`scorekit` will output:
* `scene.ogg`: The final seamless game loop with textures blended in.
* `scene.stems/`: Discrete, sample-aligned stems including `01-texture-reactor_hum.ogg`.
* `scene.meta.json`: Loop point metadata and stem manifests.
