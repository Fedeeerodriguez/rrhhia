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
        asunto="Tu postulacion a {puesto} avanzo",
        cuerpo=(
            "Hola {nombre},\n\n"
            "Revisamos tu postulacion para {puesto} en {empresa} y cumples con el "
            "perfil que buscamos. En los proximos dias te contactamos para "
            "coordinar una entrevista.\n\n"
            "Gracias por tu interes.\n{empresa}"
        ),
    ),
    Etapa.ENTREVISTA: Plantilla(
        asunto="Entrevista para {puesto}",
        cuerpo=(
            "Hola {nombre},\n\n"
            "Queremos entrevistarte para el puesto de {puesto}. Respondenos este "
            "mensaje con los dias y horarios que te quedan comodos.\n\n"
            "Traé tu licencia y tu apto medico vigentes.\n\n{empresa}"
        ),
    ),
    Etapa.ACEPTADO: Plantilla(
        asunto="Bienvenido a {empresa}",
        cuerpo=(
            "Hola {nombre},\n\n"
            "Nos alegra confirmarte que quedaste seleccionado para {puesto}. "
            "Te enviamos por separado la lista de documentacion para tu alta.\n\n"
            "Bienvenido al equipo.\n{empresa}"
        ),
    ),
    Etapa.RECHAZADO: Plantilla(
        asunto="Sobre tu postulacion a {puesto}",
        cuerpo=(
            "Hola {nombre},\n\n"
            "Gracias por postularte a {puesto} en {empresa}. En esta ocasion "
            "decidimos avanzar con otros perfiles, pero guardamos tus datos para "
            "futuras busquedas.\n\n"
            "Te deseamos mucho exito.\n{empresa}"
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
