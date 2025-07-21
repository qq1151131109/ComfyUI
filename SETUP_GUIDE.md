# ComfyUI Workflows Setup Guide

This guide helps you set up ComfyUI to run all workflows in the `workflows/` directory.

## Quick Start

1. **Install Custom Nodes**
   ```bash
   chmod +x install_custom_nodes.sh
   ./install_custom_nodes.sh
   ```

2. **Download Models**
   ```bash
   chmod +x download_models.sh
   ./download_models.sh
   ```

3. **Manual Model Downloads**
   Some models need manual download:
   - Visit [CivitAI](https://civitai.com) for:
     - UltraRealPhoto.safetensors
   - Chinese LoRA models:
     - 真实古风_FLUX-V1.0
     - F.1 | 荷叶_V1.0
     - 泡泡玛特/F.1 labubu拉布布-3D风格-泡泡玛特 稳定生成_F.1.safetensors
   - FishSpeech models from their repository

## Workflow Requirements

### 1. flux+openpose-0702-1.json
- **Purpose**: FLUX model with OpenPose control
- **Key Models**: flux1-dev, FLUX ControlNet Union
- **Custom Nodes**: controlnet_aux, advanced-controlnet

### 2. sdxl+controlnet.json
- **Purpose**: SDXL with face preservation using IPAdapter
- **Key Models**: SDXL base, IPAdapter FaceID
- **Custom Nodes**: IPAdapter_plus, controlnet_aux

### 3. 文生图 (Text-to-Image) Workflows
- **Purpose**: Generate images from text prompts
- **Key Models**: FLUX models with various LoRAs
- **Features**: Batch processing, style variations

### 4. 数字人 (Digital Human) Workflows
- **Purpose**: Create talking avatars with TTS
- **Key Models**: FishSpeech TTS models
- **Custom Nodes**: LatentSync, VideoHelperSuite, FishSpeech

## Model Directory Structure

```
models/
├── unet/              # FLUX models
├── vae/               # VAE models
├── text_encoders/     # CLIP/T5 encoders
├── checkpoints/       # SDXL checkpoints
├── controlnet/        # ControlNet models
├── loras/             # LoRA models
├── ipadapter/         # IPAdapter models
├── clip_vision/       # CLIP vision models
└── FishSpeech/        # TTS models
```

## Troubleshooting

### Missing Dependencies
```bash
# General dependencies
pip install torch torchvision torchaudio
pip install opencv-python pillow numpy
pip install transformers diffusers

# For IPAdapter
pip install insightface onnxruntime-gpu

# For video processing
pip install moviepy imageio-ffmpeg

# For audio
pip install librosa soundfile
```

### CUDA Issues
- Ensure CUDA is properly installed
- Check PyTorch CUDA version: `python -c "import torch; print(torch.cuda.is_available())"`

### Memory Issues
- FLUX models require significant VRAM (16GB+ recommended)
- Use `--lowvram` or `--cpu` flags if needed
- Reduce batch size in workflows

## Running ComfyUI

```bash
# Standard launch
python main.py

# With low VRAM
python main.py --lowvram

# CPU only
python main.py --cpu

# Custom port
python main.py --port 8189
```

## Verifying Installation

1. Start ComfyUI
2. Check console for errors
3. Load a workflow from `workflows/` directory
4. Verify all nodes load correctly (no red nodes)
5. Check model dropdowns are populated

## Additional Resources

- [ComfyUI Documentation](https://github.com/comfyanonymous/ComfyUI)
- [Model Downloads](https://huggingface.co)
- [Custom Nodes Registry](https://github.com/ltdrdata/ComfyUI-Manager)

## Notes

- Model downloads can take significant time (50GB+ total)
- Some workflows require specific hardware (GPU with 16GB+ VRAM)
- FishSpeech TTS requires CUDA support
- Keep models organized in correct directories for workflows to function