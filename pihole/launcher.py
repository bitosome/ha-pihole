"""HA lifecycle glue. DNS and HTTPS DNS are handled by upstream Pi-hole/dnsproxy."""
import ipaddress
import json
import os
from pathlib import Path
import re
import signal
import sqlite3
import subprocess
import sys
import time
from urllib.parse import urlsplit

DATA = Path('/data')
MANAGED = 'ha-pihole:managed'

def validate(o):
    if len(o.get('admin_password', '')) < 16:
        raise ValueError('Set an administration password of at least 16 characters')
    host = o.get('public_hostname', '')
    if not re.fullmatch(r'(?=.{1,253}$)[a-zA-Z0-9]+(?:[.-][a-zA-Z0-9]+)*', host):
        raise ValueError('public_hostname must be a DNS hostname, without a scheme or path')
    if o.get('doh_enabled') and not re.fullmatch(r'[A-Za-z0-9_-]{43,128}', o.get('doh_token', '')):
        raise ValueError('doh_token must be a random URL-safe secret of at least 43 characters')
    if not re.fullmatch(r'[A-Za-z0-9_+/-]+', o.get('timezone', '')):
        raise ValueError('Invalid timezone')
    if type(o.get('privacy_level')) is not int or o['privacy_level'] not in range(4):
        raise ValueError('privacy_level must be 0 through 3')
    for key in ['upstream_dns', 'bootstrap_dns', 'blocklists']:
        if not isinstance(o.get(key), list) or not o[key] or any(not isinstance(x, str) or '\n' in x for x in o[key]):
            raise ValueError(key + ' must be a nonempty list')
    for url in o['upstream_dns']:
        u = urlsplit(url)
        if u.scheme not in ('tls', 'https', 'quic') or not u.hostname or u.username or u.password:
            raise ValueError('Only encrypted upstream DNS URLs are allowed')
    for url in o['blocklists']:
        u = urlsplit(url)
        if u.scheme != 'https' or not u.hostname or u.username or u.password or any(c in url for c in '\r\n'):
            raise ValueError('Blocklists must use HTTPS without credentials')
    return o

def reconcile_lists(db_path, urls):
    """Only change rows owned by this add-on. Never take ownership of user rows."""
    with sqlite3.connect(db_path, timeout=30) as db:
        db.execute('PRAGMA foreign_keys=ON')
        old = {r[0] for r in db.execute('SELECT address FROM adlist WHERE comment=?', (MANAGED,))}
        wanted = set(urls)
        for u in old - wanted:
            db.execute('DELETE FROM adlist WHERE address=? AND comment=?', (u, MANAGED))
        for u in wanted:
            db.execute('INSERT OR IGNORE INTO adlist(address,enabled,comment) VALUES(?,1,?)', (u, MANAGED))
        return old != wanted

def nginx_config(o):
    doh = ''
    if o['doh_enabled']:
        doh = f'''
        location = /doh/{o['doh_token']}/dns-query {{
            limit_req zone=dns_rate burst=100 nodelay;
            limit_except GET POST {{ deny all; }}
            proxy_pass https://127.0.0.1:8053/dns-query;
            proxy_ssl_verify on;
            proxy_ssl_trusted_certificate /data/doh.crt;
            proxy_ssl_name localhost;
            proxy_set_header Host localhost;
            proxy_set_header CF-Connecting-IP "";
            proxy_set_header X-Forwarded-For "";
            proxy_set_header X-Real-IP "";
            proxy_hide_header Cache-Control;
            add_header Cache-Control "no-store" always;
        }}'''
    return f'''user nginx;
worker_processes 1;
pid /run/nginx.pid;
error_log /dev/null crit;
events {{ worker_connections 512; }}
http {{
    access_log off;
    server_tokens off;
    limit_req_zone $binary_remote_addr zone=dns_rate:1m rate=40r/s;
    limit_req_zone $binary_remote_addr zone=login_rate:1m rate=5r/m;
    client_max_body_size 64k;
    client_body_timeout 10s;
    proxy_connect_timeout 3s;
    proxy_read_timeout 10s;
    proxy_buffering off;
    server {{
        listen 80;
        add_header Referrer-Policy no-referrer always;
        add_header X-Content-Type-Options nosniff always;
        location = /healthz {{ allow 127.0.0.1; deny all; return 200 'ok'; }}
        {doh}
        location /doh/ {{ return 404; }}
        location = /dns-query {{ return 404; }}
        location = /api/auth {{
            limit_req zone=login_rate burst=5 nodelay;
            proxy_pass http://127.0.0.1:8081;
            proxy_set_header Host {o['public_hostname']};
        }}
        location / {{
            proxy_pass http://127.0.0.1:8081;
            proxy_set_header Host {o['public_hostname']};
        }}
    }}
}}'''

def environment(o):
    return {
        'TZ': o['timezone'],
        'FTLCONF_webserver_api_password': o['admin_password'],
        'FTLCONF_webserver_domain': o['public_hostname'],
        'FTLCONF_webserver_port': '127.0.0.1:8081',
        'FTLCONF_dns_listeningMode': 'ALL',
        'FTLCONF_dns_upstreams': '127.0.0.1#5353',
        'FTLCONF_dns_dnssec': 'true',
        'FTLCONF_dns_queryLogging': 'false',
        'FTLCONF_dns_specialDomains_iCloudPrivateRelay': 'true',
        'FTLCONF_misc_privacylevel': str(o['privacy_level']),
        'FTLCONF_database_maxDBdays': '0',
        'FTLCONF_database_DBimport': 'false',
        'FTLCONF_resolver_resolveIPv4': 'false',
        'FTLCONF_resolver_resolveIPv6': 'false',
        'FTLCONF_dhcp_active': 'false',
        'FTLCONF_ntp_ipv4_active': 'false',
        'FTLCONF_ntp_ipv6_active': 'false',
        'FTLCONF_ntp_sync_active': 'false',
        'TAIL_FTL_LOG': '0',
    }

def main():
    os.umask(0o077)
    o = validate(json.loads((DATA / 'options.json').read_text()))
    state = DATA / 'pihole'
    state.mkdir(exist_ok=True)
    os.chown(state, 1000, 1000)
    link = Path('/etc/pihole')
    if not link.is_symlink():
        # Image directory is empty. Refuse to overwrite unexpectedly populated state.
        link.rmdir()
        link.symlink_to(state)
    db = state / 'gravity.db'
    seed_marker = DATA / 'seed-blocklists.json'
    fresh = not db.exists()
    lists_changed = False
    if fresh:
        seed_marker.write_text(json.dumps(o['blocklists']))
        (state / 'adlists.list').write_text('\n'.join(o['blocklists']) + '\n')
        os.chown(state / 'adlists.list', 1000, 1000)
    elif db.stat().st_size:
        lists_changed = reconcile_lists(db, o['blocklists'])
    os.environ.update(environment(o))
    children = []
    stopping = False
    def stop(*_):
        nonlocal stopping
        if stopping:
            return
        stopping = True
        for child in children:
            try: os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError: pass
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    def start(args, quiet=False):
        # Each child owns a process group; never log commands containing secrets.
        p = subprocess.Popen(args, start_new_session=True, stdout=subprocess.DEVNULL if quiet else None, stderr=subprocess.DEVNULL if quiet else None)
        children.append(p)
        return p
    try:
        args = ['dnsproxy', '--listen=127.0.0.1', '--port=5353', '--timeout=5s', '--refuse-any', '--max-go-routines=128']
        for u in o['upstream_dns']: args += ['--upstream', u]
        for b in o['bootstrap_dns']: args += ['--bootstrap', b]
        start(args, quiet=True)
        if o['doh_enabled']:
            if not (DATA / 'doh.key').exists():
                subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '3650', '-keyout', str(DATA / 'doh.key'), '-out', str(DATA / 'doh.crt'), '-subj', '/CN=localhost', '-addext', 'subjectAltName=DNS:localhost'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            start(['dnsproxy', '--listen=127.0.0.1', '--port=0', '--https-port=8053', '--tls-crt=/data/doh.crt', '--tls-key=/data/doh.key', '--upstream=127.0.0.1:53', '--timeout=5s', '--refuse-any', '--max-go-routines=128'], quiet=True)
        Path('/etc/nginx/nginx.conf').write_text(nginx_config(o))
        subprocess.run(['nginx', '-t'], check=True)
        ftl = start(['/usr/bin/start.sh'])
        # Do not expose the public frontend until Pi-hole has initialized its password.
        for _ in range(600):
            if stopping: return 0
            if any(p.poll() is not None for p in children): raise RuntimeError('A service stopped during startup')
            r = subprocess.run(['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', '--max-time', '1', 'http://127.0.0.1:8081/api/auth'], capture_output=True)
            if r.stdout in (b'200', b'401'): break
            time.sleep(1)
        else: raise RuntimeError('Pi-hole startup timed out')
        if seed_marker.exists():
            with sqlite3.connect(db) as con:
                con.executemany('UPDATE adlist SET comment=? WHERE address=? AND comment=?', [(MANAGED, u, 'Migrated from /etc/pihole/adlists.list') for u in json.loads(seed_marker.read_text())])
            seed_marker.unlink()
        if lists_changed:
            gravity = start(['pihole', '-g'])
            deadline = time.monotonic() + 300
            while gravity.poll() is None and not stopping and time.monotonic() < deadline:
                time.sleep(0.5)
            if stopping: return 0
            if gravity.poll() != 0: raise RuntimeError('Blocklist refresh failed or timed out')
            children.remove(gravity)
        start(['nginx', '-g', 'daemon off;'])
        print('Pi-hole ready: detailed query logging disabled; authenticated administration.', flush=True)
        while not stopping:
            if any(p.poll() is not None for p in children): raise RuntimeError('A service stopped unexpectedly')
            time.sleep(1)
        return 0
    finally:
        stop()
        deadline = time.monotonic() + 20
        for child in children:
            try: child.wait(timeout=max(0.1, deadline-time.monotonic()))
            except subprocess.TimeoutExpired:
                try: os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError: pass
        # Cold backups stop the process group before Supervisor copies /data.

if __name__ == '__main__':
    try: sys.exit(main())
    except Exception as e:
        print('Pi-hole add-on failed: ' + str(e), file=sys.stderr)
        sys.exit(1)
