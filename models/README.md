# Modelos locales de FifthPlot

No subas archivos de pesos a Git. Antes de descargar modelos, comprueba las rutas y el caché de Ollama para evitar copias.

## Rutas

- DreamShaper 8: models/dreamshaper-8/
- IP-Adapter Plus SD15 y su image encoder: models/ip-adapter/
- Voz Piper es_ES-carlfm-x_low: models/voices/
- Qwen3 4B Q4_K_M: almacenado por Ollama en su directorio local de modelos.

## Licencias y procedencia

- DreamShaper 8: el README local indica CreativeML OpenRAIL-M. Revisa las restricciones del modelo original antes de redistribuir o reutilizar sus salidas.
- IP-Adapter: la ficha de h94/IP-Adapter declara Apache 2.0.
- Piper es_ES-carlfm-x_low: la tarjeta descargada indica español de España, calidad x_low, datos de dominio público y entrenamiento desde cero. Conserva la tarjeta con la voz.
- Piper es_ES-davefx-medium: copia local conservada sin uso. Su tarjeta actual indica afinado desde la voz lessac, aunque la lista reciente de licencias de Piper muestra otra cadena. No utilizar hasta verificar la procedencia exacta de esa copia.
- Qwen3 4B: Apache 2.0. El modelo se ejecuta en Ollama local.

El motor Piper se distribuye bajo GPL-3.0-or-later. FifthPlot usa esa licencia para mantener compatibilidad con el motor integrado.
