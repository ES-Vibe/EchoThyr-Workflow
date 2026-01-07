"""
PDF export module for converting DOCX to PDF
Uses docx2pdf for Windows, fallback to reportlab for cross-platform
"""

from pathlib import Path
from typing import Optional
import platform


class PDFExporter:
    """Export Word documents to PDF"""

    def __init__(self):
        self.is_windows = platform.system() == "Windows"

    def export_to_pdf(self, docx_path: str, pdf_path: Optional[str] = None, logger=None) -> bool:
        """
        Convert DOCX file to PDF

        Args:
            docx_path: Path to DOCX file
            pdf_path: Output PDF path (if None, replaces .docx with .pdf)
            logger: Optional logger

        Returns:
            True if successful, False otherwise
        """
        # Generate PDF path if not provided
        if pdf_path is None:
            pdf_path = str(Path(docx_path).with_suffix('.pdf'))

        try:
            if self.is_windows:
                return self._export_windows(docx_path, pdf_path, logger)
            else:
                return self._export_reportlab(docx_path, pdf_path, logger)

        except Exception as e:
            if logger:
                logger.error(f"Failed to export PDF: {e}", exc_info=e)
            return False

    def _export_windows(self, docx_path: str, pdf_path: str, logger=None) -> bool:
        """Export using docx2pdf (Windows only)"""
        try:
            from docx2pdf import convert
            convert(docx_path, pdf_path)

            if logger:
                logger.success(f"PDF exported: {pdf_path}")

            return True

        except ImportError:
            if logger:
                logger.warning("docx2pdf not available, trying COM automation...")
            return self._export_com(docx_path, pdf_path, logger)

    def _export_com(self, docx_path: str, pdf_path: str, logger=None) -> bool:
        """Export using Word COM automation (Windows only)"""
        try:
            import win32com.client

            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False

            doc = word.Documents.Open(str(Path(docx_path).absolute()))
            doc.SaveAs2(str(Path(pdf_path).absolute()), FileFormat=17)  # 17 = PDF format
            doc.Close()
            word.Quit()

            if logger:
                logger.success(f"PDF exported via COM: {pdf_path}")

            return True

        except Exception as e:
            if logger:
                logger.error(f"COM PDF export failed: {e}", exc_info=e)
            return False

    def _export_reportlab(self, docx_path: str, pdf_path: str, logger=None) -> bool:
        """Fallback export using reportlab (cross-platform, limited features)"""
        if logger:
            logger.warning("PDF export on non-Windows platform is limited")

        # This is a placeholder - full DOCX to PDF conversion
        # without Word/LibreOffice is complex and requires extensive parsing
        # For production use, consider using LibreOffice in headless mode

        if logger:
            logger.error("Cross-platform PDF export not fully implemented. "
                        "Please install LibreOffice and use: "
                        "soffice --headless --convert-to pdf document.docx")

        return False
