# tools/c — Herramientas en C

- `anomalia.c`: generador de ataques de fuerza bruta SSH para el laboratorio. Lo
  usa el contenedor atacante; también escribe el Ground Truth de cada intento.
- `agente.c`: agente de monitoreo heredado de SIEMLite; no forma parte del experimento.
- Compila con `make` y limpia con `make clean`. **No se commitean binarios** (`agente`, `anomalia`, `*.o`).

## `anomalia ssh <host> [opciones]`

Ataque de diccionario contra `<host>`. Reparte los intentos en ráfagas a lo largo
del segmento y anota cada intento en un CSV de Ground Truth.

| Opción | Significado | Por defecto |
|---|---|---|
| `-u a,b,c` | usuarios objetivo (separados por comas) | diccionario interno |
| `-w a,b,c` | claves a probar (separadas por comas) | diccionario interno |
| `-n N` | claves probadas por usuario y ráfaga | 1 |
| `-p MS` | pausa entre intentos, en milisegundos | 2000 |
| `-d SEG` | duración del segmento, en segundos | 0 (una sola ráfaga) |
| `-b N` | número de ráfagas repartidas en el segmento | 1 |
| `-s SEED` | semilla del desfase aleatorio entre ráfagas | 0 |
| `-g FILE` | CSV de Ground Truth (se agrega al final) | — |
| `-I IP` | IP de origen propia (para la fila de GT) | — |
| `-a NAME` | nombre del atacante (para la fila de GT) | — |
| `-S NAME` | escenario (para la fila de GT) | — |
| `-k N` | número de segmento (para la fila de GT) | — |

Ejemplo (lo arma el `entrypoint.sh` del atacante a partir del escenario):

```
anomalia ssh victim -u admin -n 50 -p 800 -d 1800 -b 2 -s 1001 \
  -g /gt/concentrado_seg1.csv -I 172.28.1.101 -a attacker_1 -S concentrado -k 1
```

### Formato del Ground Truth

Una fila por intento, encabezado incluido:

```
scenario,segment,burst_id,attacker,src_ip,user,ts_start,ts_end
```

`ts_start`/`ts_end` son UTC ISO-8601 con milisegundos, tomados justo antes y
después del intento. El parser (`scripts/01_parse_logs.py`) usa ese intervalo
para asociar cada intento al evento correcto del `auth.log`.

> Las ráfagas se reparten con `-d`/`-b` para que la partición temporal
> entrenamiento/prueba deje ataques en ambas partes (decisión D4).

Los modos `ftp`, `cpu` y `ram` son heredados de SIEMLite y quedan fuera del
alcance del experimento.
