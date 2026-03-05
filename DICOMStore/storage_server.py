"""
Serveur DICOM Storage SCP (PACS local)
Reçoit et archive les images DICOM depuis l'échographe
Avec génération automatique de CR quand US + SR sont disponibles
"""

from pynetdicom import AE, evt, AllStoragePresentationContexts
from pynetdicom.sop_class import Verification
from pydicom import dcmread
from pydicom.uid import ExplicitVRLittleEndian, ImplicitVRLittleEndian
from pathlib import Path
from datetime import datetime
import logging
import os
import sys

# Add EchoThyr-Python to path for auto CR generation
ECHOTHYR_PATH = Path(__file__).parent.parent / "EchoThyr-Python" / "src"
if ECHOTHYR_PATH.exists():
    sys.path.insert(0, str(ECHOTHYR_PATH))


class StorageServer:
    """Serveur DICOM Storage pour archivage local"""

    def __init__(
        self,
        ae_title: str = "PACS_LOCAL",
        port: int = 4243,
        storage_path: str = "./DICOM_Archive",
        folder_structure: str = "{patient_name}_{patient_id}/{study_date}",
        export_images: bool = True,
        image_format: str = "png",
        auto_generate_cr: bool = False,
        template_path: str = None
    ):
        self.ae_title = ae_title
        self.port = port
        self.storage_path = Path(storage_path)
        self.folder_structure = folder_structure
        self.export_images = export_images
        self.image_format = image_format
        self.ae = None
        self.logger = logging.getLogger('StorageServer')

        # Auto CR generation
        self.auto_generate_cr = auto_generate_cr
        self.template_path = template_path
        self.sr_parser = None
        self.word_generator = None
        self.dicom_reader = None

        # Track folders modified during current association
        self.current_association_folders = set()

        # Initialize CR generation components if enabled
        if self.auto_generate_cr:
            self._init_cr_components()

        # Statistiques
        self.stats = {
            'received': 0,
            'stored': 0,
            'errors': 0,
            'cr_generated': 0
        }

        # Créer le dossier de stockage
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def _init_cr_components(self):
        """Initialize components for CR generation"""
        try:
            from dicom.sr_parser import SRParser
            from dicom.dicom_reader import DicomReader
            from document.word_generator import WordGenerator, PatientInfo

            self.sr_parser = SRParser()
            self.dicom_reader = DicomReader(jpeg_quality=85, jpeg_max_width=1200)

            if self.template_path:
                self.word_generator = WordGenerator(self.template_path)
                self.logger.info("Auto CR generation enabled")
            else:
                self.logger.warning("Auto CR enabled but no template_path specified")
                self.auto_generate_cr = False

        except ImportError as e:
            self.logger.warning(f"Could not import EchoThyr components: {e}")
            self.logger.warning("Auto CR generation disabled")
            self.auto_generate_cr = False

    def _sanitize_filename(self, name: str) -> str:
        """Nettoie un nom pour l'utiliser comme nom de fichier"""
        # Remplacer les caractères problématiques
        invalid_chars = '<>:"/\\|?*^'
        for char in invalid_chars:
            name = name.replace(char, '_')
        # Remplacer les accents courants
        name = name.replace('^', '_')
        return name.strip()

    def _get_storage_path(self, ds) -> Path:
        """Génère le chemin de stockage basé sur les métadonnées DICOM"""
        # Extraire les informations du dataset
        patient_id = str(getattr(ds, 'PatientID', 'UNKNOWN'))
        patient_name = str(getattr(ds, 'PatientName', 'UNKNOWN'))
        study_date = str(getattr(ds, 'StudyDate', datetime.now().strftime('%Y%m%d')))
        modality = str(getattr(ds, 'Modality', 'OT'))
        series_number = str(getattr(ds, 'SeriesNumber', '1'))

        # Nettoyer les noms
        patient_name = self._sanitize_filename(patient_name)
        patient_id = self._sanitize_filename(patient_id)

        # Formater la date pour plus de lisibilité
        try:
            date_obj = datetime.strptime(study_date, '%Y%m%d')
            study_date_formatted = date_obj.strftime('%Y-%m-%d')
        except:
            study_date_formatted = study_date

        # Construire le chemin
        folder = self.folder_structure.format(
            patient_id=patient_id,
            patient_name=patient_name,
            study_date=study_date_formatted,
            modality=modality,
            series_number=series_number
        )

        return self.storage_path / folder

    def _handle_store(self, event):
        """Gère les requêtes C-STORE (réception d'images)"""
        self.stats['received'] += 1

        try:
            ds = event.dataset
            ds.file_meta = event.file_meta

            # Informations patient
            patient_name = str(getattr(ds, 'PatientName', 'UNKNOWN'))
            patient_id = str(getattr(ds, 'PatientID', 'UNKNOWN'))
            modality = str(getattr(ds, 'Modality', 'OT'))
            sop_instance = str(getattr(ds, 'SOPInstanceUID', 'unknown'))

            self.logger.info(f"Receiving: {patient_name} ({patient_id}) - {modality}")

            # Déterminer le chemin de stockage
            storage_dir = self._get_storage_path(ds)
            storage_dir.mkdir(parents=True, exist_ok=True)

            # Nom du fichier DICOM
            filename = f"{sop_instance}.dcm"
            filepath = storage_dir / filename

            # Sauvegarder le fichier DICOM
            ds.save_as(filepath)
            self.logger.info(f"  Saved: {filepath}")

            # Exporter en image si demandé
            if self.export_images and hasattr(ds, 'PixelData'):
                self._export_image(ds, storage_dir, sop_instance)

            # Track folder for auto CR generation
            if self.auto_generate_cr:
                # Get patient folder (grandparent of modality folder: patient/date/modality)
                patient_folder = storage_dir.parent.parent
                self.logger.debug(f"Tracking patient folder for CR: {patient_folder}")
                self.current_association_folders.add(str(patient_folder))

            self.stats['stored'] += 1
            return 0x0000  # Success

        except Exception as e:
            self.logger.error(f"Error storing: {e}")
            self.stats['errors'] += 1
            return 0xC000  # Error

    def _export_image(self, ds, storage_dir: Path, sop_instance: str):
        """Exporte l'image DICOM en format standard (PNG/JPEG)"""
        try:
            import numpy as np
            from PIL import Image

            # Extraire les données pixel
            pixel_array = ds.pixel_array

            # Normaliser pour l'affichage
            if pixel_array.dtype != np.uint8:
                # Normaliser en 8-bit
                pixel_min = pixel_array.min()
                pixel_max = pixel_array.max()
                if pixel_max > pixel_min:
                    pixel_array = ((pixel_array - pixel_min) / (pixel_max - pixel_min) * 255).astype(np.uint8)
                else:
                    pixel_array = np.zeros_like(pixel_array, dtype=np.uint8)

            # Créer l'image
            if len(pixel_array.shape) == 2:
                # Image en niveaux de gris
                img = Image.fromarray(pixel_array, mode='L')
            elif len(pixel_array.shape) == 3:
                # Image couleur
                img = Image.fromarray(pixel_array)
            else:
                return

            # Sauvegarder
            img_filename = f"{sop_instance}.{self.image_format}"
            img_path = storage_dir / img_filename
            img.save(img_path)
            self.logger.debug(f"  Exported: {img_path}")

        except ImportError:
            self.logger.warning("PIL/Pillow not installed - image export disabled")
        except Exception as e:
            self.logger.debug(f"  Could not export image: {e}")

    def _handle_echo(self, event):
        """Gère les requêtes C-ECHO"""
        requestor = event.assoc.requestor.ae_title
        self.logger.info(f"C-ECHO from {requestor}")
        return 0x0000

    def _handle_assoc_accepted(self, event):
        """Log association acceptée"""
        requestor = event.assoc.requestor
        self.logger.info(f"Association from: {requestor.ae_title} @ {requestor.address}")

        # Clear tracked folders for new association
        self.current_association_folders.clear()

    def _handle_assoc_released(self, event):
        """Log association terminée et génère CR si nécessaire"""
        self.logger.info(f"Association released - Stats: {self.stats['stored']} stored, {self.stats['errors']} errors")

        # Check for auto CR generation
        if self.auto_generate_cr and self.current_association_folders:
            self.logger.info(f"Checking {len(self.current_association_folders)} folder(s) for CR generation...")
            for patient_folder in self.current_association_folders:
                self._try_generate_cr(patient_folder)

            # Clear tracked folders
            self.current_association_folders.clear()

    def _try_generate_cr(self, patient_folder: str):
        """Check if patient folder has both US images and SR, and generate CR if so"""
        try:
            from document.word_generator import PatientInfo

            patient_path = Path(patient_folder)
            self.logger.info(f"Checking for CR generation in: {patient_path}")

            # Check for existing CR in patient folder and ALL subfolders FIRST
            existing_crs = list(patient_path.glob("**/CR ECHO THYR*.docx"))
            if existing_crs:
                self.logger.info(f"CR already exists: {existing_crs[0]} - skipping")
                return

            # Find all DICOM files in patient folder (recursively)
            dcm_files = list(patient_path.rglob("*.dcm"))

            if not dcm_files:
                self.logger.debug(f"No DICOM files found in {patient_folder}")
                return

            # Separate US images and SR files, grouped by study date
            us_files = []
            sr_files = []
            study_date = None

            for dcm_file in dcm_files:
                try:
                    dcm = dcmread(str(dcm_file), stop_before_pixels=True, force=True)
                    modality = str(getattr(dcm, 'Modality', ''))

                    if modality == 'SR':
                        sr_files.append(str(dcm_file))
                        if not study_date:
                            study_date = str(getattr(dcm, 'StudyDate', ''))
                    elif modality == 'US':
                        us_files.append(str(dcm_file))
                except Exception as e:
                    self.logger.debug(f"Could not read modality from {dcm_file}: {e}")

            self.logger.info(f"Found {len(us_files)} US files and {len(sr_files)} SR files")

            # Need both US and SR to generate CR
            if not us_files or not sr_files:
                self.logger.info(f"Incomplete study - US: {len(us_files)}, SR: {len(sr_files)} - skipping CR")
                return

            # Use the first SR file found
            sr_file = sr_files[0]
            self.logger.info(f"Using SR file: {sr_file}")

            # Parse SR for measurements
            sr_report = self.sr_parser.parse_sr(sr_file, self.logger)
            if not sr_report:
                self.logger.warning(f"Could not parse SR: {sr_file}")
                return

            # Get measurement text
            measurement_text = sr_report.get_formatted_text()

            # Extract patient info from SR
            name_parts = sr_report.patient_name.split('^')
            patient_info = PatientInfo(
                last_name=name_parts[0].upper() if name_parts else "INCONNU",
                first_name=name_parts[1].capitalize() if len(name_parts) > 1 else "",
                exam_date=sr_report.study_date,
                birth_date=sr_report.birth_date
            )

            self.logger.info(f"Generating CR for: {patient_info.last_name} {patient_info.first_name}")

            # Find images for embedding in report (JPG or PNG)
            image_files = []
            for us_file in us_files:
                us_path = Path(us_file)
                # Check for JPG first, then PNG
                jpg_path = us_path.parent / f"${us_path.stem}.jpg"
                png_path = us_path.parent / f"{us_path.stem}.png"

                if jpg_path.exists():
                    image_files.append(str(jpg_path))
                elif png_path.exists():
                    image_files.append(str(png_path))
                else:
                    # Try to create image from DICOM
                    _, created_img = self.dicom_reader.process_dicom_file(us_file, self.logger)
                    if created_img:
                        image_files.append(created_img)

            self.logger.debug(f"Using {len(image_files)} images for CR")

            # Generate Word document in the PATIENT folder directly
            date_file = patient_info.exam_date.replace('.', '-')
            base_name = f"CR ECHO THYR {patient_info.last_name} {patient_info.first_name} {date_file}"
            word_path = patient_path / f"{base_name}.docx"

            success = self.word_generator.generate_report_with_text(
                patient_info,
                measurement_text,
                image_files,
                str(word_path),
                self.logger
            )

            if success:
                self.stats['cr_generated'] += 1
                self.logger.info(f"CR generated: {word_path}")
            else:
                self.logger.error(f"Failed to generate CR for {patient_info.last_name}")

        except Exception as e:
            self.logger.error(f"Error generating CR: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())

    def start(self):
        """Démarre le serveur DICOM Storage"""
        self.ae = AE(ae_title=self.ae_title)

        # Accepter toutes les classes de stockage
        for context in AllStoragePresentationContexts:
            self.ae.add_supported_context(context.abstract_syntax)

        # Support C-ECHO
        self.ae.add_supported_context(Verification)

        # Handlers
        handlers = [
            (evt.EVT_C_STORE, self._handle_store),
            (evt.EVT_C_ECHO, self._handle_echo),
            (evt.EVT_ACCEPTED, self._handle_assoc_accepted),
            (evt.EVT_RELEASED, self._handle_assoc_released),
        ]

        self.logger.info(f"Starting DICOM Storage Server")
        self.logger.info(f"  AE Title: {self.ae_title}")
        self.logger.info(f"  Port: {self.port}")
        self.logger.info(f"  Storage: {self.storage_path}")
        if self.auto_generate_cr:
            self.logger.info(f"  Auto CR: ENABLED (template: {self.template_path})")
        self.logger.info(f"Waiting for incoming images...")

        # Démarrer le serveur
        self.ae.start_server(('0.0.0.0', self.port), evt_handlers=handlers)

    def stop(self):
        """Arrête le serveur"""
        if self.ae:
            self.ae.shutdown()
            stats_msg = f"Server stopped - Total: {self.stats['stored']} images stored"
            if self.auto_generate_cr:
                stats_msg += f", {self.stats['cr_generated']} CR generated"
            self.logger.info(stats_msg)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

    # Template Word pour le CR
    template_path = r"C:\Users\Emeric\Desktop\Claude\EchoThyr-Python\Modele_Echo.docx"

    server = StorageServer(
        ae_title="PACS_LOCAL",
        port=4243,
        storage_path="./DICOM_Archive",
        folder_structure="{patient_name}_{patient_id}/{study_date}/{modality}_{series_number}",
        auto_generate_cr=True,
        template_path=template_path
    )

    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
