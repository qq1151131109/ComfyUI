# Add Subtitles To Frames 节点参数说明

## 参数列表

### 基础参数

**images**
- 输入的图像序列

**alignment**  
- 字幕时间轴数据（从 Whisper 节点获取）

**video_fps**
- 视频帧率，默认 24.0
- 根据实际视频调整

---

### 字体设置

**font_language_family**
- 选择字体，按语言分类显示
- 中文推荐：中文/SourceHanSansSC-Regular.otf
- 英文推荐：English/Inter-Regular.ttf

**font_size**
- 字体大小，默认 100
- 建议范围：60-120
- 太小看不清，太大占画面

---

### 颜色设置

**font_color**
- 文字颜色，默认白色
- 深色背景用白色/黄色
- 浅色背景用黑色/深蓝

**background_color**
- 背景颜色，默认黑色
- 通常用黑色或深灰

**enable_background**
- 是否显示背景，默认开启
- 关闭后只有文字，可能看不清

**background_alpha**
- 背景透明度，默认 0.7
- 0 = 完全透明，1 = 完全不透明
- 建议 0.5-0.8

---

### 位置设置

**horizontal_align**
- 水平对齐方式，默认「居中」
- 可选项：
  - **左对齐**：文字靠左边显示
  - **居中**：文字水平居中
  - **右对齐**：文字靠右边显示

**vertical_position**
- 垂直位置预设，默认「底部-90%」
- 可选项（从上到下）：
  - **顶部边缘**：紧贴画面顶部
  - **顶部-10%**：距离顶部 10% 的位置
  - **顶部-20%**：距离顶部 20% 的位置（适合副标题）
  - **中上-30%**：距离顶部 30% 的位置
  - **居中-50%**：画面正中央（适合标题、提示）
  - **中下-70%**：距离顶部 70% 的位置
  - **底部-80%**：距离顶部 80% 的位置
  - **底部-90%**：距离顶部 90% 的位置（常用字幕位置）
  - **底部边缘**：紧贴画面底部

**margin**
- 距离边缘的间距，默认 50
- 防止字幕贴边

**padding**
- 背景内边距，默认 10
- 文字与背景边缘的距离

---

### 文本处理

**max_chars_per_screen**
- 每屏最多显示字数，默认 30
- 中文建议 20-40
- 英文建议 40-80
- 越少越容易读

**split_by_sentence**
- 按句子分割，默认开启
- 开启：在句号、问号等处断开
- 关闭：强制按字数断开

**auto_wrap**
- 自动换行，默认开启
- 防止文字超出画面

**max_width_ratio**
- 字幕最大宽度占画面比例，默认 0.9
- 0.9 = 占画面宽度的 90%
- 减小此值可增加两侧留白

---

## 常用配置

### 电影字幕
```
font_size: 80
font_color: 白色
background_color: 黑色
background_alpha: 0.7
horizontal_align: 居中
vertical_position: 底部-90%
max_chars_per_screen: 30
```

### 标题文字
```
font_size: 120
font_color: 白色
enable_background: False
horizontal_align: 居中
vertical_position: 居中-50%
max_chars_per_screen: 20
```

### 新闻字幕
```
font_size: 70
font_color: 白色
background_color: 蓝色
background_alpha: 0.9
horizontal_align: 左对齐
vertical_position: 底部-90%
max_chars_per_screen: 40
```

### 社交媒体
```
font_size: 100
font_color: 黄色
background_color: 黑色
background_alpha: 0.8
horizontal_align: 居中
vertical_position: 中下-70%
max_chars_per_screen: 25
```

### 视频开场标题
```
font_size: 150
font_color: 白色
enable_background: True
background_color: 黑色
background_alpha: 0.5
horizontal_align: 居中
vertical_position: 居中-50%
max_chars_per_screen: 15
```

### 双语字幕（上方）
```
font_size: 60
font_color: 黄色
background_color: 黑色
background_alpha: 0.7
horizontal_align: 居中
vertical_position: 顶部-10%
max_chars_per_screen: 40
```

---

## 调试技巧

1. **字幕看不清**
   - 增加 font_size
   - 提高 background_alpha
   - 换对比度更高的颜色

2. **字幕超出画面**
   - 减少 max_chars_per_screen
   - 减小 max_width_ratio
   - 确保 auto_wrap 开启

3. **字幕太挤**
   - 增加 padding
   - 增加 margin
   - 减少 max_chars_per_screen

4. **时间不对**
   - 检查 video_fps 是否正确
   - 确认 alignment 数据正确

5. **位置调整**
   - 使用垂直位置预设快速定位
   - 底部-90% 是最常用的字幕位置
   - 标题类文字使用居中-50%
   - 双语字幕可以一个在顶部-10%，一个在底部-90%

---

## 技术实现

本节点使用 PIL (Pillow) 库实现字幕渲染：
- 逐帧处理图像，在每帧上绘制文本
- 支持透明背景层合成
- 支持多种字体格式（TTF/OTF）
- 自动处理多行文本对齐
- 生成字幕蒙版用于后续处理