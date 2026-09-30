"""Agente de postulación por WhatsApp.

El conductor manda un mensaje, opcionalmente su CV, y el agente le va pidiendo
lo que falta hasta poder calificarlo. Es el canal que más sentido tiene en este
rubro: el operario ya está en WhatsApp, no va a abrir un formulario web.

**La máquina de estados es determinista; la IA solo entiende y redacta.** Es la
misma separación que en el scoring, y por la misma razón: una conversación que
decide con un modelo puede perderse, repetir preguntas o dar por buenos datos
que nadie dijo. Acá el modelo traduce "la saqué en marzo del 27" a una fecha, y
escribe la pregunta de forma humana; qué preguntar y cuándo terminar lo decide
el código.

Sin ANTHROPIC_API_KEY el agente igual funciona: usa los parsers de reglas y las
preguntas fijas. Habla más seco, pero completa la postulación.
"""
from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any

from core.domain import Campo, Escolaridad, Origen, Perfil, TipoLicencia, Unidad
from core.extraccion import MODELO, extraer, texto_de_pdf

UMBRAL_DUDOSO = 0.75


class Estado(str, Enum):
    INICIO = "inicio"
    ESPERANDO_CV = "esperando_cv"
    PREGUNTANDO = "preguntando"
    CONFIRMANDO = "confirmando"
    CERRADA = "cerrada"


@dataclass
class Pregunta:
    campo: str
    texto: str
    ejemplo: str = ""
    # Si el candidato no contesta esto, no se lo puede calificar.
    obligatoria: bool = True
    # Que contestar cuando la respuesta no sirve. Decir *que* falta convierte
    # un "no te entendi" en algo que la persona puede arreglar sola.
    reproche: str = ""


# El orden importa: primero lo que descalifica. Si alguien no tiene licencia
# federal no tiene sentido preguntarle por el sueldo pretendido.
PREGUNTAS: list[Pregunta] = [
    Pregunta("nombre", "¿Cómo te llamas? Dime tu **nombre completo**, como aparece en tu licencia.",
             "Ricardo Salinas Treviño",
             reproche="Necesito tu nombre completo, con apellido. Solo el nombre de "
                      "pila no me alcanza para registrarte."),
    Pregunta("licencias", "¿Qué licencia tienes vigente? Dime si es federal o estatal y de qué tipo.",
             "Federal tipo E",
             reproche="Me falta saber si es **federal** o **estatal**, y el tipo "
                      "(de la A a la E)."),
    Pregunta("licencia_vence", "¿Cuándo se te vence la licencia?", "15/03/2028",
             reproche="Necesito la fecha de vencimiento. Con el mes y el año me alcanza."),
    Pregunta("apto_medico_vence", "¿Hasta cuándo tienes vigente tu apto médico?", "20/07/2027",
             reproche="Necesito hasta cuándo está vigente. Con el mes y el año me alcanza."),
    Pregunta("anios_experiencia", "¿Cuántos años llevas manejando?", "9",
             reproche="Dime nada más el número de años manejando."),
    Pregunta("unidades", "¿Qué unidades has manejado?", "Tractocamión y full",
             reproche="Dime cuáles: tractocamión, full, tortón, rabón, camioneta, "
                      "autobús o roll off."),
    Pregunta("disponibilidad_foranea", "¿Puedes hacer viajes foráneos?", "Sí",
             reproche="Contéstame sí o no: ¿puedes salir a carretera varios días?"),
    Pregunta("escolaridad", "¿Hasta qué grado estudiaste?", "Secundaria",
             reproche="Dime hasta dónde llegaste: primaria, secundaria, preparatoria, "
                      "técnica o universidad."),
    Pregunta("municipio", "¿En qué municipio vives?", "Apodaca",
             reproche="Dime el municipio donde vives."),
    Pregunta("salario_pretendido", "¿Cuánto esperas ganar al mes?", "21000",
             obligatoria=False),
    Pregunta("materiales_peligrosos", "¿Has manejado materiales peligrosos?", "No",
             obligatoria=False),
    Pregunta("telefono", "¿A qué número te contactamos? Si es este mismo, dime que sí.",
             "81 1234 5678", obligatoria=False),
]

POR_CAMPO = {p.campo: p for p in PREGUNTAS}

SALUDO = (
    "¡Hola! Soy el asistente de {empresa}. Estamos contratando "
    "**{puesto}** en {municipio}, N.L., de ${salario_min:,} a ${salario_max:,} al mes.\n\n"
    "Si quieres postularte, mándame tu CV en PDF y yo lleno todo por ti. "
    "Si no lo tienes a mano, no hay problema: te hago unas preguntas cortas."
)

CIERRE_OK = (
    "¡Listo, {nombre}! Ya quedó tu postulación para {puesto}.\n\n"
    "Vamos a revisar tus datos y te contactamos por acá. Gracias por escribirnos."
)


# --- Interpretación de respuestas ---------------------------------------------

def _plano(texto: str) -> str:
    sin = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in sin if not unicodedata.combining(c)).lower().strip()


def _si_o_no(texto: str) -> bool | None:
    p = _plano(texto)
    if re.search(r"\b(si|sip|claro|por supuesto|obvio|afirmativo|sale|va|correcto|asi es)\b", p):
        return True
    if re.search(r"\b(no|nop|negativo|nunca|jamas)\b", p):
        return False
    return None


def _fecha(texto: str) -> date | None:
    p = _plano(texto)
    if m := re.search(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})", p):
        d, mes, a = (int(x) for x in m.groups())
        a = a + 2000 if a < 100 else a
        try:
            return date(a, mes, d)
        except ValueError:
            return None
    meses = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
             "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
             "noviembre": 11, "diciembre": 12}
    # "15 de marzo del 2028", "marzo de 2028", "en marzo 2028": la gente
    # contesta fechas hablando, no en formato.
    if m := re.search(r"(?:(\d{1,2})\s*(?:de|del)?\s+)?([a-z]+)\s+(?:de|del)?\s*(\d{4})", p):
        dia, nombre, anio = m.group(1), m.group(2), int(m.group(3))
        if nombre in meses:
            try:
                return date(anio, meses[nombre], int(dia) if dia else 1)
            except ValueError:
                return None
    return None


def _licencias(texto: str) -> list[str] | None:
    p = _plano(texto)
    federal = bool(re.search(r"federal|sict|sct", p))
    estatal = bool(re.search(r"estatal|del estado|de nuevo leon|nl\b", p))
    letras = re.findall(r"\b(?:tipo|categoria|cat\.?|clase)?\s*([a-f])\b", p)
    if not letras:
        return None
    familia = "federal" if federal or not estatal else "estatal"
    validas = {t.value for t in TipoLicencia}
    encontradas = [f"{familia}_{x.upper()}" for x in letras]
    return sorted({x for x in encontradas if x in validas}) or None


def _unidades(texto: str) -> list[str] | None:
    p = _plano(texto)
    sinonimos = {
        "full": ["full", "doble", "doblemente articulado"],
        "tractocamion": ["tractocamion", "tracto", "quinta rueda", "trailer", "traila"],
        "torton": ["torton"],
        "rabon": ["rabon"],
        "camioneta": ["camioneta", "pick up", "pickup"],
        "autobus": ["autobus", "camion de pasajeros"],
        "roll_off": ["roll off", "rolloff"],
    }
    halladas = [clave for clave, palabras in sinonimos.items()
                if any(x in p for x in palabras)]
    return sorted(halladas) or None


def _escolaridad(texto: str) -> str | None:
    p = _plano(texto)
    for nivel, palabras in (
        ("universidad", ["universidad", "licenciatura", "ingenieria"]),
        ("tecnica", ["tecnica", "tecnico", "conalep", "cbtis"]),
        ("preparatoria", ["preparatoria", "prepa", "bachillerato"]),
        ("secundaria", ["secundaria", "secu"]),
        ("primaria", ["primaria"]),
        ("ninguna", ["ninguna", "no estudie", "nada"]),
    ):
        if any(x in p for x in palabras):
            return nivel
    return None


def _numero(texto: str) -> float | None:
    p = _plano(texto).replace(",", "")
    letras = {"uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6,
              "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "quince": 15, "veinte": 20}
    for palabra, valor in letras.items():
        if re.search(rf"\b{palabra}\b", p):
            return float(valor)
    if m := re.search(r"(\d+(?:\.\d+)?)", p):
        n = float(m.group(1))
        # "unos 20 mil", "20k": la gente habla en miles cuando dice el sueldo.
        if n < 1000 and re.search(r"\bmil\b|\d\s*k\b", p):
            n *= 1000
        return n
    return None


# Palabras que aparecen cuando alguien contesta cualquier cosa menos su nombre.
_NO_NOMBRE = {
    "si", "no", "hola", "buenas", "ok", "listo", "gracias", "que", "onda",
    "trabajo", "vacante", "empleo", "chofer", "operador", "licencia", "cv",
    "curriculum", "sabe", "acuerdo", "ahorita", "luego", "despues", "ya",
    "pues", "aqui", "usted", "senor", "amigo", "jefe", "nada", "idea",
    # Verbos con los que la gente contesta otra cosa: "vivo en Monterrey".
    "vivo", "radico", "resido", "estoy", "vengo", "busco", "quiero",
    "necesito", "tengo", "manejo", "en",
}
# Un nombre no empieza con una preposicion: "de Monterrey" es un domicilio.
_ARRANQUE_INVALIDO = {"de", "del", "la", "el", "en", "y", "mi", "un", "una",
                      "los", "las", "por", "para", "con"}


def _nombre(texto: str) -> str | None:
    """Nombre completo o nada.

    Un "Martin" pelado no sirve: el legajo queda sin apellido, el reclutador no
    puede buscarlo ni cotejarlo contra la licencia, y dos Martines distintos son
    indistinguibles en el tablero. Se exige al menos nombre y un apellido, que
    es lo minimo con lo que se identifica a una persona.
    """
    limpio = re.sub(r"^\s*(me\s+llamo|mi\s+nombre\s+es|yo\s+soy|soy|me\s+dicen)\s+",
                    "", texto or "", flags=re.IGNORECASE)
    # Fuera numeros, emojis y puntuacion: lo que queda tienen que ser palabras.
    limpio = re.sub(r"[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ'\- ]", " ", limpio)
    palabras = [p for p in limpio.split() if len(p) >= 2]
    if not 2 <= len(palabras) <= 6:
        return None
    if _plano(palabras[0]) in _ARRANQUE_INVALIDO:
        return None
    if any(_plano(p) in _NO_NOMBRE for p in palabras):
        return None
    return " ".join(palabras)


def _evasiva(texto: str) -> bool:
    """"No se", "luego te digo": es una respuesta, pero no es un dato.

    Se distingue de "no te entendi" porque amerita otra contestacion: la persona
    entendio la pregunta, lo que no tiene es el dato a mano.
    """
    return bool(re.search(
        r"\bno\s+(se|sabria|recuerdo|estoy\s+seguro)\b|\bno\s+me\s+acuerdo\b"
        r"|\bni\s+idea\b|\bdespues\b|\bluego\b|\bal\s+rato\b"
        r"|\bahorita\s+no\b|\bmas\s+tarde\b|\bte\s+(digo|aviso|paso)\b",
        _plano(texto)))


def _telefono(texto: str) -> str | None:
    digitos = re.sub(r"[^\d]", "", texto or "")
    return texto.strip() if len(digitos) >= 10 else None


def interpretar(campo: str, texto: str) -> Any:
    """Parsers de reglas. Devuelve None si no entendió, y ahí entra la IA."""
    if campo in ("licencia_vence", "apto_medico_vence"):
        return _fecha(texto)
    if campo == "licencias":
        return _licencias(texto)
    if campo == "unidades":
        return _unidades(texto)
    if campo == "escolaridad":
        return _escolaridad(texto)
    if campo in ("disponibilidad_foranea", "materiales_peligrosos"):
        return _si_o_no(texto)
    if campo == "anios_experiencia":
        n = _numero(texto)
        return n if n is not None and 0 <= n <= 60 else None
    if campo == "salario_pretendido":
        n = _numero(texto)
        return int(n) if n is not None and n >= 1000 else None
    if campo == "telefono":
        return _telefono(texto)
    if campo == "municipio":
        # "vivo en Escobedo" es Escobedo, no "vivo en Escobedo". Nadie contesta
        # un municipio pelado.
        limpio = re.sub(
            r"^(yo\s+)?(vivo|radico|estoy|soy|resido)\s+(en|de)\s+|^en\s+|^de\s+",
            "", texto.strip(), flags=re.IGNORECASE).strip(" .,")
        return limpio if 2 <= len(limpio) <= 120 else None
    if campo == "nombre":
        return _nombre(texto)
    return None


INSTRUCCION_IA = """Convertís la respuesta de un conductor mexicano en un valor.

Campo: {campo}
Formato esperado: {formato}

Devolvé SOLO el valor en JSON, sin explicaciones. Si la respuesta no contesta la
pregunta (dice "no sé", cambia de tema, pregunta algo), devolvé null. Una
respuesta a medias también es null: no completes lo que la persona no dijo. No
inventes: un null hace que el agente vuelva a preguntar, y eso es mucho mejor
que un dato falso en el legajo."""

FORMATOS = {
    "licencias": 'lista como ["federal_E"]; categorías A-F, familia federal o estatal',
    "licencia_vence": '"AAAA-MM-DD"',
    "apto_medico_vence": '"AAAA-MM-DD"',
    "anios_experiencia": "número",
    "unidades": 'lista de: camioneta, rabon, torton, tractocamion, full, autobus, roll_off',
    "escolaridad": "ninguna, primaria, secundaria, preparatoria, tecnica o universidad",
    "disponibilidad_foranea": "true o false",
    "materiales_peligrosos": "true o false",
    "salario_pretendido": "entero en pesos mexicanos por mes",
    "nombre": ("nombre completo: nombre de pila y al menos un apellido. "
               "Si solo dijo el nombre de pila, devolvé null"),
    "municipio": "texto, solo el municipio",
    "telefono": "texto",
}


def interpretar_con_ia(campo: str, texto: str) -> Any:
    import json

    from anthropic import Anthropic

    cliente = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    respuesta = cliente.messages.create(
        model=MODELO,
        max_tokens=300,
        system=INSTRUCCION_IA.format(campo=campo, formato=FORMATOS.get(campo, "texto")),
        messages=[{"role": "user", "content": texto}],
    )
    crudo = "".join(b.text for b in respuesta.content if b.type == "text").strip()
    crudo = re.sub(r"^```[a-z]*\n|\n```$", "", crudo)
    return _validar(campo, json.loads(crudo))


# Qué tipo tiene que tener cada campo. El modelo a veces devuelve
# {"telefono": null} en vez del valor pelado, y sin esta verificación ese dict
# viajaba hasta el INSERT y tiraba la postulación entera.
_TIPOS: dict[str, type | tuple] = {
    "licencias": list, "unidades": list,
    "disponibilidad_foranea": bool, "materiales_peligrosos": bool,
    "anios_experiencia": (int, float), "salario_pretendido": (int, float),
    "nombre": str, "municipio": str, "telefono": str, "escolaridad": str,
}


def _validar(campo: str, valor: Any) -> Any:
    """Nada entra al perfil sin tener la forma que el scoring espera."""
    if valor is None:
        return None
    # El modelo envolvió la respuesta: {"telefono": "..."} en vez de "...".
    if isinstance(valor, dict):
        if campo in valor:
            return _validar(campo, valor[campo])
        if len(valor) == 1:
            return _validar(campo, next(iter(valor.values())))
        return None

    if campo in ("licencia_vence", "apto_medico_vence"):
        try:
            return date.fromisoformat(str(valor)[:10])
        except ValueError:
            return None

    esperado = _TIPOS.get(campo)
    if esperado and not isinstance(valor, esperado):
        return None
    # El nombre pasa por el mismo filtro venga de donde venga: si la IA
    # devuelve "Martin" a secas, tampoco entra.
    if campo == "nombre":
        return _nombre(str(valor))
    if campo == "salario_pretendido":
        return int(valor)
    if campo == "anios_experiencia":
        return float(valor)
    if campo in ("licencias", "unidades"):
        return [str(x) for x in valor] or None
    if isinstance(valor, str) and not valor.strip():
        return None
    return valor


def entender(campo: str, texto: str) -> Any:
    """Reglas primero, IA después. Las reglas cubren el 90% y son gratis."""
    valor = _validar(campo, interpretar(campo, texto))
    if valor is not None:
        return valor
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None
    try:
        return interpretar_con_ia(campo, texto)
    except Exception:
        return None


# --- La conversación ----------------------------------------------------------

@dataclass
class Respuesta:
    """Lo que el agente devuelve tras procesar un mensaje."""
    mensajes: list[str] = field(default_factory=list)
    estado: Estado = Estado.PREGUNTANDO
    perfil: Perfil = field(default_factory=Perfil)
    pendientes: list[str] = field(default_factory=list)
    # Campos opcionales que la persona no contestó: no se vuelven a preguntar.
    omitidos: list[str] = field(default_factory=list)
    # Cuando la conversación termina, el llamador crea la postulación.
    listo_para_postular: bool = False


def campos_que_faltan(perfil: Perfil, omitidos: "list[str] | None" = None) -> list[str]:
    """Qué preguntar: solo lo que no tenemos.

    Lo que la IA leyó con poca confianza NO se vuelve a preguntar de a uno: se
    muestra marcado en el resumen y la persona confirma todo junto. Por
    WhatsApp, hacerle doce preguntas a alguien que ya mandó el CV es la mejor
    forma de que abandone la conversación a la tercera.
    """
    fuera = set(omitidos or ())
    return [p.campo for p in PREGUNTAS
            if p.campo not in fuera and getattr(perfil, p.campo).falta]


def campos_dudosos(perfil: Perfil) -> list[str]:
    """Lo que la IA leyó sin seguridad. Va marcado en el resumen."""
    return [p.campo for p in PREGUNTAS
            if not getattr(perfil, p.campo).falta
            and getattr(perfil, p.campo).origen == Origen.CV
            and getattr(perfil, p.campo).confianza < UMBRAL_DUDOSO]


def _legible(campo: str, valor: Any) -> str:
    if valor is None:
        return "—"
    if campo == "anios_experiencia":
        return f"{float(valor):g}"   # 8, no 8.0
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    if isinstance(valor, date):
        return f"{valor:%d/%m/%Y}"
    if isinstance(valor, list):
        return ", ".join(str(x).replace("_", " ") for x in valor)
    if campo == "salario_pretendido":
        return f"${int(valor):,} MXN"
    return str(valor)


ETIQUETAS = {
    "nombre": "Nombre completo", "licencias": "Licencia", "licencia_vence": "Vence",
    "apto_medico_vence": "Apto médico", "anios_experiencia": "Experiencia",
    "unidades": "Unidades", "disponibilidad_foranea": "Viajes foráneos",
    "escolaridad": "Estudios", "municipio": "Municipio",
    "salario_pretendido": "Sueldo esperado",
    "materiales_peligrosos": "Materiales peligrosos",
    "telefono": "Teléfono",
}


def resumen(perfil: Perfil, omitidos: "list[str] | None" = None) -> str:
    """El legajo entero, para que la persona lo confirme de una.

    Se listan TODOS los campos, también los que quedaron sin dato: un resumen
    que solo muestra lo que tenemos deja que alguien confirme un legajo al que
    le falta la mitad sin enterarse. Lo que falta se ve, y se puede completar
    en el mismo mensaje.
    """
    dudosos = set(campos_dudosos(perfil))
    fuera = set(omitidos or ())
    lineas = ["Esto es lo que tengo. Revísalo completo, por favor.", ""]
    sin_dato = []
    for campo, etiqueta in ETIQUETAS.items():
        dato: Campo = getattr(perfil, campo)
        if dato.falta:
            # El teléfono no falta cuando la persona dijo "este mismo": es el
            # número desde el que está escribiendo.
            if campo == "telefono" and campo in fuera:
                lineas.append("· Teléfono: el número de este chat")
                continue
            sin_dato.append(etiqueta)
            lineas.append(f"· {etiqueta}: — (sin dato)")
            continue
        sufijo = " años" if campo == "anios_experiencia" else ""
        # Lo que salió del CV sin seguridad se marca, para que la persona lo
        # mire dos veces antes de dar todo por bueno.
        marca = "  ← revísalo" if campo in dudosos else ""
        lineas.append(f"· {etiqueta}: {_legible(campo, dato.valor)}{sufijo}{marca}")
    lineas.append("")
    if dudosos:
        lineas.append("Lo marcado con ← lo leí de tu CV y no estoy seguro de "
                      "haberlo entendido bien.")
    if sin_dato:
        lineas.append(f"Sin dato: {', '.join(sin_dato).lower()}. Si me los dices, "
                      "los agrego.")
    lineas.append('Si algo está mal o falta, dime qué cambio. Si está todo '
                  'bien, responde "sí".')
    return "\n".join(lineas)


def _pregunta_de(campo: str) -> str:
    p = POR_CAMPO[campo]
    return f"{p.texto}" + (f"\n_Por ejemplo: {p.ejemplo}_" if p.ejemplo else "")


def repregunta(campo: str, texto: str) -> list[str]:
    """Que contestar cuando la respuesta no sirve.

    Tres casos distintos, tres respuestas distintas: la persona se escapó por
    la tangente, contestó a medias, o dijo algo que no entendimos. Un
    "perdón, no te entendí" para los tres deja a la gente adivinando.
    """
    p = POR_CAMPO[campo]
    if _evasiva(texto):
        return [f"Ese dato lo necesito para poder registrarte, no lo puedo "
                f"dejar en blanco. Si lo tienes que checar, lo vemos cuando lo "
                f"tengas a mano.",
                _pregunta_de(campo)]
    if p.reproche:
        # El motivo ya contiene la pregunta: repetirla entera suena a robot
        # trabado. Lo que se repite es el ejemplo, que es lo que destraba.
        ejemplo = f"\n_Por ejemplo: {p.ejemplo}_" if p.ejemplo else ""
        return [p.reproche + ejemplo]
    return ["Perdón, no te entendí.", _pregunta_de(campo)]


def _campo_mencionado(texto: str) -> str | None:
    """Para cuando el candidato corrige algo del resumen."""
    p = _plano(texto)
    pistas = {
        "licencias": ["licencia"], "licencia_vence": ["vence la licencia", "vencimiento"],
        "apto_medico_vence": ["apto", "medico"], "anios_experiencia": ["experiencia", "anios", "años"],
        "unidades": ["unidad", "manejo", "torton", "tracto", "full"],
        "disponibilidad_foranea": ["foran", "viaje"], "escolaridad": ["estudi", "secundaria", "prepa"],
        "municipio": ["municipio", "vivo", "domicilio"], "salario_pretendido": ["sueldo", "salario", "gano"],
        "materiales_peligrosos": ["peligros"], "nombre": ["nombre", "llamo"],
        "telefono": ["telefono", "numero", "celular"],
    }
    for campo, palabras in pistas.items():
        if any(x in p for x in palabras):
            return campo
    return None


class Agente:
    """Sin estado propio: recibe la conversación, devuelve la siguiente respuesta.

    El estado vive en la base y no en el objeto, porque WhatsApp es asincrónico:
    la persona puede contestar tres horas después y el proceso puede haberse
    reiniciado en el medio.
    """

    def __init__(self, vacante_titulo: str, municipio: str, salario_min: int,
                 salario_max: int, empresa: str = "Transportes del Norte"):
        self.vacante_titulo = vacante_titulo
        self.municipio = municipio
        self.salario_min = salario_min
        self.salario_max = salario_max
        self.empresa = empresa

    def saludo(self) -> str:
        return SALUDO.format(empresa=self.empresa, puesto=self.vacante_titulo,
                             municipio=self.municipio, salario_min=self.salario_min,
                             salario_max=self.salario_max)

    def procesar(self, estado: Estado, perfil: Perfil, texto: str = "",
                 archivo: bytes | None = None, nombre_archivo: str = "",
                 omitidos: list[str] | None = None) -> Respuesta:
        """Fachada del grafo de LangGraph.

        La conversación vive en core/grafo_whatsapp.py; esto solo traduce a los
        tipos del dominio. Se importa acá adentro para no cerrar un círculo:
        el grafo usa los parsers de este módulo.
        """
        from core.grafo_whatsapp import procesar as procesar_grafo

        salida = procesar_grafo(
            vacante={
                "titulo": self.vacante_titulo, "municipio": self.municipio,
                "salario_min": self.salario_min, "salario_max": self.salario_max,
                "empresa": self.empresa,
            },
            etapa=Estado(estado).value, perfil=perfil, texto=texto,
            archivo=archivo, nombre_archivo=nombre_archivo, omitidos=omitidos,
        )
        return Respuesta(
            mensajes=salida["mensajes"],
            estado=Estado(salida["etapa"]),
            perfil=salida["perfil"],
            pendientes=salida["pendientes"],
            omitidos=salida["omitidos"],
            listo_para_postular=salida["listo_para_postular"],
        )
