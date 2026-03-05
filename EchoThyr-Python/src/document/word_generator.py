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
    birth_date: str = ""  # Date de naissance (format DD.MM.YYYY)


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

            # Helper function to set bookmark or replace placeholder text
            def set_bookmark(name: str, content: str):
                if doc.Bookmarks.Exists(name):
                    bookmark_range = doc.Bookmarks.Item(name).Range
                    bookmark_range.Text = content
                    doc.Bookmarks.Add(name, bookmark_range)
                    if logger:
                        logger.debug(f"Bookmark set: {name} = {content[:50]}...")
                else:
                    # Fallback: replace placeholder text [NAME]
                    replace_placeholder(f"[{name}]", content)

            def replace_placeholder(placeholder: str, replacement: str):
                """Replace placeholder text in the document by scanning paragraphs."""
                found = False
                try:
                    for para in doc.Paragraphs:
                        para_range = para.Range
                        para_text = para_range.Text
                        if placeholder in para_text:
                            find_obj = para_range.Find
                            find_obj.ClearFormatting()
                            find_obj.Replacement.ClearFormatting()
                            result = find_obj.Execute(
                                FindText=placeholder,
                                ReplaceWith=replacement,
                                Replace=2,
                                Forward=True,
                                Wrap=0,
                                MatchCase=False
                            )
                            if result:
                                found = True
                    if not found:
                        for para in doc.Paragraphs:
                            para_text = para.Range.Text
                            if placeholder.lower() in para_text.lower():
                                import re
                                new_text = re.sub(re.escape(placeholder), replacement, para_text, flags=re.IGNORECASE)
                                if new_text != para_text:
                                    para.Range.Text = new_text
                                    found = True
                    if logger:
                        if found:
                            logger.debug(f"Placeholder replaced: {placeholder} -> {replacement[:50]}...")
                        else:
                            logger.warning(f"Placeholder not found in document: {placeholder}")
                except Exception as e:
                    if logger:
                        logger.warning(f"Error replacing placeholder {placeholder}: {e}")

            # Set patient info bookmarks
            set_bookmark("NOM", patient_info.last_name)
            set_bookmark("PRENOM", patient_info.first_name)
            set_bookmark("DATE", patient_info.exam_date)
            if patient_info.birth_date:
                set_bookmark("DATE_NAISSANCE", patient_info.birth_date)

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

    def generate_report_with_text(
        self,
        patient_info: PatientInfo,
        measurement_text: str,
        image_paths: List[str],
        output_path: str,
        logger=None,
        max_retries: int = 2
    ) -> bool:
        """
        Generate medical report with pre-formatted measurement text (from SR)

        Args:
            patient_info: Patient information
            measurement_text: Pre-formatted measurement text from SR
            image_paths: List of image paths to embed
            output_path: Path for output DOCX file
            logger: Optional logger
            max_retries: Number of retry attempts on failure

        Returns:
            True if successful, False otherwise
        """
        # Verify template exists first
        template_path = Path(self.template_path).resolve()
        if not template_path.exists():
            if logger:
                logger.error(f"Template file not found: {template_path}")
            return False

        last_error = None
        for attempt in range(max_retries + 1):
            if attempt > 0:
                if logger:
                    logger.info(f"Retry attempt {attempt}/{max_retries}...")
                # Wait a bit before retrying
                import time
                time.sleep(1)
                # Kill any hanging Word processes before retry
                self._kill_word_processes(logger)

            result = self._generate_report_internal(
                patient_info, measurement_text, image_paths,
                output_path, template_path, logger
            )
            if result:
                return True

        return False

    def _kill_word_processes(self, logger=None):
        """Kill any hanging Word processes"""
        try:
            import subprocess
            result = subprocess.run(
                ['taskkill', '/F', '/IM', 'WINWORD.EXE'],
                capture_output=True, text=True
            )
            if logger and 'SUCCESS' in result.stdout:
                logger.debug("Killed hanging Word process")
        except:
            pass

    def _replace_placeholders_docx(self, template_path: Path, output_path: str,
                                     patient_info: PatientInfo, measurement_text: str,
                                     logger=None) -> bool:
        """Replace placeholder text using python-docx (handles split runs reliably)"""
        try:
            from docx import Document

            doc = Document(str(template_path))

            replacements = {
                "[NOM]": patient_info.last_name,
                "[PRENOM]": patient_info.first_name,
                "[DATE]": patient_info.exam_date,
                "[RESULTAT]": measurement_text,
            }
            if patient_info.birth_date:
                replacements["[DATE_NAISSANCE]"] = patient_info.birth_date

            for paragraph in doc.paragraphs:
                full_text = paragraph.text
                for placeholder, value in replacements.items():
                    if placeholder in full_text:
                        # Rebuild runs: find which runs contain parts of the placeholder
                        self._replace_in_paragraph(paragraph, placeholder, value)
                        if logger:
                            logger.info(f"Replaced {placeholder} -> {value[:50]}")

            # Also check tables
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            full_text = paragraph.text
                            for placeholder, value in replacements.items():
                                if placeholder in full_text:
                                    self._replace_in_paragraph(paragraph, placeholder, value)
                                    if logger:
                                        logger.info(f"Replaced {placeholder} in table -> {value[:50]}")

            doc.save(output_path)
            return True

        except Exception as e:
            if logger:
                logger.error(f"python-docx replacement failed: {e}", exc_info=e)
            return False

    def _replace_in_paragraph(self, paragraph, placeholder: str, replacement: str):
        """Replace placeholder in a paragraph, handling split runs and multiline text"""
        from docx.oxml.ns import qn

        runs = paragraph.runs
        full_text = "".join(run.text for run in runs)

        if placeholder not in full_text:
            return

        start_idx = full_text.index(placeholder)
        end_idx = start_idx + len(placeholder)

        # Find the run containing the start of the placeholder
        char_count = 0
        for i, run in enumerate(runs):
            run_start = char_count
            run_end = char_count + len(run.text)

            if run_start <= start_idx < run_end:
                before = run.text[:start_idx - run_start]

                # Clear subsequent runs that are part of the placeholder
                if end_idx > run_end:
                    for j in range(i + 1, len(runs)):
                        next_start = sum(len(runs[k].text) for k in range(j))
                        next_end = next_start + len(runs[j].text)
                        if next_end <= end_idx:
                            runs[j].text = ""
                        else:
                            runs[j].text = runs[j].text[end_idx - next_start:]
                            break
                    after = ""
                else:
                    after = run.text[end_idx - run_start:]

                # Handle multiline replacement with soft line breaks
                lines = replacement.replace("\r\n", "\n").split("\n")
                if len(lines) <= 1:
                    # Simple single-line replacement
                    run.text = before + replacement + after
                else:
                    # Multiline: first line in current run, then add breaks + runs
                    run.text = before + lines[0]
                    # Add remaining lines with line breaks (soft return)
                    for line_idx, line in enumerate(lines[1:], 1):
                        # Add a break element after the current run
                        br = run._element.makeelement(qn('w:br'), {})
                        run._element.append(br)
                        # Add text after the break using a text element
                        if line_idx < len(lines) - 1:
                            # Not the last line: add text then prepare for next break
                            t = run._element.makeelement(qn('w:t'), {})
                            t.text = line
                            t.set(qn('xml:space'), 'preserve')
                            run._element.append(t)
                        else:
                            # Last line: add text + after
                            t = run._element.makeelement(qn('w:t'), {})
                            t.text = line + after
                            t.set(qn('xml:space'), 'preserve')
                            run._element.append(t)
                return

            char_count = run_end

    def _generate_report_internal(
        self,
        patient_info: PatientInfo,
        measurement_text: str,
        image_paths: List[str],
        output_path: str,
        template_path: Path,
        logger=None
    ) -> bool:
        """Internal method to generate the report using python-docx only (no COM)"""
        try:
            from docx import Document
            from docx.shared import Inches

            # Step 1: Replace placeholders
            doc = Document(str(template_path))

            replacements = {
                "[NOM]": patient_info.last_name,
                "[PRENOM]": patient_info.first_name,
                "[DATE]": patient_info.exam_date,
                "[RESULTAT]": measurement_text,
            }
            if patient_info.birth_date:
                replacements["[DATE_NAISSANCE]"] = patient_info.birth_date

            for paragraph in doc.paragraphs:
                for placeholder, value in replacements.items():
                    if placeholder in paragraph.text:
                        self._replace_in_paragraph(paragraph, placeholder, value)
                        if logger:
                            logger.info(f"Replaced {placeholder} -> {value[:50]}")

            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            for placeholder, value in replacements.items():
                                if placeholder in paragraph.text:
                                    self._replace_in_paragraph(paragraph, placeholder, value)

            # Step 2: Add images at the end
            if image_paths:
                doc.add_page_break()
                for img_path in image_paths:
                    try:
                        if Path(img_path).exists():
                            doc.add_picture(img_path, width=Inches(5.5))
                            doc.add_paragraph("")  # Spacing between images
                        else:
                            if logger:
                                logger.warning(f"Image not found: {img_path}")
                    except Exception as e:
                        if logger:
                            logger.warning(f"Failed to add image {img_path}: {e}")

            # Step 3: Save
            doc.save(output_path)

            if logger:
                logger.info(f"Word document generated: {output_path}")

            return True

        except Exception as e:
            if logger:
                logger.error(f"Failed to generate Word document: {e}", exc_info=e)
            return False

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
