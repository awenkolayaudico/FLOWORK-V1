#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\prompt_engineer_module_a1b2\processor.py
# JUMLAH BARIS : 91
#######################################################################

import ttkbootstrap as ttk
from tkinter import StringVar, scrolledtext
from flowork_kernel.api_contract import BaseModule, IExecutable, IConfigurableUI, IDataPreviewer
from flowork_kernel.ui_shell import shared_properties
from flowork_kernel.ui_shell.components.LabelledCombobox import LabelledCombobox
from flowork_kernel.utils.payload_helper import get_nested_value
import json
class PromptEngineerModule(BaseModule, IExecutable, IConfigurableUI, IDataPreviewer):
    """
    (REMASTERED) This module no longer calls an AI. It acts as a powerful
    text formatter. It takes a prompt template from its properties and injects
    variables from the payload to create a final, ready-to-use prompt for an Agent Host.
    """
    TIER = "free"
    DEFAULT_TEMPLATE = """You are an autonomous AI agent running inside the Flowork platform. Your goal is to achieve the user's objective by thinking step-by-step and using the available tools.
**RULES:**
1.  **Analyze the Observation:** Carefully examine the 'Current Observation'. If the last action failed, your 'thought' must be to figure out *why* it failed and your 'action' must be to try a **different approach**.
2.  **JSON ONLY:** Your entire response MUST be a single, valid JSON object.
3.  **TOOL USAGE IS CRITICAL:** When you decide on an action, you MUST provide the necessary inputs for that tool inside the `action.data` part of your JSON.
4.  **FINISH THE JOB:** When the objective is complete, use the special tool `finish`.
**USER'S OBJECTIVE:** {objective}
**AVAILABLE TOOLS:**
---
{tools_string}
---
**HISTORY (Previous thoughts and observations):**
{history}
**Current Observation (Result of the last action):**
---
{last_observation}
---
Based on all the information above, what is your next thought and action?
Your JSON Response:
"""
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
    def execute(self, payload: dict, config: dict, status_updater, ui_callback, mode='EXECUTE'):
        input_variable = config.get('input_variable', 'data.prompt')
        prompt_template = config.get('prompt_template', self.DEFAULT_TEMPLATE)
        simple_command = get_nested_value(payload, input_variable)
        if not simple_command:
            simple_command = "No objective provided."
        status_updater("Formatting final prompt...", "INFO")
        final_prompt = prompt_template.format(
            objective=simple_command,
            tools_string="{tools_string}",
            history="{history}",
            last_observation="{last_observation}"
        )
        if 'data' not in payload or not isinstance(payload['data'], dict):
            payload['data'] = {}
        payload['data']['final_prompt'] = final_prompt
        status_updater("Prompt successfully engineered.", "SUCCESS")
        return {"payload": payload, "output_name": "success"}
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        config = get_current_config()
        property_vars = {}
        property_vars['input_variable'] = StringVar(value=config.get('input_variable', 'data.prompt'))
        LabelledCombobox(
            parent=parent_frame,
            label_text=self.loc.get('prop_engineer_input_var_label', fallback="Simple Command Variable:"),
            variable=property_vars['input_variable'],
            values=list(available_vars.keys())
        )
        ttk.Label(parent_frame, text=self.loc.get('prop_engineer_template_label', fallback="Prompt Template:")).pack(fill='x', padx=5, pady=(10, 0))
        template_editor = scrolledtext.ScrolledText(parent_frame, height=15, font=("Consolas", 9))
        template_editor.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        template_editor.insert('1.0', config.get('prompt_template', self.DEFAULT_TEMPLATE.strip()))
        property_vars['prompt_template'] = template_editor
        ttk.Label(parent_frame, text=self.loc.get('prop_engineer_template_help', fallback="The Agent Executor will automatically fill {{tools_string}}, {{history}}, and {{last_observation}}."), wraplength=400, justify='left', style='secondary.TLabel').pack(fill='x', padx=5, pady=(0, 10))
        ttk.Separator(parent_frame).pack(fill='x', pady=15, padx=5)
        debug_vars = shared_properties.create_debug_and_reliability_ui(parent_frame, config, self.loc)
        property_vars.update(debug_vars)
        return property_vars
    def get_dynamic_output_schema(self, config):
        return [
            {
                "name": "data.final_prompt",
                "type": "string",
                "description": "The final, formatted prompt template ready for the Agent Host."
            }
        ]
    def get_data_preview(self, config: dict):
        return [{'status': 'preview not implemented'}]
