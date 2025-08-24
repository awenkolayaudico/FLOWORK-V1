#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\ai_providers\specialized\dummy_ai_provider\provider.py
# JUMLAH BARIS : 34
#######################################################################

from flowork_kernel.api_contract import BaseAIProvider
import time
class DummyAiProvider(BaseAIProvider):
    """A dummy AI provider for testing that returns canned responses based on keywords."""
    def __init__(self, kernel, manifest: dict):
        super().__init__(kernel, manifest)
    def get_provider_name(self) -> str:
        return "Dummy AI (for Testing)"
    def is_ready(self) -> tuple[bool, str]:
        """The dummy provider is always ready."""
        return (True, "")
    def generate_response(self, prompt: str) -> dict:
        self.kernel.write_to_log(f"DummyAI received prompt: '{prompt[:50]}...'", "INFO")
        time.sleep(1)
        prompt_lower = prompt.lower()
        if any(keyword in prompt_lower for keyword in ["musik", "lagu", "audio", "sound", "aransemen"]):
            return {
                "type": "audio_file",
                "data": f"dummy_sad_music_track_for_{prompt.replace(' ', '_')}.mp3"
            }
        if "gambar" in prompt_lower or "image" in prompt_lower:
            return { "type": "image_url", "data": "https://i.imgur.com/8Nf3fG7.png" }
        if "kode" in prompt_lower or "python" in prompt_lower or "script" in prompt_lower:
            return { "type": "code", "data": "print('Hello from the Dummy AI!')" }
        if "analisa" in prompt_lower or "data" in prompt_lower or "csv" in prompt_lower:
            return { "type": "json", "data": { "summary": "Analysis complete" } }
        return { "type": "text", "data": f"Ini adalah respons palsu dari Dummy AI untuk prompt: '{prompt}'" }
