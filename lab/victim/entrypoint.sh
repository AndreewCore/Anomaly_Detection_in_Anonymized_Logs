#!/bin/sh
# Arranca rsyslog y sshd en primer plano dentro del contenedor víctima.
set -eu

# Crea los usuarios legítimos para que existan logins exitosos (negativos reales).
for u in ${LEGIT_USERS:-}; do
    id "$u" >/dev/null 2>&1 || useradd -m -s /bin/bash "$u"
    echo "$u:${LEGIT_PASSWORD}" | chpasswd
done

mkdir -p /run/sshd
ssh-keygen -A >/dev/null
rm -f /run/rsyslogd.pid
rsyslogd

# -D: sshd en primer plano. Sin -e, porque -e manda los logs a stderr en vez de a syslog.
exec /usr/sbin/sshd -D
