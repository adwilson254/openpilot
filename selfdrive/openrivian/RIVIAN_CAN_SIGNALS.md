# Rivian CAN Signal Findings (diagnosed during investigation)

Recovered from the `rivian_telemetryd.py` / `chargingd.py` sniffing work on this
`can-debug` branch and **reconciled against the vendored Rivian DBC**
(`opendbc_repo/opendbc/dbc/rivian_primary_actuator.dbc`).

This file preserves the diagnosed signals in a durable, reviewable form. The raw
sniffer daemons stay on `can-debug` only (per the branch safety rules); the DBC was
**not** modified — several field-diagnosed guesses turned out to be wrong or already
defined, so any DBC change should be validated on a real vehicle first.

Primary bus = 0. All bit positions below use DBC (`@0+`, big-endian) notation.

## Confirmed — already defined in the DBC (matches the diagnosis)

| Addr | Dec | DBC message | Diagnosed as | Reconciliation |
|------|-----|-------------|--------------|----------------|
| `0x150` | 336 | `VDM_PropStatus` | PRND in byte 2 (0x11 P, 0x21 R, 0x22 N, 0x44 D) | ✅ Matches `VDM_Prndl_Status` (19\|4). **Bonus:** this frame also carries `VDM_VehicleSpeed` (47\|16, 0.01 kph) and `VDM_AcceleratorPedalPosition` (31\|10) — this is the real vehicle speed source. |
| `0x162` | 354 | `VDM_AdasSts` | ADAS/drive-mode state in byte 4 | ✅ Matches `VDM_AdasDriverModeStatus` (36\|3, range 0–7). |
| `0x209` | 521 | `ESP_WSpeed_Front` | "vehicle speed", 16-bit BE bytes 2–3 | ✅ It's **front wheel speed**: `ESP_Wheel_Speed_Left_Front` (23\|16) / `Right_Front` (39\|16), scale **0.01 kph**. Confirms the "needs scaling refinement" note (raw 6100 → 61.0 kph). |
| `0x501` | 1281 | `RCM_SerialIdentifier` | 8-byte ASCII part no. "11068311" (static) | ✅ Matches `RCM_SerialNumber` (64-bit). DBC treats it as a number; the ASCII decode is a valid alternate view. |

## Corrections — diagnosis was wrong or mismatched

| Addr | Dec | Diagnosed as | Actual (per DBC) |
|------|-----|--------------|------------------|
| `0x152` | 338 | Steering wheel angle, 16-bit signed LE bytes 2–3 | ❌ `VDM_OutputSignals` — VDM **torque/brake requests**. The 16-bit field at bytes 2–3 is `VDM_Lfc_BrakeTorqueRequest` (23\|15, Nm), not steering angle. Steering angle is not in this frame (look to an EPAS message). |
| `0x5ff` | 1535 | EVSE advertised target charge limit, byte 2 × 0.1 | ❌ `DoorStatus` in the DBC. The "static 193 / charge-limit" interpretation is disproven; this frame is body/door state. |

## New / undocumented — not in the DBC (needs on-vehicle validation)

These are the genuinely novel field findings worth carrying forward. **Medium/low
confidence** — validate before adding to the DBC or any decode path.

| Addr | Dec | Diagnosed meaning | Layout / scaling | Confidence | Observed behavior |
|------|-----|-------------------|------------------|------------|-------------------|
| `0x550` | 1360 | Dynamic actual charge intake | byte 3 × 0.1 (km/h-equiv); bytes 3 & 4 identical | Medium | Dropped from the advertised limit to exactly 128 (→ 12.8 / 8.0 mi/hr) when AC activated. ~10 Hz. |
| `0x554` | 1364 | Ambiguous trip meter **or** component temperature | byte 6 | Low | Climbed 70 → 74 over a 3-min drive (a range estimate would fall). If temperature: 70–74 °C ≈ nominal stator/inverter temp. ~1 Hz. |

## Notes
- `chargingd.py` on this branch is a placeholder (no decoded signals committed) — the
  charging findings above came from `rivian_telemetryd.py`'s annotations.
- Confirmed signals (`0x150`, `0x162`, `0x209`, `0x501`) already reach `carState` via
  the Rivian car port, so `cereal2mqtt` can publish them without any sniffer.
- Recommended next step for the new signals: capture parked-vehicle logs, confirm
  `0x550`/`0x554` semantics, then propose proper `SG_` definitions to the upstream
  Rivian DBC rather than decoding them in an ad-hoc daemon.
