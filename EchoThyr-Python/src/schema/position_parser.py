"""
Parser for extracting nodule position from OCR legend text.
GE echograph legend format: RT THYROID LOBE N1 SUP EXT POST A0%
"""

import re
from typing import Optional
from .models import NodulePosition, VerticalLevel, DepthLevel, LateralLevel


# Vocabulary mapping with OCR misread variants
VERTICAL_TOKENS = {
    "SUP": VerticalLevel.SUPERIOR,
    "SUPERIEUR": VerticalLevel.SUPERIOR,
    "SUPER": VerticalLevel.SUPERIOR,
    "MOY": VerticalLevel.MIDDLE,
    "MOYEN": VerticalLevel.MIDDLE,
    "MID": VerticalLevel.MIDDLE,
    "MIDDLE": VerticalLevel.MIDDLE,
    "INF": VerticalLevel.INFERIOR,
    "INFERIEUR": VerticalLevel.INFERIOR,
    "INFER": VerticalLevel.INFERIOR,
}

DEPTH_TOKENS = {
    "ANT": DepthLevel.ANTERIOR,
    "ANTERIEUR": DepthLevel.ANTERIOR,
    "POST": DepthLevel.POSTERIOR,
    "POSTERIEUR": DepthLevel.POSTERIOR,
    "OOST": DepthLevel.POSTERIOR,   # OCR misread of POST
    "P0ST": DepthLevel.POSTERIOR,   # OCR misread with zero
}

LATERAL_TOKENS = {
    "EXT": LateralLevel.LATERAL,
    "EXTERNE": LateralLevel.LATERAL,
    "LAT": LateralLevel.LATERAL,
    "LATERAL": LateralLevel.LATERAL,
    "INT": LateralLevel.MEDIAL,
    "INTERNE": LateralLevel.MEDIAL,
    "MED": LateralLevel.MEDIAL,
    "MEDIAL": LateralLevel.MEDIAL,
}

ISTHMUS_TOKENS = {"ISTHME", "ISTHMUS", "ISTHMIQUE"}

# Tokens to ignore (descriptive terms, not position)
IGNORE_TOKENS = {
    "KYSTE", "AMAS", "PONCTION", "MACROCAL", "MICROCALC",
    "NODULE", "LOBE", "THYROID", "THYROIDE",
    "DROIT", "GAUCHE", "RIGHT", "LEFT",
    "RT", "LT", "TRANS", "LONG", "SAG",
}


class PositionParser:
    """Extract nodule position from OCR legend text"""

    def parse_position_text(self, position_text: str, nodule_id: int = 1,
                            side: str = "RT") -> NodulePosition:
        """
        Parse position tokens extracted from legend text.

        Args:
            position_text: Raw position tokens (e.g., "SUP EXT POST")
            nodule_id: Nodule number
            side: "RT" or "LT"

        Returns:
            NodulePosition with parsed levels
        """
        pos = NodulePosition(nodule_id=nodule_id, side=side)

        if not position_text:
            return pos

        tokens = position_text.upper().split()

        for token in tokens:
            # Clean token (remove trailing punctuation)
            token = re.sub(r'[^A-Z0-9]', '', token)
            if not token:
                continue

            if token in IGNORE_TOKENS:
                continue

            if token in VERTICAL_TOKENS:
                pos.vertical = VERTICAL_TOKENS[token]
            elif token in DEPTH_TOKENS:
                pos.depth = DEPTH_TOKENS[token]
            elif token in LATERAL_TOKENS:
                pos.lateral = LATERAL_TOKENS[token]
            elif token in ISTHMUS_TOKENS:
                pos.is_isthmic = True

        return pos

    def extract_position_from_legend(self, legend_text: str, nodule_id: int = 1,
                                     side: str = "RT") -> NodulePosition:
        """
        Extract position from full legend text by finding the position tokens
        between N{digit} and A{digits}%.

        Args:
            legend_text: Full legend text from OCR
            nodule_id: Nodule number
            side: "RT" or "LT"

        Returns:
            NodulePosition with parsed levels
        """
        position_text = ""
        # Match text between N{digit}[DG]? and A[O0]?{digits}%
        pos_match = re.search(
            r'N\d+[DG]?\s+(.*?)\s*A[O0]?\d*%',
            legend_text, re.IGNORECASE
        )
        if pos_match:
            position_text = pos_match.group(1).strip()

        return self.parse_position_text(position_text, nodule_id, side)
