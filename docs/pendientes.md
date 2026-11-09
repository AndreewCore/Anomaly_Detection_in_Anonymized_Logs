# Pendientes — laboratorio

Estado de las mejoras de `tools/c/anomalia.c` y del laboratorio.

## Hecho (2026-11-09)

- [x] **Ground Truth en CSV.** `anomalia ssh` escribe una fila por intento
      (`scenario,segment,burst_id,attacker,src_ip,user,ts_start,ts_end`) con `-g`.
      Es independiente de los logs.
- [x] **Parámetros por argumento.** `-u -w -n -p -d -b -s` controlan usuarios,
      claves, intentos, pausa, duración, ráfagas y semilla (ver `tools/c/README.md`).
- [x] **Varias IPs de origen.** `distribuido` y `spraying` usan `attacker_1/2/3`
      con IPs distintas; cada uno pasa su `-I`.
- [x] **Ráfagas repartidas en el tiempo.** `-d`/`-b` distribuyen el ataque a lo
      largo del segmento (decisión D4).
- [x] **Tráfico legítimo.** `lab/legit_traffic/generate_legit.sh` hace logins
      exitosos con intervalos exponenciales y errores de tipeo ocasionales.
- [x] **Bug del modo `ftp`.** Ya usa el `host` recibido en vez de `localhost`.

## Pendiente

- [ ] **Primera corrida real del laboratorio.** El `docker-compose.yml` y los
      scripts nunca se han ejecutado de punta a punta; falta una captura real
      (requiere `docker-compose` instalado).
- [ ] **Diccionarios de claves más largos.** Con `-n 50` y el diccionario interno
      de 6 claves, las claves se repiten en ciclo. Si se quiere unicidad real,
      pasar `-w` con una lista larga desde el escenario.
- [ ] **Modos `cpu` y `ram`.** Heredados de SIEMLite, fuera del experimento. Se
      pueden quitar en una limpieza futura.
