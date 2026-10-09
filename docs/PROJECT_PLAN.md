# Project plan: camera-based green reading

## Research question

Can a low-cost, camera-only system (smartphone) measure the slope of a putting
green accurately enough to predict the correct putting line, and how does
its prediction compare with real putts?

Greens typically slope only 1–3 %, about 3–9 cm of height change over a 3 m putt.
Accuracy of the height map is the central challenge.

## Sub-questions

1. How accurately does each capture method recover slope?
   - Photogrammetry from a walk-around phone video (COLMAP / Meshroom), the main method
   - Phone depth sensor (ToF on some Samsung models) or ARCore Depth, for comparison
   - Monocular AI depth (Depth Anything / MiDaS) from a single photo
2. How much slope error can the line prediction tolerate? The simulator can
   answer this: add noise to the height map and see how the aim point changes.
3. Does the predicted line match where real putts roll?
4. Which line is "best": stop 40 cm past, or the line that maximises the make zone?

## Phases

### Phase 1: simulation (done)
Physics + solver on synthetic greens. See README.

### Phase 2: controlled test on a putting mat
- Prop a putting mat at known slopes (measure with a digital level): 0 %, 1 %, 2 %, 3 %.
- Capture with each method → point cloud → fit height map (Open3D / SciPy).
- Compare measured vs. true slope. Feed the measured map into the solver.
- Measure the mat's speed with a Stimpmeter (or a DIY ramp).
- Code to add: `capture/` (point-cloud loading, plane/surface fitting),
  `detect/` (ball and hole detection with OpenCV, later YOLO).

### Phase 3: real green
- Same capture on a real practice green. Use a scale reference (e.g. a 1 m
  ruler or ArUco markers) for photogrammetry.
- Hit ~20 putts per hole location on a tripod-filmed green, track the ball in
  the video (OpenCV), compare actual paths with predicted paths.
- Measure golfer aim/speed spread to replace the placeholder values.
- Overlay the predicted line on the photo (and optionally live in AR).

## Equipment

| Item | Purpose | Notes |
|---|---|---|
| Android phone (Samsung) | video for photogrammetry; tilt sensor as level | see [CAPTURE_GUIDE.md](CAPTURE_GUIDE.md) |
| Printed ArUco markers | fixed points, scale and levelling | free to print |
| Tripod | stable video for ball tracking | |
| Straight board + level app | ground-truth slope | phone tilt sensor |
| Stimpmeter (or DIY ramp) | green speed | |
| Putting mat + shims | controlled slopes for phase 2 | |
| Laptop with Python 3.9+ | analysis | NumPy, SciPy, OpenCV, Open3D, Ultralytics, COLMAP or Meshroom |

## Related work to review

Look these up and verify before citing:
- A. R. Penner, *The physics of putting*, Canadian Journal of Physics (2002), covering ball
  roll and hole capture.
- B. W. Holmes, *Putting: How a golf ball and hole interact*, American Journal of
  Physics (1991), covering capture speed.
- AimPoint green-reading method (slope-feel based charts).
- Commercial systems: PuttView (AR projection on indoor greens), Capto putting analysis.

## Possible extensions

- Grain direction (anisotropic friction), skid-to-roll phase after impact.
- Live AR app (Swift + ARKit) drawing the line on the phone camera view.
- Learn the height map directly from video of balls rolling (inverse problem).
