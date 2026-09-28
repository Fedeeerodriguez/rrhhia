# EasyPanel: paso a paso de los tres Compose

Escrito para: vos, con EasyPanel abierto en otra pestaña.

Las tres demos se despliegan igual. Cambian tres cosas: el nombre del proyecto,
la rama y los puertos. Al final de cada bloque están los valores exactos.

---

## El repositorio

**Público**, así que EasyPanel no necesita credenciales ni conectar la cuenta de
GitHub. En el campo de repositorio va la URL completa:

```
https://github.com/Fedeeerodriguez/rrhhia.git
```

También podés usarla sin `.git`; EasyPanel acepta las dos:

```
https://github.com/Fedeeerodriguez/rrhhia
```

> Si más adelante el repo vuelve a ser privado, ahí sí hay que conectar la
> cuenta en **Settings → Git Providers → GitHub** y darle acceso al repositorio.

---

## Demo B — Formulario

Empezá por esta: es la más simple y la que menos depende de la IA.

1. **Projects → Create Project** → nombre: `rrhhia-formulario`
2. Dentro del proyecto: **+ Service → Compose**
3. Nombre del servicio: `demo`
4. Pestaña **Source**:
   - Repository URL: `https://github.com/Fedeeerodriguez/rrhhia.git`
   - Branch: **`demo-formulario`**
   - Build path: `/`
5. Pestaña **Environment**, pegá:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```
   La necesita para la evaluación con IA. El puntaje por requisitos funciona sin
   ella.

   > La clave va **solo acá**, en las variables de entorno del servicio. No está
   > en el repositorio, y ahora que es público eso importa: nunca la pegues en un
   > archivo del proyecto.
6. **Deploy**. El primer build tarda unos minutos (compila el frontend).
7. Cuando termine: **Domains → Add Domain**
   - Service: **`web`**
   - Port: **`80`**
   - Dominio: el que te sugiere EasyPanel, o el tuyo
8. Abrí el dominio. Tenés que ver el tablero con 20 candidatos repartidos en las
   cinco columnas y los chips de nivel de la IA.

---

## Demo A — CV en PDF

Igual que la anterior, cambiando:

| Campo | Valor |
|---|---|
| Nombre del proyecto | `rrhhia-cv` |
| Branch | **`demo-cv`** |

Misma variable de entorno. Acá la clave pesa más: sin ella, los CVs se leen con
el motor de reglas, que con currículums reales es bastante peor.

Después del deploy, probá `/carga` en el dominio y arrastrá los PDFs de
`docs/cvs_preproduccion/`.

---

## Demo C — Híbrido con WhatsApp

| Campo | Valor |
|---|---|
| Nombre del proyecto | `rrhhia-hibrido` |
| Branch | **`demo-hibrido`** |

Misma variable. Esta es la que más la usa: extracción de CV, agente de WhatsApp
y evaluación.

Para mostrarla: `/whatsapp` en el dominio abre el simulador del agente.

---

## Los tres valores que cambian

| | Proyecto | Rama | Web | API |
|---|---|---|---|---|
| Demo B | `rrhhia-formulario` | `demo-formulario` | 8080 | 8000 |
| Demo A | `rrhhia-cv` | `demo-cv` | 8081 | 8001 |
| Demo C | `rrhhia-hibrido` | `demo-hibrido` | 8082 | 8002 |

Los puertos no se pisan entre sí, así que **las tres pueden convivir en el mismo
servidor**.

> **Los `docker-compose.yml` no publican puertos del host.** EasyPanel avisa
> *"ports is used in backend / web. It might cause conflicts with other
> services"* cuando un compose los publica, y tiene razón: el tráfico entra por
> el dominio, no por un puerto del servidor.
>
> Los puertos de la tabla de arriba son para correrlo **en tu máquina**, con el
> override:
>
> ```bash
> docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build
> ```
>
> EasyPanel no usa ese segundo archivo.

---

## Verificar, en el orden en que fallan las cosas

```bash
# 1. El backend vive y dice si tiene IA
curl https://TU-DOMINIO/api/salud
# {"ok":true,"demo":"formulario"}

# 2. La base se sembró sola
curl https://TU-DOMINIO/api/vacantes/1/tablero
# conteo: postulado 3, filtrado 4, entrevista 3, aceptado 1, rechazado 9
```

Y en el navegador:

| Demo | Reclutador | Candidato | Extra |
|---|---|---|---|
| Formulario | `/` | `/postular` | — |
| CV | `/` | `/postular` | `/carga` |
| Híbrido | `/` | `/postular` | `/whatsapp` |

---

## Si algo falla

**"repository not found" o pide credenciales.** El repo es público: revisá que
la URL esté completa, con `https://` adelante.

**El build muere en `npm ci`.** Es el paso más frágil. Mirá el log: si dice algo
de versiones de Node, el Dockerfile fija `node:20-alpine` y hay que dejar que
mande él, no la configuración del panel.

**El frontend carga pero el tablero queda vacío.** Abrí la consola del navegador:
si hay errores en `/api`, es que nginx no encuentra al backend. En Compose no
debería pasar, porque el servicio se llama `backend` y `API_UPSTREAM` ya apunta
ahí. Si lo cambiaste de nombre, actualizá la variable.

**El tablero está vacío pero `/api/salud` responde.** El seed corre solo la
primera vez. Entrá a la terminal del servicio `backend` y corré:
```bash
python seed.py --reset
```

**Se perdieron los datos después de un redeploy.** El volumen `datos` no se
montó. Verificá que el servicio `backend` lo tenga en `/datos` y que
`DATABASE_URL` sea `sqlite:////datos/rrhhia.db` (sí, son cuatro barras: tres del
esquema y una de la ruta absoluta).

**Los candidatos no tienen evaluación de IA.** Fijate `/api/salud`: si no
aparece `"ia": true`, falta la `ANTHROPIC_API_KEY`. Cargala y apretá el botón
**Evaluar con IA** en el tablero.

**Error 413 al subir un CV.** nginx acepta 64 MB, pero el proxy de EasyPanel
tiene su propio límite. Se sube en la configuración del dominio.

---

## Advertencia honesta

**Estos Compose nunca se ejecutaron.** Los escribí sin Docker instalado en la
máquina de desarrollo, así que el primer `docker compose up` de EasyPanel es la
primera prueba real de esas imágenes. Lo que está verificado es el código: los
268 tests pasan y las tres demos corren en local con uvicorn y Vite.

Si el primer build falla, pasame el log completo y lo corregimos.
