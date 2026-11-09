# lab/ — Laboratorio Docker (se ejecuta en Linux con Docker Engine)

Genera registros de autenticación SSH variados (muchos usuarios y muchas IPs) con
su Ground Truth, dentro de una red Docker aislada. **No se levanta a mano:** usa
`capture.sh`, que fija la semilla del segmento, espera a que termine la carga y
guarda la salida con un nombre descriptivo.

## Qué hay dentro

- `docker-compose.yml`: la víctima (sshd + rsyslog), 8 clientes legítimos en 5
  subredes /24 y hasta 3 atacantes. Los servicios comparten plantilla con anclas
  YAML; cada uno cambia su IP y su configuración por variables de entorno.
- `users.txt`: los 20 usuarios legítimos que crea la víctima.
- `scenarios/<esc>.env`: parámetros de cada escenario (perfil de compose,
  duración, ráfagas, semilla base, usuarios y nº de intentos por atacante).
- `capture.sh`: orquesta una captura de un segmento de principio a fin.
- `victim/`, `attacker/`, `legit_traffic/`: imágenes de cada rol.
- `output/`: salida de las capturas. **Nunca se commitea.**

## Red (por qué estas IPs)

| Nodo | IP | Subred /24 | Nota |
|---|---|---|---|
| víctima | 172.28.0.10 | — | sshd + rsyslog |
| legit_1..3 | 172.28.10.11-13 | 172.28.10.0/24 | oficina A |
| legit_4..5 | 172.28.11.11-12 | 172.28.11.0/24 | oficina B |
| legit_6 | 172.28.12.11 | 172.28.12.0/24 | VPN (cuentas de varias oficinas) |
| legit_7 | 172.28.1.51 | 172.28.1.0/24 | **comparte /24 con attacker_1/2** |
| legit_8 | 172.28.2.51 | 172.28.2.0/24 | **comparte /24 con attacker_3** |
| attacker_1/2 | 172.28.1.101/102 | 172.28.1.0/24 | la generalización /24 los fusiona |
| attacker_3 | 172.28.2.101 | 172.28.2.0/24 | queda separado |

Que un cliente legítimo comparta /24 con atacantes es a propósito: mide el daño
colateral de generalizar la IP a /24 (decisión D1 en `docs/diseno_experimento.md`).

## Capturar (90 min = 3 segmentos de 30 min, divisibles en el tiempo)

```bash
lab/capture.sh concentrado 1        # segmento 1 del escenario concentrado
lab/capture.sh concentrado 2        # el 2 puede ser otro día
lab/capture.sh concentrado 3
lab/capture.sh concentrado 1 --minutes 5   # captura corta de prueba
```

Perfiles/escenarios: `concentrado`, `multi_cuenta`, `distribuido`, `spraying`.

Cada captura termina en
`output/<escenario>/<AAAA-MM-DD_HHMM>__seg<k>__<usuario>__<N>eventos__<min>min/`
con `victim/auth.log`, `gt/<esc>_seg<k>.csv`, `legit/*.csv` y `manifest.json`.

## Ver e inspeccionar mientras corre

```bash
tail -f lab/output/_actual/victim/auth.log                 # el log en vivo
docker compose -f lab/docker-compose.yml logs -f attacker_1 # qué hace un atacante
docker compose -f lab/docker-compose.yml ps                 # contenedores vivos
docker compose -f lab/docker-compose.yml exec victim bash   # entrar a la víctima
```

## Prerrequisitos (Arch)

```bash
sudo pacman -S docker docker-compose docker-buildx
sudo systemctl enable --now docker
sudo usermod -aG docker $USER      # luego cierra sesión y vuelve a entrar
```

El Ground Truth se registra aparte de los logs (lo escribe `anomalia.c`), nunca se
deduce de ellos. El `auth.log` usa formato RFC 3339 para alinear sin ambigüedad.
