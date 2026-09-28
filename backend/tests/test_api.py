"""Demo C: el CV prellena, la persona confirma, el score se rehace."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.db import get_db
from core.modelos import Base
from core.seed.candidatos import por_id
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


def _subir(cliente, cid="ricardo-salinas-trevino"):
    archivo = (f"{cid}.txt", cv_texto(por_id()[cid]).encode("utf-8"), "text/plain")
    return cliente.post("/api/vacantes/1/prellenar", files={"archivo": archivo})


def _confirmacion(campos: dict, **cambios):
    """Arma el payload como lo manda el front: reenvia lo extraido y marca lo tocado."""
    payload = {
        nombre: {"valor": datos["valor"], "confianza": datos["confianza"],
                 "fragmento": datos["fragmento"], "corregido": False}
        for nombre, datos in campos.items()
    }
    for nombre, valor in cambios.items():
        payload[nombre] = {"valor": valor, "confianza": 1.0,
                           "fragmento": None, "corregido": True}
    return {"campos": payload}


def test_prellenar_no_guarda_nada_todavia(cliente):
    """Nada entra a la base hasta que una persona revisa."""
    assert _subir(cliente).status_code == 200
    assert cliente.get("/api/vacantes/1/tablero").json()["conteo"]["postulado"] == 0


def test_cada_campo_viene_con_su_estado(cliente):
    campos = _subir(cliente).json()["campos"]
    estados = {c["estado"] for c in campos.values()}
    assert estados <= {"seguro", "dudoso", "vacio"}
    assert "seguro" in estados and "dudoso" in estados


def test_lo_dudoso_trae_el_fragmento_del_cv(cliente):
    """Sin la evidencia al lado, confirmar un dato es adivinar."""
    campos = _subir(cliente).json()["campos"]
    dudosos = [c for c in campos.values() if c["estado"] == "dudoso"]
    assert dudosos and all(c["fragmento"] for c in dudosos)


def test_dice_que_hay_que_revisar(cliente):
    datos = _subir(cliente).json()
    assert datos["a_revisar"]
    assert all(datos["campos"][n]["estado"] != "seguro" for n in datos["a_revisar"])
    assert 0 <= datos["completitud"] <= 100


def test_un_pdf_escaneado_pide_el_formulario_a_mano(cliente):
    archivo = ("escaneado.pdf", b"%PDF-1.4 sin texto", "application/pdf")
    r = cliente.post("/api/vacantes/1/prellenar", files={"archivo": archivo})
    assert r.status_code == 422 and "mano" in r.json()["detail"]


def test_confirmar_califica_y_guarda(cliente):
    campos = _subir(cliente).json()["campos"]
    r = cliente.post("/api/vacantes/1/confirmar", json=_confirmacion(campos))
    assert r.status_code == 201
    detalle = cliente.get(f"/api/postulaciones/{r.json()['id']}").json()
    assert detalle["apto"] and detalle["score"] >= 95
    assert cliente.get("/api/vacantes/1/tablero").json()["conteo"]["postulado"] == 1


def test_al_candidato_no_se_le_devuelve_su_puntaje(cliente):
    """Es informacion del reclutador y no queremos discutirla por WhatsApp."""
    campos = _subir(cliente).json()["campos"]
    cuerpo = cliente.post("/api/vacantes/1/confirmar", json=_confirmacion(campos)).json()
    assert "score" not in cuerpo and "apto" not in cuerpo


def test_lo_confirmado_por_una_persona_deja_de_ser_dudoso(cliente):
    campos = _subir(cliente).json()["campos"]
    r = cliente.post("/api/vacantes/1/confirmar",
                     json=_confirmacion(campos, municipio="Apodaca"))
    assert r.json()["campos_corregidos"] == 1

    detalle = cliente.get(f"/api/postulaciones/{r.json()['id']}").json()
    assert detalle["perfil"]["municipio"]["origen"] == "revisado"
    assert detalle["perfil"]["municipio"]["confianza"] == 1.0
    assert "municipio" not in detalle["dudosos"]


def test_corregir_un_dato_cambia_el_score_al_instante(cliente):
    """El caso de la demo: la IA leyo mal los anios y el reclutador lo arregla."""
    campos = _subir(cliente, "ricardo-salinas-trevino").json()["campos"]
    pid = cliente.post("/api/vacantes/1/confirmar",
                       json=_confirmacion(campos, anios_experiencia=2)).json()["id"]
    antes = cliente.get(f"/api/postulaciones/{pid}").json()["score"]

    r = cliente.patch(f"/api/postulaciones/{pid}/campo",
                      json={"campo": "anios_experiencia", "valor": 9})
    assert r.status_code == 200
    assert r.json()["score_anterior"] == antes
    assert r.json()["score"] > antes


def test_corregir_puede_descalificar_a_alguien(cliente):
    """Tambien tiene que poder ir para abajo, si no el reclutador no confia."""
    campos = _subir(cliente).json()["campos"]
    pid = cliente.post("/api/vacantes/1/confirmar",
                       json=_confirmacion(campos)).json()["id"]
    r = cliente.patch(f"/api/postulaciones/{pid}/campo",
                      json={"campo": "disponibilidad_foranea", "valor": False})
    assert not r.json()["apto"] and r.json()["score"] < 45


def test_el_desglose_se_rehace_con_la_correccion(cliente):
    campos = _subir(cliente).json()["campos"]
    pid = cliente.post("/api/vacantes/1/confirmar",
                       json=_confirmacion(campos, escolaridad="primaria")).json()["id"]
    cliente.patch(f"/api/postulaciones/{pid}/campo",
                  json={"campo": "escolaridad", "valor": "secundaria"})
    desglose = cliente.get(f"/api/postulaciones/{pid}").json()["desglose"]
    fila = next(d for d in desglose if "Secundaria" in d["criterio"])
    assert fila["cumple"]


def test_un_campo_inexistente_se_rechaza(cliente):
    campos = _subir(cliente).json()["campos"]
    pid = cliente.post("/api/vacantes/1/confirmar",
                       json=_confirmacion(campos)).json()["id"]
    r = cliente.patch(f"/api/postulaciones/{pid}/campo",
                      json={"campo": "color_favorito", "valor": "azul"})
    assert r.status_code == 422


def test_una_fecha_invalida_se_rechaza(cliente):
    campos = _subir(cliente).json()["campos"]
    pid = cliente.post("/api/vacantes/1/confirmar",
                       json=_confirmacion(campos)).json()["id"]
    r = cliente.patch(f"/api/postulaciones/{pid}/campo",
                      json={"campo": "licencia_vence", "valor": "32/13/2027"})
    assert r.status_code == 422


def test_el_que_no_viaja_sigue_sin_pasar(cliente):
    campos = _subir(cliente, "raul-eduardo-ibarra").json()["campos"]
    pid = cliente.post("/api/vacantes/1/confirmar", json=_confirmacion(campos)).json()["id"]
    assert not cliente.get(f"/api/postulaciones/{pid}").json()["apto"]


def test_confirmar_con_el_formulario_casi_vacio(cliente):
    """El CV no se pudo leer y la persona escribe solo lo que sabe."""
    r = cliente.post("/api/vacantes/1/confirmar", json={"campos": {
        "nombre": {"valor": "Pedro Solis", "confianza": 1.0, "corregido": True},
        "telefono": {"valor": "81 5555 4444", "confianza": 1.0, "corregido": True},
    }})
    assert r.status_code == 201
    detalle = cliente.get(f"/api/postulaciones/{r.json()['id']}").json()
    assert not detalle["apto"] and detalle["alertas"]


def test_salud(cliente):
    assert cliente.get("/api/salud").json()["demo"] == "hibrido"
