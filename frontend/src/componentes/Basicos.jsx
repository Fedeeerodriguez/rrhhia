/* Piezas visuales compartidas. Regla de la casa: ningun score se dibuja sin
   su porque al lado. */

export function Anillo({ valor, apto, tamano = 56 }) {
  const grosor = tamano > 70 ? 6 : 4
  const radio = (tamano - grosor) / 2
  const circunferencia = 2 * Math.PI * radio
  const color = apto ? '#1C7A55' : '#B23B32'

  return (
    <div className="relative shrink-0" style={{ width: tamano, height: tamano }}>
      <svg width={tamano} height={tamano} className="-rotate-90">
        <circle cx={tamano / 2} cy={tamano / 2} r={radio} fill="none"
                stroke="#EFEDE9" strokeWidth={grosor} />
        <circle
          cx={tamano / 2} cy={tamano / 2} r={radio} fill="none"
          stroke={color} strokeWidth={grosor} strokeLinecap="round"
          strokeDasharray={circunferencia}
          strokeDashoffset={circunferencia * (1 - Math.max(valor, 0) / 100)}
          style={{ transition: 'stroke-dashoffset 700ms cubic-bezier(0.16,1,0.3,1)' }}
        />
      </svg>
      <span className="tabular absolute inset-0 flex items-center justify-center font-semibold"
            style={{ fontSize: tamano > 70 ? 20 : 14, color }}>
        {Math.round(valor)}
      </span>
    </div>
  )
}

/* Las clases van escritas enteras: Tailwind solo genera lo que encuentra
   literal en el codigo, y `chip-${tono}` lo purgaba dejando el chip sin estilo. */
const CHIPS = {
  apto: 'chip-apto',
  alerta: 'chip-alerta',
  fuera: 'chip-fuera',
  neutro: 'chip-neutro',
}

export function Chip({ tono = 'neutro', children }) {
  return <span className={CHIPS[tono] ?? CHIPS.neutro}>{children}</span>
}

export function Cargando({ texto = 'Cargando' }) {
  return (
    <div className="flex items-center justify-center gap-2.5 py-16 text-[13px] text-tinta-suave">
      <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-piedra-300 border-t-acento" />
      {texto}…
    </div>
  )
}

export function Vacio({ titulo, detalle }) {
  return (
    <div className="animar-aparecer py-20 text-center">
      <p className="text-[15px] font-medium">{titulo}</p>
      {detalle && <p className="mx-auto mt-1.5 max-w-sm text-[13px] text-tinta-suave">{detalle}</p>}
    </div>
  )
}

export function Aviso({ tono = 'fuera', children, onCerrar }) {
  if (!children) return null
  const fondo = tono === 'fuera' ? 'bg-fuera/[0.07] text-fuera' : 'bg-alerta/[0.09] text-alerta'
  return (
    <div className={`animar-aparecer flex items-start gap-3 rounded-2xl px-4 py-3 text-[13px] ${fondo}`}>
      <span className="flex-1">{children}</span>
      {onCerrar && (
        <button onClick={onCerrar} className="shrink-0 opacity-60 hover:opacity-100">✕</button>
      )}
    </div>
  )
}

/* Barra de progreso de la carga masiva: importa que se vea que avanza. */
export function Progreso({ hechos, total }) {
  const porcentaje = total ? Math.round((hechos / total) * 100) : 0
  return (
    <div className="animar-aparecer">
      <div className="mb-2 flex items-baseline justify-between text-[13px]">
        <span className="font-medium">Analizando {hechos} de {total}</span>
        <span className="tabular text-tinta-suave">{porcentaje}%</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-piedra-200">
        <div className="h-full rounded-full bg-acento transition-all duration-500 ease-out"
             style={{ width: `${porcentaje}%` }} />
      </div>
    </div>
  )
}

export function Marco({ titulo, bajada, children, acciones, ancho = false }) {
  return (
    <div className="min-h-full">
      <header className="sticky top-0 z-20 border-b border-borde bg-papel/85 backdrop-blur-xl">
        <div className={`mx-auto flex flex-wrap items-center gap-4 px-6 py-4 ${ancho ? "max-w-ancho" : "max-w-contenido"}`}>
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-[17px] font-semibold tracking-tight">{titulo}</h1>
            {bajada && <p className="truncate text-[13px] text-tinta-suave">{bajada}</p>}
          </div>
          {acciones}
        </div>
      </header>
      <main className={`mx-auto px-6 py-8 ${ancho ? "max-w-ancho" : "max-w-contenido"}`}>{children}</main>
    </div>
  )
}

export function Pestanas({ activa, onCambiar, opciones }) {
  return (
    <nav className="inline-flex rounded-full bg-piedra-100 p-1">
      {opciones.map((o) => (
        <button
          key={o.id}
          onClick={() => onCambiar(o.id)}
          className={`rounded-full px-4 py-1.5 text-[13px] font-medium transition-all duration-200
            ${activa === o.id ? 'bg-superficie text-tinta shadow-sm' : 'text-tinta-suave hover:text-tinta'}`}
        >
          {o.nombre}
          {o.cuenta != null && <span className="tabular ml-1.5 opacity-50">{o.cuenta}</span>}
        </button>
      ))}
    </nav>
  )
}
