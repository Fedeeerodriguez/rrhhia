# Desplegar las tres demos en EasyPanel

Escrito para: vos, siguiendo los pasos en EasyPanel.

Cada demo es una rama con su propia app completa, así que son **tres proyectos
independientes** en EasyPanel. Se despliegan igual; solo cambian la rama, el
nombre y si necesita o no la clave de la IA.

| Proyecto | Rama | ¿Necesita `ANTHROPIC_API_KEY`? |
|---|---|---|
| `rrhhia-formulario` | `demo-formulario` | No. No usa IA. |
| `rrhhia-cv` | `demo-cv` | Sí, si no cae al motor de reglas |
| `rrhhia-hibrido` | `demo-hibrido` | Sí, igual que la anterior |

> **Antes de empezar:** el repo es privado. EasyPanel necesita acceso al
> repositorio `Fedeeerodriguez/rrhhia` — se conecta una vez desde
> *Settings → Git Providers → GitHub* y sirve para los tres proyectos.

---

## La forma corta: un servicio Compose por demo

Cada rama trae su `docker-compose.yml` con todo armado. Es el camino con menos
pasos y el que menos se desvía de lo que probaste en tu máquina.

1. **Create Project** → nombre `rrhhia-formulario`.
2. **+ Service → Compose**.
3. En **Source**, elegí GitHub: repo `Fedeeerodriguez/rrhhia`, rama
   `demo-formulario`, *Build path* `/`.
4. En **Environment**, si la demo usa IA:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```
5. **Deploy**.
6. Cuando termine, en el servicio `web` → **Domains** → agregá el dominio
   (EasyPanel te da uno `*.easypanel.host` gratis), puerto interno **80**.

Repetí con las otras dos ramas cambiando el nombre del proyecto.

> Los puertos del `docker-compose.yml` (8080/8000, etc.) son para correr en tu
> máquina. En EasyPanel el tráfico entra por el dominio, así que **no hace falta
> exponer nada más**. Si el panel se queja por un puerto ocupado, borrá la
> sección `ports:` del servicio `backend`: nginx lo alcanza igual por la red
> interna.

---

## La forma larga: dos servicios por demo

Más pasos, pero te deja escalar y reiniciar el backend sin tocar el frontend, y
ver los logs separados. Es lo que yo usaría si la demo pasa a ser algo que el
cliente use todos los días.

### 1. El backend

1. **+ Service → App**, nombre `backend`.
2. **Source:** GitHub → `Fedeeerodriguez/rrhhia`, rama de la demo,
   **Build path `/backend`**.
3. **Build:** método **Dockerfile** (`/backend/Dockerfile`).
4. **Environment:**
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   DATABASE_URL=sqlite:////datos/rrhhia.db
   ```
5. **Volumes:** montá un volumen en **`/datos`**. Sin esto, cada redeploy borra
   los candidatos que cargaste en la demo.
6. **Deploy.** No le pongas dominio: solo lo consume el frontend.

### 2. El frontend

1. **+ Service → App**, nombre `web`.
2. **Source:** mismo repo y rama, **Build path `/frontend`**.
3. **Build:** método **Dockerfile** (`/frontend/Dockerfile`).
4. **Environment:**
   ```
   API_UPSTREAM=http://backend:8000
   ```
   Este es **el punto donde se rompen estos deploys**. El frontend pega a `/api`
   relativo y nginx lo reenvía al backend; `API_UPSTREAM` le dice dónde está. El
   nombre tiene que ser el del servicio backend tal como EasyPanel lo resuelve
   internamente — si el panel muestra `rrhhia-formulario_backend`, va
   `http://rrhhia-formulario_backend:8000`.
5. **Domains:** agregá el dominio, puerto interno **80**.
6. **Deploy.**

---

## Verificar que quedó bien

En este orden, que es el orden en que fallan las cosas:

```bash
# 1. El backend responde y sabe si tiene IA
curl https://TU-DOMINIO/api/salud
# {"ok":true,"demo":"hibrido","ia":true}

# 2. La base se sembró sola
curl https://TU-DOMINIO/api/vacantes/1/tablero
# {"conteo":{"postulado":3,"filtrado":4,"entrevista":3,"aceptado":1,"rechazado":9}, ...}
```

Después abrí el dominio en el navegador: tenés que ver el tablero con los 20
candidatos repartidos en las cinco columnas.

Las pantallas públicas de cada demo:

| Demo | Reclutador | Candidato | Extra |
|---|---|---|---|
| Formulario | `/` | `/postular` | — |
| CV | `/` | `/postular` | `/carga` (carga masiva) |
| Híbrido | `/` | `/postular` | `/whatsapp` (simulador del agente) |

---

## Si algo falla

**El frontend carga pero el tablero queda vacío y la consola muestra errores de
`/api`.** Es `API_UPSTREAM`: el nombre del servicio backend no es el que pusiste.
Miralo en EasyPanel, en el detalle del servicio backend, y corregí la variable en
`web`. Redeploy solo del frontend.

**Error en el build del frontend, en `npm ci`.** El `package-lock.json` está
commiteado, así que suele ser versión de Node. El Dockerfile usa `node:20-alpine`;
si el panel fuerza otra, dejá que use la del Dockerfile.

**El backend arranca pero el tablero está vacío.** El seed corre solo la primera
vez. Entrá a la terminal del servicio y corré:
```bash
python seed.py --reset
```

**Se perdieron los datos después de un redeploy.** Falta el volumen en `/datos`,
o `DATABASE_URL` no apunta ahí.

**El agente de WhatsApp contesta raro o no entiende fechas.** Fijate
`/api/salud`: si `"ia": false`, falta la `ANTHROPIC_API_KEY` y está funcionando
solo con el motor de reglas.

**Subir un CV grande da error 413.** nginx acepta 64 MB, pero EasyPanel tiene su
propio proxy adelante. Si aparece, hay que subirle el límite en el dominio.

---

## Después del deploy

- **La clave de la IA es tuya**, no del cliente. Está solo en las variables de
  entorno del backend; no aparece en el repo ni la ve nadie desde el navegador.
- **Los mensajes a candidatos no se envían**: quedan en la pestaña
  Comunicaciones. Eso es a propósito mientras sea una demo.
- **El webhook de WhatsApp** queda en `POST /api/whatsapp/webhook`, listo para
  apuntarle un proveedor (YCloud, WATI o Meta) cuando haya un número aprobado.
  Hasta entonces, el simulador de `/whatsapp` muestra el mismo agente.
- **La base es SQLite en un volumen.** Aguanta de sobra una demo y varios meses
  de uso real con este volumen de candidatos. Si el cliente avanza, el
  `datos/semilla.sql` sirve de punto de partida para migrar a Postgres.
