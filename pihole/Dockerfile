ARG ALPINE=alpine:3.24.2@sha256:294b683cb724975bec92580e1e685676bd4b50bda910ddb8c51d4cabeaec77e6
FROM ${ALPINE} AS ftl
RUN apk add --no-cache build-base linux-headers libcap-dev cmake git bash xxd nettle-dev gmp-dev libidn2-dev libunistring-dev mbedtls-dev
RUN git clone --branch v6.8 --depth 1 https://github.com/pi-hole/FTL.git /src \
 && test "$(git -C /src rev-parse HEAD)" = 29c8b13f4bba0c4f4f47598e45a65cbf1cedac88
WORKDIR /src
RUN MAKEFLAGS=-j2 bash build.sh '-DSTATIC=false -DUSE_READLINE=OFF -DUSE_DBUS=OFF -DUSE_NFTSET=OFF -DUSE_CONNTRACK=OFF' \
 && ./pihole-FTL verify

FROM golang:1.26.8-alpine3.24@sha256:8ac98ca534ac3f51e1f420a1dd2c15e74c75cfa0f23f3ad27eb5d7236c349a0c AS dnsproxy
RUN apk add --no-cache git
RUN git clone --branch v0.86.0 --depth 1 https://github.com/AdguardTeam/dnsproxy.git /src \
 && test "$(git -C /src rev-parse HEAD)" = f2a42ab8563bf782c8c131b03ef2eb44569e7c9e
WORKDIR /src
RUN CGO_ENABLED=0 go build -trimpath -ldflags '-s -w' -o /dnsproxy .

FROM ${ALPINE}
RUN apk add --no-cache bash bash-completion bind-tools binutils coreutils curl git grep iproute2 jq libcap logrotate ncurses procps-ng psmisc shadow sudo tzdata unzip wget python3 nginx openssl nettle gmp libidn2 libunistring mbedtls
RUN git clone --branch v6.5 --depth 1 https://github.com/pi-hole/pi-hole.git /etc/.pihole \
 && test "$(git -C /etc/.pihole rev-parse HEAD)" = f503a65d3a07cb71fd931389f1d3babf718249aa \
 && git clone --branch v6.6.1 --depth 1 https://github.com/pi-hole/web.git /var/www/html/admin \
 && test "$(git -C /var/www/html/admin rev-parse HEAD)" = fb699c4e3fd6965d1c9a5253250d8a9b3c6f7a0e \
 && cd /etc/.pihole \
 && install -dm755 /opt/pihole /etc/pihole /var/log/pihole /var/lib/logrotate \
 && install -m755 -t /opt/pihole gravity.sh advanced/Scripts/*.sh advanced/Scripts/COL_TABLE \
 && install -m755 -t /usr/local/bin pihole \
 && install -m755 advanced/Templates/pihole-FTL-prestart.sh advanced/Templates/pihole-FTL-poststop.sh /opt/pihole/ \
 && install -m644 advanced/Templates/logrotate /etc/logrotate.d/pihole \
 && addgroup -S pihole -g 1000 && adduser -S pihole -G pihole -u 1000 \
 && git config --system --add safe.directory /etc/.pihole \
 && git config --system --add safe.directory /var/www/html/admin \
 && chmod a+r /etc/gitconfig
COPY --from=ftl /src/pihole-FTL /usr/bin/pihole-FTL
COPY --from=dnsproxy /dnsproxy /usr/local/bin/dnsproxy
COPY vendor/start.sh vendor/bash_functions.sh vendor/prefix-time.sh /usr/bin/
COPY vendor/crontab.txt /crontab.txt
COPY launcher.py /opt/addon/launcher.py
COPY healthcheck.sh /opt/addon/healthcheck.sh
RUN chmod 755 /usr/bin/start.sh /usr/bin/prefix-time.sh /opt/addon/healthcheck.sh \
 && touch /macvendor.db && echo source-2026.10.0 > /pihole.docker.tag \
 && sed -i 's/59 1  \* \* 0/59 1  * * */' /crontab.txt
ENV DNSMASQ_USER=pihole FTL_CMD=no-daemon TAIL_FTL_LOG=0
HEALTHCHECK --interval=30s --timeout=8s --start-period=300s CMD /opt/addon/healthcheck.sh
ENTRYPOINT ["python3", "/opt/addon/launcher.py"]
