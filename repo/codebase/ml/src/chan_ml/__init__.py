"""Machine-learning components for the CHẮN detection engine."""

from .constants import ENGINE_VERSION, SIGNAL_CODES
from .model import PhishingSignalModel

__all__ = ["ENGINE_VERSION", "SIGNAL_CODES", "PhishingSignalModel"]
