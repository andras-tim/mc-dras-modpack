# mc.dras.hu modpack

A small [packwiz](https://packwiz.infra.link/) modpack for a private Minecraft server: Minecraft 1.20.1, Forge
47.4.20, Create with its addons, Ad Astra, Immersive Engineering, Alex's Mobs, L_Ender's Cataclysm and Biomes O'
Plenty, plus a layer of stability fixes.

The repository holds only metadata and files written for this pack: every mod is a `.pw.toml` that points at the
author's own download (CurseForge CDN or Modrinth), checked by its hash. No mod jar and no file of another modpack is
stored here.

## Playing

The server and every client read the same `pack.toml`, so they always run the same mods.

**Phone setup page: <https://mc.dras.hu/>** (the launcher download with an optional Obtainium link for its updates, and the profile link).

| where | how |
|---|---|
| PC, Steam Deck | [Prism Launcher](https://prismlauncher.org/) profile with [packwiz-installer](https://github.com/packwiz/packwiz-installer) as its pre-launch command: `"$INST_JAVA" -jar packwiz-installer-bootstrap.jar -g <pack.toml URL>`; it updates the mods on every start |
| Android | [Amethyst::Dras](https://github.com/andras-tim/Amethyst-Android/tree/dras) (an Amethyst fork with packwiz support): open `amethyst://profile/import?url=<pack.toml URL>`; the pack is synced on every Play. `tools/phone-qr.py` shows a QR code for the APK and one for this link |
| server | [itzg/minecraft-server](https://github.com/itzg/docker-minecraft-server) with `TYPE=FORGE`, the versions of `pack.toml`, and `PACKWIZ_URL=<pack.toml URL>` |

Released pack for the launchers: `https://mc.dras.hu/pack/pack.toml`, published from the latest GitHub release. Next to
it is `mc-dras-controls.json`, the touch layout of Amethyst::Dras: the app's default layout with a Map button (`J`) in
the More drawer. It is not a game file, so packwiz ignores it; the site publishes it with the profile icon
`branding/profile-icon.png`, from the release or, on a manual run, from `main`.

Pack URLs (GitHub raw): `https://raw.githubusercontent.com/andras-tim/mc-dras-modpack/<tag>/pack.toml`. The server
pins a release tag (`1.20.1-<n>`); clients follow the latest release, published after the server runs it.

On Android the first start takes three steps, all expected: Play downloads the mods (about 210 MB); the Forge
installer runs and the app closes without a message (the launcher runs Java in its own process and exits after
every Java program); Play again downloads Minecraft itself once (about 700 MB) and starts the game. Later starts only
fetch what changed.

## What is in the pack

| group | mods |
|---|---|
| Create | Create, Connected, Deco, Easy Structures, Enchantment Industry, Interiors, New Age, Optical, Prismatic Shine, Steam 'n' Rails, Dynamic Village |
| space | Ad Astra, Create: Ad Astra Compatibility, Create Planetary Tweaks |
| industry | Immersive Engineering, Immersive Fixes |
| world and mobs | Alex's Mobs, L_Ender's Cataclysm, Biomes O' Plenty |
| tools | Just Enough Items, JourneyMap, Patchouli, Almost Unified, Statboard |
| stability, server and both sides | AllTheLeaks, Clumps, Cupboard, DEUF, Dimensional Sync Fixes, Feature Recycler, FerriteCore, Load My F***ing Tags, ModernFix, NaNny Reforked, Neruina, Packet Fixer, spark, Structure Essentials, Structure Layout Optimizer |
| client only | Embeddium, ImmediatelyFast, fix GPU memory leak, Controllable::Dras (our fork of Controllable), Controlling |
| libraries | Botarium, Citadel, Curios API, Framework, GeckoLib, GlitchCore, Lionfish API, Paxi, Puzzles Lib, Resourceful Config, Resourceful Lib, Searchables, TerraBlender, YUNG's API |

Earth is harmless: the pack has no air or temperature mechanic there. Ad Astra's planets and orbits are dangerous:

| place | air | temperature | what you need |
|---|---|---|---|
| Earth | yes | 15 °C | nothing |
| Glacio | yes | -20 °C | not tested |
| Moon, Mars | no | -173 °C, -65 °C | space suit with oxygen |
| Mercury, Venus | no | 167 °C, 464 °C | netherite or jet suit with oxygen |
| orbits | no | -270 °C | space suit with oxygen |

Statboard records every player's statistics on the server and shows them with leaderboards: `B` (on phones the Stats
button of the touch layout), or `/stats` in the chat. Its optional PixelView2 interface runs only on Windows, so it is
not in the pack; the dashboard uses the vanilla interface.

Gamepads (Xbox and the like) work through [Controllable::Dras](https://github.com/andras-tim/Controllable), our fork of
Controllable that also runs on Android launchers. Defaults of a new install: D-pad left opens the map, D-pad right the
radial menu (chat, map, Statboard, advancements, Controllable settings), D-pad up switches the camera, D-pad down drops
the item; the stick clicks sprint and sneak, `B` goes back on every screen. Everything can be changed in Controllable's
settings.

## Settings

Only the changed keys are in `config/`; everything else is each mod's default.

| file | setting | why |
|---|---|---|
| `create_new_age-common.toml` | `maxPathfindingDepth = 32` | as in the reference pack |
| `alexsmobs.toml` | `transmutingExperienceCost = 25`, `mimicreamRepair = false` | as in the reference pack |
| `lmft.json` | `disableIngameError = true` | as in the reference pack |
| `modernfix-mixins.properties` | `dynamic_resources`, `faster_item_rendering` on; branding, the missing-mods warning and `release_protochunks` off | as in the reference pack |
| `packetfixer.properties` | larger packet sizes, as in the reference pack; `timeout = 15` | see below |
| `jei/jei-client.ini` | `LowMemorySlowSearchEnabled = true` | saves memory on phones |
| `controllable/bindings.properties` | pick block unbound (`preserve`) | D-pad left is free for the map |
| `controllable/key_adapters.properties` | JourneyMap's map on D-pad left, Statboard for the radial menu (`preserve`) | |
| `controllable/radial_menu_items.json` | chat, map, Statboard, advancements, Controllable settings (`preserve`) | screenshot and fullscreen are no use on a phone |
| `options.txt` | view and simulation distance 6, fast graphics, minimal particles, 60 FPS limit; key bindings below | defaults of a new install |
| `servers.dat` | the server in the multiplayer list of a new install (`preserve`), written by `tools/servers-dat.py` |
| `paxi/datapacks/mc-dras-fixes/` | disables Ad Astra's 7 Create crushing recipes that collide with `create_ad_astra_compat` and `cp_tweaks` | one recipe per ore |

Key bindings of a new install: every mod keeps its own defaults, as in large packs, except where two bindings share a
key in the game. Forge fires every binding on a pressed key, so a shared key does two things at once.

| binding | default | in the pack | why |
|---|---|---|---|
| JourneyMap: create waypoint | `B` | none | `B` opens Statboard; the full-screen map still creates waypoints on `B` |
| JourneyMap: toggle entity names | `G` | none | `G` opens the Curios inventory |
| Load and Save Hotbar Activator | `X`, `C` | `H`, `K` | `X` and `C` are Cataclysm armor abilities; `H` and `K` sit at the same place on Hungarian and US keyboards, and do nothing without a number key |

Shared keys left as they are: `S` (Immersive Engineering's magnet equip is a double tap of walk back by design: it
pulls a magnet-upgraded shield into the off hand), `V` (Ad Astra suit flight, Cataclysm boots: both are boots), and the
keys of JEI and the full-screen map, which work on their own screens only. Controlling (in the pack) lists the
conflicts in the Controls screen.

## Known limitations

- **Ad Astra space stations** (1.15.21): an orbit is empty until you build a station from the rocket's planet screen:
  choose the planet, then the `+` next to "Space Stations", with the materials in your inventory (Earth: 64 iron plates,
  32 steel ingots, 32 desh ingots, 32 desh plates). The `+` builds at once and takes you there. Choosing "Land" without
  a station leaves you floating in empty space.
  - You arrive in a lander: **hold space from about 240 blocks on** and keep holding until it stops, or it explodes on
    the station and you die. The station is below your arrival point, so keep flying straight down.
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
| `config/` | only the keys we change: the mods add the rest with their defaults, so a mod update keeps its new defaults |
| `config/paxi/datapacks/mc-dras-fixes/` | our datapack, Paxi loads it into every world: drops Ad Astra's crushing recipes that collide with `create_ad_astra_compat` and `cp_tweaks` |
| `options.txt` | first-start graphics defaults (`preserve`: never overwrites a player's settings) |
| `prism/` | settings of a new PC install: `instance.cfg` (memory, pre-launch command), `options.txt` (view distance 10) |
| `branding/` | the profile icon |
| `docs/index.html` | template of the setup site for phones and PCs |
| `docs/parts/` | step templates of the site (`step-download`, `step-apk`, `step-link`, `step-login`) and the Android install help they share, used as `<x-NAME>` tags in the template |
| `docs/icons/` | app icons of the site's choices: `obtainium.svg` from [Obtainium](https://github.com/ImranR98/Obtainium) (`assets/graphics/icon.svg`, GPL-3.0; its `viewBox` cropped to the drawing), `amethyst-dras.webp` is the foreground layer of the [Amethyst::Dras](https://github.com/andras-tim/Amethyst-Android) launcher icon (`mipmap-xxhdpi/ic_launcher_foreground.webp`, LGPL-3.0), trimmed and scaled to 96 px, `prism-launcher.svg` from [Prism Launcher](https://github.com/PrismLauncher/PrismLauncher) (`program_info/org.prismlauncher.PrismLauncher.svg`, GPL-3.0) |
| `tools/site.py` | builds the site with its QR codes and the Prism zip; CI publishes it on GitHub Pages from `main` |
| `tools/` | maintenance scripts |

## Differences from the reference pack

The pack follows SteamPunk [LPS] v19 in mod versions and settings where it has the same mods, with its own files and
these differences:

| topic | difference | why |
|---|---|---|
| map | JourneyMap instead of Xaero's | the players' choice |
| Immersive Engineering + Immersive Fixes | added | more industry |
| Almost Unified | added, default config | Immersive Engineering, Ad Astra and Create add the same materials |
| Thin Air, Create Air | left out | no suffocation on Earth |
| FullStack Watchdog | left out | server-only, but declares no `displayTest`: every client sees a red "Incompatible" mark |
| Ad Astra temperature | stays on | the reference turned it off for Cold Sweat, which we do not have; planets stay dangerous, Earth is normal |
| Packet Fixer `timeout` | 15 instead of 120 | it also sets the keep-alive period: with 120 the server sends none for 2 minutes, and a client on the death screen, which sends nothing, is dropped after 30 s |
| monorail recipe | stays enabled | no known bug behind the reference's ban |
| Alex's Mobs start book | stays | useful for new players |
| Embeddium | added | chunk rendering on phones; Flywheel declares support for it |
| versions | 9 mods are newer | fixes, see the changelogs of those mods |
