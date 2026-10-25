# Install ThreeSlicer for worldwide printer access — copy this prompt into your AI agent

> **Copy the entire prompt below into a coding agent with terminal and repository access.** The goal is to use ThreeSlicer from a phone, tablet or computer **anywhere in the world** through a private HTTPS address protected by **Cloudflare Tunnel + Cloudflare Access**, while FFAD4Manager talks to the Adventurer 4 on the home LAN. This is **not** a localhost-only setup.

```text
ROLE
You are my deployment and security engineering agent. Build, install and verify
ThreeSlicer Responsive as a PRIVATE, always-on web application that I can reach
from any network worldwide (including mobile data) after Cloudflare Access login.
The FlashForge Adventurer 4 stays on my trusted local network.

REPOSITORIES
- This UI and current local bridge: https://github.com/spidey000/Three_slicer_responsive
- Printer CLI (including a SEPARATE Access-aware reference bridge):
  https://github.com/spidey000/FFAD4Manager
- Read README.md and docs/REMOTE_ACCESS.md before modifying anything.

SUCCESS CRITERIA
From a device outside my LAN, I can open https://MY_PRIVATE_HOSTNAME/
(or the application's /Three_slicer_responsive/ path), authenticate via
Cloudflare Access, use the actual slicer and Printer Manager, view real status
and authorized camera snapshots, and deliberately request CLI-supported printer
operations. Unauthenticated requests must never reach the origin or API.
No printer TCP/HTTP ports, web backend, or tunnel credentials are exposed publicly.

PRE-FLIGHT: do not assume remote operation already works!
The current ThreeSlicer server/ad4_bridge.py is a loopback-only local bridge:
- origin_ok() accepts only localhost Host/Origin for mutating requests.
- It DOES NOT validate Cloudflare Access JWTs.
- Its read-only GET routes do not perform authentication either.
Therefore simply pointing a Tunnel at port 8765 is NOT a working or sufficiently
hardened remote deployment. Implement and test remote-auth support first.
FFAD4Manager's own 'slicer --require-access' uses another web UI and different
endpoints; do not mistakenly substitute it for this repository's application.
You may reuse its verified Access-JWT approach as a reference, not its URL/API.

EXECUTION PLAN
1. Inspect both repositories, current commits, configuration, LAN connectivity,
   already-running cloudflared tunnels and Access apps, systemd services, and
   existing hostname routes. Preserve other services and uncommitted changes.
   Ask me for the exact public hostname, authorized human identity, access to
   the Cloudflare account, and permission before changes to Cloudflare/DNS,
   firewall, service configuration or any printer-affecting operation. Do not
   guess credentials, claim deployed access, or replace existing tunnel routes.
2. Check prerequisites: Linux with Python 3.9+ and venv/pip, Node.js 20+, npm,
   cloudflared, outbound Internet, a Cloudflare-managed domain, WebGL-capable
   client, and LAN access to the Adventurer 4. Clone or reuse the two repos.
   Install FFAD4Manager in an isolated venv (pip install -e ./FFAD4Manager),
   use 'ffadv4manager discover --json' if needed, get confirmation of the real
   printer IP, configure it, and test 'ffadv4manager status --json' (read only).
3. Build the actual ThreeSlicer repository (npm ci; npm run build). Confirm
   the local UI, same-origin /api/printer/* endpoints, Printer Manager and
   static assets work before enabling remote access.
4. Add a PROTECTED REMOTE MODE to THIS app's server/ad4_bridge.py, keeping its
   default loopback-only local mode working. In remote mode, require explicit
   public hostname/HTTPS origin and Cloudflare Access app configuration.
   Reject missing or incomplete security configuration at startup.
   Validate Cf-Access-Jwt-Assertion for EVERY public HTTP request, including
   GET /, /Three_slicer_responsive/*, camera, discovery, files, status and
   every API POST. Verify RS256 signature against the correct Cloudflare
   Access JWKS, expiry, issuer, audience and explicitly allowed identity;
   reject expired, forged and wrong-app tokens, and fail closed on key errors.
   Never trust a raw identity header without cryptographic verification.
   Enforce exact Host and HTTPS Origin checks on mutating requests, prevent
   cross-site request forgery, and avoid wildcard CORS. Preserve local behavior.
   Cover public routes and authentication with negative/positive tests.
   If you cannot implement this securely, STOP: keep the app local and report
   the blocker. Do not turn off origin checks or bypass authentication.
5. First create/configure a Cloudflare Access self-hosted PUBLIC-HOSTNAME app
   for the exact chosen FQDN. Restrict it to my approved identity; no public,
   broad-organization, wildcard or Bypass policy. Protect ALL paths, including
   /api/printer/* and static assets. For the tunnel public hostname, enable
   'Protect with Access' / Access JWT validation using the correct app AUD.
   Only AFTER protection is confirmed, add the Cloudflare Tunnel published
   application route for that hostname to http://127.0.0.1:8765 (provided
   cloudflared runs on the same machine). Preserve existing ingress rules and
   the default catch-all 404. Use the same origin for web UI and printer API.
   Do not port-forward the printer's TCP 8899, camera 8080, or server 8765.
6. Run this app's protected bridge and cloudflared as restartable services
   (for example systemd under a dedicated, low-privilege account). Bind the
   bridge only to 127.0.0.1. Store Access settings, tunnel credentials and
   private configuration in protected service/environment files, not Git,
   code, public logs or browser-side JavaScript. Reboot/restart checks must
   confirm that the services recover and security stays enabled.
7. Verify from an EXTERNAL network, not just the server itself:
   - Anonymous/unauthorized browsing and API calls are denied.
   - Authenticated browser access loads HTML, JS, WASM, Settings, and the
     Printer Manager under the public HTTPS hostname.
   - A valid Access session can call read-only status (and camera only with
     my approval); the printer state comes from FFAD4Manager.
   - Missing/invalid/expired/wrong-audience JWTs are rejected by the origin.
   - Cross-origin/malformed POST requests fail without running CLI commands.
   - A restart and a tunnel disconnect do not create an unprotected route.
   Never run actual upload, start, pause, resume, cancel, movement, heating,
   rename or fan commands as a test without my explicit informed approval.
8. Deliver a concise report with the public HTTPS URL, which Access identity
   is allowed, exact source revisions and code changes, CLI host selection,
   service start/stop/log/restart commands, all security checks performed,
   known limitations, and which parts were not verified on hardware. If
   Cloudflare account access or implementation is missing, mark deployment
   INCOMPLETE; do not claim success.

HARDWARE SAFETY
Upload-only omits explicit M23/M24 commands in the CLI path, but firmware-side
no-start behavior is not fully validated. M661 proves listed filename, not
file integrity. A successful HTTP response is not proof of actual printing.
The user must supervise initial real-world tests.

Refer to docs/REMOTE_ACCESS.md and the official Cloudflare Tunnel and Access
documentation for configuration; use currently supported Cloudflare settings.
```

---

# ThreeSlicer Responsive — private Adventurer 4 web slicer and management

A responsive slicer and printer-management web UI built on [Three Slicer](https://github.com/kimgh06/Three_Slicer) and [FFAD4Manager](https://github.com/spidey000/FFAD4Manager) for the **FlashForge Adventurer 4 (0.4 mm nozzle)**. **The intended production deployment is a private HTTPS site accessible worldwide through Cloudflare Tunnel and Cloudflare Access.** The included bridge currently works locally; a securely authenticated remote mode must be implemented and verified before publishing it.

**[Live slicer demo (no printer connection)](https://spidey000.github.io/Three_slicer_responsive/)** · **[Secure remote deployment guide](docs/REMOTE_ACCESS.md)** · **[Local development](docs/AD4_LOCAL.md)** · **[FFAD4Manager CLI reference](https://github.com/spidey000/FFAD4Manager/blob/main/docs/CLI.md)**

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

## Deployment: worldwide access through Cloudflare

<details>
<summary><strong>Remote deployment readiness — read before publishing</strong></summary>

| Component | Current status |
| --- | --- |
| WebGL slicer, Preview and Printer Manager | Implemented in this repository |
| FFAD4Manager bridge to LAN printer | Implemented, local-only |
| Cloudflare Tunnel hostname and Access app for this deployment | Must be configured in your Cloudflare account |
| Cloudflare Access token validation in this repository's bridge | **Not yet implemented** |
| Public HTTPS Host/Origin handling in this repository's bridge | **Not yet implemented** |
| Persistent protected bridge and cloudflared services | Must be installed/configured on the host |
| End-to-end authenticated remote control | **Not yet verified** |

The GitHub Pages URL is a public **slicer-only demo**, not the desired private printer-management portal. Do not expose the included, unauthenticated bridge by adding a Cloudflare Tunnel route until the protection and origin-validation steps in the agent prompt are implemented and tested.

</details>

The target architecture is:

```text
Phone / laptop anywhere (HTTPS)
           |
     Cloudflare Access
  (allowlisted identity)
           |
     Cloudflare Tunnel
  (Protect with Access)
           |
     127.0.0.1:8765
  Protected ThreeSlicer server
     (JWT + CSRF validation)
           |
     FFAD4Manager CLI
           |
  Home LAN -> Adventurer 4
```

A Cloudflare-managed hostname and approved login are required. **No public inbound ports and no exposure of printer TCP 8899 or camera 8080.** Put `cloudflared` on the same host as the loopback backend; use one same-origin site for the web UI and `/api/printer/*`.

**Installation path:** follow the [secure remote deployment guide](docs/REMOTE_ACCESS.md) or hand the [agent prompt at the top](#install-threeslicer-for-worldwide-printer-access--copy-this-prompt-into-your-ai-agent) to a coding agent. It includes the required backend changes, Cloudflare configuration, secure service installation, rejection tests and external-network verification. An automated agent must not claim the remote setup is finished until those checks pass.

### Local-only installation (development / initial checks)

Requirements: Linux, Node.js 20+, npm, Python 3.9+ and Python venv/pip; WebGL in the client browser. For printer functions the host must reach the printer over the home LAN.

```bash
# Run in a parent workspace directory, not inside either repository:
git clone https://github.com/spidey000/Three_slicer_responsive.git
git clone https://github.com/spidey000/FFAD4Manager.git
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ./FFAD4Manager
ffadv4manager discover --json                  # optional, read-only
ffadv4manager config set --host PRINTER_LAN_IP  # replace; use the correct address
ffadv4manager status --json                     # read-only connectivity check
cd Three_slicer_responsive
npm ci
npm run build
npm run local
```

Local browser URL: **http://127.0.0.1:8765/Three_slicer_responsive/**. This URL works only on the host itself. The bridge is deliberately bound to loopback; changing the listener to `0.0.0.0` is **not** the deployment solution. Use `AD4_HOST`, `AD4_CLI`, and `AD4_WEB_PORT` only as documented for the local bridge. For development, `npm run dev` proxies `/api` to port 8765 if the bridge is running.

## What FFAD4Manager can do — and what this web UI exposes

**Key:** **UI** = available in ThreeSlicer through its **currently local-only** printer bridge; these commands will be remotely reachable only after secure Access integration. **CLI only** = implemented by FFAD4Manager but not wired into this web UI; **not available** = not provided as described. None of these statuses guarantees a physical printer outcome.

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

- **Production goal:** authenticated private access from anywhere via Cloudflare Access and Cloudflare Tunnel. The built-in bridge currently has **no Access JWT validation**, and its current `origin_ok()` only allows localhost `Host`/`Origin` on writes. A Tunnel alone will not provide a working, acceptably secured remote system. See [remote deployment](docs/REMOTE_ACCESS.md).
- **Public demo:** GitHub Pages runs the browser slicer without `/api/printer/*`; it does not control a printer and is not the production portal.
- **Home origin:** `server/ad4_bridge.py` serves `dist/` and exposes the allowlisted Printer Manager APIs (status, discovery, files, uploads, job controls, diagnostics, snapshots, timelapse and CLI profiles). It invokes `ffadv4manager` without a shell and remains on `127.0.0.1:8765`; the printer is reached only through the host LAN. [Bridge and safety details](docs/PRINTER_MANAGER.md).
- **Remote security gates:** Cloudflare Access policies for the **entire exact hostname**; Cloudflare Tunnel **Protect with Access** JWT validation; origin JWT/identity verification with an exact HTTPS origin and Host allowlist; CSRF protection for actions; fail-closed configuration; no public backend bypass. Secrets remain on the host and must never be bundled into the UI.
- **Always-on runtime:** operate `cloudflared` and the protected ThreeSlicer backend as restartable services with limited privileges. The reference guide includes deployment acceptance and restart checks; no ready-made remote deployment is bundled yet.
- **Browser compatibility:** the viewer requires WebGL. Cross-origin isolation controls affect WebAssembly threading; check the installed slicer runtime independently from Access login.
- **Persistence:** custom process/filament profiles use browser-local storage, **not** cloud sync. Profiles saved in one browser/device are not automatically available on another device.
- **Physical safety:** printer firmware responses, M661 filename listings and HTTP success cannot prove content integrity or physical print completion. No automated write-action tests without informed approval.

## Developer notes

`Viewport`, `SettingsPanel` and `useSlicer` share the same settings. The responsive styling is injected into the viewer's open Shadow DOM. The [toolpath control bridge](docs/REPRODUCCION_TRAYECTORIA.md) drives the actual upstream Preview inputs rather than a second renderer. If `three-slicer-viewer` changes its internal test IDs, re-test layer and movement scrubbing.

The GitHub Pages build deploys automatically from `main` using GitHub Actions. A post-deployment Chromium test checks the empty-state card at several mobile widths and opens the printer manager at 390px. Run `npm run build` to check the production bundle.

## Credits and licenses

This application integrates [Three Slicer](https://github.com/kimgh06/Three_Slicer): `three-slicer` is AGPL-3.0-or-later and `three-slicer-viewer` is MIT. Printer communication is provided by the separate [FFAD4Manager](https://github.com/spidey000/FFAD4Manager) project (GPL-3.0-or-later). This repository is distributed under AGPL-3.0-or-later. See [LICENSE](LICENSE) and the relevant upstream notices.
