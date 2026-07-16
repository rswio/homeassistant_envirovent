# Deploying to Home Assistant OS + smoke test

Three ways to install; pick one. The integration is a standard
`custom_components/envirovent_atmos/` folder — nothing else needs copying.

> **Before you start:** close the **myenvirovent phone app**. The unit accepts only
> **one** connection at a time, so the app and Home Assistant can't both talk to it.

## Option A — HACS custom repository (recommended, gets updates)

1. Push this repo to GitHub (see *Updates* below).
2. In HA: **HACS → ⋮ → Custom repositories** → paste the repo URL, category
   **Integration** → **Add**.
3. Find **EnviroVent ATMOS** in HACS, **Download**, then **restart Home Assistant**.

## Option B — Samba share (quickest one-off)

1. Install/enable the **Samba share** add-on (Settings → Add-ons).
2. From Finder: **Go → Connect to Server** → `smb://192.168.0.x` (your HA box) →
   open the **config** share.
3. If it doesn't exist, create a `custom_components` folder inside `config`.
4. Copy the whole **`custom_components/envirovent_atmos/`** folder from this repo
   into `config/custom_components/`. You should end up with
   `config/custom_components/envirovent_atmos/manifest.json` (and the `atmos/`
   subfolder, platforms, `translations/`, etc.).
5. **Restart Home Assistant** (Settings → System → top-right power → Restart).

## Option C — Advanced SSH & Web Terminal add-on (scp)

1. Install the **Advanced SSH & Web Terminal** add-on, set a password/key, note its
   port (the add-on's *Configuration* tab — often `22`; **not** the HA UI port).
2. From the Mac, in this repo's root:
   ```bash
   scp -r -P <ssh_port> custom_components/envirovent_atmos \
       root@192.168.0.x:/config/custom_components/
   ```
   (Create `/config/custom_components` first via the add-on terminal if missing:
   `mkdir -p /config/custom_components`.)
3. **Restart Home Assistant.**

## Add the integration

1. **Settings → Devices & Services → + Add Integration →** search **“EnviroVent
   ATMOS”**.
2. Enter the unit's IP, e.g. **`192.168.1.50`** — your unit's reserved address (port
   defaults to **1337** — leave it).
   The unit may also appear as a **discovered** integration to click *Configure* on.
3. It validates by reading the unit and confirming it's a PIV, then creates the
   device with ~18 entities.

## Smoke test (2 minutes)

Run through this once; it exercises a read and both write paths.

- [ ] **Device present:** Settings → Devices & Services → **EnviroVent ATMOS** →
      the device shows **~18 entities** and *sw 2.4* (or your firmware).
- [ ] **Reads match the app:** open the myenvirovent app briefly and compare
      **Filter days remaining**, **Hours run**, current **Airflow %** and speed, then
      **close the app again**.
- [ ] **Boost (most reversible write):** toggle the **Boost** switch **on** → the fan
      note/boost should reflect it → toggle **off**. (Boost also auto-expires.)
- [ ] **Speed:** on the **Airflow** fan card, pick a different preset (e.g. Speed 3) →
      you should hear/see airflow change → set it back to Speed 4.
- [ ] **Variable airflow:** drag the fan **percentage** slider → airflow follows
      (this switches the unit to variable mode; pick a preset again to return to fixed).
- [ ] **Unavailability is graceful:** open the phone app and leave it on the status
      screen for a minute — HA entities may briefly go *unavailable* (single‑client),
      then recover once you close the app. No error spam.
- [ ] **Poll interval (optional):** Devices & Services → EnviroVent ATMOS →
      **Configure** → change the interval (default 30 s, min 15 s).

## Logs / troubleshooting

- **Settings → System → Logs** (search `envirovent_atmos`), or the file
  `config/home-assistant.log`.
- Enable debug logging (`configuration.yaml`, then restart or reload YAML):
  ```yaml
  logger:
    logs:
      custom_components.envirovent_atmos: debug
  ```
- **Can't connect / entities unavailable:** the phone app is probably connected —
  close it. Confirm the IP is right and reserved in DHCP. A one-off
  `Reload` (device menu → ⋮ → Reload) re-tries.

## Updates

- **HACS:** bump `version` in `custom_components/envirovent_atmos/manifest.json`,
  commit, and create a **git tag** that matches (e.g. `v0.1.1`) — HACS shows tagged
  releases as updates.
  ```bash
  git tag v0.1.0 && git push --tags
  ```
- **Manual:** re-copy the `envirovent_atmos` folder (Option B/C) and restart.
