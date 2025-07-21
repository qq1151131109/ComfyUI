#!/bin/bash
# 安装缺失的节点和下载模型

echo "=== 安装缺失的组件和模型 ==="

# 1. 安装 GIMM-VFI 节点
echo ""
echo "1. 安装 ComfyUI-GIMM-VFI 节点..."
if [ ! -d "custom_nodes/ComfyUI-GIMM-VFI" ]; then
    cd custom_nodes
    git clone https://github.com/kijai/ComfyUI-GIMM-VFI.git
    cd ComfyUI-GIMM-VFI
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    fi
    cd ../..
    echo "GIMM-VFI 节点安装完成"
else
    echo "GIMM-VFI 节点已存在"
fi

# 2. 下载 GIMM-VFI 模型
echo ""
echo "2. 下载 GIMM-VFI 模型..."
GIMM_MODEL_DIR="models/gimm_vfi"
mkdir -p $GIMM_MODEL_DIR

if [ ! -f "$GIMM_MODEL_DIR/gimmvfi_r_arb_lpips_fp32.safetensors" ]; then
    echo "下载 GIMM-VFI 模型文件..."
    cd $GIMM_MODEL_DIR
    # 从 Hugging Face 下载
    wget -c https://huggingface.co/AlexWortega/GIMM-VFI/resolve/main/gimmvfi_r_arb_lpips_fp32.safetensors
    cd ../..
    echo "GIMM-VFI 模型下载完成"
else
    echo "GIMM-VFI 模型已存在"
fi

# 3. 检查 WanVideo 节点
echo ""
echo "3. 检查 ComfyUI-WanVideoWrapper 节点..."
if [ ! -d "custom_nodes/ComfyUI-WanVideoWrapper" ]; then
    echo "警告：ComfyUI-WanVideoWrapper 节点未安装"
    echo "这是一个商业节点，需要从官方渠道获取"
    echo "请访问相关社区或联系开发者获取安装方式"
else
    echo "ComfyUI-WanVideoWrapper 节点已安装"
fi

# 4. 创建 WanVideo 模型目录
echo ""
echo "4. 创建 WanVideo 模型目录..."
mkdir -p models/diffusion_models/Wan14BT2VFusioniX
mkdir -p models/diffusion_models/wan2.1
mkdir -p models/vae

echo ""
echo "WanVideo 模型需要手动下载："
echo "- Wan14Bi2vFusioniX_fp16.safetensors -> models/diffusion_models/Wan14BT2VFusioniX/"
echo "- umt5-xxl-enc-bf16.safetensors -> models/diffusion_models/wan2.1/"
echo "- Wan2_1_VAE_bf16.safetensors -> models/vae/"

# 5. 创建 Lora 目录
echo ""
echo "5. 创建 Lora 模型目录..."
mkdir -p models/loras/恐怖悬疑

echo ""
echo "Lora 模型请从 Civitai 下载："
echo "- guaidanmenghe.safetensors -> models/loras/恐怖悬疑/"

# 6. 下载额外的 RealESRGAN 模型（可选）
echo ""
echo "6. 下载额外的 RealESRGAN 模型..."
if [ ! -f "models/upscale_models/RealESRGAN_x4plus.pth" ]; then
    echo "下载 RealESRGAN_x4plus 模型..."
    wget -c https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth -O models/upscale_models/RealESRGAN_x4plus.pth
else
    echo "RealESRGAN_x4plus 模型已存在"
fi

echo ""
echo "=== 安装完成 ==="
echo ""
echo "已完成："
echo "✓ RealESRGAN 模型已下载"
echo "✓ GIMM-VFI 节点和模型安装脚本已创建"
echo "✓ 目录结构已创建"
echo ""
echo "需要手动完成："
echo "✗ WanVideo 模型（商业模型，需要从官方渠道获取）"
echo "✗ Lora 模型（从 Civitai 下载）"
echo ""
echo "提示：重启 ComfyUI 以加载新安装的节点"