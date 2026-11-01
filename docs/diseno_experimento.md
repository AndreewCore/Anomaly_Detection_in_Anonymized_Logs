# Diseño del experimento

Este documento fija cómo se define y ejecuta cada run. Las secciones marcadas **DECISIÓN PENDIENTE** deben acordarse en grupo antes de implementar `features.py`, `labeling.py` y `splitting.py`. Cuando se decidan, actualiza esta página y `configs/experiment.yaml`, y registra la fecha.

## 1. Matriz de experimentos

Cada run es una combinación de:

| Eje | Valores | Dónde se define |
|---|---|---|
| dataset | `lab_<escenario>`, `loghub_openssh`, … | `experiment.yaml → datasets` |
| (tratamiento, campo) | 8 pares válidos (ver §2) | `matrix_*.yaml → treatments` |
| conjunto de reglas | lista curada con nombre | `matrix_*.yaml → rule_sets` |
| ventana | segundos | `matrix_*.yaml → window_seconds` |
| detector | `isolation_forest`, `ssif`, `umbral` | `matrix_*.yaml → detectors` |
| semilla | lista | `matrix_*.yaml → seeds` |

- **run_id** = `<dataset>__<12 hex>`. Los 12 caracteres hex salen del SHA-1 de la combinación serializada con claves ordenadas. Reordenar el YAML no cambia el id.
- **Reanudación:** un run está completo si su carpeta tiene `metrics.json`. Ese archivo se escribe de último y de forma atómica (temporal + renombrar).
- **Detectores sin semilla:** `umbral` se ejecuta una sola vez por combinación (`seed: null`).

### Dos fases

| Fase | Archivo | Contenido | Semillas | Runs (config actual) |
|---|---|---|---|---|
| Humo | `matrix_smoke.yaml` | mínimo, para comprobar que el pipeline corre | 2 | 6 |
| 1. Exploración | `matrix_exploracion.yaml` | todas las combinaciones curadas | 5 | 6 600 |
| 2. Confirmación | `matrix_confirmacion.yaml` | solo finalistas | 30 | 1 952 (con 1 regla × 1 ventana) |

Los resultados del artículo salen **solo de la fase de confirmación**. El criterio para elegir finalistas debe escribirse aquí **antes** de ver los resultados de la fase 1, para no ajustar el diseño a los datos. *(TODO: definir el criterio.)*

Puedes comprobar el tamaño de una matriz con `python scripts/04_run_matrix.py --matrix <archivo> --dry-run`.

## 2. Tratamientos por campo — decisión D3 (tomada)

Un tratamiento se aplica a los campos indicados. El campo no tratado queda **original**. Esto vale tanto para las columnas como para el texto libre del mensaje.

| tratamiento | campos válidos | Qué hace |
|---|---|---|
| original | ninguno | sin cambios (referencia) |
| suprimida | usuario, ip, ambos | reemplaza por un token fijo (`<SUPRIMIDO>`) |
| seudonimizada | usuario, ip, ambos | HMAC-SHA256 con salt secreto, consistente dentro del dataset |
| ip_generalizada | **solo ip** | IPv4 → red /24 |

`ip_generalizada + usuario` no tiene sentido, porque no transforma usuarios. `ip_generalizada + ambos` sería en realidad un tratamiento híbrido (IP generalizada + usuario tratado de otra forma). Por eso se excluyen: son 8 pares, no 10. `matrix.py` rechaza cualquier par fuera de esta lista.

*Abierto:* si el grupo quiere un híbrido (p. ej. IP /24 + usuario seudonimizado), se agrega como **tratamiento nuevo con nombre propio** (`hibrido_gen_seud`), no como un valor de campo.

## 3. Unidad de análisis — DECISIÓN PENDIENTE D1

Es la decisión más importante: define qué es una fila para el detector.

| Opción | Fila = | Ventaja | Riesgo |
|---|---|---|---|
| `ventana` | toda la actividad de una ventana | simple; no depende de identidades | un ataque pequeño se diluye entre el tráfico normal |
| `ventana_ip` | (ventana, IP) | natural para fuerza bruta | depende de que las IPs sigan siendo distinguibles |
| `ventana_usuario` | (ventana, usuario) | detecta ataques contra una cuenta | depende de que los usuarios sigan siendo distinguibles |

Las opciones `ventana_ip` y `ventana_usuario` hacen que el resultado dependa del tratamiento. **Eso es justamente lo que se quiere medir**, pero hay que decidirlo y reportarlo:

- **Suprimir la IP:** todas las IPs se vuelven el mismo token. `fallos_por_ip` se colapsa en una sola entidad, que acumula todo el tráfico.
- **Seudonimizar:** las IPs siguen siendo distintas entre sí. Las features por entidad casi no cambian.
- **Generalizar a /24:** un ataque distribuido desde la misma subred se fusiona en una sola entidad. En el laboratorio, `attacker_1` y `attacker_2` comparten 172.28.1.0/24 y `attacker_3` no, para observar ambos casos.

Hay que decidir además: si la unidad es (ventana, IP), ¿qué pasa con `fallos_por_usuario`? Se calcula a nivel de ventana y se repite en cada fila, o se excluye de ese conjunto de reglas.

## 4. Etiquetado de unidades — DECISIÓN PENDIENTE D2

Las etiquetas se asocian **por `event_id`**, nunca por IP o usuario. Se calculan una vez sobre los logs originales y viajan sin cambios a todas las versiones anonimizadas.

Una unidad se etiqueta como ataque si:

- `any`: contiene **al menos un** evento de ataque; o
- `fraction`: la fracción de eventos de ataque es ≥ `min_fraction`.

`any` maximiza el recall posible, pero etiqueta como ataque ventanas casi totalmente normales. `fraction` es más estricta, y el umbral debe justificarse.

## 5. Partición entrenamiento/prueba — decisión D4 (tomada; detalles pendientes)

- La partición es temporal: entrena el primer `train_fraction` del rango y se evalúa el resto. Todo detector que use etiquetas (`ssif`) recibe solo etiquetas de entrenamiento. Las métricas se calculan siempre sobre la parte de prueba.
- Si la parte de prueba queda **sin ataques**, `splitting.py` **falla** con `NoAttacksInTestError`, indicando dataset, corte y dónde quedaron los ataques. Nunca reporta un recall indefinido como 0.
- Prevención: los escenarios de `lab/scenarios/` reparten el ataque en varias ráfagas a lo largo de la captura (`bursts`).
- *Pendiente:* valor final de `train_fraction`, y qué hacer con Loghub (no tiene etiquetas y no se verifica el mínimo).

## 6. Detectores — D5 pendiente para SSIF

- **Interfaz común** `Detector`: `fit(X, y=None)`, `score(X)` y `predict(X)`. Un score más alto significa más anómalo.
- **isolation_forest:** usa `n_estimators`, `max_samples` y `contamination` de `experiment.yaml`.
- **ssif:** elegir entre (a) IF entrenado solo con unidades normales, o (b) un SSIF de la literatura. Ver el docstring de `detection/ssif.py`. Como necesita etiquetas, no aplica a `loghub_openssh`, y esos runs se marcan como omitidos.
- **umbral:** baseline determinista. Su score es `max(feature / umbral)`.

## 7. Métricas por run

- Precisión, recall, F1, FPR, y TP/FP/TN/FN.
- ROC-AUC y PR-AUC, calculadas sobre los scores continuos.
- Exposición residual: el porcentaje de usuarios e IPs originales que aparecen literalmente en la versión anonimizada, tanto en columnas como en texto libre.
- En datasets sin etiquetas, las métricas de detección son `NaN` con `labels_available: false`. La exposición sí se calcula.

## 8. Pruebas estadísticas

- **Wilcoxon pareado por semilla** entre pares de (tratamiento, campo), para cada (dataset, reglas, ventana, detector).
- **Corrección de Holm** dentro de cada familia de comparaciones. Con muchos pares, sin corrección algunas diferencias saldrían significativas por azar.
- **`umbral` va aparte:** no tiene semilla, así que no puede entrar en una prueba pareada. Se reporta de forma descriptiva (valor por tratamiento y diferencia contra `original`).

## Registro de decisiones

| ID | Tema | Estado | Fecha |
|---|---|---|---|
| D1 | Unidad de análisis | pendiente | |
| D2 | Regla de etiquetado | pendiente | |
| D3 | Pares (tratamiento, campo) válidos | tomada | 2026-11-01 |
| D4 | Partición temporal y fallo sin ataques en prueba | tomada (detalles pendientes) | 2026-11-01 |
| D5 | Variante de SSIF | pendiente | |
