import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest
spec = importlib.util.spec_from_file_location('launcher', Path(__file__).parents[1] / 'pihole/launcher.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def options():
    return dict(admin_password='a-test-password-long-enough', public_hostname='pihole.example.com', doh_enabled=True, doh_token='x'*43, timezone='Europe/Tallinn', privacy_level=3, upstream_dns=['tls://dns.quad9.net'], bootstrap_dns=['9.9.9.9:53'], blocklists=['https://example.com/list'])

class Tests(unittest.TestCase):
    def test_valid(self):
        m.validate(options())
    def test_injection(self):
        for key, val in [('public_hostname','a; }'), ('doh_token','x'*43+'\n'), ('timezone','Europe/Tallinn\n')]:
            o=options();o[key]=val
            with self.assertRaises(ValueError):m.validate(o)
    def test_no_passwordless_or_short_token(self):
        for key,val in [('admin_password',''),('doh_token','weak')]:
            o=options();o[key]=val
            with self.assertRaises(ValueError):m.validate(o)
    def test_encrypted_upstreams(self):
        for v in ['8.8.8.8','http://example.com/dns-query','https://user:pass@host/path']:
            o=options();o['upstream_dns']=[v]
            with self.assertRaises(ValueError):m.validate(o)
    def test_blocklist_urls(self):
        for v in ['file:///etc/passwd','http://example.com','https://example.com/\n']:
            o=options();o['blocklists']=[v]
            with self.assertRaises(ValueError):m.validate(o)
    def test_no_public_doh_without_secret(self):
        o=options();o['doh_enabled']=False
        c=m.nginx_config(o)
        self.assertNotIn('proxy_pass https:',c)
        self.assertIn('location = /dns-query { return 404;',c)
    def test_private_doh_transport(self):
        c=m.nginx_config(options())
        self.assertIn('proxy_ssl_verify on',c)
        self.assertIn('access_log off',c)
        self.assertIn('Cache-Control "no-store"',c)
        self.assertIn('limit_req zone=dns_rate',c)
    def test_privacy_and_dhcp(self):
        e=m.environment(options())
        self.assertEqual(e['FTLCONF_database_maxDBdays'],'0')
        self.assertEqual(e['FTLCONF_dns_queryLogging'],'false')
        self.assertEqual(e['FTLCONF_dhcp_active'],'false')
    def test_idempotent_list_ownership(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'gravity.db'
            with sqlite3.connect(p) as db:
                db.execute('CREATE TABLE adlist(address TEXT UNIQUE, enabled INTEGER, comment TEXT)')
                db.execute("INSERT INTO adlist VALUES('https://user/list',0,'user')")
            self.assertTrue(m.reconcile_lists(p,['https://managed/a']))
            self.assertFalse(m.reconcile_lists(p,['https://managed/a']))
            m.reconcile_lists(p,['https://managed/b','https://user/list'])
            with sqlite3.connect(p) as db:
                rows=db.execute('SELECT address,enabled,comment FROM adlist ORDER BY address').fetchall()
            self.assertEqual(rows,[('https://managed/b',1,m.MANAGED),('https://user/list',0,'user')])

if __name__ == '__main__':unittest.main()

class ProfileTests(unittest.TestCase):
    def test_removable_all_domain_profile(self):
        p = Path(__file__).parents[1] / 'scripts/make_profile.py'
        spec = importlib.util.spec_from_file_location('profile_builder', p)
        b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
        conf=b.profile(options())
        self.assertFalse(conf['PayloadRemovalDisallowed'])
        payload=conf['PayloadContent'][0]
        self.assertEqual(payload['DNSSettings']['DNSProtocol'],'HTTPS')
        self.assertNotIn('SupplementalMatchDomains',payload['DNSSettings'])
        self.assertFalse(payload['ProhibitDisablement'])
        self.assertEqual(payload['OnDemandRules'],[{'Action':'Connect'}])
        self.assertNotIn('admin_password',str(conf))
