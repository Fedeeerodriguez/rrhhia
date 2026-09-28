import { useCallback, useEffect, useState } from 'react'
import { api, pesos } from './api.js'
import { esCarga, esPublica, RUTA_CARGA, RUTA_PUBLICA } from './rutas.js'
import { Aviso, Cargando, Marco, Pestanas } from './componentes/Basicos.jsx'
import Bandeja from './componentes/Bandeja.jsx'
import PanelDetalle from './componentes/PanelDetalle.jsx'
import PostulacionPublica from './componentes/PostulacionPublica.jsx'
import Tablero from './componentes/Tablero.jsx'
import ZonaCarga from './componentes/ZonaCarga.jsx'

/* Demo A -- CV first.

   Tres áreas separadas por URL, no tres pestañas:
     /postular   el candidato sube su CV. No ve nada interno.
     /carga      el reclutador sube CVs en lote (los que llegaron por mail).
     /           el pipeline y las comunicaciones. */

function useVacante() {
  const [vacante, setVacante] = useState(null)
  const [error, setError] = useState(null)
  useEffect(() => {
    api.vacante().then(setVacante).catch((e) => setError(e.message))
  }, [])
  return { vacante, error }
}

function AreaCandidato() {
  const { vacante, error } = useVacante()
  if (error) return <div className="mx-auto max-w-md px-6 py-20"><Aviso>{error}</Aviso></div>
  if (!vacante) return <Cargando texto="Abriendo la vacante" />
  return <PostulacionPublica vacante={vacante} />
}

function AreaCargaMasiva() {
  const { vacante, error } = useVacante()
  const [abierto, setAbierto] = useState(null)

  if (error) return <div className="mx-auto max-w-md px-6 py-20"><Aviso>{error}</Aviso></div>
  if (!vacante) return <Cargando texto="Abriendo la vacante" />

  return (
    <Marco
      titulo="Cargar CVs"
      bajada={`${vacante.titulo} · ${vacante.municipio}, N.L.`}
      acciones={<a className="btn-suave" href="/">Ir al tablero</a>}
    >
      <p className="mb-5 rounded-2xl bg-acento-50 px-4 py-3 text-[13px] text-acento">
        Para los CVs que te llegaron por mail o te dieron en papel. Los candidatos que
        se postulan solos entran por el link público.
      </p>
      <ZonaCarga onAbrir={setAbierto} />
      {abierto && (
        <>
          <div className="fixed inset-0 z-20 bg-tinta/10 backdrop-blur-[2px]"
               onClick={() => setAbierto(null)} />
          <PanelDetalle postulacionId={abierto} onCerrar={() => setAbierto(null)}
                        onMover={async (id, hacia) => { await api.mover(id, hacia) }} />
        </>
      )}
    </Marco>
  )
}

function AreaReclutador() {
  const { vacante } = useVacante()
  const [tablero, setTablero] = useState(null)
  const [mensajes, setMensajes] = useState([])
  const [pestana, setPestana] = useState('tablero')
  const [abierto, setAbierto] = useState(null)
  const [error, setError] = useState(null)
  const [moviendo, setMoviendo] = useState(false)
  const [evaluando, setEvaluando] = useState(false)

  const refrescar = useCallback(async () => {
    try {
      const [t, b] = await Promise.all([api.tablero(), api.bandeja()])
      setTablero(t)
      setMensajes(b)
    } catch (e) { setError(e.message) }
  }, [])

  useEffect(() => { refrescar() }, [refrescar])

  // Las postulaciones entran por otras pantallas (y por WhatsApp): el tablero
  // se refresca solo para que el reclutador las vea aparecer.
  useEffect(() => {
    const id = setInterval(refrescar, 30000)
    return () => clearInterval(id)
  }, [refrescar])

  async function mover(id, hacia) {
    try {
      await api.mover(id, hacia)
      await refrescar()
    } catch (e) { setError(e.message) }
  }

  async function evaluarConIA() {
    setEvaluando(true)
    try {
      const r = await api.evaluarIA()
      await refrescar()
      if (!r.evaluadas) setError(r.motivo ?? 'No hay candidatos para evaluar.')
    } catch (e) { setError(e.message) } finally { setEvaluando(false) }
  }

  async function aplicarSugerencias() {
    setMoviendo(true)
    try {
      const r = await api.aplicarSugerencias()
      await refrescar()
      if (r.movidos === 0) setError('No hay candidatos nuevos para mover.')
    } catch (e) { setError(e.message) } finally { setMoviendo(false) }
  }

  if (!vacante) return <Cargando texto="Abriendo la vacante" />

  const pendientes = tablero?.conteo?.postulado ?? 0
  // Todos los candidatos se evalúan, estén en la columna que estén: la IA no
  // descarta, muestra quiénes son los más aptos.
  const sinEvaluar = (tablero?.columnas ?? [])
    .flatMap((c) => c.candidatos)
    .filter((c) => !c.nivel_ia).length

  return (
    <Marco
      ancho={pestana === 'tablero'}
      titulo={vacante.titulo}
      bajada={`${vacante.municipio}, N.L. · ${pesos(vacante.salario_min)} a ${pesos(vacante.salario_max)}`}
      acciones={
        <div className="flex flex-wrap items-center gap-2">
          <a className="btn-suave" href={RUTA_PUBLICA} target="_blank" rel="noreferrer">
            Link de postulación
          </a>
          <a className="btn-suave" href={RUTA_CARGA}>Cargar CVs</a>
          <button className="btn-suave" disabled={evaluando || !sinEvaluar}
                  onClick={evaluarConIA}
                  title="Evalúa a todos los candidatos, cumplan o no los requisitos">
            {evaluando ? 'Evaluando…' : `Evaluar con IA (${sinEvaluar})`}
          </button>
          <button className="btn-primario" disabled={moviendo || !pendientes}
                  onClick={aplicarSugerencias}>
            {moviendo ? 'Moviendo…' : `Aplicar sugerencias (${pendientes})`}
          </button>
        </div>
      }
    >
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <Pestanas activa={pestana} onCambiar={setPestana} opciones={[
          { id: 'tablero', nombre: 'Tablero' },
          { id: 'bandeja', nombre: 'Comunicaciones', cuenta: mensajes.length },
        ]} />
        <p className="text-[12px] text-piedra-400">
          El sistema propone; mover a un candidato lo decides tú.
        </p>
      </div>

      {error && <div className="mb-5"><Aviso onCerrar={() => setError(null)}>{error}</Aviso></div>}

      {!tablero ? <Cargando /> : pestana === 'tablero'
        ? <Tablero tablero={tablero} onMover={mover} onAbrir={setAbierto} />
        : <Bandeja mensajes={mensajes} />}

      {abierto && (
        <>
          <div className="fixed inset-0 z-20 bg-tinta/10 backdrop-blur-[2px]"
               onClick={() => setAbierto(null)} />
          <PanelDetalle postulacionId={abierto} onCerrar={() => setAbierto(null)} onMover={mover} />
        </>
      )}
    </Marco>
  )
}

export default function App() {
  if (esPublica()) return <AreaCandidato />
  if (esCarga()) return <AreaCargaMasiva />
  return <AreaReclutador />
}
