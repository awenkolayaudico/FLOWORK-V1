#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\debug_popup_module\processor.py
# JUMLAH BARIS : 35
#######################################################################

from flowork_kernel.api_contract import BaseModule
import json
import ttkbootstrap as ttk
from tkinter import scrolledtext
class DebugPopupModule(BaseModule):
    TIER = "free"  # ADDED BY SCANNER: Default tier
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
    def _show_popup_on_ui_thread(self, title, data_string):
        popup = ttk.Toplevel(title=title)
        popup.geometry("600x400")
        txt_area = scrolledtext.ScrolledText(popup, wrap="word", width=70, height=20)
        txt_area.pack(expand=True, fill="both", padx=10, pady=10)
        txt_area.insert("1.0", data_string)
        txt_area.config(state="disabled")
        popup.transient()
        popup.grab_set()
        popup.wait_window()
    def execute(self, payload, config, status_updater, ui_callback, mode='EXECUTE'):
        status_updater("Menyiapkan popup...", "INFO")
        try:
            payload_str = json.dumps(payload, indent=4, ensure_ascii=False)
        except Exception:
            payload_str = str(payload)
        popup_title = "Output Debug dari Node Sebelumnya"
        ui_callback(self._show_popup_on_ui_thread, popup_title, payload_str)
        status_updater("Popup ditampilkan", "SUCCESS")
        return payload
