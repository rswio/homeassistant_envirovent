# Security Policy

## About this project

This is an **unofficial, community-maintained** Home Assistant integration for the
EnviroVent ATMOS PIV, built by reverse-engineering the unit's local protocol. It is
not affiliated with or endorsed by EnviroVent.

**Security-relevant design notes:**

- **Local only.** The integration talks to the ventilation unit over a plain TCP
  socket on your LAN. It makes no cloud calls, sends no telemetry, and stores no
  credentials or tokens.
- **No authentication exists in the device protocol.** The unit does not
  authenticate commands — anything on your network that can reach it can control it.
  This is a property of the device firmware, not of this integration. Treat the unit
  as an untrusted-network-exposed appliance: keep it off guest/IoT-hostile networks
  and do not port-forward it to the internet.
- **Installer / commissioning commands are deliberately not exposed.** The unit will
  accept commissioning writes (heater/summer setpoints, spigot type, factory reset)
  without any authentication. This integration only ever issues the safe resident
  controls. The bundled client can issue installer commands, but only when explicitly
  constructed with `allow_installer=True`, which the integration never does.

## Supported versions

The latest released version is the only supported version.

## Reporting a vulnerability

Please **do not open a public issue** for security problems.

Use GitHub's **private vulnerability reporting**:
*Security → Report a vulnerability* on this repository.

Include what you found, how to reproduce it, and the impact. I'll acknowledge as soon
as I reasonably can. This is a hobby project maintained in spare time — please set
expectations accordingly.

## Out of scope

- Vulnerabilities in the EnviroVent ATMOS firmware or the official `myenvirovent`
  app. Report those to EnviroVent.
- The lack of authentication in the device's own local protocol (documented above).
