# RRHHIA — Demo C: Híbrido

El candidato sube su CV, la IA prellena el formulario y una persona confirma lo dudoso.

Esta rama (`demo-hibrido`) contiene **solo esta demo**, lista para desplegar sola.
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

- Web: http://localhost:8082
- API: http://localhost:8002/docs

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
uvicorn main:app --reload --port 8002

cd ../frontend
npm install
npm run dev                            # http://localhost:5175
```

## La pantalla

Cada campo queda en uno de tres estados:

- 🟢 **Leído del CV** — alta confianza, se da por bueno
- 🟡 **Confirma esto** — dudoso, con el **fragmento exacto del CV** al lado
- ⚪ **Falta** — no se encontró, hay que escribirlo

Ese fragmento es lo que hace la demo: sin la evidencia, "corregir lo que la IA no detectó" es adivinar. Con la evidencia, se resuelve en dos clics.

Después, en el panel de detalle, el reclutador puede corregir un dato y el score se rehace al instante **sin volver a llamar a la IA**: el perfil ya está guardado con su trazabilidad.

## Cómo califica

Dos etapas deliberadamente separadas:

1. **Extracción** — la IA solo saca datos, y devuelve cada uno con su confianza y
   el fragmento del CV que lo justifica.
2. **Calificación** — Python puro y determinista sobre datos ya estructurados.

Sin `ANTHROPIC_API_KEY`, o si la IA no responde en plena presentación, la
extracción cae a un **motor heurístico** de reglas y nada se detiene. Ese motor
reproduce el mismo score que el formulario en los 15 candidatos de prueba.

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
