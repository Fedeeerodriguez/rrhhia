import { useEffect, useState } from 'react'
import { api, ETAPAS, NOMBRE_CAMPO, NOMBRE_ETAPA, pesos } from '../api.js'
import { Anillo, Aviso, Cargando, Chip, NivelIA } from './Basicos.jsx'

/* Panel lateral: es donde se defiende el porcentaje. Cada criterio con su
   puntaje, su peso y la frase que lo explica. */

function valorLegible(campo, dato) {
  const v = dato?.valor
  if (v == null || v === '' || (Array.isArray(v) && v.length === 0)) return '—'
  if (campo === 'salario_pretendido') return pesos(v)
  if (campo === 'historial') return `${v.length} empleos`
  if (typeof v === 'boolean') return v ? 'Sí' : 'No'
  if (Array.isArray(v)) return v.map((x) => String(x).replace(/_/g, ' ')).join(', ')
  return String(v)
}

function Criterio({ fila }) {
  const tono = fila.sin_dato ? 'alerta' : fila.cumple ? 'apto' : 'fuera'
  const barra = { apto: 'bg-apto', alerta: 'bg-alerta', fuera: 'bg-fuera' }[tono]
  return (
    <li className="py-3">
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-[13px] font-medium">
          {fila.criterio}
          {fila.indispensable && (
            <span className="ml-1.5 align-middle text-[10px] font-semibold uppercase tracking-wide text-tinta-suave">
              indispensable
            </span>
          )}
        </span>
        <span className="tabular shrink-0 text-[13px] text-tinta-suave">{fila.puntaje}%</span>
      </div>
      <p className="mt-0.5 text-[12px] leading-snug text-tinta-suave">{fila.detalle}</p>
      <div className="mt-2 h-1 overflow-hidden rounded-full bg-piedra-100">
        <div className={`h-full rounded-full ${barra} transition-all duration-500`}
             style={{ width: `${fila.puntaje}%` }} />
      </div>
    </li>
  )
}

export default function PanelDetalle({ postulacionId, onCerrar, onMover, permiteCorregir = false }) {
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState(null)
  const [editando, setEditando] = useState(null)
  const [borrador, setBorrador] = useState('')

  async function cargar() {
    try { setDatos(await api.postulacion(postulacionId)) }
    catch (e) { setError(e.message) }
  }

  useEffect(() => { setDatos(null); cargar() }, [postulacionId])

  // Cerrar con Escape: el panel tapa el tablero y hay que poder salir rapido.
  useEffect(() => {
    const salir = (e) => e.key === 'Escape' && onCerrar()
    window.addEventListener('keydown', salir)
    return () => window.removeEventListener('keydown', salir)
  }, [onCerrar])

  async function guardarCampo(campo) {
    try {
      let valor = borrador
      if (campo === 'anios_experiencia' || campo === 'salario_pretendido') valor = Number(borrador)
      if (campo === 'disponibilidad_foranea' || campo === 'materiales_peligrosos') {
        valor = borrador === 'true'
      }
      await api.corregirCampo(postulacionId, campo, valor)
      setEditando(null)
      await cargar()
    } catch (e) { setError(e.message) }
  }

  return (
    <aside className="fixed inset-y-0 right-0 z-30 flex w-full max-w-lg flex-col border-l border-borde bg-superficie shadow-panel">
      <header className="flex items-start gap-4 border-b border-borde px-6 py-5">
        {datos && <Anillo valor={datos.score_final ?? datos.score} apto={datos.apto} tamano={76} />}
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-[17px] font-semibold tracking-tight">
            {datos?.nombre ?? 'Candidato'}
          </h2>
          <p className="truncate text-[13px] text-tinta-suave">
            {[datos?.telefono, datos?.email].filter(Boolean).join(' · ') || 'Sin contacto'}
          </p>
          {datos && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              <Chip tono={datos.apto ? 'apto' : 'fuera'}>
                {datos.apto ? 'Cumple los requisitos' : 'No cumple'}
              </Chip>
              <Chip tono="neutro">{NOMBRE_ETAPA[datos.etapa]}</Chip>
              {datos.origen !== 'formulario' && <Chip tono="neutro">vía {datos.origen}</Chip>}
            </div>
          )}
        </div>
        <button onClick={onCerrar} className="btn-fantasma -mr-2 -mt-1 px-2.5 py-1.5">✕</button>
      </header>

      <div className="flex-1 space-y-7 overflow-y-auto px-6 py-6">
        {error && <Aviso onCerrar={() => setError(null)}>{error}</Aviso>}
        {!datos ? <Cargando /> : (
          <>
            <section>
              <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-tinta-suave">
                Por qué este puntaje
              </h3>
              <ul className="space-y-1">
                {datos.razones.map((r, i) => (
                  <li key={i} className="flex gap-2 text-[13px]">
                    <span className={datos.apto ? 'text-apto' : 'text-fuera'}>•</span>
                    <span>{r}</span>
                  </li>
                ))}
              </ul>
              {datos.alertas.length > 0 && (
                <ul className="mt-3 space-y-1 rounded-2xl bg-alerta/[0.07] px-3.5 py-3">
                  {datos.alertas.map((a, i) => (
                    <li key={i} className="flex gap-2 text-[12px] text-alerta">
                      <span>!</span><span>{a}</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            {datos.evaluacion_ia && (
              <section>
                <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-tinta-suave">
                  Evaluación de la IA
                </h3>
                <div className="tarjeta p-4">
                  {/* Los dos números, siempre juntos: el reclutador tiene que
                      ver qué parte es objetiva y qué parte es criterio. */}
                  <div className="mb-3 flex flex-wrap items-baseline gap-x-3 gap-y-1 text-[13px]">
                    <span className="text-tinta-suave">Por requisitos</span>
                    <span className="tabular font-semibold">{datos.score}</span>
                    {datos.evaluacion_ia.ajuste !== 0 && (
                      <>
                        <span className="text-tinta-suave">· ajuste de la IA</span>
                        <span className={`tabular font-semibold ${datos.evaluacion_ia.ajuste > 0 ? 'text-apto' : 'text-fuera'}`}>
                          {datos.evaluacion_ia.ajuste > 0 ? '+' : ''}{datos.evaluacion_ia.ajuste}
                        </span>
                        <span className="text-tinta-suave">→</span>
                        <span className="tabular font-semibold">{datos.score_final}</span>
                      </>
                    )}
                    <NivelIA nivel={datos.evaluacion_ia.nivel} />
                  </div>

                  <p className="text-[13px] leading-relaxed">{datos.evaluacion_ia.resumen}</p>

                  {datos.evaluacion_ia.fortalezas?.length > 0 && (
                    <ul className="mt-3 space-y-1">
                      {datos.evaluacion_ia.fortalezas.map((f, i) => (
                        <li key={i} className="flex gap-2 text-[12px] text-tinta-suave">
                          <span className="text-apto">+</span>{f}
                        </li>
                      ))}
                    </ul>
                  )}
                  {datos.evaluacion_ia.riesgos?.length > 0 && (
                    <ul className="mt-2 space-y-1">
                      {datos.evaluacion_ia.riesgos.map((r, i) => (
                        <li key={i} className="flex gap-2 text-[12px] text-alerta">
                          <span>!</span>{r}
                        </li>
                      ))}
                    </ul>
                  )}
                  {datos.evaluacion_ia.veredicto && (
                    <p className="mt-3 border-t border-borde pt-3 text-[12px] font-medium">
                      {datos.evaluacion_ia.veredicto}
                    </p>
                  )}
                  <p className="mt-3 text-[11px] text-piedra-400">
                    La IA no descarta a nadie: ordena dentro de cada grupo. Los
                    requisitos indispensables los decide el dato, no el criterio.
                  </p>
                </div>
              </section>
            )}

            <section>
              <h3 className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-tinta-suave">
                Desglose
              </h3>
              <ul className="divide-y divide-borde">
                {datos.desglose.map((fila) => <Criterio key={fila.criterio} fila={fila} />)}
              </ul>
            </section>

            <section>
              <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-tinta-suave">
                Datos del candidato
              </h3>
              <ul className="divide-y divide-borde">
                {Object.entries(datos.perfil ?? {}).map(([campo, dato]) => {
                  const dudoso = dato.origen === 'cv' && (dato.confianza ?? 0) < 0.75
                  return (
                    <li key={campo} className="py-2.5">
                      <div className="flex items-baseline justify-between gap-3">
                        <span className="text-[12px] text-tinta-suave">{NOMBRE_CAMPO[campo] ?? campo}</span>
                        <span className="flex items-center gap-2 text-right text-[13px]">
                          {editando === campo ? (
                            <>
                              <input autoFocus className="campo w-40 px-2.5 py-1 text-[13px]"
                                     value={borrador} onChange={(e) => setBorrador(e.target.value)}
                                     onKeyDown={(e) => e.key === 'Enter' && guardarCampo(campo)} />
                              <button className="btn-acento px-3 py-1" onClick={() => guardarCampo(campo)}>
                                Guardar
                              </button>
                            </>
                          ) : (
                            <>
                              <span className={dudoso ? 'text-alerta' : ''}>
                                {valorLegible(campo, dato)}
                              </span>
                              {permiteCorregir && (
                                <button
                                  className="text-[11px] text-acento opacity-0 transition-opacity hover:underline group-hover:opacity-100"
                                  style={{ opacity: 1 }}
                                  onClick={() => { setEditando(campo); setBorrador(String(dato.valor ?? '')) }}
                                >
                                  corregir
                                </button>
                              )}
                            </>
                          )}
                        </span>
                      </div>
                      {/* La evidencia: de donde salio el dato */}
                      {dato.fragmento && (
                        <p className={`mt-1 rounded-lg px-2.5 py-1.5 text-[11px] italic leading-snug
                          ${dudoso ? 'bg-alerta/[0.07] text-alerta' : 'bg-piedra-50 text-piedra-500'}`}>
                          “{dato.fragmento}”
                        </p>
                      )}
                    </li>
                  )
                })}
              </ul>
            </section>

            {datos.eventos.length > 0 && (
              <section>
                <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-tinta-suave">
                  Historial en el proceso
                </h3>
                <ul className="space-y-1.5">
                  {datos.eventos.map((e, i) => (
                    <li key={i} className="text-[12px] text-tinta-suave">
                      {NOMBRE_ETAPA[e.desde]} → <span className="text-tinta">{NOMBRE_ETAPA[e.hacia]}</span>
                      {' · '}{e.autor}
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </>
        )}
      </div>

      {datos && (
        <footer className="flex flex-wrap gap-2 border-t border-borde px-6 py-4">
          {ETAPAS.filter((e) => e !== datos.etapa).map((etapa) => (
            <button key={etapa} className="btn-suave"
                    onClick={async () => { await onMover(datos.id, etapa); cargar() }}>
              {NOMBRE_ETAPA[etapa]}
            </button>
          ))}
        </footer>
      )}
    </aside>
  )
}
