"""Endpoints que las tres demos comparten: tablero, detalle, etapas y bandeja.

Lo unico que cambia entre demos es como entra el candidato. Todo lo que pasa
despues es esto.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core import servicio
from core.db import get_db
from core.modelos import PostulacionDB, VacanteDB
from core.pipeline import Etapa, MovimientoInvalido

router = APIRouter(prefix="/api")


class CambioEtapa(BaseModel):
    hacia: Etapa
    autor: str = "Reclutador"
    nota: str | None = None


def resumen(p: PostulacionDB) -> dict:
    return {
        "id": p.id,
        "nombre": p.candidato.nombre,
        "telefono": p.candidato.telefono,
        "email": p.candidato.email,
        "score": p.score,
        "apto": p.apto,
        "razones": p.razones,
        "alertas": p.alertas,
        "etapa": p.etapa,
        "sugerencia": p.sugerencia,
        "motivo_sugerencia": p.motivo_sugerencia,
        "origen": p.origen,
        "evaluacion_ia": p.evaluacion_ia,
        "score_final": p.score_final,
        "nivel_ia": (p.evaluacion_ia or {}).get("nivel"),
        "dudosos": [k for k, c in (p.perfil or {}).items()
                    if c.get("origen") == "cv" and (c.get("confianza") or 0) < 0.75],
    }


def buscar_vacante(db: Session, vacante_id: int) -> VacanteDB:
    fila = db.get(VacanteDB, vacante_id)
    if fila is None:
        raise HTTPException(404, "No existe esa vacante")
    return fila


def buscar_postulacion(db: Session, postulacion_id: int) -> PostulacionDB:
    fila = db.get(PostulacionDB, postulacion_id)
    if fila is None:
        raise HTTPException(404, "No existe esa postulacion")
    return fila


@router.get("/vacantes")
def listar_vacantes(db: Session = Depends(get_db)):
    return [
        {"id": v.id, "titulo": v.titulo, "municipio": v.municipio,
         "salario_min": v.salario_min, "salario_max": v.salario_max}
        for v in db.query(VacanteDB).all()
    ]


@router.get("/vacantes/{vacante_id}")
def ver_vacante(vacante_id: int, db: Session = Depends(get_db)):
    v = buscar_vacante(db, vacante_id)
    return {
        "id": v.id, "titulo": v.titulo, "municipio": v.municipio,
        "salario_min": v.salario_min, "salario_max": v.salario_max,
        "descripcion": v.descripcion,
        "indispensables": [c["etiqueta"] for c in v.criterios if c["indispensable"]],
        "deseables": [c["etiqueta"] for c in v.criterios if not c["indispensable"]],
    }


@router.get("/vacantes/{vacante_id}/tablero")
def ver_tablero(vacante_id: int, db: Session = Depends(get_db)):
    buscar_vacante(db, vacante_id)
    tab = servicio.tablero(db, vacante_id)
    return {
        "conteo": tab.conteo(),
        "columnas": [
            {"etapa": etapa.value, "etiqueta": etapa.etiqueta,
             "candidatos": [resumen(p) for p in filas]}
            for etapa, filas in tab.columnas.items()
        ],
    }


@router.get("/postulaciones/{postulacion_id}")
def ver_postulacion(postulacion_id: int, db: Session = Depends(get_db)):
    """El detalle SIEMPRE trae el desglose: ningun score se muestra sin su porque."""
    p = buscar_postulacion(db, postulacion_id)
    return {
        **resumen(p),
        "perfil": p.perfil,
        "desglose": p.desglose,
        "eventos": [
            {"desde": e.desde, "hacia": e.hacia, "autor": e.autor,
             "nota": e.nota, "momento": e.momento.isoformat()}
            for e in p.eventos
        ],
    }


@router.post("/postulaciones/{postulacion_id}/etapa")
def cambiar_etapa(postulacion_id: int, cambio: CambioEtapa,
                  db: Session = Depends(get_db)):
    p = buscar_postulacion(db, postulacion_id)
    try:
        servicio.cambiar_etapa(db, p, cambio.hacia, autor=cambio.autor, nota=cambio.nota)
    except MovimientoInvalido as e:
        raise HTTPException(409, str(e))
    return resumen(p)


@router.post("/vacantes/{vacante_id}/aplicar-sugerencias")
def aplicar_sugerencias(vacante_id: int, autor: str = "Reclutador",
                        db: Session = Depends(get_db)):
    """El boton "mover los N aptos". Lo aprieta una persona: el sistema propone,
    nunca mueve solo."""
    buscar_vacante(db, vacante_id)
    movidos = []
    pendientes = (db.query(PostulacionDB)
                  .filter(PostulacionDB.vacante_id == vacante_id,
                          PostulacionDB.etapa == Etapa.POSTULADO.value)
                  .all())
    for p in pendientes:
        destino = Etapa(p.sugerencia)
        if destino is Etapa.POSTULADO:
            continue
        try:
            servicio.cambiar_etapa(db, p, destino, autor=autor, nota=p.motivo_sugerencia)
            movidos.append({"id": p.id, "nombre": p.candidato.nombre,
                            "hacia": destino.value})
        except MovimientoInvalido:
            continue
    return {"movidos": len(movidos), "detalle": movidos}


@router.post("/vacantes/{vacante_id}/evaluar-ia")
def evaluar_con_ia(vacante_id: int, db: Session = Depends(get_db)):
    """Evalua con IA a TODOS los candidatos que falten.

    La IA no descarta a nadie: se evalua tambien a quienes no cumplen un
    indispensable, y su ajuste nunca los cruza al grupo de los aptos.
    """
    buscar_vacante(db, vacante_id)
    evaluadas = servicio.evaluar_pendientes(db, vacante_id)
    if not evaluadas:
        return {"evaluadas": 0, "detalle": [],
                "motivo": "No hay candidatos sin evaluar, o falta ANTHROPIC_API_KEY."}
    return {"evaluadas": len(evaluadas), "detalle": evaluadas}


@router.get("/vacantes/{vacante_id}/bandeja")
def ver_bandeja(vacante_id: int, db: Session = Depends(get_db)):
    """Los avisos NO se envian: se ven aca. En una demo, un mail a la direccion
    equivocada delante del cliente no se arregla."""
    buscar_vacante(db, vacante_id)
    return [
        {"id": m.id, "destinatario": m.destinatario, "asunto": m.asunto,
         "cuerpo": m.cuerpo, "etapa": m.etapa, "enviado": m.enviado,
         "momento": m.momento.isoformat()}
        for m in servicio.bandeja(db, vacante_id)
    ]
