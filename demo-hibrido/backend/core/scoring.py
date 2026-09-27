"""Motor de scoring. Deterministico a proposito: misma entrada, mismo numero.

La IA solo extrae datos (core/extraccion.py). La calificacion es Python puro
sobre datos ya estructurados. Esto nos da dos cosas que valen oro en una demo:
el porcentaje no cambia si volves a correrlo, y cada punto se puede explicar.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from core.criterios import Criterio, Resultado, evaluar
from core.domain import Perfil

# Si al candidato le falta un requisito indispensable, su score no puede pasar
# de aca por mas que brille en todo lo demas. Es exactamente el dolor que
# describe el cliente: dejar de perder tiempo con quien no cumple el minimo.
TOPE_CON_KNOCKOUT = 40.0


@dataclass
class Vacante:
    titulo: str
    municipio: str
    salario_min: int
    salario_max: int
    criterios: list[Criterio] = field(default_factory=list)
    descripcion: str = ""

    @property
    def indispensables(self) -> list[Criterio]:
        return [c for c in self.criterios if c.indispensable]


@dataclass
class Score:
    valor: float                     # 0 a 100
    resultados: list[Resultado]
    knockouts: list[Resultado]       # indispensables no cumplidos
    faltantes: list[Resultado]       # no verificables por falta de dato
    tope_aplicado: bool

    @property
    def apto(self) -> bool:
        return not self.knockouts

    @property
    def razones(self) -> list[str]:
        """Las 3 frases que ve el reclutador en la tarjeta del candidato.

        Primero lo que descalifica (es lo accionable), despues lo mas fuerte.
        """
        if self.knockouts:
            return [r.detalle for r in self.knockouts[:3]]
        fuertes = sorted(
            (r for r in self.resultados if r.cumple and not r.dato_faltante),
            key=lambda r: (r.aporte, r.peso),
            reverse=True,
        )
        return [r.detalle for r in fuertes[:3]]

    @property
    def alertas(self) -> list[str]:
        """Amarillos: cumple pero con reparos, o no se pudo verificar."""
        salida = [r.detalle for r in self.faltantes]
        salida += [r.detalle for r in self.resultados
                   if r.cumple and not r.dato_faltante and r.puntaje < 0.7]
        return salida

    def desglose(self) -> list[dict]:
        total_peso = sum(r.peso for r in self.resultados) or 1.0
        return [
            {
                "criterio": r.etiqueta,
                "detalle": r.detalle,
                "puntaje": round(r.puntaje * 100),
                "peso": round(r.peso / total_peso * 100),
                "cumple": r.cumple,
                "indispensable": r.indispensable,
                "sin_dato": r.dato_faltante,
            }
            for r in self.resultados
        ]


def calcular(vacante: Vacante, perfil: Perfil) -> Score:
    resultados = [evaluar(c, perfil) for c in vacante.criterios]
    if not resultados:
        return Score(0.0, [], [], [], False)

    peso_total = sum(r.peso for r in resultados) or 1.0
    base = sum(r.aporte for r in resultados) / peso_total * 100

    knockouts = [r for r in resultados if r.indispensable and not r.cumple]
    faltantes = [r for r in resultados if r.dato_faltante]

    # Dentro del techo, los descartados igual se ordenan por que tan cerca
    # quedaron: al que solo se le vencio la licencia lo recuperas en dos
    # semanas, al que le faltan cuatro requisitos no. Un monton de candidatos
    # empatados en 40 no le sirve a nadie.
    indisp = [r for r in resultados if r.indispensable]
    peso_indisp = sum(r.peso for r in indisp) or 1.0
    cumplido = sum(r.peso for r in indisp if r.cumple) / peso_indisp
    tope = TOPE_CON_KNOCKOUT * cumplido

    valor = min(base, tope) if knockouts else base
    return Score(
        valor=round(valor, 1),
        resultados=resultados,
        knockouts=knockouts,
        faltantes=faltantes,
        tope_aplicado=bool(knockouts) and base > tope,
    )


def rankear(vacante: Vacante, perfiles: dict[str, Perfil]) -> list[tuple[str, Score]]:
    """Ordena candidatos de mejor a peor. Los aptos siempre van arriba de los
    descartados, aunque un descartado sume mas puntos brutos."""
    puntuados = [(cid, calcular(vacante, p)) for cid, p in perfiles.items()]
    return sorted(puntuados, key=lambda t: (t[1].apto, t[1].valor), reverse=True)
