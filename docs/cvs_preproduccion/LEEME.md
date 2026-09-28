# CVs de preproducción

CVs para probar la extracción contra algo parecido a la realidad. Los 15 de
`docs/cvs_prueba/` los genera el mismo código que conoce el modelo de datos, así
que salen demasiado limpios; estos no.

| Archivo | Qué prueba |
|---|---|
| `cv-formal-jose-luis-garza.pdf` | CV bien armado, hecho en Word con tabla de datos |
| `cv-informal-martin-cepeda.pdf` | Hoja de datos escrita a mano por el operador, con abreviaturas |
| `cv-incompleto-ramiro-tovar.pdf` | CV con huecos: sin apto médico, sin escolaridad, sin sueldo |
| `cv-escaneado-sin-texto.pdf` | La foto del CV sacada con el celular: no tiene texto que extraer |

Se regeneran con:

```bash
python -m core.seed.cvs_reales
```

## Cómo probarlos

- **Demo A:** arrastralos en `/carga`.
- **Demo C:** subilos en `/postular`, o mandalos por el chat en `/whatsapp`.
- El escaneado tiene que fallar **con un mensaje claro**, no romper la carga de
  los demás.
