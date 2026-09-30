# Historical FAST-LIVO2 validation — 2026-09-01

This is a public excerpt of the historical report. No original bag or node log is included. The selected mapper modifications are now supplied as a patch against a verified public baseline; the full mapper tree is not copied here. The historical experiment was not re-run during release preparation.

## Online results

- Raw republished image: 1920 x 1080.
- `/rgb_img`: 1920 x 1080, `bgr8`, measured average approximately 9.85 Hz.
- `/pixel_point_correspondence`: measured average approximately 10.00 Hz.
- PointCloud2 field offsets: x=0, y=4, z=8, u=12, v=16, depth=20; point_step=24 bytes.
- FAST-LIVO2 completed IMU initialization and ran LIO and VIO for the complete input bag without crashing after the ownership fix.
- The mapping process was still alive after playback completed.

## Recorded result bag

- Duration: 90.116533695 s
- Total messages: 5409
- `/rgb_img`: 901
- `/pixel_point_correspondence`: 901
- `/cloud_registered`: 1803
- `/aft_mapped_to_init`: 902
- `/path`: 902

## Offline correspondence validation

- Messages parsed: 901
- Correspondence points parsed: 4,103,770
- Fields: `x,y,z,u,v,depth`
- Non-finite records: 0
- Pixel coordinates outside 1920 x 1080: 0
- Non-positive depth values: 0
- u range: [3.000210, 1916.997559]
- v range: [3.000418, 1076.993774]
- depth range: [0.258801, 35.805946] m

## Evidence and notes

- `../images/rgb_img_overlay.png` is a saved 1920 x 1080 `/rgb_img` frame with projected visual points.
- Runtime logs are not distributed in this repository.
- `../config/fast_livo2/rosbag_play_qos.yaml` is required when replaying this source bag with this Humble image_transport setup.
- The Humble `image_transport republish` executable reports exit code -11 during Ctrl-C shutdown after playback; it did not crash during playback and did not affect recorded outputs.
