#!/bin/sh
# Genera tráfico legítimo: logins SSH exitosos de un subconjunto de usuarios, a
# intervalos aleatorios (exponenciales, con semilla). Cada cierto tiempo simula
# un error humano (clave mal escrita una vez antes de acertar), para que existan
# negativos reales y no todo fallo en el log sea un ataque.
#
# La bitácora /out/legit_<id>_seg<k>.csv es APOYO para la revisión humana del
# Ground Truth, no una etiqueta: las etiquetas se derivan del GT de los atacantes.
set -eu

HOST="${TARGET_HOST:-victim}"
PASS="${LEGIT_PASSWORD:-cambiar_en_lab}"
SEED="${SEED:-1}"
TYPO_RATE="${TYPO_RATE:-0.05}"
CLIENT_ID="${CLIENT_ID:-legit}"
SEGMENT="${SEGMENT:-1}"
DURATION_S=$(( ${SEGMENT_MINUTES:-30} * 60 ))
MEAN_INTERVAL="${MEAN_INTERVAL:-15}"   # segundos promedio entre logins
# Lista de usuarios separada por comas -> por espacios, para recorrerla en sh.
USERS=$(echo "${LEGIT_USERS:-alice}" | tr ',' ' ')
set -- $USERS
NUSERS=$#

OUT="/out/legit_${CLIENT_ID}_seg${SEGMENT}.csv"
mkdir -p /out
[ -s "$OUT" ] || echo "client_id,segment,user,ts,result,typo" > "$OUT"

now_iso() { date -u +%Y-%m-%dT%H:%M:%S.%3NZ; }

# Un login exitoso: ejecuta `true` y cierra. Genera "Accepted password" en auth.log.
login_ok() {
    sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=3 \
        -o NumberOfPasswordPrompts=1 "$1@$HOST" true >/dev/null 2>&1 || true
}

# Un intento con clave incorrecta: genera "Failed password" de un usuario legítimo.
login_typo() {
    sshpass -p "clave_incorrecta" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=3 \
        -o NumberOfPasswordPrompts=1 "$1@$HOST" true >/dev/null 2>&1 || true
}

START=$(date +%s)
i=0
while [ $(( $(date +%s) - START )) -lt "$DURATION_S" ]; do
    i=$((i + 1))
    # awk como PRNG con semilla estable: elige usuario, intervalo exponencial y
    # decide el typo. Reproducible: misma semilla -> misma secuencia.
    line=$(awk -v seed="$((SEED * 100000 + i))" -v n="$NUSERS" \
               -v mean="$MEAN_INTERVAL" -v typo="$TYPO_RATE" 'BEGIN{
        srand(seed);
        u = int(rand() * n) + 1;
        iv = -mean * log(1 - rand()); if (iv < 1) iv = 1;
        t = (rand() < typo) ? 1 : 0;
        printf "%d %d %d", u, iv, t;
    }')
    uidx=$(echo "$line" | cut -d' ' -f1)
    interval=$(echo "$line" | cut -d' ' -f2)
    is_typo=$(echo "$line" | cut -d' ' -f3)
    eval "user=\${$uidx}"

    if [ "$is_typo" = "1" ]; then
        login_typo "$user"
        echo "$CLIENT_ID,$SEGMENT,$user,$(now_iso),failed,1" >> "$OUT"
        sleep 1
    fi
    login_ok "$user"
    echo "$CLIENT_ID,$SEGMENT,$user,$(now_iso),accepted,0" >> "$OUT"

    sleep "$interval"
done

echo "[$CLIENT_ID] tráfico legítimo del segmento $SEGMENT terminado tras ${DURATION_S}s"
