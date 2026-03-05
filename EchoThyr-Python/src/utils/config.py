"""
Configuration module for EchoThyr automation
Loads settings from YAML file with defaults
"""

import yaml
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass, field


@dataclass
class Config:
    """Application configuration"""

    # DICOM Mode
    dicom_mode: bool = False  # true = DICOM mode, false = legacy JPG mode
    dicom_source_dir: str = ""  # DICOM Archive folder
    jpeg_quality: int = 85  # JPEG compression quality (1-100)
    jpeg_max_width: int = 1200  # Max width for converted JPEG

    # Paths (legacy mode)
    source_dir: str = "C:\\EchoThyr\\export"
    template_path: str = "C:\\EchoThyr\\Modele_Echo.docx"
    log_dir: str = "C:\\EchoThyr\\logs"
    tesseract_path: str = "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

    # Image processing
    target_width: int = 1200

    # Monitoring
    check_interval: int = 10  # seconds

    # OCR settings
    ocr_language: str = "eng"
    ocr_psm: int = 6  # Page segmentation mode

    # Document settings
    generate_pdf: bool = True
    embed_images: bool = True

    # Logging
    log_level: str = "INFO"
    console_colors: bool = True

    # Notifications
    enable_beep: bool = True
    enable_banner: bool = True

    # Advanced
    max_workers: int = 4
    encoding: str = "utf-8"

    @classmethod
    def from_yaml(cls, config_path: str) -> 'Config':
        """Load configuration from YAML file"""
        path = Path(config_path)

        if not path.exists():
            # Return default config if file doesn't exist
            return cls()

        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}

        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})

    def to_yaml(self, config_path: str):
        """Save configuration to YAML file"""
        path = Path(config_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            k: v for k, v in self.__dict__.items()
            if not k.startswith('_')
        }

        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    def validate(self) -> bool:
        """Validate configuration paths and settings"""
        from .logger import get_logger
        logger = get_logger()

        valid = True

        # Check source directory (depends on mode)
        if self.dicom_mode:
            if not self.dicom_source_dir or not Path(self.dicom_source_dir).exists():
                logger.error(f"DICOM source directory not found: {self.dicom_source_dir}")
                valid = False
        else:
            if not Path(self.source_dir).exists():
                logger.error(f"Source directory not found: {self.source_dir}")
                valid = False

        # Check template
        if not Path(self.template_path).exists():
            logger.error(f"Template file not found: {self.template_path}")
            valid = False

        # Check Tesseract
        if not Path(self.tesseract_path).exists():
            logger.error(f"Tesseract executable not found: {self.tesseract_path}")
            valid = False

        return valid


def load_config(config_path: str = "config.yaml") -> Config:
    """Load configuration from file or create default"""
    return Config.from_yaml(config_path)
