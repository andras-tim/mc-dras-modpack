#!/bin/sh
# Boots a dedicated server from this pack the way the server role does (itzg with PACKWIZ_URL, so packwiz-installer
# installs the server side of the pack) and waits for "Done": catches mods that fail to load, e.g. a missing
# dependency, before a release reaches the players. Client-only failures stay out of its reach.
# usage: tools/smoke-test.sh   (from the pack root; needs Docker and the internet for the mod downloads)
set -eu

# https://github.com/itzg/docker-minecraft-server/releases
# changelog: in release
image=itzg/minecraft-server:2026.7.0-java17    # Forge 1.20.1 needs Java 17
timeout_s=1200
id=mc-dras-smoke-$$

versions=$(python3 -I -c 'import tomllib; v = tomllib.load(open("pack.toml", "rb"))["versions"]; print(v["minecraft"], v["forge"])')
mc=${versions% *}
forge=${versions#* }
data=$(mktemp -d)
cleanup() {
    docker rm -f "$id-server" "$id-pack" >/dev/null 2>&1 || true
    docker network rm "$id" >/dev/null 2>&1 || true
    rm -rf "$data"
}
trap cleanup EXIT

docker pull -q "$image" >/dev/null
docker network create "$id" >/dev/null
# the pack as the server sees it: plain HTTP, the files of this checkout
docker run -d --name "$id-pack" --network "$id" -v "$PWD:/pack:ro" -w /pack python:3-alpine \
    python -m http.server 8000 >/dev/null
docker run -d --name "$id-server" --network "$id" -v "$data:/data" \
    -e EULA=TRUE -e TYPE=FORGE -e VERSION="$mc" -e FORGE_VERSION="$forge" \
    -e PACKWIZ_URL="http://$id-pack:8000/pack.toml" \
    -e MEMORY=4G -e UID="$(id -u)" -e GID="$(id -g)" "$image" >/dev/null

elapsed=0
while [ "$elapsed" -lt "$timeout_s" ]; do
    if docker logs "$id-server" 2>&1 | grep -q 'Done ([0-9.]*s)!'; then
        echo "Server started: Minecraft $mc, Forge $forge, $(ls "$data/mods" | wc -l) mod jars"
        exit 0
    fi
    if [ "$(docker inspect -f '{{.State.Running}}' "$id-server")" != 'true' ]; then
        break
    fi
    sleep 10
    elapsed=$((elapsed + 10))
done
echo "Server did not start (after ${elapsed}s); last log lines:" >&2
docker logs "$id-server" 2>&1 | tail -60 >&2
exit 1
