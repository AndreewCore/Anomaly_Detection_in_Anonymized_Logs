# Contexto de build: raíz del repo (ver docker-compose.yml), para copiar tools/c/.
FROM debian:trixie-slim AS build
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc make libc6-dev \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY tools/c/ ./
RUN make anomalia

FROM debian:trixie-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends openssh-client sshpass curl \
 && rm -rf /var/lib/apt/lists/*
COPY --from=build /src/anomalia /usr/local/bin/anomalia
COPY lab/attacker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
