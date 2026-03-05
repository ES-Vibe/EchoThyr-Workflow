"""
GE Structured Report Parser for extracting thyroid measurements
Parses the proprietary GE XML format stored in DICOM SR tag (6005,1010)
"""

import pydicom
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field


@dataclass
class ThyroidMeasurement:
    """Single thyroid measurement"""
    name: str           # e.g., "Thyroïde H", "Thyroïde W", "Thyroïde L", "Vol Thyroïde"
    side: str           # "Rt" (right/droit) or "Lt" (left/gauche)
    value: float        # Value in display units
    unit: str           # "cm" or "ml"
    measurement_type: str  # "MEASURE" or "CALCULATION"


@dataclass
class NoduleMeasurement:
    """Nodule measurement with dimensions"""
    nodule_id: int      # 1, 2, 3, etc.
    side: str           # "Rt" or "Lt"
    height: float = 0.0  # in mm
    width: float = 0.0   # in mm
    length: float = 0.0  # in mm
    volume: float = 0.0  # in ml (from SR or calculated)

    def calculate_volume(self) -> float:
        """Calculate volume using ellipsoid formula: V = π/6 × H × W × L (in ml)"""
        import math
        if self.height > 0 and self.width > 0 and self.length > 0:
            # Dimensions are in mm, convert to cm for ml result
            h_cm = self.height / 10
            w_cm = self.width / 10
            l_cm = self.length / 10
            return (math.pi / 6) * h_cm * w_cm * l_cm
        return 0.0

    def get_volume(self) -> float:
        """Get volume (from SR if available, otherwise calculated)"""
        if self.volume > 0:
            return self.volume
        return self.calculate_volume()


@dataclass
class RawMeasurementSet:
    """A set of related measurements from SR sharing the same resultNo.
    Used in hybrid mode when the generic Volume tool was used (no side/context info)."""
    result_no: int              # 0, 1, 2, 3...
    qualifier: str = ""         # Original qualifier string (may be empty)
    parameter_prefix: str = ""  # "SP/2D/ThyroidDist" or "SP/2D/VolumeDist"
    height_cm: float = 0.0
    width_cm: float = 0.0
    length_cm: float = 0.0
    volume_ml: float = 0.0


@dataclass
class ThyroidReport:
    """Complete thyroid measurement report from SR"""
    patient_name: str = ""
    patient_id: str = ""
    birth_date: str = ""
    study_date: str = ""

    # Measurements organized by side
    right_lobe: Dict[str, ThyroidMeasurement] = field(default_factory=dict)
    left_lobe: Dict[str, ThyroidMeasurement] = field(default_factory=dict)
    isthmus: Dict[str, ThyroidMeasurement] = field(default_factory=dict)

    # Nodules list
    nodules: List[NoduleMeasurement] = field(default_factory=list)

    # Manual measurements (not in SR)
    isthmus_mm: float = 0.0  # Manual isthmus measurement in mm

    def set_isthmus(self, value_mm: float):
        """Set isthmus measurement manually (in mm)"""
        self.isthmus_mm = value_mm

    def get_formatted_text(self) -> str:
        """Generate formatted measurement text for the report"""
        lines = []
        lines.append("• Volume thyroïdien")

        # Right lobe
        right_dims = self._format_dimensions("Rt")
        lines.append(f"- lobe droit : {right_dims}")

        # Left lobe
        left_dims = self._format_dimensions("Lt")
        lines.append(f"- lobe gauche : {left_dims}")

        # Isthmus (from SR or manual)
        if self.isthmus:
            isthmus_dims = self._format_isthmus()
            lines.append(f"- isthme : {isthmus_dims}")
        elif self.isthmus_mm > 0:
            lines.append(f"- isthme : {self.isthmus_mm:.1f} mm")
        else:
            lines.append("- isthme : non mesuré")

        lines.append("• Echogénicité glandulaire homogène")
        lines.append("• Pas d'anomalie de la vascularisation")

        # Nodules
        if self.nodules:
            lines.append("• Nodules :")
            for nodule in self.nodules:
                side_text = "lobe droit" if nodule.side == "Rt" else "lobe gauche"
                dims = f"{nodule.height:.1f} x {nodule.width:.1f} x {nodule.length:.1f} mm"
                vol = nodule.get_volume()
                if vol > 0:
                    dims += f" (volume {vol:.2f} ml)"
                lines.append(f"  - Nodule {nodule.nodule_id} ({side_text}) : {dims}")
        else:
            lines.append("• Nodules : 0")

        lines.append("• Etude des ganglions (secteurs II, III, IV, VI) et du tractus thyréoglosse : 0")

        return "\r\n".join(lines)

    def _format_dimensions(self, side: str) -> str:
        """Format dimensions for a lobe"""
        lobe = self.right_lobe if side == "Rt" else self.left_lobe

        if not lobe:
            return "non mesuré"

        dims = []
        for key in ["H", "W", "L"]:
            for name, m in lobe.items():
                if key in name:
                    # Convert to mm for display
                    value_mm = m.value * 10 if m.unit == "cm" else m.value
                    dims.append(f"{value_mm:.1f}")
                    break

        if not dims:
            return "non mesuré"

        result = " x ".join(dims) + " mm"

        # Add volume if present
        for name, m in lobe.items():
            if "Vol" in name:
                result += f" (volume {m.value:.2f} ml)"
                break

        return result

    def _format_isthmus(self) -> str:
        """Format isthmus measurement"""
        if not self.isthmus:
            return "non mesuré"

        for name, m in self.isthmus.items():
            value_mm = m.value * 10 if m.unit == "cm" else m.value
            return f"{value_mm:.1f} mm"

        return "non mesuré"


class SRParser:
    """Parser for GE Ultrasound Structured Reports"""

    GE_XML_TAG = (0x6005, 0x1010)

    def __init__(self):
        pass

    def is_sr_file(self, dicom_path: str, logger=None) -> bool:
        """Check if a DICOM file is a Structured Report"""
        try:
            dcm = pydicom.dcmread(dicom_path, force=True)
            modality = getattr(dcm, 'Modality', '')
            sop_class = str(getattr(dcm, 'SOPClassUID', ''))

            # SR modality or SR SOP Class
            is_sr = modality == 'SR' or '1.2.840.10008.5.1.4.1.1.88' in sop_class

            if logger and is_sr:
                logger.debug(f"SR file detected: {dicom_path}")

            return is_sr
        except Exception as e:
            if logger:
                logger.warning(f"Error checking SR file {dicom_path}: {e}")
            return False

    def parse_sr(self, dicom_path: str, logger=None) -> Optional[ThyroidReport]:
        """
        Parse a GE Structured Report and extract thyroid measurements

        Args:
            dicom_path: Path to DICOM SR file
            logger: Optional logger

        Returns:
            ThyroidReport object or None if parsing failed
        """
        try:
            dcm = pydicom.dcmread(dicom_path, force=True)

            # Extract patient info
            report = ThyroidReport(
                patient_name=str(getattr(dcm, 'PatientName', '')),
                patient_id=str(getattr(dcm, 'PatientID', '')),
                birth_date=self._format_date(str(getattr(dcm, 'PatientBirthDate', ''))),
                study_date=self._format_date(str(getattr(dcm, 'StudyDate', '')))
            )

            # Extract GE XML data
            if self.GE_XML_TAG not in dcm:
                if logger:
                    logger.warning(f"No GE XML tag found in SR: {dicom_path}")
                return None

            xml_data = dcm[self.GE_XML_TAG].value
            if isinstance(xml_data, bytes):
                xml_data = xml_data.decode('utf-8', errors='replace')

            # Clean XML (remove CDATA wrapper if present)
            xml_data = xml_data.strip()
            if xml_data.startswith('<![CDATA['):
                xml_data = xml_data[9:]
            if xml_data.endswith(']]>'):
                xml_data = xml_data[:-3]

            # Parse XML
            root = ET.fromstring(xml_data)

            # Find all MEASUREMENT elements
            measurements = root.findall('.//MEASUREMENT')

            if logger:
                logger.debug(f"Found {len(measurements)} measurements in SR")

            for meas in measurements:
                self._parse_measurement(meas, report, logger)

            if logger:
                logger.info(f"SR parsed: Right lobe={len(report.right_lobe)}, Left lobe={len(report.left_lobe)} measurements")

            return report

        except ET.ParseError as e:
            if logger:
                logger.error(f"XML parse error in SR {dicom_path}: {e}")
            return None
        except Exception as e:
            if logger:
                logger.error(f"Error parsing SR {dicom_path}: {e}", exc_info=e)
            return None

    def parse_sr_raw(self, dicom_path: str, logger=None) -> Tuple[Optional[ThyroidReport], List[RawMeasurementSet], bool]:
        """
        Parse SR and return patient info + raw measurement sets + hybrid flag.

        Returns:
            Tuple of:
            - ThyroidReport with patient info (measurements populated only if thyroid tool)
            - List of RawMeasurementSet grouped by resultNo (for hybrid matching)
            - bool: True if hybrid mode is needed (generic Volume tool detected)
        """
        try:
            dcm = pydicom.dcmread(dicom_path, force=True)

            # Extract patient info
            report = ThyroidReport(
                patient_name=str(getattr(dcm, 'PatientName', '')),
                patient_id=str(getattr(dcm, 'PatientID', '')),
                birth_date=self._format_date(str(getattr(dcm, 'PatientBirthDate', ''))),
                study_date=self._format_date(str(getattr(dcm, 'StudyDate', '')))
            )

            # Extract GE XML data
            if self.GE_XML_TAG not in dcm:
                if logger:
                    logger.warning(f"No GE XML tag found in SR: {dicom_path}")
                return report, [], False

            xml_data = dcm[self.GE_XML_TAG].value
            if isinstance(xml_data, bytes):
                xml_data = xml_data.decode('utf-8', errors='replace')

            xml_data = xml_data.strip()
            if xml_data.startswith('<![CDATA['):
                xml_data = xml_data[9:]
            if xml_data.endswith(']]>'):
                xml_data = xml_data[:-3]

            root = ET.fromstring(xml_data)
            measurements = root.findall('.//MEASUREMENT')

            if logger:
                logger.debug(f"Found {len(measurements)} measurements in SR")

            # Detect if generic Volume tool was used
            needs_hybrid = False
            has_volume_dist = False
            has_empty_qualifier = False

            for meas in measurements:
                param_id = meas.findtext('parameterId', '')
                qualifier = meas.findtext('qualifier', '')
                result_no = int(meas.findtext('resultNo', '-1'))

                if result_no >= 0:  # Skip averages
                    if 'VolumeDist' in param_id or 'VolumeVolume' in param_id:
                        has_volume_dist = True
                    if not qualifier.strip():
                        has_empty_qualifier = True

            needs_hybrid = has_volume_dist and has_empty_qualifier

            if not needs_hybrid:
                # Thyroid-specific tool: use existing parsing (populates report)
                for meas in measurements:
                    self._parse_measurement(meas, report, logger)
                if logger:
                    logger.info(f"SR parsed (thyroid tool): Right={len(report.right_lobe)}, Left={len(report.left_lobe)}")
                return report, [], False

            # Generic Volume tool: build raw measurement sets grouped by resultNo
            raw_sets_dict: Dict[int, RawMeasurementSet] = {}

            for meas in measurements:
                result_no = int(meas.findtext('resultNo', '-1'))
                if result_no < 0:  # Skip averages
                    continue

                param_id = meas.findtext('parameterId', '')
                param_name = meas.findtext('parameterName', '')
                qualifier = meas.findtext('qualifier', '')
                value_str = meas.findtext('valueDouble', '0')
                unit = meas.findtext('displayUnit', '')

                try:
                    value = float(value_str)
                    if unit == 'cm':
                        value = value * 100  # meters to cm
                    elif unit in ('ml', 'cc'):
                        value = value * 1000000  # m³ to ml
                except ValueError:
                    value = 0.0

                if result_no not in raw_sets_dict:
                    raw_sets_dict[result_no] = RawMeasurementSet(
                        result_no=result_no,
                        qualifier=qualifier,
                        parameter_prefix=param_id.rsplit('/', 1)[0] if '/' in param_id else param_id
                    )

                raw_set = raw_sets_dict[result_no]

                # Assign to appropriate dimension
                if 'H' in param_name or 'Height' in param_name:
                    raw_set.height_cm = value
                elif 'W' in param_name or 'Width' in param_name:
                    raw_set.width_cm = value
                elif 'L' in param_name or 'Length' in param_name:
                    raw_set.length_cm = value
                elif 'Vol' in param_name:
                    raw_set.volume_ml = value

            raw_sets = sorted(raw_sets_dict.values(), key=lambda s: s.result_no)

            if logger:
                logger.info(f"SR parsed (generic tool, hybrid needed): {len(raw_sets)} measurement sets")
                for rs in raw_sets:
                    logger.debug(f"  resultNo={rs.result_no}: H={rs.height_cm:.2f}cm W={rs.width_cm:.2f}cm "
                               f"L={rs.length_cm:.2f}cm Vol={rs.volume_ml:.2f}ml")

            return report, raw_sets, True

        except ET.ParseError as e:
            if logger:
                logger.error(f"XML parse error in SR {dicom_path}: {e}")
            return None, [], False
        except Exception as e:
            if logger:
                logger.error(f"Error parsing SR {dicom_path}: {e}", exc_info=e)
            return None, [], False

    def _parse_measurement(self, meas_elem: ET.Element, report: ThyroidReport, logger=None):
        """Parse a single MEASUREMENT element"""
        try:
            # Get qualifier (Side=Rt or Side=Lt)
            qualifier = meas_elem.findtext('qualifier', '')
            side = ''
            if 'Rt' in qualifier:
                side = 'Rt'
            elif 'Lt' in qualifier:
                side = 'Lt'

            # Get measurement name and value
            param_name = meas_elem.findtext('parameterName', '')
            value_str = meas_elem.findtext('valueDouble', '0')
            unit = meas_elem.findtext('displayUnit', '')
            meas_type = meas_elem.findtext('parameterType', 'MEASURE')
            result_no_str = meas_elem.findtext('resultNo', '-1')

            result_no = int(result_no_str)

            # resultNo=-1 is average - only use for volume if not already set
            if result_no == -1:
                # Only capture volume from -1 as fallback
                if 'Vol' in param_name and side:
                    lobe = report.right_lobe if side == 'Rt' else report.left_lobe
                    # Only set if not already present
                    if param_name not in lobe:
                        try:
                            value = float(value_str)
                            if unit == 'ml':
                                value = value * 1000000
                            measurement = ThyroidMeasurement(
                                name=param_name,
                                side=side,
                                value=value,
                                unit=unit,
                                measurement_type=meas_type
                            )
                            lobe[param_name] = measurement
                        except:
                            pass
                return

            # Convert value
            try:
                # Values are stored in meters, convert based on display unit
                value = float(value_str)
                if unit == 'cm':
                    value = value * 100  # meters to cm
                elif unit == 'ml':
                    value = value * 1000000  # m³ to ml (cubic meters to milliliters)
            except ValueError:
                value = 0.0

            # resultNo=0 is thyroid lobe, resultNo>0 are nodules
            if result_no == 0:
                # Create measurement object for thyroid lobe
                measurement = ThyroidMeasurement(
                    name=param_name,
                    side=side,
                    value=value,
                    unit=unit,
                    measurement_type=meas_type
                )

                # Categorize by side
                if 'Isthme' in param_name or 'Isthmus' in param_name:
                    report.isthmus[param_name] = measurement
                elif side == 'Rt':
                    report.right_lobe[param_name] = measurement
                elif side == 'Lt':
                    report.left_lobe[param_name] = measurement

                if logger:
                    logger.debug(f"Lobe measurement: {param_name} ({side}) = {value:.2f} {unit}")
            else:
                # Nodule measurement (resultNo > 0)
                # Find or create nodule entry
                nodule = None
                for n in report.nodules:
                    if n.nodule_id == result_no and n.side == side:
                        nodule = n
                        break

                if nodule is None:
                    nodule = NoduleMeasurement(nodule_id=result_no, side=side)
                    report.nodules.append(nodule)

                # Value in mm
                value_mm = value * 10 if unit == 'cm' else value

                # Assign to appropriate dimension
                if 'H' in param_name or 'Height' in param_name:
                    nodule.height = value_mm
                elif 'W' in param_name or 'Width' in param_name:
                    nodule.width = value_mm
                elif 'L' in param_name or 'Length' in param_name:
                    nodule.length = value_mm
                elif 'Vol' in param_name:
                    nodule.volume = value

                if logger:
                    logger.debug(f"Nodule {result_no} ({side}): {param_name} = {value_mm:.1f} mm")

        except Exception as e:
            if logger:
                logger.warning(f"Error parsing measurement: {e}")

    def _format_date(self, dicom_date: str) -> str:
        """Convert DICOM date (YYYYMMDD) to display format (DD.MM.YYYY)"""
        if len(dicom_date) != 8:
            return dicom_date
        try:
            return f"{dicom_date[6:8]}.{dicom_date[4:6]}.{dicom_date[0:4]}"
        except:
            return dicom_date

    def find_sr_files(self, folder_path: str, logger=None) -> List[str]:
        """Find all SR files in a folder (recursively)"""
        sr_files = []
        folder = Path(folder_path)

        for dcm_file in folder.rglob('*.dcm'):
            if self.is_sr_file(str(dcm_file), logger):
                sr_files.append(str(dcm_file))

        if logger:
            logger.debug(f"Found {len(sr_files)} SR files in {folder_path}")

        return sr_files
