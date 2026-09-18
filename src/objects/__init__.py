"""Holographic Objects package.

Exports the base holographic object contract and concrete object implementations:
- BaseHolographicObject
- HolographicOrb
- HolographicCube
- HolographicPlanet
- HolographicGhostOrchid
- HolographicBhonduFace
- HolographicJellyfish
- HolographicObjectManager
"""

from src.objects.base import BaseHolographicObject
from src.objects.bhondu_face import HolographicBhonduFace
from src.objects.cube import HolographicCube
from src.objects.ghost_orchid import HolographicGhostOrchid
from src.objects.jellyfish import HolographicJellyfish
from src.objects.manager import HolographicObjectManager
from src.objects.orb import HolographicOrb
from src.objects.planet import HolographicPlanet

__all__ = [
    "BaseHolographicObject",
    "HolographicOrb",
    "HolographicCube",
    "HolographicPlanet",
    "HolographicGhostOrchid",
    "HolographicBhonduFace",
    "HolographicJellyfish",
    "HolographicObjectManager",
]
