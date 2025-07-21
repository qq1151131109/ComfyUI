#!/bin/bash
# 下载 WanVideo 模型脚本

echo "=== 开始下载 WanVideo 模型 ==="

# 创建必要的目录
echo "创建模型目录..."
mkdir -p models/diffusion_models/wan2.1
mkdir -p models/vae
mkdir -p models/diffusion_models/Wan14BT2VFusioniX

# 1. 下载 UMT5 文本编码器
echo ""
echo "1. 下载 umt5-xxl-enc-bf16.safetensors..."
if [ ! -f "models/diffusion_models/wan2.1/umt5-xxl-enc-bf16.safetensors" ]; then
    wget -c https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/umt5-xxl-enc-bf16.safetensors \
         -O models/diffusion_models/wan2.1/umt5-xxl-enc-bf16.safetensors
    echo "UMT5 文本编码器下载完成"
else
    echo "UMT5 文本编码器已存在"
fi

# 2. 下载 WanVideo VAE
echo ""
echo "2. 下载 Wan2_1_VAE_bf16.safetensors..."
if [ ! -f "models/vae/Wan2_1_VAE_bf16.safetensors" ]; then
    wget -c https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1_VAE_bf16.safetensors \
         -O models/vae/Wan2_1_VAE_bf16.safetensors
    echo "WanVideo VAE 下载完成"
else
    echo "WanVideo VAE 已存在"
fi

# 3. 尝试下载主模型
echo ""
echo "3. 查找 WanVideo 主模型..."
echo "正在检查是否有 Wan14Bi2vFusioniX_fp16.safetensors..."

# 尝试从同一个 repo 下载
MAIN_MODEL="Wan14Bi2vFusioniX_fp16.safetensors"
if [ ! -f "models/diffusion_models/Wan14BT2VFusioniX/$MAIN_MODEL" ]; then
    echo "尝试从 Hugging Face 下载主模型..."
    wget -c https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/$MAIN_MODEL \
         -O models/diffusion_models/Wan14BT2VFusioniX/$MAIN_MODEL || {
        echo ""
        echo "主模型下载失败，可能需要其他下载源"
        echo "请检查以下位置："
        echo "- https://huggingface.co/Kijai/WanVideo_comfy"
        echo "- 或搜索 'Wan14Bi2vFusioniX' 模型"
    }
else
    echo "WanVideo 主模型已存在"
fi

echo ""
echo "=== 下载完成 ==="
echo ""
echo "已下载的模型："
ls -lh models/diffusion_models/wan2.1/ 2>/dev/null
ls -lh models/vae/Wan2_1_VAE_bf16.safetensors 2>/dev/null
ls -lh models/diffusion_models/Wan14BT2VFusioniX/ 2>/dev/null

echo ""
echo "提示：如果主模型下载失败，请手动下载 Wan14Bi2vFusioniX_fp16.safetensors"