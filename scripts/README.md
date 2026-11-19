# scripts/ — Pipeline reproducible por línea de comandos

- Se ejecutan **en orden numérico** desde la raíz del repo con el venv activo: `python scripts/01_parse_logs.py ...`.
- Cada script solo orquesta: la lógica vive en `src/anonlogs/`. Aquí no se copia código del paquete.
- `05_build_tables.py` reconstruye todas las tablas solo a partir de `results/runs/`.
- Aquí no van notebooks, datos ni resultados.

## Revisiones automáticas del Ground Truth

La revisión de los dudosos ya no se marca a mano: `make_revisiones.py` la simula con
tres estrategias reproducibles (`anonlogs.revision`), para medir el efecto de la
calidad de la revisión sin la variabilidad de cada revisor:

- `cobertura` — revisa (con la etiqueta verdadera) una fracción `--frac` de los dudosos; el resto queda en auto.
- `aleatorio` — revisa todos asignando la etiqueta al azar 50/50 (baseline de "revisor que adivina").
- `aciertos` — revisa todos acertando la verdad con probabilidad `--rate` (revisión completa pero imperfecta).

La verdad de cada dudoso se deriva de las IPs del GT (atacante → 1, legítima → 0);
`00_ingest_lab.py` consolida además `<dataset>_legit.csv` para corroborar typos.

```bash
# genera data/ground_truth/<dataset>_revisiones.csv y luego se aplica en la etapa 1
python scripts/make_revisiones.py --dataset lab_concentrado --mode cobertura --frac 0.6 --seed 1
python scripts/01_parse_logs.py --datasets lab_concentrado

# o en una sola pasada, sin CSV intermedio a mano:
python scripts/01_parse_logs.py --datasets lab_concentrado --revision-mode aciertos --revision-rate 0.75
```
