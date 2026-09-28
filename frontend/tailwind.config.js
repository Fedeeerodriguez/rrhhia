/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        papel: '#FBFBFA',
        superficie: '#FFFFFF',
        borde: '#E8E6E1',
        tinta: { DEFAULT: '#16181D', suave: '#5A6068' },
        acento: { DEFAULT: '#2C4A7C', 700: '#213A64', 50: '#EEF2F8' },
        piedra: {
          50: '#F8F7F5', 100: '#F1EFEC', 200: '#E4E1DB',
          300: '#D2CEC6', 400: '#A8A39A', 500: '#7C776E',
        },
        // Reservados para el scoring. No usar de decoracion.
        apto: '#1C7A55',
        alerta: '#B07A1E',
        fuera: '#B23B32',
      },
      boxShadow: {
        suave: '0 1px 2px rgba(22,24,29,0.04), 0 8px 24px rgba(22,24,29,0.05)',
        panel: '0 4px 12px rgba(22,24,29,0.06), 0 24px 56px rgba(22,24,29,0.09)',
      },
      maxWidth: { contenido: '1240px', ancho: '1680px' },
    },
  },
  plugins: [],
}
