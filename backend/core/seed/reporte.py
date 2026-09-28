"""Ranking de los 15 candidatos de prueba en la terminal.

Sirve para calibrar el motor sin levantar nada: si este listado no coincide con
el que haria un reclutador a mano, el motor esta mal, no la UI.

    python -m core.seed.reporte
"""
from __future__ import annotations

from core.scoring import rankear
from core.seed.candidatos import perfiles, por_id
from core.seed.vacante import vacante_operador_foraneo


def main() -> None:
    vacante = vacante_operador_foraneo()
    idx = por_id()

    print(f"\n  {vacante.titulo} -- {vacante.municipio}, N.L.")
    print(f"  ${vacante.salario_min:,} - ${vacante.salario_max:,} MXN/mes")
    print(f"  {len(vacante.indispensables)} requisitos indispensables, "
          f"{len(vacante.criterios) - len(vacante.indispensables)} deseables\n")
    print(f"  {'#':>2} {'score':>6}  {'estado':10} nombre")
    print("  " + "-" * 74)

    for i, (cid, score) in enumerate(rankear(vacante, perfiles()), 1):
        candidato = idx[cid]
        estado = "APTO" if score.apto else "descartado"
        print(f"  {i:>2} {score.valor:>6.1f}  {estado:10} {candidato.perfil.nombre.valor}")
        for razon in score.razones:
            print(f"     {'':>6}  {'':10} - {razon}")
        for alerta in score.alertas[:2]:
            print(f"     {'':>6}  {'':10} ! {alerta}")
        print()


if __name__ == "__main__":
    main()
