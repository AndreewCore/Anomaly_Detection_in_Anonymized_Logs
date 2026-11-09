# Escenarios de ataque

Cada `<escenario>.env` define un escenario para `docker compose --env-file`. A
diferencia de los antiguos `.yml` (solo especificación), estos **se ejecutan**:
`anomalia.c` ya acepta los parámetros.

| Variable | Significado |
|---|---|
| `PROFILE` | perfil de compose a activar (igual al nombre del escenario) |
| `SEGMENT_MINUTES` | duración de cada segmento (90 min = 3 × 30) |
| `SEGMENTS` | nº de segmentos recomendados para completar el escenario |
| `BURSTS_PER_SEGMENT` | ráfagas de ataque dentro de cada segmento |
| `SEED_BASE` | semilla base; la de cada segmento es `SEED_BASE + k` |
| `PAUSE_MS` | pausa entre intentos del atacante |
| `LEGIT_PASSWORD` | clave de los usuarios legítimos |
| `A<n>_USERS` | usuarios objetivo del atacante n (coma) |
| `A<n>_N` | claves probadas por usuario del atacante n |

| Escenario | Forma | Atacantes | Objetivo |
|---|---|---|---|
| `concentrado` | 1 IP → 1 cuenta | attacker_1 | `admin`, 50 claves |
| `multi_cuenta` | 1 IP → N cuentas | attacker_1 | 6 cuentas, 10 claves c/u |
| `distribuido` | N IPs → 1 cuenta | 1,2,3 | `admin` desde 3 IPs (2 comparten /24) |
| `spraying` | N IPs → N cuentas | 1,2,3 | 8 cuentas, 2 claves c/u |

No se editan a mano para correr: `lab/capture.sh <escenario> <segmento>` los carga.
