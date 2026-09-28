"""CVs realistas en PDF para probar en preproducción.

Los 15 CVs de `core/seed/cvs.py` los genera el mismo código que conoce el
modelo de datos, así que son demasiado limpios: probar contra ellos es hacerse
trampa al solitario. Estos imitan currículums de conductores de verdad —
abreviaturas, columnas, encabezados en mayúscula, datos en desorden, marcas de
camión, una constancia pegada al final— para ver si la extracción aguanta.

    python -m core.seed.cvs_reales          # escribe docs/cvs_preproduccion/
"""
from __future__ import annotations

from pathlib import Path

SALIDA = Path("docs/cvs_preproduccion")

# --- Los tres casos -----------------------------------------------------------

FORMAL = {
    "archivo": "cv-formal-jose-luis-garza",
    "titulo": "CV bien armado, hecho en Word con tabla de datos",
    "bloques": [
        ("titulo", "JOSÉ LUIS GARZA MONTEMAYOR"),
        ("sub", "Operador de Autotransporte Federal de Carga"),
        ("linea", "Cel. 811 204 7789   ·   jlgarza.operador@gmail.com"),
        ("linea", "Av. Miguel Alemán 2140, Col. Centro, Apodaca, N.L."),
        ("linea", "38 años   ·   Estado civil: casado"),
        ("espacio", ""),
        ("encabezado", "OBJETIVO"),
        ("parrafo", "Incorporarme como operador de tractocamión en rutas foráneas, "
                    "aprovechando mi experiencia de 14 años en carga general y "
                    "refrigerada en el noreste del país."),
        ("espacio", ""),
        ("encabezado", "DOCUMENTACIÓN VIGENTE"),
        ("bullet", "Licencia Federal de Conductor, categoría E — vigente al 04/11/2028"),
        ("bullet", "Constancia de aptitud psicofísica integral — vigente al 19/02/2028"),
        ("bullet", "Curso de manejo de materiales peligrosos (SICT) — 2024"),
        ("bullet", "Cartilla militar liberada · INE vigente · CURP y RFC"),
        ("espacio", ""),
        ("encabezado", "EXPERIENCIA PROFESIONAL"),
        ("negrita", "TRANSPORTES MONTERREY DEL NORTE, S.A. DE C.V."),
        ("linea", "Operador de tractocamión quinta rueda    |    03/2019 – Actualidad"),
        ("bullet", "Ruta Monterrey–Laredo–San Luis Potosí, carga general y paletizada."),
        ("bullet", "Unidades Kenworth T680 y Freightliner Cascadia con caja seca de 53'."),
        ("bullet", "Cero incidentes con responsabilidad en 6 años."),
        ("espacio", ""),
        ("negrita", "FLETES Y MUDANZAS DEL GOLFO"),
        ("linea", "Operador de tortón    |    06/2012 – 01/2019"),
        ("bullet", "Distribución local y foránea de material de construcción."),
        ("espacio", ""),
        ("encabezado", "ESCOLARIDAD"),
        ("linea", "Secundaria Técnica No. 44, Monterrey, N.L. — concluida en 2004"),
        ("espacio", ""),
        ("encabezado", "OTROS DATOS"),
        ("linea", "Disponibilidad para viajar: total, incluyendo fines de semana."),
        ("linea", "Expectativa económica: $23,000 mensuales más bonos por viaje."),
    ],
}

INFORMAL = {
    "archivo": "cv-informal-martin-cepeda",
    "titulo": "Hoja de datos escrita a mano por el operador, con abreviaturas",
    "bloques": [
        ("titulo", "MARTIN CEPEDA RUIZ"),
        ("linea", "Tel 81-1877-4412"),
        ("linea", "Col. Fomerrey 35, Gral. Escobedo NL"),
        ("espacio", ""),
        ("encabezado", "DATOS"),
        ("linea", "Lic. Fed. tipo B vence 08 sep 2027"),
        ("linea", "Apto medico vence 22 enero 2027"),
        ("linea", "11 años manejando"),
        ("espacio", ""),
        ("encabezado", "CAMIONES QUE E MANEJADO"),
        ("linea", "Torton, rabon, trailer sencillo (quinta rueda)"),
        ("linea", "Volteo de 14 m3 tambien"),
        ("espacio", ""),
        ("encabezado", "DONDE E TRABAJADO"),
        ("linea", "Transportes El Roble - operador - 2015 a 2021"),
        ("linea", "Materiales Sanchez - chofer torton - 2021 a la fecha"),
        ("espacio", ""),
        ("encabezado", "ESTUDIOS"),
        ("linea", "Termine la secundaria"),
        ("espacio", ""),
        ("linea", "Si puedo salir a carretera, no tengo problema"),
        ("linea", "Quiero ganar como 19 mil al mes"),
        ("linea", "No e manejado material peligroso"),
    ],
}

PARCIAL = {
    "archivo": "cv-incompleto-ramiro-tovar",
    "titulo": "CV con huecos: sin apto médico, sin escolaridad, sin sueldo",
    "bloques": [
        ("titulo", "Ramiro Tovar Elizondo"),
        ("linea", "ramirotovar88@hotmail.com"),
        ("espacio", ""),
        ("encabezado", "EXPERIENCIA"),
        ("linea", "Grupo Logístico Regiomontano: Operador full (04/2017 - 11/2023)"),
        ("linea", "Transportes Cuauhtémoc: Operador tractocamión (12/2023 - Actualidad)"),
        ("espacio", ""),
        ("encabezado", "LICENCIA"),
        ("linea", "Federal tipo E, vigente hasta 30/06/2027"),
        ("espacio", ""),
        ("encabezado", "UNIDADES"),
        ("linea", "Tractocamión, full, tortón"),
        ("espacio", ""),
        ("linea", "Disponible para viajes foráneos."),
    ],
}

CASOS = [FORMAL, INFORMAL, PARCIAL]


# --- Render -------------------------------------------------------------------

def _texto_plano(caso: dict) -> str:
    lineas = []
    for tipo, texto in caso["bloques"]:
        if tipo == "espacio":
            lineas.append("")
        elif tipo == "bullet":
            lineas.append(f"- {texto}")
        else:
            lineas.append(texto)
    return "\n".join(lineas) + "\n"


def _pdf(caso: dict, ruta: Path) -> Path | None:
    try:
        from reportlab.lib.pagesizes import LETTER
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
    except ImportError:
        return None

    c = canvas.Canvas(str(ruta), pagesize=LETTER)
    ancho, alto = LETTER
    margen = 22 * mm
    y = alto - margen

    estilos = {
        "titulo": ("Helvetica-Bold", 16, 24),
        "sub": ("Helvetica-Oblique", 11, 16),
        "encabezado": ("Helvetica-Bold", 10.5, 18),
        "negrita": ("Helvetica-Bold", 10, 15),
        "linea": ("Helvetica", 10, 14),
        "bullet": ("Helvetica", 10, 14),
        "parrafo": ("Helvetica", 10, 13),
        "espacio": ("Helvetica", 10, 8),
    }

    for tipo, texto in caso["bloques"]:
        fuente, tamano, salto = estilos[tipo]
        if y < margen + salto:
            c.showPage()
            y = alto - margen
        c.setFont(fuente, tamano)

        if tipo == "espacio":
            y -= salto
            continue
        if tipo == "encabezado":
            c.drawString(margen, y, texto)
            c.setLineWidth(0.4)
            c.line(margen, y - 3, ancho - margen, y - 3)
            y -= salto
            continue
        if tipo == "bullet":
            c.drawString(margen + 6, y, "•")
            texto_bullet = texto
            c.drawString(margen + 16, y, texto_bullet[:98])
            y -= salto
            continue
        if tipo == "parrafo":
            # Corte simple por ancho: los CVs reales traen párrafos largos.
            palabras, linea = texto.split(), ""
            for palabra in palabras:
                if len(linea) + len(palabra) > 92:
                    c.drawString(margen, y, linea)
                    y -= salto
                    linea = palabra
                else:
                    linea = f"{linea} {palabra}".strip()
            if linea:
                c.drawString(margen, y, linea)
                y -= salto
            continue

        c.drawString(margen, y, texto[:100])
        y -= salto

    c.save()
    return ruta


def escribir(destino: Path = SALIDA) -> list[Path]:
    destino.mkdir(parents=True, exist_ok=True)
    escritos = []
    for caso in CASOS:
        txt = destino / f"{caso['archivo']}.txt"
        txt.write_text(_texto_plano(caso), encoding="utf-8")
        escritos.append(txt)
        if pdf := _pdf(caso, destino / f"{caso['archivo']}.pdf"):
            escritos.append(pdf)

    # Un PDF sin capa de texto, que es el caso más común de todos: la foto del
    # CV sacada con el celular. Sirve para probar que el sistema no se cae y
    # que el agente pasa a preguntar.
    escaneado = destino / "cv-escaneado-sin-texto.pdf"
    if _pdf_escaneado(escaneado):
        escritos.append(escaneado)

    (destino / "LEEME.md").write_text(_leeme(), encoding="utf-8")
    return escritos


def _pdf_escaneado(ruta: Path) -> Path | None:
    """Una página con un rectángulo: ningún texto que extraer."""
    try:
        from reportlab.lib.pagesizes import LETTER
        from reportlab.pdfgen import canvas
    except ImportError:
        return None
    c = canvas.Canvas(str(ruta), pagesize=LETTER)
    ancho, alto = LETTER
    c.setFillGray(0.85)
    c.rect(60, alto - 500, ancho - 120, 420, fill=1, stroke=0)
    c.save()
    return ruta


def _leeme() -> str:
    filas = "\n".join(f"| `{c['archivo']}.pdf` | {c['titulo']} |" for c in CASOS)
    return f"""# CVs de preproducción

CVs para probar la extracción contra algo parecido a la realidad. Los 15 de
`docs/cvs_prueba/` los genera el mismo código que conoce el modelo de datos, así
que salen demasiado limpios; estos no.

| Archivo | Qué prueba |
|---|---|
{filas}
| `cv-escaneado-sin-texto.pdf` | La foto del CV sacada con el celular: no tiene texto que extraer |

Se regeneran con:

```bash
python -m core.seed.cvs_reales
```

## Cómo probarlos

- **Demo A:** arrastralos en `/carga`.
- **Demo C:** subilos en `/postular`, o mandalos por el chat en `/whatsapp`.
- El escaneado tiene que fallar **con un mensaje claro**, no romper la carga de
  los demás.
"""


if __name__ == "__main__":
    archivos = escribir()
    print(f"{len(archivos)} archivos en {SALIDA}")
    for a in archivos:
        print(" ", a.name)
