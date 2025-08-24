#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\sentiment_analysis_module\processor.py
# JUMLAH BARIS : 132
#######################################################################

from flowork_kernel.api_contract import BaseModule, IExecutable, IConfigurableUI, IDataPreviewer
from flowork_kernel.utils.payload_helper import get_nested_value
from flowork_kernel.ui_shell.components.LabelledCombobox import LabelledCombobox
import ttkbootstrap as ttk
from tkinter import StringVar
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
class SentimentAnalysisModule(BaseModule, IExecutable, IConfigurableUI, IDataPreviewer):
    TIER = "free"
    def __init__(self, module_id: str, services: dict):
        super().__init__(module_id, services)
        self._local_hf_pipelines = {}
        self._local_gguf_models = {}
    def execute(self, payload: dict, config: dict, status_updater, ui_callback, mode='EXECUTE') -> dict:
        endpoint_id = config.get('selected_endpoint')
        if not endpoint_id:
            raise ValueError("No AI endpoint selected in node properties.")
        source_variable = config.get('source_variable', 'data.text')
        text_to_analyze = get_nested_value(payload, source_variable)
        if not text_to_analyze or not isinstance(text_to_analyze, str):
            raise ValueError(f"Input text not found or not a string at payload path: '{source_variable}'")
        status_updater(f"Analyzing sentiment using '{os.path.basename(endpoint_id)}'...", "INFO")
        result = None
        is_provider = endpoint_id in self.kernel.ai_manager.loaded_providers
        is_gguf = endpoint_id.endswith(".gguf")
        try:
            if is_provider:
                provider = self.kernel.ai_manager.get_provider(endpoint_id)
                prompt = f"Analyze the sentiment of the following text. Respond ONLY with a single word: POSITIVE, NEGATIVE, or NEUTRAL.\n\nText: \"{text_to_analyze}\""
                response = provider.generate_response(prompt)
                result = response.get('data', '').strip().upper()
            elif is_gguf:
                if not LLAMA_CPP_AVAILABLE: raise RuntimeError("Llama-cpp-python is required for GGUF models.")
                model_path_id = endpoint_id.replace("(Local Model) ", "")
                model_path = os.path.join(self.kernel.project_root_path, "ai_models", model_path_id)
                if model_path not in self._local_gguf_models:
                    status_updater("Loading GGUF model...", "INFO")
                    self._local_gguf_models[model_path] = Llama(model_path=model_path, n_ctx=2048, verbose=False, n_gpu_layers=-1)
                llm = self._local_gguf_models[model_path]
                prompt = f"Analyze the sentiment of the following text. Respond ONLY with a single word: POSITIVE, NEGATIVE, or NEUTRAL.\n\nText: \"{text_to_analyze}\""
                messages = [{"role": "user", "content": prompt}]
                response = llm.create_chat_completion(messages=messages, max_tokens=10)
                result = response['choices'][0]['message']['content'].strip().upper()
            else:
                if not TRANSFORMERS_AVAILABLE: raise RuntimeError("'transformers' library is required for local directory models.")
                model_path_id = endpoint_id.replace("(Local Model) ", "")
                model_path = os.path.join(self.kernel.project_root_path, "ai_models", model_path_id)
                if model_path not in self._local_hf_pipelines:
                    status_updater("Loading HF model...", "INFO")
                    self._local_hf_pipelines[model_path] = pipeline("sentiment-analysis", model=model_path)
                classifier = self._local_hf_pipelines[model_path]
                hf_result = classifier(text_to_analyze)
                result = hf_result[0]['label'].upper()
            if 'POSITIVE' in result or 'LABEL_1' in result: final_label = 'positive'
            elif 'NEGATIVE' in result or 'LABEL_0' in result: final_label = 'negative'
            else: final_label = 'neutral'
            if 'data' not in payload or not isinstance(payload['data'], dict):
                payload['data'] = {}
            payload['data']['sentiment_result'] = {'label': final_label, 'analyzed_text': text_to_analyze}
            status_updater(f"Result: {final_label.upper()}", "SUCCESS")
            return {"payload": payload, "output_name": final_label}
        except Exception as e:
            error_msg = f"An error occurred during sentiment analysis: {e}"
            self.logger(error_msg, "ERROR")
            status_updater("Analysis failed", "ERROR")
            if 'data' not in payload: payload['data'] = {}
            payload['data']['error'] = error_msg
            return {"payload": payload, "output_name": "error"}
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        config = get_current_config()
        property_vars = {}
        settings_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('sentiment_prop_title', fallback="Sentiment Settings"))
        settings_frame.pack(fill='x', padx=5, pady=10)
        ai_manager = self.kernel.get_service("ai_provider_manager_service")
        all_endpoints = ai_manager.get_available_providers() if ai_manager else {}
        name_to_id_map = {name: id for id, name in all_endpoints.items()}
        endpoint_display_list = sorted(list(name_to_id_map.keys()))
        property_vars['selected_endpoint_display'] = StringVar()
        saved_endpoint_id = config.get('selected_endpoint', '')
        if saved_endpoint_id:
            for display, eid in name_to_id_map.items():
                if eid == saved_endpoint_id:
                    property_vars['selected_endpoint_display'].set(display)
                    break
        LabelledCombobox(
            parent=settings_frame,
            label_text=self.loc.get('sentiment_prop_model_label', fallback="AI Model/Provider:"),
            variable=property_vars['selected_endpoint_display'],
            values=endpoint_display_list
        )
        property_vars['source_variable'] = StringVar(value=config.get('source_variable', 'data.text'))
        LabelledCombobox(
            parent=settings_frame,
            label_text=self.loc.get('sentiment_prop_source_label', fallback="Analyze Text From Variable:"),
            variable=property_vars['source_variable'],
            values=sorted(list(available_vars.keys()))
        )
        class EndpointVar:
            def __init__(self, tk_var, name_map):
                self.tk_var = tk_var
                self.name_map = name_map
            def get(self):
                return self.name_map.get(self.tk_var.get())
        property_vars['selected_endpoint'] = EndpointVar(property_vars['selected_endpoint_display'], name_to_id_map)
        return property_vars
    def get_data_preview(self, config: dict):
        return [{'status': 'preview_not_available', 'reason': 'AI analysis is a heavy process.'}]
    def get_dynamic_output_schema(self, config):
        return [
            {
                "name": "data.sentiment_result",
                "type": "object",
                "description": "A dictionary containing the sentiment label and the analyzed text."
            }
        ]
