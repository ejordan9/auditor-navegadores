#!/usr/bin/env python3
"""
Comparador semanal de auditoría de navegadores.
Lee los archivos CSV en ~/browser_benchmark_logs y genera un reporte comparativo.
"""

import glob
import os
import csv
from collections import defaultdict

LOG_DIR = os.path.expanduser("~/browser_benchmark_logs")

def analyze_logs():
    files = glob.glob(os.path.join(LOG_DIR, "*.csv"))
    if not files:
        print(f"No se encontraron archivos de log en {LOG_DIR}")
        return

    # Estructura: stats[browser] = {'cpu': [], 'ram': [], 'samples': 0}
    stats = defaultdict(lambda: {'cpu': [], 'ram': [], 'swap': [], 'samples': 0})

    for filepath in files:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    proc_count = int(row.get('process_count', 0))
                    # Filtrar muestras donde el navegador no estaba abierto
                    if proc_count == 0:
                        continue
                    
                    browser = row['browser'].lower()
                    cpu = float(row['cpu_percent'])
                    ram = float(row['rss_memory_mb'])
                    swap = float(row.get('swap_memory_mb', 0))

                    stats[browser]['cpu'].append(cpu)
                    stats[browser]['ram'].append(ram)
                    stats[browser]['swap'].append(swap)
                    stats[browser]['samples'] += 1
                except (ValueError, KeyError):
                    continue

    if not stats:
        print("No hay registros válidos con actividad del navegador.")
        return

    print("==========================================================================================")
    print("                    REPORTE COMPARATIVO DE RENDIMIENTO DE NAVEGADORES                    ")
    print("==========================================================================================")
    print(f"{'Navegador':<12} | {'RAM Prom (MB)':<13} | {'RAM Máx (MB)':<13} | {'CPU Prom (%)':<12} | {'Swap Prom (MB)':<14} | {'Muestras':<8}")
    print("-" * 90)

    results = []
    for browser, data in stats.items():
        if not data['ram']:
            continue
        avg_ram = sum(data['ram']) / len(data['ram'])
        max_ram = max(data['ram'])
        avg_cpu = sum(data['cpu']) / len(data['cpu'])
        avg_swap = sum(data['swap']) / len(data['swap'])
        samples = data['samples']
        results.append((browser, avg_ram, max_ram, avg_cpu, avg_swap, samples))

    # Ordenar por menor consumo promedio de RAM
    results.sort(key=lambda x: x[1])

    for r in results:
        print(f"{r[0]:<12} | {r[1]:<13.1f} | {r[2]:<13.1f} | {r[3]:<12.1f} | {r[4]:<14.1f} | {r[5]:<8}")

    print("==========================================================================================")
    print(f"Ganador en consumo de RAM: {results[0][0].upper()} (Promedio: {results[0][1]:.1f} MB)")
    print("==========================================================================================")

if __name__ == "__main__":
    analyze_logs()
