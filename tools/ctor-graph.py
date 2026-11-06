#!/usr/bin/env python3
"""Lists the Create classes a mod's @Mod constructor initializes on its own thread.

Forge builds the mods in parallel unless config/fml.toml sets maxThreads = 1. A Create addon whose constructor (or a
static initializer it triggers) touches one of Create's registry holder classes (AllBlocks, AllItems, ...) then writes
Create's unsynchronized Registrate from a second thread and can lose Create items at random (Create#8825). Run this on
a new Create addon before adding it.

Usage (from the pack root; needs javap of a JDK on PATH):
    python3 -I tools/ctor-graph.py <mod jar> <create jar> <mod class> [--all] [--lambdas] [--clinits [--paths]]

    <mod class>   the @Mod class, e.g. com.railwayteam.railways.forge.RailwaysImpl
    --all         every reference to Create or Registrate reached, not only class initializations
    --lambdas     also follow the bodies of the mod's lambdas (most run later: datagen, registry events)
    --clinits     list the static initializers reached, marking those that use Create's registrate

The graph follows method calls into the mod's and Create's own classes, and the static initializer of every class
touched by getstatic, putstatic, invokestatic or new. Method references handed to DistExecutor are not followed.
It runs javap once per class: a large mod such as Steam 'n' Rails takes about 3 minutes.
"""
import argparse
import re
import subprocess
import sys
import zipfile
from collections import deque

EXT = ('com/simibubi/create/', 'com/tterrag/registrate/', 'net/createmod/')
TRIGGERS = ('getstatic', 'putstatic', 'invokestatic', 'new')
HEADER = re.compile(r'^  (?:[\w.<>\[\], $?]+ )?([\w$<>.]+)\((.*)\)(?: throws [\w.,$ ]+)?;$')
REF = re.compile(r'// (Method|InterfaceMethod|Field) (?:([\w/$]+)\.)?([\w$<>"]+):')
CLASS_REF = re.compile(r'// class ([\w/$]+)')


def class_names(jars):
    names = set()
    for jar in jars:
        with zipfile.ZipFile(jar) as z:
            names.update(n[:-6] for n in z.namelist() if n.endswith('.class') and not n.startswith('META-INF'))
    return names


class Disassembler:
    def __init__(self, classpath):
        self.classpath = classpath
        self.cache = {}

    def methods(self, cls):
        """Instruction lines per method name; constructors are <init>, the static initializer <clinit>."""
        if cls in self.cache:
            return self.cache[cls]
        out = subprocess.run(['javap', '-c', '-p', '-classpath', self.classpath, cls.replace('/', '.')],
                             capture_output=True, text=True).stdout
        methods, current = {}, None
        for line in out.splitlines():
            if line.startswith('  static {};'):
                current = '<clinit>'
                methods.setdefault(current, [])
                continue
            m = HEADER.match(line)
            if m:
                current = '<init>' if '.' in m.group(1) else m.group(1)
                methods.setdefault(current, [])
                continue
            if current is not None and re.match(r'^\s+\d+: ', line):
                methods[current].append(line.strip())
        self.cache[cls] = methods
        return methods


def walk(dis, own, start, lambdas):
    """Breadth-first over the methods reached from the mod class; returns the visited set, paths and Create hits."""
    seen, paths, hits = set(), {}, []
    queue = deque([((start, '<clinit>'), [f'{start}.<clinit>']), ((start, '<init>'), [f'{start}.<init>'])])
    while queue:
        (cls, meth), path = queue.popleft()
        if (cls, meth) in seen:
            continue
        seen.add((cls, meth))
        paths[(cls, meth)] = path
        if lambdas and not cls.startswith(EXT):
            base = {'<init>': 'new', '<clinit>': 'static'}.get(meth, meth)
            for name in dis.methods(cls):
                if name.startswith(f'lambda${base}$'):
                    queue.append(((cls, name), path + [f'{cls}.{name}(lambda)']))
        for ins in dis.methods(cls).get(meth, []):
            op = ins.split()[1]
            refs = [(kind, owner or cls, member.strip('"')) for kind, owner, member in REF.findall(ins)]
            refs += [('Class', owner, '') for owner in CLASS_REF.findall(ins)]
            for kind, owner, member in refs:
                if owner.startswith(EXT):
                    hits.append((op, owner, member, path))
                if owner in own:
                    if op in TRIGGERS and owner != cls:
                        queue.append(((owner, '<clinit>'), path + [f'{owner}.<clinit>']))
                    if kind in ('Method', 'InterfaceMethod'):
                        queue.append(((owner, member), path + [f'{owner}.{member}']))
    return seen, paths, hits


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('mod_jar')
    parser.add_argument('create_jar')
    parser.add_argument('mod_class')
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--lambdas', action='store_true')
    parser.add_argument('--clinits', action='store_true')
    parser.add_argument('--paths', action='store_true')
    args = parser.parse_args()

    jars = [args.mod_jar, args.create_jar]
    dis = Disassembler(':'.join(jars))
    start = args.mod_class.replace('.', '/')
    seen, paths, hits = walk(dis, class_names(jars), start, args.lambdas)
    print(f'# visited {len(seen)} methods')

    if args.clinits:
        for cls, meth in sorted(seen):
            body = dis.methods(cls).get('<clinit>') if meth == '<clinit>' else None
            if body:
                uses = any('Create.registrate:' in i or 'REGISTRATE:' in i for i in body)
                print(f'CLINIT {cls}{"  [uses Create REGISTRATE]" if uses else ""}')
                if args.paths and uses:
                    print('    via ' + ' -> '.join(paths[(cls, meth)]))
        return 0

    # One line per Create class initialized (or per call of a Registrate callback), with the first path found
    shown = {}
    for op, owner, member, path in hits:
        if args.all:
            key = (op, owner, member)
        elif op in TRIGGERS:
            key = owner
        elif 'Callback' in member or member in ('onRegister', 'addDataGenerator'):
            key = (op, owner, member)
        else:
            continue
        shown.setdefault(key, (op, owner, member, ' -> '.join(path)))
    for op, owner, member, path in sorted(shown.values(), key=lambda h: (h[1], h[2])):
        print(f'{op:15} {owner}.{member}\n    via {path}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
