# ComfyUI 批量视频处理扩展

> 专为ComfyUI设计的专业批量视频处理工具，支持多选上传、文件夹批量处理、智能切分和一键下载。

## 🚀 核心功能

- **🔼 真正的批量上传**: 支持多文件选择和整个文件夹上传，突破ComfyUI原生限制
- **✂️ 智能视频切分**: 批量切分视频为指定时长片段，支持并行处理
- **🎬 视频拼接器**: 无缝拼接主视频和结尾视频
- **📦 一键打包下载**: 将处理结果自动打包为ZIP文件
- **🗂️ 文件管理器**: 管理批处理历史，定期清理临时文件

## 📸 界面预览

### 自定义批量上传组件
- ✅ 多选文件上传（Ctrl/Cmd + 点击）
- ✅ 整个文件夹选择（webkitdirectory）
- ✅ 实时上传进度显示
- ✅ 文件预览和管理
- ✅ 会话名称自定义

### 全中文界面
所有节点和参数都使用中文显示，操作更直观：
- 批量视频加载器
- 视频拼接器  
- 批量视频切分器
- 批量下载器
- 文件管理器

## 🛠️ 安装方法

### 方法1: ComfyUI Manager安装（推荐）
1. 在ComfyUI界面点击"Manager"按钮
2. 搜索"batch video"或"批量视频"
3. 点击安装并重启ComfyUI

### 方法2: 手动安装
```bash
cd ComfyUI/custom_nodes
git clone https://github.com/qq1151131109/comfyui-dingzhiban.git batch_video_processor
cd batch_video_processor
pip install -r requirements.txt
```

### 方法3: 直接下载
1. [下载ZIP文件](https://github.com/qq1151131109/comfyui-dingzhiban/archive/main.zip)
2. 解压到`ComfyUI/custom_nodes/batch_video_processor`
3. 安装依赖：`pip install ffmpeg-python`

## 🎯 快速开始

### 基础工作流
```
批量视频加载器 → 批量视频切分器 → 批量下载器
```

### 详细步骤
1. **上传视频**: 
   - 添加"批量视频加载器"节点
   - 点击节点上的"批量上传"按钮
   - 选择多个文件或整个文件夹

2. **切分处理**:
   - 添加"批量视频切分器"节点
   - 设置切分时长（如30秒）
   - 连接文件夹路径输入

3. **下载结果**:
   - 添加"批量下载器"节点  
   - 连接输出文件夹
   - 获得ZIP压缩包

## 💡 使用场景

- **短视频制作**: 长视频切分为短片段用于抖音、快手等平台
- **教学内容**: 课程视频按章节切分，添加统一片头片尾
- **广告素材**: 批量处理广告视频，添加品牌结尾
- **内容审核**: 大量视频快速切分预览
- **媒体归档**: 视频资料批量整理和标准化

## 🔧 技术特点

### 突破原生限制
- 自定义前端组件实现真正的多选上传
- 支持webkitdirectory文件夹选择
- 实时进度显示和错误处理

### 高效批量处理  
- FFmpeg底层优化
- 多线程并行处理
- 智能错误恢复

### 用户体验优先
- 全中文界面
- 简化参数设置
- 详细使用说明

## 📋 支持格式

**输入格式**: mp4, avi, mov, mkv, flv, wmv, m4v  
**输出格式**: mp4（统一编码，兼容性最佳）  
**平台支持**: Windows, macOS, Linux  

## 📚 详细文档

- [完整使用指南](USAGE.md) - 详细的使用方法和最佳实践
- [功能介绍](README_v2.md) - 改进版功能详细说明

## 🐛 问题反馈

如遇到问题请提供：
1. ComfyUI版本信息
2. 错误截图或日志
3. 使用的视频文件信息
4. 操作系统版本

[提交Issue](https://github.com/qq1151131109/comfyui-dingzhiban/issues)

## 📄 开源协议

本项目采用 MIT 协议开源，欢迎贡献代码！

---

⭐ 如果这个扩展对你有帮助，请给个Star支持一下！

🔧 Generated with [Claude Code](https://claude.ai/code)