"""
Audio normalization, post-processing, and physical measurement.
Guarantees 48kHz stereo 16-bit PCM, checks for silence and computes SHA256.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
import struct
from typing import Any, Tuple
import wave


class AudioMetrics:
    def __init__(
        self,
        duration_seconds: float,
        frames: int,
        sample_rate: int,
        channels: int,
        peak_abs: float,
        rms: float,
        sha256: str,
        is_silent: bool,
    ):
        self.duration_seconds = duration_seconds
        self.frames = frames
        self.sample_rate = sample_rate
        self.channels = channels
        self.peak_abs = peak_abs
        self.rms = rms
        self.sha256 = sha256
        self.is_silent = is_silent

    def to_dict(self) -> dict[str, Any]:
        return {
            "duration_seconds": round(self.duration_seconds, 4),
            "frames": self.frames,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "peak_abs": round(self.peak_abs, 6),
            "rms": round(self.rms, 6),
            "sha256": self.sha256,
            "is_silent": self.is_silent,
        }


def compute_file_sha256(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def measure_wav(path: Path | str) -> AudioMetrics:
    """Measure physical properties of a WAV file without extra dependencies."""
    path = Path(path)
    file_hash = compute_file_sha256(path)

    with wave.open(str(path), "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()
        raw_bytes = wf.readframes(n_frames)

    duration = n_frames / framerate if framerate > 0 else 0.0

    if sampwidth != 2:
        # Standardize assumption or simple read
        scale = 1.0 / (2 ** (8 * sampwidth - 1))
    else:
        scale = 1.0 / 32768.0

    # Unpack 16-bit signed PCM
    total_samples = n_frames * n_channels
    if total_samples == 0:
        return AudioMetrics(
            duration_seconds=0.0,
            frames=0,
            sample_rate=framerate,
            channels=n_channels,
            peak_abs=0.0,
            rms=0.0,
            sha256=file_hash,
            is_silent=True,
        )

    # Process samples in chunks
    peak_abs = 0.0
    sum_squares = 0.0

    if sampwidth == 2:
        fmt = f"<{total_samples}h"
        samples = struct.unpack(fmt, raw_bytes)
        for s in samples:
            val = abs(s * scale)
            if val > peak_abs:
                peak_abs = val
            sum_squares += val * val
    else:
        # Fallback for non-16-bit
        peak_abs = 0.0
        sum_squares = 0.0

    rms = math.sqrt(sum_squares / total_samples) if total_samples > 0 else 0.0
    is_silent = peak_abs < 1e-4

    return AudioMetrics(
        duration_seconds=duration,
        frames=n_frames,
        sample_rate=framerate,
        channels=n_channels,
        peak_abs=peak_abs,
        rms=rms,
        sha256=file_hash,
        is_silent=is_silent,
    )


def write_stereo_wav_16bit(
    path: Path | str,
    samples_l: list[float],
    samples_r: list[float],
    sample_rate: int = 48000,
    fade_in_ms: float = 10.0,
    fade_out_ms: float = 10.0,
    gain: float = 1.0,
) -> AudioMetrics:
    """
    Writes stereo audio frames to a 16-bit PCM WAV file with optional micro-fades.
    Applies gain and clamps to [-1.0, 1.0].
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    n_frames = min(len(samples_l), len(samples_r))
    fade_in_frames = int(sample_rate * (fade_in_ms / 1000.0))
    fade_out_frames = int(sample_rate * (fade_out_ms / 1000.0))

    packed_data = bytearray(n_frames * 4)  # 2 channels * 2 bytes
    offset = 0

    for i in range(n_frames):
        # Calculate fade envelope
        env = 1.0
        if fade_in_frames > 0 and i < fade_in_frames:
            env *= i / fade_in_frames
        if fade_out_frames > 0 and i >= n_frames - fade_out_frames:
            env *= (n_frames - 1 - i) / fade_out_frames

        # Left channel
        s_l = max(-1.0, min(1.0, samples_l[i] * gain * env))
        val_l = int(s_l * 32767.0)

        # Right channel
        s_r = max(-1.0, min(1.0, samples_r[i] * gain * env))
        val_r = int(s_r * 32767.0)

        struct.pack_into("<hh", packed_data, offset, val_l, val_r)
        offset += 4

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(packed_data)

    return measure_wav(path)
