#!/bin/bash
# GIMM-VFI 模型下载脚本

echo "下载 GIMM-VFI 模型..."

# 检查 ComfyUI-GIMM-VFI 节点目录
GIMM_DIR="custom_nodes/ComfyUI-GIMM-VFI"

if [ -d "$GIMM_DIR" ]; then
    cd "$GIMM_DIR"
    # 尝试从 Hugging Face 下载
    if command -v wget &> /dev/null; then
        wget -c https://huggingface.co/wkpark/GIMM-VFI/resolve/main/gimmvfi_r_arb_lpips_fp32.safetensors -P models/
    else
        echo "请安装 wget 或手动下载模型"
    fi
    cd ../..
else
    echo "未找到 ComfyUI-GIMM-VFI 节点目录"
    echo "请先安装该节点"
fi
