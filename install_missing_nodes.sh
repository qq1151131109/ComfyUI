#!/bin/bash

# ComfyUI Missing Custom Nodes Installation Script

CUSTOM_NODES_DIR="/raid0/shenglin/ComfyUI/custom_nodes"

echo "==================================="
echo "Installing Missing ComfyUI Custom Nodes"
echo "==================================="

cd "$CUSTOM_NODES_DIR"

# Function to install a node from git
install_node() {
    local repo_url=$1
    local folder_name=$2
    local description=$3
    
    echo ""
    echo "Installing: $description"
    echo "Repository: $repo_url"
    
    if [ -d "$folder_name" ]; then
        echo "$folder_name already exists, skipping..."
    else
        git clone "$repo_url" "$folder_name"
        if [ $? -eq 0 ]; then
            echo "✓ Successfully cloned $folder_name"
            
            # Install requirements if exists
            if [ -f "$folder_name/requirements.txt" ]; then
                echo "Installing requirements for $folder_name..."
                pip install -r "$folder_name/requirements.txt"
            fi
        else
            echo "✗ Failed to clone $folder_name"
        fi
    fi
}

# Install missing nodes
echo ""
echo "=== Installing Critical Missing Nodes ==="

# 1. comfyui-kjnodes - Image processing tools
install_node "https://github.com/kijai/ComfyUI-KJNodes.git" \
             "comfyui-kjnodes" \
             "KJ Nodes - Image processing and utility nodes"

# 2. ComfyUI-FramePackWrapper - Video generation framework
install_node "https://github.com/kijai/ComfyUI-FramePackWrapper.git" \
             "ComfyUI-FramePackWrapper" \
             "FramePack Wrapper - Video generation nodes"

# 3. ComfyUI-Index-TTS - TTS voice synthesis
install_node "https://github.com/chenpipi0807/ComfyUI-Index-TTS.git" \
             "ComfyUI-Index-TTS" \
             "Index TTS - Text-to-speech synthesis"

# 4. ComfyUI-WanVideoWrapper - WanVideo video generation
install_node "https://github.com/1038lab/ComfyUI-WanVideoWrapper.git" \
             "ComfyUI-WanVideoWrapper" \
             "WanVideo Wrapper - Advanced video generation"

echo ""
echo "=== Post-installation Steps ==="

# Special handling for nodes that might need additional setup
echo ""
echo "Checking for special requirements..."

# FramePackWrapper might need model downloads
if [ -d "ComfyUI-FramePackWrapper" ]; then
    echo ""
    echo "Note: FramePackWrapper requires additional model downloads:"
    echo "- FramePackI2V_HY_fp8_e4m3fn.safetensors"
    echo "Please check the node's documentation for model locations."
fi

# Index-TTS might need TTS models
if [ -d "ComfyUI-Index-TTS" ]; then
    echo ""
    echo "Note: Index-TTS requires TTS model files:"
    echo "- IndexTTS-1.5 models"
    echo "Please download from the official repository."
fi

# WanVideoWrapper special requirements
if [ -d "ComfyUI-WanVideoWrapper" ]; then
    echo ""
    echo "Note: WanVideoWrapper requires video generation models."
    echo "Please check the node's documentation for required models."
fi

echo ""
echo "==================================="
echo "Installation Summary"
echo "==================================="

# Check installation status
echo ""
echo "Checking installation status:"
[ -d "comfyui-kjnodes" ] && echo "✓ comfyui-kjnodes installed" || echo "✗ comfyui-kjnodes not installed"
[ -d "ComfyUI-FramePackWrapper" ] && echo "✓ ComfyUI-FramePackWrapper installed" || echo "✗ ComfyUI-FramePackWrapper not installed"
[ -d "ComfyUI-Index-TTS" ] && echo "✓ ComfyUI-Index-TTS installed" || echo "✗ ComfyUI-Index-TTS not installed"
[ -d "ComfyUI-WanVideoWrapper" ] && echo "✓ ComfyUI-WanVideoWrapper installed" || echo "✗ ComfyUI-WanVideoWrapper not installed"

echo ""
echo "==================================="
echo "IMPORTANT: Restart ComfyUI after installation!"
echo "==================================="
echo ""
echo "Additional nodes that might be needed based on workflows:"
echo "1. For batch processing: Consider installing ComfyUI-Impact-Pack"
echo "2. For advanced sampling: Consider installing ComfyUI-AnimateDiff-Evolved"
echo "3. For better UI: Consider installing ComfyUI-Manager"
echo ""