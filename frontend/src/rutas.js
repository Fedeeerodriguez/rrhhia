/* Dos áreas separadas de verdad, no dos pestañas de la misma pantalla.

   `/postular`  es del candidato: solo la vacante y el formulario. No ve el
                pipeline, ni los puntajes, ni a los demás postulantes.
   `/`          es del reclutador: tablero, desglose y comunicaciones.

   Es una separación por URL y no un interruptor, porque el link público se
   comparte por WhatsApp y tiene que abrir directo en el formulario. */

export const RUTA_PUBLICA = '/postular'

export function esPublica(ruta = window.location.pathname) {
  return ruta.startsWith(RUTA_PUBLICA)
}

export function irA(ruta) {
  window.location.assign(ruta)
}
