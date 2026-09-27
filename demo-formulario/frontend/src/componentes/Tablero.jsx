import { useState } from 'react'
import { ETAPAS, NOMBRE_ETAPA } from '../api.js'
import { Anillo, Chip } from './Basicos.jsx'

/* Kanban con arrastre nativo del navegador: sin dependencias y sin magia.
   Igual cada tarjeta tiene su menu de "mover a", porque arrastrar en una
   pantalla chica es incomodo y el reclutador no siempre usa mouse. */

function Tarjeta({ candidato, onAbrir, onArrastrar }) {
  const { nombre, score, apto, razones = [], alertas = [], dudosos = [] } = candidato
  return (
    <article
      draggable
      onDragStart={(e) => {
        e.dataTransfer.effectAllowed = 'move'
        onArrastrar(candidato)
      }}
      onClick={() => onAbrir(candidato.id)}
      className="tarjeta tarjeta-hover animar-entrada cursor-pointer p-4 active:cursor-grabbing"
    >
      <div className="flex items-start gap-3.5">
        <Anillo valor={score} apto={apto} tamano={48} />
        <div className="min-w-0 flex-1">
          <h3 className="text-[14px] font-semibold leading-tight">{nombre}</h3>
          {/* El porque, siempre pegado al numero */}
          <p className="mt-1 line-clamp-2 text-[12px] leading-snug text-tinta-suave">
            {razones[0] ?? 'Sin datos suficientes'}
          </p>
          <div className="mt-2.5 flex flex-wrap gap-1.5">
            {!apto && <Chip tono="fuera">No cumple</Chip>}
            {alertas.length > 0 && <Chip tono="alerta">{alertas.length} por verificar</Chip>}
            {dudosos.length > 0 && <Chip tono="neutro">{dudosos.length} dudosos</Chip>}
          </div>
        </div>
      </div>
    </article>
  )
}

export default function Tablero({ tablero, onMover, onAbrir }) {
  const [arrastrando, setArrastrando] = useState(null)
  const [encima, setEncima] = useState(null)

  const columnas = ETAPAS.map((etapa) => ({
    etapa,
    candidatos: tablero.columnas.find((c) => c.etapa === etapa)?.candidatos ?? [],
  }))

  function soltar(etapa) {
    setEncima(null)
    if (arrastrando && arrastrando.etapa !== etapa) onMover(arrastrando.id, etapa)
    setArrastrando(null)
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
      {columnas.map(({ etapa, candidatos }) => (
        <section
          key={etapa}
          onDragOver={(e) => { e.preventDefault(); setEncima(etapa) }}
          onDragLeave={() => setEncima((a) => (a === etapa ? null : a))}
          onDrop={() => soltar(etapa)}
          className={`rounded-3xl border border-transparent p-2 transition-colors duration-200
            ${encima === etapa ? 'zona-activa' : ''}`}
        >
          <header className="flex items-baseline justify-between px-2.5 pb-3 pt-1">
            <h2 className="text-[13px] font-semibold tracking-tight">{NOMBRE_ETAPA[etapa]}</h2>
            <span className="tabular text-[13px] text-piedra-400">{candidatos.length}</span>
          </header>
          <div className="space-y-2.5">
            {candidatos.map((c) => (
              <Tarjeta key={c.id} candidato={c} onAbrir={onAbrir} onArrastrar={setArrastrando} />
            ))}
            {candidatos.length === 0 && (
              <p className="px-2.5 py-8 text-center text-[12px] text-piedra-400">
                {encima === etapa ? 'Soltar aquí' : 'Vacío'}
              </p>
            )}
          </div>
        </section>
      ))}
    </div>
  )
}
