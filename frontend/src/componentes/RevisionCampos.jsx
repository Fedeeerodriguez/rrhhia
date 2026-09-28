import { useMemo, useRef, useState } from 'react'
import { api, NOMBRE_CAMPO } from '../api.js'
import { Aviso, Cargando, Chip } from './Basicos.jsx'

/* El corazón de la Demo C.

   El CV prellena y cada campo queda en uno de tres estados:
     verde     la IA lo leyó con confianza, se da por bueno
     amarillo  dudoso, se muestra el fragmento EXACTO del CV al lado
     vacío     no se encontró, hay que escribirlo

   Sin el fragmento, "corregir lo que la IA no detectó" es adivinar. Con el
   fragmento, se resuelve en dos clics. */

const LICENCIAS = ['federal_E', 'federal_B', 'federal_C', 'federal_A', 'estatal_C', 'estatal_B']
const UNIDADES = ['full', 'tractocamion', 'torton', 'rabon', 'roll_off', 'camioneta']
const ESCOLARIDAD = ['primaria', 'secundaria', 'preparatoria', 'tecnica', 'universidad']

const TIPO = {
  licencia_vence: 'fecha', apto_medico_vence: 'fecha',
  anios_experiencia: 'numero', salario_pretendido: 'numero',
  disponibilidad_foranea: 'si_no', materiales_peligrosos: 'si_no',
  licencias: 'lista', unidades: 'lista',
  escolaridad: 'opcion', historial: 'solo_lectura',
}

const ORDEN = [
  'nombre', 'telefono', 'email', 'municipio', 'licencias', 'licencia_vence',
  'apto_medico_vence', 'anios_experiencia', 'unidades', 'escolaridad',
  'disponibilidad_foranea', 'salario_pretendido', 'materiales_peligrosos', 'historial',
]

const ETIQUETA_ESTADO = {
  seguro: { tono: 'apto', texto: 'Leído del CV' },
  dudoso: { tono: 'alerta', texto: 'Confirma esto' },
  vacio: { tono: 'neutro', texto: 'Falta' },
}

function opciones(campo) {
  if (campo === 'licencias') return LICENCIAS
  if (campo === 'unidades') return UNIDADES
  if (campo === 'escolaridad') return ESCOLARIDAD
  return []
}

function Editor({ campo, valor, onCambiar }) {
  const tipo = TIPO[campo] ?? 'texto'

  if (tipo === 'solo_lectura') {
    return (
      <p className="text-[13px] text-tinta-suave">
        {Array.isArray(valor) ? `${valor.length} empleos detectados` : '—'}
      </p>
    )
  }

  if (tipo === 'si_no') {
    return (
      <div className="flex gap-2">
        {[['true', 'Sí'], ['false', 'No']].map(([v, n]) => (
          <button key={v} type="button" onClick={() => onCambiar(v === 'true')}
            className={`rounded-xl border px-3.5 py-1.5 text-[13px] transition-all active:scale-[0.97]
              ${String(valor) === v ? 'border-acento bg-acento-50 text-acento' : 'border-borde hover:border-piedra-300'}`}>
            {n}
          </button>
        ))}
      </div>
    )
  }

  if (tipo === 'lista') {
    const actual = Array.isArray(valor) ? valor : []
    return (
      <div className="flex flex-wrap gap-1.5">
        {opciones(campo).map((o) => {
          const activa = actual.includes(o)
          return (
            <button key={o} type="button"
              onClick={() => onCambiar(activa ? actual.filter((x) => x !== o) : [...actual, o])}
              className={`rounded-xl border px-2.5 py-1 text-[12px] transition-all active:scale-[0.97]
                ${activa ? 'border-acento bg-acento-50 text-acento' : 'border-borde hover:border-piedra-300'}`}>
              {o.replace(/_/g, ' ')}
            </button>
          )
        })}
      </div>
    )
  }

  if (tipo === 'opcion') {
    return (
      <div className="flex flex-wrap gap-1.5">
        {opciones(campo).map((o) => (
          <button key={o} type="button" onClick={() => onCambiar(o)}
            className={`rounded-xl border px-2.5 py-1 text-[12px] capitalize transition-all active:scale-[0.97]
              ${valor === o ? 'border-acento bg-acento-50 text-acento' : 'border-borde hover:border-piedra-300'}`}>
            {o}
          </button>
        ))}
      </div>
    )
  }

  return (
    <input
      className="campo px-3 py-2 text-[13px]"
      type={tipo === 'fecha' ? 'date' : tipo === 'numero' ? 'number' : 'text'}
      value={valor ?? ''}
      onChange={(e) => onCambiar(tipo === 'numero'
        ? (e.target.value === '' ? null : Number(e.target.value))
        : e.target.value)}
    />
  )
}

function Campo({ campo, dato, onCambiar, onConfirmar }) {
  const estado = dato.corregido ? 'seguro' : dato.estado
  const { tono, texto } = ETIQUETA_ESTADO[estado] ?? ETIQUETA_ESTADO.vacio
  const borde = { seguro: 'border-borde', dudoso: 'border-alerta/40', vacio: 'border-borde' }[estado]

  return (
    <li className={`tarjeta animar-entrada border ${borde} p-4`}>
      <div className="mb-2.5 flex flex-wrap items-center justify-between gap-2">
        <span className="text-[13px] font-medium">{NOMBRE_CAMPO[campo] ?? campo}</span>
        <div className="flex items-center gap-2">
          {dato.corregido && <Chip tono="apto">Confirmado por ti</Chip>}
          {!dato.corregido && <Chip tono={tono}>{texto}</Chip>}
        </div>
      </div>

      <Editor campo={campo} valor={dato.valor} onCambiar={(v) => onCambiar(campo, v)} />

      {/* La evidencia. Es lo que convierte una corrección en una decisión. */}
      {dato.fragmento && (
        <div className="mt-2.5 flex flex-wrap items-center gap-2">
          <p className={`flex-1 rounded-lg px-2.5 py-1.5 text-[11px] italic leading-snug
            ${estado === 'dudoso' ? 'bg-alerta/[0.08] text-alerta' : 'bg-piedra-50 text-piedra-500'}`}>
            En el CV: “{dato.fragmento}”
          </p>
          {estado === 'dudoso' && (
            <button type="button" className="btn-suave px-3 py-1 text-[12px]"
                    onClick={() => onConfirmar(campo)}>
              Está bien
            </button>
          )}
        </div>
      )}
    </li>
  )
}

export default function RevisionCampos({ onListo }) {
  const entrada = useRef(null)
  const [encima, setEncima] = useState(false)
  const [leyendo, setLeyendo] = useState(false)
  const [extraccion, setExtraccion] = useState(null)
  const [campos, setCampos] = useState(null)
  const [resultado, setResultado] = useState(null)
  const [error, setError] = useState(null)

  const porRevisar = useMemo(
    () => (campos ? Object.values(campos).filter((c) => !c.corregido && c.estado !== 'seguro').length : 0),
    [campos],
  )

  async function subir(archivos) {
    const archivo = archivos?.[0]
    if (!archivo) return
    setError(null)
    setLeyendo(true)
    setResultado(null)
    try {
      const r = await api.prellenar(archivo)
      setExtraccion(r)
      setCampos(Object.fromEntries(
        Object.entries(r.campos).map(([k, v]) => [k, { ...v, corregido: false }]),
      ))
    } catch (e) { setError(e.message) } finally { setLeyendo(false) }
  }

  const cambiar = (campo, valor) =>
    setCampos((c) => ({ ...c, [campo]: { ...c[campo], valor, corregido: true } }))

  const confirmarCampo = (campo) =>
    setCampos((c) => ({ ...c, [campo]: { ...c[campo], corregido: true } }))

  async function enviar() {
    setError(null)
    try {
      const payload = Object.fromEntries(Object.entries(campos).map(([k, v]) => [k, {
        valor: v.valor, confianza: v.confianza, fragmento: v.fragmento, corregido: v.corregido,
      }]))
      const r = await api.confirmar(payload)
      setResultado(r)
      onListo?.()
    } catch (e) { setError(e.message) }
  }

  if (resultado) {
    return (
      <div className="animar-entrada mx-auto max-w-md px-6 py-24 text-center">
        <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-apto/10 text-[22px] text-apto">
          ✓
        </div>
        <h1 className="text-[22px] font-semibold tracking-tight">Recibimos tu postulación</h1>
        <p className="mt-2 text-[14px] leading-relaxed text-tinta-suave">
          Gracias {resultado.nombre}. Vamos a revisar tus datos y te contactamos al
          teléfono que dejaste.
        </p>
        {resultado.campos_corregidos > 0 && (
          <p className="mt-4 text-[12px] text-piedra-400">
            Confirmaste o corregiste {resultado.campos_corregidos} dato(s) de tu CV.
          </p>
        )}
        <button className="btn-suave mt-8"
                onClick={() => { setResultado(null); setCampos(null); setExtraccion(null) }}>
          Cargar otro CV
        </button>
      </div>
    )
  }

  if (!campos) {
    return (
      <div className="space-y-5">
        <div
          onDragOver={(e) => { e.preventDefault(); setEncima(true) }}
          onDragLeave={() => setEncima(false)}
          onDrop={(e) => { e.preventDefault(); setEncima(false); subir(e.dataTransfer.files) }}
          onClick={() => entrada.current?.click()}
          className={`cursor-pointer rounded-3xl border-2 border-dashed p-12 text-center transition-all duration-300
            ${encima ? 'border-acento bg-acento-50' : 'border-piedra-300 bg-superficie hover:border-piedra-400'}`}
        >
          <input ref={entrada} type="file" accept=".pdf,.txt" className="hidden"
                 onChange={(e) => subir(e.target.files)} />
          <p className="text-[15px] font-medium">Sube tu CV y llenamos el formulario por ti</p>
          <p className="mx-auto mt-1.5 max-w-md text-[13px] text-tinta-suave">
            Después revisas lo que no se pudo leer bien. Si no tienes CV, también puedes
            llenar todo a mano.
          </p>
        </div>
        {leyendo && <Cargando texto="Leyendo el CV" />}
        {error && <Aviso onCerrar={() => setError(null)}>{error}</Aviso>}
        <button className="btn-fantasma mx-auto block"
                onClick={() => setCampos(Object.fromEntries(ORDEN.map((c) => [c, {
                  valor: null, confianza: 0, fragmento: null, estado: 'vacio', corregido: false,
                }])))}>
          No tengo CV, lo lleno a mano
        </button>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <div className="tarjeta flex flex-wrap items-center justify-between gap-3 p-4">
        <div>
          <p className="text-[14px] font-semibold">
            {porRevisar > 0 ? `${porRevisar} campo(s) por revisar` : 'Todo revisado'}
          </p>
          <p className="text-[12px] text-tinta-suave">
            {extraccion
              ? `Leímos el ${extraccion.completitud}% del CV con el motor ${extraccion.motor}. Lo amarillo necesita tu confirmación.`
              : 'Formulario en blanco: completa lo que sepas.'}
          </p>
        </div>
        <button className="btn-acento" onClick={enviar}>
          {porRevisar > 0 ? 'Enviar así' : 'Enviar postulación'}
        </button>
      </div>

      {error && <Aviso onCerrar={() => setError(null)}>{error}</Aviso>}

      <ul className="space-y-2.5">
        {ORDEN.filter((c) => campos[c]).map((campo) => (
          <Campo key={campo} campo={campo} dato={campos[campo]}
                 onCambiar={cambiar} onConfirmar={confirmarCampo} />
        ))}
      </ul>
    </div>
  )
}
