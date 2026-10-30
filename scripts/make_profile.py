#!/usr/bin/env python3
"""Generate a removable Apple encrypted-DNS profile. Never print its bearer URL."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import uuid

spec=importlib.util.spec_from_file_location('launcher',Path(__file__).resolve().parents[1]/'pihole/launcher.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def profile(o):
    m.validate(o)
    if not o['doh_enabled']: raise ValueError('Enable DoH before creating a profile')
    return dict(PayloadContent=[dict(
        PayloadType='com.apple.dnsSettings.managed',PayloadVersion=1,
        PayloadIdentifier='eu.bitosome.pihole.dns',PayloadUUID=str(uuid.uuid4()),
        PayloadDisplayName='Bitosome Pi-hole DNS',
        DNSSettings=dict(DNSProtocol='HTTPS',ServerURL=f"https://{o['public_hostname']}/doh/{o['doh_token']}/dns-query"),
        OnDemandRules=[dict(Action='Connect')],
        ProhibitDisablement=False)],
        PayloadType='Configuration',PayloadVersion=1,
        PayloadIdentifier='eu.bitosome.pihole',PayloadUUID=str(uuid.uuid4()),
        PayloadDisplayName='Bitosome Pi-hole',PayloadRemovalDisallowed=False,
        PayloadDescription='Filters system DNS using your Pi-hole over HTTPS through Cloudflare. This is not a VPN. Removable in Settings. Contains a private access token: do not share.')

def main():
    p=argparse.ArgumentParser();p.add_argument('options');p.add_argument('output');a=p.parse_args()
    o=json.loads(Path(a.options).read_text())
    fd=os.open(a.output,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'wb') as f:plistlib.dump(profile(o),f)
    os.chmod(a.output,0o600)
    print('Profile created; its secret URL was not printed.')
if __name__=='__main__':main()
