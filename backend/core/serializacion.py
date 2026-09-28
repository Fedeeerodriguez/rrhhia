"""Perfil <-> JSON, sin perder la confianza ni el fragmento de cada campo.

El perfil se guarda con su trazabilidad completa, no aplanado a valores. Eso
permite dos cosas: que la demo hibrida pinte en amarillo lo dudoso, y que un
re-scoring no tenga que volver a llamar a la IA.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from core.domain import Campo, Empleo, Origen, Perfil

# Como codificar/decodificar el valor de cada campo. Lo que no esta aca viaja
# tal cual (str, int, float, bool, list[str]).
_FECHAS = {"licencia_vence", "apto_medico_vence"}
_EMPLEOS = {"historial"}


def _enc(nombre: str, valor: Any) -> Any:
    if valor is None:
        return None
    if nombre in _FECHAS:
        return valor.isoformat()
    if nombre in _EMPLEOS:
        return [
            {
                "empresa": e.empresa,
                "puesto": e.puesto,
                "desde": e.desde.isoformat(),
                "hasta": e.hasta.isoformat() if e.hasta else None,
            }
            for e in valor
        ]
    return valor


def decodificar(nombre: str, valor: Any) -> Any:
    """Un valor que llega en JSON (fecha como texto, empleos como dicts) vuelve
    a ser lo que el scoring espera. Lo usa la lectura de la base y tambien la
    demo hibrida, que recibe el perfil del front."""
    if valor is None:
        return None
    if nombre in _FECHAS:
        return date.fromisoformat(valor)
    if nombre in _EMPLEOS:
        return [
            Empleo(
                empresa=e["empresa"],
                puesto=e["puesto"],
                desde=date.fromisoformat(e["desde"]),
                hasta=date.fromisoformat(e["hasta"]) if e.get("hasta") else None,
            )
            for e in valor
        ]
    return valor


def perfil_a_dict(perfil: Perfil) -> dict[str, dict]:
    return {
        nombre: {
            "valor": _enc(nombre, campo.valor),
            "origen": campo.origen.value,
            "confianza": campo.confianza,
            "fragmento": campo.fragmento,
        }
        for nombre, campo in perfil.campos().items()
    }


def perfil_desde_dict(datos: dict[str, dict]) -> Perfil:
    perfil = Perfil()
    for nombre, bruto in (datos or {}).items():
        if not hasattr(perfil, nombre):
            continue    # un campo que ya no existe en el modelo no rompe la lectura
        setattr(perfil, nombre, Campo(
            valor=decodificar(nombre, bruto.get("valor")),
            origen=Origen(bruto.get("origen", Origen.AUSENTE.value)),
            confianza=float(bruto.get("confianza", 0.0)),
            fragmento=bruto.get("fragmento"),
        ))
    return perfil
