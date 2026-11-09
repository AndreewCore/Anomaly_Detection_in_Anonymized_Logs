# Efectos de la anonimización en la detección de anomalías en registros de sistemas operativos UNIX/Linux

Proyecto de investigación — **ESPOL, Metodología de la Investigación**
Equipo: Windsor Estrada, Paúl Rodríguez, Ricardo Asanza · Tutor: Ing. Ronald Criollo

---

## 1. ¿De qué trata?

Las organizaciones anonimizan sus logs (ocultan usuarios e IPs) para poder compartirlos sin exponer a nadie. Pero esa anonimización podría "cegar" a los sistemas que detectan ataques. **Queremos medir cuánto se pierde.**

Nos enfocamos en ataques de **fuerza bruta contra SSH** en logs de autenticación de Linux. El experimento tiene 4 pasos:

1. **Generar datos.** En un laboratorio con Docker, una máquina víctima recibe ataques (con `anomalia.c`) y tráfico normal. Anotamos aparte qué ataque ocurrió y cuándo: es el **Ground Truth**. También usamos logs públicos de **Loghub**.
2. **Anonimizar.** De cada log hacemos varias versiones:
   - **original:** sin cambios.
   - **suprimida:** el dato se borra.
   - **seudonimizada:** el dato se reemplaza por un código secreto, siempre el mismo para el mismo valor.
   - **ip_generalizada:** solo se deja la red, p. ej. `192.168.1.0/24`.

   Cada tratamiento se aplica al usuario, a la IP o a ambos.
3. **Detectar.** Corremos detectores de anomalías (Isolation Forest, SSIF y reglas de umbral) sobre cada versión.
4. **Evaluar.** Comparamos qué tan bien detecta cada versión (precisión, recall, F1, etc.) y cuánta información personal se filtra todavía (**exposición residual**).

El diseño detallado y las decisiones pendientes están en [`docs/diseno_experimento.md`](docs/diseno_experimento.md).

## Estado actual (2026-11-01)

> **Si un script termina con `NotImplementedError`, no es un error.** El proyecto está en etapa de estructura: casi todo el pipeline existe como *stub* (la función y su descripción están creadas, la lógica no).

| Ya funciona | Falta implementar | Bloqueado |
|---|---|---|
| Descarga de Loghub (script 00, al mergear el PR #1) · `04_run_matrix.py --dry-run` · `make -C tools/c` · `pytest` · detectores Isolation Forest y SSIF | Parseo (01), anonimización (02), runner, métricas, exposición residual, detector por umbral, tablas (05) y figuras (06) | Features (03) → decisión D1 · etiquetado → D2 · partición → D4 · datos del laboratorio → mejoras de `anomalia.c` |

El detalle por archivo y los problemas conocidos están en [`docs/estado_implementacion.md`](docs/estado_implementacion.md).

## 2. ¿Dónde va cada cosa?

| Herramienta | Qué contiene | Quién / cuándo se usa |
|---|---|---|
| **Google Drive** (carpeta compartida) | Todos los archivos del grupo: datasets (logs del laboratorio, Loghub, versiones anonimizadas), Ground Truth, `results/runs/`, actas de reunión, ficha de investigación | Todos. Se sube después de cada captura del laboratorio o corrida del experimento, y se descarga antes de trabajar |
| **Overleaf** | El artículo científico | Todos, al redactar. Recibe las tablas (`results/tables/`) y figuras (`results/figures/`) que produce este repo |
| **Mendeley** | Referencias bibliográficas y PDFs de papers | Todos, al leer y citar. El `.bib` se exporta a Overleaf desde aquí, no desde el repo |
| **GitHub** (este repo) | Solo código, configuración, documentación técnica y resultados livianos (tablas CSV pequeñas y figuras finales) | Quien programa o corre experimentos, mediante ramas y PRs |

**Regla de oro:** en git no hay datos, ni PDFs de papers, ni el artículo, ni secretos.

## 3. Estructura del repositorio

```
├── lab/            Laboratorio Docker (víctima sshd, atacantes, tráfico legítimo, escenarios). Se ejecuta en Linux
├── tools/c/        Herramientas en C (anomalia.c, agente.c) + Makefile
├── configs/        YAML del experimento: parámetros fijos y matrices (smoke, exploración, confirmación)
├── data/           Datos descargados de Drive (ignorados por git): raw, ground_truth, interim, processed, features
├── src/anonlogs/   Paquete Python con toda la lógica: parsing, anonimización, features, detección, evaluación, reportes
├── scripts/        Pipeline por línea de comandos, numerado por etapa (00 → 06)
├── notebooks/      Exploración y análisis; importan de src/, no recalculan
├── results/        runs/ (crudos, en Drive), tables/ y figures/ (en git, para Overleaf)
├── tests/          Pruebas automáticas (pytest)
└── docs/           Diseño del experimento y pendientes
```

Cada carpeta tiene su propio `README.md` que dice qué va ahí y qué no.

## 4. Flujo de datos entre herramientas

```
 Linux + Docker (lab/)            Google Drive                Laptop Linux (este repo)                  Overleaf
┌──────────────────────┐  sube  ┌──────────────┐  descarga  ┌────────────────────────────────┐  sube  ┌──────────┐
│ auth.log + Ground    │──────▶ │ datasets/    │──────────▶ │ data/raw/ → scripts 01–04 →    │──────▶ │ tablas y │
│ Truth por escenario  │        │ ground_truth/│            │ results/runs/ → 05–06 →        │        │ figuras  │
└──────────────────────┘        │ results/runs │ ◀──────────│ results/tables/, figures/      │        └──────────┘
                                └──────────────┘ sincroniza └────────────────────────────────┘
```

### Sincronizar datos con Drive (`scripts/sync_drive.sh`)

Las capturas, los datasets y los `results/runs/` no van a git (pesan y traen
IPs/usuarios reales). Se comparten por Drive con `rclone`, que nunca borra en el
destino: como cada captura y cada `run_id` llevan nombre único, varios integrantes
suben sin pisarse.

1. Instala y configura el remoto una sola vez:
   ```bash
   sudo pacman -S rclone
   rclone config          # crea un remoto de Drive, p. ej. llamado "drive"
   ```
2. Pon el remoto y la carpeta del grupo en `.env`:
   ```
   DRIVE_REMOTE=drive
   DRIVE_FOLDER=AnonLogs
   ```
3. Sube o baja:
   ```bash
   scripts/sync_drive.sh push all              # sube capturas + datos + resultados
   scripts/sync_drive.sh push capturas         # solo lab/output/
   scripts/sync_drive.sh pull resultados       # baja results/runs y results/sessions
   scripts/sync_drive.sh push all --dry-run    # muestra qué haría, sin tocar nada
   ```

Las subcarpetas de capturas y de sesiones ya llevan en el nombre la fecha, la hora,
el usuario, el nº de eventos y la duración, así que en Drive quedan ordenadas y
rastreables. Cualquier integrante reconstruye las tablas desde los runs con
`python scripts/05_build_tables.py --phase <fase>`.

## 5. Instalación

### 5.1 Python (Linux)

Requiere Python 3.14. Todas las dependencias tienen versión fija en `requirements.txt` y se instalan desde wheels.

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt      # incluye el paquete anonlogs en modo editable
cp .env.example .env                  # y pega el salt real (ver §7)
pytest                                # todo debe pasar
```

### 5.2 Herramientas en C

```bash
make -C tools/c          # genera tools/c/agente y tools/c/anomalia
make -C tools/c clean    # borra los binarios
```

### 5.3 Laboratorio (Linux con Docker Engine)

```bash
sudo pacman -S docker docker-compose docker-buildx
sudo systemctl enable --now docker
sudo usermod -aG docker $USER      # luego cierra sesión y vuelve a entrar
```

El laboratorio no se levanta a mano: `lab/capture.sh` orquesta una captura de
principio a fin (fija la semilla, espera a que termine la carga y guarda la salida
con un nombre descriptivo).

```bash
lab/capture.sh concentrado 1               # segmento 1 del escenario
lab/capture.sh concentrado 1 --minutes 5   # captura corta de prueba
```

Una captura de 90 min son **3 segmentos de 30 min** que pueden correrse en días
distintos; el parser los concatena como una sola línea de tiempo. Perfiles:
`concentrado`, `multi_cuenta`, `distribuido`, `spraying`. Mientras corre:
`tail -f lab/output/_actual/victim/auth.log`. El detalle está en
[`lab/README.md`](lab/README.md). También funciona en Windows con Docker Desktop
usando los mismos comandos de `docker compose`.

## 6. Orden de ejecución

Ejecuta todo desde la raíz del repo con el venv activo:

| # | Script | Qué hace | Estado |
|---|---|---|---|
| 0a | `python scripts/00_download_loghub.py` | Descarga Loghub OpenSSH a `data/raw/loghub/` | ✅ |
| 0b | `python scripts/00_ingest_lab.py --scenario <e>` | Copia las capturas del lab a `data/raw/lab/` y consolida el GT | ✅ |
| 1 | `python scripts/01_parse_logs.py` | Convierte los logs en tabla y asocia el Ground Truth por `event_id` | ✅ |
| 2 | `python scripts/02_anonymize.py --matrix <m>` | Genera las versiones anonimizadas + exposición residual | ✅ |
| 3 | `python scripts/03_build_features.py --matrix <m>` | Calcula las features por ventana y unidad | ✅ |
| 4 | `python scripts/04_run_matrix.py --matrix <m>` | Ejecuta todos los runs (reanudable; `--dry-run` cuenta los runs) | ✅ |
| 5 | `python scripts/05_build_tables.py --phase <f>` | Consolida runs → tablas + Wilcoxon/Holm | 🟡 stub |
| 6 | `python scripts/06_make_figures.py --phase <f>` | Figuras PDF + PNG para Overleaf | 🟡 stub |

✅ funciona · 🟡 stub, se puede implementar ya · ⛔ bloqueado por una decisión del grupo

Orden de las fases: `matrix_smoke.yaml` (¿funciona todo?) → `matrix_exploracion.yaml` (elegir finalistas) → `matrix_confirmacion.yaml` (resultados del artículo).

### ¿Dónde están los algoritmos de detección?

Todos están en `src/anonlogs/detection/` y comparten la interfaz `fit` / `score` / `predict` definida en `src/anonlogs/detection/base.py`.

| Algoritmo | Código | Se configura en `configs/experiment.yaml` | Estado |
|---|---|---|---|
| Isolation Forest | `src/anonlogs/detection/isolation_forest.py` | `detectors.isolation_forest` | ✅ |
| SSIF (IF entrenado solo con normales) | `src/anonlogs/detection/ssif.py` | `detectors.ssif` | ✅ |
| Reglas con umbral (fijo) | `src/anonlogs/detection/threshold.py` | `detectors.umbral` | ✅ |
| Umbral calibrado (p99 de normales) | `src/anonlogs/detection/threshold_calibrated.py` | `detectors.umbral_calibrado` | ✅ |

Las reglas que miden (fallos por IP, por usuario, etc.) se calculan en `src/anonlogs/features.py`. El registro que conecta cada nombre de la matriz con su clase está en `src/anonlogs/detection/__init__.py`. Más detalle en [`docs/estado_implementacion.md`](docs/estado_implementacion.md#dónde-están-los-algoritmos-de-detección).

## 7. Convenciones

- **Ramas:** `feature/<descripcion-corta>` sale de `dev` y vuelve a `dev` por Pull Request. El flujo es `feature/* → dev → main`. Nadie hace commit directo a `dev` ni `main` (GitHub lo bloquea).
- **Commits:** en español, en imperativo y describiendo el cambio. Ejemplo: `Agrega seudonimización HMAC a anonymization.py`.
- **Salt (`.env`):** el valor real de `ANON_SALT` se comparte **solo por un canal privado del grupo**. Nunca por Drive público ni por git. Si se filtra, la seudonimización deja de proteger.
- **Notebooks:** limpia las salidas antes de commitear.
- **Datos:** nunca se commitean. Si `git status` muestra algo dentro de `data/`, avisa antes de continuar.
