"""
Thyroid schema renderer using Pillow.

Port of the Claude Design handoff `design_handoff_schema_thyroidien` (hifi):
canvas 1000 x 620, fond blanc, trois vues alignees.

- Coupe longitudinale du lobe droit (ellipse, a gauche)
- Vue de face (path SVG papillon avec lobe pyramidal, au centre)
- Coupe longitudinale du lobe gauche (ellipse, a droite)
- Une croix d'orientation sous chaque vue

Le contour de la vue de face est le path SVG du prototype : Pillow ne connait
pas les Bezier, il est donc aplati en polygone puis rendu en polygon + line.
Rendu a x3 puis reduit en LANCZOS (Pillow n'anticrenele pas les primitives).

Convention anatomique : le lobe droit du patient est affiche a gauche.
Les coordonnees, couleurs et tailles de police sont celles du handoff et ne
doivent pas etre retouchees sans reprendre le design.
"""

import math
import re
from functools import lru_cache
from typing import Iterable, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

from .models import NodulePosition, ThyroidGeometry, VerticalLevel, DepthLevel, LateralLevel

# --------------------------------------------------------------------------
# Geometrie (source de verite : design_handoff_schema_thyroidien/geometry.json)
# --------------------------------------------------------------------------

CANVAS_W = 1000
CANVAS_H = 620
SUPERSAMPLE = 3

COLOR_BG = "#ffffff"
ORGAN_FILL = "#ffffff"
ORGAN_STROKE = "#232323"
ORGAN_STROKE_W = 2

# Vue de face : path auteur (bbox x 332..668, y 96..424) puis mise a l'echelle
FACE_SCALE = 1.22
FACE_PIVOT = (500.0, 260.0)

FACE_PATH_PYRAMIDAL = (
    "M 398 96 C 386 96, 377 104, 371 118 C 363 142, 356 180, 349 220 "
    "C 341 262, 332 280, 332 306 C 332 344, 337 378, 350 400 "
    "C 362 420, 384 424, 400 414 C 428 396, 460 378, 490 376 "
    "C 496 375, 504 375, 510 376 C 540 378, 572 396, 600 414 "
    "C 616 424, 638 420, 650 400 C 663 378, 668 344, 668 306 "
    "C 668 280, 659 262, 651 220 C 644 180, 637 142, 629 118 "
    "C 623 104, 614 96, 602 96 C 590 96, 586 104, 584 122 "
    "C 574 176, 550 238, 516 272 C 510 266, 506 214, 503 158 "
    "C 501 152, 499 152, 497 158 C 494 214, 490 266, 484 272 "
    "C 450 238, 426 176, 416 122 C 414 104, 410 96, 398 96 Z"
)

# Variante sans lobe pyramidal (encoche en V simple)
FACE_PATH_PLAIN_V = (
    "M 398 96 C 386 96, 377 104, 371 118 C 363 142, 356 180, 349 220 "
    "C 341 262, 332 280, 332 306 C 332 344, 337 378, 350 400 "
    "C 362 420, 384 424, 400 414 C 428 396, 460 378, 490 376 "
    "C 496 375, 504 375, 510 376 C 540 378, 572 396, 600 414 "
    "C 616 424, 638 420, 650 400 C 663 378, 668 344, 668 306 "
    "C 668 280, 659 262, 651 220 C 644 180, 637 142, 629 118 "
    "C 623 104, 614 96, 602 96 C 590 96, 586 104, 584 122 "
    "C 574 176, 546 240, 512 276 C 506 281, 494 281, 488 276 "
    "C 454 240, 426 176, 416 122 C 414 104, 410 96, 398 96 Z"
)

# Positionnement des nodules - vue de face (repere auteur, avant le x1.22)
FACE_LOBE_CX = {"D": 400.0, "G": 600.0}
FACE_LEVEL_Y = {"SUP": 202.0, "MOY": 282.0, "INF": 352.0}
FACE_LATERAL_SHIFT = 26.0
FACE_MEDIAL_SHIFT = 15.0
# L'isthme n'est pas couvert par le handoff : bande mediane entre le fond de
# l'encoche en V (y ~ 272) et le bord inferieur remontant en arche (y ~ 376).
FACE_ISTHMUS = (500.0, 328.0)

# Coupes longitudinales (ellipses)
CUT = {
    "D": {"cx": 170.0, "cy": 280.0, "rx": 108.0, "ry": 48.0},
    "G": {"cx": 830.0, "cy": 280.0, "rx": 108.0, "ry": 48.0},
}
CUT_LEVEL_DX = {"SUP": -52.0, "MOY": 0.0, "INF": 52.0}
CUT_DEPTH_DY = {"ANT": -18.0, "POST": 20.0, "NA": 0.0}

# Echelle des nodules : deduite des mesures du lobe, pas d'une constante.
# Un nodule occupe sur le schema la meme fraction du lobe que dans la realite.
# (Le handoff figeait PX_PER_MM = 3, ce qui donnait la meme taille a l'ecran
#  quelle que soit la taille du lobe.)
FACE_MIDLINE = 500.0         # separe les deux lobes dans le repere auteur
MIN_NODULE_R = 5.0           # rayon plancher quand la mesure est absente
MAX_NODULE_FRACTION = 1.1    # un nodule peut deborder legerement du lobe
NODULE_STROKE_W = 1.5

# Valeurs de repli quand une dimension de lobe manque (mm)
FALLBACK_LOBE_H = 45.0       # craniocaudal
FALLBACK_LOBE_W = 15.0       # transverse
FALLBACK_LOBE_AP = 15.0      # antero-posterieur

PALETTE = [
    ("#D74646", "#A51E1E"),   # N1 rouge
    ("#377DD7", "#194BA5"),   # N2 bleu
    ("#41A541", "#197319"),   # N3 vert
    ("#D79119", "#A56905"),   # N4 orange
    ("#A541D7", "#7D19A5"),   # N5 violet
]

TITLES = [("Lobe droit", 170), ("Vue de face", 500), ("Lobe gauche", 830)]
TITLE_Y = 48             # baseline SVG
TITLE_SIZE = 20

CROSSES = [
    (170, 520, ("AV", "AR", "HT", "BS")),   # coupe droite : haut, bas, gauche, droite
    (500, 520, ("HT", "BS", "D", "G")),     # vue de face
    (830, 520, ("AV", "AR", "HT", "BS")),   # coupe gauche
]
CROSS_ARM = 27
CROSS_STROKE_W = 1.5
CROSS_HEAD = 5.2
ORIENT_SIZE = 12.5

NODULE_LABEL_SIZE = 10
NODULE_LABEL_DY = 3.5    # baseline sous le centre de l'ellipse

# --------------------------------------------------------------------------
# Correspondance modeles du projet -> vocabulaire du design
# --------------------------------------------------------------------------

_SIDE = {"RT": "D", "LT": "G"}
_LEVEL = {
    VerticalLevel.SUPERIOR: "SUP",
    VerticalLevel.MIDDLE: "MOY",
    VerticalLevel.INFERIOR: "INF",
    VerticalLevel.UNKNOWN: "MOY",
}
_DEPTH = {
    DepthLevel.ANTERIOR: "ANT",
    DepthLevel.POSTERIOR: "POST",
    DepthLevel.UNKNOWN: "NA",
}
_LAT = {
    LateralLevel.LATERAL: "LAT",
    LateralLevel.MEDIAL: "MED",
    LateralLevel.UNKNOWN: "NA",
}


def _dims(nod: NodulePosition) -> Tuple[float, float, float]:
    """(L, l, E) du design : craniocaudal, antero-posterieur, transverse."""
    return (nod.height_mm, nod.length_mm, nod.width_mm)


def _colors(nodule_id: int) -> Tuple[str, str]:
    return PALETTE[(nodule_id - 1) % len(PALETTE)]


def _mm(value: float, fallback: float) -> float:
    """Mesure de lobe exploitable, sinon valeur de repli."""
    return value if value and value > 0 else fallback


def _radius(mm: float, px_per_mm: float, limit_px: float) -> float:
    """Demi-axe d'un nodule, plancher si la mesure manque, plafond au lobe."""
    if mm <= 0:
        return MIN_NODULE_R
    return max(MIN_NODULE_R, min(limit_px * MAX_NODULE_FRACTION, mm * px_per_mm / 2))


@lru_cache(maxsize=2)
def _face_lobe_profile(pyramidal: bool):
    """Analyse rasterisee d'UN lobe de la vue de face (moitie x < mediane).

    Le schema etant symetrique, seul le lobe de gauche est mesure. Renvoie
    (spans, y_min, y_max, largeur_max, hauteur) ou `spans` donne pour chaque
    y auteur entier le couple (x_gauche, x_droit) du lobe a ce niveau.

    La largeur maximale ignore les lignes ou le lobe rejoint l'isthme, sinon
    la bande isthmique la gonflerait jusqu'a la ligne mediane.
    """
    pts = flatten_path(FACE_PATH_PYRAMIDAL if pyramidal else FACE_PATH_PLAIN_V)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, y0 = math.floor(min(xs)), math.floor(min(ys))
    w = math.ceil(max(xs)) - x0 + 1
    h = math.ceil(max(ys)) - y0 + 1

    mask = Image.new("1", (w, h), 0)
    ImageDraw.Draw(mask).polygon([(x - x0, y - y0) for x, y in pts], fill=1)
    px = mask.load()
    mid = int(round(FACE_MIDLINE - x0))

    spans = {}
    y_min = y_max = None
    best_w = 0
    for j in range(h):
        run = cur = 0
        run_end = -1
        for i in range(mid):
            if px[i, j]:
                cur += 1
                if cur > run:
                    run, run_end = cur, i
            else:
                cur = 0
        if run == 0:
            continue
        y = j + y0
        spans[y] = (float(run_end - run + 1 + x0), float(run_end + x0))
        if y_min is None:
            y_min = y
        y_max = y
        if run_end < mid - 1:          # lobe separe de l'isthme sur cette ligne
            best_w = max(best_w, run)

    return (spans, float(y_min), float(y_max),
            float(best_w), float(y_max - y_min + 1))


def _face_lobe_extents(pyramidal: bool) -> Tuple[float, float]:
    """(largeur max, hauteur) en px auteur d'UN lobe dans la vue de face."""
    _, _, _, width, height = _face_lobe_profile(pyramidal)
    return width, height


def _face_lobe_span(y: float, side: str,
                    pyramidal: bool) -> Optional[Tuple[float, float]]:
    """Bornes horizontales du lobe `side` au niveau `y` (repere auteur)."""
    spans, y_min, y_max, _, _ = _face_lobe_profile(pyramidal)
    span = spans.get(int(round(min(max(y, y_min), y_max))))
    if span is None:
        return None
    left, right = span
    if side == "G":                    # symetrique par rapport a la mediane
        return (2 * FACE_MIDLINE - right, 2 * FACE_MIDLINE - left)
    return span


def _fit(center: float, radius: float, lo: float, hi: float) -> float:
    """Recentre `center` pour que [center-r, center+r] tienne dans [lo, hi]."""
    if 2 * radius >= hi - lo:
        return (lo + hi) / 2
    return min(max(center, lo + radius), hi - radius)


def _face_px_per_mm(geometry: ThyroidGeometry, side: str,
                    pyramidal: bool) -> Tuple[float, float]:
    """(horizontal, vertical) px auteur par mm pour un lobe en vue de face.

    Horizontal = transverse, vertical = craniocaudal.
    """
    w_px, h_px = _face_lobe_extents(pyramidal)
    if side == "D":
        w_mm = _mm(geometry.right_width, FALLBACK_LOBE_W)
        h_mm = _mm(geometry.right_height, FALLBACK_LOBE_H)
    else:
        w_mm = _mm(geometry.left_width, FALLBACK_LOBE_W)
        h_mm = _mm(geometry.left_height, FALLBACK_LOBE_H)
    return w_px / w_mm, h_px / h_mm


def _cut_px_per_mm(geometry: ThyroidGeometry,
                   side: str) -> Tuple[float, float]:
    """(horizontal, vertical) px par mm pour une coupe longitudinale.

    Horizontal = craniocaudal, vertical = antero-posterieur.
    """
    c = CUT[side]
    if side == "D":
        h_mm = _mm(geometry.right_height, FALLBACK_LOBE_H)
        ap_mm = _mm(geometry.right_length, FALLBACK_LOBE_AP)
    else:
        h_mm = _mm(geometry.left_height, FALLBACK_LOBE_H)
        ap_mm = _mm(geometry.left_length, FALLBACK_LOBE_AP)
    return (c["rx"] * 2) / h_mm, (c["ry"] * 2) / ap_mm


# --------------------------------------------------------------------------
# Path SVG -> polygone
# --------------------------------------------------------------------------

def flatten_path(d: str, steps: int = 24) -> List[Tuple[float, float]]:
    """Aplatit un path compose uniquement de M / C / Z (le cas de ce schema)."""
    tokens = re.findall(r"[MCZmcz]|-?\d+\.?\d*", d)
    pts: List[Tuple[float, float]] = []
    i = 0
    cur = (0.0, 0.0)
    while i < len(tokens):
        cmd = tokens[i]
        if cmd in "Mm":
            cur = (float(tokens[i + 1]), float(tokens[i + 2]))
            pts.append(cur)
            i += 3
        elif cmd in "Cc":
            p1 = (float(tokens[i + 1]), float(tokens[i + 2]))
            p2 = (float(tokens[i + 3]), float(tokens[i + 4]))
            p3 = (float(tokens[i + 5]), float(tokens[i + 6]))
            for s in range(1, steps + 1):
                t = s / steps
                mt = 1 - t
                x = (mt ** 3 * cur[0] + 3 * mt * mt * t * p1[0]
                     + 3 * mt * t * t * p2[0] + t ** 3 * p3[0])
                y = (mt ** 3 * cur[1] + 3 * mt * mt * t * p1[1]
                     + 3 * mt * t * t * p2[1] + t ** 3 * p3[1])
                pts.append((x, y))
            cur = p3
            i += 7
        else:                       # Z / z
            i += 1
    return pts


def scale_about(pts: Iterable[Tuple[float, float]], k: float,
                pivot: Tuple[float, float]) -> List[Tuple[float, float]]:
    px, py = pivot
    return [(px + (x - px) * k, py + (y - py) * k) for x, y in pts]


# --------------------------------------------------------------------------
# Polices : les y du design sont des baselines (semantique SVG)
# --------------------------------------------------------------------------

_FONT_CANDIDATES = {
    False: ["C:/Windows/Fonts/arial.ttf", "DejaVuSans.ttf",
            "C:/Windows/Fonts/segoeui.ttf"],
    True: ["C:/Windows/Fonts/arialbd.ttf", "DejaVuSans-Bold.ttf",
           "C:/Windows/Fonts/seguisb.ttf"],
}


def _font(size: float, bold: bool = False) -> ImageFont.ImageFont:
    for name in _FONT_CANDIDATES[bold]:
        try:
            return ImageFont.truetype(name, int(round(size)))
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _text_baseline(draw: ImageDraw.ImageDraw, xy, s: str, font, fill,
                   anchor_x: str = "middle") -> None:
    """Ecrit `s` en respectant la semantique SVG (y = baseline)."""
    anchor = {"start": "ls", "middle": "ms", "end": "rs"}[anchor_x]
    try:
        draw.text(xy, s, font=font, fill=fill, anchor=anchor)
    except (ValueError, AttributeError):
        # Police bitmap de secours : pas d'ancre, on recentre a la main
        x, y = xy
        box = draw.textbbox((0, 0), s, font=font)
        w, h = box[2] - box[0], box[3] - box[1]
        dx = {"start": 0, "middle": -w / 2, "end": -w}[anchor_x]
        draw.text((x + dx, y - h), s, font=font, fill=fill)


# --------------------------------------------------------------------------
# Placement des nodules
# --------------------------------------------------------------------------

def face_ellipse(nod: NodulePosition, geometry: ThyroidGeometry,
                 pyramidal: bool = True) -> Tuple[float, float, float, float]:
    """(cx, cy, rx, ry) dans le repere AUTEUR (avant la mise a l'echelle).

    Les rayons sont proportionnels au lobe : un nodule occupe la meme
    fraction du lobe sur le schema que dans la realite.
    """
    d1, _d2, d3 = _dims(nod)
    _spans, y_min, y_max, w_px, h_px = _face_lobe_profile(pyramidal)

    if nod.is_isthmic:
        # L'isthme n'a pas de mesure de reference : moyenne des deux lobes
        rd = _face_px_per_mm(geometry, "D", pyramidal)
        lg = _face_px_per_mm(geometry, "G", pyramidal)
        sx, sy = (rd[0] + lg[0]) / 2, (rd[1] + lg[1]) / 2
        return (FACE_ISTHMUS[0], FACE_ISTHMUS[1],
                _radius(d3, sx, w_px / 2), _radius(d1, sy, h_px / 2))

    side = _SIDE.get(nod.side, "D")
    sign = -1 if side == "D" else 1
    lat = _LAT[nod.lateral]
    if lat == "LAT":
        shift = sign * FACE_LATERAL_SHIFT
    elif lat == "MED":
        shift = -sign * FACE_MEDIAL_SHIFT
    else:
        shift = 0.0

    sx, sy = _face_px_per_mm(geometry, side, pyramidal)
    rx = _radius(d3, sx, w_px / 2)
    ry = _radius(d1, sy, h_px / 2)

    cx = FACE_LOBE_CX[side] + shift
    cy = _fit(FACE_LEVEL_Y[_LEVEL[nod.vertical]], ry, y_min, y_max)

    # Le lobe est plus etroit aux poles qu'a sa largeur maximale : recentrer
    # sur la place reellement disponible a ce niveau.
    span = _face_lobe_span(cy, side, pyramidal)
    if span:
        cx = _fit(cx, rx, span[0], span[1])

    return (cx, cy, rx, ry)


def cut_ellipse(nod: NodulePosition,
                geometry: ThyroidGeometry) -> Tuple[float, float, float, float]:
    """(cx, cy, rx, ry) d'un nodule sur une coupe longitudinale."""
    side = _SIDE.get(nod.side, "D")
    c = CUT[side]
    d1, d2, _d3 = _dims(nod)
    sx, sy = _cut_px_per_mm(geometry, side)
    rx = _radius(d1, sx, c["rx"])
    ry = _radius(d2, sy, c["ry"])

    cx = _fit(c["cx"] + CUT_LEVEL_DX[_LEVEL[nod.vertical]], rx,
              c["cx"] - c["rx"], c["cx"] + c["rx"])
    # Hauteur disponible a cette abscisse : la coupe est une ellipse, pas un
    # rectangle, elle se resserre vers les poles.
    dx = (cx - c["cx"]) / c["rx"]
    avail = c["ry"] * math.sqrt(max(0.0, 1 - dx * dx))
    cy = _fit(c["cy"] + CUT_DEPTH_DY[_DEPTH[nod.depth]], ry,
              c["cy"] - avail, c["cy"] + avail)

    return (cx, cy, rx, ry)


def _ellipse_box(cx: float, cy: float, rx: float, ry: float) -> List[float]:
    return [cx - rx, cy - ry, cx + rx, cy + ry]


# --------------------------------------------------------------------------
# Fleches des croix d'orientation
# --------------------------------------------------------------------------

def _arrow(draw: ImageDraw.ImageDraw, x1, y1, x2, y2, color=ORGAN_STROKE,
           width: float = CROSS_STROKE_W, head: float = CROSS_HEAD) -> None:
    """Segment a double pointe (equivalent marker-start / marker-end du SVG)."""
    draw.line([x1, y1, x2, y2], fill=color, width=max(1, int(round(width))))
    ang = math.atan2(y2 - y1, x2 - x1)
    for (hx, hy), a in (((x2, y2), ang), ((x1, y1), ang + math.pi)):
        left = (hx - head * math.cos(a - 0.5), hy - head * math.sin(a - 0.5))
        right = (hx - head * math.cos(a + 0.5), hy - head * math.sin(a + 0.5))
        draw.polygon([(hx, hy), left, right], fill=color)


# --------------------------------------------------------------------------
# Renderer
# --------------------------------------------------------------------------

class ThyroidRenderer:
    """Rend le schema thyroidien annote des nodules (design hifi)."""

    def __init__(self, pyramidal_lobe: bool = True,
                 face_scale: float = FACE_SCALE,
                 supersample: int = SUPERSAMPLE):
        self.pyramidal_lobe = pyramidal_lobe
        self.face_scale = face_scale
        self.ss = supersample

    def render(self, geometry: ThyroidGeometry, nodules: List[NodulePosition],
               output_path: str, logger=None) -> bool:
        """Rend le schema dans un PNG.

        Les coordonnees de l'organe sont figees (design hifi). `geometry`
        sert a dimensionner les nodules : leurs ellipses occupent la meme
        fraction du lobe dessine que la mesure occupe du lobe reel.
        """
        try:
            img = self.render_image(nodules, geometry)
            img.save(output_path, "PNG")
            if logger:
                logger.info(f"Thyroid schema generated: {output_path}")
            return True
        except Exception as e:
            if logger:
                logger.error(f"Failed to render thyroid schema: {e}", exc_info=e)
            return False

    def render_image(self, nodules: Sequence[NodulePosition],
                     geometry: Optional[ThyroidGeometry] = None) -> Image.Image:
        """Rend le schema et renvoie l'image Pillow."""
        geometry = geometry or ThyroidGeometry()
        ss = self.ss
        img = Image.new("RGB", (CANVAS_W * ss, CANVAS_H * ss), COLOR_BG)
        draw = ImageDraw.Draw(img)

        def S(v):                       # passage au repere supersample
            return v * ss

        def box(b):
            return [S(v) for v in b]

        stroke_w = max(1, int(round(ORGAN_STROKE_W * ss)))
        nodule_w = max(1, int(round(NODULE_STROKE_W * ss)))

        # --- organe : vue de face -----------------------------------------
        path = FACE_PATH_PYRAMIDAL if self.pyramidal_lobe else FACE_PATH_PLAIN_V
        poly = scale_about(flatten_path(path), self.face_scale, FACE_PIVOT)
        poly_ss = [(S(x), S(y)) for x, y in poly]
        draw.polygon(poly_ss, fill=ORGAN_FILL, outline=ORGAN_STROKE)
        draw.line(poly_ss + [poly_ss[0]], fill=ORGAN_STROKE,
                  width=stroke_w, joint="curve")

        # --- organe : coupes longitudinales --------------------------------
        for side in ("D", "G"):
            c = CUT[side]
            draw.ellipse(box(_ellipse_box(c["cx"], c["cy"], c["rx"], c["ry"])),
                         fill=ORGAN_FILL, outline=ORGAN_STROKE, width=stroke_w)

        # --- nodules --------------------------------------------------------
        # L'etiquette reste a 10 px effectifs malgre le x1.22 de la vue de face
        f_label = _font(NODULE_LABEL_SIZE * ss, bold=True)
        for nod in nodules:
            fill, stroke = _colors(nod.nodule_id)
            label = f"N{nod.nodule_id}"

            # Vue de face
            cx, cy, rx, ry = face_ellipse(nod, geometry, self.pyramidal_lobe)
            fx, fy = scale_about([(cx, cy)], self.face_scale, FACE_PIVOT)[0]
            draw.ellipse(
                box(_ellipse_box(fx, fy, rx * self.face_scale, ry * self.face_scale)),
                fill=fill, outline=stroke, width=nodule_w)
            _text_baseline(draw, (S(fx), S(fy + NODULE_LABEL_DY)), label,
                           f_label, "#ffffff")

            # Coupe longitudinale (l'isthme n'appartient a aucun lobe)
            if nod.is_isthmic:
                continue
            cx, cy, rx, ry = cut_ellipse(nod, geometry)
            draw.ellipse(box(_ellipse_box(cx, cy, rx, ry)),
                         fill=fill, outline=stroke, width=nodule_w)
            _text_baseline(draw, (S(cx), S(cy + NODULE_LABEL_DY)), label,
                           f_label, "#ffffff")

        # --- contours redessines --------------------------------------------
        # Un nodule plus gros que le lobe deborde : le tracer par-dessus
        # garde l'anatomie lisible et rend le depassement explicite.
        draw.line(poly_ss + [poly_ss[0]], fill=ORGAN_STROKE,
                  width=stroke_w, joint="curve")
        for side in ("D", "G"):
            c = CUT[side]
            draw.ellipse(box(_ellipse_box(c["cx"], c["cy"], c["rx"], c["ry"])),
                         outline=ORGAN_STROKE, width=stroke_w)

        # --- titres ---------------------------------------------------------
        f_title = _font(TITLE_SIZE * ss, bold=True)
        for text, x in TITLES:
            _text_baseline(draw, (S(x), S(TITLE_Y)), text, f_title, ORGAN_STROKE)

        # --- croix d'orientation --------------------------------------------
        f_or = _font(ORIENT_SIZE * ss)
        for cx, cy, (top, bottom, left, right) in CROSSES:
            _arrow(draw, S(cx - CROSS_ARM), S(cy), S(cx + CROSS_ARM), S(cy),
                   width=CROSS_STROKE_W * ss, head=CROSS_HEAD * ss)
            _arrow(draw, S(cx), S(cy - CROSS_ARM), S(cx), S(cy + CROSS_ARM),
                   width=CROSS_STROKE_W * ss, head=CROSS_HEAD * ss)
            _text_baseline(draw, (S(cx), S(cy - CROSS_ARM - 8)), top,
                           f_or, ORGAN_STROKE)
            _text_baseline(draw, (S(cx), S(cy + CROSS_ARM + 17)), bottom,
                           f_or, ORGAN_STROKE)
            _text_baseline(draw, (S(cx - CROSS_ARM - 8), S(cy + 4)), left,
                           f_or, ORGAN_STROKE, anchor_x="end")
            _text_baseline(draw, (S(cx + CROSS_ARM + 8), S(cy + 4)), right,
                           f_or, ORGAN_STROKE, anchor_x="start")

        return img.resize((CANVAS_W, CANVAS_H), Image.LANCZOS) if ss > 1 else img
