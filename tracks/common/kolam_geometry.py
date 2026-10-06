"""Deterministic kolam image + geometry routines (numpy + Pillow only).

Shared by the Track A goal builder (``track_a.goals.kolam``) and the Track B evaluator
(``track_b.evaluators.kolam``); Track B must not import Track A, so everything both sides
need lives here. See docs/plans/evaluation-core.md §3.

Pipeline for a finished kolam image (``analyze_image`` + ``decompose_curves``):

1. grayscale -> optional resize (longest side 512 unless already within 384..686 px)
   -> Otsu threshold with auto polarity (ink = the minority class) -> speck removal;
2. exact Euclidean distance transform (brute force over a bounded disk of offsets);
3. pulli (dots): distance-transform peaks clearly wider than the line half width whose
   surrounding ring is mostly empty (a dot with one line through it has two "arms";
   a line crossing has four), plus small isolated round components;
4. line skeleton: ink minus dot disks, Zhang-Suen thinning, short-spur pruning;
5. skeleton graph: junction clusters + dot nodes + pixel chains between them;
6. smooth-continuation decomposition: at every node, pair the incident branches by minimum
   turning angle and follow the pairs into continuous curves (closed loops where possible).

All coordinates returned to callers are in ORIGINAL image pixels (x right, y down).
This is a shared utility, not a contract.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
from PIL import Image, ImageDraw

ALGO_VERSION = "kolam_geometry_v1"

# --- tunable constants (documented in the goal model's built_with) ----------------------
TARGET_LONG_SIDE = 512
NO_RESIZE_RANGE = (384, 686)          # images already in this range are processed unscaled
MIN_SPECK_AREA = 4                    # px; smaller ink components are noise
DOT_PEAK_RATIO = 1.35                 # dot dt-peak must exceed this x median line dt
DOT_RING_MAX = 0.32                   # max ink fraction on the ring just outside a dot
DOT_BIG_RATIO = 2.2                   # peaks this much wider than a line are dots regardless of ring
SPUR_MAX_FACTOR = 2.0                 # prune free-ended branches shorter than this x stroke width
DIR_ARC_PX = 12.0                     # arc length used to estimate a branch direction at a node
SYMMETRY_MIN_SCORE = 0.80             # tolerant overlap needed to accept a symmetry
TAU_MIN_PX = 6.0                      # tolerance band tau = max(6, 1.5 w)
TAU_W_FACTOR = 1.5

Point = Tuple[float, float]


# =========================================================================================
# Image basics
# =========================================================================================


def load_gray(src: Union[str, Path, Image.Image]) -> np.ndarray:
    """Load an image as float32 grayscale in [0, 1] (alpha composited on white)."""
    img = src if isinstance(src, Image.Image) else Image.open(src)
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        img = Image.alpha_composite(bg, rgba)
    return np.asarray(img.convert("L"), dtype=np.float32) / 255.0


def processing_scale(shape: Tuple[int, int]) -> float:
    longest = max(shape)
    if NO_RESIZE_RANGE[0] <= longest <= NO_RESIZE_RANGE[1]:
        return 1.0
    return TARGET_LONG_SIDE / float(longest)


def resize_gray(gray: np.ndarray, scale: float) -> np.ndarray:
    if scale == 1.0:
        return gray
    h, w = gray.shape
    img = Image.fromarray(np.clip(gray * 255.0, 0, 255).astype(np.uint8))
    img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.BILINEAR)
    return np.asarray(img, dtype=np.float32) / 255.0


def otsu_threshold(gray: np.ndarray) -> float:
    hist, edges = np.histogram(gray, bins=256, range=(0.0, 1.0))
    hist = hist.astype(np.float64)
    centers = (edges[:-1] + edges[1:]) / 2.0
    w0 = np.cumsum(hist)
    w1 = w0[-1] - w0
    m0 = np.cumsum(hist * centers)
    mt = m0[-1]
    with np.errstate(divide="ignore", invalid="ignore"):
        mu0 = m0 / w0
        mu1 = (mt - m0) / w1
        between = w0 * w1 * (mu0 - mu1) ** 2
    between = np.nan_to_num(between)
    k = int(np.argmax(between))
    return float(edges[k + 1])


def binarize(gray: np.ndarray) -> Tuple[np.ndarray, Dict[str, object]]:
    """Otsu threshold with auto polarity: the minority class is ink."""
    t = otsu_threshold(gray)
    bright = gray > t
    if bright.mean() <= 0.5:
        ink, polarity = bright, "light_ink_on_dark"
    else:
        ink, polarity = ~bright, "dark_ink_on_light"
    ink = remove_small_components(ink, MIN_SPECK_AREA)
    return ink, {"threshold": round(t, 4), "polarity": polarity}


# =========================================================================================
# Connected components / morphology / distance transform
# =========================================================================================

_N8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def label_components(mask: np.ndarray) -> Tuple[np.ndarray, int]:
    """8-connected component labels (0 = background), labels in raster-scan order."""
    h, w = mask.shape
    wp = w + 2
    padded = np.pad(mask.astype(bool), 1)
    flat = padded.ravel().tolist()
    labels = [0] * len(flat)
    offs = [dy * wp + dx for dy, dx in _N8]
    n = 0
    for i in np.flatnonzero(padded.ravel()).tolist():
        if labels[i]:
            continue
        n += 1
        labels[i] = n
        stack = [i]
        while stack:
            p = stack.pop()
            for o in offs:
                q = p + o
                if flat[q] and not labels[q]:
                    labels[q] = n
                    stack.append(q)
    lab = np.asarray(labels, dtype=np.int32).reshape(h + 2, wp)[1:-1, 1:-1]
    return lab, n


def remove_small_components(mask: np.ndarray, min_area: int) -> np.ndarray:
    lab, n = label_components(mask)
    if n == 0:
        return mask.copy()
    areas = np.bincount(lab.ravel(), minlength=n + 1)
    keep = areas >= min_area
    keep[0] = False
    return keep[lab]


def disk_offsets(radius: float) -> List[Tuple[float, int, int]]:
    r = int(math.ceil(radius))
    out = []
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            d = math.hypot(dx, dy)
            if d <= radius + 1e-9:
                out.append((d, dy, dx))
    out.sort()
    return out


def dilate(mask: np.ndarray, radius: float) -> np.ndarray:
    if radius <= 0:
        return mask.copy()
    h, w = mask.shape
    r = int(math.ceil(radius))
    p = np.pad(mask, r)
    out = np.zeros_like(mask)
    for _, dy, dx in disk_offsets(radius):
        out |= p[r + dy : r + dy + h, r + dx : r + dx + w]
    return out


def distance_transform(mask: np.ndarray, max_r: float = 12.0) -> np.ndarray:
    """Exact Euclidean distance from each ink pixel to the nearest non-ink pixel, clipped at
    ``max_r + 1``. Out-of-image counts as background."""
    h, w = mask.shape
    r = int(math.ceil(max_r))
    bg = np.pad(~mask, r, constant_values=True)
    ys, xs = np.nonzero(mask)
    dist = np.full(ys.shape, float(max_r + 1), dtype=np.float32)
    alive = np.arange(ys.size)
    for d, dy, dx in disk_offsets(max_r):
        if d == 0 or alive.size == 0:
            continue
        hit = bg[ys[alive] + r + dy, xs[alive] + r + dx]
        if hit.any():
            dist[alive[hit]] = d
            alive = alive[~hit]
    out = np.zeros(mask.shape, dtype=np.float32)
    out[ys, xs] = dist
    return out


def thin(mask: np.ndarray) -> np.ndarray:
    """Zhang-Suen thinning (vectorised)."""
    if not mask.any():
        return mask.copy()
    ys, xs = np.nonzero(mask)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    img = np.pad(mask[y0:y1, x0:x1].astype(np.uint8), 1)
    while True:
        changed = False
        for step in (0, 1):
            p2 = img[:-2, 1:-1]; p3 = img[:-2, 2:]; p4 = img[1:-1, 2:]; p5 = img[2:, 2:]
            p6 = img[2:, 1:-1]; p7 = img[2:, :-2]; p8 = img[1:-1, :-2]; p9 = img[:-2, :-2]
            seq = [p2, p3, p4, p5, p6, p7, p8, p9, p2]
            b = sum(seq[:8])
            a = sum(((seq[i] == 0) & (seq[i + 1] == 1)).astype(np.uint8) for i in range(8))
            c = img[1:-1, 1:-1] == 1
            if step == 0:
                cond = c & (b >= 2) & (b <= 6) & (a == 1) & (p2 * p4 * p6 == 0) & (p4 * p6 * p8 == 0)
            else:
                cond = c & (b >= 2) & (b <= 6) & (a == 1) & (p2 * p4 * p8 == 0) & (p2 * p6 * p8 == 0)
            if cond.any():
                img[1:-1, 1:-1][cond] = 0
                changed = True
        if not changed:
            break
    out = np.zeros_like(mask)
    out[y0:y1, x0:x1] = img[1:-1, 1:-1].astype(bool)
    return out


def neighbour_count(mask: np.ndarray) -> np.ndarray:
    p = np.pad(mask.astype(np.uint8), 1)
    h, w = mask.shape
    return sum(p[1 + dy : 1 + dy + h, 1 + dx : 1 + dx + w] for dy, dx in _N8)


# =========================================================================================
# Dots
# =========================================================================================


@dataclass
class Dot:
    x: float
    y: float
    r: float
    kind: str = "peak"     # "peak" (on a line) | "isolated" (separate component)


def _ring_fraction(ink: np.ndarray, x: int, y: int, r0: float, r1: float) -> float:
    h, w = ink.shape
    rr = int(math.ceil(r1))
    yy, xx = np.mgrid[-rr : rr + 1, -rr : rr + 1]
    d = np.hypot(xx, yy)
    sel = (d >= r0) & (d <= r1)
    py, px = yy[sel] + y, xx[sel] + x
    inside = (py >= 0) & (py < h) & (px >= 0) & (px < w)
    vals = np.zeros(py.shape, dtype=bool)
    vals[inside] = ink[py[inside], px[inside]]
    return float(vals.mean()) if vals.size else 1.0


def detect_dots(ink: np.ndarray, dt: np.ndarray, line_dt: float) -> List[Dot]:
    """Pulli detection: wide distance-transform peaks with a mostly empty surrounding ring,
    plus small isolated round components."""
    h, w = ink.shape
    thr = max(DOT_PEAK_RATIO * line_dt, line_dt + 0.8)
    p = np.pad(dt, 2)
    mx = np.zeros_like(dt)
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            mx = np.maximum(mx, p[2 + dy : 2 + dy + h, 2 + dx : 2 + dx + w])
    peaks = (dt >= thr) & (dt >= mx)
    ys, xs = np.nonzero(peaks)
    order = sorted(range(ys.size), key=lambda i: (-float(dt[ys[i], xs[i]]), int(ys[i]), int(xs[i])))
    dots: List[Dot] = []
    for i in order:
        y, x = int(ys[i]), int(xs[i])
        r = float(dt[y, x])
        if any(math.hypot(d.x - x, d.y - y) < d.r + r for d in dots):
            continue
        # refine centre: centroid of the plateau of near-peak dt values within radius r
        win = max(1, int(round(r)))
        y0, y1, x0, x1 = max(0, y - win), min(h, y + win + 1), max(0, x - win), min(w, x + win + 1)
        sub = dt[y0:y1, x0:x1]
        m = sub >= (r - 0.75)
        sy, sx = np.nonzero(m)
        cy, cx = float(sy.mean() + y0), float(sx.mean() + x0)
        ring = _ring_fraction(ink, int(round(cx)), int(round(cy)), r + 1.5, r + 3.0)
        if ring <= DOT_RING_MAX or r >= DOT_BIG_RATIO * line_dt:
            dots.append(Dot(cx, cy, r + 0.5, "peak"))
    # isolated small round components (dots not touched by any line)
    lab, n = label_components(ink)
    if n:
        max_area = math.pi * (4.0 * max(line_dt, 1.0)) ** 2
        areas = np.bincount(lab.ravel(), minlength=n + 1)
        min_area = math.pi * (0.9 * max(line_dt, 1.0)) ** 2
        for k in np.flatnonzero((areas <= max_area) & (areas >= min_area)).tolist():
            if k == 0:
                continue
            cy_, cx_ = np.nonzero(lab == k)
            area = cy_.size
            hgt, wid = cy_.max() - cy_.min() + 1, cx_.max() - cx_.min() + 1
            if max(hgt, wid) > 1.6 * min(hgt, wid):
                continue
            cx0, cy0 = float(cx_.mean()), float(cy_.mean())
            if any(math.hypot(d.x - cx0, d.y - cy0) < d.r + 2 for d in dots):
                continue
            dots.append(Dot(cx0, cy0, math.sqrt(area / math.pi), "isolated"))
    dots.sort(key=lambda d: (round(d.y), round(d.x)))
    return dots


# =========================================================================================
# Skeleton graph and curve decomposition
# =========================================================================================


@dataclass
class Chain:
    pixels: np.ndarray            # (n, 2) as (x, y) processed coords, ordered
    ends: List[Optional[Tuple[str, int]]] = field(default_factory=lambda: [None, None])  # node per end


@dataclass
class KolamAnalysis:
    shape: Tuple[int, int]        # original (h, w)
    scale: float                  # processed = original * scale
    ink: np.ndarray               # processed-scale ink mask
    threshold: Dict[str, object]
    line_dt: float                # median distance-transform value on the line skeleton (processed px)
    stroke_width: float           # line width in ORIGINAL px
    dots: List[Dot]               # ORIGINAL px
    skeleton: np.ndarray          # processed-scale line skeleton (dots removed)
    lines: np.ndarray             # processed-scale line ink (dots removed)

    @property
    def tau(self) -> float:
        return max(TAU_MIN_PX, TAU_W_FACTOR * self.stroke_width)

    def skeleton_points(self) -> np.ndarray:
        """Line skeleton pixels in ORIGINAL coordinates, (n, 2) as (x, y)."""
        ys, xs = np.nonzero(self.skeleton)
        return np.stack([xs, ys], axis=1).astype(np.float64) / self.scale


def crossing_number(mask: np.ndarray) -> np.ndarray:
    """Number of 0->1 transitions around each pixel (8-ring). 1 = line end, 2 = line interior
    (including staircase corners), >= 3 = junction. Zero outside the mask."""
    p = np.pad(mask.astype(np.uint8), 1)
    h, w = mask.shape
    ring = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
    vals = [p[1 + dy : 1 + dy + h, 1 + dx : 1 + dx + w] for dy, dx in ring]
    vals.append(vals[0])
    a = sum(((vals[i] == 0) & (vals[i + 1] == 1)).astype(np.uint8) for i in range(8))
    nb = sum(vals[:8])
    a = np.where((nb >= 1) & (a == 0), 2, a)   # fully surrounded pixel: interior of a blob
    return a * mask


def prune_spurs(skel: np.ndarray, max_len: int) -> np.ndarray:
    """Remove free-ended branches of at most ``max_len`` pixels that end at a junction."""
    s = skel.copy()
    cn = crossing_number(s)
    h, w = s.shape
    for y, x in np.argwhere(cn == 1).tolist():
        path = [(y, x)]
        seen = {(y, x)}
        cur = (y, x)
        at_junction = False
        while len(path) <= max_len:
            cy, cx = cur
            nbrs = [(cy + dy, cx + dx) for dy, dx in _N8
                    if 0 <= cy + dy < h and 0 <= cx + dx < w and s[cy + dy, cx + dx] and (cy + dy, cx + dx) not in seen]
            if not nbrs:
                break
            if any(cn[q] >= 3 for q in nbrs):
                at_junction = True
                break
            four = [q for q in nbrs if q[0] == cy or q[1] == cx]
            cur = sorted(four or nbrs)[0]
            seen.update(nbrs)       # staircase neighbours belong to the same branch
            path.append(cur)
        if at_junction and len(path) <= max_len:
            for q in path:
                s[q] = False
    return s


def analyze_image(src: Union[str, Path, Image.Image, np.ndarray]) -> KolamAnalysis:
    """Binarize, measure stroke width, detect dots and skeletonise the line work."""
    gray = src if isinstance(src, np.ndarray) else load_gray(src)
    shape = gray.shape
    scale = processing_scale(shape)
    g = resize_gray(gray, scale)
    ink, thr = binarize(g)
    dt = distance_transform(ink, 12.0)
    skel_all = thin(ink)
    line_dt = float(np.median(dt[skel_all])) if skel_all.any() else 1.0
    dots_p = detect_dots(ink, dt, line_dt)
    # remove dot disks before skeletonising the lines
    lines = ink.copy()
    if dots_p:
        h, w = ink.shape
        yy, xx = np.mgrid[0:h, 0:w]
        for d in dots_p:
            rr = d.r + 1.0
            y0, y1 = max(0, int(d.y - rr - 1)), min(h, int(d.y + rr + 2))
            x0, x1 = max(0, int(d.x - rr - 1)), min(w, int(d.x + rr + 2))
            sub = (xx[y0:y1, x0:x1] - d.x) ** 2 + (yy[y0:y1, x0:x1] - d.y) ** 2 <= rr * rr
            lines[y0:y1, x0:x1] &= ~sub
    lines = remove_small_components(lines, MIN_SPECK_AREA)
    skel = thin(lines)
    width_p = float(lines.sum()) / max(1.0, float(skel.sum())) if skel.any() else 2.0 * line_dt
    skel = prune_spurs(skel, int(max(4, round(SPUR_MAX_FACTOR * width_p))))
    dots = [Dot(d.x / scale, d.y / scale, d.r / scale, d.kind) for d in dots_p]
    return KolamAnalysis(shape=shape, scale=scale, ink=ink, threshold=thr, line_dt=line_dt,
                         stroke_width=width_p / scale, dots=dots, skeleton=skel, lines=lines)


def _order_component(pix: List[Tuple[int, int]]) -> Tuple[List[Tuple[int, int]], bool]:
    """Order the pixels of a thin chain. Returns (ordered (y, x) list, closed?)."""
    pset = set(pix)

    def nbrs(p):
        y, x = p
        four = [(y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)]
        diag = [(y - 1, x - 1), (y - 1, x + 1), (y + 1, x - 1), (y + 1, x + 1)]
        return [q for q in four if q in pset], [q for q in diag if q in pset]

    ring = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]

    def transitions(p):
        y, x = p
        v = [(y + dy, x + dx) in pset for dy, dx in ring]
        return sum(1 for i in range(8) if not v[i] and v[(i + 1) % 8])

    ends = sorted(p for p in pix if transitions(p) <= 1)
    closed = not ends
    start = ends[0] if ends else min(pix)
    order = [start]
    seen = {start}
    cur = start
    while True:
        four, diag = nbrs(cur)
        cand = [q for q in four if q not in seen] or [q for q in diag if q not in seen]
        if not cand:
            break
        cand.sort()
        cur = cand[0]
        order.append(cur)
        seen.add(cur)
    if closed:
        first = order[0]
        last = order[-1]
        if max(abs(first[0] - last[0]), abs(first[1] - last[1])) > 1:
            closed = False
    return order, closed


def _direction(points: np.ndarray, arc: float) -> np.ndarray:
    """Unit vector from points[0] towards the point ``arc`` px along the polyline."""
    if len(points) < 2:
        return np.array([0.0, 0.0])
    seg = np.hypot(*np.diff(points, axis=0).T)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    target = min(arc, cum[-1])
    k = int(np.searchsorted(cum, target))
    k = min(max(k, 1), len(points) - 1)
    v = points[k] - points[0]
    n = float(np.hypot(*v))
    return v / n if n > 0 else np.array([0.0, 0.0])


def _best_pairing(dirs: List[np.ndarray]) -> List[Tuple[int, int]]:
    """Pair branch ends at a node by minimum total turning angle (straight-through = 0)."""
    n = len(dirs)
    idx = list(range(n))

    def cost(i, j):
        c = float(np.clip(-np.dot(dirs[i], dirs[j]), -1.0, 1.0))
        return math.acos(c)

    if n <= 1:
        return []
    if n > 10:  # greedy fallback
        pairs, left = [], set(idx)
        allp = sorted(((cost(i, j), i, j) for i, j in combinations(idx, 2)))
        for _, i, j in allp:
            if i in left and j in left:
                pairs.append((i, j)); left -= {i, j}
        return pairs

    best: Tuple[float, List[Tuple[int, int]]] = (float("inf"), [])

    def rec(rem: List[int], acc: List[Tuple[int, int]], total: float, skips: int):
        nonlocal best
        if total >= best[0]:
            return
        if len(rem) <= 1 or (len(rem) == 0):
            if len(rem) == 1 and skips >= 1:
                return
            best = (total, list(acc))
            return
        a = rem[0]
        for b in rem[1:]:
            rest = [r for r in rem if r not in (a, b)]
            acc.append((a, b))
            rec(rest, acc, total + cost(a, b), skips)
            acc.pop()
        if n % 2 == 1 and skips == 0:   # odd degree: one end stays unpaired
            rec(rem[1:], acc, total + math.pi / 2, skips + 1)

    rec(idx, [], 0.0, 0)
    return best[1]


@dataclass
class Decomposition:
    curves: List[np.ndarray]          # ORIGINAL px, (n, 2) ordered, closed curves not repeating start
    closed: List[bool]
    n_junctions: int
    junction_degrees: Dict[int, int]
    free_endpoints: int


def _block_junctions(skel: np.ndarray) -> np.ndarray:
    """2x2 skeleton blocks with >= 3 branches leaving them (an X crossing that thinning
    collapsed into a block; its pixels have only 2 transitions each)."""
    h, w = skel.shape
    out = np.zeros_like(skel)
    blk = skel[:-1, :-1] & skel[:-1, 1:] & skel[1:, :-1] & skel[1:, 1:]
    ring = [(-1, -1), (-1, 0), (-1, 1), (-1, 2), (0, 2), (1, 2), (2, 2), (2, 1), (2, 0), (2, -1), (1, -1), (0, -1)]
    for y, x in np.argwhere(blk).tolist():
        v = [0 <= y + dy < h and 0 <= x + dx < w and bool(skel[y + dy, x + dx]) for dy, dx in ring]
        runs = sum(1 for i in range(12) if not v[i] and v[(i + 1) % 12])
        if runs >= 3:
            out[y : y + 2, x : x + 2] = True
    return out


def decompose_curves(an: KolamAnalysis) -> Decomposition:
    """Skeleton graph -> continuous curves by smooth continuation at every node."""
    skel = an.skeleton
    h, w = skel.shape
    width_p = an.stroke_width * an.scale
    # junction: >= 3 branch transitions, or >= 4 neighbours (thinning can leave a 2x2 block
    # at an X crossing whose pixels have only 2 transitions each)
    junction = (crossing_number(skel) >= 3) | _block_junctions(skel)
    rj = max(2.0, round(width_p) + 1.0)
    dots_p = [(d.x * an.scale, d.y * an.scale, d.r * an.scale) for d in an.dots]
    dot_attach = [r + 4.0 * width_p + 4.0 for _, _, r in dots_p]
    # Junction clusters that end up with fewer than 3 incident branches are thinning artefacts
    # (2x2 blocks along a line, ragged line ends next to a removed dot disk): dissolve them
    # and rebuild so the chain runs through.
    for _ in range(4):
        jregion = dilate(junction, rj)
        jlab, nj = label_components(jregion)
        chains = _build_chains(skel, jlab, dots_p, dot_attach)
        deg = np.zeros(nj + 1, dtype=int)
        for ch in chains:
            for e in ch.ends:
                if isinstance(e, tuple) and e[0] == "j":
                    deg[e[1]] += 1
        weak = [k for k in range(1, nj + 1) if deg[k] < 3]
        if not weak:
            break
        junction = junction & ~np.isin(jlab, weak)
    centres: Dict[int, np.ndarray] = {}
    for k in range(1, nj + 1):
        ys, xs = np.nonzero(junction & (jlab == k))
        if ys.size == 0:
            ys, xs = np.nonzero(jlab == k)
        centres[k] = np.array([xs.mean(), ys.mean()])

    # A crossing right next to a dot can leave no skeleton between them (the junction zone
    # and the removed dot disk overlap). Link an odd-degree dot to the nearest odd-degree
    # junction within reach by a straight bridge chain.
    deg_n: Dict[Tuple[str, int], int] = {}
    for ch in chains:
        if ch.ends[0] == "closed":
            continue
        for e in ch.ends:
            if e is not None:
                deg_n[e] = deg_n.get(e, 0) + 1
    used_j: set = set()
    for i, (dx, dy, r) in enumerate(dots_p):
        if deg_n.get(("d", i), 0) % 2 == 0:
            continue
        best = None
        for k in range(1, nj + 1):
            if deg_n.get(("j", k), 0) % 2 == 0 or k in used_j:
                continue
            dd = math.hypot(centres[k][0] - dx, centres[k][1] - dy)
            if dd <= r + rj + 2.0 * width_p + 6.0 and (best is None or dd < best[0]):
                best = (dd, k)
        if best is not None:
            k = best[1]
            n = max(3, int(math.ceil(best[0])) + 1)
            pts = np.stack([np.linspace(centres[k][0], dx, n), np.linspace(centres[k][1], dy, n)], axis=1)
            ch = Chain(pts)
            ch.ends = [("j", k), ("d", i)]
            chains.append(ch)
            used_j.add(k)
            deg_n[("j", k)] = deg_n.get(("j", k), 0) + 1
            deg_n[("d", i)] = deg_n.get(("d", i), 0) + 1

    # gather ends per node
    node_ends: Dict[Tuple[str, int], List[Tuple[int, int, np.ndarray]]] = {}
    for ci, ch in enumerate(chains):
        if ch.ends[0] == "closed":
            continue
        for e in (0, 1):
            node = ch.ends[e]
            if node is None:
                continue
            pts = ch.pixels if e == 0 else ch.pixels[::-1]
            node_ends.setdefault(node, []).append((ci, e, _direction(pts, DIR_ARC_PX)))
    return _assemble(an, chains, node_ends, centres, dots_p, nj)


def _build_chains(skel: np.ndarray, jlab: np.ndarray, dots_p: List[Tuple[float, float, float]],
                  dot_attach: List[float]) -> List[Chain]:
    h, w = skel.shape
    clab, nc = label_components(skel & (jlab == 0))
    chains: List[Chain] = []
    ys_all, xs_all = np.nonzero(clab)
    labs = clab[ys_all, xs_all]
    order = np.argsort(labs, kind="stable")
    ys_all, xs_all, labs = ys_all[order], xs_all[order], labs[order]
    bounds = np.searchsorted(labs, np.arange(1, nc + 2))
    for k in range(nc):
        a, b = bounds[k], bounds[k + 1]
        if b - a < 3:
            continue
        pix = list(zip(ys_all[a:b].tolist(), xs_all[a:b].tolist()))
        ordered, closed = _order_component(pix)
        arr = np.array([[x, y] for y, x in ordered], dtype=np.float64)
        ch = Chain(arr)
        if not closed:
            for e, (py, px) in enumerate((ordered[0], ordered[-1])):
                node = None
                y0, y1, x0, x1 = max(0, py - 2), min(h, py + 3), max(0, px - 2), min(w, px + 3)
                labs_near = jlab[y0:y1, x0:x1]
                vals = labs_near[labs_near > 0]
                if vals.size:
                    node = ("j", int(np.bincount(vals).argmax()))
                else:
                    # a dot ahead of the free end (thinning retreats line ends from the removed disk)
                    inward = _direction(arr if e == 0 else arr[::-1], DIR_ARC_PX)
                    best_d, best_i = None, None
                    for i, (dx, dy, _) in enumerate(dots_p):
                        dd = math.hypot(dx - px, dy - py)
                        if dd <= dot_attach[i] and (best_d is None or dd < best_d):
                            ahead = -((dx - px) * inward[0] + (dy - py) * inward[1]) / max(dd, 1e-6)
                            if dd <= dots_p[i][2] + 2.0 or ahead >= 0.5:
                                best_d, best_i = dd, i
                    if best_i is not None:
                        node = ("d", best_i)
                ch.ends[e] = node
        else:
            ch.ends = ["closed", "closed"]  # type: ignore[list-item]
        chains.append(ch)
    return chains


def _assemble(an: KolamAnalysis, chains: List[Chain],
              node_ends: Dict[Tuple[str, int], List[Tuple[int, int, np.ndarray]]],
              centres: Dict[int, np.ndarray], dots_p: List[Tuple[float, float, float]], nj: int) -> "Decomposition":
    pair: Dict[Tuple[int, int], Tuple[int, int]] = {}
    node_point: Dict[Tuple[str, int], np.ndarray] = {}
    degrees: Dict[int, int] = {}
    for node in sorted(node_ends):
        ends = node_ends[node]
        degrees[len(ends)] = degrees.get(len(ends), 0) + 1
        node_point[node] = centres[node[1]] if node[0] == "j" else np.array(dots_p[node[1]][:2])
        for i, j in _best_pairing([d for _, _, d in ends]):
            a, b = (ends[i][0], ends[i][1]), (ends[j][0], ends[j][1])
            pair[a] = b
            pair[b] = a

    free = sum(1 for ch in chains if ch.ends[0] != "closed" for e in (0, 1) if ch.ends[e] is None)
    free +=sum(1 for node, ends in node_ends.items() for (ci, e, _) in ends if (ci, e) not in pair)

    visited = [False] * len(chains)
    curves: List[np.ndarray] = []
    closed_flags: List[bool] = []

    def walk(ci: int, entry: int) -> Tuple[List[np.ndarray], bool, Tuple[int, int]]:
        segs: List[np.ndarray] = []
        start = (ci, entry)
        cur, ent = ci, entry
        while True:
            visited[cur] = True
            pts = chains[cur].pixels if ent == 0 else chains[cur].pixels[::-1]
            segs.append(pts)
            exit_end = 1 - ent
            nxt = pair.get((cur, exit_end))
            if nxt is None:
                return segs, False, (cur, exit_end)
            node = chains[cur].ends[exit_end]
            segs.append(node_point[node][None, :])
            if nxt == start:
                return segs, True, start
            if visited[nxt[0]]:
                return segs, False, (cur, exit_end)
            cur, ent = nxt

    chain_order = sorted(range(len(chains)), key=lambda i: (float(chains[i].pixels[:, 1].min()),
                                                              float(chains[i].pixels[:, 0].min())))
    for ci in chain_order:
        if visited[ci]:
            continue
        ch = chains[ci]
        if ch.ends[0] == "closed":
            visited[ci] = True
            curves.append(ch.pixels.copy())
            closed_flags.append(True)
            continue
        segs, closed, _ = walk(ci, 0)
        if not closed:
            back = pair.get((ci, 0))
            if back is not None and not visited[back[0]]:
                bsegs, _, _ = walk(back[0], back[1])
                node = ch.ends[0]
                rev = [s[::-1] for s in reversed(bsegs)]
                segs = rev + [node_point[node][None, :]] + segs
        pts = np.concatenate(segs, axis=0)
        curves.append(pts)
        closed_flags.append(closed)

    out_curves = []
    for pts, closed in zip(curves, closed_flags):
        pts = pts / an.scale
        pts = resample_polyline(pts, 2.0, closed)
        pts = smooth_polyline(pts, closed, 1)
        pts = canonical_orientation(pts, closed)
        out_curves.append(pts)
    keyed = sorted(zip(out_curves, closed_flags), key=lambda t: (round(float(t[0][0, 1]), 1), round(float(t[0][0, 0]), 1)))
    return Decomposition(
        curves=[c for c, _ in keyed], closed=[f for _, f in keyed], n_junctions=nj,
        junction_degrees=dict(sorted(degrees.items())), free_endpoints=int(free),
    )


# =========================================================================================
# Polylines
# =========================================================================================


def resample_polyline(points: np.ndarray, step: float, closed: bool = False) -> np.ndarray:
    pts = np.asarray(points, dtype=np.float64)
    if len(pts) < 2:
        return pts.copy()
    if closed:
        pts = np.vstack([pts, pts[:1]])
    seg = np.hypot(*np.diff(pts, axis=0).T)
    keep = np.concatenate([[True], seg > 1e-9])
    pts = pts[keep]
    seg = np.hypot(*np.diff(pts, axis=0).T)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    total = cum[-1]
    if total <= 0:
        return pts[:1].copy()
    n = max(2, int(math.floor(total / step)) + 1)
    if closed:
        s = np.linspace(0.0, total, n, endpoint=False)
    else:
        s = np.linspace(0.0, total, n)
    x = np.interp(s, cum, pts[:, 0])
    y = np.interp(s, cum, pts[:, 1])
    return np.stack([x, y], axis=1)


def smooth_polyline(points: np.ndarray, closed: bool, half: int = 1) -> np.ndarray:
    if half <= 0 or len(points) < 2 * half + 2:
        return points.copy()
    k = 2 * half + 1
    if closed:
        ext = np.vstack([points[-half:], points, points[:half]])
        kernel = np.ones(k) / k
        x = np.convolve(ext[:, 0], kernel, mode="valid")
        y = np.convolve(ext[:, 1], kernel, mode="valid")
        return np.stack([x, y], axis=1)
    out = points.copy()
    for i in range(half, len(points) - half):
        out[i] = points[i - half : i + half + 1].mean(axis=0)
    return out


def signed_area(points: np.ndarray) -> float:
    x, y = points[:, 0], points[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def canonical_orientation(points: np.ndarray, closed: bool) -> np.ndarray:
    """Closed: clockwise on screen (y down => positive shoelace area), start at the topmost
    point (ties: leftmost). Open: start at the end that is topmost."""
    pts = np.asarray(points, dtype=np.float64)
    if len(pts) < 3:
        return pts
    if closed:
        if signed_area(pts) < 0:
            pts = pts[::-1]
        key = np.lexsort((pts[:, 0], np.round(pts[:, 1], 6)))
        i = int(key[0])
        return np.vstack([pts[i:], pts[:i]])
    a, b = pts[0], pts[-1]
    if (b[1], b[0]) < (a[1], a[0]):
        pts = pts[::-1]
    return pts


def polyline_length(points: np.ndarray, closed: bool = False) -> float:
    pts = np.vstack([points, points[:1]]) if closed else points
    return float(np.hypot(*np.diff(pts, axis=0).T).sum()) if len(pts) > 1 else 0.0


def min_dists(a: np.ndarray, b: np.ndarray, chunk: int = 1024) -> np.ndarray:
    """For each point in ``a`` the Euclidean distance to the nearest point in ``b``."""
    a = np.asarray(a, dtype=np.float64).reshape(-1, 2)
    b = np.asarray(b, dtype=np.float64).reshape(-1, 2)
    if a.size == 0:
        return np.zeros(0)
    if b.size == 0:
        return np.full(len(a), np.inf)
    out = np.empty(len(a))
    for i in range(0, len(a), chunk):
        aa = a[i : i + chunk]
        d2 = (aa[:, None, 0] - b[None, :, 0]) ** 2 + (aa[:, None, 1] - b[None, :, 1]) ** 2
        out[i : i + chunk] = np.sqrt(d2.min(axis=1))
    return out


def densify_strokes(strokes: Sequence[np.ndarray], step: float = 1.0) -> List[np.ndarray]:
    return [resample_polyline(s, step, False) if len(s) > 1 else np.asarray(s, dtype=np.float64) for s in strokes]


def winding_number(point: Point, poly: np.ndarray) -> int:
    x, y = point
    pts = np.vstack([poly, poly[:1]])
    wn = 0
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        if y0 <= y:
            if y1 > y and (x1 - x0) * (y - y0) - (x - x0) * (y1 - y0) > 0:
                wn += 1
        elif y1 <= y and (x1 - x0) * (y - y0) - (x - x0) * (y1 - y0) < 0:
            wn -= 1
    return wn


# =========================================================================================
# Dot relations, symmetry
# =========================================================================================


def dot_relations(dots: Sequence[Dot], curves: Sequence[np.ndarray], closed: Sequence[bool],
                  stroke_width: float) -> List[Dict[str, object]]:
    """on_line: a curve passes within (r + w) of the centre; enclosed: inside a closed curve;
    free: neither."""
    allpts = np.concatenate(curves, axis=0) if curves else np.zeros((0, 2))
    out = []
    for d in dots:
        dist = float(min_dists(np.array([[d.x, d.y]]), allpts)[0]) if len(allpts) else float("inf")
        if dist <= d.r + stroke_width:
            rel = "on_line"
        elif any(c and winding_number((d.x, d.y), crv) != 0 for crv, c in zip(curves, closed)):
            rel = "enclosed"
        else:
            rel = "free"
        out.append({"relation": rel, "line_distance": round(dist, 2)})
    return out


def _transform_hits(pts: np.ndarray, target: np.ndarray, mats: np.ndarray, centre: np.ndarray) -> float:
    h, w = target.shape
    q = (pts - centre) @ mats.T + centre
    xi = np.round(q[:, 0]).astype(int)
    yi = np.round(q[:, 1]).astype(int)
    ok = (xi >= 0) & (xi < w) & (yi >= 0) & (yi < h)
    hits = np.zeros(len(pts), dtype=bool)
    hits[ok] = target[yi[ok], xi[ok]]
    return float(hits.mean()) if len(pts) else 0.0


def estimate_symmetry(an: KolamAnalysis, max_order: int = 12) -> Dict[str, object]:
    """Rotational order n (2..max_order) and mirror axes from tolerant ink overlap about the
    dot centroid (or ink centroid when fewer than 3 dots)."""
    ink = an.ink
    ys, xs = np.nonzero(ink)
    pts = np.stack([xs, ys], axis=1).astype(np.float64)
    if len(an.dots) >= 3:
        centre = np.array([np.mean([d.x for d in an.dots]), np.mean([d.y for d in an.dots])]) * an.scale
    else:
        centre = pts.mean(axis=0)
    target = dilate(ink, max(1.0, round(an.line_dt)))
    rot_scores: Dict[int, float] = {}
    for n in range(2, max_order + 1):
        th = 2 * math.pi / n
        m = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
        rot_scores[n] = round(_transform_hits(pts, target, m, centre), 4)
    order = 1
    for n in range(max_order, 1, -1):
        if rot_scores[n] >= SYMMETRY_MIN_SCORE:
            order = n
            break
    mirror_scores: List[Tuple[float, float]] = []
    for k in range(0, 360):
        phi = math.radians(k * 0.5)
        c2, s2 = math.cos(2 * phi), math.sin(2 * phi)
        m = np.array([[c2, s2], [s2, -c2]])
        mirror_scores.append((k * 0.5, _transform_hits(pts, target, m, centre)))
    axes = []
    vals = [s for _, s in mirror_scores]
    nn = len(vals)
    for i, (ang, s) in enumerate(mirror_scores):
        if s >= SYMMETRY_MIN_SCORE and s >= vals[(i - 1) % nn] and s > vals[(i + 1) % nn]:
            axes.append(ang)
    best_mirror = max(vals)
    return {
        "rotation_order": order,
        "mirror_axes_deg": axes,
        "centre": [round(float(centre[0] / an.scale), 2), round(float(centre[1] / an.scale), 2)],
        "scores": {
            "rotation": {str(k): v for k, v in rot_scores.items()},
            "best_mirror": round(best_mirror, 4),
            "threshold": SYMMETRY_MIN_SCORE,
        },
    }


# =========================================================================================
# Rendering and registration (photo path)
# =========================================================================================


def render(size: Tuple[int, int], strokes: Sequence[np.ndarray], width: float,
           dots: Sequence[Dot] = (), *, ink_value: int = 255, bg_value: int = 0,
           closed: Optional[Sequence[bool]] = None) -> Image.Image:
    """Render polylines (+ dots) as an 8-bit grayscale image of ``size`` = (w, h)."""
    img = Image.new("L", size, bg_value)
    dr = ImageDraw.Draw(img)
    iw = max(1, int(round(width)))
    for i, s in enumerate(strokes):
        pts = np.asarray(s, dtype=np.float64)
        if closed is not None and closed[i] and len(pts) > 2:
            pts = np.vstack([pts, pts[:1]])
        if len(pts) == 1:
            x, y = pts[0]
            dr.ellipse([x - iw / 2, y - iw / 2, x + iw / 2, y + iw / 2], fill=ink_value)
            continue
        dr.line([tuple(p) for p in pts.tolist()], fill=ink_value, width=iw, joint="curve")
        for x, y in (pts[0], pts[-1]):
            dr.ellipse([x - iw / 2, y - iw / 2, x + iw / 2, y + iw / 2], fill=ink_value)
    for d in dots:
        dr.ellipse([d.x - d.r, d.y - d.r, d.x + d.r, d.y + d.r], fill=ink_value)
    return img


@dataclass
class Similarity:
    scale: float
    theta_deg: float
    tx: float
    ty: float
    score: float
    method: str

    def apply(self, pts: np.ndarray) -> np.ndarray:
        th = math.radians(self.theta_deg)
        m = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]]) * self.scale
        return np.asarray(pts, dtype=np.float64) @ m.T + np.array([self.tx, self.ty])


def register_similarity(src_pts: np.ndarray, src_dots: Sequence[Dot], dst_pts: np.ndarray,
                        dst_dots: Sequence[Dot], dst_shape: Tuple[int, int], tol: float) -> Similarity:
    """Similarity transform mapping learner (src) coordinates into goal (dst) coordinates.

    Translation from the dot centroids, scale from the RMS dot radius ratio (ink centroid /
    RMS ink radius when dots are unusable), rotation by exhaustive search (2 deg, then 0.25 deg)
    maximising the mean of tolerant precision and recall. Mirror images are not searched."""
    use_dots = len(src_dots) >= 3 and len(dst_dots) >= 3 and 0.7 <= len(src_dots) / len(dst_dots) <= 1.43
    if use_dots:
        sd = np.array([[d.x, d.y] for d in src_dots])
        dd = np.array([[d.x, d.y] for d in dst_dots])
        sc, dc = sd.mean(axis=0), dd.mean(axis=0)
        s = math.sqrt(((dd - dc) ** 2).sum(axis=1).mean()) / max(1e-6, math.sqrt(((sd - sc) ** 2).sum(axis=1).mean()))
        method = "dots"
    else:
        sc, dc = src_pts.mean(axis=0), dst_pts.mean(axis=0)
        s = math.sqrt(((dst_pts - dc) ** 2).sum(axis=1).mean()) / max(1e-6, math.sqrt(((src_pts - sc) ** 2).sum(axis=1).mean()))
        method = "ink_moments"
    h, w = dst_shape
    dst_mask = np.zeros((h, w), dtype=bool)
    di = np.round(dst_pts).astype(int)
    ok = (di[:, 0] >= 0) & (di[:, 0] < w) & (di[:, 1] >= 0) & (di[:, 1] < h)
    dst_mask[di[ok, 1], di[ok, 0]] = True
    dst_tol = dilate(dst_mask, tol)
    rng = np.random.default_rng(0)
    sp = src_pts if len(src_pts) <= 800 else src_pts[np.sort(rng.choice(len(src_pts), 800, replace=False))]
    dp = dst_pts if len(dst_pts) <= 400 else dst_pts[np.sort(rng.choice(len(dst_pts), 400, replace=False))]

    def score(theta: float, scale: float, dx: float = 0.0, dy: float = 0.0) -> float:
        th = math.radians(theta)
        m = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]]) * scale
        q = (sp - sc) @ m.T + dc + np.array([dx, dy])
        qi = np.round(q).astype(int)
        okq = (qi[:, 0] >= 0) & (qi[:, 0] < w) & (qi[:, 1] >= 0) & (qi[:, 1] < h)
        prec = np.zeros(len(q), dtype=bool)
        prec[okq] = dst_tol[qi[okq, 1], qi[okq, 0]]
        rec = min_dists(dp, q) <= tol
        return 0.5 * (float(prec.mean()) + float(rec.mean()))

    best = max((score(float(t), s), -float(t)) for t in np.arange(0.0, 360.0, 2.0))
    best_s, best_t, best_k, bx, by = best[0], -best[1], 1.0, 0.0, 0.0
    # local refinement: rotation, scale (+-15 %), translation (+-6 px), coordinate ascent
    for _ in range(3):
        improved = False
        for t in np.arange(best_t - 2.0, best_t + 2.0001, 0.25):
            v = score(float(t), s * best_k, bx, by)
            if v > best_s + 1e-9:
                best_s, best_t, improved = v, float(t), True
        for kf in np.arange(0.85, 1.1501, 0.01):
            v = score(best_t, s * float(kf), bx, by)
            if v > best_s + 1e-9:
                best_s, best_k, improved = v, float(kf), True
        for step in (2.0, 1.0):
            cx, cy = bx, by
            for dx in np.arange(-6.0, 6.01, step) if step == 2.0 else (-1.0, 0.0, 1.0):
                for dy in np.arange(-6.0, 6.01, step) if step == 2.0 else (-1.0, 0.0, 1.0):
                    v = score(best_t, s * best_k, cx + float(dx), cy + float(dy))
                    if v > best_s + 1e-9:
                        best_s, bx, by, improved = v, cx + float(dx), cy + float(dy), True
        if not improved:
            break
    best_t = best_t % 360.0
    s = s * best_k
    th = math.radians(best_t)
    m = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]]) * s
    t = dc + np.array([bx, by]) - m @ sc
    return Similarity(scale=float(s), theta_deg=float(best_t), tx=float(t[0]), ty=float(t[1]),
                      score=float(best_s), method=method)


def split_stages(curve: np.ndarray, closed: bool, rotation_order: int, centre: Sequence[float],
                 min_stages: int = 3) -> List[Tuple[int, int]]:
    """Split one curve into drawing stages ``[(start_idx, end_idx_exclusive), ...]``.

    If the curve is closed and the figure has rotational order n >= min_stages, cut at the
    points nearest to the start point rotated by k*360/n (n congruent sections, when the
    curve maps onto itself); otherwise split into ``min_stages`` equal-arc sections."""
    n_pts = len(curve)
    if n_pts < 2 * min_stages:
        return [(0, n_pts)]
    cuts: List[int] = []
    if closed and rotation_order >= min_stages:
        c = np.asarray(centre, dtype=np.float64)
        p0 = curve[0] - c
        cand = []
        for k in range(1, rotation_order):
            th = 2 * math.pi * k / rotation_order
            q = np.array([math.cos(th) * p0[0] - math.sin(th) * p0[1], math.sin(th) * p0[0] + math.cos(th) * p0[1]]) + c
            d = np.hypot(curve[:, 0] - q[0], curve[:, 1] - q[1])
            i = int(np.argmin(d))
            if d[i] <= 6.0:
                cand.append(i)
        cand = sorted(set(cand))
        if len(cand) == rotation_order - 1 and all(b - a >= 3 for a, b in zip([0] + cand, cand + [n_pts])):
            cuts = cand
    if not cuts:
        seg = np.hypot(*np.diff(curve, axis=0).T)
        cum = np.concatenate([[0.0], np.cumsum(seg)])
        cuts = [int(np.searchsorted(cum, cum[-1] * k / min_stages)) for k in range(1, min_stages)]
    bounds = [0] + cuts + [n_pts]
    return [(a, b) for a, b in zip(bounds[:-1], bounds[1:]) if b > a]


def tau_for(stroke_width: float) -> float:
    return max(TAU_MIN_PX, TAU_W_FACTOR * stroke_width)
