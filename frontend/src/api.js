const BASE = import.meta.env.VITE_API ?? '/api'

async function pedir(ruta, opciones = {}) {
  const r = await fetch(`${BASE}${ruta}`, {
    headers: opciones.body instanceof FormData ? {} : { 'Content-Type': 'application/json' },
    ...opciones,
  })
  if (!r.ok) {
    // El detalle que manda FastAPI es legible para una persona; si no hay,
    // al menos que no quede un "error" pelado en pantalla.
    let detalle = `Error ${r.status}`
    try {
      const cuerpo = await r.json()
      if (cuerpo?.detail) detalle = typeof cuerpo.detail === 'string' ? cuerpo.detail : detalle
    } catch { /* respuesta sin json */ }
    throw new Error(detalle)
  }
  return r.status === 204 ? null : r.json()
}

export const api = {
  vacante: (id = 1) => pedir(`/vacantes/${id}`),
  tablero: (id = 1) => pedir(`/vacantes/${id}/tablero`),
  bandeja: (id = 1) => pedir(`/vacantes/${id}/bandeja`),
  postulacion: (id) => pedir(`/postulaciones/${id}`),

  postular: (datos, id = 1) =>
    pedir(`/vacantes/${id}/postular`, { method: 'POST', body: JSON.stringify(datos) }),

  cargarCvs: (archivos, id = 1) => {
    const forma = new FormData()
    for (const a of archivos) forma.append('archivos', a)
    return pedir(`/vacantes/${id}/cvs`, { method: 'POST', body: forma })
  },

  prellenar: (archivo, id = 1) => {
    const forma = new FormData()
    forma.append('archivo', archivo)
    return pedir(`/vacantes/${id}/prellenar`, { method: 'POST', body: forma })
  },

  confirmar: (campos, id = 1) =>
    pedir(`/vacantes/${id}/confirmar`, { method: 'POST', body: JSON.stringify({ campos }) }),

  corregirCampo: (postulacionId, campo, valor) =>
    pedir(`/postulaciones/${postulacionId}/campo`, {
      method: 'PATCH', body: JSON.stringify({ campo, valor }),
    }),

  mover: (postulacionId, hacia, autor = 'Reclutador') =>
    pedir(`/postulaciones/${postulacionId}/etapa`, {
      method: 'POST', body: JSON.stringify({ hacia, autor }),
    }),

  evaluarIA: (id = 1) =>
    pedir(`/vacantes/${id}/evaluar-ia`, { method: 'POST' }),

  aplicarSugerencias: (id = 1) =>
    pedir(`/vacantes/${id}/aplicar-sugerencias`, { method: 'POST' }),
}

export const ETAPAS = ['postulado', 'filtrado', 'entrevista', 'aceptado', 'rechazado']

export const NOMBRE_ETAPA = {
  postulado: 'Postulados',
  filtrado: 'Filtrados',
  entrevista: 'En entrevista',
  aceptado: 'Aceptados',
  rechazado: 'Rechazados',
}

export const NOMBRE_CAMPO = {
  nombre: 'Nombre', telefono: 'Teléfono', email: 'Correo', municipio: 'Municipio',
  licencias: 'Licencias', licencia_vence: 'Vence la licencia',
  apto_medico_vence: 'Vence el apto médico', anios_experiencia: 'Años de experiencia',
  unidades: 'Unidades manejadas', escolaridad: 'Escolaridad',
  disponibilidad_foranea: 'Viajes foráneos', salario_pretendido: 'Pretensión salarial',
  historial: 'Historial laboral', materiales_peligrosos: 'Materiales peligrosos',
}

export const pesos = (n) =>
  n == null ? '—' : `$${Number(n).toLocaleString('es-MX')}`
