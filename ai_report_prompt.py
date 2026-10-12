#!/usr/bin/env python3
"""
Prompt Generator para IA a partir del JSON de benchmark.
Ejecuta: python3 ~/Proyectos/auditor-navegadores/ai_report_prompt.py
Imprime un bloque listo para pegar o leer en el chat con la IA.
"""

import os
import json

SUMMARY_FILE = os.path.expanduser("~/browser_benchmark_logs/benchmark_ai_summary.json")

def generate_prompt():
    if not os.path.exists(SUMMARY_FILE):
        print("Aún no se ha generado información en el archivo de resumen.")
        print(f"Ruta esperada: {SUMMARY_FILE}")
        return

    with open(SUMMARY_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    prompt = f"""### Contexto de Auditoría de Rendimiento de Navegadores
A continuación tienes las métricas recolectadas automáticamente durante jornadas de trabajo reales (07:00 a 15:00):

```json
{json.dumps(data, indent=2, ensure_ascii=False)}
```

### Instrucción para la IA:
1. Compara el uso de RAM (promedio y P95) y CPU entre los navegadores evaluados.
2. Identifica si existen fugas de memoria o picos anómalos.
3. Evalúa si el navegador actual maneja adecuadamente la suspensión de Web Apps inactivas.
4. Da una recomendación clara sobre cuál es el mejor navegador según estos datos empíricos.
"""
    print(prompt)

if __name__ == "__main__":
    generate_prompt()
