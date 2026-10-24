#!/usr/bin/env python3
"""Check the pack's mods against each other, for the client and the server side separately.

Reads every jar's META-INF/mods.toml (and the mods nested through Forge's jar-in-jar) and reports:
- a mandatory dependency that no mod of that side provides (error),
- a mod declared incompatible with another one in the pack (error),
- a provided version outside the declared range (warning: the range parsing is a close approximation of Maven's).

Mods declare only what they know about: undeclared hard dependencies (like Cataclysm needing Curios) still need the
server smoke test (tools/smoke-test.sh) and a client start.

Jars are downloaded once, checked against the pack's hash, and kept in ~/.cache/mc-dras/pack-jars.
Usage (from the pack root): python3 -I tools/check_deps.py
"""
import hashlib
import io
import json
import os
import re
import sys
import tomllib
import urllib.request
import zipfile
from pathlib import Path

USER_AGENT = 'mc-dras-modpack tools (https://github.com/andras-tim/mc-dras-modpack)'
CACHE = Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache')) / 'mc-dras' / 'pack-jars'
PLATFORM = {'minecraft', 'forge', 'java', 'javafml', 'lowcodefml'}
SIDES = {'client': ('both', 'client'), 'server': ('both', 'server')}


def pack_mods():
    index = tomllib.loads(Path('index.toml').read_text())
    for entry in index['files']:
        if entry.get('metafile'):
            meta = tomllib.loads(Path(entry['file']).read_text())
            yield entry['file'], meta


def cached_jar(meta):
    download = meta['download']
    path = CACHE / download['hash'][:16] / meta['filename']
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(download['url'], headers={'User-Agent': USER_AGENT})
        data = urllib.request.urlopen(request, timeout=120).read()
        actual = hashlib.new(download['hash-format'], data).hexdigest()
        if actual != download['hash'].lower():
            raise SystemExit(f'{meta["filename"]}: downloaded {download["hash-format"]} {actual}, pack says {download["hash"]}')
        path.write_bytes(data)
    return path.read_bytes()


def jar_version(jar):
    try:
        manifest = jar.read('META-INF/MANIFEST.MF').decode('utf-8', 'replace')
    except KeyError:
        return None
    match = re.search(r'^Implementation-Version:\s*(\S+)', manifest, re.M)
    return match.group(1) if match else None


def read_mods(jar_bytes, origin):
    """(provided {modId: version}, declared [(modId, dependency table)]) of a jar and the jars nested in it."""
    provided, declared = {}, []
    jar = zipfile.ZipFile(io.BytesIO(jar_bytes))
    names = set(jar.namelist())
    if 'META-INF/mods.toml' in names:
        toml = tomllib.loads(jar.read('META-INF/mods.toml').decode('utf-8', 'replace'))
        for mod in toml.get('mods', []):
            version = str(mod.get('version', ''))
            if '${' in version:
                version = jar_version(jar) or version
            provided[mod['modId']] = version
        for owner, dependencies in toml.get('dependencies', {}).items():
            for dependency in dependencies if isinstance(dependencies, list) else []:
                declared.append((owner, dependency))
    if 'META-INF/jarjar/metadata.json' in names:
        for nested in json.loads(jar.read('META-INF/jarjar/metadata.json')).get('jars', []):
            nested_provided, nested_declared = read_mods(jar.read(nested['path']), origin)
            provided.update(nested_provided)
            declared.extend(nested_declared)
    return provided, declared


def version_key(version):
    parts = re.split(r'[.\-+_]', version)
    return [(0, int(p), '') if p.isdigit() else (1, 0, p.lower()) for p in parts if p]


def in_range(version, spec):
    """Maven version range, e.g. "[6.0.8,6.1)", "[47,)", "1.0" (any, a soft requirement), unions with commas."""
    spec = spec.strip()
    if not spec or spec == '*' or spec[0] not in '[(':
        return True
    for low_open, low, high, high_close in re.findall(r'([\[(])\s*([^,\])]*)\s*,?\s*([^\])]*)\s*([\])])', spec):
        if ',' not in spec[spec.index(low_open):] and low and not high:
            high = low  # "[1.2]" means exactly 1.2
        key = version_key(version)
        if low and (key < version_key(low) or (low_open == '(' and key == version_key(low))):
            continue
        if high and (key > version_key(high) or (high_close == ')' and key == version_key(high))):
            continue
        return True
    return False


def is_mandatory(dependency):
    if 'type' in dependency:
        return str(dependency['type']).lower() == 'required'
    return bool(dependency.get('mandatory', False))


def main():
    jars = {}
    for path, meta in pack_mods():
        provided, declared = read_mods(cached_jar(meta), meta['filename'])
        jars[meta['filename']] = (meta.get('side', 'both'), provided, declared)

    errors = warnings = 0
    for side, included in SIDES.items():
        mods = {f: j for f, j in jars.items() if j[0] in included}
        provided = {}
        for filename, (_, mod_ids, _) in mods.items():
            for mod_id, version in mod_ids.items():
                provided[mod_id] = (version, filename)
        for filename, (_, _, declared) in mods.items():
            for owner, dependency in declared:
                mod_id = dependency.get('modId', '')
                dependency_side = str(dependency.get('side', 'BOTH')).lower()
                if mod_id in PLATFORM or dependency_side not in ('both', side):
                    continue
                kind = str(dependency.get('type', '')).lower()
                if kind in ('incompatible', 'discouraged') and mod_id in provided:
                    print(f'{side}: {filename} ({owner}) is {kind} with {mod_id} ({provided[mod_id][1]})')
                    errors += kind == 'incompatible'
                    continue
                if not is_mandatory(dependency):
                    continue
                if mod_id not in provided:
                    print(f'{side}: {filename} ({owner}) needs {mod_id} {dependency.get("versionRange", "")}: missing')
                    errors += 1
                    continue
                version = provided[mod_id][0]
                spec = str(dependency.get('versionRange', ''))
                if not in_range(version, spec):
                    print(f'{side}: {filename} ({owner}) wants {mod_id} {spec}, the pack has {version}'
                          f' ({provided[mod_id][1]})')
                    warnings += 1
        print(f'{side}: {len(mods)} jars, {len(provided)} mod ids')
    print(f'{errors} errors, {warnings} warnings')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
