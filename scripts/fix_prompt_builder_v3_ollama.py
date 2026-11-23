from pathlib import Path
import shutil

archivo = Path(
    "src/fifthplot/generators/prompt_builder_v3.py"
)

codigo = archivo.read_text(encoding="utf-8-sig")

inicio = codigo.find("def llamar_qwen(")
final = codigo.find("\ndef contar_tokens(", inicio)

if inicio == -1 or final == -1:
    raise RuntimeError(
        "No se encontro la funcion llamar_qwen."
    )

nueva_funcion = '''def llamar_qwen(prompt, max_predict=1800):

    ultimo_error = None

    for intento in range(1, 3):

        payload = {
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.15 if intento == 1 else 0.0,
                "num_predict": max_predict if intento == 1 else max_predict + 400,
                "num_ctx": 4096
            }
        }

        request = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(
                request, timeout=900
            ) as response:

                data = json.loads(
                    response.read().decode("utf-8")
                )

        except urllib.error.URLError as error:
            ultimo_error = f"Error de conexion: {error}"
            print(ultimo_error)
            continue

        if data.get("error"):
            ultimo_error = data["error"]
            print("Error de Ollama:", ultimo_error)
            continue

        texto = data.get("response", "")

        if not isinstance(texto, str) or not texto.strip():

            motivo = data.get("done_reason", "no informado")

            ultimo_error = (
                f"Respuesta vacia de Qwen3. "
                f"Motivo: {motivo}. "
                f"Intento: {intento}/2."
            )

            print(ultimo_error)
            continue

        try:
            resultado = json.loads(texto)

        except json.JSONDecodeError as error:

            ultimo_error = (
                f"JSON incorrecto: {error}. "
                f"Respuesta recibida: {texto[:250]}"
            )

            print(ultimo_error)
            continue

        if not isinstance(resultado, dict):
            ultimo_error = "Qwen3 no devolvio un objeto JSON."
            print(ultimo_error)
            continue

        return resultado

    raise RuntimeError(
        "Qwen3 no produjo una respuesta JSON valida "
        f"despues de dos intentos. Detalle: {ultimo_error}"
    )


'''

codigo_nuevo = (
    codigo[:inicio]
    + nueva_funcion
    + codigo[final + 1:]
)

compile(codigo_nuevo, str(archivo), "exec")

respaldo = Path(
    "docs/evidence/backups/prompt_builder_v3_before_qwen_retry.py.txt"
)

respaldo.parent.mkdir(parents=True, exist_ok=True)

if not respaldo.exists():
    shutil.copy2(archivo, respaldo)

archivo.write_text(
    codigo_nuevo,
    encoding="utf-8"
)

print("Comunicacion con Ollama corregida.")
print("Reintentos automaticos: 2.")
print("Validacion JSON activada.")
print("Respaldo:", respaldo)
