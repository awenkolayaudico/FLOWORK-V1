#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\flowork_kernel\services\update_service\update_service.py
# JUMLAH BARIS : 65
#######################################################################

import requests
import webbrowser
from tkinter import messagebox # (PENAMBAHAN) Import messagebox
from flowork_kernel.kernel import Kernel
from flowork_kernel.services.base_service import BaseService
from flowork_kernel.exceptions import MandatoryUpdateRequiredError
from packaging import version # (PENAMBAHAN) Import library packaging
class UpdateService(BaseService):
    """
    A dedicated service to handle application update checks against a remote source.
    """
    UPDATE_JSON_URL = "https://raw.githubusercontent.com/awenkolayaudico/INFOUPDATE/refs/heads/main/update.json"
    def __init__(self, kernel: Kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.logger = self.kernel.write_to_log
    def check_for_updates(self):
        """
        Fetches the update.json file and checks if a mandatory update is required.
        Raises MandatoryUpdateRequiredError if a mandatory update is found.
        """
        self.logger("UpdateService: Checking for updates from remote URL...", "INFO")
        try:
            response = requests.get(self.UPDATE_JSON_URL, timeout=10)
            response.raise_for_status() # Raises an exception for bad status codes (4xx or 5xx)
            update_data = response.json()
            latest_version_str = update_data.get("version")
            is_mandatory = update_data.get("is_mandatory", False)
            current_version_str = Kernel.APP_VERSION
            self.logger(f"Current version: {current_version_str}, Latest version from server: {latest_version_str}", "DEBUG")
            if latest_version_str and version.parse(latest_version_str) > version.parse(current_version_str):
                if is_mandatory:
                    self.logger(f"MANDATORY update found! Version {latest_version_str} is required.", "CRITICAL")
                    raise MandatoryUpdateRequiredError("A mandatory update is available.", update_info=update_data)
                else:
                    self.logger(f"Optional update found: Version {latest_version_str} is available.", "INFO")
            else:
                self.logger("Application is up to date.", "SUCCESS")
        except requests.exceptions.RequestException as e:
            self.logger(f"Could not check for updates. Network error: {e}. Defaulting to FREE tier.", "WARN")
            self.kernel.is_premium = False
            self.kernel.license_tier = "free"
            messagebox.showwarning(
                "Update Check Failed",
                "Could not connect to the update server. The application will run in FREE mode as a security measure."
            )
        except Exception as e:
            self.logger(f"An unexpected error occurred during update check: {e}", "ERROR")
    def open_download_url(self, update_info):
        """
        Opens the download URL from the update information in the default web browser.
        This is typically called from the mandatory update dialog.
        """
        url = update_info.get("download_url")
        if url:
            self.logger(f"Opening download URL: {url}", "INFO")
            webbrowser.open(url)
        else:
            self.logger("No download URL found in update information.", "ERROR")
