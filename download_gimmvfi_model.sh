#!/bin/bash
# GIMM-VFI 模型下载脚本

echo "=== 下载 GIMM-VFI 模型 ==="

# GIMM-VFI 模型通常会自动下载到这个位置
GIMM_MODEL_DIR="custom_nodes/ComfyUI-GIMM-VFI/models"
mkdir -p $GIMM_MODEL_DIR

# 模型文件名
MODEL_FILE="gimmvfi_r_arb_lpips_fp32.safetensors"

if [ ! -f "$GIMM_MODEL_DIR/$MODEL_FILE" ]; then
    echo "正在下载 GIMM-VFI 模型..."
    cd $GIMM_MODEL_DIR
    
    # 尝试多个下载源
    echo "尝试从 Hugging Face 下载..."
    wget -c https://huggingface.co/wkpark/GIMM-VFI/resolve/main/$MODEL_FILE || {
        echo "Hugging Face 下载失败，尝试备用链接..."
        # 备用下载链接
        wget -c https://github.com/MCG-NKU/E-RAFT/releases/download/v1.0/$MODEL_FILE || {
            echo ""
            echo "自动下载失败。请手动下载模型："
            echo "1. 访问 https://huggingface.co/wkpark/GIMM-VFI"
            echo "2. 下载 $MODEL_FILE"
            echo "3. 将文件放置到: $(pwd)"
            echo ""
            echo "或者，首次运行 GIMM-VFI 节点时会自动下载"
            exit 1
        }
    }
    
    cd ../../..
    echo "GIMM-VFI 模型下载完成"
else
    echo "GIMM-VFI 模型已存在: $GIMM_MODEL_DIR/$MODEL_FILE"
fi

echo ""
echo "=== 完成 ==="