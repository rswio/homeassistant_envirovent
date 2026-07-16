# Packet captures (Phase 2)

Drop the PCAPdroid export here (e.g. `atmos-session-1.pcap` / `.pcapng`).
Then it can be decoded with:

```bash
python3 research/tools/pcap_analyze.py research/captures/atmos-session-1.pcap
```

## How to capture (PCAPdroid, no root)

1. Install **PCAPdroid** (Play Store / F-Droid).
2. Settings → **Target app = myenvirovent** (per-app capture keeps it clean).
   Dump mode "PCAP file" is fine (exports raw-IP `DLT_RAW`, which the parser handles).
3. Start capture, then in the myenvirovent app do this **slowly (~5s pauses)** and
   note the wall-clock time of each step so I can map bytes → command:
   1. Open app / let it connect and show the status screen
   2. Sit on the status screen ~10s (captures the polling read)
   3. **Boost ON → wait → Boost OFF**  (most reversible write)
   4. Airflow speed **up one step → back**
   5. Variable Airflow toggle on / set a %
   6. Auto Heater **on → off**
4. Stop capture, **export the `.pcap`/`.pcapng`**, put it in this folder.

### Do NOT
- Do **not** enter the installer access code or change any commissioning/summer/
  heater-temp setting during the capture.
- I will stay **off** the device during your capture (it accepts only one TCP
  client at a time, so the app needs the slot).

### Notes that help decoding
- If the app shows a **"unit code"/pairing password**, jot it down (it likely
  appears as an auth/ID field in the frames). Do **not** include your Wi-Fi password.
- A rough per-action timeline (even "boost on ≈ 0:15, off ≈ 0:25") massively speeds
  up mapping the bytes.
