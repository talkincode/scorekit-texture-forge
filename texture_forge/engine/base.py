"""
Base interface for sound texture generation engines.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from texture_forge.processor import AudioMetrics
from texture_forge.recipe import RecipeItem


class EngineError(Exception):
    """Raised when audio generation fails."""
    pass


class BaseEngine(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the engine."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if runtime dependencies for this engine are present."""
        pass

    @abstractmethod
    def generate(
        self,
        item: RecipeItem,
        output_file: Path,
        sample_rate: int = 48000,
    ) -> AudioMetrics:
        """
        Generate audio for the recipe item and write to output_file.
        Returns measured AudioMetrics.
        """
        pass
