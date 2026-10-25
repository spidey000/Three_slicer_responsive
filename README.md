# Copy this prompt into your AI coding agent to install ThreeSlicer for a FlashForge Adventurer 4

> **Copy everything in the block below and paste it into an AI coding agent with terminal access on the Linux computer that will run the application.** The agent should install the web slicer and the local printer bridge, connect to your Adventurer 4, and tell you exactly how to open the UI.

```text
You are my installation and verification agent. Install and configure the open-source
ThreeSlicer Responsive web application for a FlashForge Adventurer 4.

Source repositories:
- Web application: https://github.com/spidey000/Three_slicer_responsive
- Printer CLI: https://github.com/spidey000/FFAD4Manager

Operating environment: a Linux computer on the same trusted LAN as the printer.
Use Python 3.9+ (with venv and pip), Node.js 20+, and npm. Check tools and versions
first. Explain any missing prerequisite; do not silently install system software,
modify firewall rules, or enable public network access without my permission.

1. Clone both repositories into a directory I choose, or use existing clones
   after checking the remote and any uncommitted changes. Do not overwrite my work.
2. Install FFAD4Manager in an isolated Python environment:
   python3 -m venv .venv
   . .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install -e ./FFAD4Manager
   Adjust working directories accordingly; confirm ffadv4manager is available.
3. Ask me for the printer's LAN address if you cannot determine it safely.
   You may run 'ffadv4manager discover --json' as a read-only discovery step.
   If I confirm the correct IP, run:
   ffadv4manager config set --host PRINTER_IP
   ffadv4manager status --json
   Do not send any motion, heating, fan, upload, or print commands during setup.
4. Enter the Three_slicer_responsive repository and use the committed lockfile:
   npm ci
   npm run build
   Keep the FFAD4Manager virtual environment activated. Run the web bridge:
   npm run local
   Its default URL is http://127.0.0.1:8765/Three_slicer_responsive/
   The server listens on loopback only. Never bind it to 0.0.0.0 or expose
   printer-control APIs to the public Internet.
5. Verify the production build exists and the local page and read-only
   GET /api/printer/status route respond. Try the camera snapshot endpoint
   only if I ask. Verify browser WebGL compatibility. Summarize any failures.
6. Explain the workflow: open/import a model, choose process/material settings,
   Slice or enable Auto slice, review the generated G-code preview, then optionally
   choose Upload only or Print. Both upload and print control real hardware:
   NEVER click them or trigger their API routes without my explicit approval.
7. Explain precisely what is not available: GitHub Pages is a slicer demo, not
   a remote printer-control service; the web UI does not expose every CLI command.
   The CLI's upload-only path avoids M23/M24, but uploaded-file integrity and
   firmware-side no-start behavior have not been fully verified. Treat a print
   request or file-list ACK as an acknowledgement, not proof of physical success.
8. Give me the local URL, the process or service running the bridge, how to
   restart/stop it, the CLI configuration location, and the results of
   npm run build, printer status, and any smoke tests. Keep my credentials and
   personal network information out of public logs.

Do not declare hardware printing verified without an actual supervised printer test.
Consult README.md and docs/AD4_LOCAL.md for the exact integration contract.
```

---

# ThreeSlicer Responsive — Adventurer 4 Web Slicer

A responsive browser-based slicer and toolpath preview built on [Three Slicer](https://github.com/kimgh06/Three_Slicer), with an optional **local, loopback-only** bridge to [FFAD4Manager](https://github.com/spidey000/FFAD4Manager) for a **FlashForge Adventurer 4 (0.4 mm nozzle)**.

**[Try the online slicer](https://spidey000.github.io/Three_slicer_responsive/)** · **[Local setup](docs/AD4_LOCAL.md)** · **[FFAD4Manager CLI reference](https://github.com/spidey000/FFAD4Manager/blob/main/docs/CLI.md)**

**Conservative printing defaults:** The standard 0.4 mm Adventurer 4 now opens with a low-speed, quality-oriented 0.20 mm profile. All bundled AD4 processes share the conservative speed and acceleration settings; saved custom processes can intentionally override them. See [the speed, acceleration and evidence reference](docs/AD4_CONSERVATIVE_PROFILE.md).

## What works today

| Feature | Available | Notes |
| --- | --- | --- |
| Responsive desktop, tablet and mobile UI | Yes | Mobile settings drawer; dark theme and touch-friendly controls. |
| Load 3D models | Yes | STL, OBJ, 3MF, AMF, PLY and STEP/STP through the underlying viewer. |
| 3D object/plate editing | Yes | Native viewer tools include transform, object management, multi-plate functions and painting where supported. |
| Browser-side slicing | Yes | `three-slicer@0.4.0` WebAssembly worker; does not require the CLI or the printer. |
| Adventurer 4 process/material presets | Yes | Fixed AD4 0.4 mm machine; all built-in process presets share cautious motion settings while retaining each process's other parameters. |
| Save, edit and delete named process/filament profiles | Yes (browser-local) | Choose Save current settings as new profile in either dropdown. Saved custom presets persist in this browser's site storage; Update saved and Delete are available. No cloud synchronization. |
| Artillery PLA Basic filament preset | Yes | 205°C nozzle, 210°C initial layer, 55°C bed; non-HS starting values based on Artillery's temperature range. |
| Advanced slicing settings | Yes | Connected `SettingsPanel` with the same shared slicer settings state. |
| Automatic re-slicing | Yes | Optional Auto slice; changing the model or settings invalidates previous generated G-code. |
| Toolpath preview and simulated nozzle traversal | Yes | Layer and move scrubbing, play, fast-forward, pause and reset; simulated movement is **not** an accurate real-time print prediction. |
| Project/model export | Yes | Native viewer export actions, including 3MF/STL where supported by the upstream package. |
| Live printer status label | Local bridge only | Reads `ffadv4manager status --json` approximately every 8 seconds; no bridge on GitHub Pages. |
| Camera still image | Local bridge only | Uses `ffadv4manager camera snapshot`. If unavailable, the UI clearly shows a demo placeholder, not a live feed. |
| Upload sliced G-code to printer | Local bridge only | Invokes `ffadv4manager upload` and automatic G-code-to-GX wrapping. Requires a reachable printer. |
| Upload and request print start | Local bridge only | Invokes `ffadv4manager upload ... --start`. Device state must be supervised. |

This is functional slicer integration, not a static mockup. The UI delegates geometry manipulation, slicing and G-code preview to `three-slicer-viewer@0.4.0` and `three-slicer@0.4.0` instead of recreating the underlying engine.

## Installation

### Requirements

- A Linux host with **Node.js 20+**, npm, **Python 3.9+**, Python venv and pip.
- A browser with WebGL for the 3D workspace.
- For printer features only: an Adventurer 4 reachable on the same trusted local network, the FFAD4Manager CLI, and the printer's IP address. The legacy command protocol uses TCP port `8899`, and the default camera URL uses HTTP port `8080`.
- No printer connection is required to use browser-based slicing.

```bash
git clone https://github.com/spidey000/Three_slicer_responsive.git
git clone https://github.com/spidey000/FFAD4Manager.git
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ./FFAD4Manager
ffadv4manager config set --host 192.168.1.50   # REPLACE with your printer's IP
ffadv4manager status --json                     # read-only connection check
cd Three_slicer_responsive
npm ci
npm run build
npm run local
```

Open **http://127.0.0.1:8765/Three_slicer_responsive/** on the same computer. Stop the server with Ctrl+C. You can use `AD4_HOST`, `AD4_CLI` and `AD4_WEB_PORT` to customize the local bridge; see [local installation details](docs/AD4_LOCAL.md).

For browser-only development:

```bash
npm ci
npm run dev
# Optional production smoke check:
npm run build
```

The Vite dev server proxies `/api` to the local bridge on port `8765`; printer functions therefore require the bridge even in development.

## What FFAD4Manager can do — and what this web UI exposes

**Key:** **UI** = available in the ThreeSlicer web UI through its local bridge; **CLI only** = implemented by FFAD4Manager but **not wired into this web UI**; **not available** = not provided as described. These statuses describe the current software interface, **not** a blanket guarantee of physical printer behavior.

| CLI function / command | CLI support | ThreeSlicer web UI | Details |
| --- | --- | --- | --- |
| Printer status, temperature, progress — `status --json` | Implemented | **UI** | Status, temperatures, current job, layers and reported progress in Printer Manager. |
| Printer camera still — `camera snapshot` | Implemented | **UI** | One image per request/refresh, not continuous video. |
| Upload G-code / GX — `upload FILE` | Implemented | **UI** | UI posts freshly sliced G-code; CLI performs GX wrapping and listing check. |
| Upload and start — `upload FILE --start` | Implemented | **UI** | Requests an actual print; requires explicit user action. |
| Readable and JSON file list — `files [--json]` | Implemented | **UI (local bridge)** | Printer Manager lists files and can start an existing file. |
| Raw file-list diagnostics — `files-raw` | Implemented | **CLI only** | Debug output is not shown in the app. |
| Existing printer file BMP preview — `files preview` | Implemented | **CLI only** | Different from camera snapshots. |
| Printer discovery — `discover [--json]` | Implemented | **UI (local bridge)** | Discover and select a printer exposed on port 8899. |
| Continuous status sampling — `watch` | Implemented | **CLI only** | UI polls basic status, but does not expose the CLI watch display/JSONL. |
| Firmware and identity — `info` | Implemented | **UI (local bridge)** | Information available in diagnostics. |
| Reported coordinates — `position` | Implemented | **UI (local bridge)** | Read-only reports; not physical measurement. |
| Connection diagnostics — `doctor` | Implemented | **UI (local bridge)** | The actual CLI doctor result is shown, without a simulated wizard. |
| Wait for printer conditions — `wait` | Implemented | **CLI only** | No web automation for ready/temperature thresholds. |
| Monitor to JSONL — `monitor` | Implemented | **CLI only** | Status/event logs and optional state-change snapshots. |
| Desktop state notifications — `notify` | Implemented | **UI (local bridge)** | Requires Linux `notify-send`; no web notifications. |
| Timelapse capture — `camera timelapse` | Implemented | **UI (local bridge)** | Interval-based still images; not synchronized to layers. |
| Get/open camera URL — `camera url/open` | Implemented | **CLI only** | UI provides a still-image modal, not a raw stream player. |
| Convert G-code to GX — `convert` | Implemented | **CLI only** as a separate control | Automatic conversion during upload is used, but no standalone UI converter. |
| Inspect local file metadata — `inspect` | Implemented | **CLI only** | CLI checks SHA-256, size and limited G-code metadata. |
| Start a stored remote job — `print REMOTE_NAME` | Implemented | **UI (local bridge)** | Stored files can be selected and printed after confirmation. |
| Pause, resume, cancel — `pause/resume/cancel` | Implemented | **UI (local bridge)** | The printer-management panel exposes these controls. |
| Fan on/off — `fan on/off` | Implemented | **UI (local bridge)** | Only 100%-on/off for the part-cooling fan, not the enclosure fan. |
| Rename printer — `printer rename` | Implemented | **CLI only** | No UI control. |
| Connection config — `config` | Implemented | **CLI only** | Host and camera settings managed on the host. |
| Named printer profiles — `profiles` / `--profile` | Implemented | **UI (local bridge)** | Named CLI connection profiles are managed separately from the slicer profile. |
| CLI help — `help` | Implemented | **CLI only** | Full CLI documentation is external to the web UI. |
| Separate FFAD4Manager slicer launcher — `slicer` | Implemented in FFAD4Manager | **Not used by this web app** | The CLI ships its own separately bundled local slicer UI; this repository uses `npm run local` and its own bridge. |
| OrcaSlicer post-processing upload hook | Implemented separately | **Not integrated** | Available in FFAD4Manager for OrcaSlicer, not called by this web app. |
| Continuous authenticated camera streaming in this UI | Not provided by this integration | **Not available** | Only on-demand JPEG snapshots are implemented here. |
| End-to-end uploaded-file integrity verification | Not implemented | **Not available** | M661 confirms listed filename, not the file's stored content/size. |
| Physically verified unattended print start / guaranteed no-start upload | Not established | **Not guaranteed** | Printer firmware side effects and GX compatibility require supervised real-world validation. |

The CLI has broader capabilities than this web UI. For details, flags and precise safety conditions, consult the [full FFAD4Manager command reference](https://github.com/spidey000/FFAD4Manager/blob/main/docs/CLI.md).

**Printer Manager:** tap the top-right AD4 status pill. The management screen reflects real CLI results only; GitHub Pages has no printer API. [Functionality and safety notes](docs/PRINTER_MANAGER.md).

## Local printer workflow

1. On the local server, confirm `ffadv4manager status --json` works and the printer is ready. Check the nozzle, bed, material, filament and printer-side conditions yourself.
2. Import a 3D file and adjust process/filament parameters. Select **Slice** or enable **Auto slice**.
3. Review the toolpath preview, estimated time, layers, and generated output. The preview simulation does not control the physical printer.
4. Choose **Upload only** to invoke the CLI without its explicit start flag, or **Print** to request an upload followed by a start. Both actions contact real hardware; supervise the printer.

**Important:** Upload-only intentionally omits M23/M24, but M601 S1 has undocumented firmware behavior; it cannot be advertised as a universal physical no-start guarantee. The filename-verification step checks M661 listing only. Automatic GX conversion does **not** correct incompatible G-code commands. Do not assume an accepted upload/start response proves a successful, safe print.

## Architecture, limits and safety

- **Static demo:** GitHub Pages hosts only the browser slicer. The `/api/printer/*` routes do **not** exist on Pages; a static site cannot reach your local printer through those paths.
- **Local bridge:** `server/ad4_bridge.py` serves `dist/` and exposes the allowlisted endpoints used by Printer Manager (state, discovery, files, job commands, diagnostics, snapshots, timelapse, Linux notifications, CLI connection profiles and uploads). It runs `ffadv4manager` via subprocess without a shell and listens only on `127.0.0.1:8765` by default. [Endpoint and safety details](docs/PRINTER_MANAGER.md).
- **Access control:** This bridge is for local trusted use. It has no user login/authentication; do not expose it directly to the LAN, Internet or a public reverse proxy. A phone on another device cannot open the loopback address of your computer. Secure remote access requires a separately designed authenticated setup.
- **Browser requirements:** The viewer needs WebGL. GitHub Pages cannot set isolation headers needed for `SharedArrayBuffer`; the slicer may fall back to a single-threaded worker.
- **Slicing profile:** This app pins the bundled `Flashforge Adventurer 4 Series 0.4 Nozzle` preset for slicing. The new discovered-printer list and CLI connection profiles select a command target; they do not change slicer machine presets.
- **Hardware testing:** We can validate builds and the deployed browser UI automatically; we cannot claim the physical print protocol is verified across printer firmware versions.

## Developer notes

`Viewport`, `SettingsPanel` and `useSlicer` share the same settings. The responsive styling is injected into the viewer's open Shadow DOM. The [toolpath control bridge](docs/REPRODUCCION_TRAYECTORIA.md) drives the actual upstream Preview inputs rather than a second renderer. If `three-slicer-viewer` changes its internal test IDs, re-test layer and movement scrubbing.

The GitHub Pages build deploys automatically from `main` using GitHub Actions. A post-deployment Chromium test checks the empty-state card at several mobile widths and opens the printer manager at 390px. Run `npm run build` to check the production bundle.

## Credits and licenses

This application integrates [Three Slicer](https://github.com/kimgh06/Three_Slicer): `three-slicer` is AGPL-3.0-or-later and `three-slicer-viewer` is MIT. Printer communication is provided by the separate [FFAD4Manager](https://github.com/spidey000/FFAD4Manager) project (GPL-3.0-or-later). This repository is distributed under AGPL-3.0-or-later. See [LICENSE](LICENSE) and the relevant upstream notices.
