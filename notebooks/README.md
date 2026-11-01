# notebooks/ — Exploración y gráficos

- `01_exploracion_logs.ipynb`: mirar los logs y las features. `02_analisis_resultados.ipynb`: analizar lo que ya está en `results/`.
- Los notebooks **importan desde `anonlogs`** y no duplican lógica; lo reutilizable va a `src/`.
- El análisis nunca recalcula el experimento: eso lo hacen los scripts de `scripts/`.
- Limpia las salidas antes de commitear (Kernel → Restart & Clear Output) para que los diffs sean legibles.
