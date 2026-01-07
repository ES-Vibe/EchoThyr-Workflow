"""
Serveur DICOM Storage SCP (PACS local)
Reçoit et archive les images DICOM depuis l'échographe
"""

from pynetdicom import AE, evt, AllStoragePresentationContexts
from pynetdicom.sop_class import Verification
from pydicom import dcmread
from pydicom.uid import ExplicitVRLittleEndian, ImplicitVRLittleEndian
from pathlib import Path
from datetime import datetime
import logging
import os


class StorageServer:
    """Serveur DICOM Storage pour archivage local"""

    def __init__(
        self,
        ae_title: str = "PACS_LOCAL",
        port: int = 4243,
        storage_path: str = "./DICOM_Archive",
        folder_structure: str = "{patient_name}_{patient_id}/{study_date}",
        export_images: bool = True,
        image_format: str = "png"
    ):
        self.ae_title = ae_title
        self.port = port
        self.storage_path = Path(storage_path)
        self.folder_structure = folder_structure
        self.export_images = export_images
        self.image_format = image_format
        self.ae = None
        self.logger = logging.getLogger('StorageServer')

        # Statistiques
        self.stats = {
            'received': 0,
            'stored': 0,
            'errors': 0
        }

        # Créer le dossier de stockage
        self.storage_path.mkdir(parents=True, exist_ok=True)

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

    def _handle_assoc_released(self, event):
        """Log association terminée"""
        self.logger.info(f"Association released - Stats: {self.stats['stored']} stored, {self.stats['errors']} errors")

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
        self.logger.info(f"Waiting for incoming images...")

        # Démarrer le serveur
        self.ae.start_server(('0.0.0.0', self.port), evt_handlers=handlers)

    def stop(self):
        """Arrête le serveur"""
        if self.ae:
            self.ae.shutdown()
            self.logger.info(f"Server stopped - Total: {self.stats['stored']} images stored")


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

    server = StorageServer(
        ae_title="PACS_LOCAL",
        port=4243,
        storage_path="./DICOM_Archive"
    )

    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
