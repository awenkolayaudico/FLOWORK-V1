#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\ai_center_module\processor.py
# JUMLAH BARIS : 163
#######################################################################

import ttkbootstrap as ttk
from tkinter import StringVar
from flowork_kernel.api_contract import BaseModule, IExecutable, IConfigurableUI
from flowork_kernel.ui_shell import shared_properties
from flowork_kernel.ui_shell.components.LabelledCombobox import LabelledCombobox
from flowork_kernel.ui_shell.components.InfoLabel import InfoLabel
from flowork_kernel.utils.payload_helper import get_nested_value
from flowork_kernel.api_contract import IDataPreviewer
import os
import json
try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
class AICenterModule(BaseModule, IExecutable, IConfigurableUI, IDataPreviewer):
    TIER = "free"
    TASK_CATEGORIES = {
        "TEXT_GENERATION": "prop_aicenter_task_text",
        "IMAGE_GENERATION": "prop_aicenter_task_image",
        "AUDIO_GENERATION": "prop_aicenter_task_audio",
        "VIDEO_GENERATION": "prop_aicenter_task_video",
        "CODE_GENERATION": "prop_aicenter_task_code",
        "DATA_ANALYSIS": "prop_aicenter_task_data"
    }
    _local_hf_pipelines = {}
    _local_gguf_models = {}
    def execute(self, payload, config, status_updater, ui_callback, mode='EXECUTE'):
        prompt = ""
        prompt_source_variable = config.get('prompt_source_variable')
        if prompt_source_variable:
            prompt = get_nested_value(payload, prompt_source_variable)
            self.logger(f"AI Center: Got prompt from dynamic variable: '{prompt_source_variable}'", "DEBUG") # English Log
        if not prompt:
            payload_data = payload.get('data', {})
            if isinstance(payload_data, dict):
                possible_keys = ['prompt', 'konten', 'message', 'text', 'data']
                for key in possible_keys:
                    if key in payload_data and payload_data[key]:
                        prompt = payload_data[key]
                        break
            elif isinstance(payload_data, str):
                prompt = payload_data
        if not prompt:
            error_msg = "Could not find a valid prompt in the payload from any source."
            self.logger(error_msg, "ERROR") # English Log
            status_updater("Error: Prompt not found", "ERROR") # English Log
            if 'data' not in payload or not isinstance(payload.get('data'), dict):
                payload['data'] = {}
            payload['data']['error'] = error_msg
            return {"payload": payload, "output_name": "default_output"}
        status_updater("Analyzing prompt intent...", "INFO") # English Log
        task_category = None
        prompt_lower = prompt.lower()
        keyword_map = {
            "AUDIO_GENERATION": ["musik", "lagu", "sound", "audio", "aransemen"],
            "IMAGE_GENERATION": ["gambar", "lukisan", "image", "foto", "ilustrasi", "logo"],
            "VIDEO_GENERATION": ["video", "film", "klip", "animasi"],
            "CODE_GENERATION": ["kode", "script", "program", "function", "fungsi", "class"],
            "DATA_ANALYSIS": ["analisa", "data", "csv", "json", "laporan", "statistik"]
        }
        for category, keywords in keyword_map.items():
            if any(keyword in prompt_lower for keyword in keywords):
                task_category = category
                self.logger(f"Keyword match found. Classified as: {task_category}", "INFO") # English Log
                break
        if not task_category:
            task_category = "TEXT_GENERATION"
            self.logger("No keyword match. Defaulting to TEXT_GENERATION.", "INFO") # English Log
        status_updater(f"Task classified as: {task_category}", "INFO") # English Log
        provider_mapping = config.get('provider_mapping', {})
        target_endpoint_id = provider_mapping.get(task_category)
        if not target_endpoint_id:
            self.logger(f"No specific provider mapping in node config for task '{task_category}'. Falling back to global settings.", "INFO") # English Log
            target_endpoint_id = None
        result = None
        ai_manager = self.kernel.get_service("ai_provider_manager_service")
        if not ai_manager:
            raise RuntimeError("AIProviderManagerService not available.")
        log_endpoint = target_endpoint_id if target_endpoint_id else "Default System AI"
        status_updater(f"Delegating to endpoint '{log_endpoint}'...", "INFO") # English Log
        result = ai_manager.query_ai_by_task(task_category.split('_')[0].lower(), prompt, endpoint_id=target_endpoint_id)
        if "error" in result:
             raise RuntimeError(f"AI endpoint '{log_endpoint}' returned an error: {result['error']}")
        result_type = result.get('type', 'text').lower()
        result_data = result.get('data')
        if 'data' not in payload or not isinstance(payload.get('data'), dict):
             payload['data'] = {}
        payload['data'][f'ai_result_{result_type}'] = result_data
        payload['data']['prompt'] = prompt
        output_port_map = {
            'text': 'text_output',
            'image_url': 'image_output',
            'audio_file': 'audio_output',
            'video_url': 'video_output',
            'code': 'code_output',
            'json': 'data_output'
        }
        output_name = output_port_map.get(result_type, 'default_output')
        status_updater("Task completed!", "SUCCESS") # English Log
        return {"payload": payload, "output_name": output_name}
    def _get_all_available_endpoints(self):
        ai_manager = self.kernel.get_service("ai_provider_manager_service")
        if ai_manager:
            return ai_manager.get_available_providers()
        return {}
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        config = get_current_config()
        property_vars = {}
        prompt_source_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('prop_aicenter_input_source_title', fallback="Input Source"))
        prompt_source_frame.pack(fill='x', padx=5, pady=10)
        property_vars['prompt_source_variable'] = StringVar(value=config.get('prompt_source_variable', 'data.prompt'))
        LabelledCombobox(
            parent=prompt_source_frame,
            label_text=self.loc.get('prop_aicenter_prompt_from', fallback="Use Prompt From Variable:"),
            variable=property_vars['prompt_source_variable'],
            values=list(available_vars.keys())
        )
        main_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('prop_aicenter_control_cockpit_title', fallback="AI Center Control Cockpit"))
        main_frame.pack(fill='x', padx=5, pady=10)
        all_endpoints_raw = self._get_all_available_endpoints()
        id_to_display_map = {id: name for id, name in all_endpoints_raw.items()}
        display_to_id_map = {name: id for id, name in all_endpoints_raw.items()}
        endpoint_display_list = sorted(list(display_to_id_map.keys()))
        mapping_data = config.get('provider_mapping', {})
        category_vars = {}
        for category, loc_key in self.TASK_CATEGORIES.items():
            provider_var = StringVar()
            saved_endpoint_id = mapping_data.get(category)
            if saved_endpoint_id and saved_endpoint_id in id_to_display_map:
                provider_var.set(id_to_display_map[saved_endpoint_id])
            LabelledCombobox(parent=main_frame, label_text=f"{self.loc.get(loc_key, fallback=category.replace('_',' ').title())}:", variable=provider_var, values=endpoint_display_list)
            category_vars[category] = provider_var
        class MappingVar:
            def __init__(self, vars_dict, name_map):
                self.vars_dict = vars_dict
                self.name_map = name_map
            def get(self):
                mapping = {}
                for category, tk_var in self.vars_dict.items():
                    selected_name = tk_var.get()
                    if selected_name:
                        mapping[category] = self.name_map.get(selected_name)
                return mapping
        property_vars['provider_mapping'] = MappingVar(category_vars, display_to_id_map)
        debug_vars = shared_properties.create_debug_and_reliability_ui(parent_frame, config, self.loc)
        property_vars.update(debug_vars)
        return property_vars
    def get_data_preview(self, config: dict):
        self.logger(f"'get_data_preview' is not yet implemented for {self.module_id}", 'WARN') # English Log
        return [{'status': 'preview not implemented'}]
