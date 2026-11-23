import shutil
import time
from pathlib import Path

from huggingface_hub import snapshot_download


REPOSITORIO = "Lykon/dreamshaper-8"
DESTINO = Path("models/dreamshaper-8")

# Solo descargamos los archivos FP16 y sus configuraciones.
ARCHIVOS = [
    "README.md",
    "model_index.json",

    "feature_extractor/preprocessor_config.json",

    "safety_checker/config.json",
    "safety_checker/model.fp16.safetensors",

    "scheduler/scheduler_config.json",

    "text_encoder/config.json",
    "text_encoder/model.fp16.safetensors",

    "tokenizer/merges.txt",
    "tokenizer/special_tokens_map.json",
    "tokenizer/tokenizer_config.json",
    "tokenizer/vocab.json",

    "unet/config.json",
    "unet/diffusion_pytorch_model.fp16.safetensors",

    "vae/config.json",
    "vae/diffusion_pytorch_model.fp16.safetensors"
]


def main():

    espacio_libre = shutil.disk_usage(
        Path.cwd()
    ).free / (1024 ** 3)

    print("=" * 55)
    print("FIFTHPLOT - DESCARGA DE DREAMSHAPER 8")
    print("=" * 55)

    print(f"Repositorio: {REPOSITORIO}")
    print(f"Destino: {DESTINO}")
    print(f"Espacio libre: {espacio_libre:.2f} GB")

    if espacio_libre < 5:
        raise RuntimeError(
            "No hay suficiente espacio libre para descargar el modelo."
        )

    DESTINO.mkdir(parents=True, exist_ok=True)

    print("\nArchivos seleccionados:")
    print("UNet FP16")
    print("Text Encoder FP16")
    print("VAE FP16")
    print("Safety Checker FP16")
    print("Tokenizer y configuraciones")

    print("\nDescargando componentes...")
    print("Esto puede tardar algunos minutos.\n")

    inicio = time.perf_counter()

    ruta = snapshot_download(
        repo_id=REPOSITORIO,
        local_dir=str(DESTINO),
        allow_patterns=ARCHIVOS,
        max_workers=2
    )

    tiempo = time.perf_counter() - inicio

    # Comprobamos que los componentes principales existan.
    obligatorios = [
        "model_index.json",
        "unet/config.json",
        "unet/diffusion_pytorch_model.fp16.safetensors",
        "text_encoder/model.fp16.safetensors",
        "vae/diffusion_pytorch_model.fp16.safetensors",
        "safety_checker/model.fp16.safetensors",
        "tokenizer/vocab.json",
        "scheduler/scheduler_config.json"
    ]

    faltantes = [
        archivo for archivo in obligatorios
        if not (DESTINO / archivo).is_file()
    ]

    if faltantes:
        raise RuntimeError(
            f"Faltan archivos del modelo: {faltantes}"
        )

    pesos = list(DESTINO.rglob("*.safetensors"))

    espacio_modelo = sum(
        archivo.stat().st_size for archivo in pesos
    ) / (1024 ** 3)

    espacio_final = shutil.disk_usage(
        Path.cwd()
    ).free / (1024 ** 3)

    print("\nDESCARGA COMPLETADA")
    print("-" * 45)
    print("Ubicacion:", ruta)
    print("Pesos descargados:")

    for archivo in pesos:
        tamanio = archivo.stat().st_size / (1024 ** 2)
        print(f"  {archivo.relative_to(DESTINO)}: {tamanio:.2f} MB")

    print(f"\nTamano de los pesos: {espacio_modelo:.2f} GB")
    print(f"Tiempo: {tiempo:.2f} segundos")
    print(f"Espacio libre restante: {espacio_final:.2f} GB")

    print("\nTodos los componentes fueron verificados.")


if __name__ == "__main__":
    main()
