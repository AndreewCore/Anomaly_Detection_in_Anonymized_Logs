FROM debian:trixie-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends openssh-server rsyslog \
 && rm -rf /var/lib/apt/lists/*

COPY rsyslog.conf /etc/rsyslog.conf
COPY sshd_config  /etc/ssh/sshd_config
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/entrypoint.sh"]
