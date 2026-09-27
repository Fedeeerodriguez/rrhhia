"""La Demo B de punta a punta: postular, rankear, mover, avisar."""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from core.db import get_db
from core.modelos import Base
from core.seed.candidatos import CANDIDATOS
from core.serializacion import perfil_a_dict
from core.servicio import guardar_vacante
from core.seed.vacante import vacante_operador_foraneo

HOY = date.today()


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


def _form(**extra):
    base = {
        "nombre": "Candidato de Prueba",
        "telefono": "81 1111 2222",
        "email": "prueba@mail.com",
        "municipio": "Apodaca",
        "licencias": ["federal_E"],
        "licencia_vence": (HOY + timedelta(days=400)).isoformat(),
        "apto_medico_vence": (HOY + timedelta(days=200)).isoformat(),
        "anios_experiencia": 8,
        "unidades": ["tractocamion", "full"],
        "escolaridad": "secundaria",
        "disponibilidad_foranea": True,
        "salario_pretendido": 21000,
        "materiales_peligrosos": True,
    }
    base.update(extra)
    return base


def test_la_vacante_publica_muestra_sus_requisitos(cliente):
    r = cliente.get("/api/vacantes/1")
    assert r.status_code == 200
    datos = r.json()
    assert datos["titulo"].startswith("Operador")
    assert len(datos["indispensables"]) == 6 and len(datos["deseables"]) == 5


def test_postular_califica_en_el_mismo_request(cliente):
    r = cliente.post("/api/vacantes/1/postular", json=_form())
    assert r.status_code == 201
    detalle = cliente.get(f"/api/postulaciones/{r.json()['id']}").json()
    assert detalle["apto"] and detalle["score"] > 80


def test_al_candidato_no_se_le_devuelve_su_puntaje(cliente):
    """No es informacion suya y no queremos discutirla por WhatsApp."""
    r = cliente.post("/api/vacantes/1/postular", json=_form())
    assert "score" not in r.json()


def test_el_knockout_llega_hasta_la_api(cliente):
    vencida = _form(licencia_vence=(HOY - timedelta(days=30)).isoformat())
    r = cliente.post("/api/vacantes/1/postular", json=vencida)
    detalle = cliente.get(f"/api/postulaciones/{r.json()['id']}").json()
    assert not detalle["apto"]
    assert detalle["sugerencia"] == "rechazado"
    assert "VENCIDA" in detalle["razones"][0]


def test_el_detalle_nunca_viene_sin_desglose(cliente):
    r = cliente.post("/api/vacantes/1/postular", json=_form())
    detalle = cliente.get(f"/api/postulaciones/{r.json()['id']}").json()
    assert len(detalle["desglose"]) == 11
    assert all("detalle" in d and "criterio" in d for d in detalle["desglose"])


def test_el_tablero_ordena_por_score(cliente):
    cliente.post("/api/vacantes/1/postular", json=_form(nombre="Flojo", anios_experiencia=2,
                                                        licencias=["federal_B"], unidades=["torton"],
                                                        materiales_peligrosos=False))
    cliente.post("/api/vacantes/1/postular", json=_form(nombre="Fuerte"))
    columna = cliente.get("/api/vacantes/1/tablero").json()["columnas"][0]
    assert columna["etapa"] == "postulado"
    nombres = [c["nombre"] for c in columna["candidatos"]]
    assert nombres == ["Fuerte", "Flojo"]


def test_todos_entran_en_postulados_aunque_el_sistema_sugiera_otra_cosa(cliente):
    """El scoring propone; nadie se mueve solo."""
    cliente.post("/api/vacantes/1/postular", json=_form())
    tab = cliente.get("/api/vacantes/1/tablero").json()
    assert tab["conteo"]["postulado"] == 1 and tab["conteo"]["filtrado"] == 0


def test_aplicar_sugerencias_mueve_recien_cuando_lo_piden(cliente):
    cliente.post("/api/vacantes/1/postular", json=_form(nombre="Apto"))
    cliente.post("/api/vacantes/1/postular",
                 json=_form(nombre="Sin licencia", licencias=["estatal_C"]))
    r = cliente.post("/api/vacantes/1/aplicar-sugerencias").json()
    assert r["movidos"] == 2
    conteo = cliente.get("/api/vacantes/1/tablero").json()["conteo"]
    assert conteo["filtrado"] == 1 and conteo["rechazado"] == 1


def test_mover_de_columna_deja_rastro_y_avisa(cliente):
    pid = cliente.post("/api/vacantes/1/postular", json=_form()).json()["id"]
    r = cliente.post(f"/api/postulaciones/{pid}/etapa",
                     json={"hacia": "filtrado", "autor": "Laura"})
    assert r.status_code == 200 and r.json()["etapa"] == "filtrado"

    detalle = cliente.get(f"/api/postulaciones/{pid}").json()
    assert detalle["eventos"][0]["autor"] == "Laura"

    bandeja = cliente.get("/api/vacantes/1/bandeja").json()
    assert len(bandeja) == 1 and "avanzó" in bandeja[0]["asunto"]


def test_el_rechazo_tambien_avisa(cliente):
    pid = cliente.post("/api/vacantes/1/postular", json=_form()).json()["id"]
    cliente.post(f"/api/postulaciones/{pid}/etapa", json={"hacia": "rechazado"})
    bandeja = cliente.get("/api/vacantes/1/bandeja").json()
    assert bandeja[0]["etapa"] == "rechazado"


def test_los_mensajes_de_la_demo_no_se_envian(cliente):
    pid = cliente.post("/api/vacantes/1/postular", json=_form()).json()["id"]
    cliente.post(f"/api/postulaciones/{pid}/etapa", json={"hacia": "filtrado"})
    assert all(not m["enviado"] for m in cliente.get("/api/vacantes/1/bandeja").json())


def test_un_salto_invalido_de_columna_se_rechaza(cliente):
    pid = cliente.post("/api/vacantes/1/postular", json=_form()).json()["id"]
    r = cliente.post(f"/api/postulaciones/{pid}/etapa", json={"hacia": "aceptado"})
    assert r.status_code == 409


def test_sin_email_el_movimiento_igual_funciona(cliente):
    """Muchos conductores dejan solo el telefono."""
    pid = cliente.post("/api/vacantes/1/postular", json=_form(email="")).json()["id"]
    r = cliente.post(f"/api/postulaciones/{pid}/etapa", json={"hacia": "filtrado"})
    assert r.status_code == 200
    assert cliente.get("/api/vacantes/1/bandeja").json() == []


def test_campos_opcionales_vacios_no_revientan(cliente):
    """El que llena la mitad del formulario tiene que poder postularse igual."""
    r = cliente.post("/api/vacantes/1/postular",
                     json={"nombre": "Medio Datos", "telefono": "81 0000 0000"})
    assert r.status_code == 201
    detalle = cliente.get(f"/api/postulaciones/{r.json()['id']}").json()
    assert not detalle["apto"] and detalle["alertas"]


def test_vacante_inexistente_da_404(cliente):
    assert cliente.get("/api/vacantes/99").status_code == 404
    assert cliente.post("/api/vacantes/99/postular", json=_form()).status_code == 404


def test_el_perfil_sobrevive_al_viaje_a_la_base(cliente):
    """Lo que guardamos tiene que volver igual, con confianza y todo."""
    original = CANDIDATOS[0].perfil
    ida = perfil_a_dict(original)
    assert ida["licencia_vence"]["valor"] == original.licencia_vence.valor.isoformat()
    assert ida["historial"]["valor"][0]["empresa"]
    assert ida["nombre"]["confianza"] == 1.0
