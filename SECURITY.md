# Security model

- A unique administration password is mandatory; a passwordless public instance is refused.
- Phone DNS requires a separate 256-bit random bearer path. Neither the path nor generated profiles belong in Git or public logs. Treat backups as secrets.
- NGINX does not log request URLs, verifies the loopback dnsproxy TLS certificate, rate-limits DNS and authentication, and blocks the standard unprotected DNS path.
- FTL's administrative listener and both dnsproxy instances bind to loopback inside the container. Only NGINX is published; LAN DNS ports default to disabled.
- No DHCP or NTP service, broad host privileges, Docker access or Supervisor credentials. Pi-hole's upstream launcher drops the DNS process to its pihole user.
- If any long-running service fails, the wrapper stops the entire process group and exits, allowing Supervisor to restart it. Boot and watchdog settings must be enabled by the operator.
- Local query history is disabled, but Cloudflare and encrypted upstream resolvers remain trust boundaries. This is not anonymity or a universal anti-tracking guarantee.
- Scope is personal/family use. The token is not per-user identity or a public recursive DNS service. Keep the token private, rotate it if disclosed, and use network-level controls for larger deployments.
