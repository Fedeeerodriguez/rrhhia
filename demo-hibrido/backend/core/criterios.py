"""Criterios de evaluacion: cada uno mira un aspecto del perfil y devuelve
un puntaje 0..1, si cumple o no, y una frase que explica por que.

La explicacion no es decorativa: es lo que el reclutador lee para decidir, y
lo que nos permite defender un 94% frente a un 71%.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Callable

from core.domain import Escolaridad, Perfil, TipoLicencia, Unidad


@dataclass
class Resultado:
    codigo: str
    etiqueta: str
    puntaje: float            # 0.0 a 1.0
    cumple: bool
    detalle: str              # frase para la UI
    indispensable: bool = False
    peso: float = 1.0
    dato_faltante: bool = False   # no lo pudimos verificar (distinto de no cumplir)

    @property
    def aporte(self) -> float:
        return self.puntaje * self.peso


@dataclass
class Criterio:
    codigo: str
    etiqueta: str
    evaluador: str
    params: dict[str, Any] = field(default_factory=dict)
    peso: float = 1.0
    indispensable: bool = False


EVALUADORES: dict[str, Callable[[Perfil, dict], tuple[float, bool, str, bool]]] = {}

# Nombres para mostrar. El valor interno queda en minuscula y sin acentos
# (es una clave), pero al reclutador se le muestra escrito como se habla.
NOMBRE_UNIDAD = {
    "camioneta": "camioneta", "rabon": "rabón", "torton": "tortón",
    "tractocamion": "tractocamión", "full": "full (doblemente articulado)",
    "autobus": "autobús", "roll_off": "roll off",
}


def sin_acentos(texto: str) -> str:
    """Para comparar lo que escribio una persona con una lista nuestra."""
    plano = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in plano if not unicodedata.combining(c)).lower()


def evaluador(nombre: str):
    def deco(fn):
        EVALUADORES[nombre] = fn
        return fn
    return deco


# --- Licencia -----------------------------------------------------------------

@evaluador("licencia_tipo")
def _licencia_tipo(perfil: Perfil, params: dict):
    aceptadas = {TipoLicencia(x) for x in params["acepta"]}
    if perfil.licencias.falta:
        return 0.0, False, "No informa qué licencia tiene", True
    tiene = {TipoLicencia(x) for x in perfil.licencias.valor}
    match = tiene & aceptadas
    if match:
        nombres = ", ".join(sorted(m.value.replace("_", " ") for m in match))
        return 1.0, True, f"Tiene licencia {nombres}", False
    # Distingue "no tiene nada" de "tiene la estatal pero le falta la federal":
    # el segundo es recuperable y al reclutador le importa saberlo.
    if any(not t.es_federal for t in tiene) and any(a.es_federal for a in aceptadas):
        actuales = ", ".join(sorted(t.value.replace("_", " ") for t in tiene))
        return 0.25, False, f"Solo tiene licencia estatal ({actuales}); se pide federal", False
    return 0.0, False, "No tiene ninguna de las licencias requeridas", False


@evaluador("licencia_vigente")
def _licencia_vigente(perfil: Perfil, params: dict):
    margen = params.get("dias_margen", 30)
    if perfil.licencia_vence.falta:
        return 0.0, False, "No informa vencimiento de licencia", True
    vence: date = perfil.licencia_vence.valor
    dias = (vence - date.today()).days
    if dias < 0:
        return 0.0, False, f"Licencia VENCIDA hace {abs(dias)} días ({vence:%d/%m/%Y})", False
    if dias < margen:
        return 0.5, True, f"Licencia vence en {dias} días ({vence:%d/%m/%Y}) -- renovar ya", False
    return 1.0, True, f"Licencia vigente hasta {vence:%d/%m/%Y}", False


@evaluador("apto_medico_vigente")
def _apto_medico(perfil: Perfil, params: dict):
    if perfil.apto_medico_vence.falta:
        return 0.0, False, "No informa apto médico", True
    vence: date = perfil.apto_medico_vence.valor
    dias = (vence - date.today()).days
    if dias < 0:
        return 0.0, False, f"Apto médico vencido ({vence:%d/%m/%Y})", False
    if dias < 30:
        return 0.6, True, f"Apto medico vence en {dias} días", False
    return 1.0, True, f"Apto médico vigente hasta {vence:%d/%m/%Y}", False


# --- Experiencia --------------------------------------------------------------

def _anios(cantidad: float) -> str:
    """1 año, 2 años, 2.5 años."""
    return f"{cantidad:g} año" + ("" if cantidad == 1 else "s")


@evaluador("experiencia_anios")
def _experiencia(perfil: Perfil, params: dict):
    minimo = float(params["minimo"])
    ideal = float(params.get("ideal", minimo * 2))
    if perfil.anios_experiencia.falta:
        return 0.0, False, "No informa años de experiencia", True
    anios = float(perfil.anios_experiencia.valor)
    if anios < minimo:
        parcial = max(0.0, anios / minimo) * 0.6
        return parcial, False, f"{_anios(anios)} de experiencia; se piden {minimo:g}", False
    if anios >= ideal:
        return 1.0, True, f"{_anios(anios)} de experiencia (supera los {minimo:g} pedidos)", False
    rango = max(ideal - minimo, 0.001)
    return 0.7 + 0.3 * (anios - minimo) / rango, True, f"{_anios(anios)} de experiencia", False


@evaluador("unidades_manejadas")
def _unidades(perfil: Perfil, params: dict):
    pedidas = {Unidad(u) for u in params["unidades"]}
    if perfil.unidades.falta:
        return 0.0, False, "No informa qué unidades manejó", True
    tiene = {Unidad(u) for u in perfil.unidades.valor}
    match = tiene & pedidas
    if not match:
        return 0.0, False, "No manejó ninguna de las unidades requeridas", False
    ratio = len(match) / len(pedidas)
    nombres = ", ".join(sorted(NOMBRE_UNIDAD.get(m.value, m.value) for m in match))
    return ratio, True, f"Manejó {nombres}", False


@evaluador("estabilidad_laboral")
def _estabilidad(perfil: Perfil, params: dict):
    """Aparece explicito en varias vacantes de NL: estabilidad últimos 5 años."""
    max_cambios = int(params.get("max_cambios", 3))
    if perfil.historial.falta:
        return 0.0, False, "Sin historial laboral para evaluar estabilidad", True
    corte = date.today() - timedelta(days=5 * 365)
    recientes = [e for e in perfil.historial.valor if (e.hasta or date.today()) >= corte]
    cambios = max(0, len(recientes) - 1)
    if cambios <= max_cambios:
        plural = "empleo" if len(recientes) == 1 else "empleos"
        return 1.0, True, f"{len(recientes)} {plural} en los últimos 5 años", False
    exceso = cambios - max_cambios
    return (max(0.0, 1.0 - 0.25 * exceso), True,
            f"{len(recientes)} empleos en 5 años · rotación alta", False)


# --- Otros --------------------------------------------------------------------

@evaluador("escolaridad_minima")
def _escolaridad(perfil: Perfil, params: dict):
    minima = Escolaridad(params["minima"])
    if perfil.escolaridad.falta:
        return 0.0, False, "No informa escolaridad", True
    actual = Escolaridad(perfil.escolaridad.valor)
    if actual.nivel >= minima.nivel:
        return 1.0, True, f"{actual.value.capitalize()} (se pide {minima.value})", False
    return 0.0, False, f"{actual.value.capitalize()}; se pide {minima.value} terminada", False


@evaluador("disponibilidad_foranea")
def _foraneo(perfil: Perfil, params: dict):
    if perfil.disponibilidad_foranea.falta:
        return 0.0, False, "No informa disponibilidad para viajes foráneos", True
    if perfil.disponibilidad_foranea.valor:
        return 1.0, True, "Disponible para viajes foráneos", False
    return 0.0, False, "NO disponible para viajes foráneos", False


@evaluador("ubicacion")
def _ubicacion(perfil: Perfil, params: dict):
    zona = [sin_acentos(m) for m in params["municipios"]]
    if perfil.municipio.falta:
        return 0.0, False, "No informa domicilio", True
    municipio = str(perfil.municipio.valor)
    escrito = sin_acentos(municipio)
    # Por contencion y no por igualdad: "Apodaca, Nuevo Leon" y "Apodaca" son
    # el mismo lugar, y quien lo escribe no sabe que formato esperamos.
    if any(m in escrito or escrito in m for m in zona):
        return 1.0, True, f"Vive en {municipio}", False
    return 0.2, False, f"Vive en {municipio}, fuera de la zona de operación", False


@evaluador("salario_en_rango")
def _salario(perfil: Perfil, params: dict):
    tope = int(params["maximo"])
    if perfil.salario_pretendido.falta:
        return 0.5, True, "No informa pretensión salarial", True
    pretende = int(perfil.salario_pretendido.valor)
    if pretende <= tope:
        return 1.0, True, f"Pretende ${pretende:,} MXN, dentro del rango", False
    exceso = (pretende - tope) / tope
    if exceso <= 0.15:
        return 0.6, True, f"Pretende ${pretende:,} MXN, {exceso:.0%} arriba del tope", False
    return 0.0, False, f"Pretende ${pretende:,} MXN, muy arriba del tope de ${tope:,}", False


@evaluador("materiales_peligrosos")
def _matpel(perfil: Perfil, params: dict):
    if perfil.materiales_peligrosos.falta:
        return 0.0, False, "No informa experiencia en materiales peligrosos", True
    if perfil.materiales_peligrosos.valor:
        return 1.0, True, "Con experiencia en materiales peligrosos", False
    return 0.0, False, "Sin experiencia en materiales peligrosos", False


def evaluar(criterio: Criterio, perfil: Perfil) -> Resultado:
    fn = EVALUADORES[criterio.evaluador]
    puntaje, cumple, detalle, faltante = fn(perfil, criterio.params)
    return Resultado(
        codigo=criterio.codigo,
        etiqueta=criterio.etiqueta,
        puntaje=round(puntaje, 4),
        cumple=cumple,
        detalle=detalle,
        indispensable=criterio.indispensable,
        peso=criterio.peso,
        dato_faltante=faltante,
    )
