#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\keyword_router_module\processor.py
# JUMLAH BARIS : 115
#######################################################################

import ttkbootstrap as ttk
from tkinter import StringVar
from flowork_kernel.api_contract import BaseModule, IExecutable, IConfigurableUI, IDynamicPorts
from flowork_kernel.utils.payload_helper import get_nested_value
class _KeywordRouterPropertiesUI(ttk.Frame):
    """
    This class encapsulates the entire UI for the Keyword Router's properties.
    It manages its own state, including the dynamically added rule rows.
    """
    def __init__(self, parent, loc, config, available_vars):
        super().__init__(parent)
        self.loc = loc
        self.rule_rows = []
        self.input_var = StringVar(value=config.get('input_variable', 'data.prompt'))
        self._build_ui(config, available_vars)
    def _build_ui(self, config, available_vars):
        input_frame = ttk.LabelFrame(self, text=self.loc.get('keyword_router_input_source_title'))
        input_frame.pack(fill='x', padx=5, pady=(10, 5))
        ttk.Label(input_frame, text=self.loc.get('keyword_router_input_variable_label')).pack(fill='x', padx=10, pady=(5,0))
        input_combo = ttk.Combobox(input_frame, textvariable=self.input_var, values=list(available_vars.keys()))
        input_combo.pack(fill='x', padx=10, pady=(0, 10))
        rules_frame = ttk.LabelFrame(self, text=self.loc.get('keyword_router_rules_title'))
        rules_frame.pack(fill='both', expand=True, padx=5, pady=5)
        header = ttk.Frame(rules_frame)
        header.pack(fill='x', padx=10, pady=5)
        ttk.Label(header, text=self.loc.get('keyword_router_keywords_header'), width=30).pack(side='left', expand=True, fill='x')
        ttk.Label(header, text=self.loc.get('keyword_router_output_header')).pack(side='left', expand=True, fill='x', padx=(5,0))
        self.rules_list_frame = ttk.Frame(rules_frame)
        self.rules_list_frame.pack(fill='both', expand=True)
        ttk.Button(rules_frame, text=self.loc.get('keyword_router_add_rule_btn'), command=self._add_rule_row, bootstyle="outline-success").pack(fill='x', padx=10, pady=10)
        saved_rules = config.get('routing_rules', [])
        if saved_rules:
            for rule in saved_rules:
                self._add_rule_row(rule.get('keywords', ''), rule.get('output_port', ''))
        else:
            self._add_rule_row("sukses, berhasil, success", "output_sukses")
    def _add_rule_row(self, keywords="", output_port=""):
        row_frame = ttk.Frame(self.rules_list_frame)
        row_frame.pack(fill='x', padx=10, pady=3)
        keywords_var = StringVar(value=keywords)
        output_var = StringVar(value=output_port)
        ttk.Entry(row_frame, textvariable=keywords_var).pack(side='left', expand=True, fill='x')
        ttk.Entry(row_frame, textvariable=output_var).pack(side='left', expand=True, fill='x', padx=(5,5))
        def _remove_row():
            row_to_remove = next((row for row in self.rule_rows if row['frame'] == row_frame), None)
            if row_to_remove:
                row_frame.destroy()
                self.rule_rows.remove(row_to_remove)
        ttk.Button(row_frame, text="X", command=_remove_row, bootstyle="danger", width=2).pack(side='left')
        self.rule_rows.append({'frame': row_frame, 'keywords': keywords_var, 'output_port': output_var})
    def get_routing_rules(self):
        """Gathers the rules from the UI into a list of dictionaries."""
        rules_list = []
        for row in self.rule_rows:
            keywords = row['keywords'].get().strip()
            output_port = row['output_port'].get().strip().replace(" ", "_")
            if keywords and output_port:
                rules_list.append({'keywords': keywords, 'output_port': output_port})
        return rules_list
class KeywordRouterModule(BaseModule, IExecutable, IConfigurableUI, IDynamicPorts):
    TIER = "free"  # ADDED BY SCANNER: Default tier
    def get_dynamic_ports(self, current_config):
        ports = []
        rules = current_config.get('routing_rules', [])
        port_names = sorted(list(set(rule['output_port'] for rule in rules if rule.get('output_port'))))
        for port_name in port_names:
            ports.append({
                "name": port_name,
                "display_name": port_name.replace("_", " ").title()
            })
        ports.append({
            "name": "default_output",
            "display_name": self.loc.get('keyword_router_default_port', fallback="Default / No Match")
        })
        return ports
    def execute(self, payload, config, status_updater, ui_callback, mode='EXECUTE'):
        input_variable = config.get('input_variable', 'data.prompt')
        routing_rules = config.get('routing_rules', [])
        input_text = get_nested_value(payload, input_variable)
        if not isinstance(input_text, str):
            status_updater(f"Input at '{input_variable}' is not text. Cannot route.", "WARN")
            return {"payload": payload, "output_name": "default_output"}
        input_text_lower = input_text.lower()
        for rule in routing_rules:
            keywords_str = rule.get('keywords', '').lower()
            output_port = rule.get('output_port')
            if not keywords_str or not output_port:
                continue
            keywords = [kw.strip() for kw in keywords_str.split(',')]
            if any(keyword in input_text_lower for keyword in keywords if keyword):
                status_updater(f"Keyword match found. Routing to '{output_port}'.", "SUCCESS")
                return {"payload": payload, "output_name": output_port}
        status_updater("No keyword match found. Using default route.", "INFO")
        return {"payload": payload, "output_name": "default_output"}
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        config = get_current_config()
        ui_frame = _KeywordRouterPropertiesUI(parent_frame, self.loc, config, available_vars)
        ui_frame.pack(fill='both', expand=True)
        class RulesVar:
            def __init__(self, ui): self.ui = ui
            def get(self): return self.ui.get_routing_rules()
        class InputVar:
            def __init__(self, ui): self.ui = ui
            def get(self): return self.ui.input_var.get()
        return {
            'input_variable': InputVar(ui_frame),
            'routing_rules': RulesVar(ui_frame)
        }
