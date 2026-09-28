# RRHHIA

Filtro automático de candidatos para Recursos Humanos. Tres demos
**independientes**, pensadas para una empresa de transporte de Nuevo León.

**Una rama por demo.** Cada rama tiene su demo en la raíz (`backend/` +
`frontend/`), corre sola y se despliega sola sin configurar subcarpetas.

| Rama | Demo | Entrada del candidato | Puertos |
|---|---|---|---|
| `main` | — | núcleo compartido y documentación, sin UI | — |
| `demo-cv` | **A — CV first** | El reclutador arrastra 10-15 CVs en PDF | 8001 / 5174 |
| `demo-formulario` | **B — Formulario** | Link público, ocho campos, desde el celular | 8000 / 5173 |
| `demo-hibrido` | **C — Híbrido** | El CV prellena el formulario y una persona confirma | 8002 / 5175 |

Esta rama (`main`) es el **hub**: tiene el núcleo canónico en `core/` y la
documentación, pero ninguna interfaz.

> **Regla:** un arreglo al motor se hace en `main` y se copia a las tres ramas.
> Nunca al revés. Si el motor se arregla en una rama de demo, las otras dos
> quedan mintiendo.

## Trabajar en las tres a la vez

Las tres ramas están montadas como carpetas separadas con `git worktree`, así
que se pueden levantar todas juntas sin andar cambiando de rama:

```
Proyectos/rrhhia               main       (núcleo + docs)
Proyectos/rrhhia-cv            demo-cv
Proyectos/rrhhia-formulario    demo-formulario
Proyectos/rrhhia-hibrido       demo-hibrido
```

Para correr una demo, entrá a su carpeta y seguí el README de esa rama. Si
alguna carpeta se pierde, se recrea con:

```bash
git worktree add ../rrhhia-cv demo-cv
```

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

Desde la carpeta de cada demo:

```bash
cd ../rrhhia-cv/backend && pytest -q          # 67
cd ../rrhhia-formulario/backend && pytest -q  # 43
cd ../rrhhia-hibrido/backend && pytest -q     # 70
```

Los tests **no llaman a la API**: `tests/conftest.py` saca la
`ANTHROPIC_API_KEY` del entorno. Sin eso tardan minutos, gastan dinero y dejan
de ser deterministas.

## Estructura

En `main`:

```
core/         dominio, criterios, scoring, pipeline, mensajes, extracción, persistencia
core/seed/    vacante, 15 candidatos calibrados, generador de CVs de prueba
docs/         investigación de vacantes de NL y diseño de las demos
```

En cada rama de demo:

```
backend/core/      copia del núcleo
backend/main.py    la API propia de esa demo
backend/seed.py    deja la base poblada para la presentación
frontend/src/      tablero, panel de detalle, bandeja + la pantalla propia
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
