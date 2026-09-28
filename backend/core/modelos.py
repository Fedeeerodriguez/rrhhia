"""Tablas. SQLite en la demo, Postgres cuando haga falta (solo cambia la URL).

El score y su desglose se persisten: si la API se cae durante la presentacion,
todo lo ya procesado se sigue viendo.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (JSON, Boolean, DateTime, Float, ForeignKey, Integer,
                        String, Text)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from core.pipeline import Etapa


class Base(DeclarativeBase):
    pass


class VacanteDB(Base):
    __tablename__ = "vacantes"

    id: Mapped[int] = mapped_column(primary_key=True)
    titulo: Mapped[str] = mapped_column(String(200))
    municipio: Mapped[str] = mapped_column(String(120))
    salario_min: Mapped[int] = mapped_column(Integer)
    salario_max: Mapped[int] = mapped_column(Integer)
    descripcion: Mapped[str] = mapped_column(Text, default="")
    # Los criterios viajan como JSON: asi el reclutador puede armar vacantes
    # nuevas desde la UI sin que nadie toque codigo.
    criterios: Mapped[list] = mapped_column(JSON, default=list)
    creada: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    postulaciones: Mapped[list["PostulacionDB"]] = relationship(
        back_populates="vacante", cascade="all, delete-orphan")


class CandidatoDB(Base):
    __tablename__ = "candidatos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200))
    telefono: Mapped[str] = mapped_column(String(50), default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    creado: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    postulaciones: Mapped[list["PostulacionDB"]] = relationship(
        back_populates="candidato", cascade="all, delete-orphan")


class PostulacionDB(Base):
    __tablename__ = "postulaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    vacante_id: Mapped[int] = mapped_column(ForeignKey("vacantes.id"))
    candidato_id: Mapped[int] = mapped_column(ForeignKey("candidatos.id"))

    # Perfil completo con confianza y fragmento por campo, no aplanado.
    perfil: Mapped[dict] = mapped_column(JSON, default=dict)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    apto: Mapped[bool] = mapped_column(Boolean, default=False)
    desglose: Mapped[list] = mapped_column(JSON, default=list)
    razones: Mapped[list] = mapped_column(JSON, default=list)
    alertas: Mapped[list] = mapped_column(JSON, default=list)

    # Segunda capa: la lectura cualitativa de la IA. Nunca cambia `apto`.
    evaluacion_ia: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    score_final: Mapped[float | None] = mapped_column(Float, nullable=True)

    etapa: Mapped[str] = mapped_column(String(30), default=Etapa.POSTULADO.value)
    sugerencia: Mapped[str] = mapped_column(String(30), default=Etapa.POSTULADO.value)
    motivo_sugerencia: Mapped[str] = mapped_column(String(300), default="")
    origen: Mapped[str] = mapped_column(String(30), default="formulario")
    creada: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    vacante: Mapped[VacanteDB] = relationship(back_populates="postulaciones")
    candidato: Mapped[CandidatoDB] = relationship(back_populates="postulaciones")
    eventos: Mapped[list["EventoDB"]] = relationship(
        back_populates="postulacion", cascade="all, delete-orphan")
    mensajes: Mapped[list["MensajeDB"]] = relationship(
        back_populates="postulacion", cascade="all, delete-orphan")


class EventoDB(Base):
    __tablename__ = "eventos_etapa"

    id: Mapped[int] = mapped_column(primary_key=True)
    postulacion_id: Mapped[int] = mapped_column(ForeignKey("postulaciones.id"))
    desde: Mapped[str] = mapped_column(String(30))
    hacia: Mapped[str] = mapped_column(String(30))
    autor: Mapped[str] = mapped_column(String(120))
    nota: Mapped[str | None] = mapped_column(String(300), nullable=True)
    automatico: Mapped[bool] = mapped_column(Boolean, default=False)
    momento: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    postulacion: Mapped[PostulacionDB] = relationship(back_populates="eventos")


class MensajeDB(Base):
    __tablename__ = "mensajes"

    id: Mapped[int] = mapped_column(primary_key=True)
    postulacion_id: Mapped[int] = mapped_column(ForeignKey("postulaciones.id"))
    destinatario: Mapped[str] = mapped_column(String(200))
    asunto: Mapped[str] = mapped_column(String(300))
    cuerpo: Mapped[str] = mapped_column(Text)
    etapa: Mapped[str] = mapped_column(String(30))
    # En la demo siempre False: los mensajes se ven en la bandeja, no se envian.
    enviado: Mapped[bool] = mapped_column(Boolean, default=False)
    momento: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    postulacion: Mapped[PostulacionDB] = relationship(back_populates="mensajes")


class ConversacionDB(Base):
    """Una conversacion de WhatsApp por numero.

    El estado vive en la base y no en memoria: WhatsApp es asincronico, la
    persona puede contestar tres horas despues y el proceso puede haberse
    reiniciado en el medio.
    """
    __tablename__ = "conversaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    wa_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    vacante_id: Mapped[int] = mapped_column(ForeignKey("vacantes.id"))
    estado: Mapped[str] = mapped_column(String(30), default="inicio")
    perfil: Mapped[dict] = mapped_column(JSON, default=dict)
    historial: Mapped[list] = mapped_column(JSON, default=list)
    # Campos opcionales que la persona decidio no contestar.
    omitidos: Mapped[list] = mapped_column(JSON, default=list)
    postulacion_id: Mapped[int | None] = mapped_column(
        ForeignKey("postulaciones.id"), nullable=True)
    creada: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    actualizada: Mapped[datetime] = mapped_column(DateTime, default=datetime.now,
                                                  onupdate=datetime.now)
