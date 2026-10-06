"""Held-out validation of the inferred kolam drawing path.

The author's stroke-direction diagram (source.json: ``src.kolam.direction_diagram.v1``,
``used_by_system: false``) is NEVER given to the goal builder. This script is the only place
it is read. It compares the inferred decomposition (built from the target image alone) with
the diagram:

1. registration: diagram -> goal frame by a similarity transform (ink moments + local search);
2. route overlap: diagram line pixels within tau of the inferred line (precision) and inferred
   line samples within tau of diagram ink (recall);
3. arrow direction: the inferred line is cut into dot-to-dot arcs; for each arc the arrowhead
   barbs (ink 3..10 px off the whole inferred line, near one end of the arc) decide which end
   the author's arrow points to; we report how consistently the author's arrows follow the
   inferred traversal direction;
4. an overlay PNG (inferred line in colour over the diagram), kept small.

Usage: python tracks/track-a/eval/kolam_path_validation.py
Writes kolam_path_validation.json and kolam_path_overlay.png next to this script.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tracks.common import kolam_geometry as kg  # noqa: E402
from tracks.common.goals.kolam import KolamGoal, dense_goal, goal_samples, payload_from_image  # noqa: E402

TARGET = ROOT / "tracks/cases/kolam/source/ithayakkamalam_target.jpg"
DIAGRAM = ROOT / "tracks/cases/kolam/source/held_out/ithayakkamalam_direction_diagram.jpg"
HERE = Path(__file__).resolve().parent
BARB_MIN, BARB_MAX = 3.0, 10.0       # px off the inferred line
END_WINDOW = (3.0, 22.0)             # px of arc length from the arc end (diagram arrows stop short of dots)


def main() -> dict:
    payload, _ = payload_from_image(TARGET)
    goal = KolamGoal.model_validate(payload)
    tau = goal.tau
    dense = dense_goal(goal, 1.0)
    samples, _, _ = goal_samples(goal)

    dg = kg.analyze_image(DIAGRAM)
    d_ink_pts = np.argwhere(dg.ink)[:, ::-1].astype(np.float64) / dg.scale
    d_skel = dg.skeleton_points()
    sim = kg.register_similarity(d_skel, [], dense, [], (goal.canvas.height, goal.canvas.width), tau)
    ink_g = sim.apply(d_ink_pts)
    skel_g = sim.apply(d_skel)

    precision = float((kg.min_dists(skel_g, dense) <= tau).mean())
    recall = float((kg.min_dists(samples, ink_g) <= tau).mean())

    # ---- arrow direction per dot-to-dot arc --------------------------------------------
    off = kg.min_dists(ink_g, dense)
    barb = ink_g[(off >= BARB_MIN) & (off <= BARB_MAX)]
    arcs = []
    for c in goal.curves:
        pts = np.asarray(c.points)
        dpos = {d.id: (d.x, d.y) for d in goal.dots}
        idx = []
        for did in c.dot_ids:
            dd = np.hypot(pts[:, 0] - dpos[did][0], pts[:, 1] - dpos[did][1])
            idx.append((int(np.argmin(dd)), did))
        idx.sort()
        n = len(pts)
        for (i0, a), (i1, b) in zip(idx, idx[1:] + ([(idx[0][0] + n, idx[0][1])] if c.closed else [])):
            seq = np.array([pts[j % n] for j in range(i0, i1 + 1)])
            arcs.append((c.id, a, b, seq))
    rows = []
    for cid, a, b, seq in arcs:
        seg = np.hypot(*np.diff(seq, axis=0).T)
        cum = np.concatenate([[0.0], np.cumsum(seg)])
        total = cum[-1]

        def barb_count(near_start: bool) -> int:
            s = cum if near_start else total - cum
            win = seq[(s >= END_WINDOW[0]) & (s <= END_WINDOW[1])]
            if len(win) == 0 or len(barb) == 0:
                return 0
            return int((kg.min_dists(barb, win) <= BARB_MAX).sum())

        hs, he = barb_count(True), barb_count(False)
        if max(hs, he) < 4 or abs(hs - he) < 0.5 * max(hs, he):
            verdict = "unclear"
        else:
            verdict = "forward" if he > hs else "backward"
        rows.append({"curve": cid, "from_dot": a, "to_dot": b, "length_px": round(float(total), 1),
                     "barbs_at_start": hs, "barbs_at_end": he, "author_direction": verdict})
    fwd = sum(r["author_direction"] == "forward" for r in rows)
    bwd = sum(r["author_direction"] == "backward" for r in rows)
    unclear = len(rows) - fwd - bwd
    decided = fwd + bwd

    # ---- overlay -------------------------------------------------------------------------
    base = Image.open(DIAGRAM).convert("L")
    inv = np.array([[np.cos(np.radians(sim.theta_deg)), -np.sin(np.radians(sim.theta_deg))],
                    [np.sin(np.radians(sim.theta_deg)), np.cos(np.radians(sim.theta_deg))]]) * sim.scale
    minv = np.linalg.inv(inv)
    canvas = Image.merge("RGB", [base.point(lambda v: v // 2)] * 3)
    dr = ImageDraw.Draw(canvas)
    for c in goal.curves:
        p = (np.asarray(c.points) - np.array([sim.tx, sim.ty])) @ minv.T
        dr.line([tuple(q) for q in np.vstack([p, p[:1]]).tolist()], fill=(255, 90, 60), width=2)
    for r, (_, _, _, seq) in zip(rows, arcs):
        if r["author_direction"] == "unclear":
            continue
        p = (seq - np.array([sim.tx, sim.ty])) @ minv.T
        mid = p[len(p) // 2]
        col = (80, 255, 80) if r["author_direction"] == "forward" else (80, 160, 255)
        dr.ellipse([mid[0] - 3, mid[1] - 3, mid[0] + 3, mid[1] + 3], fill=col)
    canvas = canvas.resize((360, round(360 * canvas.height / canvas.width)), Image.LANCZOS)
    canvas.convert("P", palette=Image.ADAPTIVE, colors=32).save(HERE / "kolam_path_overlay.png", optimize=True)

    out = {
        "held_out_source": "src.kolam.direction_diagram.v1 (used_by_system: false)",
        "inferred": {"curves": len(goal.curves), "closed": [c.closed for c in goal.curves], "dots": len(goal.dots),
                     "crossings": goal.features.n_crossings, "arcs_dot_to_dot": len(rows), "tau_px": tau},
        "registration": {"scale": round(sim.scale, 4), "theta_deg": round(sim.theta_deg, 2), "tx": round(sim.tx, 2),
                         "ty": round(sim.ty, 2), "score": round(sim.score, 4), "method": sim.method},
        "route_overlap": {"diagram_line_within_tau_of_inferred": round(precision, 4),
                          "inferred_line_within_tau_of_diagram_ink": round(recall, 4)},
        "arrow_direction": {"forward": fwd, "backward": bwd, "unclear": unclear,
                            "consistency_of_decided": round(max(fwd, bwd) / decided, 4) if decided else None,
                            "majority": "forward" if fwd >= bwd else "backward"},
        "arcs": rows,
    }
    (HERE / "kolam_path_validation.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "arcs"}, indent=1))
    return out


if __name__ == "__main__":
    main()
