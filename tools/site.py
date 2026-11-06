#!/usr/bin/env python3
"""Build the site: docs/install.html with its links and QR codes, the mods and controls pages, the Prism profile zip
and the released pack.

A page template uses the parts under docs/parts/ as `<x-NAME attr="...">` tags, see expand_parts().

The mods and controls pages come from docs/mods.toml and docs/controls.toml, with the mod icons in one image.

CI publishes it on GitHub Pages when a release is published. Needs `qrencode`, Pillow and the network (the icons).
Usage (from the pack root): python3 -I tools/site.py <output dir> <release tag of the pack>
"""
import datetime
import html
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
import urllib.request
import zoneinfo

SITE_URL = 'https://mc.dras.hu/'
APP_REPO_URL = 'https://github.com/andras-tim/Amethyst-Android'
# the page of the latest release: its APK is named with its version, so no download link stays valid across releases
APP_RELEASE_URL = APP_REPO_URL + '/releases/latest'
# the release signing key's certificate: Obtainium refuses an update signed by anything else
APK_CERT_SHA256 = '296EB0B2F9FD3EEA8D2607F0C0B95DA8210E7540E50008861C3D3AA4DE46D764'
# the F-Droid flavour for arm64 (33 MB instead of 89 for every CPU): the launcher runs on arm64 only anyway
OBTAINIUM_APK_URL = 'https://github.com/ImranR98/Obtainium/releases/latest/download/app-arm64-v8a-fdroid-release.apk'
PRISM_ZIP = 'mc-dras-hu-prism-profile.zip'
PACK_REPO_URL = 'https://github.com/andras-tim/mc-dras-modpack'
# the header's version links
MINECRAFT_URL = 'https://minecraft.wiki/w/Java_Edition_{}'
FORGE_URL = 'https://files.minecraftforge.net/net/minecraftforge/forge/index_{}.html'
# an anvil for Forge, in the 24 px grid of Material Symbols (they have none)
SVG_ANVIL = ('<svg class="vi" viewBox="0 0 24 24" aria-hidden="true"><path d="M2.5 6.5h18.5v2.8h-3.4c-.7 1.7-2.1 2.9-3.9 '
             '3.3v2h2.4v2.6H7.7v-2.6h2.4v-2c-2.4-.5-4.1-1.9-4.8-3.6-1.2-.2-2.2-1.1-2.8-2.5zM6 19h12.5v2.5H6z"/></svg>')


def obtainium_link():
    """An obtainium://app/ link that adds the launcher with its settings; unset settings get Obtainium's defaults.

    Only the fields Obtainium requires, the source comes from the URL. The release tag is the APK's versionName (since
    1.1.7-dras.12), so Obtainium's version detection works as is. `:/,` stay unquoted for a shorter link and QR code.
    """
    app = {
        'id': 'hu.dras.amethyst',
        'url': APP_REPO_URL,
        'author': 'andras-tim',
        'name': 'Amethyst::Dras',
        'additionalSettings': json.dumps({
            # amethyst-dras-1.1.7-dras.13.apk; up to 1.1.7-dras.12 the release named it amethyst-dras.apk
            'apkFilterRegEx': r'^amethyst-dras(-[0-9].*)?\.apk$',
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


def publish_pack(output, tag):
    """The files of the release tag under pack/: the launchers get what is released, never main."""
    index = tomllib.loads(subprocess.run(['git', 'show', f'{tag}:index.toml'], check=True, capture_output=True,
                                         text=True).stdout)
    paths = ['pack.toml', 'index.toml'] + [item['file'] for item in index['files']]
    archive = subprocess.run(['git', 'archive', tag, '--', *paths], check=True, capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(os.path.join(output, 'pack'), filter='data')
    # the launcher's touch layout and the profile icon are not game files: they come with the site's commit, so a
    # manual run from main publishes them before a release
    shutil.copy('mc-dras-controls.json', os.path.join(output, 'pack'))
    os.makedirs(os.path.join(output, 'pack', 'branding'), exist_ok=True)
    shutil.copy('branding/profile-icon.png', os.path.join(output, 'pack', 'branding'))


MODS_TOML = 'docs/mods.toml'
CONTROLS_TOML = 'docs/controls.toml'
SPRITE = 'icons/mods.webp'
SPRITE_CELL = 64
SPRITE_COLUMNS = 8
# a Minecraft version in a jar's name, not the mod's: 1.16 - 1.21, also as mc1.20.1
MC_VERSION = re.compile(r'(mc)?1\.(1[6-9]|2[01])(\.\d+)?')
# the touch buttons' icons, inlined at build time: no font from a third party at runtime
MATERIAL_SVG = ('https://raw.githubusercontent.com/google/material-design-icons/10ecc14790612ca8fd164e3f4ffe9c16fc50d5b7/'
                'symbols/web/{0}/materialsymbolsoutlined/{0}_24px.svg')
USER_AGENT = 'mc.dras.hu site build (github.com/andras-tim/mc-dras-modpack)'
MENU = [
    ('install/', 'Telepítés', '<path d="M12 3.5v11M7.5 10l4.5 4.5 4.5-4.5M4 19.5h16"/>'),
    ('contents/', 'Tartalom', '<path d="M12 2.5 3.5 7v10l8.5 4.5 8.5-4.5V7z"/>'
                              '<path d="M3.5 7l8.5 4.5L20.5 7M12 11.5v10"/>'),
    ('control/', 'Irányítás', '<path d="M7.2 7.5h9.6a4.2 4.2 0 0 1 4.1 4.9l-.7 4a2.3 2.3 0 0 1-4 1l-1.7-2.1H9.5l-1.7 '
                                '2.1a2.3 2.3 0 0 1-4-1l-.7-4a4.2 4.2 0 0 1 4.1-4.9z"/><path d="M8 10.5v3M6.5 12h3M15.5 '
                                '11h.01M17.5 13h.01"/>'),
]
SVG_EXT = ('<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 '
           '1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/></svg>')
# an open book: the documentation of a mod
SVG_BOOK = ('<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M2 5h6a4 4 0 0 1 4 4v11a3 3 0 0 0-3-3H2z"/>'
            '<path d="M22 5h-6a4 4 0 0 0-4 4v11a3 3 0 0 1 3-3h7z"/></svg>')
SVG_DOWN = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M6 13l6 6 6-6"/></svg>'
SVG_KEYBOARD = ('<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><rect x="2.5" y="6" width="19" height="12" '
                'rx="2.5"/><path d="M6.5 10h1M10.5 10h1M14.5 10h1M17.5 10h.5M8 14h8"/></svg>')
# a button drawn as on the controller: a D-pad direction as a bold arrow (the characters are hard to read at this
# size), View and Menu with their symbols
PAD_SYMBOLS = {'View': '<rect x="4" y="9" width="10" height="9" rx="1.5"/><path d="M8.5 9V6.5A1.5 1.5 0 0 1 10 5h8.5A1.5 '
                       '1.5 0 0 1 20 6.5v6.5a1.5 1.5 0 0 1-1.5 1.5H14"/>',
               'Menu': '<path d="M5 7h14M5 12h14M5 17h14"/>'}
# a gamepad row's address, the drawing on the controls page links to it
PAD_IDS = {'Bal kar': 'ls', 'Jobb kar': 'rs', '←': 'left', '→': 'right', '↑': 'up', '↓': 'down'}
PAD_ARROWS = {'←': 'M19 12H6M11 6l-6 6 6 6', '→': 'M5 12h13M13 6l6 6-6 6', '↑': 'M12 19V6M6 11l6-6 6 6',
              '↓': 'M12 5v13M6 13l6 6 6-6'}
SVG_GAMEPAD = ('<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M7.2 7.5h9.6a4.2 4.2 0 0 1 4.1 4.9l-.7 '
               '4a2.3 2.3 0 0 1-4 1l-1.7-2.1H9.5l-1.7 2.1a2.3 2.3 0 0 1-4-1l-.7-4a4.2 4.2 0 0 1 4.1-4.9z"/><path d="M8 '
               '10.5v3M6.5 12h3M15.5 11h.01M17.5 13h.01"/></svg>')
SVG_CHEVRON = '<svg class="ico chev" viewBox="0 0 24 24" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>'


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': USER_AGENT}), timeout=30) as r:
        return r.read()


def masthead(pack, tag):
    """The header of every page as a function of the page's place: the site's name, the versions of Minecraft, Forge
    and the pack (each a link, the pack's to its release), and the menu in a bar that stays on top (see site.js)."""
    cube = material_icon('deployed_code').replace('<svg ', '<svg class="vi" ', 1)
    cube_path = re.search(r'<path d="([^"]+)"', cube).group(1)
    # three cubes, two below and one on top, for the pack of mods
    cubes = ('<svg class="vi" viewBox="0 -960 960 960" aria-hidden="true">'
             + ''.join(f'<path transform="translate({x} {y}) scale(.5)" d="{cube_path}"/>'
                       for x, y in ((240, -480), (0, 0), (480, 0))) + '</svg>')
    mc, forge = pack['versions']['minecraft'], pack['versions']['forge']
    parts = [('Minecraft', mc, MINECRAFT_URL.format(mc), cube),
             ('Forge', forge, FORGE_URL.format(mc), SVG_ANVIL),
             ('Modcsomag', pack['version'], f'{PACK_REPO_URL}/releases/tag/{tag}', cubes)]
    links = ''.join(f'<a href="{esc(url)}" target="_blank" rel="noopener" title="{name} {esc(version)}" '
                    f'aria-label="{name} {esc(version)}">{icon}<kbd>{esc(version)}</kbd></a>'
                    for name, version, url, icon in parts)

    def page(current, root):
        icon = f'{root}pack/branding/profile-icon.png'
        return (f'<header class="top"><img src="{icon}" alt=""><div class="tt"><h1>MC dras.hu</h1>'
                f'<p>Családi Minecraft-szerver</p></div><div class="vcol" aria-label="Verziók">{links}</div></header>\n'
                f'  <div class="sbar"><img src="{icon}" alt="">{menu(current, root)}</div>')
    return page


def updated():
    """The time of the build: the site's last version."""
    now = datetime.datetime.now(zoneinfo.ZoneInfo('Europe/Budapest')).replace(microsecond=0)
    return f'Frissítve: <time datetime="{now.isoformat()}">{now.strftime("%Y-%m-%d %H:%M:%S")}</time>'


def menu(current, root):
    """The menu of the pages; root leads from the page to the site's root."""
    links = []
    for path, title, icon in MENU:
        mark = ' aria-current="page"' if path == current else ''
        links.append(f'<a href="{root}{path or "./"}"{mark}><svg viewBox="0 0 24 24" aria-hidden="true">{icon}</svg>'
                     f'{title}</a>')
    return '<nav class="menu" aria-label="Menü">' + ''.join(links) + '</nav>'


def mod_version(filename):
    """The mod's version from its jar's name: the first number that is not a Minecraft version."""
    for token in re.split(r'[-_+]', filename.removesuffix('.jar')):
        token = token.removeprefix('v')
        if re.fullmatch(r'\d[\w.]*', token) and not MC_VERSION.fullmatch(token):
            return token
    sys.exit(f'{filename}: no version in the name, set one in {MODS_TOML}')


def load_mods(output):
    """The mods of the released pack with their entries of docs/mods.toml, and the page's layout of them.

    The build fails on a released mod without an entry, a reference to an unknown mod and a released mod the page
    does not show anywhere. A reference to a mod of the file that the release lacks is dropped.
    """
    with open(MODS_TOML, 'rb') as f:
        info = tomllib.load(f)
    released = {}
    mods_dir = os.path.join(output, 'pack', 'mods')
    for name in sorted(os.listdir(mods_dir)):
        with open(os.path.join(mods_dir, name), 'rb') as f:
            released[name.removesuffix('.pw.toml')] = tomllib.load(f)
    missing = sorted(set(released) - set(info['mods']))
    if missing:
        sys.exit(f'{MODS_TOML}: no entry for ' + ', '.join(missing))
    references = [*(key for a in info['activity'] for key in a['mods']),
                  *(key for p in info['background']['part'] for key in p['mods']),
                  *(key for m in info['mods'].values() for key in m.get('addons', []) + m.get('deps', []))]
    unknown = sorted(set(references) - set(info['mods']))
    if unknown:
        sys.exit(f'{MODS_TOML}: unknown mods: ' + ', '.join(unknown))
    hidden = sorted(set(released) - set(references))
    if hidden:
        sys.exit(f'{MODS_TOML}: not shown anywhere: ' + ', '.join(hidden))

    mods = {}
    for key, pw in released.items():
        entry = info['mods'][key]
        mods[key] = {
            'key': key, 'name': entry.get('name', pw['name']),
            'version': entry.get('version') or mod_version(pw['filename']),
            'desc': entry['desc'], 'url': entry['url'], 'docs': entry.get('docs'), 'icon': entry['icon'],
            'keys': entry.get('keys', []),
            'panel': entry.get('panel'),
            'addons': [k for k in entry.get('addons', []) if k in released],
            'deps': [k for k in entry.get('deps', []) if k in released],
        }
    activities = [{**a, 'mods': [k for k in a['mods'] if k in released]} for a in info['activity']]
    background = {**info['background'],
                  'part': [{**p, 'mods': [k for k in p['mods'] if k in released]} for p in info['background']['part']]}
    return mods, [a for a in activities if a['mods']], background


def trimmed(data, size):
    """An icon without its transparent margin, centered on a square, at size x size."""
    from PIL import Image  # only the site build needs Pillow
    image = Image.open(io.BytesIO(data)).convert('RGBA')
    box = image.getchannel('A').point(lambda a: 255 if a > 24 else 0).getbbox() or (0, 0, *image.size)
    image = image.crop(box)
    side = max(image.size)
    square = Image.new('RGBA', (side, side))
    square.paste(image, ((side - image.width) // 2, (side - image.height) // 2))
    return square.resize((size, size), Image.LANCZOS)


def build_sprite(mods, output):
    """icons/mods.webp: every mod's icon in one image, 64 px cells; returns the CSS of a cell per mod key.

    The site crops a cell with background-position in percents, so one image serves every displayed size.
    """
    from PIL import Image
    keys = sorted(mods)
    rows = -(-len(keys) // SPRITE_COLUMNS)
    sheet = Image.new('RGBA', (SPRITE_COLUMNS * SPRITE_CELL, rows * SPRITE_CELL))
    cells = {}
    for i, key in enumerate(keys):
        column, row = i % SPRITE_COLUMNS, i // SPRITE_COLUMNS
        try:
            sheet.paste(trimmed(fetch(mods[key]['icon']), SPRITE_CELL), (column * SPRITE_CELL, row * SPRITE_CELL))
        except Exception as error:
            sys.exit(f'{key}: icon {mods[key]["icon"]}: {error}')
        x = column * 100 / (SPRITE_COLUMNS - 1)
        y = row * 100 / (rows - 1) if rows > 1 else 0
        cells[key] = f'background-position:{x:.3f}% {y:.3f}%'
    sheet.save(os.path.join(output, SPRITE), 'WEBP', quality=90, method=6)
    css = (f'.ic {{ background-image: url(../{SPRITE}); '
           f'background-size: {SPRITE_COLUMNS * 100}% {rows * 100}%; }}')
    return cells, css


def esc(text):
    return html.escape(text, quote=True)


def key_caps(keys):
    """`2×S` is S pressed twice: the count stays outside the key."""
    caps = []
    for key in keys:
        count, cap = re.fullmatch(r'(\d+×)?(.+)', key).groups()
        caps.append(f'<span class="kk">{count or ""}<kbd>{esc(cap)}</kbd></span>')
    return ''.join(caps)


def mods_page(mods, activities, background, cells, controls):
    """The cards of docs/contents.html."""
    icon = lambda key, extra='': f'<i class="ic{extra}" style="{cells[key]}"></i>'
    ext = lambda m: (f'<a class="ext" href="{esc(m["url"])}" target="_blank" rel="noopener" '
                     f'aria-label="{esc(m["name"])} oldala">{SVG_EXT}</a>'
                     + (f'<a class="ext" href="{esc(m["docs"])}" target="_blank" rel="noopener" '
                        f'aria-label="{esc(m["name"])} leírása">{SVG_BOOK}</a>' if m['docs'] else ''))
    meta = lambda m: f'<span class="nm">{esc(m["name"])}</span><span class="ver">{esc(m["version"])}</span>' + ext(m)
    key_rows = {row['id']: row for row in controls['keyboard']['mods']}
    on_page = {k for a in activities for k in a['mods']} | {k for a in activities for m in a['mods']
                                                             for k in mods[m]['addons']}

    def small_row(m, tag='li'):
        return (f'<{tag} id="{m["key"]}">{icon(m["key"])}<div><div class="meta">{meta(m)}</div>'
                f'<p class="ds">{esc(m["desc"])}</p></div></{tag}>')

    out = []
    for activity in activities:
        out.append('  <section class="act">')
        out.append('    <div class="hero"><div class="amb" aria-hidden="true">'
                   + ''.join(icon(k) for k in activity['mods'][:3]) + '</div>'
                   f'<div><h2>{esc(activity["title"])}</h2><p>{esc(activity["text"])}</p></div></div>')
        out.append('    <ul class="ml">')
        for key in activity['mods']:
            m = mods[key]
            keys = ''
            if m['keys']:
                caps = key_caps([k for row in m['keys'] for k in key_rows[row]['keys']])
                keys = (f'<span class="sp" aria-hidden="true"></span><a class="keys" href="../control/#{key}" '
                        f'aria-label="{esc(m["name"])} billentyűi">{SVG_KEYBOARD}{caps}</a>')
            if m['panel']:
                keys += (f'<span class="sp" aria-hidden="true"></span><a class="keys" href="../control/#{m["panel"]}" '
                         f'aria-label="A kontroller kiosztása">{SVG_GAMEPAD}</a>')
            row_class = ' has' if m['addons'] else ''
            out.append(f'      <li id="{key}"><div class="row{row_class}">{icon(key)}<div class="tx">'
                       f'<div class="meta">{meta(m)}{keys}</div><p class="ds">{esc(m["desc"])}</p></div></div>')
            if m['addons']:
                out.append('        <ul class="tree">' + ''.join(small_row(mods[a]) for a in m['addons']) + '</ul>')
            if m['deps']:
                deps = sorted(m['deps'], key=lambda d: d not in on_page)
                rows = []
                for d in deps:
                    dm = mods[d]
                    link = (f'<a class="ext" href="#{d}" aria-label="Ugrás: {esc(dm["name"])}">{SVG_DOWN}</a>'
                            if d in on_page else ext(dm))
                    rows.append(f'<li>{icon(d)}<div><div class="meta"><span class="nm">{esc(dm["name"])}</span>'
                                f'<span class="ver">{esc(dm["version"])}</span>{link}</div>'
                                f'<p class="ds">{esc(dm["desc"])}</p></div></li>')
                out.append('        <details class="ft"><summary><span class="lb">Függőségek</span><span class="stack">'
                           + ''.join(icon(d) for d in deps) + '</span></summary><ul class="r2">' + ''.join(rows)
                           + '</ul></details>')
            out.append('      </li>')
        out.append('    </ul>')
        out.append('  </section>')

    # the background: each mod, then the mods it needs
    parts = []
    count = 0
    for part in background['part']:
        keys = [k for key in part['mods'] for k in [key, *mods[key]['deps']]]
        count += len(keys)
        parts.append(f'<p class="pt">{esc(part["title"])}</p><ul class="sub">'
                     + ''.join(small_row(mods[k]) for k in keys) + '</ul>')
    first = [k for p in background['part'] for k in p['mods']][:4]
    out.append('  <details class="bgc"><summary><span class="stack">' + ''.join(icon(k) for k in first) + '</span>'
               f'<span><span class="st">És még {count} mod {esc(background["title"].lower())}</span>'
               f'<span class="ss">{esc(background["text"])}</span></span>{SVG_CHEVRON}</summary>'
               '<div class="bgp">' + ''.join(parts) + '</div></details>')
    return '\n'.join(out)


def material_icon(name):
    svg = fetch(MATERIAL_SVG.format(name)).decode()
    return re.sub(r'\s(height|width)="\d+"', '', svg).replace('<svg ', '<svg aria-hidden="true" ', 1)


def controls_page(mods, cells, controls):
    """The panels of docs/control.html: keyboard, gamepad and touch."""
    icon = lambda key: f'<i class="ic" style="{cells[key]}"></i>'
    backdrop = lambda keys: ''.join(icon(k) for k in keys if k in cells)
    profile_icon = '<img src="../pack/branding/profile-icon.png" alt="">'

    def mod_link(key):
        name = esc(mods[key]['name'])
        return f'<a class="m" href="../contents/#{key}" aria-label="{name} a Tartalom oldalon">{icon(key)}</a>'

    def card(title, text, amb, rows, list_class='kl'):
        return ('  <section class="act">\n'
                f'    <div class="hero"><div class="amb" aria-hidden="true">{amb}</div>'
                f'<div><h2>{title}</h2><p>{text}</p></div></div>\n'
                f'    <ul class="{list_class}">\n' + '\n'.join('      ' + r for r in rows) + '\n    </ul>\n  </section>')

    where = lambda *parts: '<span class="w">' + ' · '.join(esc(p) for p in parts if p) + '</span>' if any(parts) else ''
    keyboard = controls['keyboard']
    mod_rows = []
    for row in keyboard['mods']:
        if row['mod'] not in mods:
            continue
        mod_rows.append(f'<li id="{row["id"]}" data-mod="{row["mod"]}"><span class="k">{key_caps(row["keys"])}</span>'
                        f'<span class="a">{esc(row["action"])}{where(mods[row["mod"]]["name"], row.get("where"))}'
                        f'</span>{mod_link(row["mod"])}</li>')
    base_rows = [f'<li id="{row["id"]}"><span class="k">{key_caps(row["keys"])}</span>'
                 f'<span class="a">{esc(row["action"])}{where(row.get("where"))}</span><span></span></li>'
                 for row in keyboard['base']]
    with_keys = list(dict.fromkeys(row['mod'] for row in keyboard['mods'] if row['mod'] in mods))
    keyboard_html = '\n'.join([
        card('A modok billentyűi', 'Csak a modokban működnek. Az ikon a mod sorára visz a Tartalom oldalon.',
             backdrop(with_keys[:3]), mod_rows),
        f'  <p class="note">{keyboard["note"]}</p>',
        card('Alap Minecraft', 'A játék saját billentyűi, mod nélkül is így működnek.', profile_icon, base_rows),
    ])

    gamepad = []
    for group in controls['gamepad']:
        gamepad.append(f'  <p class="pt">{esc(group["title"])}</p>\n  <ul class="kl">')
        for row in group['rows']:
            shape = ' sq' if len(row['button']) > 2 else ''
            link = mod_link(row['mod']) if row.get('mod') in mods else '<span></span>'
            button = esc(row['button'])
            symbol = PAD_SYMBOLS.get(row['button']) or (f'<path d="{PAD_ARROWS[row["button"]]}"/>'
                                                         if row['button'] in PAD_ARROWS else '')
            if symbol:
                shape = ''
                button = f'<svg class="arrow" viewBox="0 0 24 24" role="img" aria-label="{button}">{symbol}</svg>'
            # only the in-game rows have an address: the drawing links those
            row_id = '' if group.get('screen') else ' id="pad-%s"' % PAD_IDS.get(row['button'], row['button'].lower())
            gamepad.append(f'    <li{row_id}><span class="k"><span class="pb{shape}">{button}</span></span>'
                           f'<span class="a">{esc(row["action"])}{where(row.get("where"))}</span>{link}</li>')
        gamepad.append('  </ul>')

    def long_press(row):
        return f'<span class="w"><b>Hosszan:</b> {esc(row["long"])}</span>' if row.get('long') else ''

    # a touch button as the launcher's editor shows it; the text of the page names one by @@TB:<label>@@
    buttons = {}
    touch = []
    for group in controls['touch']:
        touch.append(f'  <p class="pt">{esc(group["title"])}</p>\n  <ul class="kl touch">')
        for row in group['rows']:
            button = f'<span class="tb">{material_icon(row["icon"])}{esc(row.get("label", ""))}</span>'
            if row.get('label'):
                buttons.setdefault(row['label'], button)
            touch.append(f'    <li><span class="k">{button}</span><span class="a">{esc(row["action"])}'
                         f'{where(row.get("where"))}{long_press(row)}</span></li>')
        touch.append('  </ul>')
    touch_html = ('  <section class="act">\n    <div class="hero"><div class="amb" aria-hidden="true">'
                  f'{profile_icon}</div><div><h2>Érintéses gombok</h2><p>Az Amethyst::Dras gombjai a képernyőn. '
                  'A View vált a mindennapi gombok és az összes között.</p></div></div>\n'
                  + '\n'.join(touch) + '\n  </section>')
    return keyboard_html, '\n'.join(gamepad), backdrop(['controllable-dras']), touch_html, buttons


def build_pages(output, header, footer):
    """contents/ and control/: the mods of the released pack and the controls of a new install."""
    mods, activities, background = load_mods(output)
    with open(CONTROLS_TOML, 'rb') as f:
        controls = tomllib.load(f)
    unknown = sorted({k for m in mods.values() for k in m['keys']} - {r['id'] for r in controls['keyboard']['mods']})
    if unknown:
        sys.exit(f'{MODS_TOML}: keys without a row in {CONTROLS_TOML}: ' + ', '.join(unknown))
    cells, sprite_css = build_sprite(mods, output)
    common = {'UPDATED': footer, 'MOD_COUNT': str(len(mods)), 'SPRITE_CSS': sprite_css}
    keyboard, gamepad, gamepad_backdrop, touch, buttons = controls_page(mods, cells, controls)
    pages = {
        'contents': {**common, 'HEADER': header('contents/', '../'),
                     'MODS': mods_page(mods, activities, background, cells, controls)},
        'control': {**common, 'HEADER': header('control/', '../'), 'KEYBOARD': keyboard, 'GAMEPAD': gamepad,
                    'GAMEPAD_BACKDROP': gamepad_backdrop, 'TOUCH': touch},
    }
    for name, values in pages.items():
        with open(os.path.join('docs', name + '.html'), encoding='utf-8') as f:
            page = f.read()
        for key, value in values.items():
            page = page.replace('@@' + key + '@@', value)
        unknown = sorted(set(re.findall(r'@@TB:([^@]+)@@', page)) - set(buttons))
        if unknown:
            sys.exit(f'docs/{name}.html: no touch button labelled ' + ', '.join(unknown))
        page = re.sub(r'@@TB:([^@]+)@@', lambda m: buttons[m.group(1)].replace('class="tb"', 'class="tb in"'), page)
        os.makedirs(os.path.join(output, name), exist_ok=True)
        with open(os.path.join(output, name, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(page)


def main():
    output, tag = sys.argv[1:3]
    os.makedirs(output, exist_ok=True)
    publish_pack(output, tag)
    shutil.copytree('docs/icons', os.path.join(output, 'icons'), dirs_exist_ok=True)
    for name in ('site.css', 'cards.css', 'site.js'):
        shutil.copy(os.path.join('docs', name), output)
    with open(os.path.join(output, 'pack', 'pack.toml'), 'rb') as f:
        header = masthead(tomllib.load(f), tag)
    footer = updated()
    build_pages(output, header, footer)
    subprocess.run([sys.executable, '-I', 'tools/prism-profile.py', '-o', os.path.join(output, PRISM_ZIP)], check=True)

    profile = phone_qr()
    profile_link = profile.import_link()
    prism_zip_url = SITE_URL + PRISM_ZIP
    values = {
        # a launcher's name in the text, with its icon
        'AMETHYST': '<b class="app"><img src="../icons/amethyst-dras.webp" alt="">Amethyst::Dras</b>',
        'PRISM': '<b class="app"><img src="../icons/prism-launcher.svg" alt="">Prism Launcher</b>',
        'APP_RELEASE_URL': APP_RELEASE_URL,
        'APP_RELEASE_QR': qr_svg(APP_RELEASE_URL),
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
        'HEADER': header('install/', '../'),
        'UPDATED': footer,
    }
    with open('docs/install.html', encoding='utf-8') as f:
        page = expand_parts(f.read())
    for name, value in values.items():
        page = page.replace('@@' + name + '@@', value)
    os.makedirs(os.path.join(output, 'install'), exist_ok=True)
    with open(os.path.join(output, 'install', 'index.html'), 'w', encoding='utf-8') as f:
        f.write(page)
    redirects(output)


# the addresses before 2026-11-06, which links and bookmarks may still hold, and the site's root
REDIRECTS = {'': 'install/', 'modok/': '../contents/', 'iranyitas/': '../control/'}


def redirects(output):
    """A page per old address that forwards to its new place, with the part after # (a route or a row)."""
    for old, new in REDIRECTS.items():
        os.makedirs(os.path.join(output, old), exist_ok=True)
        with open(os.path.join(output, old, 'index.html'), 'w', encoding='utf-8') as f:
            f.write('<!doctype html>\n<html lang="hu">\n<head>\n<meta charset="utf-8">\n<title>MC dras.hu</title>\n'
                    f'<meta http-equiv="refresh" content="0; url={new}">\n'
                    f'<script>location.replace({json.dumps(new)} + location.hash)</script>\n'
                    f'</head>\n<body><a href="{new}">MC dras.hu</a></body>\n</html>\n')


if __name__ == '__main__':
    main()
