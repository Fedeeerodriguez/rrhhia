/* Dos áreas separadas de verdad, no dos pestañas de la misma pantalla.

   `/postular`  es del candidato: solo la vacante y el formulario. No ve el
                pipeline, ni los puntajes, ni a los demás postulantes.
   `/`          es del reclutador: tablero, desglose y comunicaciones.

   Es una separación por URL y no un interruptor, porque el link público se
   comparte por WhatsApp y tiene que abrir directo en el formulario. */

export const RUTA_PUBLICA = '/postular'
// La carga masiva es trabajo del reclutador, pero tampoco vive dentro del
// pipeline: es otra tarea y tiene su propia pantalla.
export const RUTA_CARGA = '/carga'

export function esPublica(ruta = window.location.pathname) {
  return ruta.startsWith(RUTA_PUBLICA)
}

export function esCarga(ruta = window.location.pathname) {
  return ruta.startsWith(RUTA_CARGA)
}

export function irA(ruta) {
  window.location.assign(ruta)
}
