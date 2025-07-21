# 使用 NVIDIA CUDA 基础镜像
FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=${CUDA_HOME}/bin:${PATH}
ENV LD_LIBRARY_PATH=${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    python3-dev \
    git \
    wget \
    curl \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libglib2.0-0 \
    libgl1-mesa-glx \
    libglib2.0-dev \
    build-essential \
    fonts-wqy-zenhei \
    && rm -rf /var/lib/apt/lists/*

# 创建工作目录
WORKDIR /app/ComfyUI

# 设置 Python 别名
RUN ln -s /usr/bin/python3 /usr/bin/python

# 复制 requirements 文件（如果存在）
COPY requirements.txt* ./

# 安装 PyTorch 和基础依赖
RUN pip install --no-cache-dir \
    torch==2.1.2 \
    torchvision==0.16.2 \
    torchaudio==2.1.2 \
    --index-url https://download.pytorch.org/whl/cu121

# 安装 ComfyUI 依赖
RUN pip install --no-cache-dir \
    -r requirements.txt || \
    pip install --no-cache-dir \
    transformers>=4.36.0 \
    diffusers>=0.25.0 \
    accelerate>=0.25.0 \
    opencv-python>=4.8.0 \
    pillow>=9.5.0 \
    numpy>=1.24.0 \
    scipy>=1.10.0 \
    tqdm>=4.65.0 \
    psutil \
    einops \
    omegaconf \
    pytorch-lightning \
    kornia>=0.7.0 \
    spandrel \
    soundfile>=0.12.1 \
    safetensors>=0.4.0 \
    aiohttp \
    pyyaml \
    Pillow \
    scipy \
    tqdm \
    psutil

# 复制 ComfyUI 核心文件
COPY comfy ./comfy
COPY comfy_extras ./comfy_extras
COPY app ./app
COPY web ./web
COPY api_server.py .
COPY cli_args.py .
COPY execution.py .
COPY folder_paths.py .
COPY latent_preview.py .
COPY main.py .
COPY nodes.py .
COPY notebook.py .
COPY server.py .
COPY *.py ./

# 复制自定义节点
COPY custom_nodes ./custom_nodes

# 安装自定义节点的依赖
RUN cd custom_nodes && \
    for dir in */; do \
        if [ -f "$dir/requirements.txt" ]; then \
            echo "Installing requirements for $dir" && \
            pip install --no-cache-dir -r "$dir/requirements.txt" || true; \
        fi; \
    done

# 创建模型目录结构
RUN mkdir -p \
    models/checkpoints \
    models/vae \
    models/loras \
    models/embeddings \
    models/controlnet \
    models/upscale_models \
    models/clip \
    models/clip_vision \
    models/diffusers \
    models/gligen \
    models/hypernetworks \
    models/photomaker \
    models/style_models \
    models/unet \
    models/diffusion_models \
    models/text_encoders \
    input \
    output \
    temp

# 复制模型文件（这会让镜像很大，可选择性复制）
# 注意：由于模型文件很大，建议使用数据卷挂载而不是直接复制
# COPY models ./models

# 复制工作流文件
COPY workflows ./workflows

# 创建启动脚本
RUN echo '#!/bin/bash\n\
echo "Starting ComfyUI..."\n\
python main.py --listen 0.0.0.0 --port 8188 "$@"\n\
' > /app/start.sh && chmod +x /app/start.sh

# 暴露端口
EXPOSE 8188

# 设置启动命令
CMD ["/app/start.sh"]