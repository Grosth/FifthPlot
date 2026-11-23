# Incidencias de desarrollo

Este registro conserva incidencias observadas durante la preparación del proyecto. No es un listado de pruebas ni identifica quién ejecutó pruebas. No se añaden fechas retrospectivas cuando no quedaron anotadas en el momento.

## Python y resolución de dependencias

- **Observación:** El rango de Python declarado en `pyproject.toml` permitía versiones futuras, pero PyTorch estaba fijado al entorno CUDA auditado de Python 3.12; la resolución offline de `uv` no podía completar el lock con esa especificación amplia.
- **Corrección:** Se acotó el proyecto a Python `>=3.12,<3.13` y se regeneró `uv.lock`.
- **Estado observado:** El lock quedó resuelto con 123 paquetes y la comprobación offline de consistencia terminó correctamente.

## Captura inicial de la interfaz

- **Observación:** La primera captura del navegador sin interfaz gráfica produjo una imagen negra antes de que Gradio terminara de renderizar.
- **Corrección:** Se esperó a que la página local completara el render antes de guardar la imagen.
- **Resultado:** La captura real de la pantalla inicial está en [fifthplot-formulario-inicial.png](screenshots/01-interfaz/fifthplot-formulario-inicial.png) y se describe en [index.md](index.md). La imagen negra se descartó y no forma parte de las evidencias.

## Referencia de personaje con IP-Adapter

- **Observación:** La generación de la imagen de referencia fallaba con `TypeError` porque IP-Adapter ya estaba activado y Diffusers esperaba embeddings de imagen antes de que existiera una referencia.
- **Corrección:** La referencia ahora se genera primero con el pipeline base de DreamShaper; después se libera ese pipeline y se carga IP-Adapter para ilustrar las escenas. El prompt de referencia se acortó para reducir el truncamiento del codificador CLIP.
- **Resultado observado:** La ejecución completa `20261123_014610_11ebec14` finalizó con estado `complete` y creó una referencia de personaje más cinco escenas. La primera escena fue inspeccionada visualmente. Los detalles verificables están en su `manifest.json`.

## Longitud de prompts visuales

- **Observación:** Los prompts sin límite excedían el máximo de 77 tokens de CLIP (entre 150 y 222 tokens), por lo que el codificador descartaba parte de la descripción.
- **Corrección:** Se incorporó una construcción de prompt con límite de 70 tokens para cada escena.
- **Resultado observado:** La generación completa `20261123_014610_11ebec14` registró prompts acotados y creó las cinco imágenes. La inspección visual directa de `scene_01.png` confirmó una ilustración legible; queda pendiente la revisión comparativa de las cinco escenas y una captura real de la ejecución/interfaz para el informe.

## Límite de recursos para inferencia

- **Observación previa al reinicio:** Había 2,09 GB de RAM disponible y 2.897 MiB de VRAM libre. Ollama tenía Qwen3 4B Q4 descargado, sin un modelo activo.
- **Decisión técnica:** No se cargaron modelos de inferencia ni se inició generación de imágenes con ese margen. El generador visual comprueba la RAM disponible y se detiene si queda por debajo del mínimo configurado.
- **Resultado posterior al reinicio:** Se generó la historia local `La Brújula de los Sueños Perdidos` con cinco escenas e ilustraciones; el manifiesto informa 4,43 GB de RAM disponible al cerrar esa ejecución. Esto no completa las tres historias de géneros distintos ni la comparación controlada de estrategias, que siguen pendientes.

## Protección de memoria y elección de estrategia

- **Observación:** En la ejecución desde la interfaz, la etapa de historia terminó, pero el control de IP-Adapter detuvo la ilustración al medir 5,0 GB libres, por debajo del mínimo configurado de 6 GB. Tras cerrar Paint vacío y Overwolf se liberó memoria; la generación de historia volvió a consumir parte de ese margen y el control volvió a detener IP-Adapter con 5,3 GB libres. No se forzó la carga del modelo.
- **Corrección funcional:** Se añadió a la interfaz un selector entre IP-Adapter y `text_only`, cuya precondición requiere 4 GB libres.
- **Resultado observado:** La ejecución supervisada `20261123_021143_e0298b90` terminó con estado `complete` usando `text_only`: cinco ilustraciones, narración y ambiente por escena. El manifiesto registra 2,84 GB disponibles al cierre. La interfaz mostró el resultado y sus controles; la captura de pantalla del resultado queda pendiente.
