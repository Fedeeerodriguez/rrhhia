"""Casos de uso. Es lo que las tres demos llaman: cambia la puerta de entrada,
no lo que pasa despues de que el perfil esta armado.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from core.criterios import Criterio
from core.evaluacion_ia import evaluar as evaluar_con_ia
from core.evaluacion_ia import score_final as calcular_score_final
from core.domain import Perfil
from core.mensajes import PLANTILLAS
from core.modelos import (CandidatoDB, EventoDB, MensajeDB, PostulacionDB,
                          VacanteDB)
from core.pipeline import Etapa, Tablero, mover, sugerencia
from core.scoring import Vacante, calcular
from core.serializacion import perfil_a_dict, perfil_desde_dict

EMPRESA = "Transportes del Norte"   # remitente de los avisos en la demo


# --- Vacantes -----------------------------------------------------------------

def guardar_vacante(db: Session, vacante: Vacante) -> VacanteDB:
    fila = VacanteDB(
        titulo=vacante.titulo,
        municipio=vacante.municipio,
        salario_min=vacante.salario_min,
        salario_max=vacante.salario_max,
        descripcion=vacante.descripcion,
        criterios=[
            {
                "codigo": c.codigo,
                "etiqueta": c.etiqueta,
                "evaluador": c.evaluador,
                "params": c.params,
                "peso": c.peso,
                "indispensable": c.indispensable,
            }
            for c in vacante.criterios
        ],
    )
    db.add(fila)
    db.commit()
    return fila


def a_dominio(fila: VacanteDB) -> Vacante:
    return Vacante(
        titulo=fila.titulo,
        municipio=fila.municipio,
        salario_min=fila.salario_min,
        salario_max=fila.salario_max,
        descripcion=fila.descripcion or "",
        criterios=[Criterio(**c) for c in (fila.criterios or [])],
    )


# --- Postulaciones ------------------------------------------------------------

def _texto(valor) -> str:
    """Las columnas de contacto son texto. Un valor con otra forma (un dict que
    devolvio el modelo, por ejemplo) se descarta en vez de tumbar el INSERT."""
    if valor is None or isinstance(valor, (dict, list)):
        return ""
    return str(valor).strip()


def postular(db: Session, vacante_db: VacanteDB, perfil: Perfil,
             origen: str = "formulario") -> PostulacionDB:
    """Califica y guarda. No mueve al candidato de columna: solo sugiere."""
    score = calcular(a_dominio(vacante_db), perfil)
    etapa_sugerida, motivo = sugerencia(score)

    candidato = CandidatoDB(
        nombre=_texto(perfil.nombre.valor) or "Sin nombre",
        telefono=_texto(perfil.telefono.valor),
        email=_texto(perfil.email.valor),
    )
    db.add(candidato)
    db.flush()

    postulacion = PostulacionDB(
        vacante_id=vacante_db.id,
        candidato_id=candidato.id,
        perfil=perfil_a_dict(perfil),
        score=score.valor,
        apto=score.apto,
        desglose=score.desglose(),
        razones=score.razones,
        alertas=score.alertas,
        etapa=Etapa.POSTULADO.value,
        sugerencia=etapa_sugerida.value,
        motivo_sugerencia=motivo,
        origen=origen,
    )
    db.add(postulacion)
    db.commit()
    return postulacion


def recalcular(db: Session, postulacion: PostulacionDB) -> PostulacionDB:
    """Si el reclutador corrige un dato (demo hibrida), el score se rehace sin
    volver a llamar a la IA: el perfil ya esta guardado con su trazabilidad."""
    perfil = perfil_desde_dict(postulacion.perfil)
    score = calcular(a_dominio(postulacion.vacante), perfil)
    etapa_sugerida, motivo = sugerencia(score)

    postulacion.score = score.valor
    postulacion.apto = score.apto
    postulacion.desglose = score.desglose()
    postulacion.razones = score.razones
    postulacion.alertas = score.alertas
    postulacion.sugerencia = etapa_sugerida.value
    postulacion.motivo_sugerencia = motivo
    db.commit()
    return postulacion


# --- Evaluacion con IA --------------------------------------------------------

def evaluar(db: Session, postulacion: PostulacionDB) -> PostulacionDB:
    """Agrega la lectura cualitativa. No toca `apto` ni mueve al candidato."""
    vacante = a_dominio(postulacion.vacante)
    perfil = perfil_desde_dict(postulacion.perfil)
    score = calcular(vacante, perfil)

    evaluacion = evaluar_con_ia(vacante, perfil, score)
    if evaluacion is None:
        return postulacion

    postulacion.evaluacion_ia = evaluacion.a_dict()
    postulacion.score_final = calcular_score_final(score, evaluacion)
    db.commit()
    return postulacion


def evaluar_pendientes(db: Session, vacante_id: int) -> list[dict]:
    """Evalua a TODOS los que falten, cumplan o no los indispensables.

    Nadie queda afuera de la evaluacion: la IA no descarta, muestra quienes son
    los mas aptos y quienes no.
    """
    pendientes = (db.query(PostulacionDB)
                  .filter(PostulacionDB.vacante_id == vacante_id,
                          PostulacionDB.evaluacion_ia.is_(None))
                  .all())
    evaluadas = []
    for fila in pendientes:
        antes = fila.score
        evaluar(db, fila)
        if fila.evaluacion_ia:
            evaluadas.append({
                "id": fila.id,
                "nombre": fila.candidato.nombre,
                "nivel": fila.evaluacion_ia["nivel"],
                "score": antes,
                "score_final": fila.score_final,
            })
    return evaluadas


# --- Tablero ------------------------------------------------------------------

def cambiar_etapa(db: Session, postulacion: PostulacionDB, hacia: Etapa,
                  autor: str, nota: str | None = None) -> PostulacionDB:
    """Mueve de columna y deja el aviso en la bandeja. Lo dispara una persona."""
    evento = mover(Etapa(postulacion.etapa), hacia, autor=autor, nota=nota)

    postulacion.etapa = hacia.value
    db.add(EventoDB(
        postulacion_id=postulacion.id,
        desde=evento.desde.value,
        hacia=evento.hacia.value,
        autor=evento.autor,
        nota=evento.nota,
        automatico=evento.automatico,
    ))

    plantilla = PLANTILLAS.get(hacia)
    destinatario = postulacion.candidato.email
    if plantilla and destinatario:
        asunto, cuerpo = plantilla.render(
            nombre=postulacion.candidato.nombre,
            puesto=postulacion.vacante.titulo,
            empresa=EMPRESA,
        )
        db.add(MensajeDB(
            postulacion_id=postulacion.id,
            destinatario=destinatario,
            asunto=asunto,
            cuerpo=cuerpo,
            etapa=hacia.value,
        ))

    db.commit()
    return postulacion


def tablero(db: Session, vacante_id: int) -> Tablero:
    filas = db.query(PostulacionDB).filter(PostulacionDB.vacante_id == vacante_id).all()
    return Tablero.armar(filas)


def bandeja(db: Session, vacante_id: int) -> list[MensajeDB]:
    return (db.query(MensajeDB)
            .join(PostulacionDB)
            .filter(PostulacionDB.vacante_id == vacante_id)
            .order_by(MensajeDB.momento.desc())
            .all())
