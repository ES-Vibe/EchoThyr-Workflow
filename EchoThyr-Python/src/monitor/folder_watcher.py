"""
Folder monitoring module for detecting new patient folders
Supports both legacy JPG folders and DICOM Archive structure
"""

import time
from pathlib import Path
from typing import List, Set, Callable, Optional
from dataclasses import dataclass


@dataclass
class PatientFolder:
    """Represents a patient folder to process"""
    path: Path
    name: str
    dicom_files: List[str] = None  # List of DICOM file paths (if DICOM mode)

    def __post_init__(self):
        if self.dicom_files is None:
            self.dicom_files = []


class FolderWatcher:
    """Monitor source directory for new patient folders"""

    def __init__(self, source_dir: str, check_interval: int = 10, dicom_mode: bool = False):
        """
        Initialize folder watcher

        Args:
            source_dir: Directory to monitor
            check_interval: Seconds between checks
            dicom_mode: If True, watch for DICOM files in DICOM_Archive structure
        """
        self.source_dir = Path(source_dir)
        self.check_interval = check_interval
        self.dicom_mode = dicom_mode
        self.processed_folders: Set[str] = set()
        # Track processed study folders (patient/date/series) to detect new studies
        self.processed_studies: Set[str] = set()

    def initialize(self, logger=None) -> bool:
        """Initialize watcher - scan existing folders to avoid reprocessing"""
        if not self.source_dir.exists():
            if logger:
                logger.error(f"Source directory does not exist: {self.source_dir}")
            return False

        try:
            if self.dicom_mode:
                # DICOM mode: track date folders (parent of US_X/SR_X)
                for dcm_file in self.source_dir.rglob("*.dcm"):
                    date_folder = str(dcm_file.parent.parent)
                    self.processed_studies.add(date_folder)
                if logger:
                    logger.info(f"Initialized DICOM watcher with {len(self.processed_studies)} existing studies")
            else:
                # Legacy mode: track all folders
                for folder in self.source_dir.rglob("*"):
                    if folder.is_dir():
                        self.processed_folders.add(str(folder))
                if logger:
                    logger.info(f"Initialized watcher with {len(self.processed_folders)} existing folders")

            return True

        except Exception as e:
            if logger:
                logger.error(f"Failed to initialize watcher: {e}", exc_info=e)
            return False

    def get_new_folders(self, logger=None) -> List[PatientFolder]:
        """Get list of new patient folders"""
        if self.dicom_mode:
            return self._get_new_dicom_studies(logger)
        else:
            return self._get_new_legacy_folders(logger)

    def _get_new_legacy_folders(self, logger=None) -> List[PatientFolder]:
        """Legacy mode: get new folders (original behavior)"""
        new_folders = []

        try:
            for folder in self.source_dir.rglob("*"):
                if folder.is_dir():
                    folder_str = str(folder)
                    if folder_str not in self.processed_folders:
                        new_folders.append(PatientFolder(
                            path=folder,
                            name=folder.name
                        ))
                        self.processed_folders.add(folder_str)

        except Exception as e:
            if logger:
                logger.error(f"Error scanning folders: {e}", exc_info=e)

        return new_folders

    def _get_new_dicom_studies(self, logger=None) -> List[PatientFolder]:
        """DICOM mode: get new study folders containing .dcm files

        Groups all .dcm files by date folder (parent of US_X/SR_X) to generate
        a single report per patient/date instead of one per series folder.
        """
        new_studies = []

        try:
            # Find all folders containing .dcm files, grouped by date folder
            date_folders = {}

            for dcm_file in self.source_dir.rglob("*.dcm"):
                series_folder = dcm_file.parent  # e.g. .../PATIENT/DATE/US_1
                date_folder = series_folder.parent  # e.g. .../PATIENT/DATE
                date_str = str(date_folder)

                # Skip if this date folder was already processed
                if date_str in self.processed_studies:
                    continue

                if date_str not in date_folders:
                    date_folders[date_str] = []
                date_folders[date_str].append(str(dcm_file))

            # Create PatientFolder for each new date folder
            for date_str, dicom_files in date_folders.items():
                date_path = Path(date_str)

                # Get patient folder name (first level after source_dir)
                patient_name = self._extract_patient_name_from_path(date_path)

                new_studies.append(PatientFolder(
                    path=date_path,
                    name=patient_name,
                    dicom_files=sorted(dicom_files)
                ))

                # Mark as processed
                self.processed_studies.add(date_str)

                if logger:
                    logger.debug(f"New DICOM study detected: {patient_name} ({len(dicom_files)} files)")

        except Exception as e:
            if logger:
                logger.error(f"Error scanning DICOM folders: {e}", exc_info=e)

        return new_studies

    def _extract_patient_name_from_path(self, study_path: Path) -> str:
        """
        Extract patient name from DICOM Archive path structure

        Structure: DICOM_Archive/PATIENT_NAME_ID/DATE/US_X/
        Returns: PATIENT_NAME_ID (or folder name if structure differs)
        """
        try:
            # Go up from study folder to find patient folder
            # study_path = .../PATIENT/DATE/US_X
            parts = study_path.parts
            source_parts = self.source_dir.parts

            # Find the patient folder (first level after source_dir)
            if len(parts) > len(source_parts):
                patient_folder = parts[len(source_parts)]
                return patient_folder

        except Exception:
            pass

        return study_path.name

    def watch(self, callback: Callable[[PatientFolder], None], logger=None):
        """
        Continuously watch for new folders and call callback for each

        Args:
            callback: Function to call for each new folder
            logger: Optional logger
        """
        if logger:
            logger.info(f"Starting folder watch on: {self.source_dir}")

        while True:
            try:
                if logger:
                    logger.debug(f"Checking for new folders at: {self.source_dir}")

                new_folders = self.get_new_folders(logger)

                if new_folders and logger:
                    logger.info(f"Found {len(new_folders)} new folder(s) to process")

                for folder in new_folders:
                    if logger:
                        logger.info(f"Processing folder: {folder.name}")

                    try:
                        callback(folder)
                    except Exception as e:
                        if logger:
                            logger.error(f"Error processing folder {folder.name}: {e}", exc_info=e)

                # Sleep before next check
                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                if logger:
                    logger.info("Folder watcher stopped by user")
                break

            except Exception as e:
                if logger:
                    logger.error(f"Critical error in watch loop: {e}", exc_info=e)
                time.sleep(self.check_interval)  # Continue monitoring despite error
