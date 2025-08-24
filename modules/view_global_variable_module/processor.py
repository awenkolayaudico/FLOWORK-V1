#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\view_global_variable_module\processor.py
# JUMLAH BARIS : 76
#######################################################################

import ttkbootstrap as ttk
from tkinter import StringVar, scrolledtext
import json
from flowork_kernel.api_contract import BaseModule, IExecutable, IConfigurableUI
from flowork_kernel.ui_shell.components.LabelledCombobox import LabelledCombobox
class ViewGlobalVariableModule(BaseModule, IExecutable, IConfigurableUI):
    """
    A module to inspect the current value of a global variable from the
    VariableManagerService and display it in a popup. Also injects the
    value into the payload.
    """
    TIER = "free"
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
        self.variable_manager = services.get("variable_manager_service")
    def _show_popup_on_ui_thread(self, title, data_string):
        """
        Helper function to create and display the popup on the main UI thread.
        """
        popup = ttk.Toplevel(title=title)
        popup.geometry("600x450")
        txt_area = scrolledtext.ScrolledText(popup, wrap="word", width=70, height=20, font=("Consolas", 10))
        txt_area.pack(expand=True, fill="both", padx=10, pady=10)
        txt_area.insert("1.0", data_string)
        txt_area.config(state="disabled")
        popup.transient()
        popup.grab_set()
        popup.wait_window()
    def execute(self, payload, config, status_updater, ui_callback, mode='EXECUTE'):
        variable_name = config.get('variable_name')
        if not variable_name:
            status_updater("No global variable selected.", "WARN") # English Log
            return {"payload": payload, "output_name": "success"}
        status_updater(f"Fetching global variable: {variable_name}", "INFO") # English Log
        retrieved_value = self.variable_manager.get_variable(variable_name)
        popup_title = self.loc.get('popup_title_viewing', fallback="Viewing Global Variable: {variable}", variable=variable_name)
        if retrieved_value is None:
            display_string = self.loc.get('popup_content_var_not_found', fallback="Global variable '{variable}' not found or is disabled.", variable=variable_name)
        else:
            try:
                display_string = json.dumps(retrieved_value, indent=4, ensure_ascii=False)
            except TypeError:
                display_string = str(retrieved_value)
        ui_callback(self._show_popup_on_ui_thread, popup_title, display_string)
        status_updater("Variable displayed.", "SUCCESS") # English Log
        if 'data' not in payload or not isinstance(payload['data'], dict):
            payload['data'] = {}
        payload['data']['inspected_variable_name'] = variable_name
        payload['data']['inspected_variable_value'] = retrieved_value
        return {"payload": payload, "output_name": "success"}
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        config = get_current_config()
        property_vars = {}
        main_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('prop_view_global_title', fallback="Global Variable to View"))
        main_frame.pack(fill='x', padx=5, pady=10)
        global_vars = []
        if self.variable_manager:
            all_vars_data = self.variable_manager.get_all_variables_for_api()
            global_vars = [var['name'] for var in all_vars_data]
        else:
            self.logger("VariableManagerService not available for properties UI.", "ERROR") # English Log
        property_vars['variable_name'] = StringVar(value=config.get('variable_name', ''))
        LabelledCombobox(
            parent=main_frame,
            label_text=self.loc.get('prop_view_global_variable_label', fallback="Global Variable:"),
            variable=property_vars['variable_name'],
            values=sorted(global_vars)
        )
        return property_vars
