"""
Parser pour les exports CSV Doctolib
Extrait les informations des patients pour le DICOM Worklist
"""

import csv
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from pathlib import Path


@dataclass
class Patient:
    """Information patient pour DICOM Worklist"""
    patient_id: str
    last_name: str
    first_name: str
    birth_date: str  # Format YYYYMMDD
    sex: str  # M, F, O
    appointment_date: str  # Format YYYYMMDD
    appointment_time: str  # Format HHMMSS
    modality: str  # US pour échographie
    procedure_description: str
    accession_number: str
    study_instance_uid: str


class DoctolibParser:
    """Parse les exports CSV Doctolib"""

    def __init__(self, csv_path: str):
        self.csv_path = csv_path

    def parse(self) -> List[Patient]:
        """Parse le fichier CSV et retourne la liste des patients"""
        patients = []

        with open(self.csv_path, 'r', encoding='utf-8') as f:
            # Doctolib utilise ; comme séparateur
            reader = csv.DictReader(f, delimiter=';')

            for row in reader:
                patient = self._parse_row(row)
                if patient:
                    patients.append(patient)

        return patients

    def _parse_row(self, row: dict) -> Optional[Patient]:
        """Parse une ligne du CSV en objet Patient"""
        try:
            # Extraire les données de base
            patient_id = row.get('Doctolib Patient ID', '')
            last_name = row.get('Nom du patient', '').upper().strip()
            first_name = row.get('Prénom du patient', '').capitalize().strip()

            # Date de naissance (format: 1962-09-28 ou vide)
            birth_date_str = row.get('Date de naissance', '')
            if birth_date_str:
                try:
                    birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').strftime('%Y%m%d')
                except:
                    birth_date = ''
            else:
                birth_date = ''

            # Sexe (depuis Civilité ou Patient legal gender)
            civilite = row.get('Civilité', '')
            sex = 'F' if civilite in ['Mme', 'Mme.', 'Madame'] else 'M' if civilite in ['M.', 'M', 'Mr', 'Monsieur'] else 'O'

            # Date du RDV (format: "06/01/2026")
            date_str = row.get('Date de début', '').strip('"')
            if date_str:
                try:
                    appointment_date = datetime.strptime(date_str, '%d/%m/%Y').strftime('%Y%m%d')
                except:
                    return None
            else:
                return None

            # Heure du RDV (format: "08h30")
            time_str = row.get('Début', '').strip('"')
            if time_str:
                try:
                    # Convertir "08h30" en "083000"
                    time_str = time_str.replace('h', ':')
                    appointment_time = datetime.strptime(time_str, '%H:%M').strftime('%H%M%S')
                except:
                    appointment_time = '000000'
            else:
                appointment_time = '000000'

            # Motif du RDV
            procedure = row.get('Motif du RDV', 'Echographie')

            # Générer un accession number unique
            accession_number = row.get('Id', str(abs(hash(f"{patient_id}{appointment_date}{appointment_time}")))[:10])

            # Générer un Study Instance UID conforme DICOM
            # Règles: uniquement chiffres et points, pas de leading zeros par composant
            patient_hash = str(abs(hash(patient_id)))[:12]
            # Supprimer les leading zeros (ex: 083000 -> 83000, 20260106 -> 20260106)
            date_component = str(int(appointment_date))
            time_component = str(int(appointment_time))
            study_uid = f"1.2.826.0.1.3680043.8.498.{patient_hash}.{date_component}.{time_component}"

            return Patient(
                patient_id=patient_id,
                last_name=last_name,
                first_name=first_name,
                birth_date=birth_date,
                sex=sex,
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                modality='US',  # Ultrasound
                procedure_description=procedure,
                accession_number=accession_number,
                study_instance_uid=study_uid
            )

        except Exception as e:
            print(f"Erreur parsing ligne: {e}")
            return None


def filter_echo_patients(patients: List[Patient]) -> List[Patient]:
    """Filtre uniquement les patients avec RDV échographie/cytoponction thyroïde"""
    echo_keywords = ['echo', 'écho', 'cytoponction', 'thyro', 'thyr']

    filtered = []
    for p in patients:
        procedure_lower = p.procedure_description.lower()
        if any(kw in procedure_lower for kw in echo_keywords):
            filtered.append(p)

    return filtered


if __name__ == '__main__':
    # Test du parser
    import sys

    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    else:
        csv_path = r"C:\Users\Emeric\Downloads\export_rdv_2026-01-06-2026-01-06.csv"

    parser = DoctolibParser(csv_path)
    patients = parser.parse()

    print(f"\nTotal patients: {len(patients)}")

    # Filtrer uniquement les échos
    echo_patients = filter_echo_patients(patients)
    print(f"Patients écho/thyroïde: {len(echo_patients)}")

    print("\n--- Liste des patients échographie ---")
    for p in echo_patients:
        print(f"  {p.appointment_time[:2]}:{p.appointment_time[2:4]} - {p.last_name} {p.first_name} ({p.procedure_description})")
