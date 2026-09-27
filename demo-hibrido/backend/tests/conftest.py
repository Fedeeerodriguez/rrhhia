"""Aislamiento de los tests.

Dos cosas, las dos importantes:

1. La app no crea ni siembra la base: cada test trae la suya.
2. Se quita ANTHROPIC_API_KEY del entorno. Sin esto los tests llaman a la API
   de verdad: tardan minutos, gastan plata y dejan de ser deterministas. La
   extraccion se prueba contra el motor heuristico, que es el que ademas tiene
   que funcionar cuando la IA no responde.
"""
import os

os.environ["RRHHIA_SIN_INIT"] = "1"
os.environ.pop("ANTHROPIC_API_KEY", None)
