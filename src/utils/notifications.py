"""
Notification module for EchoThyr automation
Provides audio and visual notifications
"""

import winsound
from datetime import datetime
from typing import Optional


class Notifier:
    """Handle audio and visual notifications"""

    def __init__(self, enable_beep: bool = True, enable_banner: bool = True):
        self.enable_beep = enable_beep
        self.enable_banner = enable_banner

    def _beep(self, frequency: int, duration: int):
        """Play a beep sound"""
        if self.enable_beep:
            try:
                winsound.Beep(frequency, duration)
            except RuntimeError:
                pass  # Beep not available on this system

    def success(self, report_name: str, patient_info: str):
        """Show success notification"""
        # Audio notification (ascending beeps)
        self._beep(800, 300)
        self._beep(1200, 300)

        # Visual banner
        if self.enable_banner:
            self._print_success_banner(report_name, patient_info)

    def error(self, context: str, error_message: str):
        """Show error notification"""
        # Audio notification (descending beeps)
        self._beep(400, 200)
        self._beep(400, 200)

        # Visual banner
        if self.enable_banner:
            self._print_error_banner(context, error_message)

    def _print_success_banner(self, report_name: str, patient_info: str):
        """Print success banner to console"""
        GREEN = '\033[92m'
        RESET = '\033[0m'
        BLACK_BG = '\033[40m'

        banner = f"""
{GREEN}{'─' * 80}
SUCCESS: Report Generated Successfully!
{'─' * 80}
Report Name    : {report_name}
Patient Info   : {patient_info}
Generated At   : {datetime.now().strftime('%H:%M:%S')}
{'─' * 80}{RESET}
"""
        print(banner)

    def _print_error_banner(self, context: str, error_message: str):
        """Print error banner to console"""
        RED = '\033[91m'
        RESET = '\033[0m'

        banner = f"""
{RED}{'─' * 80}
ERROR: Report Generation Failed
{'─' * 80}
Context        : {context}
Error Message  : {error_message}
Occurred At    : {datetime.now().strftime('%H:%M:%S')}
{'─' * 80}{RESET}
"""
        print(banner)

    def startup_banner(self, version: str, config):
        """Print startup banner"""
        CYAN = '\033[96m'
        RESET = '\033[0m'

        banner = f"""
{CYAN}╔════════════════════════════════════════════════════════════════════════════════╗
║  ECHOTHYR AUTOMATION - MONITORING CR ECHO THYR GENERATION        v{version}  ║
╚════════════════════════════════════════════════════════════════════════════════╝

Source Directory: {config.source_dir}
Template File   : {config.template_path}
Log Directory   : {config.log_dir}
Monitoring start: {datetime.now().strftime('%H:%M:%S')}
{'─' * 80}{RESET}
"""
        print(banner)
