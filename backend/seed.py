"""Deja la demo con un estado ya poblado.

La presentacion no deberia empezar con un tablero vacio ni depender de que 15
personas se postulen en vivo. Esto carga la vacante y los 15 candidatos de
prueba, ya calificados, todos en Postulados para que el reclutador pueda
apretar "aplicar sugerencias" delante del cliente.

    python seed.py [--reset]
"""
from __future__ import annotations

import sys

from core.db import SessionLocal, crear_tablas, engine
from core.modelos import Base, VacanteDB
from core.seed.candidatos import CANDIDATOS
from core.servicio import guardar_vacante, postular
from core.seed.vacante import vacante_operador_foraneo


def main(reset: bool = False) -> None:
    if reset:
        Base.metadata.drop_all(engine)
    crear_tablas()

    with SessionLocal() as db:
        if db.query(VacanteDB).count() and not reset:
            print("La base ya tiene datos. Usa --reset para rehacerla.")
            return

        vacante = guardar_vacante(db, vacante_operador_foraneo())
        print(f"Vacante: {vacante.titulo} (id {vacante.id})")

        for candidato in CANDIDATOS:
            fila = postular(db, vacante, candidato.perfil, origen="formulario")
            estado = "APTO" if fila.apto else "descartado"
            print(f"  {fila.score:>5.1f}  {estado:10} {fila.candidato.nombre}")

        print(f"\n{len(CANDIDATOS)} candidatos cargados, todos en Postulados.")


if __name__ == "__main__":
    main(reset="--reset" in sys.argv)
