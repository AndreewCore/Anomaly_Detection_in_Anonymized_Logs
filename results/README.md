# results/ — Resultados

- `runs/<run_id>/`: resultado crudo de cada run (`config.yaml`, `scores.csv`, `metrics.json`, `run.log`). **No se commitea**; se sincroniza con Drive.
- `sessions/<AAAA-MM-DD_HHMM>__<fase>__<usuario>__<N>runs-<M>filas__<min>min/`: resumen de cada ejecución de `04_run_matrix.py` (`manifest.json`, `runs.csv`). **No se commitea**; se sincroniza con Drive.
- `tables/`: CSV consolidados, agregados y pruebas estadísticas. **Sí se commitea** (son livianos).
- `figures/`: figuras finales en PDF y PNG para Overleaf. **Sí se commitea**.
- Todo `tables/` se puede reconstruir desde `runs/` con `python scripts/05_build_tables.py`.
