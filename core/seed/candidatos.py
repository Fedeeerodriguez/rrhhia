"""15 candidatos de prueba, calibrados a proposito contra la vacante.

Cada uno existe para probar una rama distinta del motor: el que cumple todo,
el que tiene la licencia vencida, el que tiene la estatal pero no la federal,
el que rota de empresa cada ocho meses, el que no informa datos. La columna
`esperado` es el contrato del motor y lo que verifican los tests.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from core.domain import Campo, Empleo, Perfil

HOY = date.today()


def _d(dias: int) -> date:
    return HOY + timedelta(days=dias)


def _empleos(*tramos: tuple[str, str, int, int | None]) -> list[Empleo]:
    """(empresa, puesto, dias_desde_hoy_inicio, dias_desde_hoy_fin)."""
    return [
        Empleo(empresa=e, puesto=p, desde=_d(ini), hasta=_d(fin) if fin is not None else None)
        for e, p, ini, fin in tramos
    ]


def perfil(**datos) -> Perfil:
    """Construye un perfil como si viniera del formulario: todo confianza 1.0."""
    p = Perfil()
    for clave, valor in datos.items():
        if not hasattr(p, clave):
            raise KeyError(f"Campo desconocido en el perfil: {clave}")
        setattr(p, clave, Campo.del_formulario(valor))
    return p


@dataclass
class CandidatoSeed:
    id: str
    nota: str          # por que existe este candidato en el set
    esperado: str      # "top" | "medio" | "descartado"
    perfil: Perfil


CANDIDATOS: list[CandidatoSeed] = [
    CandidatoSeed(
        id="ricardo-salinas-trevino",
        nota="Cumple todo y con holgura. Es el techo del set.",
        esperado="top",
        perfil=perfil(
            nombre="Ricardo Salinas Trevino", telefono="81 1234 5678",
            email="r.salinas.trevino@gmail.com", municipio="Apodaca",
            licencias=["federal_E", "estatal_C"], licencia_vence=_d(540),
            apto_medico_vence=_d(300), anios_experiencia=9,
            unidades=["tractocamion", "full", "torton"], escolaridad="secundaria",
            disponibilidad_foranea=True, salario_pretendido=22000,
            materiales_peligrosos=True,
            historial=_empleos(
                ("Transportes del Norte SA", "Operador full", -2900, -1100),
                ("Fletes Regiomontanos", "Operador tractocamion", -1080, None),
            ),
        ),
    ),
    CandidatoSeed(
        id="marco-antonio-villarreal",
        nota="Muy fuerte, pero sin materiales peligrosos. Debe quedar detras de Ricardo.",
        esperado="top",
        perfil=perfil(
            nombre="Marco Antonio Villarreal", telefono="81 2345 6789",
            email="mavillarreal78@hotmail.com", municipio="Guadalupe",
            licencias=["federal_E"], licencia_vence=_d(400),
            apto_medico_vence=_d(250), anios_experiencia=7,
            unidades=["tractocamion", "full"], escolaridad="preparatoria",
            disponibilidad_foranea=True, salario_pretendido=21000,
            materiales_peligrosos=False,
            historial=_empleos(
                ("Autolineas Mexicanas", "Operador", -2600, -900),
                ("Grupo Kasto", "Operador tractocamion", -880, None),
            ),
        ),
    ),
    CandidatoSeed(
        id="jorge-luis-cavazos",
        nota="Federal E, buena experiencia, vive en zona. Solido.",
        esperado="top",
        perfil=perfil(
            nombre="Jorge Luis Cavazos", telefono="81 3456 7890",
            email="jlcavazos@gmail.com", municipio="Santa Catarina",
            licencias=["federal_E", "estatal_C"], licencia_vence=_d(210),
            apto_medico_vence=_d(150), anios_experiencia=6,
            unidades=["tractocamion", "full"], escolaridad="secundaria",
            disponibilidad_foranea=True, salario_pretendido=23000,
            materiales_peligrosos=True,
            historial=_empleos(
                ("Transportes Tamaulipas", "Operador full", -2200, -700),
                ("Logistica Monterrey", "Operador", -690, None),
            ),
        ),
    ),
    CandidatoSeed(
        id="miguel-angel-rodriguez",
        nota="Federal B (no E) y sin full. Cumple todo, pero techo mas bajo.",
        esperado="medio",
        perfil=perfil(
            nombre="Miguel Angel Rodriguez", telefono="81 4567 8901",
            email="miguelangel.rdz@gmail.com", municipio="General Escobedo",
            licencias=["federal_B"], licencia_vence=_d(320),
            apto_medico_vence=_d(180), anios_experiencia=5,
            unidades=["tractocamion", "torton"], escolaridad="secundaria",
            disponibilidad_foranea=True, salario_pretendido=20000,
            materiales_peligrosos=False,
            historial=_empleos(
                ("Distribuidora del Golfo", "Operador torton", -2000, -600),
                ("Transportes Villa", "Operador tractocamion", -590, None),
            ),
        ),
    ),
    CandidatoSeed(
        id="omar-de-la-garza",
        nota="Cumple lo minimo pero pide 28 mil, muy arriba del tope de 23 mil.",
        esperado="medio",
        perfil=perfil(
            nombre="Omar de la Garza", telefono="81 5678 9012",
            email="omardelagarza@outlook.com", municipio="Monterrey",
            licencias=["federal_B"], licencia_vence=_d(600),
            apto_medico_vence=_d(400), anios_experiencia=3,
            unidades=["torton", "tractocamion"], escolaridad="preparatoria",
            disponibilidad_foranea=True, salario_pretendido=28000,
            materiales_peligrosos=False,
            historial=_empleos(
                ("Paqueteria Express NL", "Chofer", -1400, -400),
                ("Transportes Anahuac", "Operador", -390, None),
            ),
        ),
    ),
    CandidatoSeed(
        id="juan-carlos-martinez",
        nota="8 anios de oficio pero 6 empleos en 5 anios: la rotacion lo baja.",
        esperado="medio",
        perfil=perfil(
            nombre="Juan Carlos Martinez", telefono="81 6789 0123",
            email="jcmartinez.operador@gmail.com", municipio="Juarez",
            licencias=["federal_B"], licencia_vence=_d(280),
            apto_medico_vence=_d(120), anios_experiencia=8,
            unidades=["tractocamion", "torton", "rabon"], escolaridad="secundaria",
            disponibilidad_foranea=True, salario_pretendido=19000,
            materiales_peligrosos=False,
            historial=_empleos(
                ("Fletes Unidos", "Operador", -1750, -1500),
                ("Transportes Sierra", "Operador", -1480, -1200),
                ("Carga Express MTY", "Operador", -1180, -900),
                ("Grupo Logistico RG", "Operador", -880, -560),
                ("Transportes Milenio", "Operador", -540, -200),
                ("Autotransportes Cima", "Operador", -180, None),
            ),
        ),
    ),
    CandidatoSeed(
        id="alberto-nieto-cantu",
        nota="Cumple todo pero vive en Saltillo, fuera de la zona de operacion.",
        esperado="medio",
        perfil=perfil(
            nombre="Alberto Nieto Cantu", telefono="84 4321 0987",
            email="anietocantu@gmail.com", municipio="Saltillo",
            licencias=["federal_B"], licencia_vence=_d(450),
            apto_medico_vence=_d(200), anios_experiencia=2.5,
            unidades=["tractocamion"], escolaridad="secundaria",
            disponibilidad_foranea=True, salario_pretendido=19500,
            materiales_peligrosos=False,
            historial=_empleos(
                ("Transportes Coahuila", "Operador", -1300, -300),
                ("Fletes del Sureste", "Operador", -290, None),
            ),
        ),
    ),
    CandidatoSeed(
        id="hector-ramirez-solis",
        nota="KNOCKOUT: perfil excelente pero la licencia federal esta vencida.",
        esperado="descartado",
        perfil=perfil(
            nombre="Hector Ramirez Solis", telefono="81 7890 1234",
            email="hramirezsolis@gmail.com", municipio="Apodaca",
            licencias=["federal_E"], licencia_vence=_d(-45),
            apto_medico_vence=_d(90), anios_experiencia=11,
            unidades=["tractocamion", "full"], escolaridad="secundaria",
            disponibilidad_foranea=True, salario_pretendido=22000,
            materiales_peligrosos=True,
            historial=_empleos(
                ("Transportes Castores", "Operador full", -3200, -800),
                ("Fletes Regiomontanos", "Operador", -780, None),
            ),
        ),
    ),
    CandidatoSeed(
        id="jose-antonio-pena",
        nota="KNOCKOUT: 10 anios de torton pero solo licencia estatal tipo C de NL.",
        esperado="descartado",
        perfil=perfil(
            nombre="Jose Antonio Pena", telefono="81 8901 2345",
            email="japena.torton@gmail.com", municipio="Monterrey",
            licencias=["estatal_C"], licencia_vence=_d(500),
            apto_medico_vence=_d(220), anios_experiencia=10,
            unidades=["torton", "rabon"], escolaridad="secundaria",
            disponibilidad_foranea=True, salario_pretendido=20000,
            materiales_peligrosos=False,
            historial=_empleos(
                ("Materiales del Norte", "Chofer torton", -3000, -1000),
                ("Constructora Regia", "Chofer torton", -980, None),
            ),
        ),
    ),
    CandidatoSeed(
        id="gerardo-elizondo",
        nota="KNOCKOUT: 12 anios y licencia E vigente, pero apto medico vencido.",
        esperado="descartado",
        perfil=perfil(
            nombre="Gerardo Elizondo", telefono="81 9012 3456",
            email="gelizondo12@hotmail.com", municipio="San Nicolas de los Garza",
            licencias=["federal_E"], licencia_vence=_d(360),
            apto_medico_vence=_d(-20), anios_experiencia=12,
            unidades=["tractocamion", "full"], escolaridad="secundaria",
            disponibilidad_foranea=True, salario_pretendido=23000,
            materiales_peligrosos=True,
            historial=_empleos(
                ("Transportes Julian", "Operador full", -3600, -1200),
                ("Grupo TUM", "Operador", -1180, None),
            ),
        ),
    ),
    CandidatoSeed(
        id="raul-eduardo-ibarra",
        nota="KNOCKOUT: buen operador local pero NO acepta viajes foraneos.",
        esperado="descartado",
        perfil=perfil(
            nombre="Raul Eduardo Ibarra", telefono="81 0123 4567",
            email="ribarra.mty@gmail.com", municipio="Guadalupe",
            licencias=["federal_B"], licencia_vence=_d(330),
            apto_medico_vence=_d(160), anios_experiencia=5,
            unidades=["tractocamion", "torton"], escolaridad="preparatoria",
            disponibilidad_foranea=False, salario_pretendido=20000,
            materiales_peligrosos=False,
            historial=_empleos(
                ("Distribuciones Guadalupe", "Operador local", -1900, -500),
                ("Abarrotera del Norte", "Operador", -490, None),
            ),
        ),
    ),
    CandidatoSeed(
        id="sergio-alonso-garza",
        nota="KNOCKOUT por escolaridad: primaria, se pide secundaria terminada.",
        esperado="descartado",
        perfil=perfil(
            nombre="Sergio Alonso Garza", telefono="81 1122 3344",
            email="sergiogarza74@gmail.com", municipio="Garcia",
            licencias=["federal_B"], licencia_vence=_d(290),
            apto_medico_vence=_d(140), anios_experiencia=4,
            unidades=["torton", "tractocamion"], escolaridad="primaria",
            disponibilidad_foranea=True, salario_pretendido=18500,
            materiales_peligrosos=False,
            historial=_empleos(
                ("Transportes Garcia", "Operador", -1600, -450),
                ("Fletera del Poniente", "Operador", -440, None),
            ),
        ),
    ),
    CandidatoSeed(
        id="francisco-javier-luna",
        nota="KNOCKOUT por experiencia: 1 anio, se piden 2. Recuperable a futuro.",
        esperado="descartado",
        perfil=perfil(
            nombre="Francisco Javier Luna", telefono="81 2233 4455",
            email="fjluna.99@gmail.com", municipio="Apodaca",
            licencias=["federal_B"], licencia_vence=_d(700),
            apto_medico_vence=_d(350), anios_experiencia=1,
            unidades=["tractocamion"], escolaridad="preparatoria",
            disponibilidad_foranea=True, salario_pretendido=18000,
            materiales_peligrosos=False,
            historial=_empleos(("Transportes Aguila", "Operador jr", -380, None)),
        ),
    ),
    CandidatoSeed(
        id="daniel-zuniga",
        nota="Datos incompletos: no informa apto medico ni escolaridad. "
             "Prueba que 'no verificable' se muestre distinto de 'no cumple'.",
        esperado="descartado",
        perfil=perfil(
            nombre="Daniel Zuniga", telefono="81 3344 5566",
            municipio="Monterrey",
            licencias=["federal_B"], licencia_vence=_d(240),
            anios_experiencia=3, unidades=["tractocamion", "torton"],
            disponibilidad_foranea=True,
            historial=_empleos(("Transportes del Valle", "Operador", -1100, None)),
        ),
    ),
    CandidatoSeed(
        id="luis-fernando-chapa",
        nota="Fuera de perfil: repartidor en camioneta, sin licencia de carga.",
        esperado="descartado",
        perfil=perfil(
            nombre="Luis Fernando Chapa", telefono="81 4455 6677",
            email="lfchapa@gmail.com", municipio="Monterrey",
            licencias=["estatal_A"], licencia_vence=_d(800),
            apto_medico_vence=_d(-200), anios_experiencia=2,
            unidades=["camioneta"], escolaridad="preparatoria",
            disponibilidad_foranea=False, salario_pretendido=16000,
            materiales_peligrosos=False,
            historial=_empleos(("Paqueteria Rapida", "Repartidor", -730, None)),
        ),
    ),
]


def por_id() -> dict[str, "CandidatoSeed"]:
    return {c.id: c for c in CANDIDATOS}


def perfiles() -> dict[str, Perfil]:
    return {c.id: c.perfil for c in CANDIDATOS}
