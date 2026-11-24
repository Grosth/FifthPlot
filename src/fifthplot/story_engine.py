"""Conector local para generar historias con Ollama."""

import json
import os
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from pydantic import ValidationError

from fifthplot.domain import Story, StoryRequest


DEFAULT_MODEL = "qwen3:4b-q4_K_M"
DEFAULT_BASE_URL = "http://127.0.0.1:11434"

SYSTEM_PROMPT = """Eres un cuentista que escribe en español.
Genera un cuento original con exactamente cinco escenas conectadas:
1 presenta personajes y situación; 2 y 3 desarrollan el conflicto;
4 contiene el momento decisivo; 5 resuelve la historia.
Conserva nombres, rasgos físicos y hechos relevantes.
Cada escena necesita un texto narrativo, acción y escenario describibles
en una ilustración completa, personajes presentes, una indicación de
ambiente sonoro sin voz ni música, y dirección de lectura.
Los campos visual_prompt, image_prompt y background_prompt deben estar en
inglés sencillo para Stable Diffusion 1.5. characters_present solo puede
contener nombres exactos de characters[].name. No incluyas objetos, alias,
traducciones ni títulos en characters_present. Si un objeto o criatura es
un personaje, primero inclúyelo en el reparto (máximo cuatro personajes).
Mantén cada narración en 2–4 frases y los prompts de imagen concisos.
No incluyas explicaciones fuera del objeto estructurado."""


class StoryGenerationError(RuntimeError):
    """Fallo visible durante la generación o validación narrativa."""


class OllamaStoryGenerator:
    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 600,
        transport=urlopen,
    ) -> None:
        self.model = model or os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", DEFAULT_BASE_URL)).rstrip("/")
        self.timeout = timeout
        self.transport = transport
        parsed = urlparse(self.base_url)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Ollama debe apuntar a localhost; no se permiten servicios remotos.")

    def generate(self, request: StoryRequest) -> Story:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Idea inicial: {request.idea}\n"
                    f"Género: {request.genre}\n"
                    "Devuelve el título, sinopsis, reparto, estilo visual y "
                    "exactamente cinco escenas completas. En cada escena, "
                    "characters_present debe reutilizar literalmente los "
                    "nombres escritos en el reparto."
                ),
            },
        ]
        try:
            return self._generate_story(messages)
        finally:
            # Ollama may keep mapped model pages briefly after its response,
            # even when the chat request used keep_alive=0. Explicitly unload
            # before Diffusers checks the machine's available RAM.
            self.release_model_memory()

    def _generate_story(self, messages: list[dict[str, str]]) -> Story:
        content = self._request(messages)
        try:
            return Story.model_validate_json(content)
        except (ValidationError, json.JSONDecodeError) as first_error:
            # Reparar una vez en el mismo modelo local y con la misma idea.
            # El validador sigue siendo la autoridad y la segunda respuesta
            # no se acepta si incumple las reglas del dominio.
            messages.extend(
                [
                    {"role": "assistant", "content": content},
                    {
                        "role": "user",
                        "content": (
                            "Corrige el JSON anterior para que cumpla el esquema "
                            "y las reglas de validación. Revisa en especial que "
                            "cada valor de characters_present sea exactamente "
                            "uno de los nombres del reparto; los objetos no son "
                            "personajes salvo que estén añadidos al reparto. "
                            "Conserva la historia y devuelve solo el JSON corregido. "
                            f"Error de validación: {first_error}"
                        ),
                    },
                ]
            )
            try:
                return Story.model_validate_json(self._request(messages))
            except (ValidationError, json.JSONDecodeError) as second_error:
                raise StoryGenerationError(
                    "Ollama no produjo una historia válida de cinco escenas "
                    f"tras un intento de reparación: {second_error}"
                ) from second_error

    def release_model_memory(self) -> bool:
        """Ask local Ollama to unload this model before image generation."""
        payload = {
            "model": self.model,
            "prompt": "",
            "stream": False,
            "keep_alive": 0,
        }
        req = Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self.transport(req, timeout=min(self.timeout, 30)) as response:
                response.read()
        except (OSError, TimeoutError):
            return False
        return True

    def _request(self, messages: list[dict[str, str]]) -> str:
        payload = {
            "model": self.model,
            "stream": False,
            "think": False,
            "keep_alive": 0,
            "format": Story.model_json_schema(),
            "messages": messages,
            "options": {
                "temperature": 0.7,
                "num_ctx": 4096,
                "num_predict": 3072,
            },
        }
        req = Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self.transport(req, timeout=self.timeout) as response:
                envelope = json.loads(response.read().decode("utf-8"))
            return envelope["message"]["content"]
        except URLError as exc:
            raise StoryGenerationError(
                "No se pudo conectar con Ollama local. Inicia Ollama y verifica "
                f"que esté disponible el modelo '{self.model}'."
            ) from exc
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise StoryGenerationError(f"Respuesta local de Ollama no válida: {exc}") from exc
