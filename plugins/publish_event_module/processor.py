#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\plugins\publish_event_module\processor.py
# JUMLAH BARIS : 50
#######################################################################

import ttkbootstrap as ttk
from tkinter import StringVar
from flowork_kernel.api_contract import BaseModule
class PublishEventModule(BaseModule):
    TIER = "free"  # ADDED BY SCANNER: Default tier
    """
    Modul yang didedikasikan untuk menerbitkan (publish) payload saat ini
    ke Event Bus dengan nama event yang bisa dikustomisasi oleh pengguna.
    """
    def __init__(self, module_id: str, services: dict):
        super().__init__(module_id, services)
    def on_load(self):
        """
        Called by the ModuleManager after the module is fully loaded and its manifest is available.
        """
        self.logger(f"Module '{self.manifest.get('name', self.module_id)}' initialized and loaded successfully.", "INFO")
    def execute(self, payload: dict, config: dict, status_updater, ui_callback, mode='EXECUTE') -> dict:
        """
        Menerbitkan seluruh payload ke Event Bus.
        """
        custom_event_name = config.get('custom_event_name', '').strip()
        if not custom_event_name:
            self.logger("Custom event name is not set in properties. Event not published.", "WARN")
            status_updater("Configuration Missing", "WARN")
            return payload
        self.publish_event(custom_event_name, payload)
        status_updater(f"Event '{custom_event_name}' published", "SUCCESS")
        return payload
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        """
        Membuat antarmuka (UI) untuk jendela Properti node ini.
        """
        current_config = get_current_config()
        settings_frame = ttk.LabelFrame(parent_frame, text="Event Publisher Settings")
        settings_frame.pack(fill="x", padx=5, pady=10)
        ttk.Label(settings_frame, text="Custom Event Name to Publish:").pack(fill='x', padx=10, pady=(5,0))
        event_name_var = StringVar(value=current_config.get('custom_event_name', ''))
        entry = ttk.Entry(settings_frame, textvariable=event_name_var)
        entry.pack(fill='x', padx=10, pady=10)
        ttk.Label(settings_frame, text="Example: PROCESS_A_COMPLETE, DATA_RECEIVED", font=("Helvetica", 8, "italic")).pack(fill='x', padx=10, pady=(0, 5))
        return {
            'custom_event_name': event_name_var
        }
