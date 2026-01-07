"""
Folder monitoring module for detecting new patient folders
"""

import time
from pathlib import Path
from typing import List, Set, Callable
from dataclasses import dataclass


@dataclass
class PatientFolder:
    """Represents a patient folder to process"""
    path: Path
    name: str


class FolderWatcher:
    """Monitor source directory for new patient folders"""

    def __init__(self, source_dir: str, check_interval: int = 10):
        self.source_dir = Path(source_dir)
        self.check_interval = check_interval
        self.processed_folders: Set[str] = set()

    def initialize(self, logger=None) -> bool:
        """Initialize watcher - scan existing folders to avoid reprocessing"""
        if not self.source_dir.exists():
            if logger:
                logger.error(f"Source directory does not exist: {self.source_dir}")
            return False

        # Get all existing folders
        try:
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
        new_folders = []

        try:
            # Recursively scan for directories
            for folder in self.source_dir.rglob("*"):
                if folder.is_dir():
                    folder_str = str(folder)

                    # Check if folder is new
                    if folder_str not in self.processed_folders:
                        new_folders.append(PatientFolder(
                            path=folder,
                            name=folder.name
                        ))
                        # Mark as processed (even before actual processing)
                        # to avoid duplicate processing attempts
                        self.processed_folders.add(folder_str)

        except Exception as e:
            if logger:
                logger.error(f"Error scanning folders: {e}", exc_info=e)

        return new_folders

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
