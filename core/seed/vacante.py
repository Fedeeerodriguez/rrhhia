"""Vacante de la demo.

Calibrada con vacantes reales publicadas en Nuevo Leon (OCC, Computrabajo,
Indeed, Jooble, Portal del Empleo) y con el Acuerdo de categorias de licencia
federal publicado en el DOF. Ver docs/investigacion-vacantes-nl.md.
"""
from __future__ import annotations

from core.criterios import Criterio
from core.scoring import Vacante

ZONA_METROPOLITANA = [
    "Monterrey", "Apodaca", "Guadalupe", "San Nicolas de los Garza",
    "Santa Catarina", "General Escobedo", "San Pedro Garza Garcia",
    "Juarez", "Garcia", "Santiago", "Cadereyta Jimenez",
]


def vacante_operador_foraneo() -> Vacante:
    return Vacante(
        titulo="Operador de Tractocamion Foraneo",
        municipio="Apodaca",
        salario_min=18000,
        salario_max=23000,
        descripcion=(
            "Operacion de tractocamion en rutas foraneas desde Apodaca, N.L. "
            "Sueldo base mas bonos por viaje. Prestaciones de ley."
        ),
        criterios=[
            # --- Indispensables: si falta uno, el score topa en 40 ---
            Criterio(
                codigo="licencia",
                etiqueta="Licencia federal B o E",
                evaluador="licencia_tipo",
                params={"acepta": ["federal_B", "federal_E"]},
                peso=3.0,
                indispensable=True,
            ),
            Criterio(
                codigo="licencia_vigencia",
                etiqueta="Licencia vigente",
                evaluador="licencia_vigente",
                params={"dias_margen": 45},
                peso=2.5,
                indispensable=True,
            ),
            Criterio(
                codigo="apto_medico",
                etiqueta="Apto medico vigente",
                evaluador="apto_medico_vigente",
                params={},
                peso=2.0,
                indispensable=True,
            ),
            Criterio(
                codigo="experiencia",
                etiqueta="Experiencia minima 2 anios",
                evaluador="experiencia_anios",
                params={"minimo": 2, "ideal": 8},
                peso=2.5,
                indispensable=True,
            ),
            Criterio(
                codigo="escolaridad",
                etiqueta="Secundaria terminada",
                evaluador="escolaridad_minima",
                params={"minima": "secundaria"},
                peso=1.0,
                indispensable=True,
            ),
            Criterio(
                codigo="foraneo",
                etiqueta="Disponibilidad foranea",
                evaluador="disponibilidad_foranea",
                params={},
                peso=2.0,
                indispensable=True,
            ),
            # --- Deseables: suman, no descalifican ---
            Criterio(
                codigo="unidades",
                etiqueta="Tractocamion y doblemente articulado",
                evaluador="unidades_manejadas",
                params={"unidades": ["tractocamion", "full"]},
                peso=2.0,
            ),
            Criterio(
                codigo="estabilidad",
                etiqueta="Estabilidad laboral (5 anios)",
                evaluador="estabilidad_laboral",
                params={"max_cambios": 2},
                peso=1.5,
            ),
            Criterio(
                codigo="matpel",
                etiqueta="Materiales peligrosos",
                evaluador="materiales_peligrosos",
                params={},
                peso=1.0,
            ),
            Criterio(
                codigo="zona",
                etiqueta="Reside en zona metropolitana",
                evaluador="ubicacion",
                params={"municipios": ZONA_METROPOLITANA},
                peso=1.5,
            ),
            Criterio(
                codigo="salario",
                etiqueta="Pretension dentro de rango",
                evaluador="salario_en_rango",
                params={"maximo": 23000},
                peso=1.0,
            ),
        ],
    )
