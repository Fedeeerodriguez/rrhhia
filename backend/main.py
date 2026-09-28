"""Demo B -- Formulario.

Dos pantallas: el link publico donde el candidato se postula desde el celular,
y el tablero del reclutador. Sin IA y sin costo de API: los datos ya vienen
estructurados, el score sale al instante.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import date

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core import servicio
from core.api_comun import buscar_vacante, router
from core.db import crear_tablas, get_db
from core.domain import Campo, Perfil
from core.modelos import VacanteDB

from core.seed.vacante import vacante_operador_foraneo

@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    # Los tests traen su propia base y ponen RRHHIA_SIN_INIT=1.
    if not os.getenv("RRHHIA_SIN_INIT"):
        crear_tablas()
        db = next(get_db())
        try:
            if db.query(VacanteDB).count() == 0:
                servicio.guardar_vacante(db, vacante_operador_foraneo())
        finally:
            db.close()
    yield


app = FastAPI(title="RRHHIA -- Demo B (formulario)", version="0.2.0",
              lifespan=ciclo_de_vida)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)
app.include_router(router)


# --- Esquemas -----------------------------------------------------------------

class Postulacion(BaseModel):
    """Los 8 campos del formulario publico. Pensado para llenarse en el celular:
    ocho campos, no treinta."""
    nombre: str = Field(min_length=2, max_length=200)
    telefono: str = Field(min_length=6, max_length=50)
    email: str = ""
    municipio: str = ""
    licencias: list[str] = []
    licencia_vence: date | None = None
    apto_medico_vence: date | None = None
    anios_experiencia: float | None = None
    unidades: list[str] = []
    escolaridad: str | None = None
    disponibilidad_foranea: bool | None = None
    salario_pretendido: int | None = None
    materiales_peligrosos: bool | None = None

    def a_perfil(self) -> Perfil:
        perfil = Perfil()
        for nombre, valor in self.model_dump().items():
            setattr(perfil, nombre, Campo.del_formulario(valor))
        return perfil


# --- Candidato ----------------------------------------------------------------

@app.post("/api/vacantes/{vacante_id}/postular", status_code=201)
def postular(vacante_id: int, datos: Postulacion, db: Session = Depends(get_db)):
    """El candidato se postula y el score sale en el mismo request."""
    vacante = buscar_vacante(db, vacante_id)
    fila = servicio.postular(db, vacante, datos.a_perfil(), origen="formulario")
    # Al candidato no se le devuelve su puntaje: no es informacion suya.
    return {"id": fila.id, "mensaje": "Recibimos tu postulacion. Te contactamos pronto."}


@app.get("/api/salud")
def salud():
    return {"ok": True, "demo": "formulario"}
