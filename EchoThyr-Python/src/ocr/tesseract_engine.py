"""
Tesseract OCR engine for extracting measurements from echography images
"""

import pytesseract
import re
from pathlib import Path
from typing import Optional, List, Union
from dataclasses import dataclass
from PIL import Image


@dataclass
class Measurement:
    """Represents an extracted measurement"""
    side: str  # "RT" (right) or "LT" (left)
    nodule: str  # Nodule number (e.g., "1", "2") or empty
    is_isthmus: bool  # True if isthmus measurement
    text: str  # Formatted measurement text (e.g., "45.2 x 23.1 x 18.5 mm")


@dataclass
class OCRContext:
    """Context extracted from image legend + measurement values for hybrid matching"""
    image_path: str             # Path to the JPEG image
    side: str                   # "RT" or "LT" (from legend)
    nodule: str                 # Nodule number or "" (from legend)
    is_isthmus: bool            # True if isthmus (from legend)
    legend_text: str            # Raw legend text for debugging
    dimensions_cm: List[float]  # Dimension values in cm (e.g., [2.20, 4.63, 1.65])
    volume_ml: float = 0.0     # Volume in ml if shown on image
    has_measurements: bool = True  # False for images without measurement overlay


class TesseractEngine:
    """OCR engine using Tesseract"""

    def __init__(self, tesseract_path: str, language: str = "eng", psm: int = 6):
        self.tesseract_path = tesseract_path
        self.language = language
        self.psm = psm

        # Set Tesseract executable path
        pytesseract.pytesseract.tesseract_cmd = tesseract_path

    def extract_measurements(self, image_input: Union[str, Image.Image], logger=None) -> Optional[Measurement]:
        """
        Extract measurements from an echography image

        Args:
            image_input: File path (str) or PIL Image object (raw DICOM pixels)
            logger: Optional logger for debugging

        Returns:
            Measurement object or None if no measurements found
        """
        # Determine if input is a file path or PIL Image
        if isinstance(image_input, str):
            if logger:
                logger.debug(f"Processing image: {image_input}")
            if not Path(image_input).exists():
                if logger:
                    logger.warning(f"Image file not found: {image_input}")
                return None
            ocr_source = image_input
            label = image_input
        else:
            ocr_source = image_input  # PIL Image
            label = "PIL Image"
            if logger:
                logger.debug(f"Processing PIL Image ({image_input.size[0]}x{image_input.size[1]})")

        try:
            # Run Tesseract OCR
            config = f'--psm {self.psm} -l {self.language}'
            text = pytesseract.image_to_string(ocr_source, config=config)

            if not text or not text.strip():
                if logger:
                    logger.debug(f"Tesseract extracted no text from: {label}")
                return None

            if logger:
                preview = text[:min(100, len(text))].replace('\n', ' ')
                logger.debug(f"Tesseract extracted text: {preview}...")

            # Extract measurement data
            return self._parse_measurements(text, logger)

        except Exception as e:
            if logger:
                logger.error(f"Exception in extract_measurements for {label}: {e}", exc_info=e)
            return None

    def _parse_measurements(self, text: str, logger=None) -> Optional[Measurement]:
        """Parse measurements from OCR text"""

        # Detect side (RT/LT)
        side = ""
        if re.search(r"RT|Right|Droite", text, re.IGNORECASE):
            side = "RT"
        elif re.search(r"LT|Left|Gauche", text, re.IGNORECASE):
            side = "LT"

        # Detect nodule number
        nodule_match = re.search(r"N(\d+)", text, re.IGNORECASE)
        nodule = nodule_match.group(1) if nodule_match else ""

        # Detect isthmus
        is_isthmus = bool(re.search(r"Isthme|Isthmus", text, re.IGNORECASE))

        # Extract measurements in cm (format: "XX.X cm" or "XX,X cm")
        measurements_mm = []
        for match in re.finditer(r"(\d+[.,]\d+)\s*cm", text, re.IGNORECASE):
            value_str = match.group(1).replace(',', '.')
            try:
                value_cm = float(value_str)
                value_mm = round(value_cm * 10, 1)
                measurements_mm.append(str(value_mm))
            except ValueError:
                continue

        if not measurements_mm:
            if logger:
                logger.debug(f"No measurements extracted from text")
            return None

        # Format measurement text
        measurement_text = " x ".join(measurements_mm) + " mm"

        # Check for volume
        volume_match = re.search(r"Vol.*?(\d+[.,]\d+)", text, re.IGNORECASE)
        if volume_match:
            volume = volume_match.group(1).replace(',', '.')
            measurement_text += f" (volume {volume} ml)"

        if logger:
            logger.debug(f"Extracted measurement: Side={side}, Nodule={nodule}, "
                        f"Isthmus={is_isthmus}, Measurement={measurement_text}")

        return Measurement(
            side=side,
            nodule=nodule,
            is_isthmus=is_isthmus,
            text=measurement_text
        )


    def extract_context(self, image_input: Union[str, Image.Image], logger=None, image_path: str = "") -> Optional[OCRContext]:
        """
        Extract legend context AND measurement values from image for hybrid matching.

        Unlike extract_measurements() which formats text for display,
        this returns structured data (side, nodule, dimensions as floats)
        for matching with SR measurement sets.

        Args:
            image_input: File path (str) or PIL Image object (raw DICOM pixels = best quality)
            logger: Optional logger
            image_path: Used to label the OCRContext when image_input is a PIL Image

        Returns:
            OCRContext with structured data, or None if OCR completely fails
        """
        # Determine if input is a file path or PIL Image
        if isinstance(image_input, str):
            if not Path(image_input).exists():
                if logger:
                    logger.warning(f"Image file not found: {image_input}")
                return None
            image_path = image_path or image_input
            ocr_source = image_input
        else:
            ocr_source = image_input  # PIL Image passed directly

        try:
            config = f'--psm {self.psm} -l {self.language}'
            text = pytesseract.image_to_string(ocr_source, config=config)

            if not text or not text.strip():
                if logger:
                    logger.debug(f"No text extracted from: {image_path}")
                return None

            if logger:
                preview = text[:min(150, len(text))].replace('\n', ' ')
                logger.debug(f"OCR context text: {preview}")

            # Legend is in the first few lines of the image (top-left annotation)
            # Only search there to avoid false matches with measurement numbers
            all_lines = [l.strip() for l in text.split('\n') if l.strip()]
            legend_lines = all_lines[:5]  # First 5 lines contain the legend
            legend_text = " ".join(legend_lines)

            # Extract legend: side
            side = ""
            if re.search(r"\bRT\b|Right|Droite", legend_text, re.IGNORECASE):
                side = "RT"
            elif re.search(r"\bLT\b|Left|Gauche", legend_text, re.IGNORECASE):
                side = "LT"

            # Extract legend: nodule number (N1, N2...)
            # Use single digit first to avoid OCR noise (e.g., "N14" from "N1" + stray "4")
            # Also handle OCR misreads: "Ni" or "Nl" instead of "N1"
            # GE format: N1D (nodule 1 droit), N1G (nodule 1 gauche)
            nodule = ""
            nodule_match = re.search(r"\bN(\d)[DG]?\b", legend_text, re.IGNORECASE)
            if not nodule_match:
                # Fallback: OCR often reads "1" as "i" or "l"
                nodule_match = re.search(r"\bN([il])[DG]?\b", legend_text)
                if nodule_match:
                    nodule_match = None  # reset to use manual assignment
                    nodule = "1"
            if not nodule_match and not nodule:
                # Fallback for N10-N20 (rare, double digit)
                nodule_match = re.search(r"\bN(1\d|20)[DG]?\b", legend_text, re.IGNORECASE)
            if nodule_match:
                nodule = nodule_match.group(1)

            # Extract legend: isthmus
            is_isthmus = bool(re.search(r"Isthme|Isthmus", legend_text, re.IGNORECASE))

            # Extract dimension values in cm (keep as float for matching)
            dimensions_cm = []
            for match in re.finditer(r"(\d+[.,]\d+)\s*cm", text, re.IGNORECASE):
                value_str = match.group(1).replace(',', '.')
                try:
                    dimensions_cm.append(float(value_str))
                except ValueError:
                    continue

            # Extract volume in ml
            volume_ml = 0.0
            volume_match = re.search(r"Vol.*?(\d+[.,]\d+)\s*(?:ml|cc)", text, re.IGNORECASE)
            if volume_match:
                try:
                    volume_ml = float(volume_match.group(1).replace(',', '.'))
                except ValueError:
                    pass

            has_measurements = len(dimensions_cm) > 0 or volume_ml > 0

            if logger:
                logger.debug(f"OCR context: side={side}, nodule={nodule}, isthmus={is_isthmus}, "
                           f"dims_cm={dimensions_cm}, vol={volume_ml}, has_meas={has_measurements}")

            return OCRContext(
                image_path=image_path,
                side=side,
                nodule=nodule,
                is_isthmus=is_isthmus,
                legend_text=legend_text,
                dimensions_cm=dimensions_cm,
                volume_ml=volume_ml,
                has_measurements=has_measurements
            )

        except Exception as e:
            if logger:
                logger.error(f"Exception in extract_context for {image_path}: {e}", exc_info=e)
            return None


def test_tesseract(tesseract_path: str) -> bool:
    """Test if Tesseract is properly installed and working"""
    try:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        version = pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False
