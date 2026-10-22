"""Seeded southwest Wisconsin plant studies: geometry first, ink second."""
from .model import Plant, Stroke, Surface
from .species import SPECIES, generate

__all__ = ["Plant", "Stroke", "Surface", "SPECIES", "generate"]
