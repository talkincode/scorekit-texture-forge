from pathlib import Path
from texture_forge.processor import write_stereo_wav_16bit, measure_wav


def test_write_and_measure_wav(tmp_path: Path):
    wav_path = tmp_path / "test.wav"
    sr = 48000
    duration_sec = 0.5
    n_samples = int(sr * duration_sec)

    # 440 Hz tone
    import math
    samples_l = [math.sin(2 * math.pi * 440 * i / sr) * 0.5 for i in range(n_samples)]
    samples_r = [math.sin(2 * math.pi * 440 * i / sr) * 0.5 for i in range(n_samples)]

    metrics = write_stereo_wav_16bit(
        path=wav_path,
        samples_l=samples_l,
        samples_r=samples_r,
        sample_rate=sr,
        gain=1.0,
    )

    assert metrics.frames == n_samples
    assert metrics.sample_rate == sr
    assert metrics.channels == 2
    assert not metrics.is_silent
    assert metrics.peak_abs > 0.4
    assert len(metrics.sha256) == 64

    # Verify measure_wav standalone
    rem = measure_wav(wav_path)
    assert rem.sha256 == metrics.sha256
    assert rem.frames == metrics.frames
