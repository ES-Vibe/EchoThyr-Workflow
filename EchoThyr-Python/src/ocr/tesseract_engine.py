"""
Tesseract OCR engine for extracting measurements from echography images
"""

import pytesseract
import re
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class Measurement:
    """Represents an extracted measurement"""
    side: str  # "RT" (right) or "LT" (left)
    nodule: str  # Nodule number (e.g., "1", "2") or empty
    is_isthmus: bool  # True if isthmus measurement
    text: str  # Formatted measurement text (e.g., "45.2 x 23.1 x 18.5 mm")


class TesseractEngine:
    """OCR engine using Tesseract"""

    def __init__(self, tesseract_path: str, language: str = "eng", psm: int = 6):
        self.tesseract_path = tesseract_path
        self.language = language
        self.psm = psm

        # Set Tesseract executable path
        pytesseract.pytesseract.tesseract_cmd = tesseract_path

    def extract_measurements(self, image_path: str, logger=None) -> Optional[Measurement]:
        """
        Extract measurements from an echography image

        Args:
            image_path: Path to the image file
            logger: Optional logger for debugging

        Returns:
            Measurement object or None if no measurements found
        """
        if logger:
            logger.debug(f"Processing image: {image_path}")

        # Validate image exists
        if not Path(image_path).exists():
            if logger:
                logger.warning(f"Image file not found: {image_path}")
            return None

        try:
            # Run Tesseract OCR
            config = f'--psm {self.psm} -l {self.language}'
            text = pytesseract.image_to_string(image_path, config=config)

            if not text or not text.strip():
                if logger:
                    logger.debug(f"Tesseract extracted no text from: {image_path}")
                return None

            if logger:
                # Log first 100 chars of extracted text
                preview = text[:min(100, len(text))].replace('\n', ' ')
                logger.debug(f"Tesseract extracted text: {preview}...")

            # Extract measurement data
            return self._parse_measurements(text, logger)

        except Exception as e:
            if logger:
                logger.error(f"Exception in extract_measurements for {image_path}: {e}", exc_info=e)
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


def test_tesseract(tesseract_path: str) -> bool:
    """Test if Tesseract is properly installed and working"""
    try:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        version = pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False
