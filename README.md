# Auditoría y Benchmark de Navegadores para Web Apps

Herramientas para monitorear y comparar el consumo real de recursos (RAM RSS, CPU, Swap/zram) en navegadores web en Linux de 07:00 a 15:00.

## Scripts:
- `browser_daemon.py`: Colector automatizado periódico en segundo plano.
- `browser-auditor.service`: Servicio `systemd --user` desatendido.
- `ai_report_prompt.py`: Generador de contexto estructurado para análisis por IA.
- `compare_browsers.py`: Comparador tabular semanal.
- `audit_browser.sh`: Auditor rápido interactivo en Bash.
