import { useState } from 'react'
import { api, pesos } from '../api.js'
import { Aviso } from './Basicos.jsx'

/* El formulario del candidato. Mobile-first en serio: el conductor lo llena
   desde el teléfono, parado al lado del camión. Ocho bloques, no treinta
   campos, y ningún término que no use él. */

const LICENCIAS = [
  { id: 'federal_E', nombre: 'Federal tipo E', pie: 'Doblemente articulado / peligrosos' },
  { id: 'federal_B', nombre: 'Federal tipo B', pie: 'Carga federal' },
  { id: 'federal_C', nombre: 'Federal tipo C', pie: 'Carga de 2 o 3 ejes' },
  { id: 'federal_A', nombre: 'Federal tipo A', pie: 'Pasajeros' },
  { id: 'estatal_C', nombre: 'Estatal tipo C', pie: 'De Nuevo León' },
  { id: 'estatal_B', nombre: 'Estatal tipo B', pie: 'De Nuevo León' },
]

const UNIDADES = [
  ['full', 'Full'], ['tractocamion', 'Tractocamión'], ['torton', 'Tortón'],
  ['rabon', 'Rabón'], ['roll_off', 'Roll off'], ['camioneta', 'Camioneta'],
]

const ESCOLARIDAD = [
  ['primaria', 'Primaria'], ['secundaria', 'Secundaria'],
  ['preparatoria', 'Preparatoria'], ['tecnica', 'Técnica'], ['universidad', 'Universidad'],
]

const VACIO = {
  nombre: '', telefono: '', email: '', municipio: '',
  licencias: [], licencia_vence: '', apto_medico_vence: '',
  anios_experiencia: '', unidades: [], escolaridad: '',
  disponibilidad_foranea: null, salario_pretendido: '', materiales_peligrosos: null,
}

function Opcion({ activa, onClick, children, pie }) {
  return (
    <button
      type="button" onClick={onClick}
      className={`rounded-2xl border px-3.5 py-2.5 text-left transition-all duration-200 active:scale-[0.98]
        ${activa ? 'border-acento bg-acento-50 text-acento' : 'border-borde bg-superficie hover:border-piedra-300'}`}
    >
      <span className="block text-[13px] font-medium">{children}</span>
      {pie && <span className="block text-[11px] opacity-60">{pie}</span>}
    </button>
  )
}

function SiNo({ valor, onCambiar }) {
  return (
    <div className="flex gap-2">
      <Opcion activa={valor === true} onClick={() => onCambiar(true)}>Sí</Opcion>
      <Opcion activa={valor === false} onClick={() => onCambiar(false)}>No</Opcion>
    </div>
  )
}

export default function FormularioPublico({ vacante, onListo }) {
  const [datos, setDatos] = useState(VACIO)
  const [error, setError] = useState(null)
  const [enviando, setEnviando] = useState(false)
  const [enviado, setEnviado] = useState(false)

  const set = (campo) => (valor) => setDatos((d) => ({ ...d, [campo]: valor }))
  const alternar = (campo, id) => setDatos((d) => ({
    ...d,
    [campo]: d[campo].includes(id) ? d[campo].filter((x) => x !== id) : [...d[campo], id],
  }))

  async function enviar(e) {
    e.preventDefault()
    setError(null)
    setEnviando(true)
    try {
      await api.postular({
        ...datos,
        licencia_vence: datos.licencia_vence || null,
        apto_medico_vence: datos.apto_medico_vence || null,
        anios_experiencia: datos.anios_experiencia === '' ? null : Number(datos.anios_experiencia),
        salario_pretendido: datos.salario_pretendido === '' ? null : Number(datos.salario_pretendido),
        escolaridad: datos.escolaridad || null,
      }, vacante.id)
      setEnviado(true)
      onListo?.()
    } catch (e) { setError(e.message) } finally { setEnviando(false) }
  }

  if (enviado) {
    return (
      <div className="animar-entrada mx-auto max-w-md px-6 py-24 text-center">
        <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-apto/10 text-[22px] text-apto">
          ✓
        </div>
        <h1 className="text-[22px] font-semibold tracking-tight">Recibimos tu postulación</h1>
        <p className="mt-2 text-[14px] leading-relaxed text-tinta-suave">
          Vamos a revisar tus datos y te contactamos al teléfono que dejaste. Gracias
          por postularte a {vacante.titulo}.
        </p>
        <button className="btn-suave mt-8" onClick={() => { setDatos(VACIO); setEnviado(false) }}>
          Cargar otra postulación
        </button>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-xl px-5 pb-24 pt-10 sm:px-6">
      <header className="animar-entrada mb-8">
        <p className="text-[12px] font-medium uppercase tracking-wider text-acento">
          Vacante abierta
        </p>
        <h1 className="mt-1 text-[26px] font-semibold leading-tight tracking-tight sm:text-[30px]">
          {vacante.titulo}
        </h1>
        <p className="mt-2 text-[15px] text-tinta-suave">
          {vacante.municipio}, N.L. · {pesos(vacante.salario_min)} a {pesos(vacante.salario_max)} al mes
        </p>
        {vacante.indispensables?.length > 0 && (
          <div className="tarjeta mt-5 p-4">
            <p className="mb-2 text-[12px] font-semibold">Requisitos indispensables</p>
            <ul className="space-y-1">
              {vacante.indispensables.map((r) => (
                <li key={r} className="flex gap-2 text-[13px] text-tinta-suave">
                  <span className="text-acento">•</span>{r}
                </li>
              ))}
            </ul>
          </div>
        )}
      </header>

      <form onSubmit={enviar} className="space-y-7">
        <section className="space-y-3">
          <div>
            <label className="etiqueta">Nombre completo</label>
            <input required minLength={2} className="campo" value={datos.nombre}
                   onChange={(e) => set('nombre')(e.target.value)} placeholder="Como aparece en tu licencia" />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="etiqueta">Teléfono</label>
              <input required inputMode="tel" minLength={6} className="campo" value={datos.telefono}
                     onChange={(e) => set('telefono')(e.target.value)} placeholder="81 1234 5678" />
            </div>
            <div>
              <label className="etiqueta">Correo <span className="opacity-50">(opcional)</span></label>
              <input type="email" inputMode="email" className="campo" value={datos.email}
                     onChange={(e) => set('email')(e.target.value)} placeholder="tucorreo@gmail.com" />
            </div>
          </div>
          <div>
            <label className="etiqueta">¿En qué municipio vives?</label>
            <input className="campo" value={datos.municipio}
                   onChange={(e) => set('municipio')(e.target.value)} placeholder="Apodaca" />
          </div>
        </section>

        <section>
          <label className="etiqueta">¿Qué licencias tienes vigentes?</label>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {LICENCIAS.map((l) => (
              <Opcion key={l.id} pie={l.pie} activa={datos.licencias.includes(l.id)}
                      onClick={() => alternar('licencias', l.id)}>
                {l.nombre}
              </Opcion>
            ))}
          </div>
        </section>

        <section className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className="etiqueta">¿Cuándo vence tu licencia?</label>
            <input type="date" className="campo" value={datos.licencia_vence}
                   onChange={(e) => set('licencia_vence')(e.target.value)} />
          </div>
          <div>
            <label className="etiqueta">¿Cuándo vence tu apto médico?</label>
            <input type="date" className="campo" value={datos.apto_medico_vence}
                   onChange={(e) => set('apto_medico_vence')(e.target.value)} />
          </div>
        </section>

        <section>
          <label className="etiqueta">¿Qué unidades has manejado?</label>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {UNIDADES.map(([id, nombre]) => (
              <Opcion key={id} activa={datos.unidades.includes(id)}
                      onClick={() => alternar('unidades', id)}>{nombre}</Opcion>
            ))}
          </div>
        </section>

        <section className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className="etiqueta">¿Cuántos años de experiencia tienes?</label>
            <input type="number" min="0" max="50" step="0.5" inputMode="decimal" className="campo"
                   value={datos.anios_experiencia}
                   onChange={(e) => set('anios_experiencia')(e.target.value)} placeholder="5" />
          </div>
          <div>
            <label className="etiqueta">¿Cuánto esperas ganar al mes?</label>
            <input type="number" min="0" step="500" inputMode="numeric" className="campo"
                   value={datos.salario_pretendido}
                   onChange={(e) => set('salario_pretendido')(e.target.value)} placeholder="21000" />
          </div>
        </section>

        <section>
          <label className="etiqueta">¿Hasta qué grado estudiaste?</label>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {ESCOLARIDAD.map(([id, nombre]) => (
              <Opcion key={id} activa={datos.escolaridad === id}
                      onClick={() => set('escolaridad')(id)}>{nombre}</Opcion>
            ))}
          </div>
        </section>

        <section className="grid gap-5 sm:grid-cols-2">
          <div>
            <label className="etiqueta">¿Puedes hacer viajes foráneos?</label>
            <SiNo valor={datos.disponibilidad_foranea} onCambiar={set('disponibilidad_foranea')} />
          </div>
          <div>
            <label className="etiqueta">¿Has manejado materiales peligrosos?</label>
            <SiNo valor={datos.materiales_peligrosos} onCambiar={set('materiales_peligrosos')} />
          </div>
        </section>

        {error && <Aviso onCerrar={() => setError(null)}>{error}</Aviso>}

        <div className="sticky bottom-0 -mx-5 border-t border-borde bg-papel/90 px-5 py-4 backdrop-blur-xl sm:mx-0 sm:border-0 sm:bg-transparent sm:px-0 sm:backdrop-blur-none">
          <button type="submit" disabled={enviando} className="btn-acento btn-lg w-full">
            {enviando ? 'Enviando…' : 'Enviar mi postulación'}
          </button>
          <p className="mt-2 text-center text-[11px] text-piedra-400">
            Solo te pedimos lo necesario para saber si cumples el perfil.
          </p>
        </div>
      </form>
    </div>
  )
}
