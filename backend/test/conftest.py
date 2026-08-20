"""Configuración de pytest dentro del directorio backend/test."""

import sys
import os

# Asegurar que el directorio backend y raíz estén en sys.path
test_dir = os.path.abspath(os.path.dirname(__file__))
backend_dir = os.path.abspath(os.path.join(test_dir, ".."))
root_dir = os.path.abspath(os.path.join(backend_dir, ".."))

for p in [backend_dir, root_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)
