#!/bin/bash

# ComfyUI Custom Nodes Installation Script
# This script installs all required custom nodes for the workflows

echo "Starting ComfyUI custom nodes installation..."

cd custom_nodes/

# Install comfyui_controlnet_aux
echo "Installing comfyui_controlnet_aux..."
git clone https://github.com/Fannovel16/comfyui_controlnet_aux.git
cd comfyui_controlnet_aux && pip install -r requirements.txt && cd ..

# Install comfyui-advanced-controlnet
echo "Installing comfyui-advanced-controlnet..."
git clone https://github.com/Kosinkadink/ComfyUI-Advanced-ControlNet.git

# Install ComfyLiterals
echo "Installing ComfyLiterals..."
git clone https://github.com/M1kep/ComfyLiterals.git

# Install derfuu_comfyui_moddednodes
echo "Installing derfuu_comfyui_moddednodes..."
git clone https://github.com/Derfuu/Derfuu_ComfyUI_ModdedNodes.git

# Install comfyui_ipadapter_plus
echo "Installing comfyui_ipadapter_plus..."
git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus.git
cd ComfyUI_IPAdapter_plus && pip install -r requirements.txt && cd ..

# Install comfyui_essentials
echo "Installing comfyui_essentials..."
git clone https://github.com/cubiq/ComfyUI_essentials.git
cd ComfyUI_essentials && pip install -r requirements.txt && cd ..

# Install was-node-suite-comfyui
echo "Installing was-node-suite-comfyui..."
git clone https://github.com/WASasquatch/was-node-suite-comfyui.git
cd was-node-suite-comfyui && pip install -r requirements.txt && cd ..

# Install ComfyUI-LatentSyncWrapper
echo "Installing ComfyUI-LatentSyncWrapper..."
git clone https://github.com/ShmuelRonen/ComfyUI-LatentSyncWrapper.git

# Install comfy-video-yxkj
echo "Installing comfy-video-yxkj..."
git clone https://github.com/jiafuzeng/comfy-video-yxkj.git

# Install comfyui-videohelpersuite
echo "Installing comfyui-videohelpersuite..."
git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
cd ComfyUI-VideoHelperSuite && pip install -r requirements.txt && cd ..

# Install comfyui-fishSpeech
echo "Installing comfyui-fishSpeech..."
git clone https://github.com/jiafuzeng/comfyui-fishSpeech.git
cd comfyui-fishSpeech && pip install -r requirements.txt && cd ..

# Install additional dependencies
echo "Installing additional dependencies..."

# For IPAdapter FaceID (InsightFace)
pip install insightface onnxruntime onnxruntime-gpu

# For video processing
pip install opencv-python moviepy imageio imageio-ffmpeg

# For audio processing
pip install librosa soundfile

cd ..

echo "Custom nodes installation completed!"
echo ""
echo "IMPORTANT NOTES:"
echo "1. Restart ComfyUI after installation"
echo "2. Some nodes may require additional setup or model downloads"
echo "3. Check the console for any error messages during startup"
echo ""
echo "If you encounter issues:"
echo "- Check Python dependencies: pip install -r requirements.txt in each node folder"
echo "- Some nodes may require specific Python versions or CUDA versions"
echo "- FishSpeech may require additional audio dependencies"