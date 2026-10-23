"""Prueba de humo del notebook SIN red ni API key (LLM de CrewAI y embeddings simulados).

Qué verifica: que todas las celdas corren y que la orquestación jerárquica y la lógica
determinista (compuerta, auditoría, idempotencia, memoria) producen los estados esperados.
Qué NO verifica: la calidad de las respuestas del LLM real ni la ruta de function calling
nativa (el LLM simulado usa el formato ReAct de CrewAI). Para eso está la ejecución en Colab
con la key, cuyas salidas son la evidencia de la entrega.

Uso (desde la raíz del repositorio):
    pip install -r requirements.txt nbclient ipykernel
    python tests/prueba_sin_api/correr.py EP2_Agente_SH32.ipynb _prueba_sin_api "ruta/Manual electrico SH-32.pdf"
"""
import json, sys, shutil
from pathlib import Path
import nbformat
from nbclient import NotebookClient

nb_in, trabajo, manual = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve()
kernel = sys.argv[4] if len(sys.argv) > 4 else "python3"
shutil.rmtree(trabajo, ignore_errors=True)
(trabajo / "EP2_SH32/manuales").mkdir(parents=True)
shutil.copy(manual, trabajo / "EP2_SH32/manuales/Manual electrico SH-32.pdf")

nb = nbformat.read(nb_in, as_version=4)
fakes = (Path(__file__).parent / "fakes.py").read_text(encoding="utf-8")
nb.cells.insert(0, nbformat.v4.new_code_cell(fakes + "\nimport os\nos.environ['LLM_API_KEY']='clave-de-prueba'\n"))
for c in nb.cells:
    if c.cell_type == "code":
        c.source = c.source.replace("PAUSA_ENTRE_ESCENARIOS = 30", "PAUSA_ENTRE_ESCENARIOS = 0")

NotebookClient(nb, timeout=900, kernel_name=kernel, allow_errors=False,
               resources={"metadata": {"path": str(trabajo)}}).execute()
nbformat.write(nb, trabajo / "ejecutado_sin_api.ipynb")

ev = trabajo / "EP2_SH32/evidencias"
ots = {o["aeronave"] + "/" + o["componente"]: o for o in json.loads((ev / "ordenes_trabajo.json").read_text(encoding="utf-8"))}
correos = json.loads((ev / "correos_enviados.json").read_text(encoding="utf-8"))
tr = [json.loads(l) for l in (ev / "trazas_agente.jsonl").read_text(encoding="utf-8").splitlines()]
import csv
pruebas = list(csv.DictReader(open(ev / "pruebas_herramientas.csv", encoding="utf-8")))
checks = {
    "§4.1: todas las pruebas de herramientas OK": all(p["resultado"] == "OK" for p in pruebas),
    "A: OT 49P SH-32-01 ABIERTA": ots["SH-32-01/49P"]["estado"] == "ABIERTA",
    "A: pasó por los 3 especialistas": len(tr[0]["agentes"]) == 3,
    "A: sin correos": tr[0]["correos"] == [],
    "B: compuerta subió a ALTA lo que el agente propuso MEDIA": ots["SH-32-02/49P"]["ajustada_por_compuerta"] and ots["SH-32-02/49P"]["estado"] == "PENDIENTE_APROBACION_SUPERVISOR",
    "B: auditoría envió correo a supervisión": any("supervisión" in c for c in tr[1]["correcciones_auditoria"]),
    "C: OT TR2 EN_ESPERA_REPUESTO": ots["SH-32-03/TR2"]["estado"] == "EN_ESPERA_REPUESTO",
    "C: correo a abastecimiento (del agente)": any("abastecimiento" in c["para"] for c in tr[2]["correos"]),
    "D: fuera de dominio no escribe": tr[3]["ots_creadas"] == [] and tr[3]["correos"] == [],
    "D: buscar_manual dio SIN_RESULTADOS": tr[3]["secuencia"] == ["buscar_manual", "buscar_historial_fallas"],
    "E: seguimiento sin OT nueva, menciona OT del TR2": tr[4]["ots_creadas"] == [] and ots["SH-32-03/TR2"]["id"] in tr[4]["respuesta"],
    "F: sesión 2 sin OT nueva": tr[5]["ots_creadas"] == [] and tr[5]["sesion"] == "sesion-2",
    "Sin errores en las trazas": all(t["error"] is None for t in tr),
    "Evidencias: zip": (trabajo / "EP2_SH32/evidencias_EP2.zip").exists(),
}
for k, v in checks.items():
    print(("" if v else "") + k)
print("F respuesta:", tr[5]["respuesta"][:200])
sys.exit(0 if all(checks.values()) else 1)
