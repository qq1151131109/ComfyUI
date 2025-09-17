#!/bin/bash
# ComfyUI启动脚本 - 包含cuDNN修复

echo "🚀 启动ComfyUI with cuDNN修复..."

# 设置cuDNN库路径
export LD_LIBRARY_PATH="/home/shenglin/Desktop/ComfyUI/.conda/lib/python3.11/site-packages/nvidia/cudnn/lib:$LD_LIBRARY_PATH"

echo "📚 库路径设置: $LD_LIBRARY_PATH"

# 切换到ComfyUI目录
cd /home/shenglin/Desktop/ComfyUI

# 验证库文件可访问
if [ -f "/home/shenglin/Desktop/ComfyUI/.conda/lib/python3.11/site-packages/nvidia/cudnn/lib/libcudnn_ops_infer.so.8" ]; then
    echo "✅ cuDNN修复文件存在"
else
    echo "❌ cuDNN修复文件缺失，正在重新创建..."
    ./fix_cudnn.sh
fi

echo "🎬 启动ComfyUI..."
python main.py "$@"