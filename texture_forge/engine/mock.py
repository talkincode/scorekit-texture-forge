"""
Deterministic synthetic fallback generator for tests, CI, and prototyping.
Generates audible, non-silent 48kHz stereo WAVs shaped by category and seed.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
from texture_forge.engine.base import BaseEngine
from texture_forge.processor import AudioMetrics, write_stereo_wav_16bit
from texture_forge.recipe import RecipeItem


class MockSyntheticEngine(BaseEngine):
    """
    Deterministic audio synthesizer based on Knuth LCG and sine/noise synthesis.
    Requires zero external dependencies.
    """

    @property
    def name(self) -> str:
        return "synthetic_mock"

    def is_available(self) -> bool:
        return True

    def _derive_seed(self, item: RecipeItem) -> int:
        if item.seed is not None:
            return item.seed
        # Hash item ID and prompt to integer seed
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

        # LCG parameters
        state = seed & 0xFFFFFFFF
        a = 1664525
        c = 1013904223
        m = 2**32

        def next_rand() -> float:
            nonlocal state
            state = (a * state + c) % m
            return (state / m) * 2.0 - 1.0

        # Frequency characteristics based on category
        cat = item.category
        if cat in ("industrial", "tonal"):
            base_freq_l = 55.0  # Low drone A1
            base_freq_r = 55.5  # Slight binaural beating
            noise_mix = 0.2
        elif cat in ("ambience", "organic"):
            base_freq_l = 110.0
            base_freq_r = 112.0
            noise_mix = 0.6  # Wind/water-like noise
        elif cat == "impact":
            base_freq_l = 80.0
            base_freq_r = 82.0
            noise_mix = 0.5
        else:
            base_freq_l = 140.0
            base_freq_r = 143.0
            noise_mix = 0.4

        samples_l: list[float] = [0.0] * n_samples
        samples_r: list[float] = [0.0] * n_samples

        phase_l = 0.0
        phase_r = 0.0
        d_phase_l = (2.0 * math.pi * base_freq_l) / sample_rate
        d_phase_r = (2.0 * math.pi * base_freq_r) / sample_rate

        # Simple 1-pole lowpass filter state for noise smoothing
        lpf_l = 0.0
        lpf_r = 0.0
        alpha = 0.15

        for i in range(n_samples):
            # Tonal component
            s_l = math.sin(phase_l) * 0.4 + math.sin(phase_l * 2.0) * 0.15
            s_r = math.sin(phase_r) * 0.4 + math.sin(phase_r * 2.0) * 0.15
            phase_l += d_phase_l
            phase_r += d_phase_r

            # Noise component
            noise_l = next_rand()
            noise_r = next_rand()
            lpf_l += alpha * (noise_l - lpf_l)
            lpf_r += alpha * (noise_r - lpf_r)

            val_l = (s_l * (1.0 - noise_mix) + lpf_l * noise_mix)
            val_r = (s_r * (1.0 - noise_mix) + lpf_r * noise_mix)

            # If impact, apply exponential decay envelope
            if cat == "impact":
                t = i / sample_rate
                decay = math.exp(-3.5 * t)
                val_l *= decay
                val_r *= decay

            samples_l[i] = val_l
            samples_r[i] = val_r

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
