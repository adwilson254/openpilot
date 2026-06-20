#!/usr/bin/env python3
import os
try:
    os.nice(19)
except Exception:
    pass

import time
import struct
import cereal.messaging as messaging

def main():
    # We read from the local CAN socket
    can_sock = messaging.sub_sock('can')
    
    print("[RivianTelemetryD] Started advanced CAN decoding service...")

    while True:
        msgs = messaging.drain_sock(can_sock, wait_for_one=True)
        for msg in msgs:
            for can_msg in msg.can:
                # Primary bus is 0
                if can_msg.src != 0:
                    continue
                
                address = can_msg.address
                dat = can_msg.dat
                
                # =========================================================
                # 1. CORE POWERTRAIN SIGNALS (HIGH CONFIDENCE)
                # =========================================================

                # 0x209 (521) - Vehicle Speed (~13.5Hz)
                # [Assumption]: Starts at 0, ramps smoothly to ~5200 at 38mph.
                # [Trend]: Highly correlated with 0x208 and 0x20a (likely wheel speeds).
                # [Format]: 16-bit Big-Endian across Bytes 2 and 3.
                if address == 0x209 and len(dat) >= 4:
                    raw_speed = (dat[2] << 8) | dat[3]
                    # Scaling logic needs refinement (e.g. 5200 raw ~= 38 mph / 61 kmh)
                    pass

                # 0x152 (338) - Steering Wheel Angle (~6.8Hz)
                # [Assumption]: 16-bit Signed Integer, Little-Endian.
                # [Trend]: Swings cleanly negative (left) and positive (right) symmetrically around 0.
                if address == 0x152 and len(dat) >= 4:
                    raw_steer = struct.unpack('<h', bytes([dat[2], dat[3]]))[0]
                    pass
                
                # 0x162 (354) - VDM_AdasSts (Includes Drive Mode / ADAS State)
                # [Assumption]: Contains VDM_AdasDriverModeStatus or similar.
                # [Trend]: 0=Conserve/Parked?, 3=Reverse/OffRoad?, 2=Neutral/All-Purpose?, 1=Drive/Sport?. Correlated heavily with drive shifts.
                if address == 0x162 and len(dat) >= 5:
                    adas_state = dat[4]
                    pass

                # 0x150 (336) - VDM_PropStatus (Transmission / PRND)
                # [Verified via DBC]: Contains VDM_Prndl_Status and VDM_Prndl_Request.
                # [Trend]: 0x11=Park, 0x21=Reverse, 0x22=Neutral, 0x44=Drive.
                if address == 0x150 and len(dat) >= 3:
                    prnd_flags = dat[2]
                    pass

                # =========================================================
                # 2. CHARGING & BATTERY SIGNALS (MEDIUM CONFIDENCE)
                # =========================================================

                # 0x5ff (1535) - EVSE Advertised Target Charge Limit (10Hz)
                # [Assumption]: Absolute maximum charging rate advertised by wallbox.
                # [Trend]: Completely static at 193 (19.3 km/h = 12.0 mi/hr) even when AC kicked on.
                if address == 0x5ff and len(dat) >= 3:
                    target_charge_limit_kmh = dat[2] * 0.1
                    pass
                    
                # 0x550 (1360) - Dynamic Actual Charge Intake (10Hz)
                # [Assumption]: The real-time battery intake.
                # [Trend]: Fluctuated and dropped from target limit exactly to 128 (12.8 km/h = 8.0 mi/hr) when AC activated.
                if address == 0x550 and len(dat) >= 5:
                    actual_charge_rate_kmh = dat[3] * 0.1 # Byte 3 and 4 are identical
                    pass

                # 0x554 (1364) - Ambiguous Counter / Trip / Temp (1Hz)
                # [PREVIOUS ASSUMPTION]: Estimated Range in miles. (DISPROVEN)
                # [NEW ASSUMPTION]: Granular trip meter OR component temperature.
                # [Trend]: Value incrementally climbed from 70 to 74 over a 3-minute drive. Range would go down.
                # [Trend 2]: If it is a Temperature, 70C -> 74C is 158F -> 165F (Nominal Stator/Inverter Temp).
                if address == 0x554 and len(dat) >= 7:
                    trip_or_temp_val = dat[6]
                    pass

                # =========================================================
                # 3. STATIC VEHICLE IDENTIFIERS (HIGH CONFIDENCE)
                # =========================================================

                # 0x501 (1281) - Hardware/Software Part Number (1Hz)
                # [Assumption]: 8-byte ASCII string identifying the module.
                # [Trend]: 100% static across the entire drive: "11068311"
                if address == 0x501 and len(dat) == 8:
                    part_str = "".join([chr(x) if 32 <= x <= 126 else "." for x in dat])
                    pass

if __name__ == "__main__":
    main()
