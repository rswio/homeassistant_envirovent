#!/usr/bin/env python3
"""Dependency-free pcap / pcapng analyzer for the EnviroVent ATMOS RE work.

Extracts the TCP conversation with the unit (default 192.168.1.50:1337),
prints every application-layer segment in time order with direction, length,
hex and ascii, inserts a separator on >1s idle gaps (to delineate app actions),
and prints a de-duplicated per-direction byte stream for spotting fixed framing.

Handles classic pcap (LE/BE) and pcapng; link types Ethernet(1), RAW(101),
NULL/BSD-loopback(0), Linux SLL(113) and SLL2(276). IPv4 + IPv6.

Usage:
  python3 pcap_analyze.py <file.pcap[ng]> [host=192.168.1.50] [port=1337]
"""
import struct
import sys

HOST = "192.168.1.50"
PORT = 1337


def hexd(b):
    return " ".join(f"{x:02x}" for x in b)


def asc(b):
    return "".join(chr(x) if 32 <= x < 127 else "." for x in b)


# ---------------- link/ip/tcp decoding ----------------

def parse_ip_tcp(data, linktype):
    """Return (src_ip, dst_ip, sport, dport, payload) or None."""
    # strip link layer to get to IP
    if linktype == 1:            # Ethernet
        if len(data) < 14:
            return None
        eth = struct.unpack(">H", data[12:14])[0]
        off = 14
        if eth == 0x8100:        # 802.1Q VLAN
            eth = struct.unpack(">H", data[16:18])[0]
            off = 18
        if eth == 0x0800:
            return parse_ipv4(data[off:])
        if eth == 0x86DD:
            return parse_ipv6(data[off:])
        return None
    if linktype == 101:          # RAW IP (PCAPdroid default)
        if not data:
            return None
        v = data[0] >> 4
        return parse_ipv4(data) if v == 4 else parse_ipv6(data) if v == 6 else None
    if linktype == 0:            # NULL / BSD loopback (4-byte family)
        if len(data) < 4:
            return None
        fam = struct.unpack("<I", data[:4])[0]
        if fam in (2,):
            return parse_ipv4(data[4:])
        if fam in (24, 28, 30):
            return parse_ipv6(data[4:])
        # try both
        r = parse_ipv4(data[4:])
        return r
    if linktype == 113:          # Linux cooked SLL
        if len(data) < 16:
            return None
        proto = struct.unpack(">H", data[14:16])[0]
        if proto == 0x0800:
            return parse_ipv4(data[16:])
        if proto == 0x86DD:
            return parse_ipv6(data[16:])
        return None
    if linktype == 276:          # Linux cooked SLL2
        if len(data) < 20:
            return None
        proto = struct.unpack(">H", data[0:2])[0]
        if proto == 0x0800:
            return parse_ipv4(data[20:])
        if proto == 0x86DD:
            return parse_ipv6(data[20:])
        return None
    # unknown: guess raw IP
    if data:
        v = data[0] >> 4
        if v == 4:
            return parse_ipv4(data)
        if v == 6:
            return parse_ipv6(data)
    return None


def ipv4_str(b):
    return ".".join(str(x) for x in b)


def parse_ipv4(d):
    if len(d) < 20:
        return None
    ihl = (d[0] & 0x0F) * 4
    if d[9] != 6:                # protocol TCP
        return None
    total = struct.unpack(">H", d[2:4])[0]
    src = ipv4_str(d[12:16])
    dst = ipv4_str(d[16:20])
    ip_payload = d[ihl:total] if total and total <= len(d) else d[ihl:]
    return parse_tcp(src, dst, ip_payload)


def parse_ipv6(d):
    if len(d) < 40:
        return None
    nexthdr = d[6]
    plen = struct.unpack(">H", d[4:6])[0]
    src = ":".join(f"{d[8+i]:02x}{d[9+i]:02x}" for i in range(0, 16, 2))
    dst = ":".join(f"{d[24+i]:02x}{d[25+i]:02x}" for i in range(0, 16, 2))
    if nexthdr != 6:
        return None
    payload = d[40:40 + plen] if plen else d[40:]
    return parse_tcp(src, dst, payload)


def parse_tcp(src, dst, d):
    if len(d) < 20:
        return None
    sport, dport = struct.unpack(">HH", d[0:4])
    doff = (d[12] >> 4) * 4
    payload = d[doff:]
    return (src, dst, sport, dport, payload)


# ---------------- pcap / pcapng file readers ----------------

def read_classic_pcap(raw):
    magic = raw[:4]
    if magic in (b"\xa1\xb2\xc3\xd4", b"\xa1\xb2\x3c\x4d"):
        endian = ">"
    elif magic in (b"\xd4\xc3\xb2\xa1", b"\x4d\x3c\xb2\xa1"):
        endian = "<"
    else:
        return None
    # global header 24 bytes; linktype at offset 20
    linktype = struct.unpack(endian + "I", raw[20:24])[0]
    off = 24
    pkts = []
    while off + 16 <= len(raw):
        ts_sec, ts_usec, incl, orig = struct.unpack(endian + "IIII", raw[off:off + 16])
        off += 16
        if off + incl > len(raw):
            break
        data = raw[off:off + incl]
        off += incl
        pkts.append((ts_sec + ts_usec / 1e6, data, linktype))
    return pkts


def read_pcapng(raw):
    if raw[:4] != b"\x0a\x0d\x0d\x0a":
        return None
    # determine endianness from SHB byte-order magic at offset 8
    bom = raw[8:12]
    endian = "<" if bom == b"\x4d\x3c\x2b\x1a" else ">"
    off = 0
    linktypes = {}          # interface id -> linktype
    if_index = 0
    tsresol = {}            # interface id -> ticks per second
    pkts = []
    while off + 12 <= len(raw):
        btype = struct.unpack(endian + "I", raw[off:off + 4])[0]
        blen = struct.unpack(endian + "I", raw[off + 4:off + 8])[0]
        if blen < 12 or off + blen > len(raw):
            break
        body = raw[off + 8:off + blen - 4]
        if btype == 0x00000001:      # Interface Description Block
            lt = struct.unpack(endian + "H", body[0:2])[0]
            linktypes[if_index] = lt
            tsresol[if_index] = 1e6  # default microsecond
            if_index += 1
        elif btype == 0x00000006:    # Enhanced Packet Block
            ifid = struct.unpack(endian + "I", body[0:4])[0]
            th = struct.unpack(endian + "I", body[4:8])[0]
            tl = struct.unpack(endian + "I", body[8:12])[0]
            caplen = struct.unpack(endian + "I", body[12:16])[0]
            data = body[16:16 + caplen]
            resol = tsresol.get(ifid, 1e6)
            ts = ((th << 32) | tl) / resol
            pkts.append((ts, data, linktypes.get(ifid, 101)))
        elif btype == 0x00000003:    # Simple Packet Block
            caplen = struct.unpack(endian + "I", body[0:4])[0]
            data = body[4:4 + caplen]
            pkts.append((0.0, data, linktypes.get(0, 101)))
        off += blen
    return pkts


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    path = sys.argv[1]
    host = sys.argv[2] if len(sys.argv) > 2 else HOST
    port = int(sys.argv[3]) if len(sys.argv) > 3 else PORT
    with open(path, "rb") as f:
        raw = f.read()
    pkts = read_pcapng(raw) if raw[:4] == b"\x0a\x0d\x0d\x0a" else read_classic_pcap(raw)
    if pkts is None:
        print(f"Unrecognized capture format (first bytes: {hexd(raw[:8])})")
        return

    rows = []           # (ts, direction, payload)
    linktype_seen = set()
    for ts, data, lt in pkts:
        linktype_seen.add(lt)
        r = parse_ip_tcp(data, lt)
        if not r:
            continue
        src, dst, sport, dport, payload = r
        if not payload:
            continue
        if dst == host and dport == port:
            rows.append((ts, "PHONE->UNIT", payload))
        elif src == host and sport == port:
            rows.append((ts, "UNIT ->PHONE", payload))

    rows.sort(key=lambda x: x[0])
    print(f"# capture: {path}")
    print(f"# link types seen: {sorted(linktype_seen)}   filter: {host}:{port}")
    print(f"# {len(rows)} app-layer segments on the unit's TCP/{port} session\n")
    if not rows:
        print("No TCP payloads to/from the unit were found. Check host/port, or the")
        print("capture may not include the app<->unit session (per-app filter / subnet).")
        return

    t0 = rows[0][0]
    prev = None
    for ts, direction, payload in rows:
        if prev is not None and ts - prev > 1.0:
            print(f"\n----- idle {ts - prev:.1f}s (likely a new app action) -----")
        rel = ts - t0
        print(f"\n[{rel:8.3f}s] {direction}  ({len(payload)}B)")
        # wrap hex at 16 bytes/line with ascii gutter
        for i in range(0, len(payload), 16):
            chunk = payload[i:i + 16]
            print(f"    {i:04x}  {hexd(chunk):<48}  {asc(chunk)}")
        prev = ts

    # de-duplicated per-direction byte stream (spot fixed headers/framing)
    print("\n\n===== concatenated per-direction segment starts (first 24B each) =====")
    for want in ("PHONE->UNIT", "UNIT ->PHONE"):
        print(f"\n{want}:")
        seen = set()
        for ts, d, p in rows:
            if d != want:
                continue
            head = bytes(p[:24])
            if head in seen:
                continue
            seen.add(head)
            print(f"  {hexd(p[:24])}   | {asc(p[:24])}")


if __name__ == "__main__":
    main()
