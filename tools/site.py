#!/usr/bin/env python3
"""Build the setup site: docs/index.html with its links and QR codes, and the Prism instance zip next to it.

The main branch's CI publishes it on GitHub Pages. Needs `qrencode`.
Usage (from the pack root): python3 -I tools/site.py <output dir>
"""
import importlib.util
import os
import subprocess
import sys
import urllib.parse

SITE_URL = 'https://andras-tim.github.io/mc-dras-modpack/'
APK_URL = 'https://github.com/andras-tim/Amethyst-Android/releases/latest/download/amethyst-dras.apk'
PRISM_ZIP = 'mc.dras.hu.zip'


def import_link():
    """The profile link of tools/phone-qr.py, whose file name cannot be imported directly."""
    spec = importlib.util.spec_from_file_location('phone_qr', 'tools/phone-qr.py')
    phone_qr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(phone_qr)
    return phone_qr.import_link('stable')


def qr_svg(text):
    return subprocess.run(['qrencode', '-t', 'SVG', '--inline', '--svg-path', '-l', 'L', '-m', '1', '-o', '-', text],
                          check=True, capture_output=True, text=True).stdout


def main():
    output = sys.argv[1]
    os.makedirs(output, exist_ok=True)
    subprocess.run([sys.executable, '-I', 'tools/prism-instance.py', '-o', os.path.join(output, PRISM_ZIP)], check=True)

    profile_link = import_link()
    prism_zip_url = SITE_URL + PRISM_ZIP
    values = {
        'APK_URL': APK_URL,
        'APK_QR': qr_svg(APK_URL),
        'PROFILE_LINK': profile_link.replace('&', '&amp;'),
        'PROFILE_QR': qr_svg(profile_link),
        'PRISM_ZIP_URL': prism_zip_url,
        'PRISM_LINK': 'prismlauncher://import?url=' + urllib.parse.quote(prism_zip_url, safe=''),
    }
    with open('docs/index.html', encoding='utf-8') as f:
        page = f.read()
    for name, value in values.items():
        page = page.replace('@@' + name + '@@', value)
    with open(os.path.join(output, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(page)


if __name__ == '__main__':
    main()
