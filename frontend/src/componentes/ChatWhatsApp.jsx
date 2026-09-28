import { useEffect, useRef, useState } from 'react'
import { api } from '../api.js'
import { Aviso } from './Basicos.jsx'

/* Simulador de WhatsApp.

   El agente es el mismo que atiende el webhook real: esta pantalla solo le
   manda mensajes por HTTP en vez de por el proveedor. Existe para poder
   mostrar el canal en la demo sin depender de un número de WhatsApp Business,
   que tarda días en aprobarse. */

const NUMERO = '+52 81 1234 5678'

function Burbuja({ quien, texto }) {
  const mia = quien === 'candidato'
  return (
    <div className={`flex ${mia ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`animar-entrada max-w-[78%] whitespace-pre-wrap rounded-2xl px-3.5 py-2 text-[13.5px] leading-relaxed shadow-sm
          ${mia ? 'rounded-br-md bg-[#D9FDD3] text-tinta'
                : 'rounded-bl-md bg-superficie text-tinta'}`}
      >
        {texto.replace(/\*\*/g, '').replace(/_/g, '')}
      </div>
    </div>
  )
}

export default function ChatWhatsApp({ onPostulacion }) {
  const [mensajes, setMensajes] = useState([])
  const [texto, setTexto] = useState('')
  const [ocupado, setOcupado] = useState(false)
  const [error, setError] = useState(null)
  const archivo = useRef(null)
  const fondo = useRef(null)

  useEffect(() => { cargar() }, [])
  useEffect(() => {
    fondo.current?.scrollTo({ top: fondo.current.scrollHeight, behavior: 'smooth' })
  }, [mensajes])

  async function cargar() {
    try { setMensajes(await api.historialWhatsapp(NUMERO)) }
    catch (e) { setError(e.message) }
  }

  async function enviar(e) {
    e?.preventDefault()
    const contenido = texto.trim()
    if (!contenido || ocupado) return
    setTexto('')
    setMensajes((m) => [...m, { quien: 'candidato', texto: contenido }])
    setOcupado(true)
    try {
      const r = await api.mensajeWhatsapp(NUMERO, contenido)
      await cargar()
      if (r.postulacion_id) onPostulacion?.(r.postulacion_id)
    } catch (e) { setError(e.message) } finally { setOcupado(false) }
  }

  async function mandarCv(archivos) {
    const f = archivos?.[0]
    if (!f) return
    setOcupado(true)
    try {
      const r = await api.archivoWhatsapp(NUMERO, f)
      await cargar()
      if (r.postulacion_id) onPostulacion?.(r.postulacion_id)
    } catch (e) { setError(e.message) } finally { setOcupado(false) }
  }

  async function reiniciar() {
    await api.reiniciarWhatsapp(NUMERO)
    setMensajes([])
  }

  return (
    <div className="mx-auto max-w-md">
      <div className="overflow-hidden rounded-[28px] border border-borde bg-[#EFE7DE] shadow-panel">
        <header className="flex items-center gap-3 bg-[#008069] px-4 py-3 text-white">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-white/20 text-[15px]">
            RH
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[14px] font-medium">Transportes del Norte</p>
            <p className="text-[11px] text-white/70">
              {ocupado ? 'escribiendo…' : 'en línea'}
            </p>
          </div>
          <button onClick={reiniciar} className="text-[11px] text-white/70 hover:text-white">
            reiniciar
          </button>
        </header>

        <div ref={fondo} className="h-[460px] space-y-2 overflow-y-auto px-3.5 py-4">
          {mensajes.length === 0 && (
            <p className="px-6 py-16 text-center text-[12px] text-tinta-suave">
              Escribe cualquier cosa para empezar, como haría un candidato.
            </p>
          )}
          {mensajes.map((m, i) => <Burbuja key={i} {...m} />)}
        </div>

        <form onSubmit={enviar} className="flex items-center gap-2 bg-[#F0F2F5] px-3 py-2.5">
          <input ref={archivo} type="file" accept=".pdf,.txt" className="hidden"
                 onChange={(e) => mandarCv(e.target.files)} />
          <button type="button" onClick={() => archivo.current?.click()}
                  title="Mandar el CV"
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-[18px] text-tinta-suave hover:bg-piedra-200">
            📎
          </button>
          <input
            className="min-w-0 flex-1 rounded-full border-none bg-white px-4 py-2 text-[14px] outline-none"
            placeholder="Escribe un mensaje"
            value={texto} onChange={(e) => setTexto(e.target.value)} disabled={ocupado}
          />
          <button type="submit" disabled={ocupado || !texto.trim()}
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#008069] text-white disabled:opacity-40">
            ➤
          </button>
        </form>
      </div>

      {error && <div className="mt-4"><Aviso onCerrar={() => setError(null)}>{error}</Aviso></div>}

      <p className="mt-4 text-center text-[12px] leading-relaxed text-piedra-400">
        Simulador. El agente es el mismo que responde el webhook real; acá los
        mensajes viajan por HTTP en vez del proveedor.
      </p>
    </div>
  )
}
