#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\nuitka_compiler_module_b4a1\processor.py
# JUMLAH BARIS : 131
#######################################################################

import os
import sys
import subprocess
import shutil
import ttkbootstrap as ttk
from tkinter import StringVar, BooleanVar, filedialog
from flowork_kernel.api_contract import BaseModule, IExecutable, IConfigurableUI, IDataPreviewer
from flowork_kernel.ui_shell import shared_properties
from flowork_kernel.utils.payload_helper import get_nested_value
from flowork_kernel.ui_shell.components.LabelledCombobox import LabelledCombobox
class NuitkaCompilerModule(BaseModule, IExecutable, IConfigurableUI, IDataPreviewer):
    """
    Module to compile a Python file into a .pyd extension using Nuitka.
    """
    TIER = "free"
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
        self.nuitka_available = None
    def _check_nuitka(self):
        if self.nuitka_available is None:
            try:
                subprocess.run([sys.executable, '-m', 'nuitka', '--version'], check=True, capture_output=True)
                self.nuitka_available = True
                self.logger("Nuitka installation confirmed in the current environment.", "SUCCESS")
            except (subprocess.CalledProcessError, FileNotFoundError):
                self.nuitka_available = False
                self.logger("Nuitka is not installed or accessible in the current Python environment.", "ERROR")
        return self.nuitka_available
    def execute(self, payload: dict, config: dict, status_updater, ui_callback, mode='EXECUTE'):
        if not self._check_nuitka():
            raise RuntimeError("Nuitka is not installed. Please run 'pip install nuitka' in your environment.")
        source_py_variable = config.get('source_py_path', '')
        output_directory = config.get('output_directory', '')
        remove_source = config.get('remove_source', False)
        source_py_file = get_nested_value(payload, source_py_variable)
        if not source_py_file or not os.path.isfile(source_py_file):
            error_msg = f"Source file not found or path is invalid. Path from '{source_py_variable}': {source_py_file}"
            status_updater(error_msg, "ERROR")
            payload['error'] = error_msg
            return {"payload": payload, "output_name": "error"}
        final_output_dir = output_directory if output_directory and os.path.isdir(output_directory) else os.path.dirname(source_py_file)
        status_updater(f"Compiling '{os.path.basename(source_py_file)}'...", "INFO")
        self.logger(f"Starting Nuitka compilation for: {source_py_file}", "INFO")
        command = [
            sys.executable, '-m', 'nuitka', '--module', source_py_file,
            f'--output-dir={final_output_dir}', '--remove-output', '--plugin-enable=tk-inter'
        ]
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True, cwd=self.kernel.project_root_path)
            self.logger(f"Nuitka stdout:\n{result.stdout}", "DEBUG")
            module_name = os.path.splitext(os.path.basename(source_py_file))[0]
            compiled_file = next((f for f in os.listdir(final_output_dir) if f.startswith(module_name) and (f.endswith('.pyd') or f.endswith('.so'))), None)
            if not compiled_file:
                raise RuntimeError("Nuitka ran, but the compiled output file could not be found.")
            compiled_file_path = os.path.join(final_output_dir, compiled_file)
            if remove_source:
                os.remove(source_py_file)
                self.logger(f"Source file '{source_py_file}' removed as requested.", "WARN")
                status_updater("Source file removed.", "INFO")
            if 'data' not in payload or not isinstance(payload['data'], dict):
                payload['data'] = {}
            payload['data']['compiled_path'] = compiled_file_path
            status_updater(f"Compilation successful: {compiled_file}", "SUCCESS")
            return {"payload": payload, "output_name": "success"}
        except subprocess.CalledProcessError as e:
            error_msg = f"Nuitka compilation failed. Stderr:\n{e.stderr}"
            self.logger(error_msg, "ERROR")
            payload['error'] = error_msg
            return {"payload": payload, "output_name": "error"}
        except Exception as e:
            error_msg = f"An unexpected error occurred during compilation: {e}"
            self.logger(error_msg, "ERROR")
            payload['error'] = error_msg
            return {"payload": payload, "output_name": "error"}
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        config = get_current_config()
        property_vars = {}
        property_vars['source_py_path'] = StringVar(value=config.get('source_py_path', 'data.source_file'))
        LabelledCombobox(
            parent=parent_frame,
            label_text=self.loc.get('prop_source_py_path_label', fallback="Source .py File (from Variable):"),
            variable=property_vars['source_py_path'],
            values=list(available_vars.keys())
        ).pack(fill='x', padx=5, pady=(10, 5))
        ttk.Label(parent_frame, text=self.loc.get('prop_output_dir_label', fallback="Output Directory:")).pack(fill='x', padx=5, pady=(5,0))
        output_frame = ttk.Frame(parent_frame)
        output_frame.pack(fill='x', padx=5, pady=(0, 5))
        property_vars['output_directory'] = StringVar(value=config.get('output_directory', ''))
        ttk.Entry(output_frame, textvariable=property_vars['output_directory']).pack(side='left', fill='x', expand=True)
        def _browse_folder():
            folder = filedialog.askdirectory(title="Select Output Directory")
            if folder:
                property_vars['output_directory'].set(folder)
        ttk.Button(output_frame, text="...", command=_browse_folder, width=4).pack(side='left', padx=(5,0))
        property_vars['remove_source'] = BooleanVar(value=config.get('remove_source', False))
        ttk.Checkbutton(
            parent_frame,
            text=self.loc.get('prop_remove_source_label', fallback="Delete Original .py After Compilation"),
            variable=property_vars['remove_source']
        ).pack(anchor='w', padx=5, pady=10)
        ttk.Separator(parent_frame).pack(fill='x', pady=15, padx=5)
        debug_vars = shared_properties.create_debug_and_reliability_ui(parent_frame, config, self.loc)
        property_vars.update(debug_vars)
        return property_vars
    def get_data_preview(self, config: dict):
        """
        Provides a sample of what this module might output. Compilation is too heavy for a live preview.
        """
        self.logger(f"'get_data_preview' for {self.module_id} provides a static example as live compilation is not feasible.", 'INFO')
        return {
            'compiled_path': '/path/to/your/compiled_file.pyd',
            'status': 'This is a static preview. The actual path will be generated upon execution.'
            }
    def get_dynamic_output_schema(self, config):
        """
        Defines the output structure of this module for other modules to see.
        """
        return [
            {
                "name": "data.compiled_path",
                "type": "string",
                "description": "The full local path to the newly compiled .pyd file."
            }
        ]
