# lab/ — Laboratorio Docker (se ejecuta en Windows con Docker Desktop)

- `docker-compose.yml` levanta la víctima (sshd + rsyslog), los atacantes (`anomalia.c`) y el generador de tráfico legítimo.
- Cada escenario de ataque es un *profile* de compose; su descripción está en `scenarios/`.
- El `auth.log` de la víctima cae en `output/victim/`; de ahí se sube a Drive. **`output/` nunca se commitea.**
- El Ground Truth se registra aparte de los logs (ver `docs/pendientes.md`), nunca se deduce de ellos.
