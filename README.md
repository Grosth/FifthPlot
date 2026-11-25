# FifthPlot

FifthPlot convierte una idea y un género en un cuento local de exactamente cinco escenas. Cada escena incluye narración, ilustración, voz sintética y una pista ambiental independiente.

## Estado

La reconstrucción está en curso. El flujo narrativo, el validador, la persistencia local, el audio ambiental procedural y la síntesis Piper están implementados. La estrategia local `text_only` ha completado varias generaciones manuales de cinco escenas. Se fijó una dirección visual de cuento infantil en acuarela y anclajes compactos de personajes; el estudiante revisó las nuevas salidas en varias historias y considera que cumplen el objetivo visual actual. La continuidad de cada reparto sigue sujeta a revisión de las cinco escenas. La interfaz permite elegir `text_only` o IP-Adapter según los recursos disponibles. Falta validar IP-Adapter desde la interfaz y hacer una comparación controlada de estrategias.

## Requisitos del equipo

- Windows de 64 bits, PowerShell y Python 3.12.
- uv para instalar dependencias y ejecutar FifthPlot.
- Ollama local con qwen3:4b-q4_K_M.
- DreamShaper 8 e IP-Adapter Plus SD15 en las rutas locales indicadas abajo.
- GPU NVIDIA con CUDA. En el equipo auditado: RTX 3050 Laptop con 4 GB de VRAM y 16 GB de RAM.

La generación procesa una escena a la vez. El manifiesto registra tiempos por escena, RAM disponible y memoria máxima de GPU. En el equipo de 16 GB, el servidor puede quedar con menos de 4 GB disponibles después de generar un cuento; si la siguiente ejecución falla la comprobación de memoria, reinicia el servidor local antes de reintentar.

## Instalación en Windows

Desde PowerShell, en la raíz del repositorio:

~~~powershell
uv sync
~~~

La aplicación usa uv.lock para reproducir las versiones. La instalación inicial requiere Internet para dependencias y modelos que falten; la generación normal usa Ollama local, los pesos locales y la voz local. Después de preparar el equipo puede ejecutarse sin conexión.

## Modelos locales

FifthPlot no usa APIs de pago ni servicios de inferencia remotos durante la generación.

| Uso | Modelo o recurso | Ruta esperada | Licencia / procedencia |
|---|---|---|---|
| Historia | Qwen3 4B Q4_K_M en Ollama | Instalación de Ollama | Apache 2.0 |
| Ilustración | DreamShaper 8 FP16 | models/dreamshaper-8/ | CreativeML OpenRAIL-M; sus restricciones de uso siguen aplicando |
| Referencia visual | IP-Adapter Plus SD15 | models/ip-adapter/ | Apache 2.0 |
| Voz | Piper es_ES-carlfm-x_low | models/voices/ | Tarjeta local: dominio público, entrenada desde cero |
| Ambiente | Síntesis procedural de FifthPlot | Se genera por escena | Código local; no usa grabaciones descargadas |

La voz es_ES-davefx-medium también está en el almacenamiento local, pero FifthPlot no la usa: la tarjeta de esa copia informa una cadena de entrenamiento distinta a la que el registro de Piper asocia con la licencia actual. Se conserva sin borrarla hasta aclarar la discrepancia.

Los pesos no se guardan en Git. Antes de descargar modelos, comprueba primero las carpetas models/ y el caché local de Ollama para evitar copias duplicadas. Conserva junto a cada voz su MODEL_CARD; las voces tienen condiciones propias, aunque el motor Piper esté bajo GPL.

Para obtener la voz seleccionada con Piper:

~~~powershell
uv run python -m piper.download_voices --download-dir models/voices es_ES-carlfm-x_low
~~~

Guarda también la tarjeta MODEL_CARD de la carpeta es/es_ES/carlfm/x_low del repositorio rhasspy/piper-voices como models/voices/es_ES-carlfm-x_low.MODEL_CARD.

## Ollama

Instala e inicia Ollama localmente. Comprueba que el modelo qwen3:4b-q4_K_M exista en Ollama. Si falta, descárgalo durante la instalación inicial:

~~~powershell
ollama pull qwen3:4b-q4_K_M
~~~

La aplicación rechaza una dirección de Ollama que no sea loopback. No envía la idea, el género ni la historia a un servicio remoto.

## Ejecución

~~~powershell
uv run fifthplot
~~~

La interfaz solo escucha en 127.0.0.1 y desactiva la opción de compartir públicamente. El formulario pide la idea y el género; la estrategia visual inicia en `text_only`, de menor uso de RAM, y permite elegir IP-Adapter para una comparación. Todas las escenas comparten una dirección visual fija de cuento infantil en acuarela y anclajes compactos por personaje. IP-Adapter genera una referencia de reparto específica para cada escena. Cada escena muestra su ilustración y texto, con controles de voz y ambiente separados.

## Salidas

Cada cuento se guarda en outputs/storybooks/ con:

- story.json: reparto y exactamente cinco escenas.
- scene_01.png a scene_05.png: imágenes completas de cada escena.
- scene_01/ a scene_05/: voz y ambiente separados.
- manifest.json: modelos, parámetros, versiones, tiempos, archivos y estado de la ejecución.

Los registros y experimentos previos permanecen en experiments/ y outputs/.

## Pruebas

Ejecuta las pruebas unitarias y las pruebas de integración simulada con:

~~~powershell
uv run --no-sync python -m unittest discover -v
~~~

Las pruebas automatizadas no descargan modelos ni hacen llamadas a Ollama. Las pruebas reales con GPU y las tres historias de géneros distintos se registrarán por separado en experiments/.

## Evidencias académicas

Las capturas reales y sus descripciones se organizan en [docs/evidence/README.md](docs/evidence/README.md) y se indexan en [docs/evidence/index.md](docs/evidence/index.md). Las incidencias conocidas se mantienen en [docs/evidence/incidencias.md](docs/evidence/incidencias.md). No se registran como evidencia académica los resultados que no haya supervisado o ejecutado manualmente el estudiante.

## Vista pública de revisión en Render

El archivo `render.yaml` publica `deploy/render/` como sitio estático desde la rama `codex/visual-identity`. La página permite recorrer una historia generada previamente por FifthPlot, con sus cinco ilustraciones, narraciones y ambientes. Es una vista de revisión; no genera cuentos nuevos en Render.

La generación completa se mantiene local porque requiere Ollama, Qwen, PyTorch, DreamShaper y archivos de modelos que no se distribuyen en Git. La página pública lo indica para que su contenido no se confunda con una ejecución en la nube.

## Licencias

El código de FifthPlot se distribuye bajo GNU GPL versión 3 o posterior, para mantener compatibilidad con el motor Piper incluido. Las licencias de los pesos y voces son independientes: revisa la tarjeta y las condiciones de cada modelo antes de redistribuirlo. Los modelos se excluyen del repositorio Git.

## Arquitectura

~~~mermaid
flowchart LR
    A["Idea + género"] --> B["Ollama local / Qwen"]
    B --> C["Historia validada: cinco escenas"]
    C --> D["Constructor de prompts"]
    D --> E["Diffusers + IP-Adapter"]
    C --> F["Piper local"]
    C --> G["Ambiente procedural"]
    E --> H["Biblioteca local del cuento"]
    F --> H
    G --> H
    H --> I["Interfaz Gradio local"]
~~~
