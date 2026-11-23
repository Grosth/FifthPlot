from pathlib import Path
from huggingface_hub import snapshot_download

# Modelo seleccionado.
REPO_ID = "stable-diffusion-v1-5/stable-diffusion-v1-5"

# Carpeta local del modelo.
LOCAL_DIR = Path("models/stable-diffusion-v1-5")
LOCAL_DIR.mkdir(parents=True, exist_ok=True)

# Descargamos unicamente los pesos FP16 y sus configuraciones.
ARCHIVOS = [
    "model_index.json",
    "feature_extractor/preprocessor_config.json",
    "scheduler/scheduler_config.json",
    "tokenizer/*",
    "text_encoder/config.json",
    "text_encoder/model.fp16.safetensors",
    "unet/config.json",
    "unet/diffusion_pytorch_model.fp16.safetensors",
    "vae/config.json",
    "vae/diffusion_pytorch_model.fp16.safetensors",
    "safety_checker/config.json",
    "safety_checker/model.fp16.safetensors",
]

print("Descargando Stable Diffusion 1.5...")
print("Solo se descargaran los archivos FP16 seleccionados.")

try:
    ruta = snapshot_download(
        repo_id=REPO_ID,
        local_dir=str(LOCAL_DIR),
        allow_patterns=ARCHIVOS,
        max_workers=2
    )

    archivos = [
        archivo for archivo in LOCAL_DIR.rglob("*")
        if archivo.is_file()
        and ".cache" not in archivo.parts
    ]

    total = sum(archivo.stat().st_size for archivo in archivos)

    print("\nDescarga completada.")
    print(f"Ubicacion: {ruta}")
    print(f"Archivos descargados: {len(archivos)}")
    print(f"Espacio ocupado: {total / (1024**3):.2f} GB")

except Exception as error:
    print(f"\nError durante la descarga: {error}")
    raise
