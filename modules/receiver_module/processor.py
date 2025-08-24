#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\receiver_module\processor.py
# JUMLAH BARIS : 76
#######################################################################

import ttkbootstrap as ttk
from flowork_kernel.api_contract import BaseModule
from flowork_kernel.ui_shell import shared_properties
from flowork_kernel.api_contract import IDataPreviewer
class ReceiverModule(BaseModule, IDataPreviewer):
    """
    Modul yang secara pasif mendengarkan event dari Event Bus yang
    ditujukan untuk ID uniknya.
    """
    TIER = "free"
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
        self.kernel = services.get("kernel")
        self.parent_frame_for_clipboard = None # To hold a reference for clipboard operations
    def on_load(self):
        pass
    def handle_received_event(self, event_data):
        """Callback yang akan dieksekusi ketika event yang didengarkan diterima."""
        if self.kernel and hasattr(self.kernel, 'trigger_workflow_from_node'):
            target_node_id = event_data.get('target_node_id')
            self.logger(f"Receiver '{target_node_id}' menerima event, meneruskan ke Kernel untuk eksekusi.", "SUCCESS")
            payload_from_event = event_data.get('payload', event_data)
            self.kernel.trigger_workflow_from_node(target_node_id, payload_from_event)
        else:
            self.logger(f"Receiver menerima event, tapi Kernel atau fungsi pemicu tidak ditemukan!", "ERROR")
    def _copy_node_id_to_clipboard(self, node_id):
        """Copies the provided node_id to the system clipboard."""
        if self.parent_frame_for_clipboard:
            self.parent_frame_for_clipboard.clipboard_clear()
            self.parent_frame_for_clipboard.clipboard_append(node_id)
            self.logger(f"ID Receiver '{node_id}' disalin ke clipboard.", "SUCCESS")
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        """Menampilkan informasi agar ID-nya mudah disalin."""
        config = get_current_config()
        created_vars = {}
        self.parent_frame_for_clipboard = parent_frame
        node_id = config.get('__internal_node_id', self.module_id)
        info_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('prop_receiver_title'))
        info_frame.pack(fill='x', padx=5, pady=10)
        id_display_frame = ttk.Frame(info_frame)
        id_display_frame.pack(fill='x', expand=True, padx=10, pady=10)
        id_info_text = self.loc.get('receiver_id_info', id=node_id)
        ttk.Label(id_display_frame, text=id_info_text, wraplength=350, justify="left").pack(side='left', anchor='w', fill='x', expand=True)
        copy_button = ttk.Button(
            id_display_frame,
            text=self.loc.get('copy_id_button', fallback="Salin ID"),
            command=lambda: self._copy_node_id_to_clipboard(node_id),
            bootstyle="info-outline"
        )
        copy_button.pack(side='right', anchor='center', padx=(10, 0))
        debug_vars = shared_properties.create_debug_and_reliability_ui(parent_frame, config, self.loc)
        created_vars.update(debug_vars)
        return created_vars
    def execute(self, payload, config, status_updater, ui_callback, mode='EXECUTE'):
        """
        Sekarang fungsi ini hanya untuk status visual. Logika subscribe sudah pindah.
        """
        node_id = config.get('__internal_node_id', self.module_id)
        status_updater(self.loc.get('receiver_status_listening', id=node_id[:8]), "INFO")
        return payload
    def get_data_preview(self, config: dict):
        """
        TODO: Implement the data preview logic for this module.
        This method should return a small, representative sample of the data
        that the 'execute' method would produce.
        It should run quickly and have no side effects.
        """
        self.logger(f"'get_data_preview' is not yet implemented for {self.module_id}", 'WARN')
        return [{'status': 'preview not implemented'}]
