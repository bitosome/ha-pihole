# Pi-hole for Home Assistant

A source-built Home Assistant app for Pi-hole, with optional secret-protected DNS-over-HTTPS for phones. DNS filtering is provided by **Pi-hole**; AdGuard's open-source **dnsproxy** supplies encrypted transport only.

## Install

Add `https://github.com/bitosome/ha-pihole` to the Home Assistant app store's repositories, then install **Pi-hole**. Set a strong administration password, your public hostname and (if using phone DNS) a separate random URL-safe token of at least 43 characters. Start the app.

The web port defaults to 8092. Plain DNS ports are unpublished by default. No DHCP, host networking, Docker access or Supervisor API permission is requested. Detailed query logging and historical query storage are disabled by default. Persistent Pi-hole data, credentials and the local transport certificate live under `/data` and are included in Supervisor cold backups. DNS is briefly unavailable during a cold backup or app restart.

See [configuration and phone setup](pihole/DOCS.md) and [security model](SECURITY.md).

## Source versions

- Pi-hole Core **v6.5**, commit `f503a65d3a07cb71fd931389f1d3babf718249aa`
- Pi-hole Web **v6.6.1**, commit `fb699c4e3fd6965d1c9a5253250d8a9b3c6f7a0e`
- Pi-hole FTL **v6.8**, commit `29c8b13f4bba0c4f4f47598e45a65cbf1cedac88`
- dnsproxy **v0.86.0**, commit `f2a42ab8563bf782c8c131b03ef2eb44569e7c9e`

FTL and dnsproxy are compiled from these verified source commits. Core and Web are checked out from their verified source commits. Alpine and Go build images are digest-pinned. The upstream Pi-hole Docker 2026.10.0 lifecycle scripts are vendored with URLs and SHA-256 checksums in `pihole/vendor/sources.json`. APK dependencies receive repository security updates at build time; this is not a claim of bit-for-bit reproducible builds.

## Development and updates

`python3 -m unittest discover -s tests -v`

Build with Docker using `docker build -t ha-pihole:test pihole`. Home Assistant also builds it locally. First source compilation takes several minutes. The initial release supports amd64, tested on Home Assistant OS. Enable additional architectures only after their build and runtime acceptance checks.

Update pinned versions and source commits deliberately, run the tests and container acceptance checks, increment `pihole/config.yaml`, then release. Never run Pi-hole's in-place updater inside the container. Defaults in the schema do not silently replace existing options. User-created blocklists and exceptions are preserved. Managed blocklists refresh daily; the add-on owns only rows tagged `ha-pihole:managed`.

## License and attribution

Our glue code is MIT-licensed. Pi-hole components and vendored scripts retain their upstream licenses; see [THIRD_PARTY.md](THIRD_PARTY.md). No affiliation with or endorsement by Pi-hole or AdGuard is implied.
