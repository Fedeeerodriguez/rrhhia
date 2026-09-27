# RRHHIA

Filtro automático de candidatos para Recursos Humanos. Tres demos
**independientes**, pensadas para una empresa de transporte de Nuevo León.

| Carpeta | Demo | Entrada del candidato |
|---|---|---|
| `demo-cv/` | **A — CV first** | El reclutador arrastra 10-15 CVs en PDF |
| `demo-formulario/` | **B — Formulario** | Link público, ocho campos, desde el celular |
| `demo-hibrido/` | **C — Híbrido** | El CV prellena el formulario y una persona confirma |

Cada carpeta tiene su propio `backend/` y `frontend/`, corre sola y se despliega
sola. Comparten el mismo motor de scoring, copiado en cada una.

## Correr una demo

```bash
cd demo-formulario/backend
pip install -r requirements.txt
python seed.py --reset                       # vacante + 15 candidatos calificados
uvicorn main:app --reload --port 8000

cd ../frontend
npm install
npm run dev                                  # http://localhost:5173
```

Puertos por demo, para poder levantar las tres a la vez:

| Demo | Backend | Frontend |
|---|---|---|
| `demo-formulario` | 8000 | 5173 |
| `demo-cv` | 8001 | 5174 |
| `demo-hibrido` | 8002 | 5175 |

## Cómo funciona

Dos etapas deliberadamente separadas:

1. **Extracción** — PDF → texto → Claude devuelve cada dato con su confianza y
   el fragmento exacto del CV que lo justifica.
2. **Calificación** — Python puro, determinista, sobre datos ya estructurados.

Si no hay `ANTHROPIC_API_KEY`, o si la IA no responde en medio de la
presentación, la extracción cae a un **motor heurístico** de reglas y la carga
no se detiene. Ese motor reproduce el mismo score que el formulario en los 15
candidatos de prueba.

### Las reglas que hay que saber defender

- **Los requisitos indispensables son knockout**: si falta uno, el score topa en
  40 por más que el candidato brille en todo lo demás.
- **Dentro de ese techo los descartados igual se ordenan** por cuántos
  indispensables cumplieron. Al que solo se le venció la licencia lo recuperas
  en dos semanas; al que le faltan cuatro requisitos, no.
- **"No se pudo verificar" ≠ "no cumple".** Un dato ausente es una alerta para
  pedírselo al candidato, no un descarte.
- **El sistema propone, la persona decide.** Nada se mueve solo de columna.
- **Ningún score se muestra sin su porqué**, en ninguna pantalla.

## Tests

```bash
cd demo-cv/backend && pytest -q        # 67
cd demo-formulario/backend && pytest -q  # 43
cd demo-hibrido/backend && pytest -q   # 70
```

Los tests **no llaman a la API**: `tests/conftest.py` saca la
`ANTHROPIC_API_KEY` del entorno. Sin eso tardan minutos, gastan dinero y dejan
de ser deterministas.

## Estructura de cada proyecto

```
backend/
  core/         dominio, criterios, scoring, pipeline, mensajes, extracción, persistencia
  core/seed/    vacante, 15 candidatos calibrados, generador de CVs de prueba
  main.py       la API propia de esa demo
  seed.py       deja la base poblada para la presentación
frontend/
  src/componentes/   tablero, panel de detalle, bandeja + la pantalla propia de la demo
```

## Datos de prueba

Vacante y candidatos están calibrados contra vacantes reales de Nuevo León y
contra el Acuerdo de categorías de licencia federal del DOF
([docs/investigacion-vacantes-nl.md](docs/investigacion-vacantes-nl.md)).

Los 15 candidatos son **ficticios** y existen para ejercitar cada rama del
motor: el que cumple todo, el de licencia vencida, el que tiene la estatal pero
no la federal, el que rota de empresa cada ocho meses, el que no informa la
mitad de los datos. Sus CVs en PDF se generan con:

```bash
python -m core.seed.cvs
```

## Diseño

- [docs/diseno-demos.md](docs/diseno-demos.md) — las tres pantallas y las decisiones de UI
- [docs/investigacion-vacantes-nl.md](docs/investigacion-vacantes-nl.md) — requisitos y sueldos reales de NL
