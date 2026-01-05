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
from src.document.word_generator import WordGenerator
from src.document.pdf_exporter import PDFExporter
from src.monitor.folder_watcher import FolderWatcher, PatientFolder

VERSION = "2.0.0"


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
        self.watcher = FolderWatcher(
            self.config.source_dir,
            self.config.check_interval
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
        """Process a single patient folder"""
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
