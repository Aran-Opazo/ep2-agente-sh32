# Historial de cambios del notebook

**23/10/2026**

- La primera celda instala versiones fijas solo si faltan y reúne todos los imports; si instala, reinicia la sesión.
- Antes de usar el equipo se prueba que el modelo responda, con mensajes claros si la key falla o se acaba la cuota.
- La memoria de la sesión guarda los números de OT junto a cada respuesta y no guarda las solicitudes que fallan.
- Los agentes ya no imprimen su razonamiento paso a paso: se muestra solo el resumen de cada solicitud.
- Se simplificaron los comentarios del código.
- Ejecución completa con qwen3.8-27b: 9/9 pruebas y escenarios A a F, cerca de 67.000 tokens.

**22/10/2026**

- El equipo decidió usar solo orquestación jerárquica con CrewAI. Se quitaron el agente de LangChain, el planificador aparte y la ejecución con pasos fijos.
- Se agregó un Manager propio (Jefe de Taller) con un máximo de 10 iteraciones.
- La memoria de corto plazo pasó a ser una ventana de 6 turnos.
- Las herramientas registran qué agente las usó, y se guardan las delegaciones del Manager.
- La criticidad final es la más alta entre la del agente y la de las reglas. Solo un reporte de falla crea una OT y no se duplican órdenes.
- Al final de cada solicitud se revisa si falta un correo obligatorio.
- Se agregaron 9 pruebas de las herramientas.
- El manual se sube con un botón cada vez que se ejecuta la sección 1.
- Se explicó el cálculo del umbral (1,261).
- Se quitó el escenario de consulta técnica; los escenarios quedaron de la A a la F.

**21/10/2026**

- Se corrigió el error de la memoria con modelos que no son de OpenAI (`tiktoken_model_name`).
- Se limpian los espacios de la API key al leerla.
