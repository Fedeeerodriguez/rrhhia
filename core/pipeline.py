"""Etapas del tablero y reglas de movimiento.

El scoring no mueve candidatos solo: propone. El reclutador decide. Un filtro
que mueve gente a Rechazado por su cuenta es un filtro en el que nadie confia.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from core.scoring import Score

# Score minimo para que el sistema proponga pasar a Filtrado. No descarta a
# nadie por debajo: solo deja de proponerlo.
UMBRAL_FILTRADO = 60.0


class Etapa(str, Enum):
    POSTULADO = "postulado"
    FILTRADO = "filtrado"
    ENTREVISTA = "entrevista"
    ACEPTADO = "aceptado"
    RECHAZADO = "rechazado"

    @property
    def es_terminal(self) -> bool:
        return self in (Etapa.ACEPTADO, Etapa.RECHAZADO)

    @property
    def etiqueta(self) -> str:
        return _ETIQUETAS[self]


_ETIQUETAS = {
    Etapa.POSTULADO: "Postulados",
    Etapa.FILTRADO: "Filtrados",
    Etapa.ENTREVISTA: "En entrevista",
    Etapa.ACEPTADO: "Aceptados",
    Etapa.RECHAZADO: "Rechazados",
}

# Desde cualquier etapa no terminal se puede rechazar; el avance es ordenado
# pero se permite volver atras, porque en la vida real el reclutador se
# equivoca de columna al arrastrar.
_TRANSICIONES: dict[Etapa, set[Etapa]] = {
    Etapa.POSTULADO: {Etapa.FILTRADO, Etapa.ENTREVISTA, Etapa.RECHAZADO},
    Etapa.FILTRADO: {Etapa.POSTULADO, Etapa.ENTREVISTA, Etapa.RECHAZADO},
    Etapa.ENTREVISTA: {Etapa.FILTRADO, Etapa.ACEPTADO, Etapa.RECHAZADO},
    Etapa.ACEPTADO: {Etapa.ENTREVISTA},
    Etapa.RECHAZADO: {Etapa.POSTULADO},
}


class MovimientoInvalido(ValueError):
    pass


@dataclass
class EventoEtapa:
    desde: Etapa
    hacia: Etapa
    autor: str
    momento: datetime = field(default_factory=datetime.now)
    automatico: bool = False
    nota: str | None = None


def puede_mover(desde: Etapa, hacia: Etapa) -> bool:
    return hacia in _TRANSICIONES.get(desde, set())


def mover(desde: Etapa, hacia: Etapa, autor: str, nota: str | None = None,
          automatico: bool = False) -> EventoEtapa:
    if desde == hacia:
        raise MovimientoInvalido(f"El candidato ya esta en {hacia.etiqueta}")
    if not puede_mover(desde, hacia):
        raise MovimientoInvalido(
            f"No se puede pasar de {desde.etiqueta} a {hacia.etiqueta}")
    return EventoEtapa(desde=desde, hacia=hacia, autor=autor, nota=nota,
                       automatico=automatico)


def sugerencia(score: Score) -> tuple[Etapa, str]:
    """Que propone el sistema al terminar de procesar. Solo propone."""
    if not score.apto:
        falla = score.knockouts[0].etiqueta if score.knockouts else "un requisito indispensable"
        return Etapa.RECHAZADO, f"No cumple: {falla}"
    if score.valor >= UMBRAL_FILTRADO:
        return Etapa.FILTRADO, f"Cumple los requisitos ({score.valor:.0f}%)"
    return Etapa.POSTULADO, f"Apto pero con puntaje bajo ({score.valor:.0f}%)"


@dataclass
class Tablero:
    """Vista del kanban: candidatos agrupados por columna, ordenados por score."""
    columnas: dict[Etapa, list] = field(default_factory=dict)

    @classmethod
    def armar(cls, postulaciones: list) -> "Tablero":
        columnas: dict[Etapa, list] = {e: [] for e in Etapa}
        for p in postulaciones:
            columnas[Etapa(p.etapa)].append(p)
        for etapa in columnas:
            # Ordena por el score final (con el ajuste de la IA) cuando existe.
            columnas[etapa].sort(
                key=lambda p: (getattr(p, "score_final", None) or p.score),
                reverse=True)
        return cls(columnas=columnas)

    def conteo(self) -> dict[str, int]:
        return {e.value: len(v) for e, v in self.columnas.items()}
