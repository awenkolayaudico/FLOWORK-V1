#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\sub_workflow_module\kernel.py
# JUMLAH BARIS : 45
#######################################################################

from flowork_kernel.api_contract import BaseModule
import ttkbootstrap as ttk
class SubWorkflowModule(BaseModule):
    """
    Modul yang berfungsi untuk menjalankan alur kerja lain (dari preset)
    sebagai sebuah sub-rutin.
    """
    def __init__(self, kernel_instance, module_id):
        super().__init__(kernel_instance, module_id)
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        """
        Membuat antarmuka untuk memilih preset yang akan dijalankan.
        """
        property_vars = {}
        current_config = get_current_config()
        ttk.Label(parent_frame, text="Pilih Preset Sub-Alur Kerja:").pack(fill='x', padx=5, pady=(10, 0))
        preset_list = self.kernel.get_preset_list()
        selected_preset_var = ttk.StringVar(value=current_config.get('selected_preset', ''))
        property_vars['selected_preset'] = selected_preset_var
        preset_combobox = ttk.Combobox(parent_frame, textvariable=selected_preset_var, values=preset_list, state="readonly")
        if not preset_list:
            preset_combobox.set("Tidak ada preset tersedia")
            preset_combobox.config(state="disabled")
        preset_combobox.pack(fill='x', padx=5, pady=5)
        return property_vars
    def execute(self, payload, config, status_updater, ui_callback):
        """
        Logika eksekusi utama. Untuk saat ini, hanya placeholder.
        Akan kita implementasikan di langkah berikutnya.
        """
        selected_preset = config.get('selected_preset')
        if not selected_preset:
            status_updater("Belum ada preset dipilih!", "ERROR")
            return payload
        status_updater(f"Siap menjalankan '{selected_preset}'...", "INFO")
        print(f"Placeholder: Eksekusi untuk preset '{selected_preset}' dengan payload: {payload}")
        status_updater(f"Selesai (placeholder)", "SUCCESS")
        return payload
