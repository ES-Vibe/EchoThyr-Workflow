"""
Word document generation module using win32com (COM automation)
Generates medical reports from template with bookmarks
Compatible with PowerShell version bookmark system
"""

from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PatientInfo:
    """Patient information"""
    last_name: str = "A PRECISER"
    first_name: str = ""
    exam_date: str = ""


class WordGenerator:
    """Generate Word documents from template using COM automation"""

    def __init__(self, template_path: str):
        self.template_path = template_path

    def extract_patient_info(self, folder_name: str) -> PatientInfo:
        """Extract patient info from folder name (format: 'NOM Prenom')"""
        parts = folder_name.split()
        info = PatientInfo(exam_date=datetime.now().strftime("%d.%m.%Y"))

        if len(parts) >= 1:
            info.last_name = parts[0].upper()
        if len(parts) >= 2:
            info.first_name = parts[1].capitalize()

        return info

    def generate_report(
        self,
        patient_info: PatientInfo,
        measurements: List,
        image_paths: List[str],
        output_path: str,
        logger=None
    ) -> bool:
        """
        Generate medical report from template using Word COM automation

        Args:
            patient_info: Patient information
            measurements: List of Measurement objects
            image_paths: List of resized image paths
            output_path: Path for output DOCX file
            logger: Optional logger

        Returns:
            True if successful, False otherwise
        """
        word = None
        doc = None

        try:
            import win32com.client
            import pythoncom

            # Initialize COM
            pythoncom.CoInitialize()

            # Start Word application
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False

            # Open template
            doc = word.Documents.Open(self.template_path)

            # Helper function to set bookmark
            def set_bookmark(name: str, content: str):
                if doc.Bookmarks.Exists(name):
                    bookmark_range = doc.Bookmarks.Item(name).Range
                    bookmark_range.Text = content
                    doc.Bookmarks.Add(name, bookmark_range)
                    if logger:
                        logger.debug(f"Bookmark set: {name} = {content[:50]}...")
                else:
                    if logger:
                        logger.warning(f"Bookmark not found in template: {name}")

            # Set patient info bookmarks
            set_bookmark("NOM", patient_info.last_name)
            set_bookmark("PRENOM", patient_info.first_name)
            set_bookmark("DATE", patient_info.exam_date)

            # Generate measurement text
            measurement_text = self._format_measurements(measurements)
            set_bookmark("RESULTAT", measurement_text)

            # Add images at the end
            if image_paths:
                # Go to end of document
                doc.Characters.Last.Select()
                word.Selection.InsertBreak(7)  # Page break

                for img_path in image_paths:
                    try:
                        word.Selection.InlineShapes.AddPicture(img_path)
                        word.Selection.TypeText("\r\n")
                    except Exception as e:
                        if logger:
                            logger.warning(f"Failed to add image {img_path}: {e}")

            # Save document (16 = wdFormatDocumentDefault)
            doc.SaveAs2(output_path, 16)

            if logger:
                logger.success(f"Word document generated: {output_path}")

            return True

        except ImportError as e:
            if logger:
                logger.error(f"win32com not available: {e}")
            return False

        except Exception as e:
            if logger:
                logger.error(f"Failed to generate Word document: {e}", exc_info=e)
            return False

        finally:
            # Cleanup COM objects
            try:
                if doc:
                    doc.Close(False)
                if word:
                    word.Quit()
            except:
                pass

    def _format_measurements(self, measurements: List) -> str:
        """Format measurements into medical report text"""
        # Separate measurements by type
        right_lobe = next((m for m in measurements
                          if m.side == "RT" and not m.nodule and not m.is_isthmus), None)
        left_lobe = next((m for m in measurements
                         if m.side == "LT" and not m.nodule and not m.is_isthmus), None)
        isthmus = next((m for m in measurements if m.is_isthmus), None)
        nodules = [m for m in measurements if m.nodule]

        # Build report text (using \r\n for Word compatibility)
        text = "• Volume thyroïdien\r\n"
        text += f"- lobe droit : {right_lobe.text if right_lobe else 'non mesuré'}\r\n"
        text += f"- lobe gauche : {left_lobe.text if left_lobe else 'non mesuré'}\r\n"
        text += f"- isthme : {isthmus.text if isthmus else 'non mesuré'}\r\n"
        text += "• Echogénicité glandulaire homogène\r\n"
        text += "• Pas d'anomalie de la vascularisation\r\n"
        text += "• Nodules :\r\n"

        for nodule in nodules:
            location = "Lobe droit" if nodule.side == "RT" else "Lobe gauche"
            text += f"  - Nodule N{nodule.nodule} {location} : {nodule.text}\r\n"

        text += "• Etude des ganglions (secteurs II, III, IV, VI) et du tractus thyréoglosse : 0"

        return text
