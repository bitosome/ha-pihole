# Configuration

1. Set `admin_password` to a unique password (at least 16 characters). It is separate from the phone DNS token. Never use a Home Assistant or router password here.
2. Set `public_hostname` to the hostname routed by your existing HTTPS reverse proxy.
3. For phone filtering, enable `doh_enabled` and generate `doh_token` with `python3 -c 'import secrets; print(secrets.token_urlsafe(32))'`. Store it privately.
4. Keep `privacy_level: 3` for maximum Pi-hole query privacy. Detailed DNS logging and disk query history remain disabled at every level. Lower privacy levels only change live in-memory statistics; restarting clears them.
5. The default encrypted upstream is Quad9. `upstream_dns` accepts encrypted `tls://`, `https://` or `quic://` endpoints; no unfiltered plaintext fallback is configured. Bootstrap DNS resolves the upstream hostname, not your browsing queries.
6. `blocklists` defaults to HaGeZi Pro and AdGuard DNS, including DNS-compatible Cyrillic/Russian advertising and tracker rules. Both also include Estonian advertising hosts. They cannot remove ads served from the same domain as wanted content. Browser content blocking complements DNS filtering.

## Existing Cloudflared app

Add one entry to **additional_hosts**, retaining every existing host:

```yaml
- hostname: pihole.example.com
  service: http://local-pihole:80
```

Use the actual app hostname shown by Supervisor; repository installs have a repository-prefixed name. Restart **Cloudflared only** after saving. This normally registers the public hostname through the app's existing certificate. Do not publish DNS port 53 to the Internet. The ordinary `/dns-query` path returns 404; only `/doh/<private-token>/dns-query` is accepted.

Administration requires the Pi-hole password. Phone DNS uses a separate bearer token so iOS does not need an interactive Cloudflare Access login. Apply any additional Access policy only to administration, not to the token-protected DNS path. Do not configure the entire hostname to bypass Pi-hole authentication.

## iPhone profile

Generate a profile locally using a private copy of the app options:

```
python3 scripts/make_profile.py /private/path/options.json /private/path/Pi-hole.mobileconfig
```

Transfer it privately (for example AirDrop), then install under **Settings → General → VPN & Device Management**. It is a removable DNS Settings profile, not a VPN and not a certificate-authority installation. No TLS interception certificate is installed. The profile is unsigned; inspect its payload before installation. Never publish the profile: it contains your DNS access token.

The profile applies system DNS on cellular and Wi-Fi. It cannot force apps that hard-code another encrypted resolver or IP address to use Pi-hole, and other VPNs or device-management policies may override it. Test on cellular and Wi-Fi. iCloud Private Relay can bypass the chosen resolver; Pi-hole returns the standard network-unavailable indication for its discovery names. Do not mistake the resulting Private Relay warning for a DNS failure.

To revoke a lost profile, change `doh_token`, restart the app, generate and install a new profile. Old token URLs then return 404. Disable `doh_enabled` to revoke all phone access. If filtering or connectivity fails, disable/remove the DNS profile in Settings; don't silently add an unfiltered fallback that defeats the blocking policy.

## Privacy limits

The hostname is proxied through Cloudflare, which terminates HTTPS and can observe DNS requests and the secret URL. Pi-hole and local NGINX do not retain query/access logs by default, but that does not control Cloudflare's retention or the upstream provider. Disabling Gateway logs is irrelevant when not using Gateway. Review Cloudflare account logging policies separately if required.

DNS blocking cannot prevent all personalization, first-party tracking, account-based profiling, fingerprinting or same-domain ads. Use Safari's tracking protection, deny app tracking requests and disable account ad personalization as well. YouTube and many social-media ads need separate browser/platform measures.

## Recovery

Back up the app with Supervisor before upgrading. Cold backups stop DNS briefly and include `/data`. Restore that app backup to recover lists, exceptions and credentials. Removing the phone profile restores the phone's prior DNS behavior. LAN DNS is opt-in: map both TCP and UDP 53 only after validating the server, address stability and firewall policy. This app does not change router DHCP/DNS or Home Assistant's own resolver.
