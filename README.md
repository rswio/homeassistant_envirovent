# EnviroVent ATMOS — Home Assistant integration

Local control of an **EnviroVent ATMOS** positive‑input‑ventilation (PIV) loft unit
(`SF-ATL-A`, the app‑controlled *ATL‑A* variant) from Home Assistant, over your LAN.

> ⚠️ **Unofficial & reverse‑engineered. Use at your own risk.**
> EnviroVent publishes no API. This integration was built by reverse‑engineering the
> `myenvirovent` Android app and the unit's local protocol for personal
> interoperability. It is not affiliated with or endorsed by EnviroVent. It talks to
> your unit over a plain local TCP socket — no cloud, no telemetry. Commissioning /
> installer settings are deliberately **not** exposed (see *Safety* below).

## What it does

100% local (`iot_class: local_polling`) — the integration polls the unit on
**TCP port 1337** with a small JSON protocol. No internet, no cloud account needed.

### Entities

| Entity | Type | Notes |
|---|---|---|
| **Airflow** | `fan` | 4 fixed speeds as **preset modes** (`Speed 1‑4`) **and** a **percentage** slider for variable airflow. Selecting a preset uses the unit's `SET` mode; moving the slider uses `VAR` mode. The PIV runs continuously, so it cannot be turned "off". |
| **Boost** | `switch` | Boost mode on/off (auto‑expires on the unit's own timer). |
| **Auto heater** | `switch` | Enable/disable the auto comfort heater (target temp is installer‑only). |
| **Summer mode** | `switch` | Summer bypass shutdown on/off. |
| **Boost duration** | `select` | 20 / 40 / 60 / 720 minutes. |
| **Filter period** | `select` | 12 / 24 / 36 / 48 / 60 months. |
| **Reset filter counter** | `button` | Resets the filter‑change countdown. |
| **Filter days remaining**, **Hours run**, **Airflow %**, **Airflow mode**, **Heater setpoint**, **Summer setpoint** | `sensor` | Read‑outs (setpoints are diagnostic/read‑only). |
| **Airflow active**, **Boost input**, **Summer bypass**, **Kick up**, **Filter needs changing** | `binary_sensor` | Live status flags. |

## Requirements

- An ATMOS **ATL‑A** (app‑controlled) unit joined to your Wi‑Fi ("networked" mode).
- A **fixed/reserved IP** for the unit (reserve it in your router's DHCP so it never
  moves). You enter it in the config flow (or let mDNS discovery find it).
- Home Assistant **2025.1** or newer.

## Install (HACS — custom repository)

1. HACS → **⋮** → **Custom repositories**.
2. Add this repository's URL, category **Integration**, and add it.
3. Install **EnviroVent ATMOS**, then **restart Home Assistant**.
4. **Settings → Devices & Services → Add Integration → “EnviroVent ATMOS”**.
5. Enter the unit's IP (port defaults to `1337`). The unit may also be
   auto‑discovered via mDNS.

### Manual install

Copy `custom_components/envirovent_atmos/` into your HA `config/custom_components/`
directory and restart Home Assistant.

## Configuration

- **Host** – the unit's IP (reserve it in DHCP).
- **Port** – `1337` (default; only change if you know otherwise).
- **Polling interval** – *Settings → Devices & Services → EnviroVent ATMOS →
  Configure* (default 30 s, minimum 15 s).

### ⚠️ One connection at a time

The unit accepts **only one TCP client at a time**. If the **myenvirovent phone
app is open and connected**, Home Assistant's polls may fail intermittently (and
vice‑versa). Close the app when you're not using it. The integration polls gently
and backs off/retries on failure.

## Safety

- **Local only** — no cloud, no telemetry, no outbound traffic except to the unit.
- **Installer / commissioning writes are excluded.** The app's installer access code
  is only a client‑side UI gate — the unit itself does **not** authenticate
  installer commands (heater/summer target temperatures, twin‑spigot, factory
  restore). This integration exposes only the safe resident controls. The bundled
  client library *can* perform installer writes, but only if explicitly constructed
  with `allow_installer=True`; the integration never does.

## Troubleshooting

- **Won't connect / entities unavailable:** confirm the IP, that the unit is on the
  network, and that the phone app is **closed**. Logs: *Settings → System → Logs*
  (or `config/home-assistant.log`). Enable debug logging by adding to
  `configuration.yaml`:
  ```yaml
  logger:
    logs:
      custom_components.envirovent_atmos: debug
  ```
- **Wrong device found via discovery:** discovery validates the unit by asking it for
  its status and checking `unitType == "PIV"`; non‑PIV devices are rejected.

## How it works / protocol

The full reverse‑engineered protocol is documented in
[`research/protocol-spec.md`](research/protocol-spec.md). In short: plaintext JSON
objects over a one‑shot TCP connection to port 1337, e.g.
`{"command":"GetCurrentSettings"}` → the full unit state. A standalone, dependency‑free
Python client and CLI live in [`envirovent_atmos/`](envirovent_atmos/) (`python -m
envirovent_atmos.probe <ip>`); the integration bundles a copy under
`custom_components/envirovent_atmos/atmos/`.

## Screenshots

_(placeholder — add screenshots of the device page and fan card here)_

## License

MIT — see [LICENSE](LICENSE).
