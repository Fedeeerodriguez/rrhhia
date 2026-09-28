"""El motor de scoring es el corazon de las tres demos. Si esto se rompe,
las tres mienten al mismo tiempo.
"""
from __future__ import annotations

import pytest

from core.criterios import Criterio
from core.domain import Campo, Origen
from core.scoring import TOPE_CON_KNOCKOUT, calcular, rankear
from core.seed.candidatos import CANDIDATOS, perfil, perfiles, por_id
from core.seed.vacante import vacante_operador_foraneo


@pytest.fixture
def vacante():
    return vacante_operador_foraneo()


@pytest.fixture
def ranking(vacante):
    return rankear(vacante, perfiles())


def test_ningun_descartado_supera_a_un_apto(ranking):
    aptos = [i for i, (_, s) in enumerate(ranking) if s.apto]
    descartados = [i for i, (_, s) in enumerate(ranking) if not s.apto]
    assert max(aptos) < min(descartados)


def test_los_buckets_esperados_se_respetan(ranking):
    idx = por_id()
    orden = [idx[cid].esperado for cid, _ in ranking]
    assert orden == sorted(orden, key=["top", "medio", "descartado"].index), orden


def test_knockout_topea_el_score(vacante):
    """Hector tiene 11 anios y licencia E: sin el tope estaria primero."""
    idx = por_id()
    hector = calcular(vacante, idx["hector-ramirez-solis"].perfil)
    assert not hector.apto
    assert hector.tope_aplicado
    assert hector.valor <= TOPE_CON_KNOCKOUT
    assert "VENCIDA" in hector.razones[0]


def test_descartados_no_empatan_todos_en_el_tope(ranking):
    """El que casi cumple tiene que quedar arriba del que no cumple nada."""
    valores = {cid: s.valor for cid, s in ranking if not s.apto}
    assert valores["hector-ramirez-solis"] > valores["luis-fernando-chapa"]
    assert len(set(valores.values())) > 1


def test_licencia_estatal_no_sustituye_a_la_federal(vacante):
    idx = por_id()
    score = calcular(vacante, idx["jose-antonio-pena"].perfil)
    assert not score.apto
    assert "estatal" in score.razones[0].lower()


def test_dato_faltante_no_se_reporta_como_incumplimiento(vacante):
    """Daniel no informa apto medico. No es lo mismo que tenerlo vencido:
    el reclutador tiene que poder pedirselo, no descartarlo a ciegas."""
    idx = por_id()
    score = calcular(vacante, idx["daniel-zuniga"].perfil)
    faltantes = {r.codigo for r in score.faltantes}
    assert "apto_medico" in faltantes
    assert "escolaridad" in faltantes
    assert any("No informa" in a for a in score.alertas)


def test_es_deterministico(vacante):
    p = por_id()["ricardo-salinas-trevino"].perfil
    assert calcular(vacante, p).valor == calcular(vacante, p).valor


def test_el_desglose_cubre_todos_los_criterios(vacante):
    score = calcular(vacante, por_id()["ricardo-salinas-trevino"].perfil)
    assert len(score.desglose()) == len(vacante.criterios)
    assert sum(d["peso"] for d in score.desglose()) == pytest.approx(100, abs=2)


def test_vacante_sin_criterios_no_revienta():
    from core.scoring import Vacante
    score = calcular(Vacante("X", "Monterrey", 1, 2), perfil(nombre="Ana"))
    assert score.valor == 0.0


def test_todos_los_seeds_tienen_nota_y_esperado():
    for c in CANDIDATOS:
        assert c.nota and c.esperado in {"top", "medio", "descartado"}


def test_campo_de_cv_con_baja_confianza_se_marca_dudoso():
    """Contrato de la demo hibrida: lo que la IA no vio claro va en amarillo."""
    seguro = Campo(valor=9, origen=Origen.CV, confianza=0.95, fragmento="9 anios")
    dudoso = Campo(valor=9, origen=Origen.CV, confianza=0.4, fragmento="desde 2017")
    manual = Campo.del_formulario(9)
    assert not seguro.dudoso and dudoso.dudoso and not manual.dudoso
    assert manual.confianza == 1.0


def test_criterio_con_evaluador_inexistente_falla_fuerte(vacante):
    vacante.criterios.append(Criterio("x", "X", "no_existe"))
    with pytest.raises(KeyError):
        calcular(vacante, por_id()["ricardo-salinas-trevino"].perfil)
