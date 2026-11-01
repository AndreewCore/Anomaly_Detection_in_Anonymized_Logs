# Estado de implementación

> **Si un script termina con `NotImplementedError`, no es un error.** Casi todo el pipeline está creado como *stub*: la función existe y su docstring dice qué hará, pero la lógica todavía no está escrita. Esta página dice qué funciona hoy, qué falta y qué está bloqueado.

Leyenda:
- ✅ **funciona**
- 🟡 **stub**: se puede implementar ya
- ⛔ **bloqueado**: espera una decisión del grupo (ver [`diseno_experimento.md`](diseno_experimento.md)) o datos del laboratorio

Última revisión: 2026-11-01.

## Scripts (`scripts/`)

| # | Script | Estado | Qué falta |
|---|---|---|---|
| 00 | `00_download_loghub.py` | ✅ al mergear el PR #1 | En `dev`, hasta ese merge, sigue siendo stub. Pendiente: decidir si se usa también el log completo de Zenodo |
| 01 | `01_parse_logs.py` | 🟡 | Implementar `parsing.py`. Con Loghub se puede hacer ya; con el lab hace falta el Ground Truth |
| 02 | `02_anonymize.py` | 🟡 | Implementar `anonymization.py` |
| 03 | `03_build_features.py` | ⛔ D1 | Decidir la unidad de análisis y luego implementar `features.py` |
| 04 | `04_run_matrix.py` | ✅ solo `--dry-run` | La ejecución real necesita `runner.py`, `features.py`, `labeling.py`, `splitting.py`, `metrics.py` y `exposure.py` |
| 05 | `05_build_tables.py` | 🟡 | Implementar `reporting/aggregate.py` y `reporting/stats.py` |
| 06 | `06_make_figures.py` | 🟡 | Implementar `reporting/figures.py` |

## Paquete (`src/anonlogs/`)

| Componente | Archivo | Estado | Qué falta |
|---|---|---|---|
| Configuración | `src/anonlogs/config.py` | ✅ | — |
| Matriz y `run_id` | `src/anonlogs/matrix.py` | ✅ | — |
| Parseo | `src/anonlogs/parsing.py` | 🟡 | Parser RFC 3339 (lab) y tradicional (Loghub); Ground Truth → `event_id` |
| Anonimización | `src/anonlogs/anonymization.py` | 🟡 | Supresión, HMAC y /24, en columnas y texto libre |
| Features | `src/anonlogs/features.py` | ⛔ D1 | Unidad de análisis |
| Etiquetado | `src/anonlogs/labeling.py` | ⛔ D2 | Regla `any` o `fraction` |
| Partición temporal | `src/anonlogs/splitting.py` | ⛔ D4 | Valor final de `train_fraction` |
| Runner | `src/anonlogs/runner.py` | 🟡 | `execute_run` y `provenance`. `is_complete` ya funciona |
| Interfaz de detectores | `src/anonlogs/detection/base.py` | ✅ | — |
| Registro de detectores | `src/anonlogs/detection/__init__.py` | ✅ | — |
| Isolation Forest | `src/anonlogs/detection/isolation_forest.py` | ✅ | Probado con datos sintéticos; falta conectarlo vía `runner.py` |
| SSIF (variante a) | `src/anonlogs/detection/ssif.py` | ✅ | Igual que IF |
| Reglas con umbral | `src/anonlogs/detection/threshold.py` | 🟡 | `fit`, `score` y `predict` |
| Métricas | `src/anonlogs/evaluation/metrics.py` | 🟡 | P, R, F1, FPR, matriz de confusión, ROC-AUC y PR-AUC |
| Exposición residual | `src/anonlogs/evaluation/exposure.py` | 🟡 | — |
| Tablas | `src/anonlogs/reporting/aggregate.py` | 🟡 | — |
| Estadística | `src/anonlogs/reporting/stats.py` | 🟡 | Wilcoxon + Holm; umbral aparte |
| Figuras | `src/anonlogs/reporting/figures.py` | 🟡 | — |

## Otros componentes

| Componente | Estado | Nota |
|---|---|---|
| `tools/c` (`make`) | ✅ | Compila `agente` y `anomalia` |
| Tests (`pytest`) | ✅ | Matriz, imports y detectores IF/SSIF |
| Laboratorio (`lab/`) | ⚠️ sin probar | El YAML es válido, pero nunca se ha levantado. Primera ejecución real: en Windows |
| `anomalia.c` | ⛔ | No escribe Ground Truth ni acepta parámetros (ver [`pendientes.md`](pendientes.md)) |
| Tráfico legítimo | 🟡 | `lab/legit_traffic/generate_legit.sh` es un stub |

Mientras el laboratorio no produzca logs con Ground Truth, **solo se puede trabajar con Loghub**. Loghub no tiene etiquetas, así que permite probar el parseo, la anonimización y la exposición residual, pero no las métricas de detección.

## ¿Dónde están los algoritmos de detección?

Todos viven en `src/anonlogs/detection/` y cumplen la misma interfaz.

| Algoritmo | Código | Configuración | Estado |
|---|---|---|---|
| Interfaz común `Detector` | `src/anonlogs/detection/base.py` | — | ✅ |
| Isolation Forest | `src/anonlogs/detection/isolation_forest.py` → `IsolationForestDetector` | `configs/experiment.yaml` → `detectors.isolation_forest` (`n_estimators`, `max_samples`, `contamination`) | ✅ |
| SSIF, variante (a) | `src/anonlogs/detection/ssif.py` → `SSIFDetector` | `configs/experiment.yaml` → `detectors.ssif` | ✅ |
| Reglas con umbral | `src/anonlogs/detection/threshold.py` → `ThresholdDetector` | `configs/experiment.yaml` → `detectors.umbral` (un umbral por regla) | 🟡 |

- **Convención:** todos exponen `fit(X, y=None)`, `score(X)` y `predict(X)`. En `score`, un valor más alto significa más anómalo; así ROC-AUC y PR-AUC se calculan igual para todos. `predict` devuelve 1 si es anómalo y 0 si es normal.
- **Etiquetas:** los detectores con `uses_labels = True` (hoy solo SSIF) reciben solo las etiquetas de la parte de entrenamiento temporal.
- **Las reglas** que miden los detectores (`fallos_por_ip`, `fallos_por_usuario`, `usuarios_unicos_por_ip` y `fallos_por_ventana`) se calculan en `src/anonlogs/features.py` (lista `RULES`). Los conjuntos de reglas que se prueban se definen en `configs/matrix_*.yaml` → `rule_sets`.
- **Quién los llama:** `scripts/04_run_matrix.py` expande la matriz, y por cada run `src/anonlogs/runner.py` → `execute_run` crea el detector con `make_detector(nombre, params, seed)`.
- **Agregar un detector nuevo:**
  1. Crea un archivo en `src/anonlogs/detection/` con una clase que herede de `Detector`.
  2. Agrégala a `REGISTRY` en `src/anonlogs/detection/__init__.py`.
  3. Pon sus parámetros en `detectors.<nombre>` de `experiment.yaml`.
  4. Añade su nombre a `detectors` en las matrices.

## Problemas conocidos

1. **SSIF con Loghub:** `matrix_exploracion.yaml` combina `ssif` con `loghub_openssh`, que no tiene etiquetas. Cuando se implemente, `runner.py` debe marcar esos runs como omitidos (no como fallidos), para que la reanudación no los reintente sin fin.
2. **El `run_id` no depende de la fase.** Un run de exploración con semilla 0–4 tiene el mismo `run_id` que en confirmación, y se reutiliza. Esto es correcto, porque el cálculo es idéntico. Pero `05_build_tables.py --phase` debe seleccionar los runs **por las combinaciones de la matriz de esa fase**, no por una etiqueta de fase guardada en el run.
3. **Python 3.14:** las versiones fijas solo se verificaron en Python 3.14, y `pyproject.toml` exige `>=3.14`. Todo el grupo debe usar 3.14.
4. **Laboratorio sin probar:** `docker-compose.yml` y los Dockerfiles nunca se han ejecutado. Los atacantes solo corren el modo básico de `anomalia.c` (6 intentos y terminan).
