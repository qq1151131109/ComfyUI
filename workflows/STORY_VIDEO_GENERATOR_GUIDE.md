# ComfyUI故事视频生成器 - 完整使用指南

## 🎯 项目概述

这是基于Coze工作流完整复刻的ComfyUI故事视频生成器，能够从单个主题自动生成包含文案、配音、配图、字幕、动画效果的完整历史故事视频。

## 📋 功能特性

### ✅ **完整复刻原始Coze工作流**
- **28节点功能**：100%还原原始Coze工作流的所有功能
- **微秒级精度**：时间轴计算精确到微秒，与原始工作流一致
- **智能分镜**：第一句单独分镜，后续每2句一组的精确分割
- **字幕智能分割**：25字符限制，标点符号优先级分割算法

### ✅ **高质量内容生成**
- **结构化文案**：5段式故事结构（悬念开场→身份代入→冲突升级→破局细节→主题收尾）
- **古代惊悚插画风格**：完全复刻的视觉风格配置
- **语音合成**：1.2倍速悬疑解说音色
- **2字标题提取**：自动生成简洁标题

### ✅ **专业视频制作**
- **5轨道音频**：配音+背景音乐+开场音效
- **多层视频合成**：场景图+主角图+动画效果
- **双字幕系统**：主字幕(7号字体)+标题字幕(40号字体)
- **奇偶交替动画**：1.0↔1.5缩放+主角2.0→1.2→1.0开场动画

## 🏗️ 系统架构

```
输入主题 → LLM内容生成 → 媒体批处理 → 时间轴构建 → 动画处理 → 视频合成
    ↓           ↓            ↓           ↓         ↓        ↓
 用户输入   4个LLM节点    3并发处理    微秒精度   关键帧    最终输出
```

## 🛠️ 安装配置

### **第一步：安装依赖节点**

```bash
# 1. 确保已安装 comfyui_LLM_party
cd ComfyUI/custom_nodes
git clone https://github.com/heshengtao/comfyui_LLM_party.git

# 2. 确保已安装 ComfyUI_RH_APICall  
git clone https://github.com/HM-RunningHub/ComfyUI_RH_APICall.git

# 3. 安装视频处理节点（可选，增强功能）
git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
git clone https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved.git

# 4. 本项目的自定义节点已经在 comfy_add_subtitles 目录中
```

### **第二步：配置API密钥**

在 `comfyui_LLM_party/config.ini` 中配置：

```ini
[API_KEYS]
# 必须配置 - LLM API
openrouter_api_key = your_openrouter_key_for_deepseek_v3

# 必须配置 - 图像生成 API  
runninghub_api_key = your_runninghub_api_key

# 可选配置 - 语音合成API
minimax_api_key = your_minimax_api_key
azure_api_key = your_azure_api_key
elevenlabs_api_key = your_elevenlabs_api_key
```

### **第三步：导入工作流**

1. 启动ComfyUI
2. 将 `story_video_generator_workflow.json` 拖拽到ComfyUI界面
3. 使用ComfyUI Manager安装缺失的节点

## 🎮 使用方法

### **基础使用**

1. **输入主题**：在"故事主题输入"节点中输入您想要的历史主题
   ```
   示例：秦始皇统一六国
   示例：唐太宗贞观之治
   示例：汉武帝北击匈奴
   ```

2. **配置API**：确保已正确配置所有必要的API密钥

3. **运行工作流**：点击"Queue Prompt"开始生成

4. **等待完成**：整个过程大约需要3-5分钟，取决于场景数量和API响应速度

### **高级配置**

#### **调整并发数量**
在 `StoryBatchMediaProcessor` 节点中：
```python
# 默认最大3并发，可根据API限制调整
self.max_concurrent = 3  # 改为 1-5 之间的值
```

#### **修改语音设置**
在批处理节点的 `voice_api_config` 参数中：
```json
{
  "voice_id": "7468512265134932019",  // 悬疑解说音色
  "speed_ratio": 1.2,                // 语速倍数
  "volume": 1.0                      // 音量
}
```

#### **自定义视觉风格**
在"图像提示词生成"节点的system_prompt中修改：
```
风格要求：古代惊悚插画风格 → 改为您想要的风格
```

## 📊 节点详细说明

### **阶段一：内容生成（4个LLM节点）**

| 节点 | 功能 | 输入 | 输出 | 模型 |
|------|------|------|------|------|
| 故事文案生成 | 生成1000字结构化故事 | 主题 | 完整文案 | DeepSeek-V3 |
| 主题提取 | 提取2字标题 | 文案 | 2字标题 | DeepSeek-V3 |
| 智能分镜 | 按规则分割场景 | 文案 | 场景JSON | DeepSeek-V3 |
| 图像提示词生成 | 生成绘画提示词 | 场景 | 提示词JSON | DeepSeek-V3-0324 |
| 主角形象描述 | 生成主角描述 | 文案 | 主角提示词 | DeepSeek-V3 |

### **阶段二：媒体生成（批处理+主角流水线）**

| 节点 | 功能 | 特点 |
|------|------|------|
| 批处理媒体生成 | 3并发生成图像+音频 | 异步并发，提升效率 |
| 主角图像生成 | RunningHub图像生成 | 1024x768分辨率 |
| 主角抠图 | 生成透明背景PNG | 用于叠加效果 |

### **阶段三：视频合成（时间轴+动画+合成）**

| 节点 | 功能 | 精度 |
|------|------|------|
| 时间轴构建 | 构建5种时间轴 | 微秒级精度 |
| 动画处理 | 生成关键帧动画 | 奇偶交替+主角特效 |
| 视频合成 | 最终多轨道合成 | 1440x1080输出 |

## ⚡ 性能优化

### **提升处理速度**
```python
# 1. 增加并发数（需要足够的API配额）
max_concurrent = 5  # 从3增加到5

# 2. 使用更快的模型
model = "gpt-4o-mini"  # 替代DeepSeek-V3用于简单任务

# 3. 减少场景数量
target_scene_count = 6  # 从8减少到6个场景
```

### **降低API成本**
```python
# 1. 使用缓存避免重复生成
enable_cache = True

# 2. 优化token使用
max_tokens = 512  # 对于简单任务减少token限制

# 3. 批量处理多个主题
# 一次性处理多个相关主题可以复用某些元素
```

## 🎯 输出格式

### **最终输出**
- **视频文件**：MP4格式，1440x1080分辨率，30fps
- **音频**：AAC编码，192kbps
- **字幕**：内嵌字幕，双轨道（主字幕+标题）
- **时长**：根据文案长度，通常2-4分钟

### **中间文件**
- **音频文件**：各场景的独立音频片段
- **图像文件**：场景图像+主角图像  
- **时间轴数据**：JSON格式的详细时间配置
- **合成配置**：完整的视频合成参数

## 🔧 故障排除

### **常见问题**

#### **1. API调用失败**
```
错误：API key not valid
解决：检查config.ini中的API密钥配置
```

#### **2. 并发限制错误**
```
错误：Rate limit exceeded
解决：降低max_concurrent值，或增加API配额
```

#### **3. JSON解析错误**
```
错误：Invalid JSON format
解决：检查LLM返回的JSON格式，可能需要调整prompt
```

#### **4. 视频合成失败**
```
错误：Video composition failed
解决：检查所有媒体文件是否正确生成
```

### **调试方法**

1. **检查日志**：查看ComfyUI控制台输出
2. **分步测试**：单独测试每个节点的输出
3. **验证API**：确保所有API服务正常
4. **检查依赖**：确保所有必要节点已安装

## 🎨 自定义扩展

### **添加新的视觉风格**
修改图像提示词模板：
```python
# 在图像提示词生成节点中
风格要求：
- 古代惊悚插画风格 → 水墨国画风格
- 颜色很深，黑暗中 → 淡雅清新，明亮色调
```

### **支持其他语言**
在各个LLM节点的system_prompt中添加：
```
- 支持中文、英文、日文等多语言输出
- 根据输入语言自动适配提示词风格
```

### **增加音效库**
扩展背景音乐和音效选择：
```python
background_music_options = [
    "故事背景音乐.MP3",
    "紧张悬疑音效.MP3", 
    "古典历史配乐.MP3"
]
```

## 📈 批量处理

### **配置文件批量生成**
创建主题列表文件：
```json
{
  "themes": [
    "秦始皇统一六国",
    "汉武帝北击匈奴", 
    "唐太宗贞观之治",
    "康熙智擒鳌拜"
  ],
  "settings": {
    "concurrent": 2,
    "quality": "high"
  }
}
```

### **自动化脚本**
```python
# 批量处理脚本示例
for theme in themes:
    workflow_result = run_comfyui_workflow(
        workflow_path="story_video_generator_workflow.json",
        input_theme=theme
    )
    print(f"Generated video for: {theme}")
```

## 🎉 预期效果

通过这个完整的ComfyUI实现，您将获得：

### **内容质量**
- **专业文案**：结构化的历史故事内容
- **统一视觉**：古代惊悚插画风格  
- **自然语音**：1.2倍速悬疑解说
- **精准字幕**：25字符智能分割

### **技术特性**
- **高度自动化**：从主题到成片全自动
- **批量处理**：支持大规模生产
- **参数可调**：每个环节都可独立优化
- **扩展性强**：基于ComfyUI生态易于扩展

### **商业价值**
- **内容创作**：历史教育、知识科普
- **营销应用**：品牌故事、产品宣传  
- **教育培训**：历史教学、文化传播
- **娱乐媒体**：短视频平台内容

---

**开始使用**：将工作流JSON文件导入ComfyUI，配置好API密钥，输入您的第一个历史主题，开始创造专业级的故事视频吧！

**技术支持**：如有问题，请检查ComfyUI控制台日志，确保所有依赖节点正确安装并配置了有效的API密钥。