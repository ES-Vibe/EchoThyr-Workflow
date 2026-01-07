"""
Image processing module for resizing and preparing echography images
"""

from PIL import Image
from pathlib import Path
from typing import Optional


class ImageProcessor:
    """Process and resize echography images"""

    def __init__(self, target_width: int = 1200):
        self.target_width = target_width

    def resize_image(self, input_path: str, output_path: Optional[str] = None, logger=None) -> Optional[str]:
        """
        Resize image to target width while maintaining aspect ratio

        Args:
            input_path: Path to input image
            output_path: Path for output image (if None, generates automatically)
            logger: Optional logger

        Returns:
            Path to resized image or None if failed
        """
        try:
            input_file = Path(input_path)

            if not input_file.exists():
                if logger:
                    logger.warning(f"Image file not found: {input_path}")
                return None

            # Generate output path if not provided
            if output_path is None:
                output_path = str(input_file.parent / f"${input_file.stem}.jpg")

            if logger:
                logger.debug(f"Resizing image: {input_path} -> Width={self.target_width}")

            # Open and resize image
            with Image.open(input_path) as img:
                # Calculate new dimensions
                ratio = self.target_width / img.width
                new_height = int(img.height * ratio)

                # Resize with high-quality resampling
                resized = img.resize((self.target_width, new_height), Image.Resampling.LANCZOS)

                # Save as JPEG
                resized.convert('RGB').save(output_path, 'JPEG', quality=95)

            if logger:
                logger.debug(f"Image resized successfully: {output_path}")

            return output_path

        except Exception as e:
            if logger:
                logger.warning(f"Failed to resize image {input_path}: {e}")
            return None

    def batch_resize(self, image_paths: list, logger=None) -> list:
        """
        Resize multiple images

        Args:
            image_paths: List of image file paths
            logger: Optional logger

        Returns:
            List of resized image paths (successful ones only)
        """
        resized_paths = []

        for img_path in image_paths:
            result = self.resize_image(img_path, logger=logger)
            if result:
                resized_paths.append(result)

        return resized_paths
