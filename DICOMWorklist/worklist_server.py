"""
Serveur DICOM Modality Worklist (MWL)
Répond aux requêtes C-FIND des échographes
Compatible GE Logiq
"""

from pynetdicom import AE, evt, AllStoragePresentationContexts, ALL_TRANSFER_SYNTAXES
from pynetdicom.sop_class import ModalityWorklistInformationFind, Verification
from pydicom.dataset import Dataset
from pydicom.uid import generate_uid, ExplicitVRLittleEndian, ImplicitVRLittleEndian
from typing import List, Callable
import logging

from doctolib_parser import Patient


class WorklistServer:
    """Serveur DICOM Worklist pour échographes GE"""

    def __init__(
        self,
        ae_title: str = "WORKLIST_SCP",
        port: int = 104,
        patients_provider: Callable[[], List[Patient]] = None
    ):
        self.ae_title = ae_title
        self.port = port
        self.patients_provider = patients_provider
        self.ae = None
        self.logger = logging.getLogger('WorklistServer')

    def _create_worklist_dataset(self, patient: Patient) -> Dataset:
        """Crée un Dataset DICOM Worklist à partir d'un patient"""
        ds = Dataset()

        # Patient Module
        ds.PatientName = f"{patient.last_name}^{patient.first_name}"
        ds.PatientID = patient.patient_id
        ds.PatientBirthDate = patient.birth_date
        ds.PatientSex = patient.sex

        # Scheduled Procedure Step Sequence
        sps = Dataset()
        sps.ScheduledStationAETitle = ""
        sps.ScheduledProcedureStepStartDate = patient.appointment_date
        sps.ScheduledProcedureStepStartTime = patient.appointment_time
        sps.Modality = patient.modality
        sps.ScheduledPerformingPhysicianName = ""
        sps.ScheduledProcedureStepDescription = patient.procedure_description
        sps.ScheduledProcedureStepID = patient.accession_number
        sps.ScheduledStationName = ""
        sps.ScheduledProcedureStepLocation = ""

        ds.ScheduledProcedureStepSequence = [sps]

        # Requested Procedure Module
        ds.RequestedProcedureID = patient.accession_number
        ds.RequestedProcedureDescription = patient.procedure_description
        ds.AccessionNumber = patient.accession_number
        ds.StudyInstanceUID = patient.study_instance_uid
        ds.RequestedProcedurePriority = ""

        # Imaging Service Request Module
        ds.ReferringPhysicianName = ""

        # Additional fields often required
        ds.SpecificCharacterSet = 'ISO_IR 100'

        return ds

    def _handle_assoc_request(self, event):
        """Gère les demandes d'association"""
        requestor = event.assoc.requestor
        self.logger.info(f"Association requested from: {requestor.ae_title} @ {requestor.address}:{requestor.port}")
        return 0x0000  # Accept

    def _handle_assoc_accepted(self, event):
        """Log quand association acceptée"""
        self.logger.info(f"Association accepted")

    def _handle_assoc_released(self, event):
        """Log quand association relâchée"""
        self.logger.info(f"Association released")

    def _handle_assoc_aborted(self, event):
        """Log quand association abandonnée"""
        self.logger.warning(f"Association aborted")

    def _handle_echo(self, event):
        """Gère les requêtes C-ECHO (verification)"""
        self.logger.info(f"C-ECHO received from {event.assoc.requestor.ae_title}")
        return 0x0000  # Success

    def _handle_find(self, event):
        """Gère les requêtes C-FIND (Worklist Query)"""
        requestor_ae = event.assoc.requestor.ae_title
        self.logger.info(f"C-FIND request received from {requestor_ae}")

        # Récupérer la liste des patients
        if self.patients_provider:
            patients = self.patients_provider()
        else:
            patients = []

        self.logger.info(f"Processing {len(patients)} patient(s) in worklist")

        # Identifier (query dataset)
        identifier = event.identifier

        # Log query details
        self.logger.debug(f"Query identifier: {identifier}")

        # Extraire les filtres de la requête (optionnel)
        query_date = getattr(identifier, 'ScheduledProcedureStepStartDate', None)
        query_modality = None

        if hasattr(identifier, 'ScheduledProcedureStepSequence') and identifier.ScheduledProcedureStepSequence:
            sps = identifier.ScheduledProcedureStepSequence[0]
            query_modality = getattr(sps, 'Modality', None)
            if not query_date:
                query_date = getattr(sps, 'ScheduledProcedureStepStartDate', None)

        # Filtrer par date si spécifié
        if query_date and query_date != '*' and query_date != '':
            filtered = [p for p in patients if p.appointment_date == str(query_date)]
            if filtered:
                patients = filtered

        # Filtrer par modalité si spécifié
        if query_modality and query_modality != '*' and query_modality != '':
            filtered = [p for p in patients if p.modality == str(query_modality)]
            if filtered:
                patients = filtered

        self.logger.info(f"Returning {len(patients)} patient(s)")

        # Retourner les résultats
        for patient in patients:
            ds = self._create_worklist_dataset(patient)
            self.logger.info(f"  -> {patient.last_name} {patient.first_name} @ {patient.appointment_time[:2]}:{patient.appointment_time[2:4]}")
            yield (0xFF00, ds)  # Pending

    def start(self):
        """Démarre le serveur DICOM Worklist"""
        self.ae = AE(ae_title=self.ae_title)

        # Accepter n'importe quel AE Title appelant
        self.ae.require_calling_aet = []
        self.ae.require_called_aet = []

        # Ajouter le support pour Modality Worklist avec tous les transfer syntaxes
        transfer_syntaxes = [
            ExplicitVRLittleEndian,
            ImplicitVRLittleEndian,
        ]

        self.ae.add_supported_context(ModalityWorklistInformationFind, transfer_syntaxes)
        self.ae.add_supported_context(Verification, transfer_syntaxes)  # Pour C-ECHO

        # Handlers pour les événements
        handlers = [
            (evt.EVT_C_FIND, self._handle_find),
            (evt.EVT_C_ECHO, self._handle_echo),
            (evt.EVT_ACCEPTED, self._handle_assoc_accepted),
            (evt.EVT_RELEASED, self._handle_assoc_released),
            (evt.EVT_ABORTED, self._handle_assoc_aborted),
        ]

        self.logger.info(f"Starting DICOM Worklist Server")
        self.logger.info(f"  AE Title: {self.ae_title}")
        self.logger.info(f"  Port: {self.port}")
        self.logger.info(f"Waiting for connections...")

        # Démarrer le serveur (bloquant)
        self.ae.start_server(('0.0.0.0', self.port), evt_handlers=handlers)

    def stop(self):
        """Arrête le serveur"""
        if self.ae:
            self.ae.shutdown()
            self.logger.info("Server stopped")


if __name__ == '__main__':
    # Test du serveur
    import sys
    from doctolib_parser import DoctolibParser, filter_echo_patients

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

    # Charger les patients depuis le CSV
    csv_path = r"C:\Users\Emeric\Downloads\export_rdv_2026-01-06-2026-01-06.csv"

    def get_patients():
        parser = DoctolibParser(csv_path)
        patients = parser.parse()
        return filter_echo_patients(patients)

    # Créer et démarrer le serveur
    server = WorklistServer(
        ae_title="WORKLIST",
        port=4242,
        patients_provider=get_patients
    )

    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
