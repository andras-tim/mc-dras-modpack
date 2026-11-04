#!/usr/bin/env python3
"""Build the setup site: docs/index.html with its links and QR codes, the Prism profile zip and the released pack.

A page template uses the parts under docs/parts/ as `<x-NAME attr="...">` tags, see expand_parts().

The main branch's CI publishes it on GitHub Pages. Needs `qrencode`.
Usage (from the pack root): python3 -I tools/site.py <output dir>
"""
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tomllib
import urllib.parse

SITE_URL = 'https://mc.dras.hu/'
APP_REPO_URL = 'https://github.com/andras-tim/Amethyst-Android'
APK_URL = APP_REPO_URL + '/releases/latest/download/amethyst-dras.apk'
# the release signing key's certificate: Obtainium refuses an update signed by anything else
APK_CERT_SHA256 = '296EB0B2F9FD3EEA8D2607F0C0B95DA8210E7540E50008861C3D3AA4DE46D764'
# the F-Droid flavour for arm64 (33 MB instead of 89 for every CPU): the launcher runs on arm64 only anyway
OBTAINIUM_APK_URL = 'https://github.com/ImranR98/Obtainium/releases/latest/download/app-arm64-v8a-fdroid-release.apk'
PRISM_ZIP = 'mc-dras-hu-prism-profile.zip'


def obtainium_link():
    """An obtainium://app/ link that adds the launcher with its settings; unset settings get Obtainium's defaults.

    Only the fields Obtainium requires, the source comes from the URL. The release tag is the APK's versionName, so
    Obtainium's version detection works as is. `:/,` stay unquoted for a shorter link and QR code.
    """
    app = {
        'id': 'hu.dras.amethyst',
        'url': APP_REPO_URL,
        'author': 'andras-tim',
        'name': 'Amethyst::Dras',
        'additionalSettings': json.dumps({
            # every release has the APK twice, under its versioned and its fixed name
            'apkFilterRegEx': r'^amethyst-dras\.apk$',
            'allowedSigningCertHashes': APK_CERT_SHA256,
        }, separators=(',', ':')),
    }
    return 'obtainium://app/' + urllib.parse.quote(json.dumps(app, separators=(',', ':')), safe=':/,')


PART = re.compile(r'<x-([a-z-]+)((?:\s+[a-z-]+="[^"]*")*)\s*></x-\1>')
PART_TAG = re.compile(r'<x-[^>]*>')
PART_ATTR = re.compile(r'([a-z-]+)="([^"]*)"')
PART_VALUE = re.compile(r'@@(\??)([a-z-]+)@@')


def expand_parts(page):
    """Replace each `<x-NAME attr="value"></x-NAME>` with docs/parts/NAME.html, its `@@attr@@` filled in.

    A line with an empty or unset `@@attr@@` is left out, so one part covers e.g. a step with and without a QR code.
    `@@?attr@@` prints nothing, it only keeps its line on a set attribute. A part's line holding another part's tag is
    kept with empty values (that part drops its own lines), unless a `@@?attr@@` of it is empty. The page's own
    `@@NAME@@` values are filled in after this.
    """
    def expand(match):
        attrs = dict(PART_ATTR.findall(match.group(2)))
        with open(os.path.join('docs', 'parts', match.group(1) + '.html'), encoding='utf-8') as f:
            # a tag over several lines is one line here
            text = PART_TAG.sub(lambda m: re.sub(r'\s*\n\s*', ' ', m.group(0)), f.read())
        lines = []
        for line in text.rstrip('\n').split('\n'):
            needed = [name for required, name in PART_VALUE.findall(line)
                      if required or not line.lstrip().startswith('<x-')]
            if not all(attrs.get(name) for name in needed):
                continue
            lines.append(PART_VALUE.sub(lambda m: '' if m.group(1) else attrs.get(m.group(2), ''), line))
        # the part's lines keep the tag's indentation
        indent = ' ' * (match.start() - match.string.rfind('\n', 0, match.start()) - 1)
        return ('\n' + indent).join(lines)

    while True:
        page, count = PART.subn(expand, page)
        if not count:
            return page


def phone_qr():
    """tools/phone-qr.py, whose file name cannot be imported directly: the profile link and its values."""
    spec = importlib.util.spec_from_file_location('phone_qr', 'tools/phone-qr.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def qr_svg(text):
    return subprocess.run(['qrencode', '-t', 'SVG', '--inline', '--svg-path', '-l', 'L', '-m', '1', '-o', '-', text],
                          check=True, capture_output=True, text=True).stdout


def publish_pack(output):
    """The files of the `stable` tag under pack/: the launchers get what is released, never main."""
    index = tomllib.loads(subprocess.run(['git', 'show', 'stable:index.toml'], check=True, capture_output=True,
                                         text=True).stdout)
    paths = ['pack.toml', 'index.toml'] + [item['file'] for item in index['files']]
    archive = subprocess.run(['git', 'archive', 'stable', '--', *paths], check=True, capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(os.path.join(output, 'pack'), filter='data')
    # the launcher's touch layout and the profile icon are not game files: they go out with the site, before a release
    shutil.copy('mc-dras-controls.json', os.path.join(output, 'pack'))
    os.makedirs(os.path.join(output, 'pack', 'branding'), exist_ok=True)
    shutil.copy('branding/profile-icon.png', os.path.join(output, 'pack', 'branding'))


def main():
    output = sys.argv[1]
    os.makedirs(output, exist_ok=True)
    publish_pack(output)
    shutil.copytree('docs/icons', os.path.join(output, 'icons'), dirs_exist_ok=True)
    subprocess.run([sys.executable, '-I', 'tools/prism-profile.py', '-o', os.path.join(output, PRISM_ZIP)], check=True)

    profile = phone_qr()
    profile_link = profile.import_link('stable')
    prism_zip_url = SITE_URL + PRISM_ZIP
    values = {
        # a launcher's name in the text, with its icon
        'AMETHYST': '<b class="app"><img src="icons/amethyst-dras.webp" alt="">Amethyst::Dras</b>',
        'PRISM': '<b class="app"><img src="icons/prism-launcher.svg" alt="">Prism Launcher</b>',
        'APK_URL': APK_URL,
        'APK_QR': qr_svg(APK_URL),
        'APP_REPO_URL': APP_REPO_URL,
        'OBTAINIUM_APK_URL': OBTAINIUM_APK_URL,
        'OBTAINIUM_APK_QR': qr_svg(OBTAINIUM_APK_URL),
        'OBTAINIUM_LINK': obtainium_link(),
        'OBTAINIUM_QR': qr_svg(obtainium_link()),
        'PROFILE_LINK': profile_link.replace('&', '&amp;'),
        'PROFILE_QR': qr_svg(profile_link),
        # the values a profile set up by hand needs, the same as in the link
        'PROFILE_PACK_URL': profile.RELEASED + 'pack.toml',
        'PROFILE_RAM_MB': str(profile.PROFILE_RAM_MB),
        'PRISM_ZIP_URL': prism_zip_url,
        'PRISM_LINK': 'prismlauncher://import?url=' + urllib.parse.quote(prism_zip_url, safe=''),
    }
    with open('docs/index.html', encoding='utf-8') as f:
        page = expand_parts(f.read())
    for name, value in values.items():
        page = page.replace('@@' + name + '@@', value)
    with open(os.path.join(output, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(page)


if __name__ == '__main__':
    main()
