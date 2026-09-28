"""CV -> Perfil. La IA solo extrae datos; calificar es tarea de core.scoring.

Dos motores, misma salida:

- **Claude** (cuando hay ANTHROPIC_API_KEY): devuelve valor, confianza y el
  fragmento textual del CV que justifica cada dato.
- **Heuristico** (siempre disponible): reglas sobre el texto. Menos preciso, y
  a proposito devuelve confianza media, lo que en la demo hibrida hace que los
  campos aparezcan en amarillo para que una persona los confirme.

El heuristico no es un juguete: es lo que hace que la demo funcione sin API,
sin costo y sin internet. Si la conexion se cae en plena presentacion, el
sistema sigue extrayendo.
"""
from __future__ import annotations

import io
import json
import os
import re
import unicodedata
from datetime import date, datetime

from core.domain import Campo, Empleo, Origen, Perfil
from core.serializacion import decodificar

MODELO = "claude-sonnet-5"
CONFIANZA_HEURISTICA = 0.65    # debajo del umbral de 0.75: la UI lo pinta dudoso

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
    # Abreviados, como los escribe la gente: "08 sep 2027".
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7,
    "ago": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dic": 12,
}

MUNICIPIOS = [
    "Monterrey", "Apodaca", "Guadalupe", "San Nicolas de los Garza",
    "Santa Catarina", "General Escobedo", "Escobedo", "San Pedro Garza Garcia",
    "Juarez", "Garcia", "Santiago", "Cadereyta Jimenez", "Saltillo", "Ramos Arizpe",
]

UNIDADES = {
    "full": ["full", "doblemente articulado", "doble remolque"],
    "tractocamion": ["tractocamion", "tracto camion", "tracto", "quinta rueda", "trailer"],
    "torton": ["torton"],
    "rabon": ["rabon"],
    "camioneta": ["camioneta", "pick up", "pickup"],
    "autobus": ["autobus", "camion de pasajeros"],
    "roll_off": ["roll off", "rolloff"],
}

ESCOLARIDAD = [
    ("universidad", ["universidad", "licenciatura", "ingenieria"]),
    ("tecnica", ["tecnica", "tecnico", "cbtis", "conalep"]),
    ("preparatoria", ["preparatoria", "bachillerato", "prepa"]),
    ("secundaria", ["secundaria"]),
    ("primaria", ["primaria"]),
]


# --- Texto --------------------------------------------------------------------

def texto_de_pdf(contenido: bytes) -> str:
    """Extrae el texto de un PDF. Si viene escaneado (sin capa de texto) devuelve
    vacio, y el llamador decide: pedir los datos por formulario."""
    from pypdf import PdfReader

    try:
        lector = PdfReader(io.BytesIO(contenido))
    except Exception:
        return ""
    partes = []
    for pagina in lector.pages:
        try:
            partes.append(pagina.extract_text() or "")
        except Exception:
            continue
    return "\n".join(partes).strip()


def _plano(texto: str) -> str:
    """Sin acentos y en minusculas: los CVs vienen escritos de cualquier forma."""
    sin_acentos = unicodedata.normalize("NFKD", texto)
    sin_acentos = "".join(c for c in sin_acentos if not unicodedata.combining(c))
    return sin_acentos.lower()


def _linea_con(texto: str, posicion: int) -> str:
    """La linea del CV donde aparecio el dato, para mostrarla como evidencia."""
    inicio = texto.rfind("\n", 0, posicion) + 1
    fin = texto.find("\n", posicion)
    return texto[inicio: fin if fin != -1 else len(texto)].strip()[:180]


# --- Motor heuristico ---------------------------------------------------------

def _fecha(bruto: str) -> date | None:
    bruto = bruto.strip()
    for patron, orden in ((r"(\d{1,2})/(\d{1,2})/(\d{4})", "dmy"),
                          (r"(\d{4})-(\d{1,2})-(\d{1,2})", "ymd")):
        m = re.search(patron, bruto)
        if m:
            a, b, c = m.groups()
            try:
                return (date(int(c), int(b), int(a)) if orden == "dmy"
                        else date(int(a), int(b), int(c)))
            except ValueError:
                return None
    m = re.search(r"([a-z]+)\s+(?:de\s+)?(\d{4})", _plano(bruto))
    if m and m.group(1) in MESES:
        return date(int(m.group(2)), MESES[m.group(1)], 1)
    return None


def _mes_anio(bruto: str) -> date | None:
    """"03/2019" -> date(2019, 3, 1)."""
    m = re.match(r"(\d{1,2})/(\d{4})", bruto.strip())
    if not m:
        return None
    try:
        return date(int(m.group(2)), int(m.group(1)), 1)
    except ValueError:
        return None


def _campo(valor, fragmento: str | None, confianza: float = CONFIANZA_HEURISTICA) -> Campo:
    if valor in (None, "", [], {}):
        return Campo()
    return Campo(valor=valor, origen=Origen.CV, confianza=confianza, fragmento=fragmento)


def extraer_heuristico(texto: str) -> Perfil:
    perfil = Perfil()
    if not texto.strip():
        return perfil
    plano = _plano(texto)

    # Nombre: la primera linea con pinta de nombre propio.
    for linea in texto.splitlines():
        limpia = linea.strip()
        palabras = limpia.split()
        if 2 <= len(palabras) <= 5 and all(p[:1].isupper() for p in palabras if p) \
                and not any(c.isdigit() for c in limpia):
            # Alta confianza: el nombre arriba del CV casi nunca se equivoca.
            perfil.nombre = _campo(limpia, limpia, 0.9)
            break

    if m := re.search(r"(\+?52\s?)?(\d[\d\s\-]{8,15})", texto):
        perfil.telefono = _campo(m.group(0).strip(), _linea_con(texto, m.start()), 0.85)
    if m := re.search(r"[\w\.\-]+@[\w\.\-]+\.\w+", texto):
        perfil.email = _campo(m.group(0), _linea_con(texto, m.start()), 0.95)

    for municipio in MUNICIPIOS:
        if (pos := plano.find(_plano(municipio))) != -1:
            perfil.municipio = _campo(municipio, _linea_con(texto, pos))
            break

    # Licencias. La distincion federal/estatal es el filtro mas importante de
    # esta vacante, asi que se busca explicitamente.
    licencias, evidencia = [], None
    # "Lic. Fed. tipo B" es tan común como "Licencia Federal categoría B": los
    # CVs reales vienen abreviados.
    for m in re.finditer(r"lic(?:encia|\.)?\s*(?:fed(?:eral|\.)?)?[^\n]{0,80}", plano):
        tramo = m.group(0)
        federal = bool(re.search(r"fed", tramo))
        for letra in re.findall(r"\b(?:tipo|categoria|cat\.?|clase)\s*:?\s*([a-f])\b", tramo):
            licencias.append(f"{'federal' if federal else 'estatal'}_{letra.upper()}")
            evidencia = evidencia or _linea_con(texto, m.start())
    if licencias:
        perfil.licencias = _campo(sorted(set(licencias)), evidencia)

    # "vence", "vigente al", "vigencia": cada CV lo escribe distinto.
    vigencia = r"(?:vence|vencimiento|vigente\s+(?:al|hasta)|vigencia)"
    if m := re.search(rf"lic(?:encia|\.)?[^\n]{{0,70}}?{vigencia}[^\n]{{0,30}}", plano):
        if f := _fecha(_linea_con(texto, m.start())):
            perfil.licencia_vence = _campo(f, _linea_con(texto, m.start()))
    if m := re.search(
            rf"(?:apto|constancia|examen)\s*(?:de\s+)?(?:medico|psicofisic\w*|aptitud)"
            rf"[^\n]{{0,70}}", plano):
        if f := _fecha(_linea_con(texto, m.start())):
            perfil.apto_medico_vence = _campo(f, _linea_con(texto, m.start()))

    # "9 años de experiencia", "11 años manejando", "14 años en carga general".
    if m := re.search(
            r"(\d{1,2})(?:[\.,]\d)?\s*(?:anos|anios)\s+"
            r"(?:de\s+experiencia|manejando|como\s+operador|al\s+volante|en\s+\w+)", plano):
        perfil.anios_experiencia = _campo(float(m.group(1)), _linea_con(texto, m.start()), 0.8)

    unidades, evidencia_u = [], None
    for clave, sinonimos in UNIDADES.items():
        for sinonimo in sinonimos:
            if (pos := plano.find(sinonimo)) != -1:
                unidades.append(clave)
                evidencia_u = evidencia_u or _linea_con(texto, pos)
                break
    if unidades:
        perfil.unidades = _campo(sorted(set(unidades)), evidencia_u)

    for nivel, sinonimos in ESCOLARIDAD:
        for sinonimo in sinonimos:
            if (pos := plano.find(sinonimo)) != -1:
                perfil.escolaridad = _campo(nivel, _linea_con(texto, pos))
                break
        if not perfil.escolaridad.falta:
            break

    if m := re.search(r"(?:disponibilidad|viajes?)[^\n]{0,80}", plano):
        tramo = m.group(0)
        if any(x in tramo for x in ("foran", "carretera", "viajar")):
            # Ojo con la negacion: "foraneos: no, solo rutas locales" decia SI
            # con una deteccion ingenua, y un candidato que no viaja entraba
            # como apto. Primero se busca la respuesta explicita.
            respuesta = re.search(r"foran\w*\s*:?\s*(si|no)\b", tramo)
            if respuesta:
                disponible = respuesta.group(1) == "si"
            else:
                disponible = not re.search(r"\b(no|sin|unicamente|solo)\b", tramo)
            perfil.disponibilidad_foranea = _campo(disponible, _linea_con(texto, m.start()))

    if m := re.search(r"(?:pretension|sueldo|salario)[^\n]{0,40}?\$?\s?(\d{2}[\.,]?\d{3})", plano):
        perfil.salario_pretendido = _campo(
            int(re.sub(r"[^\d]", "", m.group(1))), _linea_con(texto, m.start()))

    # Historial laboral: "- Empresa: Puesto (MM/AAAA - MM/AAAA|Actualidad)".
    # Sin esto, el criterio de estabilidad queda sin dato y todos pierden puntos
    # por igual, que es peor que no tener el criterio.
    empleos, evidencia_h = [], None
    fecha_a_fecha = (r"(?P<desde>\d{1,2}/\d{4})\s*[-–—a]+\s*"
                     r"(?P<hasta>\d{1,2}/\d{4}|actualidad|presente|la fecha)")
    patrones = [
        # "- Empresa: Puesto (03/2019 - Actualidad)"
        re.compile(r"^[-*•]?\s*(?P<empresa>[^:\n]{3,60}):\s*(?P<puesto>[^(\n]{3,60})"
                   r"\(" + fecha_a_fecha + r"\)", re.IGNORECASE | re.MULTILINE),
        # "EMPRESA S.A." en una línea y "Puesto | 03/2019 – Actualidad" en la siguiente
        re.compile(r"^(?P<empresa>[^\n]{3,70})\n\s*(?P<puesto>[^|\n]{3,60})\|\s*"
                   + fecha_a_fecha, re.IGNORECASE | re.MULTILINE),
    ]
    for patron in patrones:
        for m in patron.finditer(texto):
            desde = _mes_anio(m.group("desde"))
            bruto_hasta = m.group("hasta").strip().lower()
            abierto = bruto_hasta.startswith(("actualidad", "presente", "la fecha"))
            hasta = None if abierto else _mes_anio(bruto_hasta)
            if desde is None:
                continue
            empleos.append(Empleo(empresa=m.group("empresa").strip(" .-•"),
                                  puesto=m.group("puesto").strip(" .-|"),
                                  desde=desde, hasta=hasta))
            evidencia_h = evidencia_h or _linea_con(texto, m.start())
        if empleos:
            break
    if empleos:
        perfil.historial = _campo(empleos, evidencia_h, 0.8)

    if re.search(r"(?:materiales? peligrosos?|hazmat|sustancias peligrosas)", plano):
        pos = plano.find("peligros")
        perfil.materiales_peligrosos = _campo(True, _linea_con(texto, pos))

    return perfil


# --- Motor Claude -------------------------------------------------------------

ESQUEMA = {
    "type": "object",
    "properties": {
        campo: {
            "type": "object",
            "properties": {
                "valor": {},
                "confianza": {"type": "number", "minimum": 0, "maximum": 1},
                "fragmento": {"type": "string"},
            },
            "required": ["valor", "confianza", "fragmento"],
        }
        for campo in (
            "nombre", "telefono", "email", "municipio", "licencias",
            "licencia_vence", "apto_medico_vence", "anios_experiencia",
            "unidades", "escolaridad", "disponibilidad_foranea",
            "salario_pretendido", "materiales_peligrosos",
        )
    },
}

CAMPOS = [
    "nombre", "telefono", "email", "municipio", "licencias", "licencia_vence",
    "apto_medico_vence", "anios_experiencia", "unidades", "escolaridad",
    "disponibilidad_foranea", "salario_pretendido", "materiales_peligrosos",
    "historial",
]

INSTRUCCIONES = f"""Extrae datos del CV de un conductor mexicano. Devuelve SOLO el JSON.

El objeto tiene EXACTAMENTE estas claves, escritas asi y todas presentes:
{", ".join(CAMPOS)}

Usar otro nombre de clave equivale a perder el dato: se descarta en silencio.

Para cada campo: `valor`, `confianza` (0 a 1) y `fragmento` (el texto EXACTO del
CV que justifica el dato, o "" si lo inferiste). Si un dato no aparece, pon
valor null y confianza 0. NO inventes: es peor un dato inventado que un dato
faltante, porque un humano revisa lo faltante y no lo inventado.

- nombre, telefono, email, municipio: como figuran en el encabezado del CV.

Formatos:
- licencias: lista de "federal_A".."federal_F" o "estatal_A".."estatal_C".
  Distingue bien federal (SICT, autotransporte federal) de estatal (de Nuevo
  Leon u otro estado). Es el filtro mas importante.
- licencia_vence / apto_medico_vence: "AAAA-MM-DD".
- anios_experiencia: numero. Si solo hay fechas de empleo, calculalos y baja la confianza.
- unidades: de esta lista: camioneta, rabon, torton, tractocamion, full, autobus, roll_off.
- escolaridad: ninguna, primaria, secundaria, preparatoria, tecnica, universidad.
- disponibilidad_foranea / materiales_peligrosos: true o false.
- salario_pretendido: entero en pesos mexicanos por mes.
- historial: lista de empleos {{"empresa", "puesto", "desde", "hasta"}}, con las
  fechas en "AAAA-MM-DD" y "hasta" en null si sigue trabajando ahi."""


def extraer_con_claude(texto: str, api_key: str | None = None) -> Perfil:
    from anthropic import Anthropic

    cliente = Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])
    respuesta = cliente.messages.create(
        model=MODELO,
        max_tokens=2000,
        system=INSTRUCCIONES,
        messages=[{"role": "user", "content": f"<cv>\n{texto[:20000]}\n</cv>"}],
    )
    crudo = "".join(b.text for b in respuesta.content if b.type == "text").strip()
    if crudo.startswith("```"):
        crudo = re.sub(r"^```[a-z]*\n|\n```$", "", crudo)
    return perfil_desde_extraccion(json.loads(crudo))


def perfil_desde_extraccion(datos: dict) -> Perfil:
    """Convierte la salida del modelo en un Perfil, validando tipos.

    Un modelo puede devolver una fecha mal formada o un campo de mas; eso no
    debe tumbar la carga de 15 CVs.
    """
    perfil = Perfil()
    for nombre, bruto in (datos or {}).items():
        if not hasattr(perfil, nombre) or not isinstance(bruto, dict):
            continue
        if bruto.get("valor") in (None, "", [], {}):
            continue
        # Mismo decodificador que usa la base: fechas de texto a date, empleos
        # de dict a Empleo. Sin esto el scoring recibe dicts y explota.
        try:
            valor = decodificar(nombre, bruto.get("valor"))
        except (ValueError, TypeError, KeyError, AttributeError):
            continue
        if valor is None:
            continue
        confianza = float(bruto.get("confianza") or 0.0)
        setattr(perfil, nombre, Campo(
            valor=valor, origen=Origen.CV,
            confianza=min(max(confianza, 0.0), 1.0),
            fragmento=(bruto.get("fragmento") or None),
        ))
    return perfil


# --- Fachada ------------------------------------------------------------------

def extraer(texto: str, motor: str = "auto") -> tuple[Perfil, str]:
    """Devuelve el perfil y con que motor se extrajo, para mostrarlo en la UI."""
    if motor == "heuristico" or (motor == "auto" and not os.getenv("ANTHROPIC_API_KEY")):
        return extraer_heuristico(texto), "heuristico"
    try:
        return extraer_con_claude(texto), "claude"
    except Exception:
        # Si la API falla en medio de la presentacion, la carga no se cae.
        return extraer_heuristico(texto), "heuristico (la IA no respondio)"
