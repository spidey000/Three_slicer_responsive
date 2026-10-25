# Secure worldwide access: Cloudflare Tunnel + Access

This is the deployment runbook for accessing **ThreeSlicer Responsive and its Adventurer 4 Printer Manager from anywhere in the world** using a normal browser, without opening inbound ports or requiring the user to join the home LAN.

**Readiness warning — action required:** the code in this repository currently provides a *local-only* printer bridge. The live GitHub Pages URL is a static slicer demo, not a remote printer controller. **Do not publish the current local bridge unchanged.** Remote mode, origin-side Cloudflare Access token validation, and strict public Host/Origin handling must be implemented and tested first. The copy/paste agent prompt at the [top of the README](../README.md) is intended to perform that work.

## 1. Target topology

```text
Remote phone or laptop
       |
       | HTTPS (same public hostname for UI and API)
       v
Cloudflare Access login (only explicitly approved identities)
       |
Cloudflare Tunnel ingress ("Protect with Access" required)
       |
       v
cloudflared on the trusted Linux host
       |
       | http://127.0.0.1:8765 (private loopback hop only)
       v
ThreeSlicer protected HTTP origin + static dist/ + /api/printer/*
       |
       | Subprocess invocation: FFAD4Manager CLI
       v
FlashForge Adventurer 4 over home LAN (TCP 8899; camera HTTP 8080)
```

No public port forwarding for 8765, 8899, 8080 or any other printer service. The Cloudflare tunnel connector establishes an outbound connection. This is **Cloudflare Access (user login)** in front of a **self-hosted public hostname**; it is not a requirement for visitors to install WARP or a VPN client.

## 2. Inventory before touching Cloudflare

Collect and confirm (do **not** publish actual values in source code, issues, comments, screenshots or build logs):

| Setting | Example / explanation |
| --- | --- |
| `PUBLIC_FQDN` | An exact, dedicated hostname such as `printer.example.com`; do not assume the user's actual domain |
| `PUBLIC_ORIGIN` | `https://printer.example.com` (scheme + hostname, no path) |
| `ACCESS_TEAM_DOMAIN` | Cloudflare Access team domain supplied by the user's account |
| `ACCESS_AUD` | Audience tag from the exact Cloudflare Access app |
| Authorized identity | User-confirmed email or IdP group restricted to the intended person(s) |
| Tunnel | Existing named Cloudflare tunnel or a newly approved dedicated tunnel |
| Home Linux host | The computer that will run **both** cloudflared and ThreeSlicer origin |
| Printer IP | Real private IPv4 address, confirmed by the owner / read-only CLI discovery |
| LAN connectivity | Linux host can reach the selected Adventurer 4; browser devices do not reach the printer directly |

Inspect existing `cloudflared` services, ingress routes, Access apps, DNS records and unrelated local services. Preserve them. Require explicit approval before editing Cloudflare routing, Access policies or host service files.

## 3. Install the local prerequisites first

Use a dedicated directory and a Python virtual environment. The following commands assume a clean parent workspace; adapt paths for existing installations without overwriting local edits.

```bash
git clone https://github.com/spidey000/Three_slicer_responsive.git
git clone https://github.com/spidey000/FFAD4Manager.git
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ./FFAD4Manager

# Network discovery and status are read-only; ask before changing printer config.
ffadv4manager discover --json
ffadv4manager config set --host PRINTER_LAN_IP
ffadv4manager status --json

cd Three_slicer_responsive
npm ci
npm run build
npm run local
```

The unmodified local origin is `http://127.0.0.1:8765/Three_slicer_responsive/`. Verify its static assets and `GET /api/printer/status`. This is **only a local preflight check**, not remote deployment completion.

Printer actions must be initiated by the owner after explicitly reviewing the target device and job. The status check alone does not require a physical action.

## 4. Required origin changes **before** creating a public route

`server/ad4_bridge.py` currently has the following limitations:

- Its `origin_ok()` accepts only a localhost `Host` and local development `Origin` on POSTs; real public-hostname requests will fail rather than work remotely.
- It does not validate `Cf-Access-Jwt-Assertion` and does not authenticate the static HTML, JavaScript/WASM, status, files, camera, discovery, profile, diagnostics, timelapse or printer-control APIs.
- Its lack of origin authentication means Tunnel-level login **must not** be treated as a substitute for reviewing origin authorization, particularly for hardware-changing endpoints.

**Implementation contract for the coding agent (not a claim that it already exists):**

1. Introduce an explicit `protected remote mode` while keeping default local mode restricted to loopback. A remote-mode startup **must fail closed** if the exact public origin, Access team domain, app audience and approved identity configuration are missing or malformed.
2. Verify the signature of the `Cf-Access-Jwt-Assertion` (RS256 against the correct Cloudflare Access team JWKS), algorithm, token expiration and validity window, exact issuer, correct application `aud`, and an explicitly allowed identity/claim on **every** remote request, including assets and all API endpoints. Support automatic JWKS refresh when Access signing keys rotate. Missing/invalid/expired tokens and JWKS outages must deny, not allow, access.
3. Require exact approved public `Host`, enforce `https://PUBLIC_FQDN` as the permitted `Origin` for mutating browser requests and enforce CSRF protection; keep local Host/Origin rules for the local development use case. Do not use wildcard CORS. Do not simply replace the public `Host` with `localhost` or accept arbitrary forwarded headers to bypass these checks.
4. Preserve all existing Printer Manager API paths, methods, body types and same-origin browser fetches. Requests to `/api/printer/*` must travel through the **same exact hostname** as the app (no cross-origin printer endpoint, embedded LAN IP or bearer secrets in JavaScript).
5. Do not expose a general command executor. Preserve the current allowlisted CLI invocations, validated filenames, discovered private IPv4 selection, body-size limits and checks before sending hardware-changing actions. Ensure operations cannot be invoked without passing remote authentication checks.
6. Unit-/integration-test missing, invalid, expired, wrong-AUD, wrong-issuer, wrong-identity and forged JWTs. Test unauthorized GETs **and POSTs**, CSRF and public-host mismatch. Preserve the existing local smoke tests. Where possible, reuse the JWT verification approach in [FFAD4Manager's secure slicer bridge](https://github.com/spidey000/FFAD4Manager/blob/main/ffadv4manager/slicer_bridge.py), but **not** its distinct HTML application or its different API.
7. Do not point Cloudflare Tunnel at the service until these checks pass. **If secure remote mode cannot be implemented or verified, STOP and leave the app local-only.**

Any suggested environment variable names for the new origin mode must be implemented in code and covered by tests before they can be treated as supported installation settings. Do **not** assume FFAD4Manager's `CF_ACCESS_*` variables already work with this repository.

## 5. Create Access protection BEFORE the tunnel route

Using your own Cloudflare Zero Trust account and the owner's approval:

1. Navigate to **Zero Trust > Access controls > Applications**. Create a **self-hosted public hostname** app for exactly `PUBLIC_FQDN`. Protect the **whole hostname**, not just the UI path; all assets and `/api/printer/*` routes must require authentication.
2. Configure a narrow **Allow** policy for the owner's explicitly authorized human identity/identities (for example, exact email). Do not use `Everyone`, `Bypass`, unaudited organization-wide groups or wildcard exceptions.
3. Require your desired IdP login and session controls. For CLI/bot access, create a separate tightly scoped **Service Auth** policy/token **only if needed and explicitly approved**; never embed the client secret in browser-side JavaScript or the git repository.
4. Record the Cloudflare Access application audience (`AUD`), verified team domain and exact public hostname for the origin-mode configuration. Keep operational secrets in a restricted service secret store.
5. On the tunnel's published-application route, enable **Protect with Access** (the cloudflared JWT-validation option) for that same application/audience as an additional gate. Cloudflare documents this as validation by cloudflared before forwarding to the origin.
6. Only after the Access application and JWT verification route are ready, create/add the tunnel **published application** mapping `PUBLIC_FQDN -> http://127.0.0.1:8765` when `cloudflared` runs on the same host. Preserve all other routes and ensure a final catch-all 404 ingress rule.
7. Keep HTTPS on the public side. The HTTP hop shown above is local loopback between `cloudflared` and the origin; do not publish that hop as a direct LAN/WAN listener.

**Do not use GitHub Pages as the remote-control origin.** It serves a static copy without printer APIs. The protected production site is served by the local ThreeSlicer origin *through* Cloudflare, not by static Pages.

Official documentation:
- [Cloudflare Tunnel setup](https://developers.cloudflare.com/tunnel/get-started/)
- [Cloudflare Access self-hosted public application](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/self-hosted-public-app/)
- [Protect with Access / origin parameters](https://developers.cloudflare.com/tunnel/reference/origin-parameters/)
- [Cloudflare Access application tokens](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/application-token/)

## 6. Run the origin and tunnel as persistent services

Set up a dedicated, unprivileged account and a restartable service manager (for example `systemd`). Keep the origin bound to **`127.0.0.1`**, separate from the printer, with no direct public firewall or router forwarding.

A **service template only** (replace paths and install the protected-mode implementation first):

```ini
# /etc/systemd/system/threeslicer.service
[Unit]
Description=ThreeSlicer protected printer-management origin
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=threeslicer
Group=threeslicer
WorkingDirectory=/opt/threeslicer/Three_slicer_responsive
EnvironmentFile=/etc/threeslicer/secure.env
Environment=AD4_CLI=/opt/threeslicer/.venv/bin/ffadv4manager
ExecStart=/opt/threeslicer/.venv/bin/python /opt/threeslicer/Three_slicer_responsive/server/ad4_bridge.py
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=/opt/threeslicer

[Install]
WantedBy=multi-user.target
```

Run the service only after the protected remote mode exists and its environment contract has been implemented. Store secrets in an owner-restricted file (not in a world-readable unit, browser bundle, git checkout, app logs or CI artifacts). Check the unit's read/write permissions against the real FFAD4Manager config and profile paths; override paths or add appropriately scoped writable directories as needed.

Ensure the separate `cloudflared` connector service is healthy and enabled according to Cloudflare's supported installation instructions. Start both on reboot, monitor failures and keep software updated. Prefer access logs that do not expose printer details, Access assertions or service tokens.

## 7. Mandatory acceptance tests from a separate network

**No write-action test should execute printer hardware commands without explicit informed approval.** Use mocks/contract tests for all mutations.

| Check | Expected result |
| --- | --- |
| Anonymous browser at `https://PUBLIC_FQDN/` | Access login or denied, **not** the unprotected app |
| Anonymous `/api/printer/status` and write endpoints | Access denies; never proxy to the CLI |
| Authorized browser after login | App loads HTML, JS, CSS, workers/WASM and responsive UI |
| Authorized status and Printer Manager | Real read-only data returned, no demo/placeholder response when printer is connected |
| Authorized camera snapshot (optional) | Actual JPEG from the local CLI |
| Missing or tampered Access JWT at origin | Denied |
| Wrong audience, wrong issuer, expired or unauthorized identity | Denied |
| Cross-origin forged POST and invalid/missing Origin | Denied before running a CLI subprocess |
| Printer-target endpoints from non-Access path | No publicly reachable bypass |
| Bridge/tunnel restart and simulated connector outage | Fail closed and recover to a protected state |
| Browser on mobile data / another Wi-Fi | Private HTTPS portal works only after Access authentication |
| Upload, print, pause, resume, cancel or fan tests | **Do not run automatically**; owner-supervised only |

Check actual DNS routing, tunnel health and the user's authorized login, rather than inferring success from GitHub Actions or a local HTTP 200. If required credentials or account access are unavailable, document the manual Cloudflare steps and mark the deployment incomplete.

## 8. Known limitations

- **Current implementation:** no protected remote bridge in this repository at the time of this guide. This document is a deployment/implementation contract.
- **Static Pages vs production:** the Pages demo has no printer endpoints. Do not confuse `https://...github.io/Three_slicer_responsive/` with the protected production domain.
- **Per-browser presets:** custom process and filament profiles are stored in browser site storage. Browser/device sync is **not** implemented.
- **Upload size:** the app has a 100 MiB body limit; Cloudflare account plan request-body limits or timeouts may be lower. Verify limits before relying on large jobs.
- **Hardware verification:** upload without explicit start avoids M23/M24, but firmware-side behavior (including M601 S1) and GX compatibility are not universally confirmed. M661 only confirms the filename appears; a successful API response does not verify bytes or a physical print.
- **FFAD4Manager remote bridge is distinct:** `ffadv4manager slicer --require-access` uses its own web assets and `/api/print` routes, and is **not** a drop-in secure backend for ThreeSlicer Responsive's `/api/printer/*`.

Successful deployment means **Access-protected remote UI and APIs**, not unmonitored or automatically certified physical printing.
