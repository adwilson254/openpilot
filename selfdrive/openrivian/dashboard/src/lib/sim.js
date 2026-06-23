// Demo / design-preview simulator. Enabled with ?sim=1 so the dashboard can be viewed
// on a laptop without a comma device / MQTT broker. Produces realistic, animated values
// for every telemetry topic. Has no effect unless explicitly requested.
import { T } from './format';

export function simEnabled() {
  return new URLSearchParams(window.location.search).get('sim') === '1';
}

// Returns a flat { topic: value } snapshot for time t (seconds).
export function simSnapshot(t) {
  const sine = (period, lo, hi, phase = 0) =>
    lo + (hi - lo) * (0.5 + 0.5 * Math.sin((2 * Math.PI * t) / period + phase));

  const speed = sine(40, 4, 64);                 // mph, slow cruise sweep
  const steer = 90 * Math.sin((2 * Math.PI * t) / 12); // deg, gentle lane curves
  const leadDist = sine(18, 12, 70);
  const accel = 0.4 * Math.cos((2 * Math.PI * t) / 40);
  const blinkPhase = Math.floor(t / 6) % 3;      // none / left / right cycle
  const soc = 72 - (t / 90) % 20;                // slow drain

  return {
    [T.speed_mph]: speed,
    [T.speed_ms]: speed * 0.44704,
    [T.standstill]: speed < 1,
    [T.gear]: 'drive',
    [T.soc]: soc,
    [T.charging]: false,
    [T.ignition]: true,
    [T.aEgo]: accel,
    [T.wsFL]: speed + Math.sin(t * 3) * 0.4,
    [T.wsFR]: speed + Math.sin(t * 3 + 1) * 0.4,
    [T.wsRL]: speed + Math.sin(t * 3 + 2) * 0.4,
    [T.wsRR]: speed + Math.sin(t * 3 + 3) * 0.4,
    [T.steerAngle]: steer,
    [T.steerTorque]: steer * 0.02,
    [T.steerTorqueEps]: steer * 0.018,
    [T.gas]: accel > 0.2,
    [T.brake]: accel < -0.25,
    [T.leftBlinker]: blinkPhase === 1,
    [T.rightBlinker]: blinkPhase === 2,
    [T.doorOpen]: false,
    [T.seatbelt]: false,
    [T.leftBsm]: Math.sin(t / 7) > 0.85,
    [T.rightBsm]: Math.sin(t / 9 + 2) > 0.85,
    [T.cruiseEnabled]: true,
    [T.cruiseSpeed]: 65,
    [T.cruiseAvail]: true,
    [T.adasEnabled]: true,
    [T.adasActive]: (Math.floor(t / 10) % 2) === 0,
    [T.leadDist]: leadDist,
    [T.leadVRel]: -accel * 4,
    [T.cpuTemp]: sine(30, 54, 74),
    [T.mem]: sine(50, 38, 52),
    [T.freeSpace]: 61.4,
    [T.voltage]: sine(20, 12.1, 12.7),
    [T.cameradRunning]: true,
    [T.powerDraw]: sine(25, 16, 28),
    [T.lat]: 37.7749 + 0.002 * Math.sin(t / 30),
    [T.lon]: -122.4194 + 0.002 * Math.cos(t / 30),
    [T.alt]: sine(60, 30, 90),
    [T.bearing]: (t * 6) % 360,
  };
}
