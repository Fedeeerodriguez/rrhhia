"""Vocabulario del dominio: perfil del candidato y campos con confianza.

Un campo nunca viaja solo como valor. Siempre lleva de donde salio y que tan
seguro esta el sistema, porque la demo hibrida necesita pintar en amarillo lo
dudoso y mostrar el fragmento del CV al lado para que el reclutador confirme.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any


class Origen(str, Enum):
    FORMULARIO = "formulario"      # lo escribio el candidato: confianza 1.0
    CV = "cv"                      # lo extrajo la IA del PDF
    REVISADO = "revisado"          # la IA lo propuso y un humano lo confirmo/corrigio
    AUSENTE = "ausente"            # no se pudo determinar


@dataclass
class Campo:
    """Un dato del candidato con su trazabilidad."""
    valor: Any = None
    origen: Origen = Origen.AUSENTE
    confianza: float = 0.0         # 0.0 a 1.0
    fragmento: str | None = None   # texto textual del CV que justifica el valor

    @property
    def dudoso(self) -> bool:
        """Lo que la UI pinta en amarillo y pide confirmar."""
        return self.origen == Origen.CV and self.confianza < 0.75

    @property
    def falta(self) -> bool:
        return self.valor in (None, "", [], {}) or self.origen == Origen.AUSENTE

    @classmethod
    def del_formulario(cls, valor: Any) -> "Campo":
        if valor in (None, "", [], {}):
            return cls()
        return cls(valor=valor, origen=Origen.FORMULARIO, confianza=1.0)


class Escolaridad(str, Enum):
    NINGUNA = "ninguna"
    PRIMARIA = "primaria"
    SECUNDARIA = "secundaria"
    PREPARATORIA = "preparatoria"
    TECNICA = "tecnica"
    UNIVERSIDAD = "universidad"

    @property
    def nivel(self) -> int:
        return _NIVEL_ESCOLARIDAD[self]


_NIVEL_ESCOLARIDAD = {
    Escolaridad.NINGUNA: 0,
    Escolaridad.PRIMARIA: 1,
    Escolaridad.SECUNDARIA: 2,
    Escolaridad.PREPARATORIA: 3,
    Escolaridad.TECNICA: 3,
    Escolaridad.UNIVERSIDAD: 4,
}


class TipoLicencia(str, Enum):
    """Las dos familias que conviven en Nuevo Leon.

    Estatal: habilita carga local (torton, 2-3 ejes).
    Federal SICT: habilita autotransporte federal. Categorias segun el Acuerdo
    publicado en el DOF -- la E exige dos anios previos en B o C y vence a los
    2 anios, contra 4 del resto.
    """
    ESTATAL_A = "estatal_A"
    ESTATAL_B = "estatal_B"
    ESTATAL_C = "estatal_C"        # carga local 2-3 ejes / transporte publico
    FEDERAL_A = "federal_A"        # pasajeros
    FEDERAL_B = "federal_B"        # carga federal
    FEDERAL_C = "federal_C"        # carga 2-3 ejes
    FEDERAL_D = "federal_D"        # chofer-guia turismo
    FEDERAL_E = "federal_E"        # doblemente articulado / materiales peligrosos
    FEDERAL_F = "federal_F"        # pasajeros puertos y aeropuertos
    NINGUNA = "ninguna"

    @property
    def es_federal(self) -> bool:
        return self.value.startswith("federal_")


class Unidad(str, Enum):
    CAMIONETA = "camioneta"
    RABON = "rabon"
    TORTON = "torton"
    TRACTOCAMION = "tractocamion"
    FULL = "full"                  # doblemente articulado
    AUTOBUS = "autobus"
    ROLL_OFF = "roll_off"


@dataclass
class Empleo:
    empresa: str
    puesto: str
    desde: date
    hasta: date | None = None      # None = sigue trabajando ahi

    @property
    def meses(self) -> int:
        fin = self.hasta or date.today()
        return max(0, (fin.year - self.desde.year) * 12 + (fin.month - self.desde.month))


@dataclass
class Perfil:
    """Todo lo que sabemos de un candidato, venga de formulario o de CV."""
    nombre: Campo = field(default_factory=Campo)
    telefono: Campo = field(default_factory=Campo)
    email: Campo = field(default_factory=Campo)
    municipio: Campo = field(default_factory=Campo)

    licencias: Campo = field(default_factory=Campo)          # list[TipoLicencia]
    licencia_vence: Campo = field(default_factory=Campo)     # date
    apto_medico_vence: Campo = field(default_factory=Campo)  # date

    anios_experiencia: Campo = field(default_factory=Campo)  # float
    unidades: Campo = field(default_factory=Campo)           # list[Unidad]
    escolaridad: Campo = field(default_factory=Campo)        # Escolaridad
    disponibilidad_foranea: Campo = field(default_factory=Campo)  # bool
    salario_pretendido: Campo = field(default_factory=Campo)      # int MXN/mes
    historial: Campo = field(default_factory=Campo)               # list[Empleo]
    materiales_peligrosos: Campo = field(default_factory=Campo)   # bool

    def campos(self) -> dict[str, Campo]:
        return {k: v for k, v in self.__dict__.items() if isinstance(v, Campo)}

    @property
    def campos_dudosos(self) -> list[str]:
        """Lo que la demo hibrida le pone adelante al reclutador para confirmar."""
        return [k for k, c in self.campos().items() if c.dudoso or c.falta]

    @property
    def completitud(self) -> float:
        campos = self.campos()
        if not campos:
            return 0.0
        return sum(0.0 if c.falta else c.confianza for c in campos.values()) / len(campos)
