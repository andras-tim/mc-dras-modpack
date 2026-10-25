#!/usr/bin/env python3
"""Show the two QR codes that set up a phone, one after the other (press Enter in between).

1. The Amethyst::Dras APK (latest release): scan with the phone's camera, download, install.
2. The import link of this pack: scan after installing; the launcher adds the mc.dras.hu profile and asks first.

Neither code holds a secret. Needs `qrencode`.
Usage: python3 -I tools/phone-qr.py [--ref <git tag or branch of the pack>]   (default: stable)
"""
import argparse
import shutil
import subprocess
import sys
import urllib.parse

APK_URL = 'https://github.com/andras-tim/Amethyst-Android/releases/latest/download/amethyst-dras.apk'
RAW = 'https://raw.githubusercontent.com/andras-tim/mc-dras-modpack/{ref}/{path}'
PROFILE_NAME = 'mc.dras.hu'
# Java heap of the profile: enough for the pack, safe on the 8 GB phones (tested with 4 GB)
PROFILE_RAM_MB = 4096


def import_link(ref):
    query = urllib.parse.urlencode({
        'url': RAW.format(ref=ref, path='pack.toml'),
        'name': PROFILE_NAME,
        'icon': RAW.format(ref=ref, path='branding/profile-icon.png'),
        'ram': PROFILE_RAM_MB,
    })
    return 'amethyst://profile/import?' + query


def show(title, text):
    print(f'\n{title}\n{text}\n')
    subprocess.run(['qrencode', '-t', 'ANSIUTF8', '-m', '2', text], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--ref', default='stable', help='pack tag or branch the profile follows (default: stable)')
    args = parser.parse_args()
    if not shutil.which('qrencode'):
        sys.exit('qrencode is missing (apt / pkg install qrencode)')

    show('1/2  Scan with the camera, download and install the APK', APK_URL)
    input('Enter for the next code...')
    show('2/2  After installing: scan, open with Amethyst::Dras, confirm "Add"', import_link(args.ref))


if __name__ == '__main__':
    main()
