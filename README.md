# mc.dras.hu modpack

A small [packwiz](https://packwiz.infra.link/) modpack for a family Minecraft server: Minecraft 1.20.1, Forge
47.4.20, Create with its addons, Ad Astra, Immersive Engineering, Alex's Mobs, L_Ender's Cataclysm and Biomes O'
Plenty, plus a layer of stability fixes.

The repository holds only metadata and files written for this pack: every mod is a `.pw.toml` that points at the
author's own download (CurseForge CDN or Modrinth), checked by its hash. No mod jar and no file of another modpack is
stored here.

## Playing

The server and every client read the same `pack.toml`, so they always run the same mods.

**Phone setup page: <https://andras-tim.github.io/mc-dras-modpack/>** (the launcher download and the profile link;
the page lives in `docs/`).

| where | how |
|---|---|
| PC, Steam Deck | [Prism Launcher](https://prismlauncher.org/) instance with [packwiz-installer](https://github.com/packwiz/packwiz-installer) as its pre-launch command: `"$INST_JAVA" -jar packwiz-installer-bootstrap.jar -g <pack.toml URL>`; it updates the mods on every start |
| Android | [Amethyst::Dras](https://github.com/andras-tim/Amethyst-Android/tree/dras) (an Amethyst fork with packwiz support): open `amethyst://profile/import?url=<pack.toml URL>`; the pack is synced on every Play. `tools/phone-qr.py` shows a QR code for the APK and one for this link |
| server | [itzg/minecraft-server](https://github.com/itzg/docker-minecraft-server) with `TYPE=FORGE`, the versions of `pack.toml`, and `PACKWIZ_URL=<pack.toml URL>` |

Pack URLs (GitHub raw): `https://raw.githubusercontent.com/andras-tim/mc-dras-modpack/<tag>/pack.toml`. The server
pins a release tag (`1.20.1-<n>`); clients follow the `stable` tag, which moves to a release after the server runs it.

On Android the first start takes three steps, all expected: Play downloads the mods (about 210 MB); the Forge
installer runs and the app closes without a message (the launcher runs Java in its own process and exits after
every Java program); Play again downloads Minecraft itself once (about 700 MB) and starts the game. Later starts only
fetch what changed.

## Known limitations

- **Ad Astra space stations** (1.15.21): an orbit is empty until you build a station from the rocket's planet screen
  ("Space Stations" → "Construct", the materials in the inventory; the in-game Astrodux book explains it).
  - A rocket can miss a freshly built station and leave you floating, mostly when the station is the first place you
    visit in space ([#475](https://github.com/terrarium-earth/Ad-Astra/issues/475), open). Visit the orbit once
    before building it. When it happens, the station's coordinates are in the planet screen's tooltip ("Land on space
    station in … at [x, z]"): fly there in creative, or `/tp @s <x> <y> <z>` inside the orbit dimension.
  - Only the owner can land on a station. Argonauts parties would share it, but that does not work on a dedicated
    server ([#535](https://github.com/terrarium-earth/Ad-Astra/issues/535),
    [#762](https://github.com/terrarium-earth/Ad-Astra/issues/762), open), so it is not in the pack.

## Layout

| path | what |
|---|---|
| `pack.toml`, `index.toml` | pack name, version, Minecraft and Forge version; the list of files with their hashes |
| `mods/*.pw.toml` | one per mod: download URL, hash, side (`both`, `client`, `server`) |
| `tools/cf_direct_urls.py` | rewrites packwiz's CurseForge metafiles to the direct CDN URL (see below) |
| `tools/check_deps.py` | every mod's mandatory dependencies and incompatibilities, per side, from the jars' `mods.toml` |
| `tools/phone-qr.py` | QR codes for a phone: the launcher APK, then the profile import link |
| `branding/` | the profile icon |
| `docs/` | the phone setup page (GitHub Pages) |
| `tools/smoke-test.sh` | boots a dedicated server from the checkout the way the real server does and waits for "Done" |

## Changing the pack

The tools run from the pack root; `tools/packwiz` runs packwiz from a container (pinned in `tools/packwiz.Dockerfile`).

1. Check that the mod's author allows third-party downloads (CurseForge "Mod Distribution: Allowed"). A mod that
   forbids it can only join if we host its file ourselves.
2. Add or update it at an exact file: `packwiz curseforge add --addon-id <project> --file-id <file>` (or
   `packwiz modrinth add --project-id <slug> --version-id <id>`). Prefer a version that other maintained packs ship
   together with our other mods; read the changelogs and issue trackers of every version in between.
3. `python3 -I tools/cf_direct_urls.py`, then `packwiz refresh`. packwiz writes `mode = "metadata:curseforge"` for
   CurseForge files, which makes clients ask the CurseForge API for the download; the tool replaces it with the file's
   CDN URL after checking the distribution flag and the hash, so no client needs an API key.
4. Set `side` in the `.pw.toml` when the mod belongs to one side only.
5. `python3 -I tools/check_deps.py` and `tools/smoke-test.sh` must pass; then start a client on PC and on a phone.
6. Configs and datapacks are written for this pack. Other packs are a source of ideas (what to tune, which versions
   work together, known pitfalls), never of files.

A world outlives the mods in it: back up before every change, change one mod at a time, never remove a mod whose
blocks are in use (Create contraptions and trains included) without disassembling them first.
