#!/bin/bash
# 查找 WanVideo 主模型

echo "=== 查找 WanVideo 主模型 ==="
echo ""
echo "访问 https://huggingface.co/Kijai/WanVideo_comfy/tree/main 查看可用模型"
echo ""
echo "常见的模型名称可能包括："
echo "- Wan14Bi2vFusionX_fp16.safetensors (注意 X 而不是 iX)"
echo "- Wan14BT2VFusionX_fp16.safetensors"
echo "- Wan14B_i2v_fp16.safetensors"
echo "- wan14b_t2v_fp16.safetensors"
echo ""
echo "尝试下载其他可能的名称..."

# 尝试不同的可能名称
MODEL_DIR="models/diffusion_models/Wan14BT2VFusioniX"
BASE_URL="https://huggingface.co/Kijai/WanVideo_comfy/resolve/main"

# 尝试的模型名称列表
MODEL_NAMES=(
    "Wan14Bi2vFusionX_fp16.safetensors"
    "Wan14BT2VFusionX_fp16.safetensors"
    "Wan14B_i2v_fp16.safetensors"
    "wan14b_t2v_fp16.safetensors"
    "Wan14B_fp16.safetensors"
)

for MODEL_NAME in "${MODEL_NAMES[@]}"; do
    echo ""
    echo "尝试下载: $MODEL_NAME"
    if [ ! -f "$MODEL_DIR/$MODEL_NAME" ]; then
        wget -c "$BASE_URL/$MODEL_NAME" -O "$MODEL_DIR/$MODEL_NAME" 2>/dev/null && {
            echo "成功下载: $MODEL_NAME"
            # 如果文件名不匹配预期，创建符号链接
            if [ "$MODEL_NAME" != "Wan14Bi2vFusioniX_fp16.safetensors" ]; then
                ln -sf "$MODEL_NAME" "$MODEL_DIR/Wan14Bi2vFusioniX_fp16.safetensors"
                echo "创建符号链接: Wan14Bi2vFusioniX_fp16.safetensors -> $MODEL_NAME"
            fi
            break
        } || {
            echo "未找到: $MODEL_NAME"
            rm -f "$MODEL_DIR/$MODEL_NAME"  # 删除空文件
        }
    fi
done

echo ""
echo "如果所有尝试都失败，请："
echo "1. 访问 https://huggingface.co/Kijai/WanVideo_comfy/tree/main"
echo "2. 查看实际的模型文件名"
echo "3. 手动下载到 $MODEL_DIR/"