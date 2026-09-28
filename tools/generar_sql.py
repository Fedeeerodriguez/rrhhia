"""Genera `datos/semilla.sql`: la base ficticia de la demo, en SQL.

Por qué un .sql y no solo el seed en Python:

- Se puede leer y editar sin correr nada. Si el cliente quiere cambiar un
  nombre o un sueldo antes de la presentación, abre el archivo.
- Se carga en cualquier motor. Hoy SQLite dentro del proyecto; el día que esto
  vaya a Postgres o Supabase, el mismo archivo sirve de punto de partida.
- Queda versionado: la demo arranca siempre con el mismo estado, y si alguien
  la rompe probando, se restaura con un comando.

El escenario no es "15 candidatos recién llegados": es un proceso ya andando,
con gente en entrevista, alguien aceptado, rechazados con su motivo, mensajes
enviados y conversaciones de WhatsApp a medio camino. Un tablero donde todo
está en la primera columna no se parece a un día de trabajo.

    python -m tools.generar_sql
"""
from __future__ import annotations

import sqlite3
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

from core.db import crear_tablas
from core.domain import Campo, Empleo, Perfil
from core.modelos import ConversacionDB
from core.pipeline import Etapa
from core.seed.candidatos import CANDIDATOS, perfil as perfil_de
from core.seed.vacante import vacante_operador_foraneo
from core.serializacion import perfil_a_dict
from core.servicio import cambiar_etapa, guardar_vacante, postular

SALIDA = Path("datos/semilla.sql")
HOY = date.today()


def _d(dias: int) -> date:
    return HOY + timedelta(days=dias)


# Candidatos que entraron por los otros canales, para que el tablero muestre
# las cuatro vías de postulación conviviendo.
EXTRA = [
    dict(origen="whatsapp", etapa=Etapa.FILTRADO, datos=dict(
        nombre="José Luis Garza Montemayor", telefono="+52 81 1204 7789",
        email="jlgarza.operador@gmail.com", municipio="Apodaca",
        licencias=["federal_E"], licencia_vence=_d(760), apto_medico_vence=_d(510),
        anios_experiencia=14, unidades=["tractocamion", "full"],
        escolaridad="secundaria", disponibilidad_foranea=True,
        salario_pretendido=23000, materiales_peligrosos=True,
        historial=[Empleo("Fletes y Mudanzas del Golfo", "Operador de tortón",
                          date(2012, 6, 1), date(2019, 1, 1)),
                   Empleo("Transportes Monterrey del Norte", "Operador quinta rueda",
                          date(2019, 3, 1), None)])),
    dict(origen="whatsapp", etapa=Etapa.POSTULADO, datos=dict(
        nombre="Martín Cepeda Ruiz", telefono="+52 81 1877 4412",
        municipio="General Escobedo",
        licencias=["federal_B"], licencia_vence=_d(345), apto_medico_vence=_d(120),
        anios_experiencia=11, unidades=["torton", "rabon", "tractocamion"],
        escolaridad="secundaria", disponibilidad_foranea=True,
        salario_pretendido=19000, materiales_peligrosos=False,
        historial=[Empleo("Transportes El Roble", "Operador",
                          date(2015, 1, 1), date(2021, 6, 1)),
                   Empleo("Materiales Sánchez", "Chofer tortón",
                          date(2021, 7, 1), None)])),
    dict(origen="cv", etapa=Etapa.ENTREVISTA, datos=dict(
        nombre="Ramiro Tovar Elizondo", telefono="81 3344 9911",
        email="ramirotovar88@hotmail.com", municipio="Guadalupe",
        licencias=["federal_E"], licencia_vence=_d(275),
        apto_medico_vence=_d(95), anios_experiencia=9,
        unidades=["tractocamion", "full", "torton"], escolaridad="secundaria",
        disponibilidad_foranea=True, salario_pretendido=22500,
        materiales_peligrosos=False,
        historial=[Empleo("Grupo Logístico Regiomontano", "Operador full",
                          date(2017, 4, 1), date(2023, 11, 1)),
                   Empleo("Transportes Cuauhtémoc", "Operador tractocamión",
                          date(2023, 12, 1), None)])),
    dict(origen="formulario", etapa=Etapa.RECHAZADO, datos=dict(
        nombre="Efraín Lozano Vega", telefono="81 5566 2211",
        email="efrain.lozano@gmail.com", municipio="Monterrey",
        licencias=["estatal_C"], licencia_vence=_d(600),
        apto_medico_vence=_d(300), anios_experiencia=7,
        unidades=["torton"], escolaridad="secundaria",
        disponibilidad_foranea=True, salario_pretendido=18000,
        materiales_peligrosos=False,
        historial=[Empleo("Abarrotes del Norte", "Chofer repartidor",
                          date(2018, 2, 1), None)])),
    dict(origen="formulario", etapa=Etapa.ACEPTADO, datos=dict(
        nombre="Noé Bernal Quiroga", telefono="81 7788 3322",
        email="noe.bernal@outlook.com", municipio="Apodaca",
        licencias=["federal_E"], licencia_vence=_d(880), apto_medico_vence=_d(430),
        anios_experiencia=13, unidades=["tractocamion", "full"],
        escolaridad="preparatoria", disponibilidad_foranea=True,
        salario_pretendido=22000, materiales_peligrosos=True,
        historial=[Empleo("Autotransportes Bernal", "Operador full",
                          date(2013, 5, 1), date(2021, 9, 1)),
                   Empleo("Transportes del Bravo", "Operador",
                          date(2021, 10, 1), None)])),
]

# Dónde queda cada uno de los 15 originales, para que el tablero tenga vida.
DESTINOS = {
    "ricardo-salinas-trevino": Etapa.ENTREVISTA,
    "jorge-luis-cavazos": Etapa.ENTREVISTA,
    "marco-antonio-villarreal": Etapa.FILTRADO,
    "miguel-angel-rodriguez": Etapa.FILTRADO,
    "juan-carlos-martinez": Etapa.FILTRADO,
    "omar-de-la-garza": Etapa.POSTULADO,
    "alberto-nieto-cantu": Etapa.POSTULADO,
}

CONVERSACIONES = [
    # (número, estado, qué se ve en el chat)
    ("+52 81 1877 4412", "cerrada", [
        ("candidato", "buenas, vi la vacante del tractocamión"),
        ("agente", "¡Hola! Soy el asistente de Transportes del Norte…"),
        ("candidato", "no tengo CV a la mano"),
        ("agente", "Va, te hago unas preguntas cortas."),
        ("candidato", "Martín Cepeda Ruiz"),
        ("agente", "¿Qué licencia tienes vigente?"),
        ("candidato", "federal tipo B, vence en septiembre del 27"),
        ("agente", "Esto es lo que tengo. ¿Está bien?"),
        ("candidato", "sí, todo bien"),
        ("agente", "¡Listo, Martín! Ya quedó tu postulación."),
    ]),
    ("+52 81 1204 7789", "cerrada", [
        ("candidato", "[envió cv-formal-jose-luis-garza.pdf]"),
        ("agente", "¡Gracias! Ya leí tu CV y saqué 13 datos."),
        ("agente", "Esto es lo que tengo. ¿Está bien?"),
        ("candidato", "sí"),
        ("agente", "¡Listo, José! Ya quedó tu postulación."),
    ]),
    # A medio camino: sirve para mostrar en vivo que la conversación se retoma.
    ("+52 81 2299 6655", "preguntando", [
        ("candidato", "hola, me interesa el trabajo"),
        ("agente", "¡Hola! Soy el asistente de Transportes del Norte…"),
        ("candidato", "no tengo curriculum"),
        ("agente", "Va, te hago unas preguntas cortas."),
        ("candidato", "Gustavo Adolfo Rangel"),
        ("agente", "¿Qué licencia tienes vigente?"),
    ]),
]


def construir(db_path: str) -> None:
    from core.db import SessionLocal

    crear_tablas()
    with SessionLocal() as db:
        vacante = guardar_vacante(db, vacante_operador_foraneo())

        for candidato in CANDIDATOS:
            fila = postular(db, vacante, candidato.perfil, origen="formulario")
            destino = DESTINOS.get(candidato.id)
            if destino is None and not fila.apto:
                destino = Etapa.RECHAZADO
            if destino and destino is not Etapa.POSTULADO:
                _mover(db, fila, destino)

        for extra in EXTRA:
            perfil = _perfil(extra["datos"])
            fila = postular(db, vacante, perfil, origen=extra["origen"])
            if extra["etapa"] is not Etapa.POSTULADO:
                _mover(db, fila, extra["etapa"])

        # Evaluacion con IA de TODOS los candidatos, para que la demo abra
        # completa. Sin clave se saltea y la semilla queda igual de valida:
        # el boton "Evaluar con IA" la corre en vivo.
        import os
        if os.getenv("ANTHROPIC_API_KEY"):
            from core.servicio import evaluar_pendientes
            evaluadas = evaluar_pendientes(db, vacante.id)
            print(f"  {len(evaluadas)} candidatos evaluados con IA")
        else:
            print("  sin ANTHROPIC_API_KEY: la semilla va sin evaluaciones")

        for wa_id, estado, mensajes in CONVERSACIONES:
            db.add(ConversacionDB(
                wa_id=wa_id, vacante_id=vacante.id, estado=estado, perfil={},
                omitidos=[],
                historial=[{"quien": q, "texto": t,
                            "momento": datetime.now().isoformat()}
                           for q, t in mensajes],
            ))
        db.commit()


def _perfil(datos: dict) -> Perfil:
    perfil = Perfil()
    for clave, valor in datos.items():
        setattr(perfil, clave, Campo.del_formulario(valor))
    return perfil


def _mover(db, fila, destino: Etapa) -> None:
    """Camina las etapas intermedias: el historial tiene que ser creíble."""
    camino = {
        Etapa.FILTRADO: [Etapa.FILTRADO],
        Etapa.ENTREVISTA: [Etapa.FILTRADO, Etapa.ENTREVISTA],
        Etapa.ACEPTADO: [Etapa.FILTRADO, Etapa.ENTREVISTA, Etapa.ACEPTADO],
        Etapa.RECHAZADO: [Etapa.RECHAZADO],
    }[destino]
    for paso in camino:
        cambiar_etapa(db, fila, paso, autor="Laura Méndez",
                      nota=fila.motivo_sugerencia if paso is camino[0] else None)


def exportar(db_path: str, destino: Path = SALIDA) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    cuerpo = "\n".join(linea for linea in con.iterdump())
    con.close()

    cabecera = f"""-- Base ficticia de la demo RRHHIA
--
-- Generado por `python -m tools.generar_sql` el {HOY:%d/%m/%Y}.
-- No se edita a mano salvo para retocar un dato antes de una presentación:
-- cualquier cambio de fondo va en tools/generar_sql.py y se regenera.
--
-- Cargar:   python seed.py --sql
-- Reiniciar: python seed.py --sql --reset
--
-- Los candidatos son ficticios. La vacante y los criterios están calibrados
-- contra vacantes reales de Nuevo León (docs/investigacion-vacantes-nl.md).

"""
    destino.write_text(cabecera + cuerpo + "\n", encoding="utf-8")
    return destino


def main() -> None:
    import os

    temporal = Path(tempfile.gettempdir()) / "rrhhia_semilla.db"
    if temporal.exists():
        temporal.unlink()
    os.environ["DATABASE_URL"] = f"sqlite:///{temporal.as_posix()}"

    # El engine se arma al importar core.db, así que se recarga con la URL nueva.
    import importlib

    import core.db
    importlib.reload(core.db)

    construir(str(temporal))
    ruta = exportar(str(temporal))
    lineas = ruta.read_text(encoding="utf-8").count("\n")
    print(f"{ruta} — {lineas} líneas")


if __name__ == "__main__":
    main()
