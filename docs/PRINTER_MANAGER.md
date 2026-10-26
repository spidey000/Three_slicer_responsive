# Printer Manager (mobile and desktop)

> **Worldwide remote access:** Printer Manager can operate through the self-hosted ThreeSlicer origin protected by Cloudflare Tunnel + Access. Configure **all four** required `CF_ACCESS_*` settings to enable signed origin JWT validation, and follow the [secure deployment instructions](REMOTE_ACCESS.md) before publishing a Tunnel route. The default configuration remains local-only; GitHub Pages is only a slicer demo.

Open the **AD4 / printer-status button** in the top right of ThreeSlicer to access the management screen. The panel reuses the project's lime accent (#a3e635), slate surfaces and existing responsive styles. The camera card offers an on-demand snapshot and an opt-in live MJPEG feed, proxied through the protected bridge.

## Actual functionality

This screen calls FFAD4Manager through the **local** Python bridge:

| Screen card | CLI commands | Notes |
| --- | --- | --- |
| Printer state and print progress | status --json | Reads actual telemetry, no demo values. Missing fields show “—”. |
| Current job | pause, resume, cancel | Enables actions based on observed print state; cancelling requires confirmation. |
| Discover/connect | discover --json, then --host | A new host must have been discovered with command port 8899. |
| Stored files | files --json, print REMOTE_NAME | Ten items per page, sortable by name/duration/upload date. Durations, temperatures and dates are indexed only for files uploaded via this bridge; unknown values show —. |
| Camera | camera snapshot, camera url | Snapshot or real MJPEG feed, proxied on the same authorized origin; the LAN camera URL is not exposed to clients. |
| Cooling | fan on, fan off | Part cooling only; no numerical fan speed control or enclosure fan control. |
| Diagnostics | doctor, info --json, position --json | Real CLI output; no made-up sensor/system health indicators. |
| Timelapse | camera timelapse FOLDER --interval 10 | Manual or opt-in per-print recording, server-side print-finish detection, H.264 MP4 encoding, HTML5 playback, MP4 download and deletion. Not layer-synchronized. |
| Notifications | notify --events paused,offline,printing,ready | Starts/stops the **host Linux desktop** notifier (notify-send). Not browser/phone push notifications. |
| Connection profiles | profiles list/add/delete, --profile | CLI printer **connection** profiles, **not** slicer speed/quality presets. |
| Upload | upload FILE or upload FILE --start | Uploads selected G-code/GX up to 100 MiB; starting requires confirmation. |

The original slicer functions, including its existing sliced-G-code upload/print buttons, remain unchanged.

## Running locally

Install FFAD4Manager and build this repository per [AD4_LOCAL.md](AD4_LOCAL.md). Install the system encoder on the bridge host with `sudo apt-get install ffmpeg`, then run npm ci, npm run build and npm run local.

Enable **Timelapse** next to **Auto slice** in the slicer's top toolbar (desktop) or bottom action bar (mobile). This preference is stored in the browser and applies when clicking **Print**, not **Upload only**. The same setting applies to Print/Upload & Print actions in Printer Manager. With automatic recording selected, the bridge checks FFmpeg availability before starting the job, then polls printer status itself every five seconds; two READY readings following a printing state finalize the recording, even if the browser disconnects. Pause leaves the recording active, while cancelling stops and finalizes it. Manual recording is also available in Printer Manager.

A finished session is encoded at 10 fps to an H.264/yuv420p MP4 with CRF 28 and fast-start metadata, then published atomically. Captured JPEGs are deleted **only after** a successful encoding; on failure, they are retained and the gallery displays the error. The next bridge startup retries unfinished conversions. The gallery streams MP4 with HTTP Range support for seeking. FFmpeg is required only on the bridge host, not on the mobile device or printer.

Open **http://127.0.0.1:8765/Three_slicer_responsive/** *on the bridge computer*. For development, npm run dev proxies API calls to the local bridge.

**GitHub Pages is a static website.** Its new manager UI is available but its cards correctly show the bridge as unavailable; it does not send commands to your printer. The Python bridge deliberately listens only on **127.0.0.1** without authentication. To use printer controls from a **phone**, an authenticated, encrypted, trusted remote-access setup is needed before making the bridge reachable from the phone. **Never forward port 8765 or 8899 on your router or expose them unauthenticated.**

## Caveats

- Printer firmware/CLI replies do not independently prove a motor/fan's physical effect.
- The existing CLI upload-only path omits M23/M24, but firmware behavior of M601 S1 is insufficiently documented to guarantee no physical start. Supervise the machine.
- A successful upload confirms only printer-side file *name* presence, not byte integrity.
- The automatic completion watcher requires the bridge process and printer-status connection to be available. It cannot reconstruct frames missing during a server outage. A hard reboot after capture can still salvage saved frames on next start; unobserved manual starts outside the bridge cannot follow the browser-only Timelapse toggle.
- Timelapses and upload metadata are stored on the bridge machine under `~/.local/share/three-slicer-ad4/` by default (`AD4_DATA_DIR` can override it). MP4s persist across restarts until deleted in the gallery; source frames are removed after successful conversion to save space. No cloud sync is provided.
- A Linux desktop session with working notify-send is required for notifications. Alerts are displayed on the bridge computer, not on the phone.
- No auxiliary/enclosure fan slider, remote printer-file rename/delete, Home-axes button, material metadata or estimated remaining time is shown. Existing printer-side files cannot supply duration, temperatures or dates unless previously uploaded through this bridge. The live camera feed is genuine MJPEG, not simulated.

Run python3 -m unittest discover -s tests -p 'test_printer_manager_bridge.py' to test the bridge with no actual printer. Hardware-dependent controls require supervised testing on your Adventurer 4.
