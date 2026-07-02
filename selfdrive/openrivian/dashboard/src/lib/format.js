// Topic constants (from cereal2mqtt) ---------------------------------------
export const T = {
  speed_mph: 'openrivian/vehicle/powertrain/speed_mph',
  speed_ms: 'openrivian/vehicle/powertrain/speed_ms',
  standstill: 'openrivian/vehicle/powertrain/standstill',
  gear: 'openrivian/vehicle/powertrain/gear',
  soc: 'openrivian/vehicle/powertrain/soc',
  charging: 'openrivian/vehicle/powertrain/charging',
  ignition: 'openrivian/vehicle/powertrain/ignition',
  aEgo: 'openrivian/vehicle/powertrain/a_ego',
  wsFL: 'openrivian/vehicle/powertrain/wheel_speed_fl',
  wsFR: 'openrivian/vehicle/powertrain/wheel_speed_fr',
  wsRL: 'openrivian/vehicle/powertrain/wheel_speed_rl',
  wsRR: 'openrivian/vehicle/powertrain/wheel_speed_rr',
  steerAngle: 'openrivian/vehicle/controls/steering_angle_deg',
  steerTorque: 'openrivian/vehicle/controls/steering_torque',
  steerTorqueEps: 'openrivian/vehicle/controls/steering_torque_eps',
  gas: 'openrivian/vehicle/controls/gas_pressed',
  brake: 'openrivian/vehicle/controls/brake_pressed',
  leftBlinker: 'openrivian/vehicle/controls/left_blinker',
  rightBlinker: 'openrivian/vehicle/controls/right_blinker',
  doorOpen: 'openrivian/vehicle/body/door_open',
  seatbelt: 'openrivian/vehicle/body/seatbelt_unlatched',
  leftBsm: 'openrivian/vehicle/adas/left_blindspot',
  rightBsm: 'openrivian/vehicle/adas/right_blindspot',
  cruiseEnabled: 'openrivian/vehicle/adas/cruise_enabled',
  cruiseSpeed: 'openrivian/vehicle/adas/cruise_speed_mph',
  cruiseAvail: 'openrivian/vehicle/adas/cruise_available',
  adasEnabled: 'openrivian/adas/enabled',
  adasActive: 'openrivian/adas/active',
  leadDist: 'openrivian/adas/radar/lead_one_d_rel',
  leadVRel: 'openrivian/adas/radar/lead_one_v_rel',
  cpuTemp: 'openrivian/device/hardware/cpu_temp_c',
  mem: 'openrivian/device/hardware/memory_usage_percent',
  freeSpace: 'openrivian/device/hardware/free_space_percent',
  voltage: 'openrivian/device/hardware/voltage',
  cameradRunning: 'openrivian/device/hardware/camerad_running',
  powerDraw: 'openrivian/device/power/draw_w',
  lat: 'openrivian/vehicle/location/latitude',
  lon: 'openrivian/vehicle/location/longitude',
  alt: 'openrivian/vehicle/location/altitude',
  bearing: 'openrivian/vehicle/location/bearing',
};

export const fmt = (v, digits = 0, dash = '—') =>
  (v === undefined || v === null || Number.isNaN(v)) ? dash
    : (typeof v === 'number' ? v.toFixed(digits) : String(v));

export const bool = (v) => v === true || v === 1 || v === '1' || v === 'true';

export function gearLabel(raw) {
  if (raw === undefined || raw === null) return '—';
  const s = String(raw).toLowerCase();
  if (s.includes('drive')) return 'D';
  if (s.includes('reverse')) return 'R';
  if (s.includes('neutral')) return 'N';
  if (s.includes('park')) return 'P';
  return String(raw).slice(0, 3).toUpperCase();
}

export function ageLabel(ts) {
  if (!ts) return '';
  const s = (Date.now() - ts) / 1000;
  if (s < 1) return 'now';
  if (s < 60) return `${s.toFixed(0)}s`;
  return `${(s / 60).toFixed(0)}m`;
}
