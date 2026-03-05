"""
DICOM Worklist Server - Point d'entrée principal
Serveur Modality Worklist pour échographes GE Logiq

Lit les exports CSV Doctolib et fournit une liste de patients
accessible depuis l'échographe via le protocole DICOM.
"""

import sys
import os
import logging
import subprocess
import yaml
from pathlib import Path
from datetime import datetime

# Ajouter le dossier courant au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from doctolib_parser import DoctolibParser, filter_echo_patients, Patient
from worklist_server import WorklistServer


# Configuration par défaut
DEFAULT_CONFIG = {
    'server': {
        'ae_title': 'WORKLIST',
        'port': 4242
    },
    'csv': {
        'path': '',  # Sera demandé si vide
        'filter_echo_only': True
    },
    'logging': {
        'level': 'INFO',
        'file': 'worklist_server.log'
    }
}


def setup_logging(config: dict):
    """Configure le logging"""
    log_level = getattr(logging, config.get('level', 'INFO'))
    log_file = config.get('file', 'worklist_server.log')

    # Créer le formatter
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)-8s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Handler console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    # Handler fichier
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    # Configurer le logger racine
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    return logging.getLogger('DICOMWorklist')


def load_config(config_path: str = 'config.yaml') -> dict:
    """Charge la configuration depuis un fichier YAML"""
    config = DEFAULT_CONFIG.copy()

    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            user_config = yaml.safe_load(f)
            if user_config:
                # Merge configs
                for key, value in user_config.items():
                    if isinstance(value, dict) and key in config:
                        config[key].update(value)
                    else:
                        config[key] = value

    return config


def find_latest_csv(downloads_folder: str = None) -> str:
    """Trouve le dernier fichier CSV Doctolib dans les téléchargements"""
    if not downloads_folder:
        downloads_folder = os.path.expanduser('~/Downloads')

    csv_files = list(Path(downloads_folder).glob('export_rdv_*.csv'))

    if not csv_files:
        return None

    # Trier par date de modification (plus récent en premier)
    csv_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    return str(csv_files[0])


def print_banner():
    """Affiche la bannière de démarrage"""
    print()
    print("=" * 60)
    print("   DICOM WORKLIST SERVER - Doctolib > Echographe GE")
    print("=" * 60)
    print()


def print_patients_summary(patients: list, logger):
    """Affiche un résumé des patients"""
    if not patients:
        logger.warning("Aucun patient trouvé dans le fichier CSV")
        return

    logger.info(f"Patients chargés: {len(patients)}")
    print()
    print("-" * 50)
    print("  LISTE DES PATIENTS DU JOUR")
    print("-" * 50)

    for p in sorted(patients, key=lambda x: x.appointment_time):
        time_str = f"{p.appointment_time[:2]}:{p.appointment_time[2:4]}"
        print(f"  {time_str}  {p.last_name:15} {p.first_name:15}")

    print("-" * 50)
    print()


def kill_existing_on_port(port: int):
    """Tue toute instance existante écoutant sur ce port"""
    try:
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True, text=True, timeout=5
        )
        pids = set()
        for line in result.stdout.splitlines():
            if f':{port}' in line and 'LISTENING' in line:
                parts = line.split()
                if parts:
                    pids.add(parts[-1])
        my_pid = str(os.getpid())
        for pid in pids:
            if pid != my_pid and pid != '0':
                print(f"  Arrêt de l'ancienne instance (PID {pid}) sur le port {port}...")
                subprocess.run(['taskkill', '/PID', pid, '/F'],
                               capture_output=True, timeout=5)
    except Exception:
        pass


def main():
    """Point d'entrée principal"""
    print_banner()

    # Charger la configuration
    config = load_config()

    # Tuer toute ancienne instance sur le même port
    port = config['server'].get('port', 4242)
    kill_existing_on_port(port)

    # Setup logging
    logger = setup_logging(config['logging'])
    logger.info("DICOM Worklist Server starting...")

    # Trouver le fichier CSV
    csv_path = config['csv'].get('path', '')

    if not csv_path or not os.path.exists(csv_path):
        # Chercher le dernier CSV dans Downloads
        csv_path = find_latest_csv()

        if not csv_path:
            logger.error("Aucun fichier CSV Doctolib trouvé!")
            logger.info("Placez un export CSV Doctolib dans le dossier Téléchargements")
            logger.info("ou spécifiez le chemin dans config.yaml")
            input("\nAppuyez sur Entrée pour quitter...")
            return

    logger.info(f"Fichier CSV: {csv_path}")

    # Parser le CSV
    parser = DoctolibParser(csv_path)
    all_patients = parser.parse()

    # Filtrer si configuré
    if config['csv'].get('filter_echo_only', True):
        patients = filter_echo_patients(all_patients)
        logger.info(f"Filtrage: {len(patients)} patients écho/thyroïde sur {len(all_patients)} total")
    else:
        patients = all_patients

    # Afficher le résumé
    print_patients_summary(patients, logger)

    # Fonction provider pour le serveur
    def get_patients():
        return patients

    # Configuration serveur
    server_config = config['server']
    ae_title = server_config.get('ae_title', 'WORKLIST')
    port = server_config.get('port', 4242)

    # Afficher les infos de connexion
    print("=" * 60)
    print("  CONFIGURATION POUR ÉCHOGRAPHE GE LOGIQ")
    print("=" * 60)
    print()
    print(f"  AE Title (SCP):     {ae_title}")
    print(f"  Port:               {port}")
    print(f"  Adresse IP:         (utilisez l'IP de ce PC)")
    print()
    print("  Sur l'échographe GE, configurez:")
    print("  - Worklist > Configuration > Add Server")
    print(f"  - AE Title: {ae_title}")
    print(f"  - IP: [IP de ce PC]")
    print(f"  - Port: {port}")
    print()
    print("=" * 60)
    print()
    print("  Serveur en cours d'exécution... (Ctrl+C pour arrêter)")
    print()

    # Créer et démarrer le serveur
    server = WorklistServer(
        ae_title=ae_title,
        port=port,
        patients_provider=get_patients
    )

    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Arrêt demandé par l'utilisateur")
        server.stop()
    except Exception as e:
        logger.error(f"Erreur serveur: {e}")
        input("\nAppuyez sur Entrée pour quitter...")


if __name__ == '__main__':
    main()
