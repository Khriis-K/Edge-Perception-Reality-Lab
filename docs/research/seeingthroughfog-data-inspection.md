# SeeingThroughFog: data inspection (2026-09-29)

First look at the real download, done for #9 (fog-chamber fixture sample). Inspected locally, never committed:
`labeltool_labels.zip`, `labeltool_labels_refined.zip`, `gt_labels/cam_left_labels_TMP.zip`,
`weather_station.zip`, `filtered_relevant_can_data.zip`. Camera images not yet downloaded.

## How the download is packaged

Per-folder split archives, e.g. `SeeingThroughFog/cam_stereo_left_lut/cam_stereo_left_lut.z01`–`.z23` + `.zip`.
There is no combined `SeeingThroughFogCompressed.*` archive, which is what `backend/SeeingThroughFog_sha256sum.txt` lists.

## Metadata (`labeltool_labels`)

- 12,997 JSONs, one per labelled sample; the upstream `splits/all.txt` has 12,994 ids.
- Every file has the same key schema, identical to the upstream example JSON: `bad_sensor`, `daytime.{day,night}`,
  `meta.environment.*`, `meta.illumination.*`, `meta.infrastructure.*`, `objects.no_objects`, `rating.*`,
  `weather.{clear,light_fog,dense_fog,rain,snow}`. The fixture's keys match the real data.
- No key marks a fog-chamber sample.

## Refined metadata (`labeltool_labels_refined`)

Same 12,997 ids, **different schema**: `fog.{no, yes.denseFog, yes.lightFog}`, `precipitation.{no, yes.rain,
yes.snow.{heavySnow,lightSnow}}`, `roadState.*`, `sidewalkState.*`, `infrastructure.{highway,inCity,suburban}`,
`tunnel`, `twilight`, `daytime.{day,night}`, `point_removed`. Fog and precipitation are separate axes here, so a
sample can be foggy and snowy at once. `daytime` differs from the original in 711 samples. No fog-chamber key.

## Fog chamber: not found in this release

The paper (arXiv 1902.08913, §3.2) says 1.5k labelled chamber frames exist (day/night, visibility 30/40/50 m).
Checked in the labelled release:

- **Recording dates.** 2018-10-08 and 2018-10-29 are almost all fog, outside the Feb/Dec campaigns. But CAN
  vehicle speed (median 53 and 40 km/h, under 3% stationary) and `highway`/`suburban` tags show road driving,
  not a chamber.
- **Stationary foggy recordings** (max speed < 15 km/h): 6 recordings, 58 frames. The largest is
  `2018-02-07_18-26-13` (49 frames, 0 km/h). That is far short of 1.5k.
- Upstream issue #65 refers to a separate "Fogchamber Dataset". The links file has no chamber archive.

Conclusion: the 1.5k labelled chamber frames are not in this download. They are most likely a separate release.

## Fog-chamber candidate: PixelAccurateBenchmark

A separate dataset on the same download site (`PixelAccurateBenchmark/`). Inspected by reading the zip indexes
over HTTP range requests; nothing downloaded yet.

- One 26 GB zip of 14 inner zips: `rgb_left_8bit` (3.1 GB), `rgb_right_8bit`, `gated*_10bit`, `lidar_hdl64_*`,
  `intermetric_*`, `sgm`, `psmnet`, `monodepth`, `sparse2dense`, `calibration`. **No 2D box labels.**
- `rgb_left_8bit`: 1,600 PNGs named `scene{1-4}_{day,night}_{condition}_{0-9}.png`. Conditions: `clear`,
  `fog20` … `fog100` in 5 m steps, `rain15`, `rain55`. 10 frames per scene, light and condition.
- Filenames carry the fog density, and every scene has a clear reference, so real chamber fog can be compared
  with synthetic fog at the same visibility on the same scene.
- Viewed via range reads: scene 1 in clear day, fog 50 m day and clear night. It is an indoor fog hall, and the
  camera and objects do not move between conditions. So one set of hand-drawn boxes per scene should serve all
  its frames; only scene 1 was compared across conditions.
- Objects seen in the clear day frames: scene 1 has mannequins, bicycles and furniture (no cars). Scene 2 has 2
  cars, 3 mannequins and a bicycle. Scene 3 has 2 cars and a mannequin among cones and signs. Scene 4 has 1 car.
  That is roughly 15–20 scoreable objects in total.
- The 10 frames per condition are near-duplicates of a static scene, so each condition is about 4 independent
  scenes, not 40 samples. Results would be case studies, not statistics.

## Open questions

- Whether the STF paper's 1.5k labelled chamber frames were ever published, and where.
- Whether PixelAccurateBenchmark scenes are static enough to share hand-drawn boxes across conditions.
- Which metadata the adapter should read: original or refined.
- Checksums for the per-folder archives.
