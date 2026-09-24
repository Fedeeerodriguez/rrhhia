# Investigacion: vacantes de conductores en Nuevo Leon

Relevamiento hecho el 2026-09-24 para calibrar la vacante y los candidatos de
prueba de las demos. Fuentes: bolsas de trabajo activas (OCC, Computrabajo,
Indeed, Jooble, Portal del Empleo) y normativa federal.

## Requisitos knockout que aparecen en casi todas las vacantes

| Requisito | Detalle |
|---|---|
| Licencia vigente | Dos familias distintas: **estatal tipo C de NL** (carga local, 2-3 ejes) y **federal SICT tipo B o E** (autotransporte federal / foraneo) |
| Experiencia | 2-3 anios comprobables en la unidad especifica (torton, full, quinta rueda) |
| Apto medico vigente | Constancia de aptitud psicofisica; obligatoria para la federal |
| Escolaridad | Secundaria terminada con certificado en carga; en urbano/personal alcanza con saber leer y escribir |
| Disponibilidad | Horario rotativo / nocturno / viajes foraneos |

## Deseables recurrentes

Estabilidad laboral en los ultimos 5 anios (aparece explicito), experiencia en
la carga concreta (perecederos, roll-off, materiales peligrosos), edad 23+,
cartas de recomendacion, sin antecedentes penales, antidoping.

## Sueldos reales en NL (2026)

- Chofer torton local: **$16,000 - $23,000 MXN/mes** ($4,200-$5,500 semanales)
- Torton foraneo con incentivos: ~**$18,400** ($2,700 semanales + $800-1,600 de bonos)
- Chofer de camion urbano / de personal: ~**$15,000** + 2 meses de capacitacion pagada (~$12,000)
- Foraneo de carga pesada: reportes de **$8,000-$10,000 semanales** segun viajes

## Categorias de licencia federal (Acuerdo publicado en el DOF)

| Cat. | Ampara | Vigencia |
|---|---|---|
| A | Autotransporte federal de pasajeros y turismo | 4 anios |
| B | Autotransporte federal de carga (sin doblemente articulado ni peligrosos) | 4 anios |
| C | Carga de 2-3 ejes (sin materiales peligrosos) | 4 anios |
| D | Turismo, modalidad chofer-guia | 4 anios |
| **E** | **Doblemente articulado o materiales peligrosos** | **2 anios** |
| F | Pasajeros hacia/desde puertos y aeropuertos federales | 4 anios |

Dato clave para el scoring: **la categoria E exige 2 anios previos en B o C y
vence a los 2 anios**, contra 4 del resto. Es un knockout verificable y con
fecha, no una apreciacion subjetiva. Todas las categorias piden 18 anios
minimos, constancia psicofisica vigente y certificado de capacitacion de un
centro autorizado por la DGAF.

## Hallazgo que definio el diseno del producto

**Los conductores casi no tienen CV en PDF.** Este mercado se mueve por
formulario, WhatsApp y foto del documento. El dolor del reclutador de
transporte no es leer curriculums largos: es perseguir gente para confirmar si
la licencia esta vigente y de que tipo.

Por eso el motor corre sobre **datos estructurados**, y la extraccion con IA es
solo una de las formas de llenarlos. De ahi salen las tres demos:

- **A (CV first)** -- carga masiva de PDFs, extraccion con IA
- **B (Formulario)** -- captura estructurada, scoring instantaneo y sin costo de API
- **C (Hibrido)** -- el CV prellena el formulario y el reclutador confirma lo dudoso

## Advertencia sobre las fuentes

Sueldos y requisitos salen de agregadores y de una nota periodistica, no de un
estudio salarial. Sirven para calibrar una demo; **no usar en una propuesta
comercial sin contrastar con lo que el cliente paga hoy.**

## Fuentes

- [ACUERDO de categorias de la licencia federal de conductor -- SIDOF/SEGOB](https://sidof.segob.gob.mx/notas/docFuente/5427046) *(oficial)*
- [Licencia federal de conductor 2026: requisitos y costo](https://tramite.com.mx/vehiculos/licencia-federal/)
- [Jooble -- Chofer torton en Monterrey, N.L.](https://mx.jooble.org/trabajo-chofer-torton/Monterrey%2C-N.L.)
- [Jooble -- Operador quinta rueda en Monterrey, N.L.](https://mx.jooble.org/trabajo-operador-quinta-rueda/Monterrey%2C-N.L.)
- [Computrabajo -- Operador de carga en Monterrey](https://mx.computrabajo.com/trabajo-de-operador-de-carga-en-monterrey)
- [OCC -- Operador de tractocamion en Nuevo Leon](https://www.occ.com.mx/empleos/de-operador-de-tracto-camion/en-nuevo-leon/)
- [Indeed -- Operador tractocamion en Apodaca, N.L.](https://mx.indeed.com/q-operador-tractocamion-l-apodaca,-n.-l.-empleos.html)
- [Portal del Empleo (gob.mx) -- Chofer operador de transporte](https://www.empleo.gob.mx/puesto-de-trabajo/vacante/20736326-CHOFER-OPERADOR-DE-TRANSPORTE)
- [ABC Noticias -- Que se necesita para ser chofer de camion en Nuevo Leon](https://abcnoticias.mx/tendencia/2025/5/21/que-se-necesita-para-ser-chofer-de-camion-en-nuevo-leon-requisitos-2025-249801.html)
