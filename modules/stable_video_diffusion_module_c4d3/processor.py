#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\stable_video_diffusion_module_c4d3\processor.py
# JUMLAH BARIS : 157
#######################################################################

import os
import time
import ttkbootstrap as ttk
from tkinter import StringVar, IntVar, DoubleVar, filedialog
from flowork_kernel.api_contract import BaseModule, IExecutable, IConfigurableUI, IDataPreviewer
from flowork_kernel.ui_shell import shared_properties
from flowork_kernel.ui_shell.components.LabelledCombobox import LabelledCombobox
from flowork_kernel.utils.payload_helper import get_nested_value
try:
    import torch
    from diffusers import StableVideoDiffusionPipeline
    from diffusers.utils import load_image, export_to_video
    from PIL import Image
    DIFFUSERS_AVAILABLE = True
except ImportError:
    DIFFUSERS_AVAILABLE = False
class StableVideoDiffusionModule(BaseModule, IExecutable, IConfigurableUI, IDataPreviewer):
    """
    Module to generate video from a starting image using Stable Video Diffusion.
    [UPGRADED] The properties UI now dynamically detects available input variables from connected nodes.
    [FIXED] Now loads model from a local project path instead of downloading.
    """
    TIER = "free"
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
        self._pipeline = None  # Cache for the loaded pipeline
        self.output_dir = os.path.join(self.kernel.data_path, "generated_videos_svd")
        os.makedirs(self.output_dir, exist_ok=True)
        if not DIFFUSERS_AVAILABLE:
            self.logger("FATAL: 'diffusers', 'torch', or 'Pillow' library not found for SVD Module.", "CRITICAL")
    def _get_pipeline(self, status_updater):
        """
        Loads and configures the StableVideoDiffusionPipeline, caching it for reuse.
        """
        if self._pipeline:
            self.logger("Using cached SVD pipeline.", "INFO")
            return self._pipeline
        if not DIFFUSERS_AVAILABLE:
            raise RuntimeError("Required libraries (diffusers, torch, Pillow, accelerate) are not installed.")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cpu":
             self.logger("WARNING: Running SVD on CPU. This will be extremely slow.", "WARN")
        status_updater("Loading SVD model from local files...", "INFO")
        self.logger("Loading Stable Video Diffusion pipeline from project folder for the first time...", "WARN")
        model_path = os.path.join(self.kernel.project_root_path, "ai_models", "image", "stable-video-diffusion")
        if not os.path.isdir(model_path):
            raise FileNotFoundError(f"Local SVD model folder not found. Please ensure it exists at: {model_path}")
        pipe = StableVideoDiffusionPipeline.from_pretrained(
            model_path, # [FIX] Using local path, not downloading from the internet
            torch_dtype=torch.float16,
            variant="fp16"
        )
        pipe.to(device)
        if device == "cuda":
            pipe.enable_model_cpu_offload()
        self._pipeline = pipe
        self.logger("SVD Pipeline loaded and cached successfully from local files.", "SUCCESS")
        return self._pipeline
    def execute(self, payload: dict, config: dict, status_updater, ui_callback, mode='EXECUTE'):
        input_image_var = config.get('input_image_path', 'data.image_path')
        output_folder = config.get('output_folder', '').strip()
        num_frames = int(config.get('num_frames', 25))
        fps = int(config.get('fps', 7))
        motion_bucket_id = int(config.get('motion_bucket_id', 127))
        noise_aug = float(config.get('noise_aug_strength', 0.02))
        image_path = get_nested_value(payload, input_image_var)
        if not image_path or not isinstance(image_path, str) or not os.path.exists(image_path):
            error_msg = f"Input image path is invalid or file does not exist: '{image_path}'"
            status_updater(error_msg, "ERROR")
            payload['error'] = error_msg
            return {"payload": payload, "output_name": "error"}
        save_dir = output_folder if output_folder and os.path.isdir(output_folder) else self.output_dir
        try:
            pipeline = self._get_pipeline(status_updater)
            status_updater("Loading initial image...", "INFO")
            initial_image = load_image(image_path)
            initial_image = initial_image.resize((1024, 576))
            status_updater(f"Generating {num_frames} frames...", "INFO")
            self.logger(f"Starting SVD generation from image: '{os.path.basename(image_path)}'", "INFO")
            frames = pipeline(
                initial_image,
                decode_chunk_size=8,
                num_frames=num_frames,
                motion_bucket_id=motion_bucket_id,
                noise_aug_strength=noise_aug
            ).frames[0]
            status_updater("Saving video to MP4...", "INFO")
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"svd_video_{timestamp}.mp4"
            output_path = os.path.join(save_dir, filename)
            export_to_video(frames, output_path, fps=fps)
            self.logger(f"Video saved successfully to: {output_path}", "SUCCESS")
            if 'data' not in payload or not isinstance(payload['data'], dict):
                payload['data'] = {}
            payload['data']['video_path'] = output_path
            status_updater("Video generated successfully!", "SUCCESS")
            return {"payload": payload, "output_name": "success"}
        except Exception as e:
            self.logger(f"An error occurred during SVD generation: {e}", "ERROR")
            payload['error'] = str(e)
            return {"payload": payload, "output_name": "error"}
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        config = get_current_config()
        property_vars = {}
        input_frame = ttk.LabelFrame(parent_frame, text="Input & Output")
        input_frame.pack(fill='x', padx=5, pady=10)
        property_vars['input_image_path'] = StringVar(value=config.get('input_image_path', ''))
        LabelledCombobox(
            parent=input_frame,
            label_text="Input Image Variable:",
            variable=property_vars['input_image_path'],
            values=list(available_vars.keys())
        )
        dest_frame = ttk.Frame(input_frame)
        dest_frame.pack(fill='x', pady=5, padx=5)
        ttk.Label(dest_frame, text="Output Folder:").pack(anchor='w')
        entry_frame = ttk.Frame(dest_frame)
        entry_frame.pack(fill='x', expand=True, pady=(2,0))
        dest_var = StringVar(value=config.get('output_folder', ''))
        property_vars['output_folder'] = dest_var
        dest_entry = ttk.Entry(entry_frame, textvariable=dest_var)
        dest_entry.pack(side='left', fill='x', expand=True)
        def _browse_folder():
            folder_selected = filedialog.askdirectory(title="Select Output Folder")
            if folder_selected: dest_var.set(folder_selected)
        browse_button = ttk.Button(entry_frame, text="Browse...", command=_browse_folder)
        browse_button.pack(side='left', padx=(5,0))
        params_frame = ttk.LabelFrame(parent_frame, text="Generation Parameters")
        params_frame.pack(fill='x', padx=5, pady=5)
        params_grid = ttk.Frame(params_frame, padding=5)
        params_grid.pack(fill='x')
        params_grid.columnconfigure((1, 3), weight=1)
        ttk.Label(params_grid, text="Frames:").grid(row=0, column=0, sticky='w', pady=2)
        property_vars['num_frames'] = IntVar(value=config.get('num_frames', 25))
        ttk.Entry(params_grid, textvariable=property_vars['num_frames'], width=8).grid(row=0, column=1, sticky='ew', padx=5)
        ttk.Label(params_grid, text="FPS:").grid(row=0, column=2, sticky='w', padx=(10,0))
        property_vars['fps'] = IntVar(value=config.get('fps', 7))
        ttk.Entry(params_grid, textvariable=property_vars['fps'], width=8).grid(row=0, column=3, sticky='ew', padx=5)
        ttk.Label(params_grid, text="Motion Bucket ID:").grid(row=1, column=0, sticky='w', pady=2)
        property_vars['motion_bucket_id'] = IntVar(value=config.get('motion_bucket_id', 127))
        ttk.Entry(params_grid, textvariable=property_vars['motion_bucket_id'], width=8).grid(row=1, column=1, sticky='ew', padx=5)
        ttk.Label(params_grid, text="Noise Aug:").grid(row=1, column=2, sticky='w', padx=(10,0))
        property_vars['noise_aug_strength'] = DoubleVar(value=config.get('noise_aug_strength', 0.02))
        ttk.Entry(params_grid, textvariable=property_vars['noise_aug_strength'], width=8).grid(row=1, column=3, sticky='ew', padx=5)
        ttk.Separator(parent_frame).pack(fill='x', pady=15, padx=5)
        debug_vars = shared_properties.create_debug_and_reliability_ui(parent_frame, config, self.loc)
        property_vars.update(debug_vars)
        return property_vars
    def get_data_preview(self, config: dict):
        return [{'status': 'preview_not_available', 'reason': 'Video generation is a heavy process and requires a file input.'}]
