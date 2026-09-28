"""Deja la demo con un estado ya poblado.

La presentación no debería empezar con un tablero vacío ni depender de que 15
personas se postulen en vivo.

Dos fuentes, misma base:

    python seed.py              # carga datos/semilla.sql si existe
    python seed.py --python     # arma los datos con el seed de Python
    python seed.py --reset      # borra todo antes de cargar

El .sql es el estado "de demostración": un proceso ya andando, con gente en
entrevista, alguien aceptado, mensajes enviados y conversaciones de WhatsApp a
medio camino. El seed de Python es el mínimo: la vacante y los 15 candidatos
recién postulados.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from core.db import DATABASE_URL, SessionLocal, crear_tablas, engine
from core.modelos import Base, VacanteDB
from core.seed.candidatos import CANDIDATOS
from core.seed.vacante import vacante_operador_foraneo
from core.servicio import guardar_vacante, postular

SQL = Path(__file__).resolve().parent / "datos" / "semilla.sql"


def _ruta_sqlite() -> str | None:
    if not DATABASE_URL.startswith("sqlite"):
        return None
    return DATABASE_URL.split("///", 1)[-1]


def _ya_tiene_datos() -> bool:
    crear_tablas()
    with SessionLocal() as db:
        return db.query(VacanteDB).count() > 0


def cargar_sql(reset: bool) -> bool:
    """Carga el .sql tal cual. Devuelve False si no se puede (no es SQLite)."""
    destino = _ruta_sqlite()
    if destino is None:
        print("La semilla .sql es de SQLite; con otro motor usá --python.")
        return False
    if not SQL.exists():
        print(f"No existe {SQL}; se usa el seed de Python.")
        return False

    # En Docker esto corre en CADA arranque del contenedor. Sin esta guarda,
    # reiniciar el servicio borraría los candidatos cargados durante la demo.
    if not reset and _ya_tiene_datos():
        print("La base ya tiene datos: no se toca. Usá --reset para rehacerla.")
        return True

    if reset:
        Base.metadata.drop_all(engine)
    crear_tablas()

    con = sqlite3.connect(destino)
    try:
        # El dump trae sus propios CREATE TABLE: se limpian las tablas primero
        # para que no choquen, y se ejecuta el archivo entero.
        for tabla in reversed(Base.metadata.sorted_tables):
            con.execute(f"DROP TABLE IF EXISTS {tabla.name}")
        con.commit()
        con.executescript(SQL.read_text(encoding="utf-8"))
        con.commit()
        filas = con.execute("SELECT COUNT(*) FROM postulaciones").fetchone()[0]
        conversaciones = con.execute("SELECT COUNT(*) FROM conversaciones").fetchone()[0]
    finally:
        con.close()

    print(f"Semilla SQL cargada: {filas} postulaciones, "
          f"{conversaciones} conversaciones de WhatsApp.")
    return True


def cargar_python(reset: bool) -> None:
    if reset:
        Base.metadata.drop_all(engine)
    crear_tablas()

    with SessionLocal() as db:
        if db.query(VacanteDB).count() and not reset:
            print("La base ya tiene datos. Usá --reset para rehacerla.")
            return

        vacante = guardar_vacante(db, vacante_operador_foraneo())
        print(f"Vacante: {vacante.titulo} (id {vacante.id})")
        for candidato in CANDIDATOS:
            fila = postular(db, vacante, candidato.perfil, origen="formulario")
            estado = "APTO" if fila.apto else "descartado"
            print(f"  {fila.score:>5.1f}  {estado:10} {fila.candidato.nombre}")
        print(f"\n{len(CANDIDATOS)} candidatos cargados, todos en Postulados.")


def main(argv: list[str]) -> None:
    reset = "--reset" in argv
    if "--python" in argv or not cargar_sql(reset):
        cargar_python(reset)


if __name__ == "__main__":
    main(sys.argv[1:])
