FROM debian:bookworm-slim@sha256:88200866dfff7ea7f5cbcb6ec7c8a701889efe6fe859fe64d6990e4b07ea4171
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    bash iproute2 iputils-ping dnsutils curl netcat-openbsd nmap tcpdump procps traceroute \
    ca-certificates less vim-tiny && rm -rf /var/lib/apt/lists/*
CMD ["sleep","infinity"]
