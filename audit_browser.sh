#!/usr/bin/env bash
# ==============================================================================
# Browser Resource Benchmark & Auditor (Linux)
# Registra CPU (%), Memoria RAM (MB), Swap (MB) y conteo de procesos.
# ==============================================================================

set -euo pipefail

LOG_DIR="${HOME}/browser_benchmark_logs"
mkdir -p "$LOG_DIR"

INTERVAL=10 # Intervalo de muestreo en segundos

print_usage() {
    echo "Uso: $0 <nombre_del_navegador_o_proceso> [etiqueta_opcional]"
    echo ""
    echo "Ejemplos:"
    echo "  $0 brave"
    echo "  $0 chrome jornada-lunes"
    echo "  $0 firefox"
    echo "  $0 edge"
    echo "  $0 floorp"
    echo "  $0 vivaldi"
    echo ""
    echo "Navegadores comunes y nombres de binario:"
    echo "  - Brave:       brave"
    echo "  - Chrome:      chrome"
    echo "  - Firefox:     firefox"
    echo "  - Edge:        msedge"
    echo "  - Vivaldi:     vivaldi"
    echo "  - Chromium:    chromium"
    echo "  - Floorp:      floorp"
    exit 1
}

if [ $# -lt 1 ]; then
    print_usage
fi

BROWSER_PATTERN="$1"
TAG="${2:-sesion}"
DATE_STR="$(date +'%Y-%m-%d_%H-%M-%S')"
OUTPUT_FILE="${LOG_DIR}/${BROWSER_PATTERN}_${TAG}_${DATE_STR}.csv"

echo "timestamp,browser,process_count,cpu_percent,rss_memory_mb,swap_memory_mb" > "$OUTPUT_FILE"

echo "=========================================================="
echo " [Auditor de Navegadores Iniciado]"
echo " Patrón de búsqueda: $BROWSER_PATTERN"
echo " Intervalo:          ${INTERVAL}s"
echo " Archivo de log:     $OUTPUT_FILE"
echo " Presiona [Ctrl + C] al finalizar tu jornada o prueba."
echo "=========================================================="

trap finish INT TERM

finish() {
    echo -e "\n\nMonitoreo finalizado. Analizando resumen rápido..."
    if [ -f "$OUTPUT_FILE" ] && [ $(wc -l < "$OUTPUT_FILE") -gt 1 ]; then
        python3 - <<EOF
import csv
import sys

filename = "$OUTPUT_FILE"
cpu_vals = []
mem_vals = []
proc_vals = []

with open(filename, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        try:
            cpu_vals.append(float(row['cpu_percent']))
            mem_vals.append(float(row['rss_memory_mb']))
            proc_vals.append(int(row['process_count']))
        except (ValueError, KeyError):
            pass

if mem_vals:
    avg_cpu = sum(cpu_vals) / len(cpu_vals)
    max_cpu = max(cpu_vals)
    avg_mem = sum(mem_vals) / len(mem_vals)
    max_mem = max(mem_vals)
    avg_procs = sum(proc_vals) / len(proc_vals)

    print("\n---------------- RESUMEN PRELIMINAR ----------------")
    print(f"Muestras tomadas:     {len(mem_vals)}")
    print(f"Memoria RAM promedio: {avg_mem:.1f} MB  | Máxima: {max_mem:.1f} MB")
    print(f"CPU promedio:         {avg_cpu:.1f} %   | Máximo: {max_cpu:.1f} %")
    print(f"Procesos promedio:    {avg_procs:.1f}")
    print("-----------------------------------------------------")
    print(f"Datos guardados en: {filename}\n")
EOF
    else
        echo "No se registraron datos suficientes."
    fi
    exit 0
}

while true; do
    TIMESTAMP="$(date +'%Y-%m-%d %H:%M:%S')"
    
    # Obtener PIDs asociados al patrón (excluyendo este mismo script o grep)
    PIDS=$(pgrep -f -i "$BROWSER_PATTERN" | grep -v "$$" || true)

    if [ -z "$PIDS" ]; then
        # Navegador no detectado en esta muestra
        echo "$TIMESTAMP,$BROWSER_PATTERN,0,0.0,0.0,0.0" >> "$OUTPUT_FILE"
    else
        # Calcular uso consolidado de todos los subprocesos del navegador
        # ps --no-headers -p ... -o %cpu,rss
        STATS=$(ps --no-headers -o %cpu,rss -p $PIDS 2>/dev/null || true)
        
        if [ -n "$STATS" ]; then
            METRICS=$(echo "$STATS" | awk '{cpu+=$1; rss+=$2; count++} END {printf "%d %.1f %.2f", count, cpu, rss/1024}')
            read -r PROC_COUNT TOTAL_CPU TOTAL_RSS <<< "$METRICS"
            
            # Cálculo de Swap consolidado vía /proc/[pid]/status
            TOTAL_SWAP_KB=0
            for pid in $PIDS; do
                if [ -r "/proc/$pid/status" ]; then
                    SWAP_VAL=$(awk '/VmSwap:/ {print $2}' "/proc/$pid/status" 2>/dev/null || echo 0)
                    TOTAL_SWAP_KB=$((TOTAL_SWAP_KB + SWAP_VAL))
                fi
            done
            TOTAL_SWAP_MB=$(awk -v swap="$TOTAL_SWAP_KB" 'BEGIN {printf "%.2f", swap/1024}')

            echo "$TIMESTAMP,$BROWSER_PATTERN,$PROC_COUNT,$TOTAL_CPU,$TOTAL_RSS,$TOTAL_SWAP_MB" >> "$OUTPUT_FILE"
            
            # Feedback en consola en una sola línea
            printf "\r[%s] %s -> RAM: %7.1f MB | CPU: %5.1f%% | Procesos: %3d" "$TIMESTAMP" "$BROWSER_PATTERN" "$TOTAL_RSS" "$TOTAL_CPU" "$PROC_COUNT"
        fi
    fi
    sleep "$INTERVAL"
done
