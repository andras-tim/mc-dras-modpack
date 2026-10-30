#!/usr/bin/env python3
"""Build a Prism Launcher instance zip of this pack: Minecraft and Forge from pack.toml, packwiz-installer-bootstrap
inside and set as the pre-launch command, so importing the zip leaves nothing to fill in by hand.

Prism imports it from a file or a URL (Add Instance, Import). The zip holds no secret.
Usage: python3 -I tools/prism-instance.py -o <file.zip> [--url <pack.toml URL>] [--name <instance name>]
       (from the pack root; default URL: the stable tag on GitHub)
"""
import argparse
import hashlib
import json
import sys
import tomllib
import urllib.request
import zipfile

PACK_URL = 'https://raw.githubusercontent.com/andras-tim/mc-dras-modpack/stable/pack.toml'
INSTANCE_NAME = 'mc.dras.hu'
# Same heap as the phone profile, see phone-qr.py
INSTANCE_RAM_MB = 4096

BOOTSTRAP_NAME = 'packwiz-installer-bootstrap.jar'
# https://github.com/packwiz/packwiz-installer-bootstrap/releases
# changelog: in release
BOOTSTRAP_URL = f'https://github.com/packwiz/packwiz-installer-bootstrap/releases/download/v0.0.3/{BOOTSTRAP_NAME}'
BOOTSTRAP_SHA256 = 'a8fbb24dc604278e97f4688e82d3d91a318b98efc08d5dbfcbcbcab6443d116c'


def bootstrap_jar():
    with urllib.request.urlopen(BOOTSTRAP_URL) as r:
        jar = r.read()
    if hashlib.sha256(jar).hexdigest() != BOOTSTRAP_SHA256:
        sys.exit(f'{BOOTSTRAP_URL}: unexpected sha256')
    return jar


def instance_cfg(name, pack_url):
    command = f'"$INST_JAVA" -jar {BOOTSTRAP_NAME} -g {pack_url}'
    # Prism reads this file as QSettings INI: a value with inner quotes must be quoted and escaped
    escaped = command.replace('\\', '\\\\').replace('"', '\\"')
    return '\n'.join([
        '[General]',
        'ConfigVersion=1.2',
        'InstanceType=OneSix',
        f'name={name}',
        'OverrideCommands=true',
        f'PreLaunchCommand="{escaped}"',
        'OverrideMemory=true',
        f'MaxMemAlloc={INSTANCE_RAM_MB}',
        '',
    ])


def mmc_pack(versions):
    return json.dumps({
        'formatVersion': 1,
        'components': [
            {'uid': 'net.minecraft', 'version': versions['minecraft'], 'important': True},
            {'uid': 'net.minecraftforge', 'version': versions['forge']},
        ],
    }, indent=4) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-o', '--output', required=True, help='zip file to write')
    parser.add_argument('--url', default=PACK_URL, help='pack.toml URL the instance follows')
    parser.add_argument('--name', default=INSTANCE_NAME, help=f'instance name (default: {INSTANCE_NAME})')
    args = parser.parse_args()

    with open('pack.toml', 'rb') as f:
        versions = tomllib.load(f)['versions']
    jar = bootstrap_jar()
    with zipfile.ZipFile(args.output, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('instance.cfg', instance_cfg(args.name, args.url))
        z.writestr('mmc-pack.json', mmc_pack(versions))
        z.writestr(f'.minecraft/{BOOTSTRAP_NAME}', jar)
    print(args.output)


if __name__ == '__main__':
    main()
