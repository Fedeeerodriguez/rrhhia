# RRHHIA

Filtro automatico de candidatos para reclutamiento. Tres demos sobre **un solo
motor de scoring**, pensadas para una empresa de transporte de Nuevo Leon.

| Demo | Entrada del candidato | Que muestra |
|---|---|---|
| **A** `apps/a_cv` | Carga masiva de CVs en PDF | Extraccion con IA + ranking automatico |
| **B** `apps/b_form` | Formulario publico | Scoring instantaneo, deterministico, sin costo de API |
| **C** `apps/c_hibrido` | CV que prellena el formulario | Cada campo con su confianza y el fragmento del CV que lo justifica |

Las tres comparten `core/`: modelos, motor de scoring, tablero y mensajes. Un
arreglo al motor queda arreglado en las tres.

## Por que el scoring es Python puro

La IA **solo extrae datos**. La calificacion es codigo deterministico sobre
datos ya estructurados. Eso da dos cosas que importan en una demo en vivo:

1. **Reproducible** -- el mismo candidato saca el mismo numero siempre. Nada
   peor que un porcentaje que cambia al recargar.
2. **Explicable** -- cada punto se desglosa por criterio, con una frase en
   castellano. Es lo que convierte "87%" en una decision.

Si la API falla durante la presentacion, los resultados ya estan en la base y
la demo sigue.

## Reglas del motor

- Los **requisitos indispensables son knockout**: si falta uno, el score topa
  en 40 por mas que el candidato brille en todo lo demas.
- Dentro de ese techo los descartados **igual se ordenan** por cuantos
  indispensables cumplieron. Al que solo se le vencio la licencia lo recuperas
  en dos semanas; al que le faltan cuatro requisitos, no.
- **"No se pudo verificar" no es "no cumple".** Un dato ausente se muestra como
  alerta para pedirselo al candidato, no como descarte.

## Correr

```bash
pip install -r requirements.txt
pytest -q                      # 12 tests sobre el motor
python -m core.seed.reporte    # ranking de los 15 candidatos de prueba
```

## Estructura

```
core/
  domain.py       Campo con {valor, origen, confianza, fragmento}; perfil del candidato
  criterios.py    Un evaluador por criterio -> puntaje + por que
  scoring.py      Vacante, Score, knockouts, ranking
  seed/           Vacante de la demo + 15 candidatos calibrados
apps/             Las tres demos (backend + frontend)
docs/             Investigacion de vacantes reales de Nuevo Leon
```

## Datos

Vacante y candidatos estan calibrados contra vacantes reales publicadas en
Nuevo Leon y contra el Acuerdo de categorias de licencia federal del DOF. Ver
[docs/investigacion-vacantes-nl.md](docs/investigacion-vacantes-nl.md).

Los 15 candidatos de prueba son **ficticios** y existen para ejercitar cada
rama del motor: el que cumple todo, el de licencia vencida, el que tiene la
estatal pero no la federal, el que rota de empresa cada ocho meses, el que no
informa la mitad de los datos.
