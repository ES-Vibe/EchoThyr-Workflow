"""
Thyroid schema renderer using Pillow.
Generates frontal (coronal) and transverse (axial) views with nodule positions.
Uses 3x supersampling for anti-aliased rendering.
"""

from PIL import Image, ImageDraw, ImageFont
from typing import List, Optional, Tuple
from .models import NodulePosition, ThyroidGeometry, VerticalLevel, DepthLevel, LateralLevel

# Canvas dimensions (final output)
CANVAS_W = 800
CANVAS_H = 900  # Frontal + transverse
SUPERSAMPLE = 3  # 3x supersampling for anti-aliasing

# Colors
COLOR_BG = (255, 255, 255)
COLOR_TRACHEA = (173, 216, 230)       # Light blue
COLOR_TRACHEA_OUTLINE = (100, 149, 237)
COLOR_LOBE = (255, 218, 185)          # Peach
COLOR_LOBE_OUTLINE = (180, 130, 100)
COLOR_ISTHMUS = (255, 205, 170)       # Slightly darker peach
COLOR_ISTHMUS_OUTLINE = (180, 130, 100)
COLOR_TEXT = (60, 60, 60)
COLOR_LABEL = (100, 100, 100)
COLOR_MARKER = (150, 150, 150)
COLOR_TITLE = (40, 40, 80)

# Nodule colors (distinct for each nodule)
NODULE_COLORS = [
    ((220, 80, 80), (180, 40, 40)),     # Red
    ((80, 140, 220), (40, 90, 180)),     # Blue
    ((80, 180, 80), (40, 130, 40)),      # Green
    ((220, 160, 40), (180, 120, 20)),    # Orange
    ((180, 80, 220), (140, 40, 180)),    # Purple
    ((220, 80, 180), (180, 40, 140)),    # Pink
]


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """Get a font, falling back to default if system fonts unavailable"""
    font_paths = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/calibri.ttf",
    ]
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


class ThyroidRenderer:
    """Renders thyroid schema with nodules positioned from OCR data"""

    def __init__(self):
        self.ss = SUPERSAMPLE  # Shorthand

    def render(self, geometry: ThyroidGeometry, nodules: List[NodulePosition],
               output_path: str, logger=None) -> bool:
        """
        Render the thyroid schema to a PNG file.

        Args:
            geometry: Thyroid lobe dimensions
            nodules: List of positioned nodules
            output_path: Path for output PNG
            logger: Optional logger

        Returns:
            True if successful
        """
        try:
            ss = self.ss
            w, h = CANVAS_W * ss, CANVAS_H * ss
            img = Image.new('RGB', (w, h), COLOR_BG)
            draw = ImageDraw.Draw(img)

            # Fonts (scaled for supersampling)
            font_title = _get_font(18 * ss)
            font_label = _get_font(14 * ss)
            font_small = _get_font(11 * ss)
            font_marker = _get_font(10 * ss)

            # --- Frontal view (top section) ---
            frontal_y_offset = 40 * ss
            self._draw_frontal_view(
                draw, geometry, nodules,
                y_offset=frontal_y_offset,
                canvas_w=w,
                fonts=(font_title, font_label, font_small, font_marker),
                ss=ss
            )

            # --- Transverse view (bottom section) ---
            trans_y_offset = 520 * ss
            self._draw_transverse_view(
                draw, geometry, nodules,
                y_offset=trans_y_offset,
                canvas_w=w,
                fonts=(font_title, font_label, font_small, font_marker),
                ss=ss
            )

            # --- Legend ---
            self._draw_legend(
                draw, nodules,
                y_offset=830 * ss,
                canvas_w=w,
                fonts=(font_title, font_label, font_small, font_marker),
                ss=ss
            )

            # Downsample with LANCZOS for anti-aliasing
            img = img.resize((CANVAS_W, CANVAS_H), Image.LANCZOS)
            img.save(output_path, 'PNG')

            if logger:
                logger.info(f"Thyroid schema generated: {output_path}")

            return True

        except Exception as e:
            if logger:
                logger.error(f"Failed to render thyroid schema: {e}", exc_info=e)
            return False

    def _draw_frontal_view(self, draw: ImageDraw.Draw, geometry: ThyroidGeometry,
                           nodules: List[NodulePosition], y_offset: int,
                           canvas_w: int, fonts: tuple, ss: int):
        """Draw frontal (coronal) view of thyroid"""
        font_title, font_label, font_small, font_marker = fonts

        # Title
        title = "Vue frontale"
        bbox = draw.textbbox((0, 0), title, font=font_title)
        tw = bbox[2] - bbox[0]
        draw.text(((canvas_w - tw) // 2, y_offset - 30 * ss), title,
                  fill=COLOR_TITLE, font=font_title)

        center_x = canvas_w // 2
        center_y = y_offset + 210 * ss

        # Scale factor: map mm to pixels (proportional rendering)
        # Use the larger lobe height to set scale
        max_lobe_h = max(geometry.right_height, geometry.left_height, 30)
        scale = (350 * ss) / max_lobe_h  # Lobe height maps to 350 ss-pixels

        # Trachea
        trachea_r = 25 * ss
        draw.ellipse(
            [center_x - trachea_r, center_y - trachea_r,
             center_x + trachea_r, center_y + trachea_r],
            fill=COLOR_TRACHEA, outline=COLOR_TRACHEA_OUTLINE, width=2 * ss
        )
        bbox = draw.textbbox((0, 0), "Trachee", font=font_small)
        tw = bbox[2] - bbox[0]
        draw.text(((center_x - tw // 2), center_y - 6 * ss),
                  "Trachee", fill=COLOR_TRACHEA_OUTLINE, font=font_small)

        # Lobe dimensions in pixels
        r_lobe_h = geometry.right_height * scale
        r_lobe_w = geometry.right_width * scale
        l_lobe_h = geometry.left_height * scale
        l_lobe_w = geometry.left_width * scale

        # Clamp lobe widths to reasonable range
        min_lobe_w = 50 * ss
        max_lobe_w = 130 * ss
        r_lobe_w = max(min_lobe_w, min(max_lobe_w, r_lobe_w))
        l_lobe_w = max(min_lobe_w, min(max_lobe_w, l_lobe_w))
        r_lobe_h = max(150 * ss, min(400 * ss, r_lobe_h))
        l_lobe_h = max(150 * ss, min(400 * ss, l_lobe_h))

        # Lobe positions (anatomical: right lobe on left side of image = patient's right)
        lobe_gap = 30 * ss  # Gap for isthmus
        r_lobe_cx = center_x - lobe_gap - int(r_lobe_w * 0.5)
        l_lobe_cx = center_x + lobe_gap + int(l_lobe_w * 0.5)

        # Isthmus (rectangle connecting lobes)
        isth_h = max(15 * ss, int(geometry.isthmus_thickness * scale * 0.5))
        isth_h = min(isth_h, 40 * ss)
        draw.rectangle(
            [r_lobe_cx + int(r_lobe_w * 0.3), center_y - isth_h,
             l_lobe_cx - int(l_lobe_w * 0.3), center_y + isth_h],
            fill=COLOR_ISTHMUS, outline=COLOR_ISTHMUS_OUTLINE, width=2 * ss
        )

        # Draw lobes (ellipses)
        self._draw_lobe(draw, r_lobe_cx, center_y, r_lobe_w, r_lobe_h)
        self._draw_lobe(draw, l_lobe_cx, center_y, l_lobe_w, l_lobe_h)

        # Labels
        r_label = "Lobe Droit"
        bbox = draw.textbbox((0, 0), r_label, font=font_label)
        tw = bbox[2] - bbox[0]
        draw.text((r_lobe_cx - tw // 2, center_y + int(r_lobe_h * 0.5) + 15 * ss),
                  r_label, fill=COLOR_TEXT, font=font_label)

        l_label = "Lobe Gauche"
        bbox = draw.textbbox((0, 0), l_label, font=font_label)
        tw = bbox[2] - bbox[0]
        draw.text((l_lobe_cx - tw // 2, center_y + int(l_lobe_h * 0.5) + 15 * ss),
                  l_label, fill=COLOR_TEXT, font=font_label)

        # Vertical markers (S/M/I) on right side of each lobe
        for lobe_cx, lobe_h in [(r_lobe_cx, r_lobe_h), (l_lobe_cx, l_lobe_h)]:
            markers = [("S", -0.35), ("M", 0.0), ("I", 0.35)]
            for marker_text, frac in markers:
                my = center_y + int(lobe_h * frac)
                mx = lobe_cx + int(max(r_lobe_w, l_lobe_w) * 0.5) + 12 * ss
                draw.text((mx, my - 5 * ss), marker_text,
                          fill=COLOR_MARKER, font=font_marker)

        # Draw nodules on frontal view
        for nod in nodules:
            self._draw_nodule_frontal(
                draw, nod, center_x, center_y,
                r_lobe_cx, l_lobe_cx,
                r_lobe_w, r_lobe_h, l_lobe_w, l_lobe_h,
                scale, lobe_gap, fonts, ss
            )

    def _draw_lobe(self, draw: ImageDraw.Draw, cx: int, cy: int,
                   w: float, h: float):
        """Draw a lobe ellipse"""
        draw.ellipse(
            [cx - int(w * 0.5), cy - int(h * 0.5),
             cx + int(w * 0.5), cy + int(h * 0.5)],
            fill=COLOR_LOBE, outline=COLOR_LOBE_OUTLINE, width=2 * self.ss
        )

    def _draw_nodule_frontal(self, draw: ImageDraw.Draw, nod: NodulePosition,
                             center_x: int, center_y: int,
                             r_lobe_cx: int, l_lobe_cx: int,
                             r_lobe_w: float, r_lobe_h: float,
                             l_lobe_w: float, l_lobe_h: float,
                             scale: float, lobe_gap: int, fonts: tuple, ss: int):
        """Draw a single nodule on the frontal view"""
        _, _, font_small, _ = fonts

        # Determine which lobe
        if nod.is_isthmic:
            nod_cx = center_x
            nod_cy = center_y
        elif nod.side == "RT":
            nod_cx = r_lobe_cx
            nod_cy = center_y
            lobe_w, lobe_h = r_lobe_w, r_lobe_h
        else:
            nod_cx = l_lobe_cx
            nod_cy = center_y
            lobe_w, lobe_h = l_lobe_w, l_lobe_h

        if not nod.is_isthmic:
            # Vertical offset
            if nod.vertical == VerticalLevel.SUPERIOR:
                nod_cy = center_y - int(lobe_h * 0.28)
            elif nod.vertical == VerticalLevel.INFERIOR:
                nod_cy = center_y + int(lobe_h * 0.28)

            # Lateral offset (lateral = away from center, medial = toward center)
            if nod.lateral == LateralLevel.LATERAL:
                offset = int(lobe_w * 0.2)
                nod_cx += -offset if nod.side == "RT" else offset
            elif nod.lateral == LateralLevel.MEDIAL:
                offset = int(lobe_w * 0.2)
                nod_cx += offset if nod.side == "RT" else -offset

        # Nodule size (proportional to dimensions, with min/max)
        nod_w = max(12 * ss, min(60 * ss, int(nod.width_mm * scale * 0.6))) if nod.width_mm > 0 else 18 * ss
        nod_h = max(12 * ss, min(60 * ss, int(nod.height_mm * scale * 0.6))) if nod.height_mm > 0 else 18 * ss

        # Color
        color_idx = (nod.nodule_id - 1) % len(NODULE_COLORS)
        fill_color, outline_color = NODULE_COLORS[color_idx]

        # Draw nodule ellipse
        draw.ellipse(
            [nod_cx - nod_w, nod_cy - nod_h,
             nod_cx + nod_w, nod_cy + nod_h],
            fill=fill_color + (180,),  # Semi-transparent via solid color approximation
            outline=outline_color, width=2 * ss
        )

        # Label
        label = f"N{nod.nodule_id}"
        bbox = draw.textbbox((0, 0), label, font=font_small)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((nod_cx - tw // 2, nod_cy - th // 2), label,
                  fill=(255, 255, 255), font=font_small)

    def _draw_transverse_view(self, draw: ImageDraw.Draw, geometry: ThyroidGeometry,
                              nodules: List[NodulePosition], y_offset: int,
                              canvas_w: int, fonts: tuple, ss: int):
        """Draw transverse (axial) view showing depth"""
        font_title, font_label, font_small, font_marker = fonts

        # Title
        title = "Coupe transversale"
        bbox = draw.textbbox((0, 0), title, font=font_title)
        tw = bbox[2] - bbox[0]
        draw.text(((canvas_w - tw) // 2, y_offset - 30 * ss), title,
                  fill=COLOR_TITLE, font=font_title)

        center_x = canvas_w // 2
        center_y = y_offset + 110 * ss

        # Scale for transverse view (based on width/length)
        max_dim = max(geometry.right_width, geometry.right_length,
                      geometry.left_width, geometry.left_length, 15)
        scale = (100 * ss) / max_dim

        # Trachea (posterior, at center)
        trachea_r = 20 * ss
        trachea_y = center_y + 15 * ss  # Slightly posterior
        draw.ellipse(
            [center_x - trachea_r, trachea_y - trachea_r,
             center_x + trachea_r, trachea_y + trachea_r],
            fill=COLOR_TRACHEA, outline=COLOR_TRACHEA_OUTLINE, width=2 * ss
        )
        bbox_t = draw.textbbox((0, 0), "T", font=font_small)
        tw_t = bbox_t[2] - bbox_t[0]
        draw.text((center_x - tw_t // 2, trachea_y - 6 * ss),
                  "T", fill=COLOR_TRACHEA_OUTLINE, font=font_small)

        # Lobes as ellipses (width x length = transverse x AP)
        r_w = max(40 * ss, min(100 * ss, int(geometry.right_width * scale)))
        r_l = max(40 * ss, min(100 * ss, int(geometry.right_length * scale)))
        l_w = max(40 * ss, min(100 * ss, int(geometry.left_width * scale)))
        l_l = max(40 * ss, min(100 * ss, int(geometry.left_length * scale)))

        lobe_gap = 25 * ss
        r_cx = center_x - lobe_gap - r_w // 2
        l_cx = center_x + lobe_gap + l_w // 2

        # Draw lobes
        draw.ellipse(
            [r_cx - r_w // 2, center_y - r_l // 2,
             r_cx + r_w // 2, center_y + r_l // 2],
            fill=COLOR_LOBE, outline=COLOR_LOBE_OUTLINE, width=2 * ss
        )
        draw.ellipse(
            [l_cx - l_w // 2, center_y - l_l // 2,
             l_cx + l_w // 2, center_y + l_l // 2],
            fill=COLOR_LOBE, outline=COLOR_LOBE_OUTLINE, width=2 * ss
        )

        # Labels
        draw.text((r_cx - 10 * ss, center_y + r_l // 2 + 5 * ss),
                  "D", fill=COLOR_TEXT, font=font_label)
        draw.text((l_cx - 10 * ss, center_y + l_l // 2 + 5 * ss),
                  "G", fill=COLOR_TEXT, font=font_label)

        # Anterior/Posterior markers
        draw.text((canvas_w - 60 * ss, center_y - r_l // 2 - 5 * ss),
                  "Ant", fill=COLOR_MARKER, font=font_marker)
        draw.text((canvas_w - 60 * ss, center_y + r_l // 2 - 5 * ss),
                  "Post", fill=COLOR_MARKER, font=font_marker)

        # Draw nodules on transverse view
        for nod in nodules:
            self._draw_nodule_transverse(
                draw, nod, center_x, center_y,
                r_cx, l_cx, r_w, r_l, l_w, l_l,
                scale, fonts, ss
            )

    def _draw_nodule_transverse(self, draw: ImageDraw.Draw, nod: NodulePosition,
                                center_x: int, center_y: int,
                                r_cx: int, l_cx: int,
                                r_w: int, r_l: int, l_w: int, l_l: int,
                                scale: float, fonts: tuple, ss: int):
        """Draw a single nodule on the transverse view"""
        _, _, font_small, _ = fonts

        # Determine lobe center
        if nod.is_isthmic:
            nod_cx = center_x
            nod_cy = center_y
        elif nod.side == "RT":
            nod_cx = r_cx
            nod_cy = center_y
        else:
            nod_cx = l_cx
            nod_cy = center_y

        if not nod.is_isthmic:
            # Depth offset (anterior = up, posterior = down in transverse)
            lobe_l = r_l if nod.side == "RT" else l_l
            if nod.depth == DepthLevel.ANTERIOR:
                nod_cy = center_y - int(lobe_l * 0.2)
            elif nod.depth == DepthLevel.POSTERIOR:
                nod_cy = center_y + int(lobe_l * 0.2)

            # Lateral offset
            lobe_w = r_w if nod.side == "RT" else l_w
            if nod.lateral == LateralLevel.LATERAL:
                offset = int(lobe_w * 0.15)
                nod_cx += -offset if nod.side == "RT" else offset
            elif nod.lateral == LateralLevel.MEDIAL:
                offset = int(lobe_w * 0.15)
                nod_cx += offset if nod.side == "RT" else -offset

        # Nodule size
        nod_r = max(8 * ss, min(35 * ss, int(max(nod.width_mm, nod.length_mm, 5) * scale * 0.4)))

        # Color
        color_idx = (nod.nodule_id - 1) % len(NODULE_COLORS)
        fill_color, outline_color = NODULE_COLORS[color_idx]

        draw.ellipse(
            [nod_cx - nod_r, nod_cy - nod_r,
             nod_cx + nod_r, nod_cy + nod_r],
            fill=fill_color, outline=outline_color, width=2 * ss
        )

        # Label
        label = f"N{nod.nodule_id}"
        bbox = draw.textbbox((0, 0), label, font=font_small)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((nod_cx - tw // 2, nod_cy - th // 2), label,
                  fill=(255, 255, 255), font=font_small)

    def _draw_legend(self, draw: ImageDraw.Draw, nodules: List[NodulePosition],
                     y_offset: int, canvas_w: int, fonts: tuple, ss: int):
        """Draw legend with nodule colors and dimensions"""
        _, _, font_small, _ = fonts

        if not nodules:
            return

        x = 30 * ss
        y = y_offset

        for nod in nodules:
            color_idx = (nod.nodule_id - 1) % len(NODULE_COLORS)
            fill_color, _ = NODULE_COLORS[color_idx]

            # Color swatch
            draw.rectangle([x, y, x + 12 * ss, y + 12 * ss], fill=fill_color)

            # Label
            side_text = "D" if nod.side == "RT" else "G"
            dims = ""
            if nod.height_mm > 0 or nod.width_mm > 0:
                parts = []
                if nod.height_mm > 0:
                    parts.append(f"{nod.height_mm:.1f}")
                if nod.width_mm > 0:
                    parts.append(f"{nod.width_mm:.1f}")
                if nod.length_mm > 0:
                    parts.append(f"{nod.length_mm:.1f}")
                dims = f" ({' x '.join(parts)} mm)"

            text = f"N{nod.nodule_id} ({side_text}){dims}"
            draw.text((x + 18 * ss, y - 1 * ss), text,
                      fill=COLOR_TEXT, font=font_small)

            x += (len(text) * 7 + 40) * ss
            # Wrap to next line if needed
            if x > canvas_w - 100 * ss:
                x = 30 * ss
                y += 18 * ss
