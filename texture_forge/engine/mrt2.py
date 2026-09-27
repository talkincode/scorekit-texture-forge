"""
Magenta RealTime 2 (MRT2) inference engine.
Supports native Python magenta-rt (MLX/JAX) and C++ hello_mrt2 CLI.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Optional
from texture_forge.engine.base import BaseEngine, EngineError
from texture_forge.processor import AudioMetrics, measure_wav
from texture_forge.recipe import RecipeItem


class MRT2Engine(BaseEngine):
    """
    Engine that interfaces with Magenta RealTime 2.
    """

    def __init__(
        self,
        model_size: str = "mrt2_base",
        cli_path: Optional[str] = None,
    ):
        self.model_size = model_size
        self._cli_path = cli_path or shutil.which("hello_mrt2")
        self._mrt_cmd = shutil.which("mrt")

    @property
    def name(self) -> str:
        return "magenta_realtime_2"

    def is_available(self) -> bool:
        # Check python import or CLI presence
        try:
            import magenta_rt  # type: ignore # noqa: F401
            return True
        except ImportError:
            pass

        if self._cli_path and os.path.exists(self._cli_path):
            return True
        if self._mrt_cmd:
            return True
        return False

    def generate(
        self,
        item: RecipeItem,
        output_file: Path,
        sample_rate: int = 48000,
    ) -> AudioMetrics:
        output_file = Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # 1. Try python module
        try:
            return self._generate_python(item, output_file, sample_rate)
        except ImportError:
            pass
        except Exception as e:
            # Fallthrough to CLI if python failed on environment setup
            pass

        # 2. Try hello_mrt2 C++ CLI
        if self._cli_path and os.path.exists(self._cli_path):
            return self._generate_cpp_cli(item, output_file)

        # 3. Try mrt CLI
        if self._mrt_cmd:
            return self._generate_mrt_cli(item, output_file)

        raise EngineError(
            "Magenta RealTime 2 is not available. Please install 'magenta-rt' (uv pip install 'magenta-rt[mlx]') "
            "or compile the 'hello_mrt2' CLI. Alternatively, pass '--engine mock' for testing."
        )

    def _generate_python(self, item: RecipeItem, output_file: Path, sample_rate: int) -> AudioMetrics:
        from magenta_rt.mlx import MLXEngine  # type: ignore

        engine = MLXEngine()
        engine.load_model(self.model_size)

        temp = item.temperature if item.temperature is not None else 0.9
        cfg_coca = item.cfg_musiccoca if item.cfg_musiccoca is not None else 4.0

        engine.set_temperature(temp)
        engine.set_cfg_musiccoca(cfg_coca)
        engine.set_cfg_notes(0.0)
        if item.playback.default_mode == "loop":
            engine.set_drumless(True)

        engine.set_text_prompt(item.prompt)
        engine.prefill_silence(duration_frames=100)

        frames = int(item.duration_sec * 25)
        audio = engine.generate(num_frames=frames)
        audio.save_wav(str(output_file), sample_rate=sample_rate)

        return measure_wav(output_file)

    def _generate_cpp_cli(self, item: RecipeItem, output_file: Path) -> AudioMetrics:
        num_frames = int(item.duration_sec * 25)
        cmd = [
            self._cli_path,
            "--prompt", item.prompt,
            "--output", str(output_file),
            "--prefill-silence",
            str(num_frames),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise EngineError(f"hello_mrt2 failed with exit {res.returncode}: {res.stderr}")
        return measure_wav(output_file)

    def _generate_mrt_cli(self, item: RecipeItem, output_file: Path) -> AudioMetrics:
        cmd = [
            self._mrt_cmd,
            "mlx", "generate",
            "--prompt", item.prompt,
            "--duration", str(item.duration_sec),
            "--model", self.model_size,
            "--output", str(output_file),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise EngineError(f"mrt CLI failed with exit {res.returncode}: {res.stderr}")
        return measure_wav(output_file)
