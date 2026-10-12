#!/usr/bin/env python3
"""
Automated Browser Resource Daemon & IA-Friendly Auditor.
Diseñado para correr de 07:00 a 15:00 de forma automática.
Muestreo sistemático periódico cada 30 segundos.
Guarda logs diarios detallados y un archivo consolidado en JSON con metadata completa.
"""

import os
import sys
import time
import json
import psutil
from datetime import datetime, time as dtime

# ================= CONFIGURACIÓN =================
DEFAULT_BROWSER = "vivaldi"
LOG_DIR = os.path.expanduser("~/browser_benchmark_logs")
DAILY_SUMMARY_FILE = os.path.join(LOG_DIR, "benchmark_ai_summary.json")

# Horario de auditoría: 07:00:00 a 15:00:00
START_HOUR = 7
START_MINUTE = 0
END_HOUR = 15
END_MINUTE = 0

SAMPLING_INTERVAL_SEC = 30  # Intervalo de muestreo regular
# =================================================

os.makedirs(LOG_DIR, exist_ok=True)

def is_within_work_hours(now=None):
    if now is None:
        now = datetime.now()
    start = dtime(START_HOUR, START_MINUTE)
    end = dtime(END_HOUR, END_MINUTE)
    curr = now.time()
    return start <= curr <= end

def collect_browser_metrics(target_name):
    target_lower = target_name.lower()
    pids = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            name = (proc.info['name'] or '').lower()
            cmdline = " ".join(proc.info['cmdline'] or []).lower()
            if target_lower in name or target_lower in cmdline:
                # Evitar coincidencia con este script o editores
                if 'browser_daemon' in cmdline or 'audit' in cmdline:
                    continue
                pids.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    if not pids:
        return None

    total_rss = 0
    total_vms = 0
    total_swap = 0
    total_cpu = 0.0
    active_procs = 0

    for p in pids:
        try:
            mem_info = p.memory_info()
            total_rss += mem_info.rss
            total_vms += mem_info.vms
            
            # Intento de lectura de memoria swap por proceso
            try:
                mem_full = p.memory_full_info()
                total_swap += getattr(mem_full, 'swap', 0)
            except (AttributeError, psutil.AccessDenied):
                pass

            # cpu_percent no bloqueante
            total_cpu += p.cpu_percent(interval=None)
            active_procs += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Lectura del estado general del host en ese mismo instante
    sys_mem = psutil.virtual_memory()
    sys_cpu = psutil.cpu_percent(interval=None)

    return {
        "timestamp": datetime.now().isoformat(),
        "process_count": active_procs,
        "rss_mb": round(total_rss / (1024 * 1024), 2),
        "vms_mb": round(total_vms / (1024 * 1024), 2),
        "swap_mb": round(total_swap / (1024 * 1024), 2),
        "cpu_percent": round(total_cpu, 2),
        "system_total_ram_used_mb": round(sys_mem.used / (1024 * 1024), 2),
        "system_ram_percent": sys_mem.percent,
        "system_cpu_percent": sys_cpu
    }

def update_ai_summary(target_browser, session_date, samples):
    """
    Escribe/actualiza una estructura JSON diseñada para ser consumida e interpretada
    directamente por cualquier modelo de IA o asistente.
    """
    if not samples:
        return

    rss_list = [s['rss_mb'] for s in samples]
    cpu_list = [s['cpu_percent'] for s in samples]
    procs_list = [s['process_count'] for s in samples]

    day_metrics = {
        "date": session_date,
        "total_samples": len(samples),
        "audit_window": f"{START_HOUR:02d}:{START_MINUTE:02d} - {END_HOUR:02d}:{END_MINUTE:02d}",
        "metrics": {
            "ram_rss_mb": {
                "avg": round(sum(rss_list) / len(rss_list), 2),
                "min": round(min(rss_list), 2),
                "max": round(max(rss_list), 2),
                "p95": round(sorted(rss_list)[int(len(rss_list) * 0.95)], 2) if len(rss_list) >= 20 else round(max(rss_list), 2)
            },
            "cpu_percent": {
                "avg": round(sum(cpu_list) / len(cpu_list), 2),
                "max": round(max(cpu_list), 2)
            },
            "avg_processes": round(sum(procs_list) / len(procs_list), 1)
        }
    }

    data = {}
    if os.path.exists(DAILY_SUMMARY_FILE):
        try:
            with open(DAILY_SUMMARY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = {}

    if "browsers" not in data:
        data["browsers"] = {}

    if target_browser not in data["browsers"]:
        data["browsers"][target_browser] = []

    # Reemplazar o agregar el día evaluado
    existing = [d for d in data["browsers"][target_browser] if d.get("date") != session_date]
    existing.append(day_metrics)
    data["browsers"][target_browser] = existing
    data["last_updated"] = datetime.now().isoformat()

    with open(DAILY_SUMMARY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def run_auditor(target_browser=DEFAULT_BROWSER, force_now=False):
    today_str = datetime.now().strftime("%Y-%m-%d")
    raw_log_file = os.path.join(LOG_DIR, f"{target_browser}_{today_str}.jsonl")
    
    print(f"[*] Iniciando Auditor Automatizado para: {target_browser.upper()}")
    print(f"[*] Ventana operativa: {START_HOUR:02d}:{START_MINUTE:02d} a {END_HOUR:02d}:{END_MINUTE:02d}")
    print(f"[*] Frecuencia de muestreo: Cada {SAMPLING_INTERVAL_SEC} segundos")
    print(f"[*] Archivo crudo (JSONL): {raw_log_file}")
    print(f"[*] Consolidado para IA:   {DAILY_SUMMARY_FILE}")

    daily_samples = []

    while True:
        now = datetime.now()
        
        # Validar si estamos dentro del horario laboral
        if not force_now and not is_within_work_hours(now):
            current_time = now.time()
            if current_time > dtime(END_HOUR, END_MINUTE):
                print(f"[!] Fin de la jornada de monitoreo ({now.strftime('%H:%M:%S')}). Consolidando datos...")
                update_ai_summary(target_browser, today_str, daily_samples)
                print("[✓] Resumen actualizado con éxito. El servicio esperará hasta mañana a las 07:00.")
                # Dormir hasta las 06:59 del día siguiente
                time.sleep(3600)
                continue
            else:
                # Es antes de las 07:00 AM
                time.sleep(30)
                continue

        metrics = collect_browser_metrics(target_browser)
        if metrics:
            daily_samples.append(metrics)
            # Guardar en formato JSON Lines (fácil de ingerir y persistente ante fallos)
            with open(raw_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(metrics) + "\n")
            
            # Cada 10 muestras (~5 min) actualizamos el consolidado IA por si se corta la sesión
            if len(daily_samples) % 10 == 0:
                update_ai_summary(target_browser, today_str, daily_samples)

            print(f"[{metrics['timestamp'][11:19]}] {target_browser.capitalize():<8} | "
                  f"RAM: {metrics['rss_mb']:7.1f} MB | CPU: {metrics['cpu_percent']:5.1f}% | "
                  f"Pestañas/Procesos: {metrics['process_count']:3d} | Total Sistema RAM: {metrics['system_ram_percent']}%", flush=True)
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {target_browser.capitalize()} no detectado en ejecución. Esperando...", flush=True)

        time.sleep(SAMPLING_INTERVAL_SEC)

if __name__ == "__main__":
    browser_arg = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BROWSER
    force = "--now" in sys.argv
    run_auditor(browser_arg, force_now=force)
