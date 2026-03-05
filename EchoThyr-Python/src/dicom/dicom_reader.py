"""
DICOM file reader and processor for extracting patient data and converting images to JPEG
"""

import pydicom
from PIL import Image
import numpy as np
from pathlib import Path
from typing import Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PatientData:
    """Patient information extracted from DICOM metadata"""
    last_name: str = ""
    first_name: str = ""
    birth_date: str = ""  # Format: DD.MM.YYYY
    exam_date: str = ""   # Format: DD.MM.YYYY
    patient_id: str = ""
    modality: str = ""


class DicomReader:
    """Read DICOM files and extract patient data and images"""

    def __init__(self, jpeg_quality: int = 85, jpeg_max_width: int = 1200):
        """
        Initialize DICOM reader

        Args:
            jpeg_quality: JPEG compression quality (1-100)
            jpeg_max_width: Maximum width for output JPEG images
        """
        self.jpeg_quality = jpeg_quality
        self.jpeg_max_width = jpeg_max_width

    def read_dicom(self, dicom_path: str, logger=None) -> Optional[pydicom.Dataset]:
        """
        Read a DICOM file

        Args:
            dicom_path: Path to DICOM file
            logger: Optional logger

        Returns:
            pydicom Dataset or None if failed
        """
        try:
            # Use force=True for files without standard DICOM header
            dcm = pydicom.dcmread(dicom_path, force=True)
            if logger:
                logger.debug(f"DICOM file read successfully: {dicom_path}")
            return dcm
        except Exception as e:
            if logger:
                logger.warning(f"Failed to read DICOM file {dicom_path}: {e}")
            return None

    def extract_patient_data(self, dcm: pydicom.Dataset, logger=None) -> PatientData:
        """
        Extract patient information from DICOM metadata

        Args:
            dcm: pydicom Dataset
            logger: Optional logger

        Returns:
            PatientData object with extracted information
        """
        data = PatientData()

        # Extract patient name (format: LASTNAME^Firstname)
        if hasattr(dcm, 'PatientName') and dcm.PatientName:
            name_parts = str(dcm.PatientName).split('^')
            data.last_name = name_parts[0].upper() if len(name_parts) > 0 else ""
            data.first_name = name_parts[1].capitalize() if len(name_parts) > 1 else ""

        # Extract patient ID
        if hasattr(dcm, 'PatientID'):
            data.patient_id = str(dcm.PatientID)

        # Extract birth date (format: YYYYMMDD -> DD.MM.YYYY)
        if hasattr(dcm, 'PatientBirthDate') and dcm.PatientBirthDate:
            data.birth_date = self._format_dicom_date(str(dcm.PatientBirthDate))

        # Extract study/exam date (format: YYYYMMDD -> DD.MM.YYYY)
        if hasattr(dcm, 'StudyDate') and dcm.StudyDate:
            data.exam_date = self._format_dicom_date(str(dcm.StudyDate))

        # Extract modality
        if hasattr(dcm, 'Modality'):
            data.modality = str(dcm.Modality)

        if logger:
            logger.debug(f"Patient data extracted: {data.last_name} {data.first_name}, "
                        f"born {data.birth_date}, exam {data.exam_date}")

        return data

    def _format_dicom_date(self, dicom_date: str) -> str:
        """
        Convert DICOM date format (YYYYMMDD) to display format (DD.MM.YYYY)

        Args:
            dicom_date: Date string in YYYYMMDD format

        Returns:
            Date string in DD.MM.YYYY format
        """
        if len(dicom_date) != 8:
            return dicom_date

        try:
            year = dicom_date[0:4]
            month = dicom_date[4:6]
            day = dicom_date[6:8]
            return f"{day}.{month}.{year}"
        except:
            return dicom_date

    def convert_to_jpeg(self, dcm: pydicom.Dataset, output_path: str, logger=None) -> Optional[str]:
        """
        Convert DICOM image to compressed JPEG

        Args:
            dcm: pydicom Dataset containing pixel data
            output_path: Path for output JPEG file
            logger: Optional logger

        Returns:
            Path to created JPEG file or None if failed
        """
        try:
            # Check if pixel data exists
            if not hasattr(dcm, 'pixel_array'):
                if logger:
                    logger.warning("DICOM file does not contain pixel data")
                return None

            # Get pixel array
            pixel_array = dcm.pixel_array

            # Handle different photometric interpretations
            photometric = getattr(dcm, 'PhotometricInterpretation', 'UNKNOWN')

            if photometric == 'MONOCHROME1':
                # Invert for proper display (white = low values)
                pixel_array = np.max(pixel_array) - pixel_array

            # Normalize to 8-bit if needed
            if pixel_array.dtype != np.uint8:
                # Scale to 0-255 range
                pixel_min = pixel_array.min()
                pixel_max = pixel_array.max()
                if pixel_max > pixel_min:
                    pixel_array = ((pixel_array - pixel_min) / (pixel_max - pixel_min) * 255).astype(np.uint8)
                else:
                    pixel_array = np.zeros_like(pixel_array, dtype=np.uint8)

            # Handle RGB vs grayscale
            if len(pixel_array.shape) == 2:
                # Grayscale - convert to RGB for JPEG
                image = Image.fromarray(pixel_array, mode='L').convert('RGB')
            elif len(pixel_array.shape) == 3:
                # Already RGB or has multiple frames
                if pixel_array.shape[2] == 3:
                    image = Image.fromarray(pixel_array, mode='RGB')
                else:
                    # Multiple frames - take first frame
                    image = Image.fromarray(pixel_array[:, :, 0], mode='L').convert('RGB')
            else:
                if logger:
                    logger.warning(f"Unsupported pixel array shape: {pixel_array.shape}")
                return None

            # Resize if needed
            if image.width > self.jpeg_max_width:
                ratio = self.jpeg_max_width / image.width
                new_height = int(image.height * ratio)
                image = image.resize((self.jpeg_max_width, new_height), Image.Resampling.LANCZOS)
                if logger:
                    logger.debug(f"Image resized to {self.jpeg_max_width}x{new_height}")

            # Save as JPEG
            image.save(output_path, 'JPEG', quality=self.jpeg_quality, optimize=True)

            if logger:
                # Get file size
                file_size = Path(output_path).stat().st_size / 1024
                logger.debug(f"JPEG created: {output_path} ({file_size:.1f} KB)")

            return output_path

        except Exception as e:
            if logger:
                logger.error(f"Failed to convert DICOM to JPEG: {e}", exc_info=e)
            return None

    def extract_pil_image(self, dcm: pydicom.Dataset, logger=None) -> Optional[Image.Image]:
        """
        Extract raw PIL Image from DICOM pixel data (no compression, full resolution).
        Ideal for OCR since there are no JPEG artifacts or resizing.

        Args:
            dcm: pydicom Dataset containing pixel data
            logger: Optional logger

        Returns:
            PIL Image object or None if no pixel data
        """
        try:
            if not hasattr(dcm, 'pixel_array'):
                return None

            pixel_array = dcm.pixel_array

            # Handle photometric interpretation
            photometric = getattr(dcm, 'PhotometricInterpretation', 'UNKNOWN')
            if photometric == 'MONOCHROME1':
                pixel_array = np.max(pixel_array) - pixel_array

            # Normalize to 8-bit
            if pixel_array.dtype != np.uint8:
                pixel_min = pixel_array.min()
                pixel_max = pixel_array.max()
                if pixel_max > pixel_min:
                    pixel_array = ((pixel_array - pixel_min) / (pixel_max - pixel_min) * 255).astype(np.uint8)
                else:
                    pixel_array = np.zeros_like(pixel_array, dtype=np.uint8)

            # Build PIL Image
            if len(pixel_array.shape) == 2:
                return Image.fromarray(pixel_array, mode='L').convert('RGB')
            elif len(pixel_array.shape) == 3:
                if pixel_array.shape[2] == 3:
                    return Image.fromarray(pixel_array, mode='RGB')
                else:
                    return Image.fromarray(pixel_array[:, :, 0], mode='L').convert('RGB')
            return None

        except Exception as e:
            if logger:
                logger.error(f"Failed to extract PIL image from DICOM: {e}")
            return None

    def process_dicom_file(self, dicom_path: str, logger=None) -> Tuple[Optional[PatientData], Optional[str]]:
        """
        Process a single DICOM file: extract patient data and convert to JPEG

        Args:
            dicom_path: Path to DICOM file
            logger: Optional logger

        Returns:
            Tuple of (PatientData, jpeg_path) or (None, None) if failed
        """
        # Read DICOM
        dcm = self.read_dicom(dicom_path, logger)
        if dcm is None:
            return None, None

        # Extract patient data
        patient_data = self.extract_patient_data(dcm, logger)

        # Generate JPEG output path (same folder, with $ prefix)
        dicom_file = Path(dicom_path)
        jpeg_path = str(dicom_file.parent / f"${dicom_file.stem}.jpg")

        # Convert to JPEG
        jpeg_result = self.convert_to_jpeg(dcm, jpeg_path, logger)

        return patient_data, jpeg_result

    def find_dicom_files(self, folder_path: str, logger=None) -> List[str]:
        """
        Find all DICOM files in a folder (recursively)

        Args:
            folder_path: Path to search
            logger: Optional logger

        Returns:
            List of DICOM file paths
        """
        dicom_files = []
        folder = Path(folder_path)

        # Search for .dcm files
        for dcm_file in folder.rglob("*.dcm"):
            dicom_files.append(str(dcm_file))

        # Also search for files without extension (common in DICOM)
        # But only in specific DICOM folders
        for potential_dcm in folder.rglob("*"):
            if potential_dcm.is_file() and not potential_dcm.suffix:
                # Check if it looks like a DICOM file (starts with specific bytes)
                try:
                    with open(potential_dcm, 'rb') as f:
                        # Skip preamble and check for DICM magic
                        f.seek(128)
                        magic = f.read(4)
                        if magic == b'DICM':
                            dicom_files.append(str(potential_dcm))
                except:
                    pass

        if logger:
            logger.debug(f"Found {len(dicom_files)} DICOM files in {folder_path}")

        return sorted(dicom_files)
