"""
Thyroid schema renderer using Pillow.
Generates anatomical thyroid diagram based on a traced reference template:
- Vue de face: butterfly outline traced from standard echography schema (center)
- Coupes longitudinales: sagittal sections of each lobe (left & right)
- Orientation crosses with arrows (AV/AR/HT/BS, HT/BS/D/G)
- Nodule positions overlaid on all views

Uses 3x supersampling + LANCZOS downscale for anti-aliased rendering.
Anatomical convention: patient's right (lobe droit) displayed on viewer's left.
"""

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from typing import List
from .models import NodulePosition, ThyroidGeometry, VerticalLevel, DepthLevel, LateralLevel

# Canvas dimensions (final output)
CANVAS_W = 1000
CANVAS_H = 800
SUPERSAMPLE = 3

# Template image for the butterfly thyroid shape
TEMPLATE_PATH = Path(__file__).parent / 'thyroid_template.png'

# Colors
COLOR_BG = (255, 255, 255)
COLOR_OUTLINE = (35, 35, 35)
COLOR_LOBE_FILL = (253, 235, 220)
COLOR_TEXT = (30, 30, 30)
COLOR_CROSS = (50, 50, 50)

# Nodule colors (fill, outline)
NODULE_COLORS = [
    ((215, 70, 70), (165, 30, 30)),     # Red
    ((55, 125, 215), (25, 75, 165)),    # Blue
    ((65, 165, 65), (25, 115, 25)),     # Green
    ((215, 145, 25), (165, 105, 5)),    # Orange
    ((165, 65, 215), (125, 25, 165)),   # Purple
    ((215, 65, 165), (165, 25, 125)),   # Pink
]

# Template geometry (normalized coordinates within the template image)
# These define where the lobes are within the butterfly template
TMPL_RIGHT_LOBE_CX = 0.28   # Right lobe center x (viewer's left)
TMPL_LEFT_LOBE_CX = 0.72    # Left lobe center x (viewer's right)
TMPL_LOBE_CY = 0.50         # Lobe vertical center
TMPL_SUP_Y = 0.18           # Superior region y
TMPL_INF_Y = 0.82           # Inferior region y
TMPL_LAT_OFFSET = 0.08      # Lateral/medial offset from lobe center


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """Get a TrueType font, falling back to default"""
    for path in ["C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/segoeui.ttf",
                 "C:/Windows/Fonts/calibri.ttf"]:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


class ThyroidRenderer:
    """Renders anatomical thyroid schema using traced template and nodule positions"""

    def __init__(self):
        self.ss = SUPERSAMPLE

    def render(self, geometry: ThyroidGeometry, nodules: List[NodulePosition],
               output_path: str, logger=None) -> bool:
        """Render the thyroid schema to a PNG file."""
        try:
            ss = self.ss
            w, h = CANVAS_W * ss, CANVAS_H * ss
            img = Image.new('RGBA', (w, h), COLOR_BG + (255,))
            draw = ImageDraw.Draw(img)

            fonts = {
                'title': _get_font(16 * ss),
                'label': _get_font(13 * ss),
                'small': _get_font(10 * ss),
                'nodule': _get_font(9 * ss),
                'cross': _get_font(12 * ss),
            }

            # Layout columns
            left_cx = 155 * ss
            center_cx = w // 2
            right_cx = w - 155 * ss
            main_cy = 280 * ss

            # Titles
            self._centered_text(draw, "Lobe droit", left_cx, 40 * ss, fonts['title'])
            self._centered_text(draw, "Vue de face", center_cx, 40 * ss, fonts['title'])
            self._centered_text(draw, "Lobe gauche", right_cx, 40 * ss, fonts['title'])

            # Frontal view (butterfly template)
            self._draw_frontal_template(img, draw, geometry, nodules,
                                         center_cx, main_cy, fonts, ss, logger)

            # Longitudinal sections
            self._draw_longitudinal(draw, geometry, nodules, "RT",
                                     left_cx, main_cy + 15 * ss, fonts, ss)
            self._draw_longitudinal(draw, geometry, nodules, "LT",
                                     right_cx, main_cy + 15 * ss, fonts, ss)

            # Sub-labels
            long_label_y = main_cy + 200 * ss
            self._centered_text(draw, "Coupe", left_cx, long_label_y, fonts['label'])
            self._centered_text(draw, "longitudinale", left_cx, long_label_y + 18 * ss, fonts['label'])
            self._centered_text(draw, "Coupe", right_cx, long_label_y, fonts['label'])
            self._centered_text(draw, "longitudinale", right_cx, long_label_y + 18 * ss, fonts['label'])

            # Orientation crosses
            cross_y = main_cy + 310 * ss
            self._draw_orientation_cross(draw, left_cx, cross_y,
                                          "AV", "AR", "HT", "BS", fonts, ss)
            self._draw_orientation_cross(draw, center_cx, cross_y,
                                          "HT", "BS", "D", "G", fonts, ss)
            self._draw_orientation_cross(draw, right_cx, cross_y,
                                          "AV", "AR", "HT", "BS", fonts, ss)

            # Legend
            self._draw_legend(draw, nodules, 30 * ss, h - 60 * ss, w, fonts, ss)

            # Convert to RGB and downsample
            img_rgb = Image.new('RGB', img.size, COLOR_BG)
            img_rgb.paste(img, (0, 0), img)
            img_rgb = img_rgb.resize((CANVAS_W, CANVAS_H), Image.LANCZOS)
            img_rgb.save(output_path, 'PNG')

            if logger:
                logger.info(f"Thyroid schema generated: {output_path}")
            return True

        except Exception as e:
            if logger:
                logger.error(f"Failed to render thyroid schema: {e}", exc_info=e)
            return False

    # ----------------------------------------------------------------
    # Frontal view using template image
    # ----------------------------------------------------------------

    def _draw_frontal_template(self, img, draw, geometry, nodules,
                                cx, cy, fonts, ss, logger=None):
        """Draw the frontal view by scaling and pasting the butterfly template."""
        # Load template
        if not TEMPLATE_PATH.exists():
            if logger:
                logger.warning(f"Template not found: {TEMPLATE_PATH}, using fallback")
            self._draw_frontal_fallback(draw, geometry, nodules, cx, cy, fonts, ss)
            return

        template = Image.open(str(TEMPLATE_PATH)).convert('RGBA')
        tw, th = template.size

        # Target size for the butterfly on canvas (in ss-pixels)
        # Scale proportionally based on measurements
        ref_h, ref_w = 45.0, 15.0
        max_h = max(geometry.right_height, geometry.left_height, 1)
        max_w = max(geometry.right_width, geometry.left_width, 1)
        scale_h = max(0.80, min(1.20, max_h / ref_h))
        scale_w = max(0.80, min(1.20, max_w / ref_w))

        target_w = int(330 * ss * scale_w)
        target_h = int(target_w * th / tw * scale_h)

        # Clamp height
        max_target_h = 420 * ss
        if target_h > max_target_h:
            target_h = max_target_h
            target_w = int(target_h * tw / th)

        # Scale template
        scaled = template.resize((target_w, target_h), Image.LANCZOS)

        # Position: centered at (cx, cy)
        paste_x = cx - target_w // 2
        paste_y = cy - target_h // 2

        # Composite template onto canvas
        img.paste(scaled, (paste_x, paste_y), scaled)

        # Re-create draw object after paste (needed for subsequent drawing)
        draw = ImageDraw.Draw(img)

        # Draw nodules on top of template
        for nod in nodules:
            self._draw_nodule_frontal(draw, nod, paste_x, paste_y,
                                       target_w, target_h, fonts, ss)

    def _draw_nodule_frontal(self, draw, nod, tmpl_x, tmpl_y,
                              tmpl_w, tmpl_h, fonts, ss):
        """Position and draw a nodule on the frontal template view."""
        if nod.is_isthmic:
            nx = tmpl_x + int(tmpl_w * 0.50)
            ny = tmpl_y + int(tmpl_h * TMPL_LOBE_CY)
        elif nod.side == "RT":
            nx = tmpl_x + int(tmpl_w * TMPL_RIGHT_LOBE_CX)
            ny = tmpl_y + int(tmpl_h * TMPL_LOBE_CY)
        else:
            nx = tmpl_x + int(tmpl_w * TMPL_LEFT_LOBE_CX)
            ny = tmpl_y + int(tmpl_h * TMPL_LOBE_CY)

        if not nod.is_isthmic:
            # Vertical positioning
            if nod.vertical == VerticalLevel.SUPERIOR:
                ny = tmpl_y + int(tmpl_h * TMPL_SUP_Y)
            elif nod.vertical == VerticalLevel.INFERIOR:
                ny = tmpl_y + int(tmpl_h * TMPL_INF_Y)

            # Lateral offset
            lat_px = int(tmpl_w * TMPL_LAT_OFFSET)
            if nod.lateral == LateralLevel.LATERAL:
                nx += -lat_px if nod.side == "RT" else lat_px
            elif nod.lateral == LateralLevel.MEDIAL:
                nx += lat_px if nod.side == "RT" else -lat_px

        # Nodule size proportional to actual dimensions
        px_per_mm = tmpl_h / max(45.0 * 2, 1)
        nw = max(10*ss, min(45*ss, int(nod.width_mm * px_per_mm * 0.7))) if nod.width_mm > 0 else 14*ss
        nh = max(10*ss, min(45*ss, int(nod.height_mm * px_per_mm * 0.7))) if nod.height_mm > 0 else 14*ss

        self._draw_nodule_ellipse(draw, nx, ny, nw, nh, nod.nodule_id, fonts, ss)

    def _draw_frontal_fallback(self, draw, geometry, nodules, cx, cy, fonts, ss):
        """Fallback: draw simple ellipses if template is missing."""
        hw, hh = 150 * ss, 180 * ss
        # Right lobe
        draw.ellipse([cx - hw - 30*ss, cy - hh, cx - 30*ss, cy + hh],
                     fill=COLOR_LOBE_FILL, outline=COLOR_OUTLINE, width=2*ss)
        # Left lobe
        draw.ellipse([cx + 30*ss, cy - hh, cx + hw + 30*ss, cy + hh],
                     fill=COLOR_LOBE_FILL, outline=COLOR_OUTLINE, width=2*ss)

    # ----------------------------------------------------------------
    # Longitudinal section view
    # ----------------------------------------------------------------

    def _draw_longitudinal(self, draw, geometry, nodules, side, cx, cy, fonts, ss):
        """Draw a longitudinal (sagittal) section of one lobe as an ellipse.

        Orientation: horizontal = craniocaudal (HT left, BS right)
                     vertical   = anteroposterior (AV up, AR down)
        """
        if side == "RT":
            lobe_h = geometry.right_height
            lobe_ap = geometry.right_length
        else:
            lobe_h = geometry.left_height
            lobe_ap = geometry.left_length

        base_ew = 130 * ss
        base_eh = 75 * ss
        ew = max(80*ss, min(160*ss, int(base_ew * lobe_h / 45.0)))
        eh = max(45*ss, min(110*ss, int(base_eh * lobe_ap / 15.0)))

        draw.ellipse([cx - ew, cy - eh, cx + ew, cy + eh],
                     fill=COLOR_LOBE_FILL, outline=COLOR_OUTLINE, width=2 * ss)

        side_nodules = [n for n in nodules if n.side == side and not n.is_isthmic]
        for nod in side_nodules:
            self._draw_nodule_longitudinal(draw, nod, cx, cy, ew, eh, fonts, ss)

    def _draw_nodule_longitudinal(self, draw, nod, cx, cy, ew, eh, fonts, ss):
        """Position and draw a nodule on a longitudinal section.

        Horizontal = craniocaudal: SUP left, INF right
        Vertical = anteroposterior: ANT up, POST down
        """
        nx, ny = cx, cy

        if nod.vertical == VerticalLevel.SUPERIOR:
            nx = cx - int(ew * 0.40)
        elif nod.vertical == VerticalLevel.INFERIOR:
            nx = cx + int(ew * 0.40)

        if nod.depth == DepthLevel.ANTERIOR:
            ny = cy - int(eh * 0.35)
        elif nod.depth == DepthLevel.POSTERIOR:
            ny = cy + int(eh * 0.35)

        px_per_mm = (ew * 2) / max(45.0, 1)
        nw = max(8*ss, min(35*ss, int(nod.height_mm * px_per_mm * 0.25))) if nod.height_mm > 0 else 12*ss
        nh = max(8*ss, min(35*ss, int(nod.length_mm * px_per_mm * 0.25))) if nod.length_mm > 0 else 12*ss

        self._draw_nodule_ellipse(draw, nx, ny, nw, nh, nod.nodule_id, fonts, ss)

    # ----------------------------------------------------------------
    # Common nodule drawing
    # ----------------------------------------------------------------

    def _draw_nodule_ellipse(self, draw, cx, cy, hw, hh, nodule_id, fonts, ss):
        """Draw a colored nodule ellipse with label."""
        idx = (nodule_id - 1) % len(NODULE_COLORS)
        fill, outline = NODULE_COLORS[idx]

        draw.ellipse([cx - hw, cy - hh, cx + hw, cy + hh],
                     fill=fill, outline=outline, width=2 * ss)

        label = f"N{nodule_id}"
        bbox = draw.textbbox((0, 0), label, font=fonts['nodule'])
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((cx - tw // 2, cy - th // 2), label,
                  fill=(255, 255, 255), font=fonts['nodule'])

    # ----------------------------------------------------------------
    # Orientation crosses
    # ----------------------------------------------------------------

    def _draw_orientation_cross(self, draw, cx, cy, top_lbl, bot_lbl,
                                 left_lbl, right_lbl, fonts, ss):
        """Draw an orientation cross with arrows and labels."""
        arm = 30 * ss

        self._draw_arrow(draw, cx, cy, cx, cy - arm, ss)
        self._draw_arrow(draw, cx, cy, cx, cy + arm, ss)
        self._draw_arrow(draw, cx, cy, cx - arm, cy, ss)
        self._draw_arrow(draw, cx, cy, cx + arm, cy, ss)

        gap = 6 * ss
        font = fonts['cross']
        self._centered_text(draw, top_lbl, cx, cy - arm - 16 * ss, font, COLOR_CROSS)
        self._centered_text(draw, bot_lbl, cx, cy + arm + gap, font, COLOR_CROSS)

        bbox = draw.textbbox((0, 0), left_lbl, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((cx - arm - gap - tw, cy - th // 2), left_lbl,
                  fill=COLOR_CROSS, font=font)
        draw.text((cx + arm + gap, cy - th // 2), right_lbl,
                  fill=COLOR_CROSS, font=font)

    def _draw_arrow(self, draw, x1, y1, x2, y2, ss):
        """Draw a line with arrowhead at (x2, y2)."""
        draw.line([(x1, y1), (x2, y2)], fill=COLOR_CROSS, width=max(1, ss))

        angle = math.atan2(y2 - y1, x2 - x1)
        arrow_len = 7 * ss
        spread = math.pi / 6
        ax1 = x2 - arrow_len * math.cos(angle - spread)
        ay1 = y2 - arrow_len * math.sin(angle - spread)
        ax2 = x2 - arrow_len * math.cos(angle + spread)
        ay2 = y2 - arrow_len * math.sin(angle + spread)
        draw.polygon([(x2, y2), (int(ax1), int(ay1)), (int(ax2), int(ay2))],
                     fill=COLOR_CROSS)

    # ----------------------------------------------------------------
    # Legend
    # ----------------------------------------------------------------

    def _draw_legend(self, draw, nodules, x_start, y, canvas_w, fonts, ss):
        """Draw legend with nodule colors and dimensions."""
        if not nodules:
            return

        x = x_start
        font = fonts['small']

        for nod in nodules:
            idx = (nod.nodule_id - 1) % len(NODULE_COLORS)
            fill, _ = NODULE_COLORS[idx]

            sw = 12 * ss
            draw.rectangle([x, y, x + sw, y + sw], fill=fill, outline=COLOR_OUTLINE, width=ss)

            side_text = "D" if nod.side == "RT" else "G"
            parts = []
            for v in [nod.height_mm, nod.width_mm, nod.length_mm]:
                if v > 0:
                    parts.append(f"{v:.1f}")
            dims = f" ({' x '.join(parts)} mm)" if parts else ""
            text = f"N{nod.nodule_id} ({side_text}){dims}"

            draw.text((x + sw + 6 * ss, y - 1 * ss), text,
                      fill=COLOR_TEXT, font=font)

            bbox = draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            x += sw + 6 * ss + tw + 25 * ss

            if x > canvas_w - 120 * ss:
                x = x_start
                y += 18 * ss

    # ----------------------------------------------------------------
    # Text helper
    # ----------------------------------------------------------------

    def _centered_text(self, draw, text, cx, cy, font, color=COLOR_TEXT):
        """Draw text centered at (cx, cy)."""
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text((cx - tw // 2, cy - th // 2), text, fill=color, font=font)
