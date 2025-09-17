# 使用带CUDA的PyTorch基础镜像（更轻量的版本）
FROM pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime

# 设置工作目录
WORKDIR /app

# 安装系统依赖（优化安装过程）
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    wget \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 先复制requirements文件
COPY requirements.txt .

# 安装Python依赖（使用国内镜像加速）
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt || \
    pip install --no-cache-dir -r requirements.txt

# 复制代码（不包括大型模型文件）
COPY --chown=1000:1000 . .

# 创建必要的目录
RUN mkdir -p input output custom_nodes models/checkpoints models/loras models/vae \
    && chmod -R 755 /app

# 暴露端口
EXPOSE 8188

# 设置环境变量
ENV PYTHONUNBUFFERED=1

# 启动命令
CMD ["python", "main.py", "--listen", "0.0.0.0", "--port", "8188"]