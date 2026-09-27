import { NOMBRE_ETAPA } from '../api.js'
import { Chip, Vacio } from './Basicos.jsx'

/* Bandeja de salida. En la demo los avisos NO se envian: se leen acá. Se dice
   explicito en pantalla para que nadie crea que ya salieron. */

export default function Bandeja({ mensajes }) {
  if (!mensajes.length) {
    return <Vacio titulo="Todavía no hay avisos"
                  detalle="Cuando muevas a un candidato de columna, el mensaje aparece aquí." />
  }

  return (
    <div className="space-y-4">
      <p className="rounded-2xl bg-acento-50 px-4 py-3 text-[13px] text-acento">
        Los mensajes de la demo no se envían: quedan aquí para que veas qué recibiría
        cada candidato.
      </p>
      <ul className="space-y-3">
        {mensajes.map((m) => (
          <li key={m.id} className="tarjeta animar-entrada p-5">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h3 className="text-[14px] font-semibold">{m.asunto}</h3>
              <Chip tono={m.etapa === 'rechazado' ? 'fuera' : 'apto'}>
                {NOMBRE_ETAPA[m.etapa]}
              </Chip>
            </div>
            <p className="mt-0.5 text-[12px] text-tinta-suave">Para {m.destinatario}</p>
            <pre className="mt-3 whitespace-pre-wrap border-l-2 border-borde pl-3.5 font-sans text-[13px] leading-relaxed text-tinta-suave">
              {m.cuerpo}
            </pre>
          </li>
        ))}
      </ul>
    </div>
  )
}
