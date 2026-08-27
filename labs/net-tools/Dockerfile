FROM debian:bookworm-slim
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    bash iproute2 iputils-ping dnsutils curl netcat-openbsd nmap tcpdump procps traceroute \
    ca-certificates less vim-tiny && rm -rf /var/lib/apt/lists/*
CMD ["sleep","infinity"]
