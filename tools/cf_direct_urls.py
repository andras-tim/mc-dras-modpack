#!/usr/bin/env python3
"""Give CurseForge files in the pack a direct download URL.

packwiz writes `mode = "metadata:curseforge"` for every CurseForge file: the client then needs the CurseForge API to
find the download. This pack's clients (the Amethyst::Dras launcher, packwiz-installer in Prism and on the server)
should only fetch plain URLs, so every such metafile is rewritten to the file's CDN URL, after checking that the
author allows third-party downloads and that the CDN file has the hash packwiz recorded. A file whose author forbids
it stops the run: such a file must be hosted by us instead.

Usage (from the pack root):
    python3 -I tools/cf_direct_urls.py          rewrite, then run `packwiz refresh`
    python3 -I tools/cf_direct_urls.py --check  fail if a metafile still uses the CurseForge API
"""
import hashlib
import re
import sys
import time
import tomllib
import urllib.parse
import urllib.request
from pathlib import Path

USER_AGENT = 'mc-dras-modpack tools (https://github.com/andras-tim/mc-dras-modpack)'
CDN = 'https://mediafilez.forgecdn.net/files/{head}/{tail}/{name}'
# CFLookup shows the API's allowModDistribution flag, which the public CurseForge website API does not expose
DISTRIBUTION_PAGE = 'https://cflookup.com/{project}'
DISTRIBUTION_ROW = re.compile(r'Mod Distribution</b></td>\s*<td[^>]*>([^<]+)<', re.S)
API_MODE = 'mode = "metadata:curseforge"'


def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': USER_AGENT}), timeout=60)


def distribution(project):
    time.sleep(1)  # a third-party site: no burst
    html = fetch(DISTRIBUTION_PAGE.format(project=project)).read().decode('utf-8', 'replace')
    match = DISTRIBUTION_ROW.search(html)
    return match.group(1).strip() if match else 'unknown'


def cdn_url(file_id, filename):
    return CDN.format(head=file_id // 1000, tail=file_id % 1000, name=urllib.parse.quote(filename))


def remote_hash(url, algorithm):
    digest = hashlib.new(algorithm)
    with fetch(url) as response:
        while chunk := response.read(1 << 16):
            digest.update(chunk)
    return digest.hexdigest()


def api_metafiles(root):
    return sorted(p for p in root.rglob('*.pw.toml') if 'tools' not in p.parts and API_MODE in p.read_text())


def rewrite(path):
    meta = tomllib.loads(path.read_text())
    download = meta['download']
    source = meta['update']['curseforge']
    project, file_id = source['project-id'], source['file-id']
    allowed = distribution(project)
    if allowed != 'Allowed':
        raise SystemExit(f'{path}: CurseForge project {project} has third-party distribution "{allowed}";'
                         ' host this file ourselves instead')
    url = cdn_url(file_id, meta['filename'])
    algorithm = {'sha1': 'sha1', 'sha256': 'sha256', 'sha512': 'sha512', 'md5': 'md5'}[download['hash-format']]
    actual = remote_hash(url, algorithm)
    if actual != download['hash'].lower():
        raise SystemExit(f'{path}: {url} has {algorithm} {actual}, packwiz recorded {download["hash"]}')
    path.write_text(path.read_text().replace(API_MODE, f'url = "{url}"'))
    print(f'{path}: {url}')


def main():
    root = Path('.')
    pending = api_metafiles(root)
    if '--check' in sys.argv[1:]:
        for path in pending:
            print(f'{path}: still uses the CurseForge API (run tools/cf_direct_urls.py)')
        return 1 if pending else 0
    for path in pending:
        rewrite(path)
    if pending:
        print(f'{len(pending)} rewritten; now run `packwiz refresh`')
    return 0


if __name__ == '__main__':
    sys.exit(main())
