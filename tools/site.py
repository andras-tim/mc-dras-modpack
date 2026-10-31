#!/usr/bin/env python3
"""Build the setup site: docs/index.html with its links and QR codes, the Prism profile zip and the released pack.

The main branch's CI publishes it on GitHub Pages. Needs `qrencode`.
Usage (from the pack root): python3 -I tools/site.py <output dir>
"""
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tarfile
import tomllib
import urllib.parse

SITE_URL = 'https://mc.dras.hu/'
APK_URL = 'https://github.com/andras-tim/Amethyst-Android/releases/latest/download/amethyst-dras.apk'
PRISM_ZIP = 'mc-dras-hu-prism-profile.zip'


def import_link():
    """The profile link of tools/phone-qr.py, whose file name cannot be imported directly."""
    spec = importlib.util.spec_from_file_location('phone_qr', 'tools/phone-qr.py')
    phone_qr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(phone_qr)
    return phone_qr.import_link('stable')


def qr_svg(text):
    return subprocess.run(['qrencode', '-t', 'SVG', '--inline', '--svg-path', '-l', 'L', '-m', '1', '-o', '-', text],
                          check=True, capture_output=True, text=True).stdout


def publish_pack(output):
    """The files of the `stable` tag under pack/: the launchers get what is released, never main."""
    index = tomllib.loads(subprocess.run(['git', 'show', 'stable:index.toml'], check=True, capture_output=True,
                                         text=True).stdout)
    paths = ['pack.toml', 'index.toml', 'branding/profile-icon.png'] + [item['file'] for item in index['files']]
    archive = subprocess.run(['git', 'archive', 'stable', '--', *paths], check=True, capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(os.path.join(output, 'pack'), filter='data')
    # the launcher's touch layout, not a game file: it goes out with the site, before the next release
    shutil.copy('mc-dras-controls.json', os.path.join(output, 'pack'))


def main():
    output = sys.argv[1]
    os.makedirs(output, exist_ok=True)
    publish_pack(output)
    subprocess.run([sys.executable, '-I', 'tools/prism-profile.py', '-o', os.path.join(output, PRISM_ZIP)], check=True)

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
