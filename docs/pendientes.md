# Pendientes — `tools/c/anomalia.c`

Mejoras necesarias para usar `anomalia.c` en el experimento. Ninguna está implementada todavía.

- [ ] **Ground Truth en CSV.** Escribir una fila por ataque con escenario, timestamp de inicio y fin, IP de origen y usuarios objetivo. Debe ser independiente de los logs.
- [ ] **Bug del modo `ftp`.** Ignora el argumento `host` y siempre ataca `localhost` (`ftp://localhost/` en `intento_ftp`).
- [ ] **Una sola IP de origen.** Los escenarios *distribuido* y *spraying* necesitan varios contenedores atacantes con IPs distintas (ya definidos en `lab/docker-compose.yml`) o un orquestador de escenarios.
- [ ] **Parámetros por argumento.** Hoy el número de intentos (`INTENTOS`), la pausa (`PAUSA`) y la lista de credenciales están fijos en el código.
- [ ] **Tráfico legítimo.** Generar logins exitosos para que existan negativos reales (stub en `lab/legit_traffic/`).
- [ ] **Ráfagas repartidas en el tiempo.** El ataque debe repartirse a lo largo de la captura para que la partición temporal deje ataques en la parte de prueba (decisión D4 en `diseno_experimento.md`).
- [ ] **Modos `cpu` y `ram`.** No son relevantes para esta investigación (venían de SIEMLite). Se pueden quitar o ignorar.
