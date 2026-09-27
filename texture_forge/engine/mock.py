"""
Deterministic acoustic physics synthesizer for natural and atmospheric sound textures.
Generates genuine recognizable birdsong, rain beds, wind, thunder, and drones.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import List, Tuple
from texture_forge.engine.base import BaseEngine
from texture_forge.processor import AudioMetrics, write_stereo_wav_16bit
from texture_forge.recipe import RecipeItem


class MockSyntheticEngine(BaseEngine):
    """
    Acoustic physics synthesizer modeling natural sound phenomena:
    - Birdsong (high-frequency FM chirps, cuckoo intervals, raptor screeches)
    - Rain (pink-noise beds with Poisson raindrop impulses)
    - Wind (LFO-modulated bandpass gusts)
    - Thunder & Impacts (sub-bass transient with rumble decay)
    - Industrial/Drones (binaural detuned harmonics)
    """

    @property
    def name(self) -> str:
        return "synthetic_mock"

    def is_available(self) -> bool:
        return True

    def _derive_seed(self, item: RecipeItem) -> int:
        if item.seed is not None:
            return item.seed
        h = hashlib.sha256(f"{item.id}:{item.prompt}".encode("utf-8")).digest()
        return int.from_bytes(h[:4], "little")

    def generate(
        self,
        item: RecipeItem,
        output_file: Path,
        sample_rate: int = 48000,
    ) -> AudioMetrics:
        seed = self._derive_seed(item)
        n_samples = int(item.duration_sec * sample_rate)

        # PRNG
        state = seed & 0xFFFFFFFF
        a = 1664525
        c = 1013904223
        m = 2**32

        def randf() -> float:
            nonlocal state
            state = (a * state + c) % m
            return (state / m) * 2.0 - 1.0

        def rand01() -> float:
            nonlocal state
            state = (a * state + c) % m
            return state / m

        # Match text keywords to select specific acoustic synthesis model
        keywords = set(item.tags + [item.id] + item.prompt.lower().split())

        if "cuckoo" in keywords:
            samples_l, samples_r = self._synth_cuckoo(n_samples, sample_rate, rand01)
        elif "eagle" in keywords or "hawk" in keywords:
            samples_l, samples_r = self._synth_eagle(n_samples, sample_rate, rand01)
        elif "nightingale" in keywords:
            samples_l, samples_r = self._synth_nightingale(n_samples, sample_rate, rand01)
        elif "bird" in keywords or "birds" in keywords or "chirp" in keywords:
            samples_l, samples_r = self._synth_dawn_chorus(n_samples, sample_rate, rand01)
        elif "rain" in keywords or "water" in keywords or "stream" in keywords:
            samples_l, samples_r = self._synth_rain(n_samples, sample_rate, randf, rand01)
        elif "wind" in keywords or "breeze" in keywords:
            samples_l, samples_r = self._synth_wind(n_samples, sample_rate, randf)
        elif "thunder" in keywords:
            samples_l, samples_r = self._synth_thunder(n_samples, sample_rate, randf)
        elif "snap" in keywords or item.category == "foley":
            samples_l, samples_r = self._synth_snap(n_samples, sample_rate, randf)
        elif item.category == "impact":
            samples_l, samples_r = self._synth_impact(n_samples, sample_rate, randf)
        else:
            # Default drone / room tone
            samples_l, samples_r = self._synth_drone(n_samples, sample_rate, randf)

        fade_in = 5.0
        fade_out = 15.0 if item.playback.default_mode == "one_shot" else 5.0

        return write_stereo_wav_16bit(
            path=output_file,
            samples_l=samples_l,
            samples_r=samples_r,
            sample_rate=sample_rate,
            fade_in_ms=fade_in,
            fade_out_ms=fade_out,
            gain=item.gain,
        )

    # --- Birdsong Synthesis ---

    def _synth_dawn_chorus(self, n_samples: int, sr: int, rand01) -> Tuple[List[float], List[float]]:
        """Multi-voice asynchronous forest dawn chorus with high-frequency chirps."""
        l = [0.0] * n_samples
        r = [0.0] * n_samples

        # 4 independent bird voices singing at different times and pitch ranges
        voices = [
            {"base_f": 3200.0, "pan": 0.3, "period": 1.4, "phrase_len": 0.25},
            {"base_f": 4500.0, "pan": 0.7, "period": 2.1, "phrase_len": 0.18},
            {"base_f": 2800.0, "pan": 0.2, "period": 3.0, "phrase_len": 0.35},
            {"base_f": 5200.0, "pan": 0.8, "period": 1.8, "phrase_len": 0.15},
        ]

        for v in voices:
            phase = rand01() * math.pi * 2
            period_samples = int(v["period"] * sr)
            phrase_samples = int(v["phrase_len"] * sr)
            offset = int(rand01() * period_samples)

            for i in range(n_samples):
                cycle_pos = (i + offset) % period_samples
                if cycle_pos < phrase_samples:
                    # Normalized progress inside syllable
                    t = cycle_pos / phrase_samples
                    # Chirp: rapid upward then downward pitch sweep
                    fm = math.sin(t * math.pi * 4.0) * 800.0 + math.sin(t * math.pi * 8.0) * 300.0
                    freq = v["base_f"] + fm
                    # Smooth bell envelope
                    env = math.sin(t * math.pi) ** 2

                    phase += (2.0 * math.pi * freq) / sr
                    val = math.sin(phase) * env * 0.25

                    l[i] += val * (1.0 - v["pan"])
                    r[i] += val * v["pan"]

        # Add subtle distant high-pass foliage whisper
        whisper_phase = 0.0
        for i in range(n_samples):
            whisper_phase += (2.0 * math.pi * 3800.0) / sr
            bg = math.sin(whisper_phase) * 0.015 * (math.sin(i * 0.0002) * 0.5 + 0.5)
            l[i] += bg
            r[i] += bg

        return l, r

    def _synth_cuckoo(self, n_samples: int, sr: int, rand01) -> Tuple[List[float], List[float]]:
        """Distinct clear two-note cuckoo call: high note (~750Hz) -> lower note (~580Hz)."""
        l = [0.0] * n_samples
        r = [0.0] * n_samples

        interval = int(1.8 * sr)  # Repeats every 1.8 seconds
        note1_dur = int(0.22 * sr)
        gap = int(0.08 * sr)
        note2_dur = int(0.35 * sr)

        f1 = 760.0  # Note 1 (higher)
        f2 = 590.0  # Note 2 (lower, minor third below)

        phase1 = 0.0
        phase2 = 0.0

        for i in range(n_samples):
            pos = i % interval
            val = 0.0
            if pos < note1_dur:
                t = pos / note1_dur
                env = math.sin(t * math.pi) ** 1.5
                phase1 += (2.0 * math.pi * (f1 - t * 20.0)) / sr
                val = math.sin(phase1) * env * 0.6 + math.sin(phase1 * 2) * 0.08
            elif pos < note1_dur + gap:
                pass
            elif pos < note1_dur + gap + note2_dur:
                t = (pos - note1_dur - gap) / note2_dur
                env = math.sin(t * math.pi) ** 1.5
                phase2 += (2.0 * math.pi * (f2 - t * 25.0)) / sr
                val = math.sin(phase2) * env * 0.55 + math.sin(phase2 * 2) * 0.07

            l[i] = val * 0.6
            r[i] = val * 0.4
        return l, r

    def _synth_eagle(self, n_samples: int, sr: int, rand01) -> Tuple[List[float], List[float]]:
        """Mountain raptor / eagle sharp screech with pitch rise, harsh overtone, and valley echo."""
        l = [0.0] * n_samples
        r = [0.0] * n_samples

        screech_dur = int(1.2 * sr)
        f_start = 2800.0
        f_peak = 4300.0
        f_end = 3200.0

        phase = 0.0
        phase_mod = 0.0

        for i in range(n_samples):
            if i < screech_dur:
                t = i / screech_dur
                # Rise to peak then glide down
                if t < 0.35:
                    freq = f_start + (f_peak - f_start) * (t / 0.35)
                else:
                    freq = f_peak - (f_peak - f_end) * ((t - 0.35) / 0.65)

                # Tremolo/flutter in voice
                tremolo = 1.0 + 0.25 * math.sin(t * 120.0)
                phase_mod += (2.0 * math.pi * 85.0) / sr  # Rough screech modulator
                harsh = math.sin(phase_mod) * 150.0

                phase += (2.0 * math.pi * (freq + harsh)) / sr
                env = (math.sin(t * math.pi) ** 1.8) * tremolo
                val = (math.sin(phase) + math.sin(phase * 2.0) * 0.4) * env * 0.5
                l[i] = val
                r[i] = val * 0.85

            # Valley echo (delayed by 250ms)
            echo_offset = int(0.28 * sr)
            if i >= echo_offset and (i - echo_offset) < screech_dur:
                l[i] += l[i - echo_offset] * 0.3
                r[i] += r[i - echo_offset] * 0.38
        return l, r

    def _synth_nightingale(self, n_samples: int, sr: int, rand01) -> Tuple[List[float], List[float]]:
        """Nightingale fast lyrical trill / warble."""
        l = [0.0] * n_samples
        r = [0.0] * n_samples

        phase = 0.0
        phrase_len = int(1.5 * sr)
        interval = int(2.5 * sr)

        for i in range(n_samples):
            pos = i % interval
            if pos < phrase_len:
                t = pos / phrase_len
                # Rapid 18Hz vibrato warble
                trill = math.sin(t * math.pi * 36.0) * 600.0
                freq = 3800.0 + trill + math.sin(t * math.pi * 3.0) * 800.0
                env = math.sin(t * math.pi) ** 1.4
                phase += (2.0 * math.pi * freq) / sr
                val = math.sin(phase) * env * 0.4
                l[i] = val * 0.45
                r[i] = val * 0.55
        return l, r

    # --- Weather & Elemental Synthesis ---

    def _synth_rain(self, n_samples: int, sr: int, randf, rand01) -> Tuple[List[float], List[float]]:
        """Continuous rain with pink-filtered noise bed and discrete droplet clicks."""
        l = [0.0] * n_samples
        r = [0.0] * n_samples

        b0_l = b1_l = b2_l = 0.0
        b0_r = b1_r = b2_r = 0.0

        for i in range(n_samples):
            # Pink noise generation (Paul Kellet's filter)
            white_l = randf()
            white_r = randf()

            b0_l = 0.99886 * b0_l + white_l * 0.0555179
            b1_l = 0.99332 * b1_l + white_l * 0.0750759
            b2_l = 0.96900 * b2_l + white_l * 0.1538520
            pink_l = b0_l + b1_l + b2_l + white_l * 0.5362

            b0_r = 0.99886 * b0_r + white_r * 0.0555179
            b1_r = 0.99332 * b1_r + white_r * 0.0750759
            b2_r = 0.96900 * b2_r + white_r * 0.1538520
            pink_r = b0_r + b1_r + b2_r + white_r * 0.5362

            # Random high-frequency droplet transient impulse
            drop = 0.0
            if rand01() < 0.008:
                drop = randf() * 0.4

            l[i] = pink_l * 0.15 + drop
            r[i] = pink_r * 0.15 + drop * 0.8
        return l, r

    def _synth_wind(self, n_samples: int, sr: int, randf) -> Tuple[List[float], List[float]]:
        """LFO-modulated blowing wind with low-mid band resonance."""
        l = [0.0] * n_samples
        r = [0.0] * n_samples

        lpf_l = 0.0
        lpf_r = 0.0

        for i in range(n_samples):
            t = i / sr
            # Slow wind swell envelope (0.2 Hz)
            gust = 0.4 + 0.3 * math.sin(t * 0.4) + 0.2 * math.sin(t * 1.1)
            alpha = 0.02 + 0.03 * gust  # Modulated filter cutoff

            w_l = randf() * gust
            w_r = randf() * gust
            lpf_l += alpha * (w_l - lpf_l)
            lpf_r += alpha * (w_r - lpf_r)

            l[i] = lpf_l * 0.7
            r[i] = lpf_r * 0.7
        return l, r

    def _synth_thunder(self, n_samples: int, sr: int, randf) -> Tuple[List[float], List[float]]:
        """Sub-bass heavy thunder strike with decaying low rumble."""
        l = [0.0] * n_samples
        r = [0.0] * n_samples

        phase = 0.0
        lpf = 0.0

        for i in range(n_samples):
            t = i / sr
            # Sub-bass pitch sweep 75Hz -> 35Hz
            freq = 75.0 * math.exp(-t * 0.8) + 35.0
            phase += (2.0 * math.pi * freq) / sr

            decay = math.exp(-t * 0.65)
            # Low-pass filtered thunder rumble noise
            n = randf() * decay
            lpf += 0.04 * (n - lpf)

            sub = math.sin(phase) * decay * 0.7
            val = (sub + lpf * 0.8)
            l[i] = val
            r[i] = val * 0.95
        return l, r

    def _synth_snap(self, n_samples: int, sr: int, randf) -> Tuple[List[float], List[float]]:
        """Crisp wooden branch snap / footstep transient."""
        l = [0.0] * n_samples
        r = [0.0] * n_samples
        phase = 0.0

        for i in range(n_samples):
            t = i / sr
            decay = math.exp(-t * 45.0)  # Very fast decay
            wood_res = math.sin(phase) * decay * 0.6
            phase += (2.0 * math.pi * 1800.0) / sr
            snap = randf() * decay * 0.8 + wood_res
            l[i] = snap
            r[i] = snap * 0.9
        return l, r

    def _synth_impact(self, n_samples: int, sr: int, randf) -> Tuple[List[float], List[float]]:
        l = [0.0] * n_samples
        r = [0.0] * n_samples
        phase = 0.0
        for i in range(n_samples):
            t = i / sr
            decay = math.exp(-t * 4.0)
            phase += (2.0 * math.pi * 65.0) / sr
            val = (math.sin(phase) * 0.6 + randf() * 0.4) * decay
            l[i] = val
            r[i] = val
        return l, r

    def _synth_drone(self, n_samples: int, sr: int, randf) -> Tuple[List[float], List[float]]:
        l = [0.0] * n_samples
        r = [0.0] * n_samples
        phase_l = 0.0
        phase_r = 0.0
        lpf_l = 0.0
        lpf_r = 0.0
        for i in range(n_samples):
            phase_l += (2.0 * math.pi * 55.0) / sr
            phase_r += (2.0 * math.pi * 55.4) / sr
            n_l = randf()
            n_r = randf()
            lpf_l += 0.05 * (n_l - lpf_l)
            lpf_r += 0.05 * (n_r - lpf_r)
            l[i] = math.sin(phase_l) * 0.4 + lpf_l * 0.15
            r[i] = math.sin(phase_r) * 0.4 + lpf_r * 0.15
        return l, r
