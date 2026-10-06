# Media Candidates for Anveshan Test Suite

**Compiled:** 2026-10-06  
**Purpose:** Licensed test inputs for the three live cases (Kolam, Origami, Tabla).  
**Allowed licences:** public domain, CC0, CC BY, CC BY-SA. NC/ND and "all rights reserved" excluded.  
**Sources:** Wikimedia Commons, Internet Archive, Openverse.

---

## Download Status

Wikimedia CDN returned HTTP 429 (Too Many Requests) after approximately 7 download requests in the first session, and the rate limit persisted for the full follow-up session (~2 hours later). The CDN block is IP-level (Varnish XID tracked). All three download strategies failed for the blocked URLs: full-size direct, 1000px thumbnail, `Special:FilePath` redirect, and PowerShell `Invoke-WebRequest`.

The floor kolam photos were subsequently downloaded manually by Jim directly from the Wikimedia URLs and copied into `var/kiro/media/kolam/`. An additional image (`Colorful_Kolam.jpg`, CC BY-SA) was sourced from Wikimedia independently.

**All files present in `var/kiro/media/kolam/` are verified valid JPEGs or PNGs (checked via header bytes and WIA dimensions).**

**Not downloaded (still missing):**
- `kolam_5_vasudevan.jpg` (CC BY-SA 4.0, R vasudevan, 3.1 MB)
- `nerkodui_mayoo.jpg` (PD, Mayooranathan, 23 KB, 200×201 px)
- `valikodu2_mayoo.jpg` (PD, Mayooranathan, 31 KB, 200×200 px)

---

## Origami

**Summary of search:** Wikimedia Commons has only two hand-folding crane tutorial videos (`OrigamiCrane.ogv` and `Crane.ogv`), both already in use. No other free-licence standalone crane-folding tutorials exist on Wikimedia Commons or Internet Archive. The candidates below are (a) a news clip showing people folding cranes (PD) and (b) a hexagonal box folding tutorial (CC BY-SA, fallback — not a crane but demonstrates the folding-hands capture pattern).

| Category | Title | File page URL | Direct URL | Licence (exact) | Author/attribution | Size (bytes) | Duration/dimensions | SHA-256 | Local path | Why it's useful | Concerns |
|---|---|---|---|---|---|---|---|---|---|---|---|
| origami ⭐ | Hong Kong Protestors Make Paper Origami Cranes to Protest | https://commons.wikimedia.org/wiki/File:Hong_Kong_Protestors_Make_Paper_Origami_Cranes_to_Protest.webm | https://upload.wikimedia.org/wikipedia/commons/d/dc/Hong_Kong_Protestors_Make_Paper_Origami_Cranes_to_Protest.webm | Public Domain (US Government work — Voice of America) | Voice of America / voanews | 25,873,856 | 79.9 s, 1920×1080 | 65E8E2896D13B5EA063A38A7F1B68DDF1509131DE10AAD07CE67C1663C34D86B | var/kiro/media/origami/hk_protesters_crane_fold.webm | Shows multiple people actively folding paper cranes; only PD crane-folding video found outside existing set; tests Gemma's ability to identify crane-folding from a non-tutorial angle | News clip, not a tutorial; hands may not be top-down; multiple people in frame; 25.9 MB is within the 30 MB upload limit |
| origami (fallback) | Hexagonal origami box part 1 | https://commons.wikimedia.org/wiki/File:Hexagonal_origami_box_part_1.ogv | https://upload.wikimedia.org/wikipedia/commons/2/2b/Hexagonal_origami_box_part_1.ogv | CC BY-SA 3.0 | Slashme (David Richfield) | 187,635,276 | 11 m 55 s, 1920×1080 | *not downloaded — 188 MB original, use 240P transcode* | var/kiro/media/origami/ *(retry with transcode URL)* | Hands and paper clearly visible; shows fold-by-fold process; tests long video handling; different folder/not crane so also tests negative-case detection | Not a crane (hexagonal box); 188 MB original far exceeds 30 MB upload limit; use 240P transcode (~25 MB estimate). Transcode URL: `https://upload.wikimedia.org/wikipedia/commons/transcoded/2/2b/Hexagonal_origami_box_part_1.ogv/Hexagonal_origami_box_part_1.ogv.240p.vp9.webm` |

**Note for Claude Code:** Crane-folding tutorial videos with permissive licences are genuinely scarce. The two existing files (`OrigamiCrane.ogv` by Tavin, `Crane.ogv` by the same uploader) are confirmed to be different recordings of the same performance. The Hong Kong VOA clip (above) is the only public-domain crane-folding footage found; it is not a tutorial but does show the folding act. If a genuinely independent tutorial is needed, consider asking a team member to record one and contribute it under CC BY.

---

## Tabla

| Category | Title | File page URL | Direct URL | Licence (exact) | Author/attribution | Size (bytes) | Duration/dimensions | SHA-256 | Local path | Why it's useful | Concerns |
|---|---|---|---|---|---|---|---|---|---|---|---|
| tabla ⭐ | A man playing tabla in village pranpur near Chanderi | https://commons.wikimedia.org/wiki/File:A_man_playing_tabla_in_village_pranpur_near_Chanderi.webm | https://upload.wikimedia.org/wikipedia/commons/4/48/A_man_playing_tabla_in_village_pranpur_near_Chanderi.webm | CC BY-SA 4.0 | Manishontop02 | 7,219,730 | 35 s, 720×1280 (portrait) | 0E0B17B17CC0AFEC6AD043D1006FD41D72E974B1747CF8D65C997B21E665B17B | var/kiro/media/tabla/tabla_chanderi_1.webm | Steady village tabla playing; short (35 s); good for a goal-clip or learner clip; distinct from the existing `Tabla drums demo.oga` | Same uploader, location and date as `tabla_chanderi_2.webm` — likely the same player/session, possibly a second take. Treat as one paired recording, not two independent players |
| tabla | Excellent Tabla playing by a man | https://commons.wikimedia.org/wiki/File:Excellent_Tabla_playing_by_a_man.webm | https://upload.wikimedia.org/wikipedia/commons/5/54/Excellent_Tabla_playing_by_a_man.webm | CC BY-SA 4.0 | Manishontop02 | 9,152,801 | 47 s, 720×1280 (portrait) | 289DF988C2CC1547C9A68B2E3650C23C59C982882CF18177B7A1F8875FBE5BBC | var/kiro/media/tabla/tabla_chanderi_2.webm | Longer companion clip from same location; if chanderi_1 is goal, chanderi_2 is a natural learner attempt (same skill, same session) | Same uploader and session as chanderi_1 — not an independent player; note the pair as potentially the same performance |
| tabla | Ravindra Yavagal tabla play sample | https://commons.wikimedia.org/wiki/File:Ravindra_Yavagal_tabla_play_sample_1.webm | https://upload.wikimedia.org/wikipedia/commons/b/b9/Ravindra_Yavagal_tabla_play_sample_1.webm | CC BY 3.0 | Shaale (YouTube CC) | 2,160,563 | 8.2 s, 1920×1080 | 8B1BACC129B3B750917AB29CE0B21D277606BE792FBBC2A9A0F436CA0CF0A285 | var/kiro/media/tabla/tabla_yavagal_sample.webm | Different professional player (Ravindra Yavagal, Goa tradition); independent of the Pranpur pair; useful as a second-expert reference to test multi-source alignment | Very short (8 s) — only one cycle; not enough for steady-theka analysis on its own; best used as a quality reference or splice test |
| tabla | Tabla played by Vijay Kangutkar | https://commons.wikimedia.org/wiki/File:Tabla_played_by_Vijay_Kangutkar.webm | https://upload.wikimedia.org/wikipedia/commons/a/aa/Tabla_played_by_Vijay_Kangutkar.webm | CC BY 3.0 (YouTube CC, St Cecilia's Hall) | St Cecilia's Hall: all things musical instruments | 26,301,519 | 4 m 12 s, 1280×720 | 9B7AAEDF0907B202A014EE9C95898324A459C84A76A56D32CEC9B2A66633DF81 | var/kiro/media/tabla/tabla_kangutkar.webm | Different professional (Vijay Kangutkar, museum performance); longest clip available; discusses technique; good for testing extended analysis and bayan/treble distinction | 4m12s: at 30 MB upload limit, may need trimming. Contains talking sections (not all tabla). The museum-exhibit context is excellent for a judge-visible attribution story |

---

## Kolam

| Category | Title | File page URL | Direct URL | Licence (exact) | Author/attribution | Size (bytes) | Duration/dimensions | SHA-256 | Local path | Why it's useful | Concerns |
|---|---|---|---|---|---|---|---|---|---|---|---|
| kolam ⭐ | Kolam-8 (sikku/pulli diagram) | https://commons.wikimedia.org/wiki/File:Kolam-8.png | https://upload.wikimedia.org/wikipedia/commons/9/9c/Kolam-8.png | Public domain (author's own work, transferred from ta.wikipedia) | Mayooranathan at Tamil Wikipedia | 90,108 | 600×599 px | 74BBD4C4EA8E6394445894A4D5E99884D4038C912ED58FD7C7E1B89E60E68AC6 | var/kiro/media/kolam/kolam_8_mayoo.png | High-contrast black/white diagram; dot-based pulli design; ideal for geometry analysis; same author as Ithayakkamalam; different pattern | Diagram-style (drawn, not photographed); no perspective challenge |
| kolam | Thirukulam (tank/pond kolam diagram) | https://commons.wikimedia.org/wiki/File:Thirukulam.png | https://upload.wikimedia.org/wikipedia/commons/f/f0/Thirukulam.png | Public domain (author's own work) | Mayooranathan at Tamil Wikipedia | 38,152 | 600×588 px | 3CF6E1DEC0A7F0DF332C675FBEF5CDB57148A406E9076ABD21F5C254843998AC | var/kiro/media/kolam/thirukulam_mayoo.png | High-contrast; different geometric pattern (rectangular symmetry); tests detector on non-diamond layouts | Diagram-style; smaller line count |
| kolam | Thoddil (swing/cradle motif kolam) | https://commons.wikimedia.org/wiki/File:Thoddil.png | https://upload.wikimedia.org/wikipedia/commons/a/a3/Thoddil.png | Public domain (author's own work) | Mayooranathan at Tamil Wikipedia | 46,293 | 600×545 px | 3C8ECD02BAC23E7B413500078E7FD991378457EB9E32C8AEC6333D73893B046F | var/kiro/media/kolam/thoddil_mayoo.png | Different motif with curved loops; 5-fold symmetry; tests curve-detection on more organic shapes | Diagram-style |
| kolam | India - Kolam - 06 (floor photograph) | https://commons.wikimedia.org/wiki/File:India_-_Kolam_-_06_(2486394060).jpg | https://upload.wikimedia.org/wikipedia/commons/9/95/India_-_Kolam_-_06_%282486394060%29.jpg | CC BY 2.0 (Flickr) | McKay Savage from London, UK | 4,297,225 | 3264×2448 px | 74DAE85367D5C437B8910A8FD95F1C9C4C1DCB56464456F3AB8D8099D6182E5B | var/kiro/media/kolam/india_kolam_06_savage.jpg | Real floor kolam (rice flour on floor); perspective, lighting variation, texture — a "harder case" exactly as required; from a well-known Flickr photographer CC set | Has lighting/angle distortion; coloured chalk design (not pure pulli), may challenge the monochrome assumption in the geometry pipeline |
| kolam | India - Kolam - 09 (floor photograph) | https://commons.wikimedia.org/wiki/File:India_-_Kolam_-_09_(2486349844).jpg | https://upload.wikimedia.org/wikipedia/commons/8/81/India_-_Kolam_-_09_%282486349844%29.jpg | CC BY 2.0 (Flickr) | McKay Savage from London, UK | 281,150 (thumb) | 960×720 px (thumbnail — original 3264×2448, 4.5 MB) | 400E44B833C930C379F12108823AEB08004BDCD30D07BEF6337A0E66C2F6712B | var/kiro/media/kolam/india_kolam_09_savage.jpg | Second floor photo from same CC series; different design; provides variation in pattern complexity and perspective. Note: downloaded copy is a browser-resized thumbnail (960×720), not the full-resolution original | Same concerns as kolam-06 re: colour and perspective; lower resolution than kolam-06 — for a full-resolution copy use the direct URL above |
| kolam | Colorful Kolam (floor photograph) | https://commons.wikimedia.org/wiki/File:Colorful_Kolam.jpg | https://upload.wikimedia.org/wikipedia/commons/a/a5/Colorful_Kolam.jpg | CC BY-SA (Wikimedia; uploaded 2012) | Sivasankaran | 329,744 (thumb) | 960×720 px (thumbnail — original 3072×2304, 878 KB) | FCFBCF0D46B7726246AA963ED991E32DBD678627961C591129C34E7551D2D9E2 | var/kiro/media/kolam/colorful_kolam.jpg | Colourful floor kolam (chalk/powder); used in English Wikipedia (Vrata article) and French Wiktionary; third independent floor photograph; good for colour-polarity tests | Downloaded as a 960×720 thumbnail; colourful design may fail the monochrome geometry pipeline — good test of how the pipeline handles unexpected colour input |
| kolam | Nerkodui-1 (straight-thread kolam diagram) | https://commons.wikimedia.org/wiki/File:Nerkodui-1.jpg | https://upload.wikimedia.org/wikipedia/commons/8/84/Nerkodui-1.jpg | Public domain | Mayooranathan at Tamil Wikipedia | 23,345 | 200×201 px | *not downloaded — CDN 429* | var/kiro/media/kolam/ *(retry needed)* | Simple straight-thread pattern (easy geometry case); from the same Mayooranathan set | Very small (200 px); may be too low-res for reliable dot detection |
| kolam | Valikodu-2 (intertwined kolam diagram) | https://commons.wikimedia.org/wiki/File:Valikodu-2.jpg | https://upload.wikimedia.org/wikipedia/commons/3/36/Valikodu-2.jpg | Public domain | Mayooranathan at Tamil Wikipedia | 31,246 | 200×200 px | *not downloaded — CDN 429* | var/kiro/media/kolam/ *(retry needed)* | Intertwined (valaikoodu) pattern — more complex topology; tests interleaving curve detection | Same resolution concern as Nerkodui |

---

## Retry Instructions for Claude Code

Wikimedia CDN enforces rate limits when many file downloads occur in a short window. To download the remaining files:

1. Wait at least 10 minutes after the last request.
2. Use `curl.exe --ssl-no-revoke -L -A "AnveshanHackathon/0.1 (research prototype)" -o <local_path> <url>` with **at least 60 seconds** between requests.
3. For the **Hexagonal Origami Box** (188 MB original), use the VP9 240P transcode instead:
   ```
   https://upload.wikimedia.org/wikipedia/commons/transcoded/2/2b/Hexagonal_origami_box_part_1.ogv/Hexagonal_origami_box_part_1.ogv.240p.vp9.webm
   ```
4. For the **floor kolam photos** (McKay Savage series), using the 1000px thumbnail is acceptable for testing:
   ```
   https://upload.wikimedia.org/wikipedia/commons/thumb/9/95/India_-_Kolam_-_06_%282486394060%29.jpg/1000px-India_-_Kolam_-_06_%282486394060%29.jpg
   ```
5. The Hong Kong origami video (25.9 MB) should be attempted first as it is the highest-value missing file:
   ```
   https://upload.wikimedia.org/wikipedia/commons/d/dc/Hong_Kong_Protestors_Make_Paper_Origami_Cranes_to_Protest.webm
   ```

---

## Files Present in `var/kiro/media/`

| File | Bytes | Dimensions | SHA-256 |
|---|---|---|---|
| origami/hk_protesters_crane_fold.webm | 25,873,856 | 1920×1080, 79.9 s | 65E8E2896D13B5EA063A38A7F1B68DDF1509131DE10AAD07CE67C1663C34D86B |
| tabla/tabla_chanderi_1.webm | 7,219,730 | 720×1280, 35 s | 0E0B17B17CC0AFEC6AD043D1006FD41D72E974B1747CF8D65C997B21E665B17B |
| tabla/tabla_chanderi_2.webm | 9,152,801 | 720×1280, 47 s | 289DF988C2CC1547C9A68B2E3650C23C59C982882CF18177B7A1F8875FBE5BBC |
| tabla/tabla_yavagal_sample.webm | 2,160,563 | 1920×1080, 8 s | 8B1BACC129B3B750917AB29CE0B21D277606BE792FBBC2A9A0F436CA0CF0A285 |
| tabla/tabla_kangutkar.webm | 26,301,519 | 1280×720, 4 m 12 s | 9B7AAEDF0907B202A014EE9C95898324A459C84A76A56D32CEC9B2A66633DF81 |
| kolam/india_kolam_06_savage.jpg | 4,297,225 | 3264×2448 px | 74DAE85367D5C437B8910A8FD95F1C9C4C1DCB56464456F3AB8D8099D6182E5B |
| kolam/india_kolam_09_savage.jpg | 281,150 | 960×720 px (thumbnail) | 400E44B833C930C379F12108823AEB08004BDCD30D07BEF6337A0E66C2F6712B |
| kolam/colorful_kolam.jpg | 329,744 | 960×720 px (thumbnail) | FCFBCF0D46B7726246AA963ED991E32DBD678627961C591129C34E7551D2D9E2 |
| kolam/kolam_8_mayoo.png | 90,108 | 600×599 px | 74BBD4C4EA8E6394445894A4D5E99884D4038C912ED58FD7C7E1B89E60E68AC6 |
| kolam/thirukulam_mayoo.png | 38,152 | 600×588 px | 3CF6E1DEC0A7F0DF332C675FBEF5CDB57148A406E9076ABD21F5C254843998AC |
| kolam/thoddil_mayoo.png | 46,293 | 600×545 px | 3C8ECD02BAC23E7B413500078E7FD991378457EB9E32C8AEC6333D73893B046F |
