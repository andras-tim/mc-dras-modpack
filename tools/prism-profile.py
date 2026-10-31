#!/usr/bin/env python3
"""Build a Prism Launcher profile zip of this pack, so importing it leaves nothing to fill in by hand.

The settings live in prism/: instance.cfg (memory, pre-launch command) and options.txt (the graphics of a new PC
install). This tool adds the Minecraft and Forge versions from pack.toml and packwiz-installer-bootstrap.

Prism imports the zip from a file or a URL (Add Instance, Import). The zip holds no secret.
Usage: python3 -I tools/prism-profile.py -o <file.zip> [--url <pack.toml URL>] [--name <profile name>]
       (from the pack root; default URL: the stable tag on GitHub)
"""
import argparse
import hashlib
import json
import sys
import tomllib
import urllib.request
import zipfile

PACK_URL = 'https://mc.dras.hu/pack/pack.toml'
PROFILE_NAME = 'MC dras.hu'
# Prism installs the file of the instance root named after instance.cfg's iconKey
ICON = 'mc-dras-hu.png'

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
    parser.add_argument('--url', default=PACK_URL, help='pack.toml URL the profile follows')
    parser.add_argument('--name', default=PROFILE_NAME, help=f'profile name (default: {PROFILE_NAME})')
    args = parser.parse_args()

    with open('pack.toml', 'rb') as f:
        versions = tomllib.load(f)['versions']
    with open('prism/instance.cfg') as f:
        instance_cfg = f.read().replace('@NAME@', args.name).replace('@PACK_URL@', args.url)
    jar = bootstrap_jar()
    with zipfile.ZipFile(args.output, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('instance.cfg', instance_cfg)
        z.writestr('mmc-pack.json', mmc_pack(versions))
        z.write('branding/profile-icon.png', ICON)
        z.write('prism/options.txt', '.minecraft/options.txt')
        z.writestr(f'.minecraft/{BOOTSTRAP_NAME}', jar)
    print(args.output)


if __name__ == '__main__':
    main()
