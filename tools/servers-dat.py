#!/usr/bin/env python3
"""Write servers.dat, the multiplayer server list of a new install, as Minecraft's uncompressed NBT.

Usage (from the pack root): python3 -I tools/servers-dat.py, then tools/packwiz refresh
"""
import struct

SERVER_NAME = 'mc.dras.hu'
SERVER_ADDRESS = 'mc.dras.hu'
TAG_END, TAG_STRING, TAG_LIST, TAG_COMPOUND = 0, 8, 9, 10


def name(text):
    data = text.encode('utf-8')
    return struct.pack('>H', len(data)) + data


def string(key, value):
    return bytes([TAG_STRING]) + name(key) + name(value)


def main():
    server = string('name', SERVER_NAME) + string('ip', SERVER_ADDRESS) + bytes([TAG_END])
    servers = bytes([TAG_LIST]) + name('servers') + bytes([TAG_COMPOUND]) + struct.pack('>i', 1) + server
    with open('servers.dat', 'wb') as f:
        f.write(bytes([TAG_COMPOUND]) + name('') + servers + bytes([TAG_END]))


if __name__ == '__main__':
    main()
