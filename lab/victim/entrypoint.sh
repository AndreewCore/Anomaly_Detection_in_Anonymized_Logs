#!/bin/sh
# Arranca rsyslog y sshd en primer plano dentro del contenedor víctima.
# Crea los usuarios legítimos de /etc/legit_users.txt para que existan logins
# exitosos (negativos reales); si no está montado, usa una lista mínima.
set -eu

USERS_FILE=/etc/legit_users.txt
if [ -f "$USERS_FILE" ]; then
    USERS=$(grep -vE '^\s*#|^\s*$' "$USERS_FILE")
else
    USERS="alice bob carol"
fi

for u in $USERS; do
    id "$u" >/dev/null 2>&1 || useradd -m -s /bin/bash "$u"
    echo "$u:${LEGIT_PASSWORD:-cambiar_en_lab}" | chpasswd
done

mkdir -p /run/sshd
ssh-keygen -A >/dev/null
rm -f /run/rsyslogd.pid
rsyslogd

# -D: sshd en primer plano. Sin -e, porque -e manda los logs a stderr y no a syslog
# (y entonces rsyslog no escribiría auth.log, que es justo lo que se analiza).
exec /usr/sbin/sshd -D
