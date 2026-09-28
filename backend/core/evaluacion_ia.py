"""Segunda capa: la lectura cualitativa que las reglas no pueden hacer.

Las reglas miran hechos verificables —la licencia vence tal día, tiene tantos
años— y eso está bien: son los que pueden terminar en un reclamo y hay que
poder defenderlos con una fecha, no con un modelo.

Lo que las reglas no ven es el matiz. Seis empleos en cinco años pueden ser
rotación o una progresión de rabón a tortón a full. Nueve años manejando pueden
ser reparto urbano o ruta larga a Laredo. Para una vacante foránea eso cambia
todo, y ningún criterio numérico lo distingue.

**Tres reglas que hacen esto confiable:**

1. **La IA no descarta a nadie.** Evalúa a todos, incluidos los que no cumplen
   un indispensable, porque todos tienen derecho a ser evaluados. Lo que hace es
   mostrar quiénes son los más aptos y quiénes no.
2. **Nunca revierte un requisito indispensable.** Si la licencia está vencida,
   no hay evaluación que lo cambie: el tope se vuelve a aplicar después del
   ajuste. La IA ordena dentro de cada grupo, no decide quién entra.
3. **Los dos números se muestran siempre.** El reclutador ve qué parte es
   objetiva y qué parte es criterio.

Sin `ANTHROPIC_API_KEY` no hay evaluación y el sistema sigue funcionando con el
puntaje por requisitos, que es el que manda.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from core.extraccion import MODELO
from core.scoring import TOPE_CON_KNOCKOUT, Score, Vacante
from core.serializacion import perfil_a_dict
from core.domain import Perfil

# Cuánto puede mover la IA el puntaje. Acotado a propósito: es un matiz sobre
# una medición objetiva, no una segunda opinión que la reemplace.
AJUSTE_MAXIMO = 10.0

NIVELES = ("muy apto", "apto", "con reservas", "poco apto")


@dataclass
class Evaluacion:
    nivel: str                                  # uno de NIVELES
    resumen: str
    fortalezas: list[str] = field(default_factory=list)
    riesgos: list[str] = field(default_factory=list)
    ajuste: float = 0.0
    veredicto: str = ""                         # qué haría un reclutador
    modelo: str = MODELO

    def a_dict(self) -> dict:
        return asdict(self)


INSTRUCCIONES = """Evalúas candidatos a operador de autotransporte en México para
un reclutador. Devuelves SOLO JSON.

Ya existe un puntaje por requisitos, calculado con reglas objetivas sobre hechos
verificables (licencias, vigencias, años, escolaridad). NO lo repitas ni lo
discutas: tu trabajo es el matiz que las reglas no pueden ver.

Mirá:
- Progresión real: ¿los cambios de empresa fueron crecimiento o rotación?
- Calidad de la experiencia: ¿ruta larga foránea o reparto urbano? ¿qué unidades?
- Especialización que suma para esta vacante.
- Riesgos: huecos sin explicar, incoherencias, datos que no cierran.

Formato exacto:
{
  "nivel": "muy apto" | "apto" | "con reservas" | "poco apto",
  "resumen": "una o dos frases, para que el reclutador entienda de un vistazo",
  "fortalezas": ["...", "..."],      // maximo 3, una linea cada una
  "riesgos": ["..."],                // maximo 2, una linea cada una
  "ajuste": número entre -10 y 10,
  "veredicto": "qué harías con este candidato, en una frase"
}

Sobre el ajuste: es un retoque al puntaje por requisitos, no una nota nueva.
0 significa que las reglas ya lo midieron bien. Usá los extremos solo cuando
haya algo fuerte que las reglas no captaron.

Escribí cada texto en una sola línea, sin saltos de línea adentro. Sé breve:
el reclutador lee esto de un vistazo, al lado de otros veinte candidatos.

NO inventes datos que no estén en el perfil. Si falta información para juzgar,
decilo en los riesgos y mantené el ajuste cerca de 0. Un candidato con datos
incompletos no es un mal candidato: es uno del que sabemos poco."""


def _contexto(vacante: Vacante, perfil: Perfil, score: Score) -> str:
    indispensables = [c.etiqueta for c in vacante.criterios if c.indispensable]
    incumplidos = [r.etiqueta for r in score.knockouts]
    campos = {
        nombre: datos["valor"]
        for nombre, datos in perfil_a_dict(perfil).items()
        if datos["valor"] not in (None, "", [], {})
    }
    return json.dumps({
        "vacante": {
            "puesto": vacante.titulo,
            "municipio": vacante.municipio,
            "sueldo": [vacante.salario_min, vacante.salario_max],
            "indispensables": indispensables,
        },
        "candidato": campos,
        "puntaje_por_requisitos": score.valor,
        "cumple_indispensables": score.apto,
        "requisitos_que_no_cumple": incumplidos,
        "sin_verificar": [r.etiqueta for r in score.faltantes],
    }, ensure_ascii=False, indent=2, default=str)


def evaluar(vacante: Vacante, perfil: Perfil, score: Score,
            api_key: str | None = None) -> Evaluacion | None:
    """Evalúa a un candidato. Devuelve None si no hay IA disponible."""
    clave = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not clave:
        return None
    try:
        from anthropic import Anthropic

        cliente = Anthropic(api_key=clave)
        respuesta = cliente.messages.create(
            model=MODELO,
            max_tokens=2000,
            system=INSTRUCCIONES,
            messages=[{"role": "user", "content": _contexto(vacante, perfil, score)}],
        )
        crudo = "".join(b.text for b in respuesta.content if b.type == "text").strip()
        crudo = re.sub(r"^```[a-z]*\n|\n```$", "", crudo)
        return _desde_json(json.loads(crudo))
    except Exception as e:
        # Que la IA no responda no puede dejar sin calificar a nadie: el
        # puntaje por requisitos ya está y es el que manda. Pero el motivo se
        # registra: si falla siempre, hay que enterarse, no descubrirlo en la
        # presentación.
        logging.getLogger(__name__).warning("Evaluacion con IA fallida: %s: %s",
                                            type(e).__name__, e)
        return None


def _parsear(crudo: str) -> dict:
    """JSON tolerante.

    `strict=False` admite saltos de línea dentro de los strings, que es como
    escribe el modelo. Y si la respuesta llegó cortada, se rescata lo que haya:
    media evaluación le sirve más al reclutador que ninguna.
    """
    try:
        return json.loads(crudo, strict=False)
    except json.JSONDecodeError:
        pass

    rescatado: dict[str, Any] = {}
    for campo in ("nivel", "resumen", "veredicto"):
        if m := re.search(rf'"{campo}"\s*:\s*"(.*?)"\s*[,}}]', crudo, re.S):
            rescatado[campo] = " ".join(m.group(1).split()).strip()
    if m := re.search(r'"ajuste"\s*:\s*(-?\d+(?:\.\d+)?)', crudo):
        rescatado["ajuste"] = float(m.group(1))
    for campo in ("fortalezas", "riesgos"):
        if m := re.search(rf'"{campo}"\s*:\s*\[(.*?)\]', crudo, re.S):
            rescatado[campo] = [x.strip().strip('"') for x in
                                re.findall(r'"([^"]+)"', m.group(1))]
    if not rescatado:
        raise ValueError("la respuesta no trae ningun campo utilizable")
    rescatado["truncada"] = True
    return rescatado


def _desde_json(datos: dict[str, Any]) -> Evaluacion | None:
    if not isinstance(datos, dict):
        return None
    nivel = str(datos.get("nivel", "")).strip().lower()
    if nivel not in NIVELES:
        nivel = "apto"
    try:
        ajuste = float(datos.get("ajuste") or 0.0)
    except (TypeError, ValueError):
        ajuste = 0.0
    return Evaluacion(
        nivel=nivel,
        resumen=str(datos.get("resumen") or "").strip(),
        fortalezas=[str(x) for x in (datos.get("fortalezas") or [])][:4],
        riesgos=[str(x) for x in (datos.get("riesgos") or [])][:4],
        ajuste=max(-AJUSTE_MAXIMO, min(AJUSTE_MAXIMO, ajuste)),
        veredicto=str(datos.get("veredicto") or "").strip(),
    )


def score_final(score: Score, evaluacion: Evaluacion | None) -> float:
    """Aplica el ajuste SIN romper los knockouts.

    El tope se vuelve a aplicar después: un candidato con la licencia vencida
    puede quedar mejor ubicado entre los descartados, pero no cruza a los aptos
    por más que la IA lo vea bien. Esa línea la decide un hecho, no un criterio.
    """
    if evaluacion is None:
        return score.valor
    ajustado = score.valor + evaluacion.ajuste
    if score.knockouts:
        ajustado = min(ajustado, TOPE_CON_KNOCKOUT)
    return round(max(0.0, min(100.0, ajustado)), 1)
