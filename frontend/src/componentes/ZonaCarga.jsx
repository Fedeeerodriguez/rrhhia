import { useRef, useState } from 'react'
import { api } from '../api.js'
import { Anillo, Aviso, Chip, Progreso } from './Basicos.jsx'

/* El momento "wow" de la Demo A: arrastrar la carpeta de CVs y ver cómo se
   acomodan del mejor al peor.
   Los archivos se mandan en tandas de a 3 para que la barra de progreso avance
   de verdad; una sola llamada con 15 archivos deja la pantalla congelada y
   parece que no funciona. */

const TANDA = 3

function Fila({ item, indice, onAbrir }) {
  return (
    <li
      onClick={() => onAbrir(item.id)}
      className="tarjeta tarjeta-hover animar-entrada flex cursor-pointer items-center gap-4 p-4"
      style={{ animationDelay: `${Math.min(indice, 12) * 35}ms` }}
    >
      <span className="tabular w-6 shrink-0 text-center text-[13px] text-piedra-400">
        {indice + 1}
      </span>
      <Anillo valor={item.score} apto={item.apto} tamano={52} />
      <div className="min-w-0 flex-1">
        <h3 className="truncate text-[14px] font-semibold leading-tight">{item.nombre}</h3>
        <p className="mt-0.5 line-clamp-1 text-[12px] text-tinta-suave">
          {item.razones?.[0] ?? 'Sin datos suficientes'}
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          {!item.apto && <Chip tono="fuera">No cumple</Chip>}
          {item.alertas?.length > 0 && <Chip tono="alerta">{item.alertas.length} por verificar</Chip>}
          <Chip tono="neutro">{item.completitud}% del CV leído</Chip>
          <span className="truncate text-[11px] text-piedra-400">{item.archivo}</span>
        </div>
      </div>
    </li>
  )
}

export default function ZonaCarga({ onCargado, onAbrir }) {
  const entrada = useRef(null)
  const [encima, setEncima] = useState(false)
  const [progreso, setProgreso] = useState(null)
  const [resultado, setResultado] = useState(null)
  const [error, setError] = useState(null)

  async function procesar(archivos) {
    const lista = Array.from(archivos)
    if (!lista.length) return
    setError(null)
    setResultado(null)
    setProgreso({ hechos: 0, total: lista.length })

    const procesados = []
    const fallidos = []
    try {
      for (let i = 0; i < lista.length; i += TANDA) {
        const tanda = lista.slice(i, i + TANDA)
        const r = await api.cargarCvs(tanda)
        procesados.push(...r.procesados)
        fallidos.push(...r.fallidos)
        setProgreso({ hechos: Math.min(i + TANDA, lista.length), total: lista.length })
      }
      procesados.sort((a, b) => (b.apto - a.apto) || (b.score - a.score))
      setResultado({ procesados, fallidos })
      onCargado?.()
    } catch (e) {
      setError(e.message)
    } finally {
      setProgreso(null)
    }
  }

  return (
    <div className="space-y-6">
      <div
        onDragOver={(e) => { e.preventDefault(); setEncima(true) }}
        onDragLeave={() => setEncima(false)}
        onDrop={(e) => { e.preventDefault(); setEncima(false); procesar(e.dataTransfer.files) }}
        onClick={() => entrada.current?.click()}
        className={`cursor-pointer rounded-3xl border-2 border-dashed p-12 text-center transition-all duration-300
          ${encima ? 'border-acento bg-acento-50' : 'border-piedra-300 bg-superficie hover:border-piedra-400'}`}
      >
        <input ref={entrada} type="file" multiple accept=".pdf,.txt" className="hidden"
               onChange={(e) => procesar(e.target.files)} />
        <p className="text-[15px] font-medium">
          {encima ? 'Suelta los CVs aquí' : 'Arrastra los CVs o haz clic para elegirlos'}
        </p>
        <p className="mx-auto mt-1.5 max-w-md text-[13px] text-tinta-suave">
          PDF o texto, todos juntos. Cada CV se lee, se califica y se ordena solo.
        </p>
      </div>

      {progreso && <div className="tarjeta p-5"><Progreso {...progreso} /></div>}
      {error && <Aviso onCerrar={() => setError(null)}>{error}</Aviso>}

      {resultado && (
        <section className="animar-aparecer space-y-4">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-[15px] font-semibold tracking-tight">
              {resultado.procesados.length} CVs analizados
              <span className="ml-2 font-normal text-tinta-suave">
                · {resultado.procesados.filter((p) => p.apto).length} cumplen el perfil
              </span>
            </h2>
            <p className="text-[12px] text-piedra-400">
              Motor: {resultado.procesados[0]?.motor ?? '—'}
            </p>
          </div>

          {resultado.fallidos.length > 0 && (
            <Aviso tono="alerta">
              {resultado.fallidos.length} archivo(s) no se pudieron leer:{' '}
              {resultado.fallidos.map((f) => `${f.archivo} (${f.motivo})`).join(', ')}
            </Aviso>
          )}

          <ul className="space-y-2.5">
            {resultado.procesados.map((p, i) => (
              <Fila key={p.id} item={p} indice={i} onAbrir={onAbrir} />
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
