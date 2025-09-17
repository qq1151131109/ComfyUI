#!/bin/bash

# 临时解决cuDNN版本冲突的脚本
# 备份原有的cuDNN 9.x库，创建到cuDNN 8.x的符号链接

CONDA_LIB="/home/shenglin/Desktop/ComfyUI/.conda/lib"

# 备份cuDNN 9.x库（如果还没有备份过）
if [ ! -f "${CONDA_LIB}/libcudnn.so.9.backup" ]; then
    echo "备份cuDNN 9.x库..."
    cp "${CONDA_LIB}/libcudnn.so.9" "${CONDA_LIB}/libcudnn.so.9.backup"
    cp "${CONDA_LIB}/libcudnn_ops.so.9" "${CONDA_LIB}/libcudnn_ops.so.9.backup"
    cp "${CONDA_LIB}/libcudnn_cnn.so.9" "${CONDA_LIB}/libcudnn_cnn.so.9.backup"
    cp "${CONDA_LIB}/libcudnn_adv.so.9" "${CONDA_LIB}/libcudnn_adv.so.9.backup"
    cp "${CONDA_LIB}/libcudnn_engines_precompiled.so.9" "${CONDA_LIB}/libcudnn_engines_precompiled.so.9.backup"
    cp "${CONDA_LIB}/libcudnn_engines_runtime_compiled.so.9" "${CONDA_LIB}/libcudnn_engines_runtime_compiled.so.9.backup"
    cp "${CONDA_LIB}/libcudnn_graph.so.9" "${CONDA_LIB}/libcudnn_graph.so.9.backup"
    cp "${CONDA_LIB}/libcudnn_heuristic.so.9" "${CONDA_LIB}/libcudnn_heuristic.so.9.backup"
fi

# 创建指向cuDNN 8.x的符号链接
echo "创建cuDNN 8.x符号链接..."
ln -sf "${CONDA_LIB}/libcudnn.so.8.9.7" "${CONDA_LIB}/libcudnn.so.9"
ln -sf "${CONDA_LIB}/libcudnn_ops_infer.so.8.9.7" "${CONDA_LIB}/libcudnn_ops.so.9" 
ln -sf "${CONDA_LIB}/libcudnn_cnn_infer.so.8.9.7" "${CONDA_LIB}/libcudnn_cnn.so.9"
ln -sf "${CONDA_LIB}/libcudnn_adv_infer.so.8.9.7" "${CONDA_LIB}/libcudnn_adv.so.9"

# 为兼容性创建一些空的符号链接
touch "${CONDA_LIB}/empty_lib.so"
ln -sf "${CONDA_LIB}/empty_lib.so" "${CONDA_LIB}/libcudnn_engines_precompiled.so.9"
ln -sf "${CONDA_LIB}/empty_lib.so" "${CONDA_LIB}/libcudnn_engines_runtime_compiled.so.9"
ln -sf "${CONDA_LIB}/empty_lib.so" "${CONDA_LIB}/libcudnn_graph.so.9"
ln -sf "${CONDA_LIB}/empty_lib.so" "${CONDA_LIB}/libcudnn_heuristic.so.9"

echo "cuDNN符号链接已创建"
echo "现在可以运行WhisperX了"