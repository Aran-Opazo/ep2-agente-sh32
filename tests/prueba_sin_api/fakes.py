"""Dobles de prueba para ejecutar el notebook jerárquico SIN red ni API key.
- Embeddings por hashing de palabras (deterministas, normalizados).
- LLM de CrewAI falso (formato ReAct): el Manager delega Diagnosticador → Planificador →
  Coordinador en los reportes; a propósito el Coordinador propone criticidad MEDIA siempre
  (prueba la compuerta) y nunca avisa a supervisión (prueba la auditoría).
Valida la orquestación y la lógica determinista, NO la calidad del LLM real.
"""
import sys, types, re, json, hashlib, math
from typing import Any
from langchain_core.embeddings import Embeddings


class HashEmbeddings(Embeddings):
    def __init__(self, *a, **k):
        self.dim = 256
    def _vec(self, t):
        v = [0.0] * self.dim
        for w in re.findall(r"\w+", t.lower()):
            if len(w) < 3:
                continue
            v[int(hashlib.md5(w.encode()).hexdigest(), 16) % self.dim] += 1.0
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]
    def embed_documents(self, texts): return [self._vec(t) for t in texts]
    def embed_query(self, text): return self._vec(text)

mod_hf = types.ModuleType("langchain_huggingface")
mod_hf.HuggingFaceEmbeddings = HashEmbeddings
sys.modules["langchain_huggingface"] = mod_hf

import crewai
from crewai import BaseLLM

CODIGOS = ["33P5", "TR1", "TR2", "49P", "58X", "35X1", "35X2", "37X1", "BAT-24V"]
LLAMADAS = {"n": 0}

def _sol(texto):
    m = re.search(r"SOLICITUD: (.*)", texto)
    return m.group(1).strip() if m else ""

def _codigo(sol):
    c = next((c for c in CODIGOS if c.lower() in sol.lower()), None)
    return c or ("33P5" if "interbarras" in sol.lower() else "SIN-CODIGO")

def _es_reporte(sol):
    return bool(re.search(r"\breport(o|a|amos|an)\b|falla en (la )?aeronave|se encendi|se enciende|"
                          r"no entrega|disparo", sol, re.I))

def _accion(paso, herr, args):
    return (f"Thought: [paso {paso}] uso {herr}\nAction: {herr}\n"
            f"Action Input: {json.dumps(args, ensure_ascii=False)}")

def _final(texto):
    return f"Thought: I now know the final answer\nFinal Answer: {texto}"


class FakeLLM(BaseLLM):
    def __init__(self, model="fake", **kw):
        super().__init__(model=str(model), temperature=kw.get("temperature"))

    def call(self, messages, tools=None, callbacks=None, available_functions=None,
             from_task=None, from_agent=None, response_model=None, **kw):
        LLAMADAS["n"] += 1
        if isinstance(messages, str):
            return "funcionando"
        todo = "\n".join(str(m.get("content", "")) for m in messages)
        rol = (re.search(r"You are (.+?)\. ", todo) or [None, ""])[1]
        pasos = sum(str(m.get("content", "")).count("[paso ") for m in messages if m.get("role") == "assistant")
        obs = "\n".join(str(m.get("content", "")) for m in messages if m.get("role") != "system")
        sol = _sol(todo)
        aeronave = (re.search(r"SH-32-\d\d", sol) or ["SH-32-01"])[0]
        codigo = _codigo(sol)
        estado = "en vuelo" if re.search(r"en vuelo", sol, re.I) else "en tierra"

        if rol.startswith("Jefe de Taller"):
            if _es_reporte(sol):
                plan = ["Técnico Diagnosticador", "Planificador de Mantenimiento", "Coordinador de Mantenimiento"]
            elif "perros" in sol.lower():
                plan = ["Técnico Diagnosticador"]
            else:
                plan = []
            if pasos < len(plan):
                return _accion(pasos, "Delegate work to coworker", {
                    "task": f"SOLICITUD: {sol}\nRealiza tu parte para la aeronave {aeronave} ({estado}), componente {codigo}.",
                    "context": f"Aeronave {aeronave}, {estado}, componente {codigo}.",
                    "coworker": plan[pasos]})
            ots = sorted(set(re.findall(r"OT-\d{8}-\d{3}", obs)))
            if "perros" in sol.lower():
                return _final("**Diagnóstico** El manual no cubre ese tema (SIN_RESULTADOS_RELEVANTES). Declino. "
                              "**Decisiones tomadas** No se delegaron tareas de escritura. **Próximos pasos** — **Fuentes** —")
            if not plan:
                lineas_tr2 = [l for l in todo.splitlines() if "TR2" in l]
                ots_tr2 = sorted(set(re.findall(r"OT-\d{8}-\d{3}", "\n".join(lineas_tr2))))
                return _final(f"**Diagnóstico** Seguimiento desde memoria. OT del TR2: {', '.join(ots_tr2) or 'ninguna'}. "
                              "**Decisiones tomadas** Respondí con la conversación y la memoria de largo plazo. "
                              "**Próximos pasos** — **Fuentes** memoria")
            return _final(f"**Diagnóstico** (simulado) Falla en {aeronave}, componente {codigo}. "
                          f"**Decisiones tomadas** Delegué a los tres especialistas. OT: {', '.join(ots) or 'ninguna'}. "
                          "**Próximos pasos** Ejecutar la OT. **Fuentes** manual y OT.")

        if rol.startswith("Técnico Diagnosticador"):
            seq = [("buscar_manual", {"consulta": sol[:200]}), ("buscar_historial_fallas", {"consulta": sol[:200]})]
        elif rol.startswith("Planificador de Mantenimiento"):
            seq = [("evaluar_criticidad", {"descripcion_falla": sol, "estado_aeronave": estado}),
                   ("consultar_stock", {"codigo_componente": codigo})]
        elif rol.startswith("Coordinador de Mantenimiento"):
            seq = [("crear_orden_trabajo", {"aeronave": aeronave, "componente": codigo, "descripcion": sol[:150],
                                            "criticidad": "MEDIA", "accion_recomendada": f"Revisar y reemplazar {codigo}"})]
            if '"EN_ESPERA_REPUESTO"' in obs:
                seq.append(("enviar_correo", {"destinatario": "abastecimiento@taller-sh32.cl",
                                              "asunto": f"Sin stock {codigo}", "cuerpo": "Repuesto sin stock."}))
        else:
            return _final("(respuesta simulada)")
        if pasos < len(seq):
            return _accion(pasos, *seq[pasos])
        return _final(f"(simulado) {rol}: listo. " + " ".join(re.findall(r"OT-\d{8}-\d{3}[^,\n]{0,40}", obs))[:300])


crewai.LLM = FakeLLM
print("Modo prueba: embeddings y LLM de CrewAI simulados (sin red).")
