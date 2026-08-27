FROM debian:bookworm-slim
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    bash coreutils findutils grep sed gawk iproute2 iputils-ping procps curl netcat-openbsd \
    python3 ca-certificates less vim-tiny && rm -rf /var/lib/apt/lists/*
RUN useradd -m -s /bin/bash student && mkdir -p /challenge /srv/site && \
    printf 'Kali Academy target\n' > /srv/site/index.html && \
    printf 'Pip hid this file for the permissions lesson.\n' > /challenge/hidden.txt && \
    chown -R student:student /challenge /srv/site
USER student
WORKDIR /home/student
EXPOSE 8080
ENV LAB_SCENARIO=clean
CMD ["bash","-lc","if [ \"$LAB_SCENARIO\" = permissions ]; then chmod 000 /challenge/hidden.txt; else chmod 644 /challenge/hidden.txt; fi; if [ \"$LAB_SCENARIO\" = broken-http ]; then sleep infinity; else exec python3 -m http.server 8080 --directory /srv/site; fi"]
