"""
Engine factory and registration.
"""

from __future__ import annotations

from typing import Optional
from texture_forge.engine.base import BaseEngine, EngineError
from texture_forge.engine.mock import MockSyntheticEngine
from texture_forge.engine.mrt2 import MRT2Engine


def get_engine(name: str = "auto") -> BaseEngine:
    """
    Select an audio generation engine.
    - 'auto': Use MRT2 if available, otherwise fallback to synthetic mock.
    - 'mrt2': Force Magenta RealTime 2 (fails if not available).
    - 'mock': Force synthetic mock generator.
    """
    if name == "mock":
        return MockSyntheticEngine()

    mrt2 = MRT2Engine()
    if name == "mrt2":
        if not mrt2.is_available():
            raise EngineError(
                "Engine 'mrt2' requested but neither 'magenta_rt' Python library nor 'hello_mrt2'/'mrt' CLI is found."
            )
        return mrt2

    if name == "auto":
        if mrt2.is_available():
            return mrt2
        return MockSyntheticEngine()

    raise EngineError(f"Unknown engine '{name}'. Supported: 'auto', 'mrt2', 'mock'")
