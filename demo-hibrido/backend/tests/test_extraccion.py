"""La extraccion es lo unico del sistema que puede equivocarse en silencio.

Cada test de aca nace de un error real: el candidato que NO viaja y entraba como
apto, el historial que no se leia y le costaba puntos a todos por igual.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.extraccion import (extraer, extraer_heuristico,
                             perfil_desde_extraccion, texto_de_pdf)
from core.scoring import calcular
from core.seed.candidatos import por_id
from core.seed.cvs import cv_texto
from core.seed.vacante import vacante_operador_foraneo

CVS = Path(__file__).resolve().parent.parent / "cvs_prueba"


@pytest.fixture
def vacante():
    return vacante_operador_foraneo()


def _perfil_de(cid: str):
    return extraer_heuristico(cv_texto(por_id()[cid]))


@pytest.mark.parametrize("cid", list(por_id()))
def test_el_cv_da_el_mismo_score_que_el_formulario(cid, vacante):
    """Un candidato no puede valer distinto segun por donde entro. Es lo que
    permite mostrar las tres demos juntas sin quedar en offside."""
    esperado = calcular(vacante, por_id()[cid].perfil).valor
    obtenido = calcular(vacante, _perfil_de(cid)).valor
    assert abs(obtenido - esperado) <= 1.0, f"{cid}: {obtenido} vs {esperado}"


def test_el_que_no_viaja_no_pasa_como_apto(vacante):
    """El CV dice 'foraneos: no, solo rutas locales'. Una deteccion ingenua de
    la negacion lo leia como SI y lo metia entre los aptos."""
    perfil = _perfil_de("raul-eduardo-ibarra")
    assert perfil.disponibilidad_foranea.valor is False
    assert not calcular(vacante, perfil).apto


def test_distingue_licencia_federal_de_estatal():
    assert _perfil_de("jose-antonio-pena").licencias.valor == ["estatal_C"]
    assert "federal_E" in _perfil_de("ricardo-salinas-trevino").licencias.valor


def test_lee_el_historial_laboral():
    historial = _perfil_de("juan-carlos-martinez").historial.valor
    assert len(historial) == 6
    assert all(e.empresa and e.desde for e in historial)


def test_el_empleo_actual_queda_abierto():
    historial = _perfil_de("ricardo-salinas-trevino").historial.valor
    assert historial[-1].hasta is None


def test_detecta_la_licencia_vencida(vacante):
    perfil = _perfil_de("hector-ramirez-solis")
    score = calcular(vacante, perfil)
    assert not score.apto and "VENCIDA" in score.razones[0]


def test_lo_extraido_queda_marcado_como_dudoso():
    """El motor heuristico devuelve confianza media a proposito: en la demo
    hibrida eso pinta el campo en amarillo y pide confirmacion."""
    perfil = _perfil_de("ricardo-salinas-trevino")
    assert perfil.municipio.dudoso
    assert perfil.municipio.fragmento, "sin fragmento no se puede confirmar nada"


def test_el_nombre_y_el_mail_van_con_confianza_alta():
    perfil = _perfil_de("ricardo-salinas-trevino")
    assert not perfil.nombre.dudoso and not perfil.email.dudoso


def test_un_pdf_sin_texto_no_revienta():
    assert texto_de_pdf(b"no soy un pdf") == ""


def test_el_pdf_real_se_lee(vacante):
    pdf = CVS / "ricardo-salinas-trevino.pdf"
    if not pdf.exists():
        pytest.skip("los CVs de prueba se generan con python -m core.seed.cvs")
    perfil = extraer_heuristico(texto_de_pdf(pdf.read_bytes()))
    assert calcular(vacante, perfil).valor >= 95


def test_sin_api_key_usa_el_heuristico(monkeypatch):
    """Si la conexion se cae en plena presentacion, el sistema sigue extrayendo."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    _, motor = extraer(cv_texto(por_id()["ricardo-salinas-trevino"]))
    assert motor == "heuristico"


def test_una_respuesta_rota_del_modelo_no_tumba_la_carga():
    """Un modelo puede devolver una fecha invalida o un campo que no existe."""
    perfil = perfil_desde_extraccion({
        "nombre": {"valor": "Ana Lopez", "confianza": 0.9, "fragmento": "Ana Lopez"},
        "licencia_vence": {"valor": "32/13/2027", "confianza": 0.5, "fragmento": ""},
        "campo_inventado": {"valor": 1, "confianza": 1, "fragmento": ""},
        "anios_experiencia": "esto no es un dict",
    })
    assert perfil.nombre.valor == "Ana Lopez"
    assert perfil.licencia_vence.falta
    assert perfil.anios_experiencia.falta


def test_la_confianza_del_modelo_se_acota():
    perfil = perfil_desde_extraccion(
        {"nombre": {"valor": "X", "confianza": 7.5, "fragmento": ""}})
    assert perfil.nombre.confianza == 1.0


def test_texto_vacio_da_perfil_vacio():
    perfil = extraer_heuristico("   \n  ")
    assert all(c.falta for c in perfil.campos().values())
