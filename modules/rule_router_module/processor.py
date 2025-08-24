#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\rule_router_module\processor.py
# JUMLAH BARIS : 113
#######################################################################

import ttkbootstrap as ttk
from tkinter import StringVar
import json
from flowork_kernel.api_contract import BaseModule, IExecutable, IConfigurableUI, IDynamicPorts, IDataPreviewer
from flowork_kernel.ui_shell import shared_properties
from flowork_kernel.utils.payload_helper import get_nested_value
from flowork_kernel.ui_shell.components.LabelledCombobox import LabelledCombobox
class RuleBasedRouter(BaseModule, IExecutable, IConfigurableUI, IDynamicPorts, IDataPreviewer):
    """
    Modul yang mengarahkan payload berdasarkan kata kunci yang ditemukan dalam prompt.
    Versi 'hemat' dari AI Center tanpa menggunakan AI untuk klasifikasi.
    """
    TIER = "free"
    def get_dynamic_ports(self, current_config):
        """Secara dinamis membuat port output berdasarkan aturan yang dibuat pengguna."""
        ports = []
        rules = current_config.get('routing_rules', [])
        if isinstance(rules, list):
            port_names = sorted(list(set(rule['port_name'] for rule in rules if rule.get('port_name'))))
            for port_name in port_names:
                ports.append({"name": port_name, "display_name": port_name.replace("_", " ").title()})
        ports.append({"name": "default", "display_name": self.loc.get('port_default_output', fallback="Default / No Match")})
        return ports
    def execute(self, payload: dict, config: dict, status_updater, ui_callback, mode='EXECUTE'):
        input_variable = config.get('input_variable')
        routing_rules = config.get('routing_rules', [])
        if not input_variable:
            status_updater("Input variable not configured. Using default output.", "WARN")
            return {"payload": payload, "output_name": "default"}
        input_text = get_nested_value(payload, input_variable)
        if not isinstance(input_text, str):
            status_updater(f"Input at '{input_variable}' is not text. Using default route.", "WARN")
            return {"payload": payload, "output_name": "default"}
        input_text_lower = input_text.lower()
        for rule in routing_rules:
            port_name = rule.get('port_name')
            keywords_str = rule.get('keywords', '').lower()
            if not port_name or not keywords_str:
                continue
            keywords = [kw.strip() for kw in keywords_str.split(',')]
            if any(keyword in input_text_lower for keyword in keywords if keyword):
                status_updater(f"Keyword match found. Routing to '{port_name}'.", "SUCCESS")
                return {"payload": payload, "output_name": port_name}
        status_updater("No rules matched. Using default route.", "INFO")
        return {"payload": payload, "output_name": "default"}
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        config = get_current_config()
        self.rules_ui_list = []
        property_vars = {}
        input_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('prop_input_variable_label'))
        input_frame.pack(fill='x', padx=5, pady=5)
        property_vars['input_variable'] = StringVar(value=config.get('input_variable', ''))
        ttk.Combobox(input_frame, textvariable=property_vars['input_variable'], values=list(available_vars.keys()), state='readonly').pack(fill='x', padx=5, pady=5)
        main_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('prop_routing_rules_label'))
        main_frame.pack(fill='x', padx=5, pady=5)
        header = ttk.Frame(main_frame)
        header.pack(fill='x', padx=10, pady=5)
        ttk.Label(header, text=self.loc.get('prop_output_port_header'), width=20).pack(side='left', padx=(0,5))
        ttk.Label(header, text=self.loc.get('prop_keywords_header')).pack(side='left', padx=5)
        self.rules_container = ttk.Frame(main_frame)
        self.rules_container.pack(fill="x", expand=True, padx=10, pady=(0, 10))
        saved_rules = config.get('routing_rules', [])
        if saved_rules and isinstance(saved_rules, list):
            for rule_data in saved_rules:
                self._add_rule_row(rule_data)
        else:
            self._add_rule_row()
        add_button = ttk.Button(main_frame, text=self.loc.get('prop_add_rule_button'), command=self._add_rule_row, style="success-outline.TButton")
        add_button.pack(pady=5, anchor='w', padx=10)
        class RulesVar:
            def __init__(self, ui_list):
                self.ui_list = ui_list
            def get(self):
                rules_data = []
                for rule_widgets in self.ui_list:
                    if rule_widgets['row'].winfo_exists():
                        port_name = rule_widgets['port_var'].get().strip().replace(" ", "_") # Sanitize port name
                        keywords = rule_widgets['keywords_var'].get().strip()
                        if port_name and keywords:
                            rules_data.append({'port_name': port_name, 'keywords': keywords})
                return rules_data
        property_vars['routing_rules'] = RulesVar(self.rules_ui_list)
        debug_vars = shared_properties.create_debug_and_reliability_ui(parent_frame, config, self.loc)
        property_vars.update(debug_vars)
        return property_vars
    def _add_rule_row(self, rule_data=None):
        if rule_data is None: rule_data = {}
        row_frame = ttk.Frame(self.rules_container)
        row_frame.pack(fill='x', pady=2)
        port_var = StringVar(value=rule_data.get('port_name', ''))
        ttk.Entry(row_frame, textvariable=port_var, width=20).pack(side='left', padx=(0, 5))
        keywords_var = StringVar(value=rule_data.get('keywords', ''))
        ttk.Entry(row_frame, textvariable=keywords_var).pack(side='left', fill='x', expand=True)
        remove_button = ttk.Button(row_frame, text="X", width=2, style="danger.TButton", command=row_frame.destroy)
        remove_button.pack(side='left', padx=(5, 0))
        self.rules_ui_list.append({
            'row': row_frame,
            'port_var': port_var,
            'keywords_var': keywords_var
        })
    def get_data_preview(self, config: dict):
        rules = config.get('routing_rules', [])
        return {
            'input_variable': config.get('input_variable', 'not_set'),
            'possible_outputs': [rule.get('port_name') for rule in rules if rule.get('port_name')] + ['Default']
        }
