"""Demo A -- CV first.

Una sola pantalla: el reclutador arrastra 10-15 CVs en PDF y el sistema los
extrae, califica y rankea. Si no hay ANTHROPIC_API_KEY, o si la IA no responde
en medio de la presentacion, cae al motor heuristico y la carga no se detiene.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from core import servicio
from core.api_comun import buscar_vacante, resumen, router
from core.db import crear_tablas, get_db
from core.extraccion import extraer, texto_de_pdf
from core.modelos import VacanteDB
from core.seed.vacante import vacante_operador_foraneo

MAX_BYTES = 10 * 1024 * 1024


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


app = FastAPI(title="RRHHIA -- Demo A (CV en PDF)", version="0.3.0",
              lifespan=ciclo_de_vida)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])
app.include_router(router)


@app.post("/api/vacantes/{vacante_id}/cvs", status_code=201)
async def cargar_cvs(vacante_id: int, archivos: list[UploadFile] = File(...),
                     db: Session = Depends(get_db)):
    """Carga masiva. Un CV ilegible no puede tumbar los otros catorce: cada uno
    se informa por separado con su motivo."""
    vacante = buscar_vacante(db, vacante_id)
    procesados, fallidos = [], []

    for archivo in archivos:
        contenido = await archivo.read()
        if len(contenido) > MAX_BYTES:
            fallidos.append({"archivo": archivo.filename,
                             "motivo": "Pesa mas de 10 MB"})
            continue

        texto = (texto_de_pdf(contenido) if (archivo.filename or "").lower().endswith(".pdf")
                 else contenido.decode("utf-8", errors="ignore"))
        if not texto.strip():
            # Pasa con los CVs escaneados: son una foto, no tienen texto.
            fallidos.append({"archivo": archivo.filename,
                             "motivo": "El PDF no tiene texto (parece escaneado)"})
            continue

        perfil, motor = extraer(texto)
        if perfil.nombre.falta:
            perfil.nombre.valor = (archivo.filename or "Sin nombre").rsplit(".", 1)[0]

        fila = servicio.postular(db, vacante, perfil, origen="cv")
        procesados.append({**resumen(fila), "archivo": archivo.filename,
                           "motor": motor,
                           "completitud": round(perfil.completitud * 100)})

    procesados.sort(key=lambda p: (p["apto"], p["score"]), reverse=True)
    return {"procesados": procesados, "fallidos": fallidos,
            "total": len(archivos), "con_error": len(fallidos)}


@app.get("/api/salud")
def salud():
    return {"ok": True, "demo": "cv",
            "ia": bool(os.getenv("ANTHROPIC_API_KEY"))}
