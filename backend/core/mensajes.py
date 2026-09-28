"""Plantillas de aviso al candidato y bandeja de salida.

En la demo NO se envia nada de verdad: los mensajes caen en una bandeja visible
en la UI. Un correo a la direccion equivocada delante del cliente no se arregla.
Cuando esto pase a produccion, se cambia `Bandeja.despachar` por el proveedor
real y nada mas.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from core.pipeline import Etapa


@dataclass
class Plantilla:
    asunto: str
    cuerpo: str

    def render(self, **datos) -> tuple[str, str]:
        faltantes = [k for k in ("nombre", "puesto", "empresa") if k not in datos]
        if faltantes:
            raise KeyError(f"Faltan variables para la plantilla: {faltantes}")
        return self.asunto.format(**datos), self.cuerpo.format(**datos)


PLANTILLAS: dict[Etapa, Plantilla] = {
    Etapa.FILTRADO: Plantilla(
        asunto="Tu postulación a {puesto} avanzó",
        cuerpo=(
            "Hola {nombre},\n\n"
            "Revisamos tu postulación para {puesto} en {empresa} y cumples con el "
            "perfil que buscamos. En los próximos días te contactamos para "
            "coordinar una entrevista.\n\n"
            "Gracias por tu interés.\n{empresa}"
        ),
    ),
    Etapa.ENTREVISTA: Plantilla(
        asunto="Entrevista para {puesto}",
        cuerpo=(
            "Hola {nombre},\n\n"
            "Queremos entrevistarte para el puesto de {puesto}. Respóndenos este "
            "mensaje con los días y horarios que te queden cómodos.\n\n"
            "Trae tu licencia y tu apto médico vigentes.\n\n{empresa}"
        ),
    ),
    Etapa.ACEPTADO: Plantilla(
        asunto="Bienvenido a {empresa}",
        cuerpo=(
            "Hola {nombre},\n\n"
            "Nos alegra confirmarte que quedaste seleccionado para {puesto}. "
            "Te enviamos por separado la lista de documentación para tu alta.\n\n"
            "Bienvenido al equipo.\n{empresa}"
        ),
    ),
    Etapa.RECHAZADO: Plantilla(
        asunto="Sobre tu postulación a {puesto}",
        cuerpo=(
            "Hola {nombre},\n\n"
            "Gracias por postularte a {puesto} en {empresa}. En esta ocasión "
            "decidimos avanzar con otros perfiles, pero guardamos tus datos para "
            "futuras búsquedas.\n\n"
            "Te deseamos mucho éxito.\n{empresa}"
        ),
    ),
}


@dataclass
class Mensaje:
    destinatario: str
    asunto: str
    cuerpo: str
    etapa: Etapa
    momento: datetime = field(default_factory=datetime.now)
    enviado: bool = False       # en la demo siempre queda en False


@dataclass
class Bandeja:
    """Lo que en la UI se ve como la pestania Comunicaciones."""
    mensajes: list[Mensaje] = field(default_factory=list)

    def para_etapa(self, etapa: Etapa, destinatario: str, **datos) -> Mensaje | None:
        """Arma el aviso de una transicion. Devuelve None si esa etapa no avisa
        (pasar a Postulado de vuelta no le manda nada a nadie)."""
        plantilla = PLANTILLAS.get(etapa)
        if plantilla is None:
            return None
        if not destinatario:
            return None
        asunto, cuerpo = plantilla.render(**datos)
        mensaje = Mensaje(destinatario=destinatario, asunto=asunto,
                          cuerpo=cuerpo, etapa=etapa)
        self.mensajes.append(mensaje)
        return mensaje

    def pendientes(self) -> list[Mensaje]:
        return [m for m in self.mensajes if not m.enviado]
