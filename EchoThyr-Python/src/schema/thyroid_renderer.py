"""
Thyroid schema renderer using Pillow.
Generates anatomical thyroid diagram inspired by standard echography report schemas:
- Vue de face: butterfly-shaped frontal view (center)
- Coupes longitudinales: sagittal sections of each lobe (left & right)
- Orientation crosses with arrows (AV/AR/HT/BS, HT/BS/D/G)
- Nodule positions overlaid on all views

Uses 3x supersampling + LANCZOS downscale for anti-aliased rendering.
Anatomical convention: patient's right (lobe droit) displayed on viewer's left.
"""

import math
from PIL import Image, ImageDraw, ImageFont
from typing import List, Tuple
from .models import NodulePosition, ThyroidGeometry, VerticalLevel, DepthLevel, LateralLevel

# Canvas dimensions (final output)
CANVAS_W = 1000
CANVAS_H = 800
SUPERSAMPLE = 3

# Colors
COLOR_BG = (255, 255, 255)
COLOR_OUTLINE = (35, 35, 35)          # Near-black for anatomy outlines
COLOR_LOBE_FILL = (253, 235, 220)     # Very light peach fill
COLOR_TEXT = (30, 30, 30)             # Near-black for labels
COLOR_CROSS = (50, 50, 50)           # Dark gray for orientation crosses

# Nodule colors (fill, outline) — distinct per nodule
NODULE_COLORS = [
    ((215, 70, 70), (165, 30, 30)),     # Red
    ((55, 125, 215), (25, 75, 165)),    # Blue
    ((65, 165, 65), (25, 115, 25)),     # Green
    ((215, 145, 25), (165, 105, 5)),    # Orange
    ((165, 65, 215), (125, 25, 165)),   # Purple
    ((215, 65, 165), (165, 25, 125)),   # Pink
]


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
    """Renders anatomical thyroid schema with butterfly shape and nodule positions"""

    def __init__(self):
        self.ss = SUPERSAMPLE

    def render(self, geometry: ThyroidGeometry, nodules: List[NodulePosition],
               output_path: str, logger=None) -> bool:
        """Render the thyroid schema to a PNG file."""
        try:
            ss = self.ss
            w, h = CANVAS_W * ss, CANVAS_H * ss
            img = Image.new('RGB', (w, h), COLOR_BG)
            draw = ImageDraw.Draw(img)

            fonts = {
                'title': _get_font(16 * ss),
                'label': _get_font(13 * ss),
                'small': _get_font(10 * ss),
                'nodule': _get_font(9 * ss),
                'cross': _get_font(12 * ss),
            }

            # Layout — three columns
            left_cx = 155 * ss        # Lobe droit (longitudinal section)
            center_cx = w // 2        # Vue de face (butterfly)
            right_cx = w - 155 * ss   # Lobe gauche (longitudinal section)
            main_cy = 280 * ss        # Vertical center of main drawings

            # --- Titles ---
            self._centered_text(draw, "Lobe droit", left_cx, 40 * ss, fonts['title'])
            self._centered_text(draw, "Vue de face", center_cx, 40 * ss, fonts['title'])
            self._centered_text(draw, "Lobe gauche", right_cx, 40 * ss, fonts['title'])

            # --- Frontal butterfly view (center) ---
            self._draw_frontal_butterfly(draw, geometry, nodules,
                                         center_cx, main_cy, fonts, ss)

            # --- Longitudinal sections (left & right) ---
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

            # --- Orientation crosses ---
            cross_y = main_cy + 310 * ss
            # Longitudinal sections: AV (up), AR (down), HT (left), BS (right)
            self._draw_orientation_cross(draw, left_cx, cross_y,
                                          "AV", "AR", "HT", "BS", fonts, ss)
            # Frontal view: HT (up), BS (down), D (left), G (right)
            self._draw_orientation_cross(draw, center_cx, cross_y,
                                          "HT", "BS", "D", "G", fonts, ss)
            self._draw_orientation_cross(draw, right_cx, cross_y,
                                          "AV", "AR", "HT", "BS", fonts, ss)

            # --- Legend ---
            self._draw_legend(draw, nodules, 30 * ss, h - 60 * ss, w, fonts, ss)

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

    # ----------------------------------------------------------------
    # Bezier curve utilities
    # ----------------------------------------------------------------

    def _cubic_bezier(self, p0, p1, p2, p3, n=25):
        """Generate n+1 points along a cubic Bezier curve."""
        pts = []
        for i in range(n + 1):
            t = i / n
            mt = 1 - t
            x = mt**3*p0[0] + 3*mt**2*t*p1[0] + 3*mt*t**2*p2[0] + t**3*p3[0]
            y = mt**3*p0[1] + 3*mt**2*t*p1[1] + 3*mt*t**2*p2[1] + t**3*p3[1]
            pts.append((int(round(x)), int(round(y))))
        return pts

    def _thyroid_outline(self, cx, cy, hw, hh):
        """Build the butterfly thyroid outline as a closed polygon.

        cx, cy: center of the thyroid shape
        hw: half-width (center to widest lateral edge of a lobe)
        hh: half-height (center to superior/inferior pole tip)

        Returns list of (x, y) integer tuples forming a closed polygon.
        """
        bz = lambda p0, p1, p2, p3: self._cubic_bezier(p0, p1, p2, p3, 30)[:-1]

        # Key anatomical landmarks — tuned to match reference butterfly shape
        # The V-notch between superior poles is deep (~55% from top)
        # Superior poles are narrow and prominent
        # Lobes are wide and bulbous
        # Inferior poles taper with a concavity between them
        tn  = (cx, cy - hh * 0.40)            # top notch (deep V between poles)
        rsp = (cx + hw * 0.38, cy - hh)        # right superior pole peak (narrow)
        rw  = (cx + hw, cy + hh * 0.10)        # right lobe widest point
        rip = (cx + hw * 0.48, cy + hh)        # right inferior pole tip
        bn  = (cx, cy + hh * 0.28)             # bottom notch (between inferior poles)
        lip = (cx - hw * 0.48, cy + hh)        # left inferior pole tip
        lw  = (cx - hw, cy + hh * 0.10)        # left lobe widest point
        lsp = (cx - hw * 0.38, cy - hh)        # left superior pole peak (narrow)

        points = []

        # Segment 1: top notch → right superior pole (sharp upward sweep)
        points += bz(tn,
                     (cx + hw * 0.03, cy - hh * 0.52),
                     (cx + hw * 0.18, cy - hh * 1.08),
                     rsp)

        # Segment 2: right sup pole → right widest (sweeping outward and down)
        points += bz(rsp,
                     (cx + hw * 0.62, cy - hh * 0.98),
                     (cx + hw * 1.06, cy - hh * 0.45),
                     rw)

        # Segment 3: right widest → right inferior pole (outer right, lower half)
        points += bz(rw,
                     (cx + hw * 1.06, cy + hh * 0.62),
                     (cx + hw * 0.72, cy + hh * 0.94),
                     rip)

        # Segment 4: right inf pole → bottom notch (inner concavity, curving up)
        points += bz(rip,
                     (cx + hw * 0.28, cy + hh * 1.06),
                     (cx + hw * 0.05, cy + hh * 0.42),
                     bn)

        # Segment 5: bottom notch → left inf pole (mirror of 4)
        points += bz(bn,
                     (cx - hw * 0.05, cy + hh * 0.42),
                     (cx - hw * 0.28, cy + hh * 1.06),
                     lip)

        # Segment 6: left inf pole → left widest (mirror of 3)
        points += bz(lip,
                     (cx - hw * 0.72, cy + hh * 0.94),
                     (cx - hw * 1.06, cy + hh * 0.62),
                     lw)

        # Segment 7: left widest → left sup pole (mirror of 2)
        points += bz(lw,
                     (cx - hw * 1.06, cy - hh * 0.45),
                     (cx - hw * 0.62, cy - hh * 0.98),
                     lsp)

        # Segment 8: left sup pole → top notch (mirror of 1)
        points += bz(lsp,
                     (cx - hw * 0.18, cy - hh * 1.08),
                     (cx - hw * 0.03, cy - hh * 0.52),
                     tn)

        return points

    # ----------------------------------------------------------------
    # Frontal butterfly view
    # ----------------------------------------------------------------

    def _draw_frontal_butterfly(self, draw, geometry, nodules, cx, cy, fonts, ss):
        """Draw the frontal (coronal) butterfly thyroid shape with nodules."""

        # Scale butterfly dimensions from actual measurements
        ref_h, ref_w = 45.0, 15.0  # reference lobe mm
        base_hw = 165 * ss   # base half-width in ss-pixels
        base_hh = 220 * ss   # base half-height in ss-pixels (taller for anatomical shape)

        max_h = max(geometry.right_height, geometry.left_height, 1)
        max_w = max(geometry.right_width, geometry.left_width, 1)
        scale_h = max(0.75, min(1.25, max_h / ref_h))
        scale_w = max(0.75, min(1.25, max_w / ref_w))

        hw = int(base_hw * scale_w)
        hh = int(base_hh * scale_h)

        # Generate and draw outline
        outline = self._thyroid_outline(cx, cy, hw, hh)

        # Fill
        draw.polygon(outline, fill=COLOR_LOBE_FILL)

        # Outline (draw as connected line segments for smooth line)
        closed = outline + [outline[0]]
        draw.line(closed, fill=COLOR_OUTLINE, width=2 * ss, joint='curve')

        # Draw nodules on frontal view
        for nod in nodules:
            self._draw_nodule_frontal(draw, nod, cx, cy, hw, hh, fonts, ss)

    def _draw_nodule_frontal(self, draw, nod, cx, cy, hw, hh, fonts, ss):
        """Position and draw a nodule on the frontal butterfly view."""
        # Determine lobe center x
        # Right lobe center is at ~cx - hw*0.55, left at ~cx + hw*0.55
        if nod.is_isthmic:
            nx, ny = cx, cy
        elif nod.side == "RT":
            nx = cx - int(hw * 0.55)
            ny = cy
        else:
            nx = cx + int(hw * 0.55)
            ny = cy

        if not nod.is_isthmic:
            # Vertical offset within lobe
            if nod.vertical == VerticalLevel.SUPERIOR:
                ny = cy - int(hh * 0.35)
            elif nod.vertical == VerticalLevel.INFERIOR:
                ny = cy + int(hh * 0.35)

            # Lateral offset (lateral = away from center, medial = toward center)
            lat_offset = int(hw * 0.12)
            if nod.lateral == LateralLevel.LATERAL:
                nx += -lat_offset if nod.side == "RT" else lat_offset
            elif nod.lateral == LateralLevel.MEDIAL:
                nx += lat_offset if nod.side == "RT" else -lat_offset

        # Nodule display size (proportional to actual mm, clamped)
        max_lobe = max(geometry.right_height, geometry.left_height, 30) if hasattr(self, '_geom') else 45.0
        px_per_mm = (hh * 2) / max(max_lobe, 30)
        nw = max(10*ss, min(50*ss, int(nod.width_mm * px_per_mm * 0.35))) if nod.width_mm > 0 else 14*ss
        nh = max(10*ss, min(50*ss, int(nod.height_mm * px_per_mm * 0.35))) if nod.height_mm > 0 else 14*ss

        self._draw_nodule_ellipse(draw, nx, ny, nw, nh, nod.nodule_id, fonts, ss)

    # ----------------------------------------------------------------
    # Longitudinal section view
    # ----------------------------------------------------------------

    def _draw_longitudinal(self, draw, geometry, nodules, side, cx, cy, fonts, ss):
        """Draw a longitudinal (sagittal) section of one lobe as an ellipse.

        Orientation: horizontal = craniocaudal (HT left, BS right)
                     vertical   = anteroposterior (AV up, AR down)
        """
        if side == "RT":
            lobe_h = geometry.right_height   # craniocaudal → horizontal
            lobe_ap = geometry.right_length   # anteroposterior → vertical
        else:
            lobe_h = geometry.left_height
            lobe_ap = geometry.left_length

        # Scale to pixels (with clamping)
        base_ew = 130 * ss   # base ellipse half-width for reference 45mm height
        base_eh = 75 * ss    # base ellipse half-height for reference 15mm AP

        ew = max(80*ss, min(160*ss, int(base_ew * lobe_h / 45.0)))
        eh = max(45*ss, min(110*ss, int(base_eh * lobe_ap / 15.0)))

        # Draw ellipse outline (no fill, matching reference style)
        draw.ellipse(
            [cx - ew, cy - eh, cx + ew, cy + eh],
            fill=COLOR_LOBE_FILL, outline=COLOR_OUTLINE, width=2 * ss
        )

        # Draw nodules for this side
        side_nodules = [n for n in nodules if n.side == side and not n.is_isthmic]
        for nod in side_nodules:
            self._draw_nodule_longitudinal(draw, nod, cx, cy, ew, eh, fonts, ss)

    def _draw_nodule_longitudinal(self, draw, nod, cx, cy, ew, eh, fonts, ss):
        """Position and draw a nodule on a longitudinal section.

        Horizontal axis = craniocaudal: SUP→left, INF→right
        Vertical axis = anteroposterior: ANT→up, POST→down
        """
        nx, ny = cx, cy

        # Horizontal: vertical level maps to craniocaudal
        if nod.vertical == VerticalLevel.SUPERIOR:
            nx = cx - int(ew * 0.40)
        elif nod.vertical == VerticalLevel.INFERIOR:
            nx = cx + int(ew * 0.40)

        # Vertical: depth maps to anteroposterior
        if nod.depth == DepthLevel.ANTERIOR:
            ny = cy - int(eh * 0.35)
        elif nod.depth == DepthLevel.POSTERIOR:
            ny = cy + int(eh * 0.35)

        # Nodule size (proportional, clamped)
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
        arm = 30 * ss  # arm length

        # Draw arrows (line + arrowhead)
        self._draw_arrow(draw, cx, cy, cx, cy - arm, ss)   # up
        self._draw_arrow(draw, cx, cy, cx, cy + arm, ss)   # down
        self._draw_arrow(draw, cx, cy, cx - arm, cy, ss)   # left
        self._draw_arrow(draw, cx, cy, cx + arm, cy, ss)   # right

        # Labels
        gap = 6 * ss
        font = fonts['cross']
        self._centered_text(draw, top_lbl, cx, cy - arm - 16 * ss, font, COLOR_CROSS)
        self._centered_text(draw, bot_lbl, cx, cy + arm + gap, font, COLOR_CROSS)
        # Left label (right-aligned before arrow tip)
        bbox = draw.textbbox((0, 0), left_lbl, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((cx - arm - gap - tw, cy - th // 2), left_lbl,
                  fill=COLOR_CROSS, font=font)
        # Right label (left-aligned after arrow tip)
        draw.text((cx + arm + gap, cy - th // 2), right_lbl,
                  fill=COLOR_CROSS, font=font)

    def _draw_arrow(self, draw, x1, y1, x2, y2, ss):
        """Draw a line from (x1,y1) to (x2,y2) with an arrowhead at (x2,y2)."""
        draw.line([(x1, y1), (x2, y2)], fill=COLOR_CROSS, width=max(1, ss))

        # Arrowhead
        angle = math.atan2(y2 - y1, x2 - x1)
        arrow_len = 7 * ss
        spread = math.pi / 6  # 30 degrees
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

            # Color swatch
            sw = 12 * ss
            draw.rectangle([x, y, x + sw, y + sw], fill=fill, outline=COLOR_OUTLINE, width=ss)

            # Text
            side_text = "D" if nod.side == "RT" else "G"
            parts = []
            for v in [nod.height_mm, nod.width_mm, nod.length_mm]:
                if v > 0:
                    parts.append(f"{v:.1f}")
            dims = f" ({' x '.join(parts)} mm)" if parts else ""
            text = f"N{nod.nodule_id} ({side_text}){dims}"

            draw.text((x + sw + 6 * ss, y - 1 * ss), text,
                      fill=COLOR_TEXT, font=font)

            # Advance x
            bbox = draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            x += sw + 6 * ss + tw + 25 * ss

            # Wrap
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
