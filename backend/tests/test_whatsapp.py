"""El agente de WhatsApp: una conversación tiene que terminar en una
postulación calificada, o volver a preguntar. Nunca inventar un dato.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.agente_whatsapp import Agente, Estado, entender, interpretar, resumen
from core.db import get_db
from core.domain import Perfil
from core.modelos import Base
from core.seed.candidatos import por_id
from core.seed.cvs import cv_texto
from core.seed.vacante import vacante_operador_foraneo
from core.servicio import guardar_vacante
from main import app

NUMERO = "+52 81 1234 5678"


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


def escribir(cliente, texto, wa_id=NUMERO):
    return cliente.post("/api/whatsapp/mensaje",
                        json={"wa_id": wa_id, "texto": texto}).json()


def mandar_cv(cliente, cid="ricardo-salinas-trevino", wa_id=NUMERO):
    archivo = (f"{cid}.txt", cv_texto(por_id()[cid]).encode("utf-8"), "text/plain")
    return cliente.post("/api/whatsapp/archivo",
                        data={"wa_id": wa_id, "vacante_id": 1},
                        files={"archivo": archivo}).json()


# --- Parsers ------------------------------------------------------------------

@pytest.mark.parametrize("texto,esperado", [
    ("15/03/2028", "2028-03-15"),
    ("se me vence el 15 de marzo del 2028", "2028-03-15"),
    ("marzo de 2028", "2028-03-01"),
    ("20-07-27", "2027-07-20"),
])
def test_entiende_fechas_habladas(texto, esperado):
    assert str(interpretar("licencia_vence", texto)) == esperado


def test_no_inventa_una_fecha_que_no_esta():
    """Preferimos volver a preguntar antes que un dato falso en el legajo."""
    assert interpretar("licencia_vence", "no me acuerdo la verdad") is None


@pytest.mark.parametrize("texto,esperado", [
    ("tengo la federal tipo E", ["federal_E"]),
    ("federal B", ["federal_B"]),
    ("la estatal tipo C de Nuevo León", ["estatal_C"]),
])
def test_distingue_federal_de_estatal(texto, esperado):
    assert interpretar("licencias", texto) == esperado


@pytest.mark.parametrize("texto,esperado", [
    ("sí claro", True), ("simón", None), ("no, solo local", False),
    ("por supuesto", True), ("nunca", False),
])
def test_entiende_si_y_no(texto, esperado):
    assert interpretar("disponibilidad_foranea", texto) is esperado


def test_entiende_numeros_escritos():
    assert interpretar("anios_experiencia", "como nueve años") == 9
    assert interpretar("anios_experiencia", "llevo 12") == 12


def test_sin_api_key_no_llama_a_la_ia(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert entender("licencia_vence", "ni idea") is None


# --- La conversación ----------------------------------------------------------

def test_saluda_y_ofrece_las_dos_vias(cliente):
    r = escribir(cliente, "")
    texto = " ".join(r["mensajes"])
    assert "CV" in texto and "preguntas" in texto
    assert r["estado"] == Estado.ESPERANDO_CV.value


def test_el_cv_llena_todo_y_pasa_a_confirmar(cliente):
    r = mandar_cv(cliente)
    assert r["estado"] == Estado.CONFIRMANDO.value
    assert "leí tu CV" in r["mensajes"][0]
    assert not r["pendientes"]


def test_un_cv_incompleto_deja_preguntas(cliente):
    """Daniel no informa apto médico ni escolaridad: el agente los pide."""
    r = mandar_cv(cliente, "daniel-zuniga")
    assert r["estado"] == Estado.PREGUNTANDO.value
    assert r["pendientes"]


def test_una_foto_no_frena_la_postulacion(cliente):
    """El CV escaneado es lo más común: el agente pasa a preguntar."""
    r = cliente.post("/api/whatsapp/archivo", data={"wa_id": NUMERO, "vacante_id": 1},
                     files={"archivo": ("foto.pdf", b"%PDF-1.4 sin texto", "application/pdf")}).json()
    assert r["estado"] == Estado.PREGUNTANDO.value
    assert "preguntas" in " ".join(r["mensajes"])


def test_conversacion_completa_sin_cv_termina_en_postulacion(cliente):
    escribir(cliente, "hola, quiero el trabajo")
    escribir(cliente, "no tengo CV")
    respuestas = [
        "Ricardo Salinas Treviño",
        "federal tipo E",
        "se vence el 15 de marzo del 2028",
        "el apto médico hasta el 20/07/2027",
        "nueve años",
        "tractocamión y full",
        "sí, sin problema",
        "secundaria",
        "Apodaca",
        "21000",
        "sí, con hazmat",
        "este mismo",
    ]
    r = None
    for texto in respuestas:
        r = escribir(cliente, texto)
        if r["estado"] == Estado.CONFIRMANDO.value:
            break

    assert r["estado"] == Estado.CONFIRMANDO.value, r["mensajes"]
    assert "Revísalo completo" in r["mensajes"][-1]

    final = escribir(cliente, "sí, todo correcto")
    assert final["estado"] == Estado.CERRADA.value
    assert final["postulacion_id"]

    detalle = cliente.get(f"/api/postulaciones/{final['postulacion_id']}").json()
    assert detalle["apto"] and detalle["score"] >= 90
    assert detalle["origen"] == "whatsapp"


def test_el_candidato_entra_al_tablero(cliente):
    mandar_cv(cliente)
    escribir(cliente, "sí")
    conteo = cliente.get("/api/vacantes/1/tablero").json()["conteo"]
    assert conteo["postulado"] == 1


def test_el_numero_de_whatsapp_queda_como_contacto(cliente):
    mandar_cv(cliente, "jorge-luis-cavazos")
    r = escribir(cliente, "sí")
    detalle = cliente.get(f"/api/postulaciones/{r['postulacion_id']}").json()
    assert detalle["telefono"]


def test_no_entender_no_avanza_la_conversacion(cliente):
    escribir(cliente, "no tengo CV")
    primera = escribir(cliente, "Ricardo Salinas Treviño")["pendientes"]
    segunda = escribir(cliente, "qué onda")["pendientes"]
    # Sigue esperando lo mismo: no se saltea ni inventa.
    assert primera == segunda


def test_se_puede_corregir_en_la_confirmacion(cliente):
    mandar_cv(cliente)
    r = escribir(cliente, "no, el municipio es Guadalupe")
    assert "Corregido" in r["mensajes"][0]
    assert "Guadalupe" in r["mensajes"][-1]


def test_confirmar_dos_veces_no_duplica_la_postulacion(cliente):
    mandar_cv(cliente)
    primera = escribir(cliente, "sí")
    segunda = escribir(cliente, "sí")
    assert primera["postulacion_id"] == segunda["postulacion_id"]
    assert cliente.get("/api/vacantes/1/tablero").json()["conteo"]["postulado"] == 1


def test_la_conversacion_sobrevive_entre_mensajes(cliente):
    """WhatsApp es asincrónico: el estado vive en la base, no en memoria."""
    escribir(cliente, "no tengo CV")
    escribir(cliente, "Ricardo Salinas Treviño")
    historial = cliente.get(f"/api/whatsapp/{NUMERO}/historial").json()
    assert len(historial) >= 4
    assert {h["quien"] for h in historial} == {"candidato", "agente"}


def test_dos_numeros_no_se_mezclan(cliente):
    escribir(cliente, "no tengo CV", wa_id="+52 81 1111 1111")
    escribir(cliente, "Juan Pérez", wa_id="+52 81 1111 1111")
    otro = escribir(cliente, "hola", wa_id="+52 81 2222 2222")
    assert otro["estado"] == Estado.ESPERANDO_CV.value
    assert len(cliente.get("/api/whatsapp/conversaciones").json()) == 2


def test_el_reclutador_ve_las_conversaciones(cliente):
    mandar_cv(cliente)
    fila = cliente.get("/api/whatsapp/conversaciones").json()[0]
    assert fila["wa_id"] == NUMERO and fila["nombre"]


def test_se_puede_reiniciar_para_repetir_la_demo(cliente):
    mandar_cv(cliente)
    assert cliente.delete(f"/api/whatsapp/{NUMERO}").status_code == 204
    assert escribir(cliente, "")["estado"] == Estado.ESPERANDO_CV.value


# --- Webhook ------------------------------------------------------------------

@pytest.mark.parametrize("cuerpo", [
    {"message": {"from": "+5218112223333", "text": {"body": "hola"}}},
    {"messages": [{"from": "+5218112223333", "text": "hola"}]},
    {"waId": "+5218112223333", "text": "hola"},
])
def test_el_webhook_acepta_las_formas_de_los_proveedores(cliente, cuerpo):
    r = cliente.post("/api/whatsapp/webhook", json=cuerpo)
    assert r.status_code == 200 and r.json()["ok"]


def test_el_webhook_nunca_devuelve_error(cliente):
    """Si devolvemos 500 el proveedor reintenta y el candidato recibe todo
    duplicado. Mejor 200 con el motivo adentro."""
    r = cliente.post("/api/whatsapp/webhook", json={"cualquier": "cosa"})
    assert r.status_code == 200 and not r.json()["ok"]


# --- Piezas sueltas -----------------------------------------------------------

def test_el_resumen_muestra_tambien_lo_que_falta():
    """Un resumen que solo muestra lo que tenemos deja que alguien confirme un
    legajo a medias sin enterarse."""
    agente = Agente("Operador", "Apodaca", 18000, 23000)
    texto = resumen(Perfil())
    assert "Nombre completo: — (sin dato)" in texto
    assert "Teléfono: — (sin dato)" in texto
    assert agente.saludo()


def test_el_resumen_no_pide_el_telefono_si_es_el_de_este_chat():
    texto = resumen(Perfil(), omitidos=["telefono"])
    assert "Teléfono: el número de este chat" in texto


# --- Blindaje: nada entra al perfil con la forma equivocada -------------------

@pytest.mark.parametrize("valor", [
    {"telefono": None},              # el modelo envolvió la respuesta
    {"a": 1, "b": 2},                # dict que no dice nada
    "",                              # texto vacío
])
def test_una_respuesta_rara_del_modelo_no_llega_a_la_base(valor):
    from core.agente_whatsapp import _validar
    assert _validar("telefono", valor) is None


def test_el_tipo_equivocado_se_descarta():
    from core.agente_whatsapp import _validar
    assert _validar("anios_experiencia", "muchos") is None
    assert _validar("licencias", "federal_E") is None
    assert _validar("licencia_vence", "32/13/2027") is None


def test_el_modelo_puede_envolver_el_valor_y_se_desenvuelve():
    from core.agente_whatsapp import _validar
    assert _validar("telefono", {"telefono": "81 1234 5678"}) == "81 1234 5678"


def test_este_mismo_numero_no_pide_el_telefono(cliente):
    """El número de WhatsApp ya es el contacto."""
    escribir(cliente, "no tengo CV")
    for texto in ["Ana Ruiz", "federal B", "15/03/2028", "20/07/2027", "5",
                  "torton", "sí", "secundaria", "Apodaca", "19000", "no",
                  "este mismo"]:
        r = escribir(cliente, texto)
        if r["estado"] == Estado.CONFIRMANDO.value:
            break
    assert r["estado"] == Estado.CONFIRMANDO.value
    final = escribir(cliente, "sí")
    detalle = cliente.get(f"/api/postulaciones/{final['postulacion_id']}").json()
    assert detalle["telefono"] == NUMERO


# --- El grafo -----------------------------------------------------------------

VACANTE = {"titulo": "Operador de Tractocamión Foráneo", "municipio": "Apodaca",
           "salario_min": 18000, "salario_max": 23000, "empresa": "Transportes del Norte"}


def test_el_grafo_tiene_los_nodos_esperados():
    from core.grafo_whatsapp import GRAFO
    nodos = set(GRAFO.get_graph().nodes)
    assert {"saludo", "leer_cv", "arranque", "interpretar", "confirmar", "cerrada"} <= nodos


@pytest.mark.parametrize("etapa,texto,archivo,esperado", [
    ("inicio", "", None, "saludo"),
    ("inicio", "hola", None, "arranque"),
    ("esperando_cv", "no tengo", None, "arranque"),
    ("preguntando", "federal B", None, "interpretar"),
    ("confirmando", "sí", None, "confirmar"),
    ("cerrada", "hola", None, "cerrada"),
    ("preguntando", "", b"pdf", "leer_cv"),
])
def test_cada_mensaje_entra_por_el_nodo_correcto(etapa, texto, archivo, esperado):
    from core.grafo_whatsapp import por_donde_entra
    assert por_donde_entra({"etapa": etapa, "texto": texto, "archivo": archivo}) == esperado


def test_el_grafo_no_avanza_solo():
    """Cada nodo contesta y devuelve el control. El siguiente paso lo dispara
    la persona, no el grafo: si encadenara nodos, mandaría tres preguntas de
    una y nadie contesta eso."""
    from core.domain import Perfil
    from core.grafo_whatsapp import procesar
    r = procesar(VACANTE, "inicio", Perfil())
    assert len(r["mensajes"]) == 1 and r["etapa"] == "esperando_cv"


def test_el_grafo_conserva_lo_ya_contestado():
    from core.domain import Perfil
    from core.grafo_whatsapp import procesar
    r = procesar(VACANTE, "preguntando", Perfil(), texto="Ana Ruiz")
    assert r["perfil"].nombre.valor == "Ana Ruiz"
    r2 = procesar(VACANTE, r["etapa"], r["perfil"], texto="federal tipo B",
                  omitidos=r["omitidos"])
    assert r2["perfil"].nombre.valor == "Ana Ruiz"
    assert r2["perfil"].licencias.valor == ["federal_B"]


def test_un_dato_con_forma_rara_no_tumba_la_postulacion():
    """Defensa en profundidad: aunque algo raro llegue al perfil, la
    postulación se crea igual. Una conversación guardada hace días puede tener
    datos de una versión anterior del agente."""
    from core.domain import Campo, Perfil
    from core.servicio import _texto
    assert _texto({"telefono": None}) == ""
    assert _texto(["a"]) == ""
    assert _texto(None) == ""
    assert _texto("  81 1234 5678 ") == "81 1234 5678"

# --- Nombre completo: nada de respuestas a medias -----------------------------

@pytest.mark.parametrize("texto", [
    "Martín",                 # solo el nombre de pila
    "soy Martín",
    "no sé",
    "qué onda",
    "vivo en Monterrey",
    "el trabajo",
    "12345",
])
def test_no_acepta_un_nombre_a_medias(texto):
    """Un nombre sin apellido deja un legajo que el reclutador no puede ni
    buscar ni cotejar contra la licencia."""
    assert interpretar("nombre", texto) is None


@pytest.mark.parametrize("texto,esperado", [
    ("Ricardo Salinas Treviño", "Ricardo Salinas Treviño"),
    ("me llamo Ana Ruiz", "Ana Ruiz"),
    ("soy Omar de la Garza", "Omar de la Garza"),
    ("mi nombre es José Luis Garza Montemayor", "José Luis Garza Montemayor"),
])
def test_acepta_el_nombre_completo(texto, esperado):
    assert interpretar("nombre", texto) == esperado


def test_la_ia_tampoco_puede_meter_un_nombre_a_medias():
    """El filtro es el mismo venga de las reglas o del modelo."""
    from core.agente_whatsapp import _validar
    assert _validar("nombre", "Martín") is None
    assert _validar("nombre", "Martín Cepeda") == "Martín Cepeda"


def test_insiste_hasta_tener_el_nombre_completo(cliente):
    escribir(cliente, "no tengo CV")
    r = escribir(cliente, "Martín")
    assert "nombre" in r["pendientes"]
    assert "apellido" in " ".join(r["mensajes"])
    r = escribir(cliente, "Martín Cepeda Ruiz")
    assert "nombre" not in r["pendientes"]


# --- Repreguntar diciendo qué falta ------------------------------------------

def test_la_repregunta_dice_qué_faltó():
    """"Perdón, no te entendí" deja a la persona adivinando."""
    from core.agente_whatsapp import repregunta
    assert "federal" in " ".join(repregunta("licencias", "la de manejar"))
    assert "mes y el año" in " ".join(repregunta("licencia_vence", "ya casi"))


def test_una_evasiva_no_se_trata_como_un_malentendido():
    """La persona entendió la pregunta; lo que no tiene es el dato a mano."""
    from core.agente_whatsapp import repregunta
    texto = " ".join(repregunta("licencia_vence", "no me acuerdo"))
    assert "no lo puedo dejar en blanco" in texto

# --- Memoria de sesion: 30 minutos desde el ultimo mensaje --------------------

def test_dentro_de_la_media_hora_el_agente_se_acuerda(cliente):
    escribir(cliente, "no tengo CV")
    escribir(cliente, "Ana Ruiz Garcia")
    r = escribir(cliente, "federal tipo B")
    # No volvio a preguntar el nombre: lo tiene de los mensajes anteriores.
    assert "nombre" not in r["pendientes"]


def test_pasada_la_media_hora_empieza_de_cero(cliente):
    """Sin este corte, el tercero que prueba la demo cae en la mitad de la
    conversacion del segundo: contesta una pregunta que nunca vio."""
    from datetime import datetime, timedelta

    from core.db import get_db
    from core.modelos import ConversacionDB
    from main import app

    escribir(cliente, "no tengo CV")
    escribir(cliente, "Ana Ruiz Garcia")

    db = next(app.dependency_overrides[get_db]())
    fila = db.query(ConversacionDB).filter(ConversacionDB.wa_id == NUMERO).one()
    fila.actualizada = datetime.now() - timedelta(minutes=31)
    db.commit()

    r = escribir(cliente, "hola")
    assert r["estado"] == Estado.ESPERANDO_CV.value
    assert "asistente" in " ".join(r["mensajes"])
    assert len(cliente.get(f"/api/whatsapp/{NUMERO}/historial").json()) == 2


def test_la_postulacion_ya_hecha_no_se_borra_con_la_memoria(cliente):
    """Olvidar la charla no es olvidar al candidato: si llego a confirmar, su
    legajo ya esta en el tablero."""
    from datetime import datetime, timedelta

    from core.db import get_db
    from core.modelos import ConversacionDB
    from main import app

    mandar_cv(cliente)
    escribir(cliente, "si")
    antes = cliente.get("/api/vacantes/1/tablero").json()["conteo"]["postulado"]

    db = next(app.dependency_overrides[get_db]())
    fila = db.query(ConversacionDB).filter(ConversacionDB.wa_id == NUMERO).one()
    fila.actualizada = datetime.now() - timedelta(hours=2)
    db.commit()

    escribir(cliente, "hola")
    assert cliente.get("/api/vacantes/1/tablero").json()["conteo"]["postulado"] == antes


def test_la_ventana_se_corre_con_cada_mensaje():
    """30 minutos desde el ULTIMO mensaje, no desde que empezo la charla."""
    from datetime import datetime, timedelta

    from core.modelos import ConversacionDB
    from core.servicio_whatsapp import expirada

    ahora = datetime.now()
    vieja = ConversacionDB(creada=ahora - timedelta(hours=5),
                           actualizada=ahora - timedelta(minutes=5))
    assert not expirada(vieja, ahora)
    quieta = ConversacionDB(creada=ahora - timedelta(hours=5),
                            actualizada=ahora - timedelta(minutes=31))
    assert expirada(quieta, ahora)
