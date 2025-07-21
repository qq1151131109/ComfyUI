import os
import sys
import torch
import soundfile as sf
import folder_paths

# Add the parent directory of 'fish_speech' to the Python path
# This is custom_nodes/comfyui-fishSpeech/
# This allows imports like `from fish_speech.models...`
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from .models.text2semantic.inference import launch_thread_safe_queue
from .models.dac.inference import load_model as load_decoder_model
from .inference_engine import TTSInferenceEngine
from .utils.schema import ServeTTSRequest, ServeReferenceAudio

class FishSpeechLoaderNode:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "model": (folder_paths.get_filename_list("checkpoints"), {"tooltip": "model of openaudio-s1-mini path"}),
                "decoder_model":(folder_paths.get_filename_list("checkpoints"), {"tooltip": "model of openaudio-s1-mini path"}),
                "device": (["cuda", "cpu"],),
                "compile": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("TTS_INFERENCE_ENGINE",)
    RETURN_NAMES = ("tts_engine",)
    FUNCTION = "load_models"
    CATEGORY = "FishSpeech"

    def load_models(self, model,decoder_model,device, compile):

        model = folder_paths.get_full_path_or_raise("checkpoints", model)

        model_path = os.path.dirname(model)

        if not os.path.isdir(model_path):
            raise FileNotFoundError(f"model path not found: {model}")

        decoder_model_path = folder_paths.get_full_path_or_raise("checkpoints", decoder_model) 
        if not os.path.isfile(decoder_model_path):
            raise FileNotFoundError(f"decoder model file not found: {decoder_model_path}")

        torch_dtype = torch.float16

        # Check for MPS or XPU
        if torch.backends.mps.is_available():
            device = "mps"
        elif hasattr(torch, "xpu") and torch.xpu.is_available():
            device = "xpu"
        elif not torch.cuda.is_available():
            device = "cpu"

        print("Loading Llama model...")
        llama_queue = launch_thread_safe_queue(
            checkpoint_path=model_path,
            device=device,
            precision=torch_dtype,
            compile=compile,
        )

        print("Loading VQ-GAN (Decoder) model...")
        decoder_model = load_decoder_model(
            config_name="modded_dac_vq",
            checkpoint_path=decoder_model_path,
            device=device,
        )
        
        print("Creating TTS Inference Engine...")
        engine = TTSInferenceEngine(
            llama_queue=llama_queue,
            decoder_model=decoder_model,
            precision=torch_dtype,
            compile=compile
        )
        
        # Warm up
        print("Warming up TTS engine...")
        for _ in engine.inference(ServeTTSRequest(text="warm up")):
            pass
        print("TTS engine warmed up.")

        return (engine,)


class FishSpeechTTSNode:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "tts_engine": ("TTS_INFERENCE_ENGINE",),
                "text": ("STRING", {"multiline": True, "default": "你好,世界"}),
                "top_p": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 0.95, "step": 0.01}),
                "temperature": ("FLOAT", {"default": 0.9, "min": 0.7, "max": 1.0, "step": 0.01}),
                "repetition_penalty": ("FLOAT", {"default": 1.1, "min": 1.0, "max": 1.2, "step": 0.01}),
                "chunk_length": ("INT", {"default": 0, "min": 0, "max": 500, "step": 10}),
                "max_new_tokens": ("INT", {"default": 0, "min": 0, "max": 2048, "step": 12}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
            },
            "optional": {
                "reference_audio_path": ("STRING", {"default": ""}),
                "reference_text": ("STRING", {"multiline": True, "default": ""}),
            }
        }

    RETURN_TYPES = ("AUDIO", )
    RETURN_NAMES = ("audio",)
    FUNCTION = "generate_speech"
    CATEGORY = "FishSpeech"

    def generate_speech(self, tts_engine: TTSInferenceEngine, text, top_p, temperature, repetition_penalty, chunk_length, max_new_tokens, seed, reference_audio_path=None, reference_text=None):
        references = []
        if reference_audio_path and os.path.exists(reference_audio_path):
            try:
                # The TTSInferenceEngine expects bytes
                with open(reference_audio_path, "rb") as f:
                    audio_bytes = f.read()
                
                references.append(
                    ServeReferenceAudio(
                        audio=audio_bytes,
                        text=reference_text if reference_text else "",
                    )
                )
                print(f"Loaded reference audio: {reference_audio_path}")
            except Exception as e:
                print(f"Warning: Could not load reference audio {reference_audio_path}. Error: {e}")

        req = ServeTTSRequest(
            text=text,
            references=references,
            top_p=top_p,
            temperature=temperature,
            repetition_penalty=repetition_penalty,
            max_new_tokens=max_new_tokens,
            chunk_length=chunk_length,
            seed=seed if seed != 0 else None,
        )

        print(f"Generating audio for text: {text}")
        
        final_audio = None
        for result in tts_engine.inference(req):
            if result.code == "final" and result.audio is not None:
                sample_rate, audio_data = result.audio
                final_audio = (sample_rate, audio_data)
                break
            elif result.code == "error":
                raise RuntimeError(f"TTS generation failed: {result.error}")

        if final_audio is None:
            raise RuntimeError("No audio generated.")

        sample_rate, waveform_numpy = final_audio
        
        print(f"Generated audio with sample rate {sample_rate} and shape {waveform_numpy.shape}")
        
        waveform = torch.from_numpy(waveform_numpy).float()
        if waveform.dim() == 1:
            waveform = waveform.unsqueeze(0).unsqueeze(0)  # [N] -> [1, 1, N]
        elif waveform.dim() == 2:
            waveform = waveform.transpose(0, 1).unsqueeze(0)  # [N, C] -> [C, N] -> [1, C, N]
        audio = waveform
        return ({'waveform': audio, 'sample_rate': sample_rate},)


class FishSpeechAudioPreviewNode:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "audio": ("AUDIO",),
                "filename_prefix": ("STRING", {"default": "fish-speech"}),
            }
        }

    RETURN_TYPES = ()
    FUNCTION = "save_and_preview"
    OUTPUT_NODE = True
    CATEGORY = "FishSpeech"

    def save_and_preview(self,audio,filename_prefix="fish-speech"):
        import time
        import os

        # Save audio to a temporary file for playback
        temp_dir = folder_paths.get_temp_directory()
        
        waveform_tensor = audio["waveform"]
        sample_rate = audio["sample_rate"] 
        # Convert to numpy
        #audio_data = waveform_tensor.squeeze(0).cpu().numpy()
        audio_data = audio['waveform'].squeeze(0).transpose(0,1).cpu().numpy()
        
        filename = f"{filename_prefix}_{int(time.time() * 1000)}.wav"
        
        filepath = os.path.join(temp_dir, filename)
        sf.write(filepath, audio_data, sample_rate, subtype='PCM_16')

        return {"ui": {"audio": [{"filename": filename, "subfolder": "", "type": "temp"}]}}



if __name__ == "__main__":
    # This is for testing purposes
    # You would typically run this inside ComfyUI
    
    loader = FishSpeechLoaderNode()
    engine, = loader.load_models(
    model="checkpoints/openaudio-s1-mini",
    device="cuda",
    compile=True
    )
    
    tts = FishSpeechTTSNode()
    audio_tuple = tts.generate_speech(
        tts_engine=engine,
        text="Hello, this is a test of the fish speech model in ComfyUI, using the new inference engine.",
        top_p=0.7,
        temperature=0.8,
        repetition_penalty=1.1,
        chunk_length=200,
        max_new_tokens=0,
        seed=42,
        reference_audio_path="/home/ubuntu/jfz/fish-speech2/wav/test.mp3",
        reference_text="",
    )

    # Save the audio using the preview node
    waveform_tensor, sample_rate = audio_tuple
    
    preview = FishSpeechAudioPreviewNode()
    result = preview.save_and_preview(
        waveform=waveform_tensor,
        sample_rate=sample_rate,
        filename_prefix="output_comfy"
    )

    # The result contains UI information, which we can use to report the saved file path
    saved_file_info = result['ui']['audio'][0]
    # For temp files, the subfolder is empty and the base is the temp dir
    filepath = os.path.join(folder_paths.get_temp_directory(), saved_file_info['filename'])
    
    # We need to make sure the path is absolute for printing
    if not os.path.isabs(filepath):
        filepath = os.path.abspath(filepath)
        
    print(f"Test audio saved to {filepath} at {sample_rate} Hz") 