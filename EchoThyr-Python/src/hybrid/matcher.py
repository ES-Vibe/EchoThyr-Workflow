"""
Hybrid matcher: combines SR measurement values with OCR-extracted context.
Matches SR measurement sets to images by comparing dimension/volume values.

When the doctor uses the generic "Volume" tool on the GE Logiq ultrasound,
the SR contains precise measurement values but without context (no side, no nodule ID).
The OCR reads image legends to get context (RT/LT, N1/N2, isthmus).
This module matches them by comparing measurement values.
"""

from typing import List, Optional
from src.dicom.sr_parser import RawMeasurementSet, ThyroidReport, ThyroidMeasurement, NoduleMeasurement
from src.ocr.tesseract_engine import OCRContext


class HybridMatcher:
    """Match SR measurements to OCR contexts by value comparison"""

    VOLUME_TOLERANCE = 0.1    # ml (image shows 2 decimal places)
    DIMENSION_TOLERANCE = 0.1  # cm

    def match(
        self,
        sr_report: ThyroidReport,
        raw_sets: List[RawMeasurementSet],
        ocr_contexts: List[OCRContext],
        logger=None
    ) -> ThyroidReport:
        """
        Match SR measurement sets to OCR contexts and populate the ThyroidReport.

        Args:
            sr_report: ThyroidReport with patient info already populated
            raw_sets: Raw measurement sets from SR (uncontextualized)
            ocr_contexts: Context extracted from images via OCR
            logger: Optional logger

        Returns:
            Enriched ThyroidReport with measurements assigned to correct sides/nodules
        """
        # Separate OCR contexts by type
        matchable_by_volume = [c for c in ocr_contexts if c.has_measurements and c.volume_ml > 0]
        matchable_by_dims = [c for c in ocr_contexts if c.has_measurements and c.volume_ml == 0 and c.dimensions_cm]
        isthmus_contexts = [c for c in ocr_contexts if c.is_isthmus]

        unmatched_sr = list(raw_sets)
        matched_pairs = []  # List of (RawMeasurementSet, OCRContext)

        # Pass 1: Match by volume (highest confidence)
        for sr_set in list(unmatched_sr):
            if sr_set.volume_ml <= 0:
                continue
            for ocr in list(matchable_by_volume):
                if abs(sr_set.volume_ml - ocr.volume_ml) < self.VOLUME_TOLERANCE:
                    matched_pairs.append((sr_set, ocr))
                    unmatched_sr.remove(sr_set)
                    matchable_by_volume.remove(ocr)
                    if logger:
                        logger.info(f"Matched by volume ({sr_set.volume_ml:.2f}ml): "
                                   f"SR resultNo={sr_set.result_no} <-> OCR {ocr.side} {ocr.legend_text}")
                    break

        # Pass 2: Match remaining by dimensions (sorted comparison)
        for sr_set in list(unmatched_sr):
            sr_dims = sorted([d for d in [sr_set.height_cm, sr_set.width_cm, sr_set.length_cm] if d > 0])
            if not sr_dims:
                continue

            # Try volume-matchable contexts that didn't match in pass 1
            all_remaining = list(matchable_by_volume) + list(matchable_by_dims)
            for ocr in all_remaining:
                ocr_dims = sorted(ocr.dimensions_cm)
                if len(sr_dims) == len(ocr_dims) and len(sr_dims) > 0:
                    if all(abs(s - o) < self.DIMENSION_TOLERANCE for s, o in zip(sr_dims, ocr_dims)):
                        matched_pairs.append((sr_set, ocr))
                        unmatched_sr.remove(sr_set)
                        if ocr in matchable_by_volume:
                            matchable_by_volume.remove(ocr)
                        if ocr in matchable_by_dims:
                            matchable_by_dims.remove(ocr)
                        if logger:
                            logger.info(f"Matched by dimensions ({sr_dims}): "
                                       f"SR resultNo={sr_set.result_no} <-> OCR {ocr.side} {ocr.legend_text}")
                        break

        # Pass 3: Match remaining by partial dimensions + side
        # When OCR extracts only 1-2 dimensions, match if at least one dimension
        # from the SR matches one from the OCR (within tolerance) AND sides match
        for sr_set in list(unmatched_sr):
            sr_dims = [d for d in [sr_set.height_cm, sr_set.width_cm, sr_set.length_cm] if d > 0]
            if not sr_dims:
                continue

            all_remaining = list(matchable_by_volume) + list(matchable_by_dims)
            best_match = None
            best_count = 0

            for ocr in all_remaining:
                if ocr.is_isthmus:
                    continue
                # Require side to match
                if not ocr.side:
                    continue

                # Count how many OCR dimensions match any SR dimension
                match_count = 0
                for ocr_dim in ocr.dimensions_cm:
                    for sr_dim in sr_dims:
                        if abs(sr_dim - ocr_dim) < self.DIMENSION_TOLERANCE:
                            match_count += 1
                            break

                if match_count > 0 and match_count > best_count:
                    best_count = match_count
                    best_match = ocr

            if best_match:
                matched_pairs.append((sr_set, best_match))
                unmatched_sr.remove(sr_set)
                if best_match in matchable_by_volume:
                    matchable_by_volume.remove(best_match)
                if best_match in matchable_by_dims:
                    matchable_by_dims.remove(best_match)
                if logger:
                    logger.info(f"Matched by partial dimensions ({best_count} dim(s), side={best_match.side}): "
                               f"SR resultNo={sr_set.result_no} <-> OCR {best_match.side} {best_match.legend_text[:60]}")

        # Pass 4: Handle isthmus (OCR-only measurement, not in SR volume data)
        for ocr in isthmus_contexts:
            if ocr.dimensions_cm:
                # Isthmus is a single distance measurement, take the first/only value
                sr_report.isthmus_mm = ocr.dimensions_cm[0] * 10  # cm to mm
                if logger:
                    logger.info(f"Isthmus from OCR: {sr_report.isthmus_mm:.1f} mm")

        # Build ThyroidReport from matched pairs
        for sr_set, ocr in matched_pairs:
            side = "Rt" if ocr.side == "RT" else ("Lt" if ocr.side == "LT" else "")

            if ocr.is_isthmus:
                # Isthmus matched to SR (rare: measured with volume tool)
                if sr_set.height_cm > 0:
                    sr_report.isthmus_mm = max(sr_set.height_cm, sr_set.width_cm, sr_set.length_cm) * 10
                continue

            if ocr.nodule:
                # Nodule measurement
                try:
                    nodule_id = int(ocr.nodule)
                except ValueError:
                    nodule_id = len(sr_report.nodules) + 1

                nodule = NoduleMeasurement(
                    nodule_id=nodule_id,
                    side=side,
                    height=sr_set.height_cm * 10,   # cm to mm
                    width=sr_set.width_cm * 10,
                    length=sr_set.length_cm * 10,
                    volume=sr_set.volume_ml
                )
                sr_report.nodules.append(nodule)
                if logger:
                    logger.info(f"Nodule N{nodule_id} ({side}): "
                               f"{nodule.height:.1f}x{nodule.width:.1f}x{nodule.length:.1f}mm "
                               f"vol={nodule.volume:.2f}ml")
            else:
                # Lobe measurement
                if not side:
                    if logger:
                        logger.warning(f"No side detected for lobe measurement (resultNo={sr_set.result_no})")
                    continue

                lobe = sr_report.right_lobe if side == "Rt" else sr_report.left_lobe

                for label, val in [("H", sr_set.height_cm), ("W", sr_set.width_cm), ("L", sr_set.length_cm)]:
                    if val > 0:
                        name = f"Thyroide {label}"
                        lobe[name] = ThyroidMeasurement(
                            name=name, side=side, value=val, unit="cm",
                            measurement_type="MEASURE"
                        )

                if sr_set.volume_ml > 0:
                    name = "Vol Thyroide"
                    lobe[name] = ThyroidMeasurement(
                        name=name, side=side, value=sr_set.volume_ml, unit="ml",
                        measurement_type="CALCULATION"
                    )

                if logger:
                    side_text = "droit" if side == "Rt" else "gauche"
                    logger.info(f"Lobe {side_text}: H={sr_set.height_cm:.2f}cm "
                               f"W={sr_set.width_cm:.2f}cm L={sr_set.length_cm:.2f}cm "
                               f"Vol={sr_set.volume_ml:.2f}ml")

        # Pass 5: OCR-only nodules (not matched to any SR set)
        # When a nodule image has 3 dimensions from OCR but no corresponding SR measurement,
        # create a nodule entry with volume calculated from the ellipsoid formula
        import math
        all_matched_ocr = {id(ocr) for _, ocr in matched_pairs}
        all_remaining_ocr = list(matchable_by_volume) + list(matchable_by_dims)
        for ocr in all_remaining_ocr:
            if id(ocr) in all_matched_ocr:
                continue
            if not ocr.nodule or ocr.is_isthmus:
                continue
            if len(ocr.dimensions_cm) < 3:
                continue

            side = "Rt" if ocr.side == "RT" else ("Lt" if ocr.side == "LT" else "")
            try:
                nodule_id = int(ocr.nodule)
            except ValueError:
                nodule_id = len(sr_report.nodules) + 1

            # Dimensions in mm (OCR gives cm)
            dims_mm = sorted(ocr.dimensions_cm, reverse=True)[:3]
            h_mm, w_mm, l_mm = dims_mm[0] * 10, dims_mm[1] * 10, dims_mm[2] * 10

            # Ellipsoid volume: V = π/6 × H × W × L (in ml, from cm)
            vol_ml = (math.pi / 6) * dims_mm[0] * dims_mm[1] * dims_mm[2]

            nodule = NoduleMeasurement(
                nodule_id=nodule_id,
                side=side,
                height=h_mm,
                width=w_mm,
                length=l_mm,
                volume=vol_ml
            )
            sr_report.nodules.append(nodule)
            if logger:
                logger.info(f"Nodule N{nodule_id} ({side}) from OCR only: "
                           f"{h_mm:.1f}x{w_mm:.1f}x{l_mm:.1f}mm "
                           f"vol={vol_ml:.2f}ml (calculated)")

        # Log unmatched SR sets
        if unmatched_sr and logger:
            for sr_set in unmatched_sr:
                logger.warning(f"Unmatched SR measurement: resultNo={sr_set.result_no}, "
                             f"H={sr_set.height_cm:.2f}cm W={sr_set.width_cm:.2f}cm "
                             f"L={sr_set.length_cm:.2f}cm Vol={sr_set.volume_ml:.2f}ml")

        if logger:
            logger.info(f"Hybrid matching complete: {len(matched_pairs)} matched, "
                       f"{len(unmatched_sr)} unmatched SR sets, "
                       f"Right={len(sr_report.right_lobe)}, Left={len(sr_report.left_lobe)}, "
                       f"Nodules={len(sr_report.nodules)}, Isthmus={sr_report.isthmus_mm:.1f}mm")

        return sr_report
