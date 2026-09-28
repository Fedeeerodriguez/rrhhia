"""Demo A de punta a punta: arrastrar CVs y ver el ranking."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.db import get_db
from core.modelos import Base
from core.seed.candidatos import CANDIDATOS, por_id
from core.seed.cvs import cv_texto
from core.seed.vacante import vacante_operador_foraneo
from core.servicio import guardar_vacante
from main import app


@pytest.fixture
def cliente(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path/'test.db'}",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Sesion = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def _db():
        db = Sesion()
        try:
            yield db
        finally:
            db.close()

    with Sesion() as db:
        guardar_vacante(db, vacante_operador_foraneo())

    app.dependency_overrides[get_db] = _db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _cv(cid: str):
    return (f"{cid}.txt", cv_texto(por_id()[cid]).encode("utf-8"), "text/plain")


def test_carga_masiva_rankea_de_mejor_a_peor(cliente):
    archivos = [("archivos", _cv(c.id)) for c in CANDIDATOS]
    r = cliente.post("/api/vacantes/1/cvs", files=archivos)
    assert r.status_code == 201

    datos = r.json()
    assert datos["total"] == 15 and datos["con_error"] == 0
    scores = [p["score"] for p in datos["procesados"]]
    assert scores == sorted(scores, reverse=True)
    assert datos["procesados"][0]["nombre"] == "Ricardo Salinas Treviño"


def test_los_aptos_quedan_arriba_de_los_descartados(cliente):
    archivos = [("archivos", _cv(c.id)) for c in CANDIDATOS]
    procesados = cliente.post("/api/vacantes/1/cvs", files=archivos).json()["procesados"]
    aptos = [i for i, p in enumerate(procesados) if p["apto"]]
    assert len(aptos) == 7 and max(aptos) < min(
        i for i, p in enumerate(procesados) if not p["apto"])


def test_informa_con_que_motor_extrajo(cliente):
    """El reclutador tiene que saber si lo leyo la IA o el motor de reglas."""
    p = cliente.post("/api/vacantes/1/cvs",
                     files=[("archivos", _cv("ricardo-salinas-trevino"))]).json()
    assert p["procesados"][0]["motor"] in ("heuristico", "claude")
    assert 0 <= p["procesados"][0]["completitud"] <= 100


def test_un_cv_ilegible_no_tumba_los_demas(cliente):
    """Un PDF escaneado no tiene texto. Los otros tienen que procesarse igual."""
    archivos = [
        ("archivos", _cv("ricardo-salinas-trevino")),
        ("archivos", ("escaneado.pdf", b"%PDF-1.4 sin capa de texto", "application/pdf")),
        ("archivos", _cv("jorge-luis-cavazos")),
    ]
    datos = cliente.post("/api/vacantes/1/cvs", files=archivos).json()
    assert len(datos["procesados"]) == 2
    assert datos["fallidos"][0]["archivo"] == "escaneado.pdf"
    assert "escaneado" in datos["fallidos"][0]["motivo"]


def test_un_archivo_gigante_se_rechaza_sin_procesar(cliente):
    grande = ("enorme.pdf", b"x" * (11 * 1024 * 1024), "application/pdf")
    datos = cliente.post("/api/vacantes/1/cvs", files=[("archivos", grande)]).json()
    assert datos["con_error"] == 1 and "10 MB" in datos["fallidos"][0]["motivo"]


def test_un_cv_sin_nombre_usa_el_del_archivo(cliente):
    """Preferimos "cv_juan_perez" a "Sin nombre": el reclutador lo reconoce."""
    archivo = ("cv_operador_nuevo.txt", b"Licencia Federal tipo B\n5 anios de experiencia\n",
               "text/plain")
    datos = cliente.post("/api/vacantes/1/cvs", files=[("archivos", archivo)]).json()
    assert datos["procesados"][0]["nombre"] == "cv_operador_nuevo"


def test_el_detalle_trae_el_fragmento_del_cv(cliente):
    """Es lo que sostiene el score: de donde salio cada dato."""
    pid = cliente.post("/api/vacantes/1/cvs",
                       files=[("archivos", _cv("ricardo-salinas-trevino"))]
                       ).json()["procesados"][0]["id"]
    perfil = cliente.get(f"/api/postulaciones/{pid}").json()["perfil"]
    assert perfil["licencias"]["fragmento"]
    assert perfil["licencias"]["origen"] == "cv"


def test_los_campos_dudosos_se_listan(cliente):
    pid = cliente.post("/api/vacantes/1/cvs",
                       files=[("archivos", _cv("ricardo-salinas-trevino"))]
                       ).json()["procesados"][0]["id"]
    assert cliente.get(f"/api/postulaciones/{pid}").json()["dudosos"]


def test_todo_entra_en_postulados(cliente):
    cliente.post("/api/vacantes/1/cvs", files=[("archivos", _cv("ricardo-salinas-trevino"))])
    conteo = cliente.get("/api/vacantes/1/tablero").json()["conteo"]
    assert conteo["postulado"] == 1 and conteo["filtrado"] == 0


def test_el_flujo_completo_del_tablero(cliente):
    archivos = [("archivos", _cv(c.id)) for c in CANDIDATOS]
    cliente.post("/api/vacantes/1/cvs", files=archivos)
    movidos = cliente.post("/api/vacantes/1/aplicar-sugerencias").json()["movidos"]
    assert movidos == 15
    conteo = cliente.get("/api/vacantes/1/tablero").json()["conteo"]
    assert conteo["filtrado"] == 7 and conteo["rechazado"] == 8
    # Un candidato dejo solo telefono, asi que no se le puede avisar.
    assert len(cliente.get("/api/vacantes/1/bandeja").json()) == 14


def test_vacante_inexistente_da_404(cliente):
    r = cliente.post("/api/vacantes/99/cvs",
                     files=[("archivos", _cv("ricardo-salinas-trevino"))])
    assert r.status_code == 404


def test_salud_dice_si_hay_ia(cliente):
    assert cliente.get("/api/salud").json()["demo"] == "cv"
