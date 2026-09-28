"""Genera los CVs de prueba en texto y en PDF a partir de los 15 candidatos.

Los conductores casi no tienen CV en PDF, y los que tienen no son curriculums
de oficina: son una hoja con los datos, la licencia y los camiones que
manejaron. Estos imitan eso, con variaciones de formato a proposito para que la
extraccion se pruebe contra texto real y no contra una plantilla unica.

    python -m core.seed.cvs            # escribe docs/cvs_prueba/
"""
from __future__ import annotations

from pathlib import Path

from core.domain import Perfil
from core.seed.candidatos import CANDIDATOS, CandidatoSeed

SALIDA = Path("docs/cvs_prueba")

_NOMBRE_LICENCIA = {
    "federal_A": "Licencia Federal tipo A",
    "federal_B": "Licencia Federal tipo B",
    "federal_C": "Licencia Federal tipo C",
    "federal_E": "Licencia Federal tipo E",
    "estatal_A": "Licencia estatal tipo A (Nuevo León)",
    "estatal_B": "Licencia estatal tipo B (Nuevo León)",
    "estatal_C": "Licencia estatal tipo C (Nuevo León)",
}

_UNIDAD = {
    "full": "Full (doblemente articulado)",
    "tractocamion": "Tractocamión / quinta rueda",
    "torton": "Tortón",
    "rabon": "Rabón",
    "camioneta": "Camioneta de reparto",
    "autobus": "Autobús",
    "roll_off": "Roll off",
}


def _valor(perfil: Perfil, campo: str):
    return getattr(perfil, campo).valor


def cv_texto(candidato: CandidatoSeed, formato: int = 0) -> str:
    """`formato` cambia el orden y los encabezados: los CVs reales no vienen
    todos iguales y la extraccion tiene que aguantar eso."""
    p = candidato.perfil
    lineas: list[str] = []

    lineas.append(str(_valor(p, "nombre")))
    contacto = [x for x in (_valor(p, "telefono"), _valor(p, "email")) if x]
    if contacto:
        lineas.append("   |   ".join(contacto))
    if municipio := _valor(p, "municipio"):
        lineas.append(f"Domicilio: {municipio}, Nuevo León" if municipio != "Saltillo"
                      else "Domicilio: Saltillo, Coahuila")
    lineas.append("")

    bloque_lic = ["DOCUMENTACION" if formato == 0 else "LICENCIAS Y DOCUMENTOS"]
    for lic in (_valor(p, "licencias") or []):
        bloque_lic.append(f"- {_NOMBRE_LICENCIA.get(lic, lic)}")
    if vence := _valor(p, "licencia_vence"):
        bloque_lic.append(f"- Licencia vigente hasta {vence:%d/%m/%Y}")
    if apto := _valor(p, "apto_medico_vence"):
        bloque_lic.append(f"- Apto médico psicofísico vigente hasta {apto:%d/%m/%Y}")
    if _valor(p, "materiales_peligrosos"):
        bloque_lic.append("- Curso de manejo de materiales peligrosos")

    bloque_exp = ["EXPERIENCIA" if formato == 0 else "EXPERIENCIA LABORAL"]
    if (anios := _valor(p, "anios_experiencia")) is not None:
        bloque_exp.append(f"{anios:g} años de experiencia como operador.")
    for empleo in (_valor(p, "historial") or []):
        hasta = f"{empleo.hasta:%m/%Y}" if empleo.hasta else "Actualidad"
        bloque_exp.append(f"- {empleo.empresa}: {empleo.puesto} "
                          f"({empleo.desde:%m/%Y} - {hasta})")

    bloque_uni = ["UNIDADES QUE HE MANEJADO"]
    for unidad in (_valor(p, "unidades") or []):
        bloque_uni.append(f"- {_UNIDAD.get(unidad, unidad)}")

    bloque_otros = ["OTROS DATOS"]
    if (escolaridad := _valor(p, "escolaridad")) is not None:
        bloque_otros.append(f"Escolaridad: {escolaridad} terminada")
    if (foraneo := _valor(p, "disponibilidad_foranea")) is not None:
        bloque_otros.append("Disponibilidad para viajes foráneos: sí" if foraneo
                            else "Disponibilidad para viajes foráneos: no, solo rutas locales")
    if salario := _valor(p, "salario_pretendido"):
        bloque_otros.append(f"Pretensión de sueldo: ${salario:,} MXN mensuales")

    orden = ([bloque_lic, bloque_exp, bloque_uni, bloque_otros] if formato == 0
             else [bloque_exp, bloque_uni, bloque_lic, bloque_otros])
    for bloque in orden:
        lineas.extend(bloque)
        lineas.append("")
    return "\n".join(lineas).strip() + "\n"


def escribir(destino: Path = SALIDA) -> list[Path]:
    destino.mkdir(parents=True, exist_ok=True)
    escritos = []
    for i, candidato in enumerate(CANDIDATOS):
        texto = cv_texto(candidato, formato=i % 2)
        ruta_txt = destino / f"{candidato.id}.txt"
        ruta_txt.write_text(texto, encoding="utf-8")
        escritos.append(ruta_txt)
        if ruta_pdf := _a_pdf(texto, destino / f"{candidato.id}.pdf"):
            escritos.append(ruta_pdf)
    return escritos


def _a_pdf(texto: str, ruta: Path) -> Path | None:
    """PDF simple, una sola columna. Sin reportlab instalado, se saltea: los
    .txt alcanzan para probar la extraccion."""
    try:
        from reportlab.lib.pagesizes import LETTER
        from reportlab.pdfgen import canvas
    except ImportError:
        return None

    c = canvas.Canvas(str(ruta), pagesize=LETTER)
    ancho, alto = LETTER
    y = alto - 60
    for linea in texto.splitlines():
        if y < 60:
            c.showPage()
            y = alto - 60
        encabezado = linea.isupper() and len(linea) > 3
        c.setFont("Helvetica-Bold" if encabezado else "Helvetica", 11 if encabezado else 10)
        c.drawString(60, y, linea[:100])
        y -= 16 if encabezado else 14
    c.save()
    return ruta


if __name__ == "__main__":
    archivos = escribir()
    pdfs = [a for a in archivos if a.suffix == ".pdf"]
    print(f"{len(archivos) - len(pdfs)} CVs en texto y {len(pdfs)} en PDF -> {SALIDA}")
    if not pdfs:
        print("(sin reportlab no se generan PDFs: pip install reportlab)")
