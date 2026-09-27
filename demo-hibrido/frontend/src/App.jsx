import { useCallback, useEffect, useState } from 'react'
import { api, pesos } from './api.js'
import { Aviso, Cargando, Marco, Pestanas } from './componentes/Basicos.jsx'
import Bandeja from './componentes/Bandeja.jsx'
import PanelDetalle from './componentes/PanelDetalle.jsx'
import Tablero from './componentes/Tablero.jsx'
import RevisionCampos from './componentes/RevisionCampos.jsx'

/* Demo C -- Híbrido. El CV prellena el formulario, una persona confirma lo
   dudoso, y recién ahí se califica. En el panel de detalle el reclutador puede
   corregir un dato después y el score se rehace al instante. */

export default function App() {
  const [vacante, setVacante] = useState(null)
  const [tablero, setTablero] = useState(null)
  const [mensajes, setMensajes] = useState([])
  const [pestana, setPestana] = useState('carga')
  const [abierto, setAbierto] = useState(null)
  const [error, setError] = useState(null)
  const [moviendo, setMoviendo] = useState(false)

  const refrescar = useCallback(async () => {
    try {
      const [t, b] = await Promise.all([api.tablero(), api.bandeja()])
      setTablero(t)
      setMensajes(b)
    } catch (e) { setError(e.message) }
  }, [])

  useEffect(() => {
    api.vacante().then(setVacante).catch((e) => setError(e.message))
    refrescar()
  }, [refrescar])

  async function mover(id, hacia) {
    try {
      await api.mover(id, hacia)
      await refrescar()
    } catch (e) { setError(e.message) }
  }

  async function aplicarSugerencias() {
    setMoviendo(true)
    try {
      const r = await api.aplicarSugerencias()
      await refrescar()
      setPestana('tablero')
      if (r.movidos === 0) setError('No hay candidatos nuevos para mover.')
    } catch (e) { setError(e.message) } finally { setMoviendo(false) }
  }

  if (!vacante) return <Cargando texto="Abriendo la vacante" />

  const pendientes = tablero?.conteo?.postulado ?? 0

  return (
    <Marco
      ancho={pestana === 'tablero'}
      titulo={vacante.titulo}
      bajada={`${vacante.municipio}, N.L. · ${pesos(vacante.salario_min)} a ${pesos(vacante.salario_max)}`}
      acciones={
        <button className="btn-primario" disabled={moviendo || !pendientes}
                onClick={aplicarSugerencias}>
          {moviendo ? 'Moviendo…' : `Aplicar sugerencias (${pendientes})`}
        </button>
      }
    >
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <Pestanas activa={pestana} onCambiar={setPestana} opciones={[
          { id: 'carga', nombre: 'Postular con CV' },
          { id: 'tablero', nombre: 'Tablero', cuenta: tablero ? Object.values(tablero.conteo).reduce((a, b) => a + b, 0) : null },
          { id: 'bandeja', nombre: 'Comunicaciones', cuenta: mensajes.length },
        ]} />
        <p className="text-[12px] text-piedra-400">
          El sistema propone; mover a un candidato lo decides tú.
        </p>
      </div>

      {error && <div className="mb-5"><Aviso onCerrar={() => setError(null)}>{error}</Aviso></div>}

      {pestana === 'carga' && <RevisionCampos onListo={refrescar} onAbrir={setAbierto} />}
      {pestana === 'tablero' && (!tablero
        ? <Cargando />
        : <Tablero tablero={tablero} onMover={mover} onAbrir={setAbierto} />)}
      {pestana === 'bandeja' && <Bandeja mensajes={mensajes} />}

      {abierto && (
        <>
          <div className="fixed inset-0 z-20 bg-tinta/10 backdrop-blur-[2px]"
               onClick={() => setAbierto(null)} />
          <PanelDetalle postulacionId={abierto} onCerrar={() => setAbierto(null)}
                        onMover={mover} permiteCorregir />
        </>
      )}
    </Marco>
  )
}
