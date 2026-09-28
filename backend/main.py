"""Demo C -- Hibrido.

El candidato sube su CV, la IA prellena el formulario y la persona confirma o
corrige lo dudoso. Cada campo viaja con su confianza y con el fragmento exacto
del CV de donde salio: sin esa evidencia, "corregir lo que la IA no detecto" es
adivinar.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import date
from typing import Any

from fastapi import Body, Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core import servicio, servicio_whatsapp
from core.api_comun import buscar_postulacion, buscar_vacante, resumen, router
from core.db import crear_tablas, get_db
from core.domain import Campo, Origen, Perfil
from core.extraccion import extraer, texto_de_pdf
from core.modelos import VacanteDB
from core.seed.vacante import vacante_operador_foraneo
from core.serializacion import decodificar, perfil_a_dict, perfil_desde_dict

UMBRAL_DUDOSO = 0.75
FECHAS = {"licencia_vence", "apto_medico_vence"}


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    if not os.getenv("RRHHIA_SIN_INIT"):
        crear_tablas()
        db = next(get_db())
        try:
            if db.query(VacanteDB).count() == 0:
                servicio.guardar_vacante(db, vacante_operador_foraneo())
        finally:
            db.close()
    yield


app = FastAPI(title="RRHHIA -- Demo C (hibrido)", version="0.3.0",
              lifespan=ciclo_de_vida)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])
app.include_router(router)


# --- Paso 1: el CV prellena ----------------------------------------------------

def _estado(campo: Campo) -> str:
    """Los tres colores de la pantalla. Vacio y dudoso son acciones distintas:
    uno hay que escribirlo, el otro solo confirmarlo."""
    if campo.falta:
        return "vacio"
    return "dudoso" if campo.confianza < UMBRAL_DUDOSO else "seguro"


def _serializable(valor: Any) -> Any:
    return valor.isoformat() if isinstance(valor, date) else valor


@app.post("/api/vacantes/{vacante_id}/prellenar")
async def prellenar(vacante_id: int, archivo: UploadFile = File(...),
                    db: Session = Depends(get_db)):
    """Extrae y devuelve el formulario prellenado. NO guarda todavia: nada entra
    a la base hasta que una persona revisa."""
    buscar_vacante(db, vacante_id)
    contenido = await archivo.read()
    texto = (texto_de_pdf(contenido) if (archivo.filename or "").lower().endswith(".pdf")
             else contenido.decode("utf-8", errors="ignore"))
    if not texto.strip():
        raise HTTPException(
            422, "El PDF no tiene texto (parece escaneado). Llena el formulario a mano.")

    perfil, motor = extraer(texto)
    campos = {
        nombre: {
            "valor": _serializable(campo.valor),
            "confianza": round(campo.confianza, 2),
            "fragmento": campo.fragmento,
            "estado": _estado(campo),
        }
        for nombre, campo in perfil.campos().items()
    }
    return {
        "motor": motor,
        "completitud": round(perfil.completitud * 100),
        "campos": campos,
        "a_revisar": [n for n, c in campos.items() if c["estado"] != "seguro"],
    }


# --- Paso 2: la persona confirma ----------------------------------------------

class CampoRevisado(BaseModel):
    valor: Any = None
    # Lo que devolvio la extraccion, que el front reenvia tal cual. Si el
    # usuario lo toco, `corregido` viene en True y el campo pasa a confianza 1.
    confianza: float = 0.0
    fragmento: str | None = None
    corregido: bool = False


class Confirmacion(BaseModel):
    campos: dict[str, CampoRevisado]


def _a_perfil(campos: dict[str, CampoRevisado]) -> Perfil:
    perfil = Perfil()
    for nombre, revisado in campos.items():
        if not hasattr(perfil, nombre):
            continue
        if revisado.valor in (None, "", [], {}):
            continue
        # El front manda JSON: las fechas vienen como texto y el historial como
        # lista de dicts. Sin decodificar, el scoring explota al comparar fechas.
        try:
            valor = decodificar(nombre, revisado.valor)
        except (ValueError, TypeError, KeyError):
            continue
        if valor is None:
            continue
        if revisado.corregido:
            # Confirmado por una persona: deja de ser dudoso para siempre.
            campo = Campo(valor=valor, origen=Origen.REVISADO, confianza=1.0,
                          fragmento=revisado.fragmento)
        else:
            campo = Campo(valor=valor, origen=Origen.CV,
                          confianza=min(max(revisado.confianza, 0.0), 1.0),
                          fragmento=revisado.fragmento)
        setattr(perfil, nombre, campo)
    return perfil


@app.post("/api/vacantes/{vacante_id}/confirmar", status_code=201)
def confirmar(vacante_id: int, datos: Confirmacion, db: Session = Depends(get_db)):
    """Recien aca se califica y se guarda."""
    vacante = buscar_vacante(db, vacante_id)
    perfil = _a_perfil(datos.campos)
    revisados = sum(1 for c in datos.campos.values() if c.corregido)
    fila = servicio.postular(db, vacante, perfil, origen="hibrido")
    # Acuse, no resultado: el puntaje no se le devuelve al candidato.
    return {
        "id": fila.id,
        "nombre": fila.candidato.nombre,
        "campos_corregidos": revisados,
        "mensaje": "Recibimos tu postulacion. Te contactamos pronto.",
    }


# --- Paso 3: corregir despues, sin volver a llamar a la IA ---------------------

class Correccion(BaseModel):
    campo: str
    valor: Any = None


@app.patch("/api/postulaciones/{postulacion_id}/campo")
def corregir_campo(postulacion_id: int, correccion: Correccion,
                   db: Session = Depends(get_db)):
    """El reclutador arregla un dato en el panel de detalle y el score se rehace
    al instante: el perfil ya esta guardado, no hace falta volver al CV ni a la IA."""
    p = buscar_postulacion(db, postulacion_id)
    perfil = perfil_desde_dict(p.perfil)
    if not hasattr(perfil, correccion.campo):
        raise HTTPException(422, f"No existe el campo {correccion.campo}")

    try:
        valor = decodificar(correccion.campo, correccion.valor)
    except (ValueError, TypeError, KeyError):
        raise HTTPException(422, f"Valor invalido para {correccion.campo}")

    anterior = p.score
    setattr(perfil, correccion.campo, Campo(
        valor=valor, origen=Origen.REVISADO, confianza=1.0,
        fragmento=getattr(perfil, correccion.campo).fragmento))
    p.perfil = perfil_a_dict(perfil)
    servicio.recalcular(db, p)
    return {**resumen(p), "score_anterior": anterior}


# --- WhatsApp -----------------------------------------------------------------
#
# El canal que mas sentido tiene en este rubro: el conductor ya esta en
# WhatsApp y no va a abrir un formulario web. El agente le pide el CV o le hace
# preguntas cortas, confirma los datos y crea la postulacion.

class MensajeEntrante(BaseModel):
    wa_id: str
    texto: str = ""


@app.post("/api/whatsapp/mensaje")
def mensaje_whatsapp(entrante: MensajeEntrante, vacante_id: int = 1,
                     db: Session = Depends(get_db)):
    """Mensaje de texto. Lo usa el simulador de la demo."""
    vacante = buscar_vacante(db, vacante_id)
    return servicio_whatsapp.recibir(db, vacante, entrante.wa_id, texto=entrante.texto)


@app.post("/api/whatsapp/archivo")
async def archivo_whatsapp(wa_id: str = Form(...), archivo: UploadFile = File(...),
                           vacante_id: int = Form(1), db: Session = Depends(get_db)):
    """El candidato manda su CV por WhatsApp."""
    vacante = buscar_vacante(db, vacante_id)
    contenido = await archivo.read()
    return servicio_whatsapp.recibir(db, vacante, wa_id, archivo=contenido,
                                     nombre_archivo=archivo.filename or "")


@app.post("/api/whatsapp/webhook")
async def webhook_whatsapp(cuerpo: dict = Body(...), db: Session = Depends(get_db)):
    """Entrada real del proveedor (YCloud, WATI, Meta Cloud API).

    Cada proveedor arma el JSON distinto, asi que se leen las formas mas comunes
    en vez de atarse a una. Siempre responde 200: si devolvemos error, el
    proveedor reintenta y el candidato recibe todo duplicado.
    """
    try:
        mensaje = (cuerpo.get("message") or cuerpo.get("messages") or cuerpo)
        if isinstance(mensaje, list):
            mensaje = mensaje[0] if mensaje else {}
        wa_id = str(mensaje.get("from") or mensaje.get("wa_id")
                    or mensaje.get("customerPhone") or cuerpo.get("waId") or "").strip()
        texto = (mensaje.get("text", {}).get("body")
                 if isinstance(mensaje.get("text"), dict) else mensaje.get("text")) or ""
        if not wa_id:
            return {"ok": False, "motivo": "el mensaje no trae numero"}

        vacante = buscar_vacante(db, 1)
        resultado = servicio_whatsapp.recibir(db, vacante, wa_id, texto=str(texto))
        # En produccion, aca se despachan los mensajes al proveedor. En la demo
        # quedan en el historial de la conversacion, como los mails.
        return {"ok": True, "respuestas": resultado["mensajes"]}
    except Exception as e:
        return {"ok": False, "motivo": str(e)}


@app.get("/api/whatsapp/conversaciones")
def listar_conversaciones(vacante_id: int = 1, db: Session = Depends(get_db)):
    buscar_vacante(db, vacante_id)
    return servicio_whatsapp.conversaciones(db, vacante_id)


@app.get("/api/whatsapp/{wa_id}/historial")
def historial_whatsapp(wa_id: str, db: Session = Depends(get_db)):
    return servicio_whatsapp.historial(db, wa_id)


@app.delete("/api/whatsapp/{wa_id}", status_code=204)
def reiniciar_whatsapp(wa_id: str, db: Session = Depends(get_db)):
    """Para poder repetir la demo con el mismo numero."""
    servicio_whatsapp.reiniciar(db, wa_id)


@app.get("/api/salud")
def salud():
    return {"ok": True, "demo": "hibrido", "ia": bool(os.getenv("ANTHROPIC_API_KEY"))}
