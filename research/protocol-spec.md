# EnviroVent ATMOS PIV — local control protocol spec

**Status:** reverse-engineered from the `com.envirovent.myandroid` v1.9 (build 43)
Android app and **confirmed live** against a real unit (`192.168.1.50`, unit
softwareVersion `2.4`) on 2026-07-16. Unofficial; for personal interoperability.

Source of truth: decompiled classes under `com.envirovent.myapp` — chiefly
`service/implementation/JSONStringSocketService`, `api/implementation/PivUnitApi`,
`api/result/piv/PivGetCurrentSettingsResult`, `api/result/BaseResult`,
`ui/model/Piv/PivHomeUnitSettings`, `ApplicationConstants`, `ServiceDiscoveryService`.

---

## 1. Transport

| Property | Value |
|---|---|
| Protocol | **Plaintext JSON over a raw TCP socket** (no HTTP, no TLS, no encryption, no checksum) |
| Port | **TCP 1337** (`ApplicationConstants.UnitPort`) — networked *and* AP mode |
| Request | A single JSON object, UTF-8 bytes, written once. No length prefix, no delimiter/newline required |
| Response | A single JSON object, written back on the same socket |
| Connection model | **One request per connection**, and the unit accepts **only one client at a time**. Connect → send → read → close |
| Read termination | App reads 1024-char chunks until a read returns `< 1024` chars (i.e. the whole JSON arrives, typically in one segment; responses are a few hundred bytes) |
| Timeout | `SocketTimeout = 10000 ms` |
| Concurrency guard | App serializes all requests through a global lock (`MyLock.mAccessLock`) |

**Consequences for a client (and for Home Assistant):**
- Never hold the socket open; do one request/response per connection and close.
- The unit serves **one** TCP client at a time — the phone app and any other client
  **cannot be connected simultaneously**. Poll gently and back off on failure.
- Do **not** scan/hammer it. A concurrent port scan against this single-client
  device gives false results (this is how port 1337 was initially missed).

## 2. Discovery

- The unit advertises itself via **mDNS/DNS-SD, service type `_http._tcp`**
  (`ApplicationConstants.ServiceType`). The app browses with `NsdManager`
  (`PROTOCOL_DNS_SD`).
- The app uses the resolved **host** (IP) but **ignores the SRV port** — it always
  connects on the hardcoded **1337**. (Confirmed: `getPort()` is never called; port
  1337 is validated live.)
- Discovery is **name-agnostic** — there is no `ENVIROVENT*` name filter in the app;
  it probes each `_http._tcp` responder with `GetCurrentSettings` and treats any
  reply whose `unitType` is `"PIV"`/`"MVHR"` as a unit.
- **AP / direct-connect mode** (initial Wi-Fi provisioning, phone on the unit's own
  SoftAP): host `192.168.1.1`, port `1337`.
- **Home Assistant:** offer manual host entry (default `192.168.1.50`, port `1337`)
  and optionally zeroconf discovery on `_http._tcp` + a `GetCurrentSettings` probe
  that checks `unitType == "PIV"` (mirroring the app). The unit's mDNS instance name
  (reverse-DNS shows `ENVIROVENT-XXXX`) is firmware-set and not needed for control.

## 3. Message envelope

Every **request** is `{"command": "<Name>", ...}`.
Every **response** carries the `BaseResult` envelope:

| Key | Type | Meaning |
|---|---|---|
| `success` | int `0/1` | `1` = command succeeded (only field checked on writes) |
| `noresponse` | int `0/1` | present when the unit produced no response (read only if `success!=1`) |
| `error` | string | error text; observed as `""` on success (always present) |

**All booleans on the wire are integers `0/1`** (`BaseResult.getBoolean` = `getInt==1`).

## 4. Read commands

### `GetStatus` — `{"command":"GetStatus"}`
For PIV this returns **only the envelope** (the app's `GetStatusResult` parses no
payload and nothing in the PIV UI calls it). **Do not use it for status.**

### `GetCurrentSettings` — `{"command":"GetCurrentSettings"}`  ← the real status/read
Returns the full state. Live example (real unit):

```json
{
  "success": 1, "error": "", "unitType": "PIV", "softwareVersion": "2.4",
  "settings": {
    "airflow":      { "mode": "SET", "value": 4, "active": 1 },
    "boost":        { "enabled": 0, "mins": 20 },
    "boostInput":   { "enabled": 0 },
    "filter":       { "remainingDays": 1813, "resetMonths": 60 },
    "heater":       { "autoActive": 1, "temperature": 10 },
    "summerBypass": { "active": 1, "summerShutdown": 1, "temperature": 25 },
    "kickUp":       { "active": 1 },
    "spigot":       { "type": 1, "canChange": 1 },
    "hoursRun":     6346
  },
  "airflowConfiguration": { "maps": [
    {"mark":1,"percent":8},{"mark":2,"percent":30},{"mark":3,"percent":44},
    {"mark":4,"percent":57},{"mark":5,"percent":74},{"mark":6,"percent":100} ] }
}
```

#### Field reference

| JSON path | Type | Meaning | Safe to write? |
|---|---|---|---|
| `unitType` | string | `"PIV"` (case-insensitive). Identifies the unit family | read-only |
| `softwareVersion` | string | Unit firmware version (e.g. `"2.4"`). *App ignores it; good for device info* | read-only |
| `settings.airflow.mode` | string | `"SET"` = fixed preset, `"VAR"` = variable %. (Parser: `"var"`→variable, else preset) | write |
| `settings.airflow.value` | int | preset speed **1..maxPreset** in SET mode; **percentage** in VAR mode | write |
| `settings.airflow.active` | int 0/1 | fan currently moving air | read-only |
| `settings.boost.enabled` | int 0/1 | boost mode currently on | via `SetBoost` |
| `settings.boost.mins` | int | boost run-on duration (minutes) | write (home) |
| `settings.boostInput.enabled` | int 0/1 | hardwired boost switch input active | read-only |
| `settings.filter.remainingDays` | int | **filter days remaining** (`0` ⇒ change filter) | read-only (reset via command) |
| `settings.filter.resetMonths` | int | filter period in months | write (home) |
| `settings.heater.autoActive` | int 0/1 | auto (comfort) heater enabled | write (home) |
| `settings.heater.temperature` | int °C | heater setpoint | **installer only** |
| `settings.summerBypass.active` | int 0/1 | summer bypass currently active (drives "Summer Mode" indicator) | read-only |
| `settings.summerBypass.summerShutdown` | int 0/1 | summer mode enabled | via `SetSummerBypass` / home |
| `settings.summerBypass.temperature` | int °C | summer setpoint | **installer only** |
| `settings.kickUp.active` | int 0/1 | kick-up active | read-only |
| `settings.spigot.type` | int | `1` single, `2` twin | **installer only** |
| `settings.spigot.canChange` | int 0/1 | whether spigot may be changed | read-only |
| `settings.hoursRun` | int | total run hours | read-only |
| `airflowConfiguration.maps[]` | array | `{mark(1-based), percent}` calibration points | read-only |

**Power / online:** there is **no** explicit power field. The app treats the unit
as on/online whenever a non-error `GetCurrentSettings` reply is received. So
"available" == reachable + `success==1`.

**No measured temperatures** are reported — `heater.temperature` /
`summerBypass.temperature` are *setpoints*, not sensor readings.

## 5. Airflow model (presets ↔ percentages)

`airflowConfiguration.maps` is the fan curve. The app:
1. reads all points (subtracting 1 from `mark`, so internally 0-based),
2. takes the **first** point's `percent` as the variable-mode **min %** and the
   **last** as the **max %**,
3. strips the first and last, leaving the **selectable presets**.

For the live unit (`8,30,44,57,74,100`):
- variable-mode range: **8 %..100 %**, step 1 %.
- presets → `value` **1..4** = **30 / 44 / 57 / 74 %** (this unit has **4 fixed speeds**).

Writing airflow (via `SetHomeSettings`):
- preset: `airflow.mode="SET"`, `airflow.value=<1..maxPreset>`
- variable: `airflow.mode="VAR"`, `airflow.value=<percent within min..max>`

## 6. Write commands (resident-safe set)

Responses are all just the envelope (`{"success":1,...}`); the `Set*Result` classes
add no fields. Booleans are int `0/1`.

| Command | Request | Effect |
|---|---|---|
| `SetBoost` | `{"command":"SetBoost","enabled":0\|1}` | boost mode on/off (**most reversible** — use for first write test) |
| `SetSummerBypass` | `{"command":"SetSummerBypass","enabled":0\|1}` | summer mode on/off |
| `FilterMaintenanceComplete` | `{"command":"FilterMaintenanceComplete"}` | reset filter counter (→ `resetMonths*30` days) |
| `SetHomeSettings` | *whole home block, see below* | airflow, auto-heater, boost duration, filter period, summer on/off |

### `SetHomeSettings` — **read-modify-write** (rewrites the entire home block)

```json
{"command":"SetHomeSettings","settings":{
  "airflow":      {"mode":"VAR"|"SET","value":<int>},
  "heater":       {"autoActive":0|1},
  "boost":        {"mins":<20|40|60|720>},
  "filter":       {"resetMonths":<12|24|36|48|60>},
  "summerBypass": {"summerShutdown":0|1}
}}
```

To change one field, first `GetCurrentSettings`, then resend this block with all
other fields set to their current values. It contains **no** temperature/spigot keys,
so it cannot alter installer setpoints. (Note: boost *on/off* is not here — use
`SetBoost`; this block only sets boost *duration*.)

## 7. Installer / commissioning commands — **excluded from v1** ⚠️

The unit does **not** authenticate these — the app's installer access code is a
**client-side UI gate only** (`ValidInstallerAccessCode`, never sent on the wire).
Treat them as dangerous; keep them out of v1 (or behind an explicit, default-off flag).

- `SetInstallerSettings` — superset of home block **plus** `heater.temperature`,
  `summerBypass.temperature`, `spigot.type`.
- `SetSpigotType` — `{"command":"SetSpigotType","type":1|2}` (Gson-serialized).
- `RestoreHomeSettingsToFactoryDefaults` / `RestoreInstallerSettingsToFactoryDefaults`
  / `RestoreCommissioningSettingsToFactoryDefaults` — factory resets.

## 8. Value ranges & defaults

| Control | Values | JSON | Class |
|---|---|---|---|
| Airflow preset speed | `1..maxPreset` (unit: 4) | `airflow.mode="SET"`, `airflow.value` | resident |
| Variable airflow % | `min..max` (unit: 8..100), step 1 | `airflow.mode="VAR"`, `airflow.value` | resident |
| Boost on/off | `0/1` | `SetBoost.enabled` | resident |
| Boost duration | `20, 40, 60, 720` min | `SetHomeSettings … boost.mins` | resident |
| Auto heater | `0/1` | `heater.autoActive` | resident |
| Summer mode | `0/1` | `SetSummerBypass.enabled` / `summerBypass.summerShutdown` | resident |
| Filter period | `12, 24, 36, 48, 60` months | `filter.resetMonths` | resident |
| Filter reset | — | `FilterMaintenanceComplete` | resident |
| Heater temp | `5..15 °C` (default 10) | `heater.temperature` | **installer** |
| Summer temp | `18..28 °C` (factory ~25) | `summerBypass.temperature` | **installer** |
| Spigot type | `1` single / `2` twin | `spigot.type` | **installer** |

Boost-mins and filter-months are discrete slider positions; anything else falls back
to the lowest (`20` / `12`).

## 9. Constants (from `ApplicationConstants`)

`UnitPort=1337`, `SocketTimeout=10000 ms`, `ScheduledTaskInterval=15` (poll cadence,
seconds — used for the app's status poll), `UnitConnectionFailureThreshold=5`
(mark offline after 5 consecutive no-responses), `UnitConnectionFailureRediscoverThreshold=3`,
`MaxResolveRetryAttempts=3`, `ServiceType="_http._tcp"`, AP default `192.168.1.1`.
Installer gate `ValidInstallerAccessCode` is a fixed client-side code, never sent to
the unit. A vendor cloud backend exists for account/content only — **not** used for
unit control.

## 10. Open items to confirm live in Phase 3

- Exact preset `value` numbering on a **write** (read shows `value=4` at top preset;
  confirm `SetHomeSettings airflow.value=1..4` selects the expected speeds).
- Whether the unit rejects out-of-range values or clamps them.
- mDNS instance name string (for optional HA zeroconf matching).
