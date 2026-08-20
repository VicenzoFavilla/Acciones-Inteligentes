"""Configuración de pytest para el backend y suite de pruebas del Agente Financiero."""

import sys
import os
import pytest

# Asegurar que el directorio backend y la raíz del proyecto estén en sys.path
backend_dir = os.path.abspath(os.path.dirname(__file__))
root_dir = os.path.abspath(os.path.join(backend_dir, ".."))

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
