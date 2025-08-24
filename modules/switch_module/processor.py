#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\switch_module\processor.py
# JUMLAH BARIS : 65
#######################################################################

from flowork_kernel.api_contract import BaseModule, IExecutable, IConfigurableUI, IDynamicPorts
import ttkbootstrap as ttk
from tkinter import StringVar, scrolledtext
from flowork_kernel.ui_shell import shared_properties
from flowork_kernel.ui_shell.components.LabelledCombobox import LabelledCombobox
from flowork_kernel.utils.payload_helper import get_nested_value
import json
class SwitchModule(BaseModule, IExecutable, IConfigurableUI, IDynamicPorts):
    TIER = "free"
    def get_dynamic_ports(self, current_config):
        ports = []
        cases_str = current_config.get('cases', '')
        case_names = [line.strip() for line in cases_str.split('\n') if line.strip()]
        for case_name in case_names:
            ports.append({
                "name": case_name.replace(" ", "_").lower(),
                "display_name": case_name
            })
        ports.append({
            "name": "default_output",
            "display_name": self.loc.get('switch_module_default_port', fallback="Default")
        })
        return ports
    def execute(self, payload: dict, config: dict, status_updater, ui_callback, mode='EXECUTE'):
        input_variable = config.get('input_variable', '')
        cases_str = config.get('cases', '')
        if not input_variable:
            status_updater("Input variable not configured.", "WARN")
            return {"payload": payload, "output_name": "default_output"}
        input_value = get_nested_value(payload, input_variable)
        if input_value is None:
            status_updater(f"Variable '{input_variable}' not found in payload.", "WARN")
            return {"payload": payload, "output_name": "default_output"}
        case_names = [line.strip() for line in cases_str.split('\n') if line.strip()]
        str_input_value = str(input_value)
        for case in case_names:
            if str_input_value == case:
                output_port = case.replace(" ", "_").lower()
                status_updater(f"Match found. Routing to '{output_port}'.", "SUCCESS")
                return {"payload": payload, "output_name": output_port}
        status_updater("No case matched. Using default route.", "INFO")
        return {"payload": payload, "output_name": "default_output"}
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        config = get_current_config()
        property_vars = {}
        property_vars['input_variable'] = StringVar(value=config.get('input_variable', ''))
        LabelledCombobox(
            parent=parent_frame,
            label_text="Input Variable to Switch On:",
            variable=property_vars['input_variable'],
            values=list(available_vars.keys())
        )
        ttk.Label(parent_frame, text="Cases (one per line):").pack(fill='x', padx=5, pady=(10, 0))
        cases_editor = scrolledtext.ScrolledText(parent_frame, height=8, font=("Consolas", 10))
        cases_editor.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        cases_editor.insert('1.0', config.get('cases', ''))
        property_vars['cases'] = cases_editor
        return property_vars
