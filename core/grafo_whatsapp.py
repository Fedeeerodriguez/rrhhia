"""El agente de WhatsApp como grafo de LangGraph.

Por qué un grafo y no un if largo: la conversación tiene estados con nombre y
transiciones explícitas, y así se ve el flujo de un vistazo, se le agrega un
paso sin tocar los demás, y se puede dibujar para explicárselo al cliente.

    ┌──────────┐   sin CV   ┌───────────┐
    │  saludo  │──────────▶│ preguntar │◀──┐
    └────┬─────┘            └─────┬─────┘   │ falta otro dato
         │ manda CV               │         │
    ┌────▼─────┐            ┌─────▼──────┐  │
    │ leer_cv  │───────────▶│ interpretar│──┘
    └──────────┘            └─────┬──────┘
                                  │ ya está todo
                            ┌─────▼─────┐   corrige
                            │  resumir  │◀──────────┐
                            └─────┬─────┘           │
                                  │ confirma        │
                            ┌─────▼─────┐           │
                            │  cerrar   │           │
                            └───────────┘───────────┘

**Los nodos son código determinista.** El modelo se usa en un solo lugar: para
entender una respuesta en lenguaje natural cuando los parsers de reglas no
alcanzan (`entender`). Qué preguntar, cuándo terminar y qué se da por bueno lo
decide el grafo. Un agente que decide todo con el modelo se pierde, repite
preguntas y da por buenos datos que nadie dijo.

El estado se serializa y vive en la tabla `conversaciones`, no en el proceso:
WhatsApp es asincrónico y la persona puede contestar tres horas después.
"""
from __future__ import annotations

import re
from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from core.agente_whatsapp import (CIERRE_OK, POR_CAMPO, Campo, Estado, Origen,
                                  Perfil, _campo_mencionado, _plano,
                                  _pregunta_de, _si_o_no, campos_que_faltan,
                                  entender, extraer, resumen, texto_de_pdf)


def _ultimo(_viejo, nuevo):
    """Los campos del estado se pisan con el valor nuevo de cada vuelta."""
    return nuevo


class EstadoConversacion(TypedDict, total=False):
    # Entrada
    texto: str
    archivo: bytes | None
    nombre_archivo: str
    # Estado que persiste entre mensajes
    etapa: str
    perfil: Any            # core.domain.Perfil
    omitidos: list[str]
    # Salida
    mensajes: Annotated[list[str], _ultimo]
    listo_para_postular: bool
    # Datos de la vacante, para redactar
    vacante: dict


# --- Nodos --------------------------------------------------------------------

def nodo_saludo(estado: EstadoConversacion) -> dict:
    v = estado["vacante"]
    saludo = (
        f"¡Hola! Soy el asistente de {v['empresa']}. Estamos contratando "
        f"**{v['titulo']}** en {v['municipio']}, N.L., de ${v['salario_min']:,} "
        f"a ${v['salario_max']:,} al mes.\n\n"
        "Si quieres postularte, mándame tu CV en PDF y yo lleno todo por ti. "
        "Si no lo tienes a mano, no hay problema: te hago unas preguntas cortas."
    )
    return {"mensajes": [saludo], "etapa": Estado.ESPERANDO_CV.value}


def nodo_leer_cv(estado: EstadoConversacion) -> dict:
    perfil: Perfil = estado["perfil"]
    nombre = estado.get("nombre_archivo") or ""
    crudo = estado["archivo"] or b""
    texto = (texto_de_pdf(crudo) if nombre.lower().endswith(".pdf")
             else crudo.decode("utf-8", errors="ignore"))

    if not texto.strip():
        # El CV escaneado es lo más común en este rubro: es una foto y no tiene
        # texto. No es un error, es el caso normal.
        faltan = campos_que_faltan(perfil, estado.get("omitidos"))
        return {
            "mensajes": ["No pude leer ese archivo, parece una foto o un escaneo. "
                         "No te preocupes: te hago unas preguntas y listo.",
                         _pregunta_de(faltan[0])],
            "etapa": Estado.PREGUNTANDO.value,
        }

    extraido, _ = extraer(texto)
    for campo, dato in extraido.campos().items():
        if not dato.falta and getattr(perfil, campo).falta:
            setattr(perfil, campo, dato)

    leidos = sum(1 for c in perfil.campos().values() if not c.falta)
    faltan = campos_que_faltan(perfil, estado.get("omitidos"))
    mensajes = [f"¡Gracias! Ya leí tu CV y saqué {leidos} datos."]
    if not faltan:
        mensajes.append(resumen(perfil))
        return {"mensajes": mensajes, "perfil": perfil,
                "etapa": Estado.CONFIRMANDO.value}
    mensajes += [f"Me faltan {len(faltan)} cosas, te las pregunto rápido.",
                 _pregunta_de(faltan[0])]
    return {"mensajes": mensajes, "perfil": perfil, "etapa": Estado.PREGUNTANDO.value}


def nodo_arranque(estado: EstadoConversacion) -> dict:
    """Decide si empezar el cuestionario o insistir con el CV."""
    perfil: Perfil = estado["perfil"]
    # Un "hola" pelado recibe el saludo, no una pregunta salida de la nada.
    sin_cv = re.search(
        r"\bno\s+(tengo|cuento|traigo)\b|\bno\s+lo\s+tengo\b"
        r"|\bsin\s+(cv|curriculum)\b|\bpregunt|\bhazme\b|\bhaceme\b",
        _plano(estado.get("texto", "")))
    if not sin_cv:
        return nodo_saludo(estado)
    faltan = campos_que_faltan(perfil, estado.get("omitidos"))
    return {"mensajes": ["Va, te hago unas preguntas cortas.", _pregunta_de(faltan[0])],
            "etapa": Estado.PREGUNTANDO.value}


def nodo_interpretar(estado: EstadoConversacion) -> dict:
    """Toma la respuesta como contestación de la pregunta pendiente."""
    perfil: Perfil = estado["perfil"]
    omitidos = list(estado.get("omitidos") or [])
    texto = estado.get("texto", "")
    faltan = campos_que_faltan(perfil, omitidos)

    if not faltan:
        return {"mensajes": [resumen(perfil)], "etapa": Estado.CONFIRMANDO.value}

    campo = faltan[0]

    # "este mismo": el número de WhatsApp ya es el contacto.
    if campo == "telefono" and re.search(r"\b(este|el)\s+mismo\b|\beste\b", _plano(texto)):
        omitidos.append(campo)
        return _seguir(perfil, omitidos)

    valor = entender(campo, texto)
    if valor is None:
        if not POR_CAMPO[campo].obligatoria:
            # Lo opcional no se insiste: se marca omitido y se sigue. Que quede
            # registrado es lo que evita volver a preguntarlo eternamente.
            omitidos.append(campo)
            return _seguir(perfil, omitidos)
        return {"mensajes": ["Perdón, no te entendí.", _pregunta_de(campo)],
                "etapa": Estado.PREGUNTANDO.value, "omitidos": omitidos}

    setattr(perfil, campo, Campo(valor=valor, origen=Origen.REVISADO, confianza=1.0,
                                 fragmento=texto.strip()[:180]))
    return _seguir(perfil, omitidos)


def _seguir(perfil: Perfil, omitidos: list[str]) -> dict:
    restantes = campos_que_faltan(perfil, omitidos)
    if not restantes:
        return {"mensajes": [resumen(perfil)], "perfil": perfil,
                "omitidos": omitidos, "etapa": Estado.CONFIRMANDO.value}
    return {"mensajes": [_pregunta_de(restantes[0])], "perfil": perfil,
            "omitidos": omitidos, "etapa": Estado.PREGUNTANDO.value}


def nodo_confirmar(estado: EstadoConversacion) -> dict:
    perfil: Perfil = estado["perfil"]
    omitidos = list(estado.get("omitidos") or [])
    texto = estado.get("texto", "")
    decision = _si_o_no(texto)

    # Un "sí" cierra, aunque la frase nombre algún campo. Sin esto, "sí, todo
    # bien con mi licencia" se tomaba como una corrección y la conversación no
    # terminaba nunca: la persona confirma y el agente le vuelve a mostrar el
    # resumen, para siempre.
    corrige = re.search(
        r"\bno\b|\bcambia|\bcorrig|\bmal\b|\ben realidad\b|\bes\s|\bmejor\b|\bponle\b",
        _plano(texto))
    campo = _campo_mencionado(texto) if (decision is not True or corrige) else None

    # "no, la licencia vence en marzo" niega y corrige en el mismo mensaje: se
    # atiende la corrección, que es lo que la persona quiso decir.
    if campo:
        valor = entender(campo, texto)
        if valor is not None:
            setattr(perfil, campo, Campo(valor=valor, origen=Origen.REVISADO,
                                         confianza=1.0, fragmento=texto.strip()[:180]))
            if campo in omitidos:
                omitidos.remove(campo)
            return {"mensajes": ["Corregido.", resumen(perfil)], "perfil": perfil,
                    "omitidos": omitidos, "etapa": Estado.CONFIRMANDO.value}
        return {"mensajes": [_pregunta_de(campo)], "perfil": perfil,
                "omitidos": [o for o in omitidos if o != campo],
                "etapa": Estado.PREGUNTANDO.value}

    if decision is True:
        nombre = getattr(perfil.nombre, "valor", None) or "amigo"
        return {
            "mensajes": [CIERRE_OK.format(nombre=str(nombre).split()[0],
                                          puesto=estado["vacante"]["titulo"])],
            "etapa": Estado.CERRADA.value,
            "listo_para_postular": True,
        }
    if decision is False:
        return {"mensajes": ["¿Qué dato corrijo? Dime cuál y el valor correcto."],
                "etapa": Estado.CONFIRMANDO.value}
    return {"mensajes": ['No te entendí. Si todo está bien responde "sí"; '
                         'si no, dime qué dato cambio.'],
            "etapa": Estado.CONFIRMANDO.value}


def nodo_cerrada(estado: EstadoConversacion) -> dict:
    return {"mensajes": ["Tu postulación ya está registrada. Si quieres corregir "
                         "algo, dime qué dato cambio."],
            "etapa": Estado.CERRADA.value}


# --- Ruteo --------------------------------------------------------------------

Destino = Literal["saludo", "leer_cv", "arranque", "interpretar", "confirmar", "cerrada"]


def por_donde_entra(estado: EstadoConversacion) -> Destino:
    """Un solo lugar decide a qué nodo entra cada mensaje."""
    etapa = estado.get("etapa") or Estado.INICIO.value
    if estado.get("archivo") is not None:
        return "leer_cv"
    if etapa in (Estado.INICIO.value, Estado.ESPERANDO_CV.value):
        return "arranque" if (estado.get("texto") or "").strip() else "saludo"
    if etapa == Estado.CONFIRMANDO.value:
        return "confirmar"
    if etapa == Estado.CERRADA.value:
        return "cerrada"
    return "interpretar"


def construir_grafo():
    grafo = StateGraph(EstadoConversacion)
    grafo.add_node("saludo", nodo_saludo)
    grafo.add_node("leer_cv", nodo_leer_cv)
    grafo.add_node("arranque", nodo_arranque)
    grafo.add_node("interpretar", nodo_interpretar)
    grafo.add_node("confirmar", nodo_confirmar)
    grafo.add_node("cerrada", nodo_cerrada)

    grafo.add_conditional_edges(START, por_donde_entra, {
        "saludo": "saludo", "leer_cv": "leer_cv", "arranque": "arranque",
        "interpretar": "interpretar", "confirmar": "confirmar", "cerrada": "cerrada",
    })
    # Cada nodo produce la respuesta del turno y devuelve el control: el
    # siguiente paso lo dispara el próximo mensaje de la persona, no el grafo.
    for nodo in ("saludo", "leer_cv", "arranque", "interpretar", "confirmar", "cerrada"):
        grafo.add_edge(nodo, END)
    return grafo.compile()


GRAFO = construir_grafo()


def procesar(vacante: dict, etapa: str, perfil: Perfil, texto: str = "",
             archivo: bytes | None = None, nombre_archivo: str = "",
             omitidos: list[str] | None = None) -> dict:
    """Una vuelta de conversación. Entra un mensaje, sale la respuesta."""
    salida = GRAFO.invoke({
        "vacante": vacante,
        "etapa": etapa,
        "perfil": perfil,
        "omitidos": list(omitidos or []),
        "texto": texto or "",
        "archivo": archivo,
        "nombre_archivo": nombre_archivo,
        "mensajes": [],
        "listo_para_postular": False,
    })
    return {
        "mensajes": salida.get("mensajes", []),
        "etapa": salida.get("etapa", etapa),
        "perfil": salida.get("perfil", perfil),
        "omitidos": salida.get("omitidos", list(omitidos or [])),
        "listo_para_postular": bool(salida.get("listo_para_postular")),
        "pendientes": campos_que_faltan(salida.get("perfil", perfil),
                                        salida.get("omitidos", omitidos)),
    }


def dibujar() -> str:
    """El grafo en texto, para la documentación y para explicarlo en la demo."""
    try:
        return GRAFO.get_graph().draw_ascii()
    except Exception:
        return "\n".join(f"{n}" for n in GRAFO.get_graph().nodes)
