"""Holographic Objects package.

Exports the base holographic object contract and concrete object implementations:
- BaseHolographicObject
- HolographicOrb
- HolographicCube
- HolographicPlanet
- HolographicObjectManager
"""

from src.objects.base import BaseHolographicObject
from src.objects.cube import HolographicCube
from src.objects.manager import HolographicObjectManager
from src.objects.orb import HolographicOrb
from src.objects.planet import HolographicPlanet

__all__ = [
    "BaseHolographicObject",
    "HolographicOrb",
    "HolographicCube",
    "HolographicPlanet",
    "HolographicObjectManager",
]
