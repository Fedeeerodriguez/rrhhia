"""Pega el agente de WhatsApp con la base y con el pipeline.

Recibe un mensaje entrante, recupera la conversación de ese número, deja que el
agente decida qué responder, guarda todo y —cuando la conversación llega a
buen puerto— crea la postulación como cualquier otro canal.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from core import servicio
from core.agente_whatsapp import Agente, Estado
from core.domain import Campo
from core.modelos import ConversacionDB, VacanteDB
from core.serializacion import perfil_a_dict, perfil_desde_dict


def agente_de(vacante: VacanteDB) -> Agente:
    return Agente(
        vacante_titulo=vacante.titulo,
        municipio=vacante.municipio,
        salario_min=vacante.salario_min,
        salario_max=vacante.salario_max,
        empresa=servicio.EMPRESA,
    )


def conversacion_de(db: Session, wa_id: str, vacante: VacanteDB) -> ConversacionDB:
    fila = (db.query(ConversacionDB)
            .filter(ConversacionDB.wa_id == wa_id)
            .one_or_none())
    if fila is None:
        fila = ConversacionDB(wa_id=wa_id, vacante_id=vacante.id,
                              estado=Estado.INICIO.value, perfil={}, historial=[],
                              omitidos=[])
        db.add(fila)
        db.commit()
    return fila


def _anotar(fila: ConversacionDB, quien: str, texto: str) -> None:
    # JSON mutable: SQLAlchemy no detecta el append sin reasignar la lista.
    fila.historial = list(fila.historial or []) + [{
        "quien": quien, "texto": texto, "momento": datetime.now().isoformat(),
    }]


def recibir(db: Session, vacante: VacanteDB, wa_id: str, texto: str = "",
            archivo: bytes | None = None, nombre_archivo: str = "") -> dict:
    """Procesa un mensaje entrante y devuelve lo que hay que contestar."""
    fila = conversacion_de(db, wa_id, vacante)
    agente = agente_de(vacante)
    perfil = perfil_desde_dict(fila.perfil)

    if texto.strip():
        _anotar(fila, "candidato", texto.strip())
    if archivo is not None:
        _anotar(fila, "candidato", f"[envió {nombre_archivo or 'un archivo'}]")

    respuesta = agente.procesar(
        Estado(fila.estado), perfil, texto=texto,
        archivo=archivo, nombre_archivo=nombre_archivo,
        omitidos=list(fila.omitidos or []),
    )

    fila.perfil = perfil_a_dict(respuesta.perfil)
    fila.estado = respuesta.estado.value
    fila.omitidos = list(respuesta.omitidos)
    for mensaje in respuesta.mensajes:
        _anotar(fila, "agente", mensaje)

    # La postulación se crea una sola vez, cuando la persona confirma.
    if respuesta.listo_para_postular and fila.postulacion_id is None:
        if respuesta.perfil.telefono.falta:
            # El número de WhatsApp ES el contacto: no hace falta pedirlo.
            respuesta.perfil.telefono = Campo.del_formulario(wa_id)
            fila.perfil = perfil_a_dict(respuesta.perfil)
        postulacion = servicio.postular(db, vacante, respuesta.perfil, origen="whatsapp")
        fila.postulacion_id = postulacion.id

    db.commit()
    return {
        "wa_id": wa_id,
        "estado": fila.estado,
        "mensajes": respuesta.mensajes,
        "pendientes": respuesta.pendientes,
        "postulacion_id": fila.postulacion_id,
    }


def historial(db: Session, wa_id: str) -> list[dict]:
    fila = (db.query(ConversacionDB)
            .filter(ConversacionDB.wa_id == wa_id)
            .one_or_none())
    return list(fila.historial or []) if fila else []


def conversaciones(db: Session, vacante_id: int) -> list[dict]:
    filas = (db.query(ConversacionDB)
             .filter(ConversacionDB.vacante_id == vacante_id)
             .order_by(ConversacionDB.actualizada.desc())
             .all())
    return [
        {
            "wa_id": f.wa_id,
            "estado": f.estado,
            "mensajes": len(f.historial or []),
            "postulacion_id": f.postulacion_id,
            "actualizada": f.actualizada.isoformat(),
            "nombre": (f.perfil or {}).get("nombre", {}).get("valor"),
        }
        for f in filas
    ]


def reiniciar(db: Session, wa_id: str) -> None:
    """Para la demo: volver a empezar la conversación de un número."""
    fila = (db.query(ConversacionDB)
            .filter(ConversacionDB.wa_id == wa_id)
            .one_or_none())
    if fila is not None:
        db.delete(fila)
        db.commit()
