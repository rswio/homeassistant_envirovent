# Phase 1 — Device probing findings

**Target:** EnviroVent ATMOS PIV (`SF-ATL-A`), IP `192.168.1.50`
**Date:** 2026-07-15/16
**Probing host:** a machine on the same LAN, able to reach the unit's subnet

> ## ⚠️ CORRECTION (after Phase 2 + live test)
> The control port is **TCP 1337**, **not 80**. My full-range scan reported "only
> port 80 open," but that was a **single-client scan artifact**: a 256-thread
> connect-scan against a device that accepts one TCP client at a time dropped the
> SYN for 1337 (and other ports), so it never showed as open. A clean *sequential*
> `{"command":"GetCurrentSettings"}` to `192.168.1.50:1337` returns valid PIV
> JSON; port 80 refuses. **Lesson: never trust an aggressive concurrent scan of a
> single-client embedded device — probe sequentially.** The protocol is **plaintext
> JSON over TCP/1337** (see [protocol-spec.md](protocol-spec.md)), not a binary
> protocol on 80. The rest of this document is preserved as the original
> (misleading) scan record.

## TL;DR

This is **NOT** a Blauberg/VENTS UDP/4000 device, and **NOT** an HTTP device. It is
an embedded unit that speaks **plaintext JSON over a plain TCP socket on port 1337**
(one request per connection, single client at a time). Black-box probing alone
mis-identified the port (see correction above); the schema was recovered by
decompiling the `myenvirovent` app (Phase 2) and confirmed live. Blauberg reference
libraries (pyEcoventV2 etc.) do **not** apply.

## What responded / didn't

| Test | Result |
|---|---|
| ICMP ping | **UP**, ~12–25 ms RTT, **TTL 254** (initial 255 ⇒ lightweight embedded IP stack, 1 router hop) |
| Reverse DNS (nmap) | Hostname **`ENVIROVENT-XXXX`** — vendor-set; `ACEE` suffix almost certainly MAC-derived |
| Full TCP scan (1–65535) | **Only `80/tcp` open.** Everything else closed/filtered |
| `80/tcp` — HTTP GET/HEAD/OPTIONS (1.0 & 1.1, various paths) | Connection accepted, **0 bytes returned** (≥20s). Not HTTP |
| `80/tcp` — server banner on connect | None (device stays silent, waits for client to speak) |
| `80/tcp` — TLS ClientHello | No response |
| `80/tcp` — Modbus-RTU & Modbus-TCP reads (F01/02/03/04, several slave IDs) | No response (see note on single-client below) |
| `80/tcp` — raw bytes / AT command / Blauberg header | No response |
| UDP/4000 Blauberg/BGCP frames (multiple IDs/pwds, read param 1) | **No reply** (off-subnet ⇒ can't broadcast; wrong device-ID also yields silence, so not 100% conclusive, but combined with everything else: not the protocol) |
| UDP discovery beacons: 48899 (HF-LPB100/USR), 30303 (Lantronix), 1900 SSDP, 5683 CoAP, 8899/6666/5577/8888 | No reply (most are broadcast-only listeners; I'm off-subnet) |

## The single-client constraint (important)

Port 80 accepts **one** TCP connection at a time. During probing:
- The first connections succeeded (accepted, held open, silent).
- Rapid subsequent connects were **refused**, and after heavy probing the device
  **stopped accepting new connections entirely** for a while (errno 35 / EAGAIN),
  while still replying to ICMP ping.

Implications:
1. **The HA integration and the phone app cannot both be connected at once.** The
   client must hold at most one connection, close it cleanly, and poll gently
   (this fits `iot_class: local_polling`).
2. Do **not** hammer the port. Back off on error; reconnect with delay.
3. After my probing the unit may briefly refuse the app until it times out the
   stale socket (self-recovers in a few minutes; a power-cycle also clears it).

## Device fingerprint / hardware guess

- TTL 255 initial + single-client silent TCP server + vendor hostname ⇒ a small
  **serial↔WiFi bridge / embedded module** fronting the unit's controller.
- `ENVIROVENT-XXXX` hostname convention (`<vendor><hex>`) matches how such modules
  set their DHCP name. Full MAC/OUI needs an **on-subnet ARP** — worth grabbing later
  to name the module vendor.
- The most likely wire protocol is a vendor UART frame (possibly Modbus-like)
  tunneled transparently over TCP/80, but the exact framing is unconfirmed.

## Conclusion & next step

Black-box probing has established **transport (TCP/80), single-client behavior,
and "not Blauberg / not HTTP"** — but not the frame format. The decisive next
step is **Phase 2: recover the protocol from the app**, via:
- a **pcap** of the phone app talking to the unit (ground-truth wire bytes), and/or
- **static decompilation** of `com.envirovent.myandroid` (command catalog, encoding,
  checksum).

Tooling installed and ready: `nmap`, `jadx 1.5.6`, `apktool 3.0.2`, OpenJDK 26,
Python 3.9. Internet egress available.
