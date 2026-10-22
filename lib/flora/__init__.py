"""Seeded southwest Wisconsin plant studies: geometry first, ink second."""
from .model import Plant, Stroke, Surface
from .species import SPECIES, generate
from .oak import Oak, savanna_oak

__all__ = ["Plant", "Stroke", "Surface", "SPECIES", "generate", "Oak", "savanna_oak"]
