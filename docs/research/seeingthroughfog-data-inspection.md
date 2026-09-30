# SeeingThroughFog: data inspection (2026-09-29)

First look at the real download, prompted by the fog-chamber comment on #9. Inspected locally, never committed:
`labeltool_labels.zip`, `labeltool_labels_refined.zip`, `gt_labels/cam_left_labels_TMP.zip`,
`weather_station.zip`, `filtered_relevant_can_data.zip`. Camera images not yet downloaded.

## How the download is packaged

Per-folder split archives, e.g. `SeeingThroughFog/cam_stereo_left_lut/cam_stereo_left_lut.z01`–`.z23` + `.zip`.
There is no combined `SeeingThroughFogCompressed.*` archive, which is what upstream's `SeeingThroughFog_sha256sum.txt` lists.

## Checksums: none published for the per-folder archives (2026-09-29, for #30)

- The upstream repository's only checksum file is `SeeingThroughFog_sha256sum.txt`. It lists
  `SeeingThroughFogCompressed.z01`–`.z18` + `.zip`, and the upstream README says to run `sha256sum -c` against them.
- The download listing (472 files) has only per-folder `.zip`/`.zNN` archives and calibration JSONs. None is a
  checksum file.
- The upstream issues have no report about checksums for the split archives.

So the checksum command was removed. Zip stores a CRC32 per file, so corruption fails at extraction. Hashing our
own copy would only check it against itself.

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

## Mixed fog and precipitation (2026-09-29, for #9)

Counted over all 12,997 refined files before committing to excluding fog plus rain or snow:

| Refined flags | Not twilight | Including twilight |
| --- | --- | --- |
| Fog, no precipitation | 1,353 | 1,360 |
| Fog + snow | 1,549 | 1,894 |
| Fog + rain | 0 | 0 |
| Mixed share of all fog | 53% | 58% |

- The mixed samples are all fog with snow; there is no fog with rain.
- Mixed fog is mostly light fog. Light fog is 258 fog-only samples against 1,409 with snow. Dense fog is 1,095
  fog-only against 140 with snow.
- The flags are clean. No sample contradicts its `no` flag, none has rain and snow together, and every sample has
  exactly one of `daytime.day` / `daytime.night`. 2,128 samples (16%) are `twilight`.

**Decision: exclude them anyway.** The share is large, but 1,353 fog-only frames remain (about 1,134 by day and 219
by night), which is enough for a cap of a few hundred per condition. Precedence rules were considered and rejected:
counting fog + snow as fog puts snowfall into the fog condition, and counting it as snow puts fog into snow. Either
way, one condition would measure two effects.

**Consequence to report:** the fog condition is about 81% dense fog, so light fog is under-represented. Fog-night
(219 frames) falls short of a 300 cap. The mapping is in `backend/conditions.py`.

## Labels (`gt_labels/cam_left_labels_TMP`)

- 12,997 files, and every non-empty line has 27 fields. 64 files are empty (samples with no labelled objects).
- Three lines have an all-zero 2D box (`2018-02-07_18-05-09_00000` line 1, `2018-02-07_18-25-17_00170` line 7,
  `2018-12-10_08-55-01_00600` line 8). The adapter treats these as malformed and excludes the frame.
- Classes beyond the six in the spec: `DontCare` (5,295), `Pedestrian_is_group` (1,134), `PassengerCar_is_group`
  (238), a few other `*_is_group`, `person` (3) and `train` (1). Only the four main classes are counted as objects
  in the Subset table. For Benchmark scoring, `DontCare` and every `*_is_group` box are ignore regions, like the
  fallback classes; the stray `person` and `train` labels are dropped (see `backend/class_mapping.py`).
- Reading every refined metadata and label file took 300–340 s, even on a second pass. The app builds the index once
  per run and caches it in memory.

## The default subset on the real data (seed 0, cap 300)

`index_dataset` on the real refined metadata and labels: 9,318 usable samples, 3,679 excluded (fog with snow 1,549,
twilight 2,128, malformed label line 2; the third zero-box frame was already excluded for another reason).

| Condition | Usable | In subset | Objects | Rarest class | Low n (< 30) |
| --- | --- | --- | --- | --- | --- |
| clear-day | 3,011 | 300 | 2,946 | RidableVehicle 107 | |
| clear-night | 2,496 | 300 | 2,297 | LargeVehicle 76 | |
| fog-day | 1,134 | 300 | 1,092 | RidableVehicle 7 | low n |
| fog-night | 219 | 219 | 829 | RidableVehicle 14 | low n |
| snow-day | 1,237 | 300 | 2,041 | RidableVehicle 16 | low n |
| snow-night | 989 | 300 | 2,045 | RidableVehicle 63 | |
| rain-day | 68 | 68 | 333 | RidableVehicle 8 | low n |
| rain-night | 164 | 164 | 1,963 | RidableVehicle 28 | low n |

At cap 300, RidableVehicle is the bottleneck in every adverse condition except snow-night. Per-class AP for bikes
under fog and rain will be flagged as low n unless the cap goes up. Rain-day has only 68 usable frames in total.

## Day/night: original vs refined (spot-check, 2026-09-29, for #9)

The original and refined metadata disagree on day/night for 711 samples:

| Original → refined | Not twilight | Twilight |
| --- | --- | --- |
| night → day | 388 | 260 |
| day → night | 54 | 9 |

Twilight samples are excluded from the conditions anyway, so only the 442 non-twilight disagreements move frames
between conditions. All 648 night → day samples have `meta.illumination.overall_dark = false` in the original file,
so the original contradicts its own darkness flag there.

Spot-checked 12 non-twilight samples, drawn with `random.Random(9)`: 8 night → day and 4 day → night. The images
were read one at a time from the split `cam_stereo_left_lut` archive over HTTP range requests (about 30 MB instead
of 37.6 GB), and each was checked against its zip CRC.

| Sample | Original | Refined | Seen |
| --- | --- | --- | --- |
| 2018-02-12_08-42-40_00300 | night | day | day: overcast, snow, buildings lit by daylight |
| 2018-10-29_16-18-47_04600 | night | day | day: overcast, fog; some cars with headlights on |
| 2018-10-29_16-38-10_00170 | night | day | day: dense fog, daylit |
| 2018-10-29_16-38-10_00900 | night | day | day: dense fog, daylit |
| 2018-10-29_16-42-03_00310 | night | day | day: fog, pedestrians in daylight |
| 2018-12-10_09-51-03_00030 | night | day | day: snow, grey sky |
| 2018-12-11_09-18-59_00900 | night | day | day: snowy forest road, grey sky |
| 2018-12-11_09-18-59_04000 | night | day | day: snowy forest road, bus with headlights |
| 2019-05-02_21-24-45_00930 | day | night | night: black sky, street lamps lit |
| 2019-05-02_21-24-45_01710 | day | night | night: black sky, lit shop windows |
| 2019-05-02_21-24-45_01800 | day | night | night: black sky, street lamps lit |
| 2019-05-02_21-24-45_02070 | day | night | night: black sky, street lamps lit |

**Result: the refined file is right in all 12.** The clock times in the ids agree: morning and afternoon for night →
day, 21:24 in May for day → night. The adapter already reads the refined file, so nothing changes. Headlights
switched on in fog and snow are a plausible cause of the original "night" labels.

Caveat: the 12 frames come from 7 recordings, and 4 are from one drive (2019-05-02_21-24-45). This is strong
evidence for these recordings, not a measured error rate for the refined file. No image was ambiguous.

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
