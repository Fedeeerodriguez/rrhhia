import { useCallback, useEffect, useState } from 'react'
import { api, pesos } from './api.js'
import { Aviso, Cargando, Marco, Pestanas } from './componentes/Basicos.jsx'
import Bandeja from './componentes/Bandeja.jsx'
import FormularioPublico from './componentes/FormularioPublico.jsx'
import PanelDetalle from './componentes/PanelDetalle.jsx'
import Tablero from './componentes/Tablero.jsx'

/* Demo B -- Formulario.
   Dos vistas: el link publico del candidato y el tablero del reclutador. Se
   alternan con un interruptor arriba para poder mostrar las dos en la demo. */

export default function App() {
  const [vista, setVista] = useState('reclutador')
  const [vacante, setVacante] = useState(null)
  const [tablero, setTablero] = useState(null)
  const [mensajes, setMensajes] = useState([])
  const [pestana, setPestana] = useState('tablero')
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
      if (r.movidos === 0) setError('No hay candidatos nuevos para mover.')
    } catch (e) { setError(e.message) } finally { setMoviendo(false) }
  }

  if (!vacante) return <Cargando texto="Abriendo la vacante" />

  if (vista === 'candidato') {
    return (
      <>
        <div className="flex justify-center pt-5">
          <Pestanas activa={vista} onCambiar={setVista} opciones={[
            { id: 'reclutador', nombre: 'Vista del reclutador' },
            { id: 'candidato', nombre: 'Vista del candidato' },
          ]} />
        </div>
        <FormularioPublico vacante={vacante} onListo={refrescar} />
      </>
    )
  }

  const pendientes = tablero?.conteo?.postulado ?? 0

  return (
    <Marco
      ancho={pestana === 'tablero'}
      titulo={vacante.titulo}
      bajada={`${vacante.municipio}, N.L. · ${pesos(vacante.salario_min)} a ${pesos(vacante.salario_max)}`}
      acciones={
        <div className="flex flex-wrap items-center gap-2">
          <Pestanas activa={vista} onCambiar={setVista} opciones={[
            { id: 'reclutador', nombre: 'Reclutador' },
            { id: 'candidato', nombre: 'Formulario público' },
          ]} />
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
          <PanelDetalle postulacionId={abierto} onCerrar={() => setAbierto(null)}
                        onMover={mover} />
        </>
      )}
    </Marco>
  )
}
