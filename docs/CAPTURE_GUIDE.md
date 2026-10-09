# Capture guide: filming a green for 3-D reconstruction

Method: **photogrammetry from video** on an Android phone (Samsung). Any recent
phone camera works. Practise on a putting mat at home before a real green.

## Phone options (Samsung)

| Method | Phones | Use |
|---|---|---|
| Photogrammetry from video | any | **main method** |
| Depth sensor (ToF) | Galaxy S10 5G, Note10+, S20+, S20 Ultra only | optional comparison |
| ARCore Depth (depth-from-motion) | most recent phones | too coarse for 1–3 % slopes alone |

The phone's tilt sensor plus a level app (e.g. "Bubble Level") on a straight
board doubles as the ground-truth slope gauge.

## Gravity: which way is down?

Photogrammetry recovers shape but not the direction of gravity, and a 1° tilt
error ruins slope measurement. Level the model with markers whose height
differences you measured (straight board + level), or with phone accelerometer
data recorded during capture. Phase 2 (mat at known slope) checks this.

## Before filming

**Settings (Samsung Camera → Pro Video):** 4K, 30 fps, main 1× lens (not
ultra-wide/zoom), focus and exposure locked, video stabilisation **off**,
shutter 1/250 s or faster.

**Conditions:** overcast is best (no hard shadows, including your own); dry
grass, no dew; nobody walking through the area.

**Area setup:**
- Ball, hole and ~1 m margin around both (≈ 6 × 3 m for a 4 m putt).
- 4–6 printed ArUco markers around the edges, 1–2 along the line (grass is
  repetitive, so markers give the software fixed points).
- Tape-measure distances between markers (scale).
- Measure true slope along and across the putt line with board + level app.
- Ball in place, flag out.

## Filming (~3 minutes)

```
        ← loop 1: chest height, phone tilted ~45° down
   ┌───────────────────────┐
   │  ▣              ▣     │   ▣ = marker
   │      ●  ─ ─ ─ ─ ⊙     │   ● = ball, ⊙ = hole
   │  ▣              ▣     │
   └───────────────────────┘
        ← loop 2: knee height, flatter angle
        ↕ pass 3: phone pointing straight down, walk lines across
```

1. **Loop 1:** walk slowly around the outside at chest height, phone ~45° down,
   area centred. About one step per second.
2. **Loop 2:** repeat at knee height, phone flatter.
3. **Pass 3:** phone straight down at arm's length (selfie stick helps), walk
   back-and-forth lines across the area with ~50 % overlap.

Move slowly and smoothly; walk around, don't spin on the spot; keep the area in frame.

## After filming

- Copy the original video to the laptop by cable or Google Drive. Messaging
  apps compress it.
- Log: date, Stimpmeter reading, measured slopes, marker distances.

## Filming putts (phase 3 validation)

Separate recording: phone on a tripod, high behind the ball, whole putt in
frame, 60 fps or more, same locked settings. Used to track the real ball path
and compare with the prediction.
