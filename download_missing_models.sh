#!/bin/bash
# 下载缺失的模型脚本

echo "=== 开始下载缺失的模型 ==="

# 创建必要的目录
echo "创建模型目录..."
mkdir -p models/upscale_models
mkdir -p models/diffusion_models/Wan14BT2VFusioniX
mkdir -p models/diffusion_models/wan2.1
mkdir -p models/loras/恐怖悬疑

# 1. 下载 RealESRGAN 模型
echo ""
echo "1. 下载 RealESRGAN_x2.pth..."
if [ ! -f "models/upscale_models/RealESRGAN_x2.pth" ]; then
    wget -c https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth -O models/upscale_models/RealESRGAN_x2.pth
    echo "RealESRGAN_x2.pth 下载完成"
else
    echo "RealESRGAN_x2.pth 已存在，跳过下载"
fi

# 2. GIMM-VFI 模型通常由节点自动下载
echo ""
echo "2. GIMM-VFI 模型说明："
echo "   - gimmvfi_r_arb_lpips_fp32.safetensors"
echo "   - 此模型通常在首次运行 GIMM-VFI 节点时自动下载"
echo "   - 如果需要手动下载，可以从以下地址获取："
echo "   - https://huggingface.co/wkpark/GIMM-VFI"

# 3. WanVideo 模型说明
echo ""
echo "3. WanVideo 模型说明："
echo "   需要下载以下模型："
echo "   - Wan14Bi2vFusioniX_fp16.safetensors"
echo "   - umt5-xxl-enc-bf16.safetensors"
echo "   - Wan2_1_VAE_bf16.safetensors"
echo ""
echo "   这些是商业模型，请从以下途径获取："
echo "   1. 联系模型提供方"
echo "   2. 查看 ComfyUI-WanVideoWrapper 节点的文档"
echo "   3. 或从相关社区获取下载链接"

# 4. 创建模型下载辅助脚本
echo ""
echo "4. 创建 GIMM-VFI 手动下载脚本..."
cat > download_gimmvfi.sh << 'EOF'
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
EOF

chmod +x download_gimmvfi.sh

# 5. Lora 模型说明
echo ""
echo "5. Lora 模型说明："
echo "   - 恐怖悬疑/guaidanmenghe.safetensors"
echo "   - 可以从 Civitai 或其他模型分享平台下载"
echo "   - 下载后放置到 models/loras/恐怖悬疑/ 目录"

echo ""
echo "=== 脚本执行完成 ==="
echo ""
echo "注意事项："
echo "1. RealESRGAN 模型已下载（如果之前不存在）"
echo "2. GIMM-VFI 模型请运行 ./download_gimmvfi.sh 下载"
echo "3. WanVideo 模型需要从官方渠道获取"
echo "4. Lora 模型请从模型分享平台下载"