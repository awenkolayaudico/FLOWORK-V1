#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\flowork_kernel\services\startup_service\startup_service.py
# JUMLAH BARIS : 64
#######################################################################

from ..base_service import BaseService
import time
from tkinter import messagebox
from flowork_kernel.exceptions import MandatoryUpdateRequiredError, PermissionDeniedError
class StartupService(BaseService):
    """
    A dedicated service to handle the application's startup sequence.
    [REFACTORED V3] Now handles None services gracefully if a premium service
    failed to load due to license restrictions.
    [FIXED V4] Removed direct call to start trigger listeners to prevent race conditions.
    The TriggerManager now subscribes to an event instead.
    """
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
    def run_startup_sequence(self):
        """
        Executes the main startup logic with robust error handling for permissions.
        """
        try:
            self.logger("StartupService (Phase 1): Running Benteng Baja file integrity check...", "INFO")
            integrity_checker = self.kernel.get_service("integrity_checker_service", is_system_call=True)
            if integrity_checker: integrity_checker.verify_core_files()
            self.logger("StartupService (Phase 2): Beginning new startup sequence (Update & License Verification)...", "INFO")
            update_service = self.kernel.get_service("update_service", is_system_call=True)
            if update_service: update_service.check_for_updates()
            self.logger("StartupService (Phase 3): All checks passed. Starting normal services...", "INFO")
            services_to_start = [
                ("module_manager_service", lambda s: s.discover_and_load_modules()),
                ("widget_manager_service", lambda s: s.discover_and_load_widgets()),
                ("trigger_manager_service", lambda s: s.discover_and_load_triggers()),
                ("localization_manager", lambda s: s.load_all_languages()),
                ("tab_manager_service", lambda s: s.start() if hasattr(s, 'start') else None),
                ("scheduler_manager_service", lambda s: s.start() if hasattr(s, 'start') else None),
                ("trigger_manager_service", lambda s: s.start() if hasattr(s, 'start') else None), # (ADDED) We call the new start() method
                ("api_server_service", lambda s: s.start() if hasattr(s, 'start') else None)
            ]
            for service_id, start_action in services_to_start:
                try:
                    service_instance = self.kernel.get_service(service_id, is_system_call=True)
                    if service_instance:
                        start_action(service_instance)
                except PermissionDeniedError as e:
                    self.logger(f"StartupService: Skipped loading/starting '{service_id}' due to license restrictions.", "WARN")
                except Exception as e:
                    self.logger(f"StartupService: An error occurred with service '{service_id}': {e}", "ERROR")
            time.sleep(1)
            event_bus = self.kernel.get_service("event_bus", is_system_call=True)
            if event_bus:
                event_bus.publish("event_all_services_started", {})
            self.kernel.startup_complete = True
            self.logger("StartupService: All services started successfully.", "SUCCESS")
            return {"status": "complete"}
        except MandatoryUpdateRequiredError:
            raise
        except Exception as e:
            self.logger(f"A critical, unrecoverable error occurred during startup: {e}", "CRITICAL")
            raise e
