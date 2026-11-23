from pathlib import Path
from huggingface_hub import snapshot_download

repositorio = "h94/IP-Adapter"
destino = Path("models/ip-adapter")

destino.mkdir(parents=True, exist_ok=True)

archivos = [
    "models/image_encoder/config.json",
    "models/image_encoder/model.safetensors",
    "models/ip-adapter-plus_sd15.safetensors"
]

print("Descargando IP-Adapter Plus...")
print("Se descargaran solamente los archivos necesarios.")

ruta = snapshot_download(
    repo_id=repositorio,
    local_dir=str(destino),
    allow_patterns=archivos,
    max_workers=2
)

print("\nDescarga completada.")
print(f"Ubicacion: {ruta}")

for archivo in archivos:
    ruta_archivo = destino / archivo

    if not ruta_archivo.exists():
        raise FileNotFoundError(f"No se encontro: {archivo}")

    print(f"{archivo}: {ruta_archivo.stat().st_size / (1024**2):.2f} MB")

print("\nIP-Adapter Plus preparado correctamente.")
