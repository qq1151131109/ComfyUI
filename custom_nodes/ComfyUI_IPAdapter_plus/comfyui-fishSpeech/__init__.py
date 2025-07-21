from .fish_speech.nodes import FishSpeechAudioPreviewNode,FishSpeechTTSNode,FishSpeechLoaderNode


NODE_CLASS_MAPPINGS = {
    "FishSpeechLoader": FishSpeechLoaderNode,
    "FishSpeechTTS": FishSpeechTTSNode,
    "FishSpeechAudioPreview": FishSpeechAudioPreviewNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "FishSpeechLoader": "Fish-Speech Loader",
    "FishSpeechTTS": "Fish-Speech TTS",
    "FishSpeechAudioPreview": "Fish-Speech Audio Preview",
}
