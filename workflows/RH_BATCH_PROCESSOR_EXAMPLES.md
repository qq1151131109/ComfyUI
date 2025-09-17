# RunningHub Batch Processor 使用示例

## 🎯 简化设计理念

新的 `RHBatchProcessor` 节点采用简洁直观的设计：
- **单类型数据**：只有一个字段时自动处理，无需配置
- **双类型数据**：用户直接指定字段名，程序读取对应内容批量执行

## 📋 输入参数说明

### **必需参数：**
- `rh_api_key`: RunningHub API密钥
- `rh_base_url`: API基础URL  
- `workflow_id`: RunningHub工作流ID
- `batch_data`: JSON格式的批量数据

### **可选参数：**
- `image_field`: 图像字段名（双类型数据时指定）
- `audio_field`: 音频字段名（双类型数据时指定）
- `concurrency_limit`: 并发数限制（默认3）
- `run_timeout`: 任务超时时间（默认600秒）
- `use_rtx4090_48g`: 是否使用高端实例
- `output_type`: 输出类型（images/audio/mixed）

## 🚀 使用方式

### **方式1：单字段数据（零配置）**

```json
// 只生成图像
batch_data: [
  {"prompt": "古代惊悚插画风格：孙悟空紧锁眉头..."},
  {"prompt": "一个美丽的风景画..."},
  {"prompt": "科幻场景描述..."}
]

// 参数设置
image_field: ""  // 留空
audio_field: ""  // 留空
output_type: "images"
```

```json
// 只生成音频
batch_data: [
  {"text": "西游记里，孙悟空真的能一眼识破妖怪伪装吗？"},
  {"text": "这是要转换为语音的文本..."},
  {"text": "配音文案内容..."}
]

// 参数设置  
image_field: ""  // 留空
audio_field: ""  // 留空
output_type: "audio"
```

---

### **方式2：双字段数据（用户指定）**

```json
// 同时生成图像和音频
batch_data: [
  {
    "desc_promopt": "古代惊悚插画风格：孙悟空紧锁眉头...",
    "cap": "西游记里，孙悟空真的能一眼识破妖怪伪装吗？"
  },
  {
    "image_description": "一个美丽的风景画...",
    "audio_script": "这是要转换为语音的文本..."
  }
]

// 参数设置
image_field: "desc_promopt"  // 用户指定图像字段名
audio_field: "cap"          // 用户指定音频字段名  
output_type: "mixed"
```

```json
// 自定义字段名
batch_data: [
  {
    "my_visual_content": "科幻场景描述...",
    "my_voice_script": "配音内容...",
    "other_data": "其他不相关数据"
  }
]

// 参数设置
image_field: "my_visual_content"  // 用户指定
audio_field: "my_voice_script"    // 用户指定
output_type: "mixed"
```

---

### **方式3：多字段数据（按顺序自动选择）**

```json
// 有多个字段但用户不想手动指定
batch_data: [
  {
    "field_a": "图像描述内容",
    "field_b": "音频脚本内容", 
    "field_c": "其他数据"
  }
]

// 参数设置
image_field: ""  // 留空，自动选择第一个字段 field_a
audio_field: ""  // 留空，自动选择第二个字段 field_b  
output_type: "mixed"
```

## 📊 处理逻辑

### **字段检测规则：**

1. **只有1个字段**：
   - 根据 `output_type` 自动判断用途
   - `output_type="images"` → 该字段用于图像生成
   - `output_type="audio"` → 该字段用于音频生成

2. **有2个或更多字段**：
   - 用户指定了 `image_field`/`audio_field` → 使用指定字段
   - 用户未指定 → 按顺序自动选择前两个字段

3. **输出格式**：
   - 图像：ComfyUI IMAGE张量格式
   - 音频：ComfyUI AUDIO字典格式 
   - 元数据：处理信息和错误日志

## ✅ 关键优势

1. **✅ 极简设计**：单字段零配置，双字段直接指定
2. **✅ 用户控制**：不做智能猜测，用户明确指定字段用途
3. **✅ 灵活支持**：支持任意字段名和数据结构
4. **✅ 向后兼容**：原有 `desc_promopt`/`cap` 格式完全支持
5. **✅ 原生输出**：直接输出ComfyUI格式数据
6. **✅ 批量高效**：3并发异步处理

## 🎉 实际使用示例

### **故事视频生成（原场景）**
```
batch_data: '[{"desc_promopt": "古代场景...", "cap": "旁白文案..."}]'
image_field: "desc_promopt"
audio_field: "cap"  
output_type: "mixed"
```

### **图像批量生成**
```  
batch_data: '[{"prompt": "cat"}, {"prompt": "dog"}]'
image_field: ""  // 留空
output_type: "images"
```

### **音频批量生成**
```
batch_data: '[{"text": "你好"}, {"text": "再见"}]'
audio_field: ""  // 留空  
output_type: "audio"
```

简洁明了，用户完全掌控！ 🎬