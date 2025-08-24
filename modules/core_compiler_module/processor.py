#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\core_compiler_module\processor.py
# JUMLAH BARIS : 233
#######################################################################

import ttkbootstrap as ttk
from tkinter import StringVar
import os
import json
import re
from flowork_kernel.api_contract import BaseModule, IExecutable, IConfigurableUI
class CoreCompilerModule(BaseModule, IExecutable, IConfigurableUI):
    TIER = "free"
    """
    Implements the "Compile Core" functionality described in the manifesto.
    """
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
        self.core_services_path = os.path.join(self.kernel.project_root_path, "core_services")
        self.output_path = os.path.join(self.kernel.project_root_path, "generated_services")
        os.makedirs(self.output_path, exist_ok=True)
    def execute(self, payload: dict, config: dict, status_updater, ui_callback, mode='EXECUTE'):
        service_filename = config.get('service_to_compile')
        if service_filename == 'core_lifecycle.flowork':
            message = "Skipping compilation: 'core_lifecycle.flowork' is a special bootstrap workflow, not a standard service."
            self.logger(message, "WARN")
            status_updater("Skipped (Bootstrap File)", "INFO")
            if not isinstance(payload, dict) or 'data' not in payload or not isinstance(payload.get('data'), dict):
                self.logger("Payload 'data' is not a dict. Reconstructing payload structure.", "DEBUG")
                payload = {'data': {}, 'history': payload.get('history', [])}
            payload['data']['compilation_status'] = message
            return {"payload": payload, "output_name": "success"}
        if not service_filename:
            error_msg = "No service was selected to be compiled."
            status_updater(error_msg, "ERROR")
            payload['error'] = error_msg
            return {"payload": payload, "output_name": "error"}
        status_updater(f"Starting compilation for {service_filename}...", "INFO")
        self.logger(f"--- CORE COMPILER INITIATED FOR: {service_filename} ---", "SUCCESS")
        flowork_path = os.path.join(self.core_services_path, service_filename)
        with open(flowork_path, 'r', encoding='utf-8') as f:
            workflow_data = json.load(f)
        self.logger("Step 1/5: Read service workflow file... SUCCESS", "INFO")
        status_updater("Reading visual workflow...", "INFO")
        nodes = {node['id']: node for node in workflow_data.get('nodes', [])}
        connections = workflow_data.get('connections', [])
        start_node_ids = set(nodes.keys()) - {c['to'] for c in connections if c.get('to')}
        translated_methods = []
        for node_id in start_node_ids:
            start_node = nodes.get(node_id)
            if start_node:
                method_code = self._translate_flow_to_method(start_node, nodes, connections)
                if method_code:
                    translated_methods.append(method_code)
        self.logger("Step 2/5: Translating flows to Python code... SUCCESS", "INFO")
        status_updater("Translating logic...", "INFO")
        class_name_base = service_filename.replace('.flowork', '')
        class_name = "".join(word.capitalize() for word in class_name_base.replace('_', ' ').split())
        if not class_name.endswith("Service"):
             class_name += "Service"
        full_python_code = self._generate_class_string(class_name, class_name_base, translated_methods)
        self.logger("Step 3/5: Generating new .py service file... SUCCESS", "INFO")
        status_updater("Generating Python file...", "INFO")
        output_subfolder = os.path.join(self.output_path, f"{class_name_base}_service")
        os.makedirs(output_subfolder, exist_ok=True)
        output_filepath = os.path.join(output_subfolder, "service.py")
        with open(output_filepath, 'w', encoding='utf-8') as f:
            f.write(full_python_code)
        self.logger(f"Step 4/5: New service file saved to '{output_filepath}'", "SUCCESS")
        status_updater("Updating service manifest...", "INFO")
        try:
            services_json_path = os.path.join(self.kernel.project_root_path, "flowork_kernel", "services.json")
            self.logger(f"Step 5/5: Attempting to auto-update '{services_json_path}'...", "INFO")
            with open(services_json_path, 'r', encoding='utf-8') as f:
                services_data = json.load(f)
            service_id_to_update = None
            target_preset_path = f"core_services/{service_filename}"
            for service_entry in services_data['services']:
                if service_entry.get('preset_path') == target_preset_path:
                    service_id_to_update = service_entry.get('id')
                    self.logger(f"Match found via 'preset_path'. Target Service ID is '{service_id_to_update}'.", "DEBUG")
                    break
                if service_entry.get('source_workflow') == target_preset_path:
                    service_id_to_update = service_entry.get('id')
                    self.logger(f"Match found via 'source_workflow' trail. Target Service ID is '{service_id_to_update}'.", "DEBUG")
                    break
            if not service_id_to_update:
                error_msg = f"Could not find any service in services.json that uses the preset '{target_preset_path}'."
                self.logger(error_msg, "ERROR")
                raise ValueError(error_msg)
            service_found_and_updated = False
            for i, service_entry in enumerate(services_data['services']):
                if service_entry['id'] == service_id_to_update:
                    self.logger(f"Found service entry for '{service_id_to_update}'. Updating...", "DEBUG")
                    new_path_base = os.path.basename(output_subfolder)
                    new_service_entry = {
                        "id": service_id_to_update,
                        "path": f"generated_services.{new_path_base}.service",
                        "class": class_name,
                        "source_workflow": target_preset_path
                    }
                    services_data['services'][i] = new_service_entry
                    service_found_and_updated = True
                    break
            if not service_found_and_updated:
                 self.logger(f"Service entry for '{service_id_to_update}' not found in services.json. Cannot update automatically.", "ERROR")
                 raise ValueError(f"Service ID '{service_id_to_update}' not found in manifest during update phase.")
            with open(services_json_path, 'w', encoding='utf-8') as f:
                json.dump(services_data, f, indent=4)
            self.logger(f"Step 5/5: Successfully updated '{services_json_path}'.", "SUCCESS")
        except Exception as e:
            error_msg = f"Core Compiler failed at Step 5 (updating services.json): {e}"
            self.logger(error_msg, "CRITICAL")
            status_updater(f"Failed to update services.json: {e}", "ERROR")
            payload['error'] = error_msg
            return {"payload": payload, "output_name": "error"}
        status_updater("Compilation complete!", "SUCCESS")
        if not isinstance(payload, dict): payload = {'data': {}}
        if 'data' not in payload or not isinstance(payload['data'], dict): payload['data'] = {}
        payload['data']['compiled_service'] = service_filename
        payload['data']['output_path'] = output_filepath
        return {"payload": payload, "output_name": "success"}
    def _generate_class_string(self, class_name, service_id, methods):
        methods_str = "\n\n".join(methods)
        template = """# THIS FILE WAS AUTO-GENERATED BY THE FLOWORK CORE COMPILER
from flowork_kernel.services.base_service import BaseService
import os
import json
import importlib.util
import shutil
import datetime
class {class_name}(BaseService):
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.logger = self.kernel.write_to_log
{methods_str}
"""
        return template.format(service_id=service_id, class_name=class_name, methods_str=methods_str)
    def _translate_flow_to_method(self, start_node, all_nodes, all_connections):
        method_name_raw = start_node.get('name')
        if not method_name_raw: return ""
        method_name = method_name_raw.replace(' ', '_')
        header = f"    def {method_name}(self, *args, **kwargs):"
        code_lines = [
            header,
            "        # This entire method was translated from a visual workflow.",
            "        kernel = self.kernel",
            "        log = self.logger",
            "        payload = {'data': {'args': args, 'kwargs': kwargs}, 'history': []}",
            "        # Dictionary to store results of each node",
            "        node_results = {}",
            ""
        ]
        flow_map = {node_id: [] for node_id in all_nodes}
        for conn in all_connections:
            if conn.get('from'):
                flow_map[conn['from']].append(conn)
        in_degree = {i: 0 for i in all_nodes}
        for conn in all_connections:
            if conn.get('to'):
                in_degree[conn['to']] += 1
        queue = [start_node['id']]
        exec_order = []
        visited_nodes = set()
        while queue:
            u = queue.pop(0)
            if u in visited_nodes:
                continue
            visited_nodes.add(u)
            exec_order.append(u)
            for conn in flow_map.get(u, []):
                v = conn['to']
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)
        for node_id in exec_order:
            node_info = all_nodes[node_id]
            node_name = node_info.get("name", "Unnamed Node")
            incoming_conns = [c for c in all_connections if c.get('to') == node_id]
            if not incoming_conns:
                input_payload_var = "payload"
            else:
                prev_node_id = incoming_conns[0]['from']
                input_payload_var = f"node_results.get('{prev_node_id}')"
            code_lines.append(f"        # --- Executing Node: {node_name} ---")
            code_lines.append(f"        try:")
            code_lines.append(f"            current_payload = {input_payload_var}")
            code_lines.append(self._get_node_execution_code(node_info, "current_payload", "            "))
            code_lines.append(f"        except Exception as e:")
            code_lines.append(f"            self.logger(f'Error executing node {node_name}: {{e}}', 'ERROR')")
            code_lines.append(f"            return None # Or handle error appropriately")
            code_lines.append("")
        if exec_order:
            final_node_id = exec_order[-1]
            final_result_var = f"node_results.get('{final_node_id}')"
            code_lines.append("        # Return the result from the final node in the flow")
            code_lines.append(f"        return {final_result_var}")
        else:
            code_lines.append("        return payload")
        return "\n".join(code_lines)
    def _get_node_execution_code(self, node_info, input_payload_var, indent_str):
        node_id = node_info['id']
        module_id = node_info['module_id']
        config = node_info.get('config_values', {})
        if module_id == 'function_runner_module':
            user_code = config.get('python_code', '')
            code_block = [f"{indent_str}def temp_func(payload, log, kernel, args, json, os, importlib):"]
            function_body_indent = indent_str + "    "
            if not user_code.strip():
                code_block.append(f"{function_body_indent}pass")
            else:
                for line in user_code.splitlines():
                    code_block.append(f"{function_body_indent}{line}")
            code_block.append(f"{indent_str}node_results['{node_id}'] = temp_func({input_payload_var}, log, kernel, {input_payload_var}.get('data',{{}}).get('args', []), json, os, importlib.util)")
            return "\n".join(code_block)
        elif module_id == 'set_variable_module':
            return f"{indent_str}log('Node {node_info['name']} executed (set_variable_module)', 'DEBUG')\n{indent_str}node_results['{node_id}'] = {input_payload_var}"
        else: # Fallback for unknown modules
            return (f"{indent_str}log('Node {node_info['name']} ({module_id}) is not fully translatable yet.', 'WARN')\n"
                    f"{indent_str}node_results['{node_id}'] = {input_payload_var}")
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        config = get_current_config()
        property_vars = {}
        ttk.Label(parent_frame, text=self.loc.get('compiler_select_service', fallback="Service Workflow to Compile:")).pack(fill='x', padx=5, pady=(5,0))
        service_var = StringVar(value=config.get('service_to_compile'))
        property_vars['service_to_compile'] = service_var
        service_files = []
        if os.path.isdir(self.core_services_path):
            service_files = [f for f in os.listdir(self.core_services_path) if f.endswith(".flowork")]
        ttk.Combobox(parent_frame, textvariable=service_var, values=sorted(service_files), state='readonly').pack(fill='x', padx=5, pady=(0, 5))
        return property_vars
