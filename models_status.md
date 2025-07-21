# ComfyUI 模型状态总结

## ✅ 已成功下载的模型

### 1. Flux 文生图模型（完整）
- `models/unet/flux1-dev.safetensors` ✓
- `models/vae/flux_ae.safetensors` ✓
- `models/text_encoders/flux_text_encoders/t5xxl_fp16.safetensors` ✓
- `models/text_encoders/flux_text_encoders/clip_l.safetensors` ✓

### 2. RealESRGAN 图像放大模型
- `models/upscale_models/RealESRGAN_x2.pth` ✓
- `models/upscale_models/RealESRGAN_x4plus.pth` ✓

### 3. WanVideo 模型（部分）
- `models/diffusion_models/wan2.1/umt5-xxl-enc-bf16.safetensors` ✓ (11GB)
- `models/vae/Wan2_1_VAE_bf16.safetensors` ✓ (243MB)

### 4. LatentSync 模型（完整）
- `custom_nodes/ComfyUI-LatentSyncWrapper/checkpoints/latentsync_unet.pt` ✓
- `custom_nodes/ComfyUI-LatentSyncWrapper/checkpoints/whisper/tiny.pt` ✓

## ❌ 缺失的模型

### 1. WanVideo 主模型
- **文件名**: `Wan14Bi2vFusioniX_fp16.safetensors`
- **状态**: 未找到
- **解决方案**:
  1. 访问 https://huggingface.co/Kijai/WanVideo_comfy/tree/main 查看实际文件名
  2. 或搜索其他 WanVideo 相关仓库
  3. 可能需要从官方渠道获取

### 2. GIMM-VFI 模型
- **文件名**: `gimmvfi_r_arb_lpips_fp32.safetensors`
- **状态**: 节点会自动下载
- **位置**: 首次运行 GIMM-VFI 节点时会自动下载

### 3. Lora 模型（可选）
- **文件名**: `恐怖悬疑/guaidanmenghe.safetensors`
- **状态**: 需要从 Civitai 下载

## 📋 可用的工作流

### ✅ 完全可用
- LatentSync 数字人工作流
- Flux 文生图工作流

### ⚠️ 部分可用
- 批量图生视频工作流（缺少 WanVideo 主模型）
- 文生图+图生视频工作流（缺少 WanVideo 主模型）

## 🔗 相关链接
- WanVideo 模型仓库: https://huggingface.co/Kijai/WanVideo_comfy
- GIMM-VFI 仓库: https://huggingface.co/wkpark/GIMM-VFI
- Civitai (Lora模型): https://civitai.com/

## 📝 备注
- WanVideo 主模型可能需要特殊权限或从其他来源获取
- 建议先使用已完全可用的工作流
- GIMM-VFI 会在首次使用时自动下载，无需手动操作