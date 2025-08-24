#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\sleep_module\processor.py
# JUMLAH BARIS : 98
#######################################################################

import time
import random
from flowork_kernel.api_contract import BaseModule, IExecutable, IConfigurableUI, IDataPreviewer
from flowork_kernel.ui_shell import shared_properties
import ttkbootstrap as ttk
from tkinter import StringVar, IntVar
class Processor(BaseModule, IExecutable, IConfigurableUI, IDataPreviewer):
    """
    Processor for the Sleep module. Pauses execution for a static or random duration.
    [REFACTORED] Updated to align with modern architecture and full localization.
    """
    TIER = "free"
    def __init__(self, module_id: str, services: dict):
        super().__init__(module_id, services)
    def execute(self, payload, config, status_updater, ui_callback, mode='EXECUTE'):
        sleep_type = config.get('sleep_type', 'static')
        duration = 0.0
        log_msg = ""
        if sleep_type == 'random_range':
            try:
                min_val = int(config.get('random_min', 1))
                max_val = int(config.get('random_max', 10))
                if min_val > max_val:
                    min_val, max_val = max_val, min_val # Swap if min is greater than max
                duration = random.uniform(min_val, max_val)
                log_msg = self.loc.get('log_sleep_random', min_val=min_val, max_val=max_val, duration=duration)
            except (ValueError, TypeError):
                duration = random.uniform(1, 10)
                log_msg = f"Sleeping randomly (config error) for {duration:.2f} seconds..."
        else: # Default to static
            try:
                duration = int(config.get("duration_seconds", 3))
            except (ValueError, TypeError):
                duration = 3
            log_msg = self.loc.get('log_sleep_static', duration=duration, fallback=f"Sleeping for {duration} seconds...")
        if mode == 'EXECUTE':
            self.logger(log_msg, "INFO")
            for i in range(int(duration), 0, -1):
                countdown_msg = self.loc.get('status_sleep_countdown', seconds=i)
                status_updater(countdown_msg, "INFO")
                time.sleep(1)
            remaining_sleep = duration - int(duration)
            if remaining_sleep > 0:
                time.sleep(remaining_sleep)
            status_updater(self.loc.get('status_sleep_finished', fallback="Sleep finished!"), "SUCCESS")
            self.logger(self.loc.get('log_sleep_finished', fallback="Sleep complete, resuming workflow."), "INFO")
        else: # SIMULATE mode
            status_updater(self.loc.get('status_sleep_simulating', duration=duration), "WARN")
        return payload
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        config = get_current_config()
        created_vars = {}
        main_props_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('prop_sleep_title', fallback="Sleep Configuration"))
        main_props_frame.pack(fill='x', padx=5, pady=(5, 10), expand=True)
        options_frame = ttk.Frame(main_props_frame, padding=(10, 5))
        options_frame.pack(fill='x', expand=True)
        created_vars['sleep_type'] = StringVar(value=config.get('sleep_type', 'static'))
        static_frame = ttk.Frame(options_frame)
        random_frame = ttk.Frame(options_frame)
        def _toggle_details(*args):
            if created_vars['sleep_type'].get() == 'static':
                static_frame.pack(fill='x', pady=(5,0), padx=15)
                random_frame.pack_forget()
            else:
                static_frame.pack_forget()
                random_frame.pack(fill='x', pady=(5,0), padx=15)
        ttk.Radiobutton(options_frame, text=self.loc.get('sleep_type_static_radio'), variable=created_vars['sleep_type'], value='static', command=_toggle_details).pack(anchor='w')
        ttk.Radiobutton(options_frame, text=self.loc.get('sleep_type_random_radio'), variable=created_vars['sleep_type'], value='random_range', command=_toggle_details).pack(anchor='w')
        ttk.Label(static_frame, text=self.loc.get('sleep_duration_label')).pack(side='left', padx=(0,5))
        created_vars['duration_seconds'] = IntVar(value=config.get('duration_seconds', 3))
        ttk.Entry(static_frame, textvariable=created_vars['duration_seconds'], width=5).pack(side='left')
        ttk.Label(random_frame, text=self.loc.get('random_min_label')).pack(side='left', padx=(0,5))
        created_vars['random_min'] = IntVar(value=config.get('random_min', 1))
        ttk.Entry(random_frame, textvariable=created_vars['random_min'], width=5).pack(side='left', padx=5)
        ttk.Label(random_frame, text=self.loc.get('random_max_label')).pack(side='left', padx=(10,5))
        created_vars['random_max'] = IntVar(value=config.get('random_max', 10))
        ttk.Entry(random_frame, textvariable=created_vars['random_max'], width=5).pack(side='left')
        _toggle_details()
        debug_vars = shared_properties.create_debug_and_reliability_ui(parent_frame, config, self.loc)
        created_vars.update(debug_vars)
        return created_vars
    def get_data_preview(self, config: dict):
        """
        This module doesn't alter data, so it provides a simple status message.
        """
        sleep_type = config.get('sleep_type', 'static')
        if sleep_type == 'random_range':
            duration_text = f"random {config.get('random_min', 1)}-{config.get('random_max', 10)}s"
        else:
            duration_text = f"{config.get('duration_seconds', 3)}s"
        return [{'status': 'pauses execution', 'duration': duration_text}]
