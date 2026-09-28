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

## Correr

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
