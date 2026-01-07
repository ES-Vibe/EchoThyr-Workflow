"""
DICOM Storage Server (PACS local) - Point d'entrée principal
Archive automatiquement les images DICOM depuis l'échographe GE Logiq
"""

import sys
import os
import logging
import yaml
from pathlib import Path

# Ajouter le dossier courant au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from storage_server import StorageServer


# Configuration par défaut
DEFAULT_CONFIG = {
    'server': {
        'ae_title': 'PACS_LOCAL',
        'port': 4243
    },
    'storage': {
        'root_path': './DICOM_Archive',
        'folder_structure': '{patient_name}_{patient_id}/{study_date}',
        'keep_dicom': True,
        'export_images': True,
        'image_format': 'png'
    },
    'logging': {
        'level': 'INFO',
        'file': 'dicom_store.log'
    }
}


def setup_logging(config: dict):
    """Configure le logging"""
    log_level = getattr(logging, config.get('level', 'INFO'))
    log_file = config.get('file', 'dicom_store.log')

    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)-8s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    return logging.getLogger('DICOMStore')


def load_config(config_path: str = 'config.yaml') -> dict:
    """Charge la configuration depuis un fichier YAML"""
    config = DEFAULT_CONFIG.copy()

    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            user_config = yaml.safe_load(f)
            if user_config:
                for key, value in user_config.items():
                    if isinstance(value, dict) and key in config:
                        config[key].update(value)
                    else:
                        config[key] = value

    return config


def print_banner():
    """Affiche la bannière de démarrage"""
    print()
    print("=" * 60)
    print("   DICOM STORAGE SERVER (PACS LOCAL)")
    print("   Archivage automatique depuis echographe GE")
    print("=" * 60)
    print()


def main():
    """Point d'entrée principal"""
    print_banner()

    # Charger la configuration
    config = load_config()

    # Setup logging
    logger = setup_logging(config['logging'])
    logger.info("DICOM Storage Server starting...")

    # Configuration serveur
    server_config = config['server']
    storage_config = config['storage']

    ae_title = server_config.get('ae_title', 'PACS_LOCAL')
    port = server_config.get('port', 4243)
    storage_path = storage_config.get('root_path', './DICOM_Archive')
    folder_structure = storage_config.get('folder_structure', '{patient_name}_{patient_id}/{study_date}')
    export_images = storage_config.get('export_images', True)
    image_format = storage_config.get('image_format', 'png')

    # Afficher les infos de connexion
    print("=" * 60)
    print("  CONFIGURATION POUR ECHOGRAPHE GE LOGIQ")
    print("=" * 60)
    print()
    print(f"  AE Title (SCP):     {ae_title}")
    print(f"  Port:               {port}")
    print(f"  Stockage:           {storage_path}")
    print()
    print("  Sur l'echographe GE, configurez:")
    print("  - DICOM > Store > Add Server")
    print(f"  - AE Title: {ae_title}")
    print(f"  - IP: [IP de ce PC]")
    print(f"  - Port: {port}")
    print()
    print("=" * 60)
    print()
    print("  Serveur en cours d'execution... (Ctrl+C pour arreter)")
    print("  Les images recues seront stockees dans:")
    print(f"  {os.path.abspath(storage_path)}")
    print()

    # Créer et démarrer le serveur
    server = StorageServer(
        ae_title=ae_title,
        port=port,
        storage_path=storage_path,
        folder_structure=folder_structure,
        export_images=export_images,
        image_format=image_format
    )

    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Arret demande par l'utilisateur")
        server.stop()
    except Exception as e:
        logger.error(f"Erreur serveur: {e}")
        input("\nAppuyez sur Entree pour quitter...")


if __name__ == '__main__':
    main()
