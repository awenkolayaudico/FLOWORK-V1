#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\plugins\flowork_core_ui\settings_components\license_management_frame.py
# JUMLAH BARIS : 72
#######################################################################

import ttkbootstrap as ttk
from tkinter import messagebox
import os
import threading # (PENAMBAHAN) Import threading for background task
class LicenseManagementFrame(ttk.LabelFrame):
    def __init__(self, parent, kernel):
        self.kernel = kernel
        self.loc = self.kernel.get_service("localization_manager")
        super().__init__(parent, text=self.loc.get("settings_license_title", fallback="License Management"), padding=15)
        self._build_widgets()
        self.load_settings_data(None) # Panggil untuk set state awal
    def _build_widgets(self):
        self.deactivate_button = ttk.Button(
            self,
            text=self.loc.get("settings_license_deactivate_button", fallback="Deactivate License on This Computer"),
            command=self._deactivate_license_action, # (PERBAIKAN) Ganti nama fungsi
            bootstyle="danger-outline"
        )
        self.deactivate_button.pack(pady=5, padx=5, fill='x')
    def update_ui_based_on_license_status(self):
        """Enables or disables the deactivate button based on the license status."""
        if hasattr(self, 'deactivate_button') and self.deactivate_button.winfo_exists():
            if self.kernel.is_premium_user():
                self.deactivate_button.config(state="normal")
            else:
                self.deactivate_button.config(state="disabled")
    def _deactivate_license_action(self):
        """
        (PERBAIKAN) Prompts for confirmation and then runs the license deactivation in a thread.
        """
        if messagebox.askyesno(
            self.loc.get("settings_license_deactivate_confirm_title", fallback="Confirm Deactivation"),
            self.loc.get("settings_license_deactivate_confirm_message"),
            parent=self
        ):
            self.deactivate_button.config(state="disabled") # Disable button during process
            threading.Thread(target=self._deactivate_worker, daemon=True).start()
    def _deactivate_worker(self):
        """
        (PENAMBAHAN) Worker function to call the kernel service in the background.
        """
        success, message = self.kernel.deactivate_license_online()
        self.after(0, self._on_deactivate_complete, success, message) # Schedule UI update on main thread
    def _on_deactivate_complete(self, success, message):
        """
        (PENAMBAHAN) UI callback to show results after deactivation attempt.
        """
        if success:
            self.kernel.license_tier = "free"
            self.kernel.is_premium = False
            messagebox.showinfo(
                self.loc.get("messagebox_success_title", fallback="Success"),
                message
            )
            self.kernel.get_service("event_bus").publish("RESTART_APP", {})
        else:
            messagebox.showerror(self.loc.get("messagebox_error_title", fallback="Failed"), message, parent=self)
        self.deactivate_button.config(state="normal") # Re-enable button
        self.update_ui_based_on_license_status() # Update button state based on new license status
    def load_settings_data(self, settings_data):
        """This frame's UI is updated based on kernel state, not settings data."""
        self.update_ui_based_on_license_status()
    def get_settings_data(self):
        """This frame doesn't save any settings, it only performs actions."""
        return {}
