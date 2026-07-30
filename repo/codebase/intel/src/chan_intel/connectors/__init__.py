"""Licensed threat-intelligence source adapters."""

from .openphish import OpenPhishConnector
from .phishtank import PhishTankConnector

__all__ = ["OpenPhishConnector", "PhishTankConnector"]
