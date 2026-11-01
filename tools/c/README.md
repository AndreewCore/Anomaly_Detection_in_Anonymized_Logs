# tools/c — Herramientas en C

- `anomalia.c`: generador de ataques (fuerza bruta SSH/FTP). Lo usa el contenedor atacante del laboratorio.
- `agente.c`: agente de monitoreo heredado del proyecto SIEMLite; no forma parte del experimento.
- Compila con `make` y limpia con `make clean`. **No se commitean binarios** (`agente`, `anomalia`, `*.o`).
- Las mejoras pendientes de `anomalia.c` están en `docs/pendientes.md`.
