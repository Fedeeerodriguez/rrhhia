# RRHHIA — Demo A: CV first

El reclutador arrastra 10-15 CVs en PDF y el sistema los extrae, califica y rankea.

Esta rama (`demo-cv`) contiene **solo esta demo**, lista para desplegar sola.
Las otras dos viven en sus propias ramas; el núcleo compartido está en `main`.

| Rama | Demo |
|---|---|
| `main` | núcleo compartido y documentación, sin UI |
| `demo-cv` | A — carga masiva de CVs en PDF |
| `demo-formulario` | B — formulario público del candidato |
| `demo-hibrido` | C — el CV prellena el formulario |

## Docker

```bash
ANTHROPIC_API_KEY=sk-... docker compose up -d --build
```

- Web: http://localhost:8081
- API: http://localhost:8001/docs

Dos servicios: `backend` (uvicorn) y `web` (nginx con el build de Vite). El
frontend pega a `/api` relativo y **nginx lo reenvía al backend**, así que no
hace falta decirle al front dónde está la API.

Detalles que importan:

- La base vive en un **volumen** (`datos`), no en la imagen: reconstruir no
  borra los candidatos cargados.
- `seed.py` corre al arrancar y es idempotente: siembra la primera vez y después
  respeta lo que haya.
- **Sin `ANTHROPIC_API_KEY` la demo igual funciona**: la extracción cae al motor
  heurístico.
- nginx acepta hasta 64 MB por request y espera hasta 5 minutos, porque la carga
  masiva de CVs manda varios PDF juntos y la extracción con IA tarda.

Para borrar todo y empezar de cero:

```bash
docker compose down -v
```

> Si ya tenés algo escuchando en esos puertos (por ejemplo el `uvicorn` de
> desarrollo), bajalo antes o cambiá los puertos en `docker-compose.yml`.

## Correr sin Docker

```bash
cd backend
pip install -r requirements.txt
python seed.py --reset                 # vacante + 15 candidatos ya calificados
uvicorn main:app --reload --port 8001

cd ../frontend
npm install
npm run dev                            # http://localhost:5174
```

## La pantalla

Una sola pantalla de reclutador con tres pestañas: **Cargar CVs**, **Tablero** y **Comunicaciones**.

Los archivos se procesan en tandas para que la barra de progreso avance de verdad. Un CV ilegible (un PDF escaneado, que es una foto y no tiene texto) se informa aparte y **no detiene el procesamiento de los otros**.

## Cómo califica

Dos etapas deliberadamente separadas:

1. **Extracción** — la IA solo saca datos, y devuelve cada uno con su confianza y
   el fragmento del CV que lo justifica.
2. **Calificación** — Python puro y determinista sobre datos ya estructurados.

Sin `ANTHROPIC_API_KEY`, o si la IA no responde en plena presentación, la
extracción cae a un **motor heurístico** de reglas y nada se detiene. Ese motor
reproduce el mismo score que el formulario en los 15 candidatos de prueba.

### La evaluación con IA

Sobre el puntaje por requisitos corre una **segunda capa**: una lectura
cualitativa que las reglas no pueden hacer. Seis empleos en cinco años pueden
ser rotación o una progresión de rabón a tortón a full; nueve años manejando
pueden ser reparto urbano o ruta larga a Laredo.

Tres reglas la hacen confiable:

- **La IA no descarta a nadie.** Evalúa a todos, cumplan o no los
  indispensables, porque todos tienen derecho a ser evaluados. Lo que hace es
  mostrar quiénes son los más aptos y quiénes no.
- **Nunca revierte un requisito indispensable.** El ajuste está acotado a ±10 y
  el tope de los knockout se vuelve a aplicar después: un candidato con la
  licencia vencida puede quedar mejor ubicado entre los descartados, pero no
  cruza al grupo de los aptos. Esa línea la decide un hecho, no un criterio.
- **Los dos números se muestran siempre.** El reclutador ve qué parte es
  objetiva y qué parte es criterio.

Sin `ANTHROPIC_API_KEY` no hay evaluación y el sistema sigue funcionando con el
puntaje por requisitos, que es el que manda.

### Las reglas que hay que saber defender

- **Los indispensables son knockout**: si falta uno, el score topa en 40 por más
  que el candidato brille en todo lo demás.
- **Dentro de ese techo los descartados igual se ordenan** por cuántos
  indispensables cumplieron. Al que solo se le venció la licencia lo recuperas en
  dos semanas; al que le faltan cuatro requisitos, no.
- **"No se pudo verificar" ≠ "no cumple".** Un dato ausente es una alerta para
  pedírselo al candidato, no un descarte.
- **El sistema propone, la persona decide.** Nada se mueve solo de columna.
- **Ningún score se muestra sin su porqué**, en ninguna pantalla.

## Datos de la demo

La base ficticia está en **`backend/datos/semilla.sql`**, versionada dentro del
proyecto. No es Supabase ni ningún servicio externo: es SQL plano que se carga
en el SQLite del contenedor.

```bash
cd backend
python seed.py            # carga la semilla la primera vez
python seed.py --reset    # la rehace desde cero
python seed.py --python   # el seed mínimo: vacante + 15 candidatos sin mover
```

No es "15 candidatos recién llegados": es un proceso ya andando, con gente en
entrevista, alguien aceptado, rechazados con su motivo, 21 mensajes enviados y
3 conversaciones de WhatsApp (una a medio camino, para retomarla en vivo).

| | |
|---|---|
| Postulaciones | 20, repartidas en las 5 etapas |
| Orígenes | formulario, CV, WhatsApp |
| Conversaciones | 3 |

Se regenera con `python -m tools.generar_sql` desde la rama `main`. **El .sql no
se edita a mano** salvo para retocar un dato antes de una presentación: los
cambios de fondo van en el generador.

Como es SQL estándar, el día que esto pase a Postgres o Supabase el mismo
archivo sirve de punto de partida.

## CVs para probar

En `docs/cvs_preproduccion/` hay CVs que imitan currículums reales —
abreviaturas, faltas de ortografía, columnas, datos en desorden— más uno
escaneado sin capa de texto, que es el caso más común de todos.

| Archivo | Qué prueba |
|---|---|
| `cv-formal-jose-luis-garza.pdf` | CV bien armado, hecho en Word |
| `cv-informal-martin-cepeda.pdf` | Hoja de datos con abreviaturas: "Lic. Fed. tipo B vence 08 sep 2027" |
| `cv-incompleto-ramiro-tovar.pdf` | Con huecos: sin apto médico, sin escolaridad |
| `cv-escaneado-sin-texto.pdf` | La foto del CV: no tiene texto que extraer |

Se regeneran con `python -m core.seed.cvs_reales`.

## Tests

```bash
cd backend && pytest -q
```

Los tests **no llaman a la API**: `tests/conftest.py` saca la
`ANTHROPIC_API_KEY` del entorno. Sin eso tardan minutos, gastan dinero y dejan de
ser deterministas.

## Deploy

La raíz de esta rama es la demo. En EasyPanel: un servicio para `backend/`
(uvicorn) y otro para `frontend/` (build de Vite servido como estático), con
`ANTHROPIC_API_KEY` como variable de entorno del backend.

## Datos

Vacante y candidatos calibrados contra vacantes reales de Nuevo León y el
Acuerdo de categorías de licencia federal del DOF, en
[docs/investigacion-vacantes-nl.md](docs/investigacion-vacantes-nl.md). Los 15
candidatos son ficticios y existen para ejercitar cada rama del motor.

## Si tocas el núcleo

`backend/core/` es una copia del núcleo que vive en `main`. Un arreglo al motor
se hace en `main` y se copia a las tres ramas. Al revés no: si el motor se
arregla solo acá, las otras dos demos quedan mintiendo.
