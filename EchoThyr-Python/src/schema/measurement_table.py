"""
Tableau de mesures des nodules (design handoff `schema_thyroidien`).

Le design retire la legende de couleurs du schema et la remplace par un
tableau : Nodule, Cote, Siege, Long., Larg., Epais., Volume, Examen, suivi
d'une ligne « Volume nodulaire total ».

Le siege est derive des memes descripteurs que la position sur le schema, il
n'est jamais saisi deux fois.
"""

import math
from typing import List, Sequence

from .models import NodulePosition, VerticalLevel, DepthLevel, LateralLevel

# Libelles du handoff. « Long. / Larg. / Epais. » et non « L / l / E » :
# en capitales, « L » et « l » deviennent indistinguables.
HEADERS = ["Nodule", "Côté", "Siège", "Long. (mm)", "Larg. (mm)",
           "Épais. (mm)", "Volume (mL)", "Examen"]
TOTAL_LABEL = "Volume nodulaire total"

_LEVEL_LABEL = {
    VerticalLevel.SUPERIOR: "tiers supérieur",
    VerticalLevel.MIDDLE: "tiers moyen",
    VerticalLevel.INFERIOR: "tiers inférieur",
    VerticalLevel.UNKNOWN: None,
}
_DEPTH_LABEL = {
    DepthLevel.ANTERIOR: "antérieur",
    DepthLevel.POSTERIOR: "postérieur",
    DepthLevel.UNKNOWN: None,
}
_LAT_LABEL = {
    LateralLevel.LATERAL: "latéral",
    LateralLevel.MEDIAL: "médial",
    LateralLevel.UNKNOWN: None,
}


def nodule_volume_ml(nod: NodulePosition) -> float:
    """Volume ellipsoide V = pi/6 x L x l x E, en mL (mm3 / 1000)."""
    d1, d2, d3 = nod.height_mm, nod.length_mm, nod.width_mm
    if d1 <= 0 or d2 <= 0 or d3 <= 0:
        return 0.0
    return math.pi / 6 * d1 * d2 * d3 / 1000


def nodule_site(nod: NodulePosition) -> str:
    """Siege lisible, derive des descripteurs de position."""
    if nod.is_isthmic:
        return "isthme"
    parts = [_LEVEL_LABEL[nod.vertical], _DEPTH_LABEL[nod.depth],
             _LAT_LABEL[nod.lateral]]
    return ", ".join(p for p in parts if p)


def _fmt(value: float) -> str:
    return f"{value:.1f}".replace(".", ",") if value > 0 else "—"


def build_rows(nodules: Sequence[NodulePosition],
               exam_date: str = "") -> List[dict]:
    """Lignes du tableau, une par nodule, dans l'ordre des numeros.

    L'appariement hybride les produit dans l'ordre ou il les resout, pas dans
    celui de leurs numeros.
    """
    rows = []
    for nod in sorted(nodules, key=lambda n: n.nodule_id):
        if nod.is_isthmic:
            side = "Isthme"
        else:
            side = "Droit" if nod.side == "RT" else "Gauche"
        volume = nodule_volume_ml(nod)
        rows.append({
            "nodule": f"N{nod.nodule_id}",
            "cote": side,
            "siege": nodule_site(nod),
            "long_mm": _fmt(nod.height_mm),
            "larg_mm": _fmt(nod.length_mm),
            "epais_mm": _fmt(nod.width_mm),
            "volume_ml": f"{volume:.2f}".replace(".", ",") if volume > 0 else "—",
            "examen": exam_date,
        })
    return rows


def total_volume_ml(nodules: Sequence[NodulePosition]) -> float:
    return sum(nodule_volume_ml(n) for n in nodules)


def build_table(nodules: Sequence[NodulePosition],
                exam_date: str = "") -> dict:
    """Tableau complet : en-tetes, lignes, et ligne de total."""
    total = total_volume_ml(nodules)
    return {
        "headers": HEADERS,
        "rows": build_rows(nodules, exam_date),
        "total_label": TOTAL_LABEL,
        "total_volume_ml": f"{total:.2f}".replace(".", ",") if total > 0 else "—",
    }
