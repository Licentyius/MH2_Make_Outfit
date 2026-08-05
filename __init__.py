"""
MakeOutfit
Official wardrobe workspace environment suite for MakeHuman 2.
"""
__version__ = "1.0.0"
__author__ = "Elvaerwyn_MH2"

import sys
import os

_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)

# Points safely to the renamed logic file
from .outfit_logic import initialize_outfit_studio

def initialize_extension(app_reference, glob_reference):
    print("[Outfit Studio Core] Executing native decoupled official tool initialization sequence...")
    return initialize_outfit_studio(app_reference, glob_reference)

__all__ = [
    "initialize_outfit_studio",
    "initialize_extension"
]

