from __future__ import annotations

import pytest

from core.mensajes import PLANTILLAS, Bandeja
from core.pipeline import (UMBRAL_FILTRADO, Etapa, MovimientoInvalido, mover,
                           puede_mover, sugerencia)
from core.scoring import calcular
from core.seed.candidatos import por_id
from core.seed.vacante import vacante_operador_foraneo


@pytest.fixture
def vacante():
    return vacante_operador_foraneo()


def test_el_avance_normal_esta_permitido():
    assert puede_mover(Etapa.POSTULADO, Etapa.FILTRADO)
    assert puede_mover(Etapa.FILTRADO, Etapa.ENTREVISTA)
    assert puede_mover(Etapa.ENTREVISTA, Etapa.ACEPTADO)


def test_se_puede_rechazar_desde_cualquier_etapa_viva():
    for etapa in (Etapa.POSTULADO, Etapa.FILTRADO, Etapa.ENTREVISTA):
        assert puede_mover(etapa, Etapa.RECHAZADO)


def test_se_puede_volver_atras():
    """El reclutador se equivoca de columna al arrastrar; hay que perdonarlo."""
    assert puede_mover(Etapa.FILTRADO, Etapa.POSTULADO)
    assert puede_mover(Etapa.ENTREVISTA, Etapa.FILTRADO)
    assert puede_mover(Etapa.RECHAZADO, Etapa.POSTULADO)


def test_no_se_salta_de_postulado_a_aceptado():
    assert not puede_mover(Etapa.POSTULADO, Etapa.ACEPTADO)
    with pytest.raises(MovimientoInvalido):
        mover(Etapa.POSTULADO, Etapa.ACEPTADO, autor="rh")


def test_mover_a_la_misma_etapa_falla():
    with pytest.raises(MovimientoInvalido):
        mover(Etapa.FILTRADO, Etapa.FILTRADO, autor="rh")


def test_el_movimiento_deja_rastro():
    evento = mover(Etapa.POSTULADO, Etapa.FILTRADO, autor="laura", nota="buen perfil")
    assert (evento.desde, evento.hacia, evento.autor) == (Etapa.POSTULADO, Etapa.FILTRADO, "laura")
    assert evento.nota == "buen perfil" and not evento.automatico


def test_el_sistema_propone_rechazo_para_los_knockout(vacante):
    score = calcular(vacante, por_id()["hector-ramirez-solis"].perfil)
    etapa, motivo = sugerencia(score)
    assert etapa is Etapa.RECHAZADO and "Licencia" in motivo


def test_el_sistema_propone_filtrado_para_los_aptos(vacante):
    score = calcular(vacante, por_id()["ricardo-salinas-trevino"].perfil)
    etapa, _ = sugerencia(score)
    assert etapa is Etapa.FILTRADO and score.valor >= UMBRAL_FILTRADO


def test_la_sugerencia_nunca_mueve_sola(vacante):
    """sugerencia() devuelve una propuesta, no un EventoEtapa: mover es acto humano."""
    score = calcular(vacante, por_id()["ricardo-salinas-trevino"].perfil)
    etapa, motivo = sugerencia(score)
    assert isinstance(etapa, Etapa) and isinstance(motivo, str)


def test_cada_etapa_que_avisa_tiene_plantilla():
    for etapa in (Etapa.FILTRADO, Etapa.ENTREVISTA, Etapa.ACEPTADO, Etapa.RECHAZADO):
        assert etapa in PLANTILLAS


def test_el_rechazo_tambien_avisa():
    """Hoy el candidato que no pasa nunca recibe respuesta. Esto lo arregla."""
    bandeja = Bandeja()
    msg = bandeja.para_etapa(Etapa.RECHAZADO, "juan@mail.com",
                             nombre="Juan", puesto="Operador", empresa="Transportes X")
    assert msg and "Juan" in msg.cuerpo and "Transportes X" in msg.cuerpo


def test_volver_a_postulado_no_manda_mensaje():
    bandeja = Bandeja()
    assert bandeja.para_etapa(Etapa.POSTULADO, "juan@mail.com",
                              nombre="Juan", puesto="Operador", empresa="X") is None
    assert bandeja.mensajes == []


def test_sin_email_no_se_arma_mensaje():
    """Muchos conductores dejan solo el telefono. No debe reventar."""
    bandeja = Bandeja()
    assert bandeja.para_etapa(Etapa.FILTRADO, "", nombre="Juan",
                              puesto="Operador", empresa="X") is None


def test_plantilla_incompleta_falla_fuerte():
    with pytest.raises(KeyError):
        PLANTILLAS[Etapa.FILTRADO].render(nombre="Juan")


def test_los_mensajes_de_la_demo_no_se_envian():
    bandeja = Bandeja()
    bandeja.para_etapa(Etapa.FILTRADO, "a@b.com", nombre="A", puesto="P", empresa="E")
    assert len(bandeja.pendientes()) == 1
    assert all(not m.enviado for m in bandeja.mensajes)
