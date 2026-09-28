"""La segunda capa de evaluación.

Lo que estos tests protegen es una promesa que le hacemos al cliente: la IA
**no descarta a nadie**. Evalúa a todos y muestra quiénes son los más aptos,
pero la línea entre apto y no apto la sigue decidiendo un hecho verificable.
"""
from __future__ import annotations

import pytest

from core.evaluacion_ia import (AJUSTE_MAXIMO, NIVELES, Evaluacion, _desde_json,
                                evaluar, score_final)
from core.scoring import TOPE_CON_KNOCKOUT, calcular
from core.seed.candidatos import por_id
from core.seed.vacante import vacante_operador_foraneo


@pytest.fixture
def vacante():
    return vacante_operador_foraneo()


def _score(vacante, cid):
    return calcular(vacante, por_id()[cid].perfil)


# --- La regla que no se negocia ----------------------------------------------

def test_la_ia_no_puede_salvar_una_licencia_vencida(vacante):
    """Héctor tiene 11 años y licencia E, pero vencida. Aunque la IA lo vea
    excelente, no cruza al grupo de los aptos."""
    score = _score(vacante, "hector-ramirez-solis")
    brillante = Evaluacion(nivel="muy apto", resumen="Excelente perfil", ajuste=10)
    final = score_final(score, brillante)
    assert final <= TOPE_CON_KNOCKOUT
    assert not score.apto


def test_dentro_del_grupo_igual_se_ordena(vacante):
    """Lo que sí puede hacer: dejarlo mejor ubicado entre los descartados, para
    que el reclutador vea a quién llamar cuando renueve la licencia."""
    score = _score(vacante, "luis-fernando-chapa")
    con_ia = score_final(score, Evaluacion(nivel="con reservas", resumen="", ajuste=6))
    assert con_ia > score.valor
    assert con_ia <= TOPE_CON_KNOCKOUT


def test_un_apto_puede_subir_y_bajar(vacante):
    score = _score(vacante, "miguel-angel-rodriguez")
    arriba = score_final(score, Evaluacion(nivel="muy apto", resumen="", ajuste=8))
    abajo = score_final(score, Evaluacion(nivel="con reservas", resumen="", ajuste=-8))
    assert arriba > score.valor > abajo


def test_el_ajuste_esta_acotado():
    """Es un matiz sobre una medición objetiva, no una segunda opinión que la
    reemplace."""
    assert _desde_json({"nivel": "muy apto", "ajuste": 99}).ajuste == AJUSTE_MAXIMO
    assert _desde_json({"nivel": "poco apto", "ajuste": -99}).ajuste == -AJUSTE_MAXIMO


def test_el_score_nunca_se_va_de_rango(vacante):
    score = _score(vacante, "ricardo-salinas-trevino")   # ya está en 100
    assert score_final(score, Evaluacion(nivel="muy apto", resumen="", ajuste=10)) <= 100


def test_sin_evaluacion_manda_el_puntaje_por_requisitos(vacante):
    score = _score(vacante, "ricardo-salinas-trevino")
    assert score_final(score, None) == score.valor


# --- Robustez ----------------------------------------------------------------

def test_sin_api_key_no_hay_evaluacion_pero_nada_se_rompe(vacante, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    score = _score(vacante, "ricardo-salinas-trevino")
    assert evaluar(vacante, por_id()["ricardo-salinas-trevino"].perfil, score) is None


def test_un_nivel_inventado_se_normaliza():
    assert _desde_json({"nivel": "excelentísimo", "resumen": "x"}).nivel in NIVELES


def test_una_respuesta_rota_no_tumba_la_evaluacion():
    assert _desde_json({"ajuste": "mucho"}).ajuste == 0.0
    assert _desde_json([]) is None


def test_las_listas_se_acotan():
    """Un modelo verborrágico no puede llenar la pantalla del reclutador."""
    e = _desde_json({"nivel": "apto", "fortalezas": [f"f{i}" for i in range(20)],
                     "riesgos": [f"r{i}" for i in range(20)]})
    assert len(e.fortalezas) == 4 and len(e.riesgos) == 4


def test_la_evaluacion_se_serializa_para_la_base():
    e = Evaluacion(nivel="apto", resumen="ok", fortalezas=["a"], riesgos=["b"], ajuste=3)
    d = e.a_dict()
    assert d["nivel"] == "apto" and d["ajuste"] == 3 and d["modelo"]
