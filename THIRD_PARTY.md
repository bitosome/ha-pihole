# Upstream components

- [Pi-hole Core](https://github.com/pi-hole/pi-hole/tree/v6.5): EUPL-1.2, copyright Pi-hole contributors.
- [Pi-hole FTL](https://github.com/pi-hole/FTL/tree/v6.8): EUPL-1.2; bundled dependencies retain their licenses.
- [Pi-hole Web](https://github.com/pi-hole/web/tree/v6.6.1): EUPL-1.2.
- [Pi-hole Docker](https://github.com/pi-hole/docker-pi-hole/tree/2026.10.0): upstream lifecycle scripts are vendored unchanged; upstream license is included in `pihole/vendor/LICENSE`.
- [AdGuard dnsproxy](https://github.com/AdguardTeam/dnsproxy/tree/v0.86.0): Apache-2.0. The source-build Dockerfile fetches the exact source commit and its go.sum-verified dependencies.
- Blocklists are fetched at runtime from their maintainers; their respective licenses and source information apply.

The complete corresponding source for the pinned upstream versions is available at the links above. Local wrapper modifications are in this repository. The installed container keeps the Core and Web source trees, and the build stages compile FTL and dnsproxy from the documented commits.
