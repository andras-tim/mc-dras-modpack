# How the pack reaches the players

The pack is maintained with packwiz, and the server and every client follow the same `pack.toml`. This page records
the ways considered for getting it onto the players' launchers, and why packwiz was chosen. Requirements: updates
reach the players without them doing anything, worlds survive an update, only stable releases (no beta, release
candidate or development build) on the players' side, and as few changes to a launcher as possible.

## Decision

**packwiz everywhere**, each launcher through its own standard path:

| where | how | updates |
|---|---|---|
| PC, Steam Deck | [Prism Launcher](https://prismlauncher.org/) instance with [packwiz-installer](https://github.com/packwiz/packwiz-installer) as its pre-launch command (the packwiz documentation's Prism setup) | automatic on every start; a Forge version change is a manual step |
| Android | [Amethyst::Dras](https://github.com/andras-tim/Amethyst-Android) (Amethyst with a native packwiz sync) | automatic before every Play, Forge version changes included |
| server | [itzg/minecraft-server](https://github.com/itzg/docker-minecraft-server) with `PACKWIZ_URL` | when its pinned pack version moves |

One entry point for everyone: the [setup page](https://andras-tim.github.io/mc-dras-modpack/), which offers the
button that fits the device.

## Alternatives considered

| option | Prism | Amethyst | updates | why not |
|---|---|---|---|---|
| **`.mrpack`** (Modrinth pack, `packwiz modrinth export`) | standard import from a file or a URL | standard import | Prism: paste the pack URL once on the instance's Modrinth tab, then "Update Pack" by hand; Amethyst: every import makes a new profile in a new folder (worlds stay behind) unless the launcher gets an update button | manual updates; Prism lists every file not hosted on `cdn.modrinth.com` (49 of our mods) as "untrusted" and asks before each import and update; the format carries no command, memory setting or update URL |
| **CurseForge zip** (`packwiz curseforge export`) | standard import, update from a URL | import, a new profile each time | manual | the zip names files by CurseForge ID only, so the client needs a CurseForge API key |
| **zip with the jars inside** | import | import | manual re-import | the jars may only be shared privately (several mods do not allow redistribution) |
| **publishing on Modrinth or CurseForge** | install from the launcher's search, update button | install from search | manual | public, moderated per file; CurseForge requires the manifest its own app generates |
| **AutoModpack** (a mod that syncs the client from the server) | any launcher | any launcher | automatic on joining | an extra mod in the pack; the Android fix is only in the 5.0 line, which is all beta (`5.0.0-rc.*`); the stable 4.0.7 lacks it |
| **FCL / HMCL "server pack"** | HMCL instead of Prism | Fold Craft Launcher instead of Amethyst | automatic | changing launchers; FCL's interface was rejected |
| **one link for both launchers** (`prismlauncher://import`, with Amethyst::Dras reading Prism instance zips) | standard | needs a Prism instance importer in the fork | as packwiz | more launcher changes for the same result as the setup page |

A `.mrpack` can still be offered next to packwiz (one `packwiz modrinth export` per release) for players on other
launchers who accept manual updates.

## Stability of the chosen parts

| part | release state |
|---|---|
| Amethyst::Dras | built on the stable Amethyst 1.1.7 release tag, not on upstream's development branch |
| Prism Launcher | stable release |
| packwiz-installer | stable release (0.5.14, 2024), widely used, no newer release since |
| itzg/minecraft-server | pinned stable image tag |
| mods | stable (release) files only |
| packwiz CLI | **no releases at all**, pinned to a `main` commit in `tools/packwiz.Dockerfile`; runs only when the pack is maintained, never on the players' side |
