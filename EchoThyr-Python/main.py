#!/usr/bin/env python3
"""
EchoThyr Automation - Main Entry Point
Medical report generation automation for thyroid echography
Version: 2.0.0 (Python)
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.utils.logger import get_logger
from src.utils.config import load_config
from src.utils.notifications import Notifier
from src.ocr.tesseract_engine import TesseractEngine, test_tesseract
from src.ocr.image_processor import ImageProcessor
from src.document.word_generator import WordGenerator, PatientInfo
from src.document.pdf_exporter import PDFExporter
from src.monitor.folder_watcher import FolderWatcher, PatientFolder
from src.dicom.dicom_reader import DicomReader
from src.dicom.sr_parser import SRParser

VERSION = "2.2.0"  # Added SR support (no OCR needed)


class EchoThyrApp:
    """Main application class"""

    def __init__(self, config_path: str = "config.yaml"):
        # Load configuration
        self.config = load_config(config_path)

        # Initialize logger
        self.logger = get_logger()

        # Initialize components
        self.notifier = Notifier(
            enable_beep=self.config.enable_beep,
            enable_banner=self.config.enable_banner
        )
        self.ocr_engine = TesseractEngine(
            self.config.tesseract_path,
            self.config.ocr_language,
            self.config.ocr_psm
        )
        self.image_processor = ImageProcessor(self.config.target_width)
        self.word_generator = WordGenerator(self.config.template_path)
        self.pdf_exporter = PDFExporter()

        # DICOM mode configuration
        self.dicom_mode = getattr(self.config, 'dicom_mode', False)
        if self.dicom_mode:
            dicom_source = getattr(self.config, 'dicom_source_dir', self.config.source_dir)
            self.dicom_reader = DicomReader(
                jpeg_quality=getattr(self.config, 'jpeg_quality', 85),
                jpeg_max_width=getattr(self.config, 'jpeg_max_width', 1200)
            )
            self.sr_parser = SRParser()  # Parser for Structured Reports
            self.watcher = FolderWatcher(
                dicom_source,
                self.config.check_interval,
                dicom_mode=True
            )
        else:
            self.dicom_reader = None
            self.sr_parser = None
            self.watcher = FolderWatcher(
                self.config.source_dir,
                self.config.check_interval,
                dicom_mode=False
            )

    def validate_prerequisites(self) -> bool:
        """Validate all prerequisites before starting"""
        self.logger.info("Starting prerequisite validation...")

        # Validate configuration paths
        if not self.config.validate():
            return False

        # Test Tesseract
        if not test_tesseract(self.config.tesseract_path):
            self.logger.error("Tesseract test failed")
            return False

        self.logger.success("All prerequisites validated successfully")
        return True

    def process_patient_folder(self, folder: PatientFolder):
        """Process a single patient folder (routes to DICOM or legacy mode)"""
        if self.dicom_mode:
            self._process_dicom_folder(folder)
        else:
            self._process_legacy_folder(folder)

    def _process_dicom_folder(self, folder: PatientFolder):
        """Process a DICOM study folder with 3-way detection:
        1. SR + thyroid tool → SR only (full context in SR)
        2. SR + generic Volume tool → Hybrid (SR values + OCR context)
        3. No SR → OCR only (fallback)
        """
        try:
            if not folder.dicom_files:
                self.logger.debug(f"No DICOM files in folder: {folder.path}")
                return

            self.logger.info(f"Processing DICOM study: {folder.name} ({len(folder.dicom_files)} files)")

            # --- Step 1: Analyze SR if present ---
            sr_files = self.sr_parser.find_sr_files(str(folder.path), self.logger)

            # Wait for SR if not yet received (echograph sends SR after images)
            if not sr_files:
                import time
                self.logger.info("No SR found yet - waiting 20s for echograph to send SR...")
                time.sleep(20)
                sr_files = self.sr_parser.find_sr_files(str(folder.path), self.logger)
                if sr_files:
                    self.logger.info(f"SR received after waiting: {len(sr_files)} file(s)")
                    # Re-scan all DICOM files to include the SR
                    folder.dicom_files = sorted(
                        str(f) for f in folder.path.rglob("*.dcm")
                    )
                else:
                    self.logger.info("No SR received after waiting - proceeding with OCR only")

            sr_report = None
            raw_sets = []
            needs_hybrid = False
            measurement_text = None

            if sr_files:
                sr_report, raw_sets, needs_hybrid = self.sr_parser.parse_sr_raw(
                    sr_files[0], self.logger
                )

                if sr_report and not needs_hybrid:
                    # Thyroid-specific tool: SR has full context
                    measurement_text = sr_report.get_formatted_text()
                    self.logger.info("Mode SR: outil thyroide specifique detecte")
                elif sr_report and needs_hybrid:
                    self.logger.info("Mode HYBRIDE: outil Volume generique detecte - OCR necessaire pour contexte")

            # --- Step 2: Extract patient info ---
            if sr_report:
                name_parts = sr_report.patient_name.split('^')
                patient_info = PatientInfo(
                    last_name=name_parts[0].upper() if name_parts else "",
                    first_name=name_parts[1].capitalize() if len(name_parts) > 1 else "",
                    exam_date=sr_report.study_date,
                    birth_date=sr_report.birth_date
                )
            else:
                # Fallback: get patient info from a DICOM image (skip SR files)
                patient_data = None
                for dcm_path in folder.dicom_files:
                    if not self.sr_parser.is_sr_file(dcm_path, self.logger):
                        patient_data, _ = self.dicom_reader.process_dicom_file(
                            dcm_path, self.logger
                        )
                        if patient_data:
                            break
                if not patient_data:
                    self.logger.warning(f"Could not extract patient data from DICOM")
                    return
                patient_info = PatientInfo(
                    last_name=patient_data.last_name,
                    first_name=patient_data.first_name,
                    exam_date=patient_data.exam_date,
                    birth_date=patient_data.birth_date
                )

            self.logger.info(f"Patient: {patient_info.last_name} {patient_info.first_name}, "
                           f"born {patient_info.birth_date}, exam {patient_info.exam_date}")

            # --- Step 3: Generate file names ---
            date_file = patient_info.exam_date.replace('.', '-')
            base_name = f"CR ECHO THYR {patient_info.last_name} {patient_info.first_name} {date_file}"
            word_path = folder.path / f"{base_name}.docx"
            pdf_path = folder.path / f"{base_name}.pdf"

            if word_path.exists():
                self.logger.debug(f"Report already exists for: {patient_info.last_name} {patient_info.first_name}")
                return

            # --- Step 4: Convert DICOM images to JPEG + extract raw PIL for OCR ---
            jpeg_images = []
            raw_pil_images = []  # Raw DICOM pixels (full res, no compression) for OCR
            for dcm_path in folder.dicom_files:
                if self.sr_parser.is_sr_file(dcm_path, self.logger):
                    continue
                self.logger.debug(f"Converting DICOM to JPEG: {Path(dcm_path).name}")
                dcm = self.dicom_reader.read_dicom(dcm_path, self.logger)
                if dcm is None:
                    continue

                # JPEG for Word document (compressed, resized)
                dicom_file = Path(dcm_path)
                jpeg_path = str(dicom_file.parent / f"${dicom_file.stem}.jpg")
                jpeg_result = self.dicom_reader.convert_to_jpeg(dcm, jpeg_path, self.logger)
                if jpeg_result:
                    jpeg_images.append(jpeg_result)

                # Raw PIL Image for OCR (full resolution, no compression)
                pil_img = self.dicom_reader.extract_pil_image(dcm, self.logger)
                if pil_img:
                    raw_pil_images.append((pil_img, dcm_path))

            if jpeg_images:
                self.logger.info(f"Converted {len(jpeg_images)} DICOM files to JPEG")
            if raw_pil_images:
                self.logger.info(f"Extracted {len(raw_pil_images)} raw PIL images for OCR (full resolution)")

            # --- Step 5: Process measurements (3 voies) ---
            measurements = []  # For OCR-only path
            source = "SR"

            if needs_hybrid and sr_report and raw_sets:
                # VOIE 2: Hybrid - SR values + OCR context
                source = "Hybrid"
                self.logger.info(f"Running OCR on {len(raw_pil_images)} raw DICOM images for context extraction...")

                from src.hybrid.matcher import HybridMatcher
                ocr_contexts = []
                for pil_img, dcm_path in raw_pil_images:
                    context = self.ocr_engine.extract_context(pil_img, self.logger, image_path=dcm_path)
                    if context:
                        ocr_contexts.append(context)

                self.logger.info(f"OCR context extracted from {len(ocr_contexts)} images")

                matcher = HybridMatcher()
                enriched_report = matcher.match(sr_report, raw_sets, ocr_contexts, self.logger)
                measurement_text = enriched_report.get_formatted_text()

            elif not measurement_text:
                # VOIE 3: OCR only (no SR)
                source = "OCR"
                self.logger.info("No SR found - falling back to full OCR")
                for pil_img, dcm_path in raw_pil_images:
                    measurement = self.ocr_engine.extract_measurements(pil_img, self.logger)
                    if measurement:
                        measurements.append(measurement)

                if not measurements:
                    self.logger.warning(f"No measurements extracted - skipping report")
                    return

                # Format OCR measurements as text for python-docx method
                measurement_text = self.word_generator._format_measurements(measurements)

            # --- Step 6: Generate Word document ---
            success = self.word_generator.generate_report_with_text(
                patient_info,
                measurement_text,
                jpeg_images,
                str(word_path),
                self.logger
            )

            if not success:
                self.notifier.error(
                    f"{patient_info.last_name} {patient_info.first_name}",
                    "Failed to generate Word document"
                )
                return

            # --- Step 7: Export to PDF ---
            if self.config.generate_pdf:
                self.logger.info(f"Exporting PDF: {pdf_path}")
                self.pdf_exporter.export_to_pdf(str(word_path), str(pdf_path), self.logger)

            # --- Step 8: Success notification ---
            patient_info_str = f"{patient_info.last_name} {patient_info.first_name} ({patient_info.exam_date}) [{source}]"
            self.notifier.success(base_name, patient_info_str)

        except Exception as e:
            self.logger.error(f"Unexpected error processing DICOM folder {folder.path}: {e}", exc_info=e)
            self.notifier.error(str(folder.path), str(e))

    def _process_legacy_folder(self, folder: PatientFolder):
        """Process a legacy JPG folder (original behavior)"""
        try:
            # Extract patient info from folder name
            patient_info = self.word_generator.extract_patient_info(folder.name)
            self.logger.debug(f"Patient info: {patient_info.last_name} {patient_info.first_name}")

            # Generate file names
            date_file = patient_info.exam_date.replace('.', '-')
            base_name = f"CR ECHO THYR {patient_info.last_name} {patient_info.first_name} {date_file}"
            word_path = folder.path / f"{base_name}.docx"
            pdf_path = folder.path / f"{base_name}.pdf"

            # Check if report already exists
            if word_path.exists():
                self.logger.debug(f"Report already exists for: {patient_info.last_name} {patient_info.first_name}")
                return

            # Get image files (JPG only, exclude processed ones with $ prefix)
            image_files = [
                f for f in folder.path.glob("*.jpg")
                if not f.name.startswith("$")
            ]

            if not image_files:
                self.logger.debug(f"No image files found in folder: {folder.path}")
                return

            self.logger.info(f"Found {len(image_files)} image file(s) for processing")

            # Process images and extract measurements
            measurements = []
            resized_images = []

            for img_file in image_files:
                self.logger.debug(f"Processing image: {img_file.name}")

                # Extract measurements
                measurement = self.ocr_engine.extract_measurements(str(img_file), self.logger)
                if measurement:
                    measurements.append(measurement)

                # Resize image
                resized_path = self.image_processor.resize_image(str(img_file), logger=self.logger)
                if resized_path:
                    resized_images.append(resized_path)

            # Check if we have measurements
            if not measurements:
                self.logger.warning(f"No measurements extracted - skipping report for: {patient_info.last_name} {patient_info.first_name}")
                return

            self.logger.info(f"Extracted {len(measurements)} measurement(s) - generating Word document")

            # Generate Word document
            success = self.word_generator.generate_report(
                patient_info,
                measurements,
                resized_images,
                str(word_path),
                self.logger
            )

            if not success:
                self.notifier.error(
                    f"{patient_info.last_name} {patient_info.first_name}",
                    "Failed to generate Word document"
                )
                return

            # Export to PDF
            if self.config.generate_pdf:
                self.logger.info(f"Exporting PDF: {pdf_path}")
                self.pdf_exporter.export_to_pdf(str(word_path), str(pdf_path), self.logger)

            # Success notification
            patient_info_str = f"{patient_info.last_name} {patient_info.first_name} ({patient_info.exam_date})"
            self.notifier.success(base_name, patient_info_str)

        except Exception as e:
            self.logger.error(f"Unexpected error processing folder {folder.path}: {e}", exc_info=e)
            self.notifier.error(str(folder.path), str(e))

    def run(self):
        """Main application loop"""
        # Show startup banner
        self.notifier.startup_banner(VERSION, self.config)

        # Log startup
        self.logger.info(f"EchoThyr Automation started - Version {VERSION}")
        self.logger.info(f"Configuration - Source: {self.config.source_dir}, Template: {self.config.template_path}")

        # Validate prerequisites
        if not self.validate_prerequisites():
            self.logger.error("Prerequisites validation failed. Exiting.")
            sys.exit(1)

        # Initialize watcher
        if not self.watcher.initialize(self.logger):
            self.logger.error("Failed to initialize folder watcher. Exiting.")
            sys.exit(1)

        # Start monitoring
        self.logger.info("Starting folder monitoring...")
        self.watcher.watch(self.process_patient_folder, self.logger)


def main():
    """Entry point"""
    try:
        app = EchoThyrApp()
        app.run()
    except KeyboardInterrupt:
        print("\n\nApplication stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
