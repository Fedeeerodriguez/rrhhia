# Diseño de las tres demos

Un solo núcleo, tres puertas de entrada. Este documento fija qué comparten,
qué cambia y cómo se ve cada una antes de escribir la UI.

---

## 1. Qué comparte el núcleo

Todo lo que ya existe (`domain`, `criterios`, `scoring`) más tres piezas que
faltan y que son idénticas en las tres demos:

| Pieza | Que resuelve |
|---|---|
| `core/pipeline.py` | Etapas del tablero y reglas de movimiento entre ellas |
| `core/mensajes.py` | Plantillas por etapa y bandeja de salida |
| `core/db.py` + `core/modelos.py` | Persistencia SQLite |

### Etapas del tablero

```
POSTULADO → FILTRADO → ENTREVISTA → ACEPTADO
                    ↘ RECHAZADO ↙
```

- **POSTULADO** — entró, todavía sin revisar por un humano
- **FILTRADO** — pasó el corte automático (apto y sobre el umbral)
- **ENTREVISTA** — el reclutador lo agendó
- **ACEPTADO / RECHAZADO** — terminales

El scoring **no mueve candidatos solo**: propone. Al terminar la carga, los
aptos aparecen en POSTULADO ordenados por score con un botón "mover los N
aptos a Filtrados". El reclutador mantiene el control, que es lo que hace que
confíe en la herramienta.

Cada movimiento deja un `EventoEtapa` con quién, cuándo y de dónde a dónde.
En la demo sirve para mostrar trazabilidad sin construir un módulo de auditoría.

### Mensajes

Una plantilla por transición, con variables `{nombre}`, `{puesto}`, `{empresa}`.
Se disparan al mover de columna y caen en una **bandeja de salida visible en la
UI**, no se envían de verdad. En una demo, mandar correos reales es riesgo puro:
un mail a una dirección equivocada delante del cliente no se arregla.

| Transición | Plantilla |
|---|---|
| → FILTRADO | "Tu postulación avanzó, te contactamos para agendar" |
| → ENTREVISTA | "Confirmamos entrevista" |
| → ACEPTADO | "Bienvenido, estos son los siguientes pasos" |
| → RECHAZADO | "Gracias por postularte, no continuamos en esta ocasión" |

El rechazo se manda **siempre**, y es medio punto de venta por sí solo: hoy el
candidato que no pasa simplemente nunca recibe respuesta.

---

## 2. Modelo de datos

```
Vacante ──< Postulacion >── Candidato
              │
              ├──< EventoEtapa
              └──< Mensaje

Postulacion guarda: perfil (JSON), score, desglose (JSON), etapa, origen
```

El **perfil se guarda serializado con su confianza y fragmento por campo**, no
aplanado. Es lo que permite que la demo C pinte en amarillo y que un re-scoring
no tenga que volver a llamar a la IA.

El **score se persiste junto con su desglose**. Si la API se cae durante la
presentación, todo lo ya procesado se sigue viendo.

---

## 3. Las tres demos

### Demo A — CV first

**Pantalla única del reclutador.**

1. Crear vacante (formulario con indispensables y deseables)
2. Zona de drop: arrastrar 10-15 PDFs
3. Barra de progreso "analizando 8 de 12" — procesamiento en paralelo
4. Lista rankeada con score, chips de match y alertas
5. Click → panel lateral con el desglose por criterio y el CV al lado
6. Tablero kanban

**Riesgo:** depende de la API en vivo. Mitigación: el set de prueba viene
pre-procesado en la base, y el botón de carga vuelve a procesarlo de verdad
solo si el reclutador lo pide.

### Demo B — Formulario

**Dos pantallas:** el link público del candidato y el tablero del reclutador.

El formulario del candidato es corto y pensado para celular, porque el conductor
lo va a llenar desde el teléfono: tipo de licencia, vencimiento, unidades que
manejó, años, disponibilidad foránea, pretensión. **Ocho campos, no treinta.**

Al enviar, el score se calcula al instante — sin IA, sin costo, sin espera — y
el candidato ya aparece en el tablero del reclutador.

**Es la demo que arrancamos primero**: cierra end-to-end sin depender de nada
externo y nos deja el tablero validado para las otras dos.

### Demo C — Híbrido

El flujo real que usan muchas empresas: **subís el CV y te prellena el formulario.**

1. El candidato sube su CV
2. La IA extrae y prellena
3. **Cada campo se muestra con su estado:**
   - 🟢 verde — alta confianza, se da por bueno
   - 🟡 amarillo — dudoso, con el fragmento del CV al lado: *"desde 2017 en Transportes X"* → ¿9 años?
   - ⚪ vacío — no se encontró, hay que llenarlo a mano
4. La persona confirma o corrige lo amarillo
5. Recién ahí se calcula el score

**El detalle que hace la demo:** al lado de cada campo dudoso se muestra el
texto exacto del CV de donde salió el dato. Sin eso, "corregir lo que la IA no
detectó" es adivinar. Con eso, se resuelve en dos clics.

Esta capa ya está soportada por el núcleo: `Campo` guarda
`{valor, origen, confianza, fragmento}` desde el primer commit.

---

## 4. Decisiones de UI

- **Mobile-first en las pantallas del candidato**, desktop en las del reclutador.
  El conductor llena desde el celular; el de RH trabaja en una PC.
- **El score nunca aparece sin su porqué.** Ni un número suelto en toda la UI.
- **Rojo = descartado por knockout. Amarillo = falta verificar un dato.**
  Nunca el mismo color: son acciones distintas para el reclutador.
- **El tablero es la pantalla principal**, no la lista. La lista rankeada es el
  momento del filtro; el tablero es donde se trabaja todos los días.

---

## 5. Orden de construcción

| Fase | Qué | Estado |
|---|---|---|
| 1 | Núcleo: dominio, criterios, scoring, seed | ✅ |
| 2 | Persistencia + pipeline + mensajes + **Demo B** completa | ⬜ |
| 3 | **Demo A**: extracción de PDF + carga masiva | ⬜ |
| 4 | **Demo C**: confianza por campo + revisión | ⬜ |
| 5 | Deploy EasyPanel (3 URLs) + guion de 5 minutos | ⬜ |
