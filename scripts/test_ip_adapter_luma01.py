from pathlib import Path
import torch

from fifthplot.generators import ip_adapter_test as experimento

# Utilizamos la primera ilustracion como referencia.
experimento.REFERENCE = Path("outputs/images/luma_prueba_01.png")

# Comprobamos la disponibilidad de los archivos.
experimento.comprobar_archivos()

if not torch.cuda.is_available():
    raise RuntimeError("No se detecto CUDA.")

# Guardamos este ensayo en una carpeta independiente.
salida = Path("experiments/configuration_b_luma01")

print("\nFIFTHPLOT - PRUEBA B2")
print("Referencia: primera ilustracion de Luma")
print("IP-Adapter Scale:", experimento.ADAPTER_SCALE)

experimento.generar_prueba(
    "B_luma01",
    salida,
    usar_adapter=True
)

print("\nPrueba B2 finalizada.")
