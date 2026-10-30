#!/bin/sh
set -eu
dig @127.0.0.1 pi.hole +time=2 +tries=1 +short | grep -q .
curl -fsS --max-time 2 http://127.0.0.1:80/healthz >/dev/null
# Upstream resolution is deliberately not a watchdog condition during WAN loss.
