import { useRef, useState } from 'react'
import { api, pesos } from '../api.js'
import { Aviso, Cargando } from './Basicos.jsx'

/* El área del candidato. Pantalla propia, no una pestaña del reclutador: el
   operario entra por un link, sube su CV y se va. No ve el pipeline, ni su
   puntaje, ni a los demás postulantes. */

export default function PostulacionPublica({ vacante }) {
  const entrada = useRef(null)
  const [encima, setEncima] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [listo, setListo] = useState(false)
  const [error, setError] = useState(null)

  async function enviar(archivos) {
    const archivo = archivos?.[0]
    if (!archivo) return
    setError(null)
    setEnviando(true)
    try {
      await api.postularConCv(archivo, vacante.id)
      setListo(true)
    } catch (e) { setError(e.message) } finally { setEnviando(false) }
  }

  if (listo) {
    return (
      <div className="animar-entrada mx-auto max-w-md px-6 py-24 text-center">
        <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-apto/10 text-[22px] text-apto">
          ✓
        </div>
        <h1 className="text-[22px] font-semibold tracking-tight">Recibimos tu postulación</h1>
        <p className="mt-2 text-[14px] leading-relaxed text-tinta-suave">
          Vamos a revisar tu CV y te contactamos al teléfono que aparece ahí. Gracias
          por postularte a {vacante.titulo}.
        </p>
        <button className="btn-suave mt-8" onClick={() => setListo(false)}>
          Enviar otro CV
        </button>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-xl px-5 pb-20 pt-10 sm:px-6">
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

      <div
        onDragOver={(e) => { e.preventDefault(); setEncima(true) }}
        onDragLeave={() => setEncima(false)}
        onDrop={(e) => { e.preventDefault(); setEncima(false); enviar(e.dataTransfer.files) }}
        onClick={() => entrada.current?.click()}
        className={`cursor-pointer rounded-3xl border-2 border-dashed p-12 text-center transition-all duration-300
          ${encima ? 'border-acento bg-acento-50' : 'border-piedra-300 bg-superficie hover:border-piedra-400'}`}
      >
        <input ref={entrada} type="file" accept=".pdf,.txt" className="hidden"
               onChange={(e) => enviar(e.target.files)} />
        <p className="text-[15px] font-medium">
          {encima ? 'Suelta tu CV aquí' : 'Sube tu CV para postularte'}
        </p>
        <p className="mx-auto mt-1.5 max-w-sm text-[13px] text-tinta-suave">
          En PDF. Nos fijamos en tu licencia, tu experiencia y las unidades que has
          manejado.
        </p>
      </div>

      {enviando && <Cargando texto="Enviando tu CV" />}
      {error && <div className="mt-5"><Aviso onCerrar={() => setError(null)}>{error}</Aviso></div>}

      <p className="mt-6 text-center text-[12px] text-piedra-400">
        Si tu CV es una foto o no lo tienes a mano, escríbenos por WhatsApp y te
        tomamos los datos por ahí.
      </p>
    </div>
  )
}
