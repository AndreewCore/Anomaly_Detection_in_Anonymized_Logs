FROM debian:trixie-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends openssh-client sshpass \
 && rm -rf /var/lib/apt/lists/*
COPY generate_legit.sh /generate_legit.sh
RUN chmod +x /generate_legit.sh
ENTRYPOINT ["/generate_legit.sh"]
