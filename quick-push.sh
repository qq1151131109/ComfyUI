#!/bin/bash

# 快速推送脚本 - 用于构建并推送最小版本到Docker Hub

DOCKER_USER="your-username"
DOCKER_TOKEN="your-docker-token"
DOCKER_REPO="comfyui"

echo "ComfyUI Docker快速推送脚本"
echo "=========================="
echo ""

# 登录Docker Hub
echo "登录Docker Hub..."
echo $DOCKER_TOKEN | docker login -u $DOCKER_USER --password-stdin

if [ $? -ne 0 ]; then
    echo "登录失败"
    exit 1
fi

echo "登录成功"
echo ""

# 构建最小版本镜像
echo "构建最小版Docker镜像..."
docker build -f Dockerfile.minimal -t $DOCKER_USER/$DOCKER_REPO:minimal . --no-cache

if [ $? -ne 0 ]; then
    echo "构建失败"
    exit 1
fi

echo "构建成功"
echo ""

# 推送镜像
echo "推送镜像到Docker Hub..."
docker push $DOCKER_USER/$DOCKER_REPO:minimal

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 推送成功！"
    echo ""
    echo "其他用户可以使用以下命令拉取："
    echo "docker pull $DOCKER_USER/$DOCKER_REPO:minimal"
    echo ""
    echo "运行命令："
    echo "docker run -d -p 8188:8188 --name comfyui $DOCKER_USER/$DOCKER_REPO:minimal"
else
    echo "❌ 推送失败"
    exit 1
fi

# 同时创建latest标签
read -p "是否将minimal版本标记为latest? (y/n): " tag_latest
if [ "$tag_latest" = "y" ] || [ "$tag_latest" = "Y" ]; then
    docker tag $DOCKER_USER/$DOCKER_REPO:minimal $DOCKER_USER/$DOCKER_REPO:latest
    docker push $DOCKER_USER/$DOCKER_REPO:latest
    echo "已推送latest标签"
fi