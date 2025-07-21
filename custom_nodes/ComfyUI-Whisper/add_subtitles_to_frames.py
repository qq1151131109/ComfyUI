from PIL import ImageDraw, ImageFont, Image
from .utils import tensor2pil, pil2tensor, tensor2Mask
import math
import os
import re
import textwrap

FONT_DIR = os.path.join(os.path.dirname(__file__),"fonts")

class AddSubtitlesToFramesNode:
    
    # 预设颜色定义
    PRESET_COLORS = {
        "白色": (255, 255, 255),
        "黑色": (0, 0, 0),
        "红色": (255, 0, 0),
        "绿色": (0, 255, 0),
        "蓝色": (0, 0, 255),
        "黄色": (255, 255, 0),
        "青色": (0, 255, 255),
        "品红": (255, 0, 255),
        "橙色": (255, 165, 0),
        "紫色": (128, 0, 128),
        "粉色": (255, 192, 203),
        "灰色": (128, 128, 128),
        "浅灰": (192, 192, 192),
        "深灰": (64, 64, 64),
        "金色": (255, 215, 0),
        "银色": (192, 192, 192),
        "棕色": (139, 69, 19),
        "浅蓝": (173, 216, 230),
        "深蓝": (0, 0, 139),
        "浅绿": (144, 238, 144),
        "深绿": (0, 100, 0),
        "米色": (245, 245, 220),
        "珊瑚色": (255, 127, 80),
        "天蓝色": (135, 206, 235),
        "透明": (0, 0, 0)  # 特殊标记，用于背景
    }
    
    @classmethod
    def get_language_fonts(cls):
        """获取按语种分类的字体列表"""
        language_fonts = {}
        
        # 定义语种映射
        language_map = {
            "english": "English",
            "chinese": "中文",
            "japanese": "日本語",
            "korean": "한국어",
            "arabic": "العربية",
            "hindi": "हिन्दी",
            "thai": "ไทย",
            "vietnamese": "Tiếng Việt",
            "russian": "Русский",
            "general": "General/通用",
            "artistic": "Artistic/艺术",
            "special": "Special/特殊"
        }
        
        # 扫描字体目录
        for lang_dir in os.listdir(FONT_DIR):
            lang_path = os.path.join(FONT_DIR, lang_dir)
            if os.path.isdir(lang_path):
                fonts = [f for f in os.listdir(lang_path) if f.endswith(('.ttf', '.ttc', '.otf'))]
                if fonts:
                    display_name = language_map.get(lang_dir.lower(), lang_dir)
                    for font in fonts:
                        language_fonts[f"{display_name}/{font}"] = os.path.join(lang_dir, font)
        
        # 如果没有分类字体，使用根目录字体
        if not language_fonts:
            root_fonts = [f for f in os.listdir(FONT_DIR) if f.endswith(('.ttf', '.ttc', '.otf'))]
            for font in root_fonts:
                language_fonts[font] = font
                
        return language_fonts
    
    @classmethod
    def INPUT_TYPES(s):
        font_dict = s.get_language_fonts()
        font_choices = list(font_dict.keys())
        if not font_choices:
            font_choices = ["default"]

        return {
            "required": { 
                "images": ("IMAGE",),
                "alignment" : ("whisper_alignment",),
                "font_language_family": (font_choices,),
                "font_size": ("INT",{
                    "default": 100,
                    "step":5,
                    "display": "number"
                }),
                "font_color": (list(s.PRESET_COLORS.keys()),{
                    "default": "白色"
                }),
                "background_color": (list(s.PRESET_COLORS.keys()),{
                    "default": "黑色"
                }),
                "enable_background": ("BOOLEAN", {
                    "default": True,
                    "label": "启用背景"
                }),
                "background_alpha": ("FLOAT",{
                    "default": 0.7,
                    "min": 0.0,
                    "max": 1.0,
                    "step":0.05,
                    "display": "number"
                }),
                "horizontal_align": (["左对齐", "居中", "右对齐"],{
                    "default": "居中"
                }),
                "vertical_position": (["顶部边缘", "顶部-10%", "顶部-20%", "中上-30%", "居中-50%", "中下-70%", "底部-80%", "底部-90%", "底部边缘"],{
                    "default": "底部-90%"
                }),
                "video_fps": ("FLOAT",{
                    "default": 24.0,
                    "step":1,
                    "display": "number"
                }),
                "padding": ("INT",{
                    "default": 10,
                    "min": 0,
                    "max": 100,
                    "step":5,
                    "display": "number"
                }),
                "max_width_ratio": ("FLOAT",{
                    "default": 0.9,
                    "min": 0.3,
                    "max": 1.0,
                    "step":0.05,
                    "display": "number",
                    "label": "最大宽度比例"
                }),
                "auto_wrap": ("BOOLEAN", {
                    "default": True,
                    "label": "自动换行"
                }),
                "margin": ("INT",{
                    "default": 50,
                    "min": 0,
                    "max": 200,
                    "step":10,
                    "display": "number",
                    "label": "边距"
                }),
                "max_chars_per_screen": ("INT",{
                    "default": 30,
                    "min": 10,
                    "max": 100,
                    "step":5,
                    "display": "number",
                    "label": "每屏最大字数"
                }),
                "split_by_sentence": ("BOOLEAN", {
                    "default": True,
                    "label": "按句子分割"
                }),
            }
        }

    RETURN_TYPES = ("IMAGE", "MASK", "IMAGE", "subtitle_coord", )
    RETURN_NAMES = ("IMAGE","MASK", "cropped_subtitles","subtitle_coord",)
    FUNCTION = "add_subtitles_to_frames"
    CATEGORY = "whisper"


    @staticmethod
    def split_subtitle_content(text, max_chars, split_by_sentence=True):
        """
        分割字幕内容，保证每段不超过最大字数
        """
        if len(text) <= max_chars:
            return [text]
        
        segments = []
        
        if split_by_sentence:
            # 定义句子结束标记
            sentence_endings = ['。', '！', '？', '.', '!', '?', '；', ';']
            
            # 先按句子分割
            sentences = []
            current_sentence = ""
            
            for char in text:
                current_sentence += char
                if char in sentence_endings:
                    sentences.append(current_sentence)
                    current_sentence = ""
            
            if current_sentence:
                sentences.append(current_sentence)
            
            # 合并句子，但不超过最大字数
            current_segment = ""
            for sentence in sentences:
                if len(current_segment) + len(sentence) <= max_chars:
                    current_segment += sentence
                else:
                    if current_segment:
                        segments.append(current_segment.strip())
                    # 如果单个句子太长，需要强制分割
                    if len(sentence) > max_chars:
                        # 按逗号或空格再分
                        sub_parts = sentence.replace('，', '，|').replace(',', ',|').replace(' ', ' |').split('|')
                        temp_segment = ""
                        for part in sub_parts:
                            if len(temp_segment) + len(part) <= max_chars:
                                temp_segment += part
                            else:
                                if temp_segment:
                                    segments.append(temp_segment.strip())
                                temp_segment = part
                        if temp_segment:
                            segments.append(temp_segment.strip())
                    else:
                        current_segment = sentence
            
            if current_segment:
                segments.append(current_segment.strip())
        else:
            # 简单按字数分割
            for i in range(0, len(text), max_chars):
                segments.append(text[i:i+max_chars])
        
        return segments
    
    def add_subtitles_to_frames(self, images, alignment, font_language_family, font_size, 
                                font_color, background_color, enable_background, background_alpha,
                                horizontal_align, vertical_position, video_fps, padding,
                                max_width_ratio, auto_wrap, margin, max_chars_per_screen, split_by_sentence):
        pil_images = tensor2pil(images)

        pil_images_with_text = []
        cropped_pil_images_with_text = []
        pil_images_masks = []
        subtitle_coord = []

        # 获取实际字体路径
        font_dict = self.get_language_fonts()
        actual_font_path = font_dict.get(font_language_family, font_language_family)
        font_full_path = os.path.join(FONT_DIR, actual_font_path)
        
        # 如果文件不存在，尝试使用默认字体
        if not os.path.exists(font_full_path):
            # 尝试查找任何可用字体
            for root, dirs, files in os.walk(FONT_DIR):
                for file in files:
                    if file.endswith(('.ttf', '.ttc', '.otf')):
                        font_full_path = os.path.join(root, file)
                        break
                if os.path.exists(font_full_path):
                    break
        
        font = ImageFont.truetype(font_full_path, font_size)
        original_font_size = font_size  # 保存原始字体大小
        
        # 获取预设颜色
        font_color_rgb = self.PRESET_COLORS.get(font_color, (255, 255, 255))
        background_color_rgb = self.PRESET_COLORS.get(background_color, (0, 0, 0))
        
        # 设置带透明度的背景颜色
        background_color_rgba = background_color_rgb + (int(background_alpha * 255),)

        if len(alignment) == 0:
            pil_images_with_text = pil_images
            cropped_pil_images_with_text = pil_images
            subtitle_coord.extend([(0,0,0,0)]*len(pil_images))

            # create mask
            width, height = pil_images[0].size
            black_img = Image.new('RGB', (width, height), 'black')
            pil_images_masks.extend([black_img]*len(pil_images))
        

        # 预处理字幕，分割过长的内容
        processed_alignment = []
        for align_obj in alignment:
            text_segments = self.split_subtitle_content(
                align_obj["value"], 
                max_chars_per_screen, 
                split_by_sentence
            )
            
            # 计算每段的时间
            total_duration = align_obj["end"] - align_obj["start"]
            segment_duration = total_duration / len(text_segments)
            
            for idx, segment in enumerate(text_segments):
                processed_alignment.append({
                    "start": align_obj["start"] + idx * segment_duration,
                    "end": align_obj["start"] + (idx + 1) * segment_duration,
                    "value": segment
                })
        
        last_frame_no = 0
        for i in range(len(processed_alignment)):
            alignment_obj = processed_alignment[i]
            start_frame_no = math.floor(alignment_obj["start"] * video_fps)
            end_frame_no = math.floor(alignment_obj["end"] * video_fps)
            
            # 确保帧号不超过图像数量
            start_frame_no = min(start_frame_no, len(pil_images) - 1)
            end_frame_no = min(end_frame_no, len(pil_images))

            # create images without text
            for i in range(last_frame_no, start_frame_no):
                # 边界检查
                if i >= len(pil_images):
                    break
                img = pil_images[i].convert("RGB")
                width, height = img.size
                pil_images_with_text.append(img)

                # create mask + cropped image
                black_img = Image.new('RGB', (width, height), 'black')
                pil_images_masks.append(black_img)
                black_img = Image.new('RGB', (1, 1), 'black') # to prevent max() from considering these images, use very small size
                cropped_pil_images_with_text.append(black_img)  
                subtitle_coord.append((0,0,0,0))


            for i in range(start_frame_no,end_frame_no):
                # 边界检查，防止索引超出范围
                if i >= len(pil_images):
                    break
                img = pil_images[i].convert("RGB")
                width, height = img.size

                d = ImageDraw.Draw(img)
                
                # 每个字幕段重置字体大小
                font = ImageFont.truetype(font_full_path, original_font_size)
                
                # 准备文本
                text = alignment_obj["value"]
                max_text_width = int(width * max_width_ratio) - 2 * margin
                
                # 如果启用自动换行
                if auto_wrap:
                    # 估算每个字符的平均宽度
                    test_text = "测"  # 使用一个中文字符作为参考
                    test_bbox = d.textbbox((0, 0), test_text, font=font)
                    avg_char_width = test_bbox[2] - test_bbox[0]
                    
                    # 估算每行可以放多少个字符
                    chars_per_line = max(1, int(max_text_width / avg_char_width))
                    
                    # 分割文本
                    lines = []
                    current_line = ""
                    for char in text:
                        test_line = current_line + char
                        test_bbox = d.textbbox((0, 0), test_line, font=font)
                        if test_bbox[2] - test_bbox[0] > max_text_width and current_line:
                            lines.append(current_line)
                            current_line = char
                        else:
                            current_line = test_line
                    if current_line:
                        lines.append(current_line)
                    
                    # 如果换行后有多行，合并成多行文本
                    if len(lines) > 1:
                        text = "\n".join(lines)
                else:
                    # 不换行，但检查是否超出
                    text_bbox = d.textbbox((0, 0), text, font=font)
                    text_width = text_bbox[2] - text_bbox[0]
                    if text_width > max_text_width:
                        # 如果超出，缩小字体
                        scale_factor = max_text_width / text_width
                        adjusted_font_size = int(font_size * scale_factor * 0.95)  # 0.95为安全系数
                        font = ImageFont.truetype(font_full_path, adjusted_font_size)

                # 获取文本边界框
                text_bbox = d.textbbox((0, 0), text, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                
                # 计算水平位置
                if horizontal_align == "左对齐":
                    actual_x = margin
                elif horizontal_align == "居中":
                    actual_x = (width - text_width) / 2
                else:  # 右对齐
                    actual_x = width - text_width - margin
                
                # 计算垂直位置
                if vertical_position == "顶部边缘":
                    actual_y = margin
                elif vertical_position == "顶部-10%":
                    actual_y = height * 0.1
                elif vertical_position == "顶部-20%":
                    actual_y = height * 0.2
                elif vertical_position == "中上-30%":
                    actual_y = height * 0.3
                elif vertical_position == "居中-50%":
                    actual_y = (height - text_height) / 2
                elif vertical_position == "中下-70%":
                    actual_y = height * 0.7 - text_height
                elif vertical_position == "底部-80%":
                    actual_y = height * 0.8 - text_height
                elif vertical_position == "底部-90%":
                    actual_y = height * 0.9 - text_height
                else:  # 底部边缘
                    actual_y = height - text_height - margin
                
                
                # 边界检测和调整
                # 左边界
                if actual_x < margin:
                    actual_x = margin
                
                # 右边界
                text_width = text_bbox[2] - text_bbox[0]
                if actual_x + text_width > width - margin:
                    actual_x = width - margin - text_width
                
                # 上边界
                if actual_y < margin:
                    actual_y = margin
                
                # 下边界
                text_height = text_bbox[3] - text_bbox[1]
                if actual_y + text_height > height - margin:
                    actual_y = height - margin - text_height
                
                # 获取最终文本边界框（考虑居中）
                final_bbox = d.textbbox((actual_x, actual_y), text, font=font)
                
                # 如果需要背景，先绘制背景
                if enable_background and background_alpha > 0:
                    # 创建带透明度的图层
                    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
                    overlay_draw = ImageDraw.Draw(overlay)
                    
                    # 绘制带padding的背景矩形
                    bg_bbox = (
                        final_bbox[0] - padding,
                        final_bbox[1] - padding,
                        final_bbox[2] + padding,
                        final_bbox[3] + padding
                    )
                    overlay_draw.rectangle(bg_bbox, fill=background_color_rgba)
                    
                    # 将透明图层合并到原图
                    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
                    d = ImageDraw.Draw(img)
                
                # 绘制文本
                if "\n" in text:
                    # 多行文本需要特殊处理
                    lines = text.split("\n")
                    line_height = font.getbbox("A")[3] + 5  # 行高
                    for idx, line in enumerate(lines):
                        line_y = actual_y + idx * line_height
                        # 每行都需要单独计算位置
                        line_bbox = d.textbbox((0, 0), line, font=font)
                        line_width = line_bbox[2] - line_bbox[0]
                        
                        if horizontal_align == "左对齐":
                            line_x = actual_x
                        elif horizontal_align == "居中":
                            line_x = (width - line_width) / 2
                        else:  # 右对齐
                            line_x = width - line_width - margin
                        d.text((line_x, line_y), line, fill=font_color_rgb, font=font)
                else:
                    d.text((actual_x, actual_y), text, fill=font_color_rgb, font=font)
                pil_images_with_text.append(img)

                # create mask
                black_img = Image.new('RGB', (width, height), 'black')
                d = ImageDraw.Draw(black_img)
                # 处理多行文本的蒙版
                if "\n" in text:
                    lines = text.split("\n")
                    line_height = font.getbbox("A")[3] + 5
                    for idx, line in enumerate(lines):
                        line_y = actual_y + idx * line_height
                        line_bbox = d.textbbox((0, 0), line, font=font)
                        line_width = line_bbox[2] - line_bbox[0]
                        
                        if horizontal_align == "左对齐":
                            line_x = actual_x
                        elif horizontal_align == "居中":
                            line_x = (width - line_width) / 2
                        else:  # 右对齐
                            line_x = width - line_width - margin
                        d.text((line_x, line_y), line, fill="white", font=font)
                else:
                    d.text((actual_x, actual_y), text, fill="white",font=font)    
                pil_images_masks.append(black_img)    

                # crop subtitles to black frame
                text_bbox = d.textbbox((actual_x, actual_y), text, font=font)
                cropped_text_frame = black_img.crop(text_bbox)
                cropped_pil_images_with_text.append(cropped_text_frame)
                subtitle_coord.append(text_bbox)

            
            last_frame_no = end_frame_no

        # add missing frames with no text at end
        for i in range(len(pil_images_with_text),len(pil_images)):
            pil_images_with_text.append(pil_images[i])
            width,height = pil_images[i].size

            # create mask + cropped image
            black_img = Image.new('RGB', (width, height), 'black')
            pil_images_masks.append(black_img)
            black_img = Image.new('RGB', (1, 1), 'black') # to prevent max() from considering these images, use very small size
            cropped_pil_images_with_text.append(black_img)  
            subtitle_coord.append((0,0,0,0))

        # make cropped images same size
        cropped_pil_images_with_text_normalised = []
        max_width = max(img.width for img in cropped_pil_images_with_text)
        max_height = max(img.height for img in cropped_pil_images_with_text)

        for img in cropped_pil_images_with_text:
            blank_frame = Image.new("RGB", (max_width, max_height), "black")
            blank_frame.paste(img, (0,0))
            cropped_pil_images_with_text_normalised.append(blank_frame)


        tensor_images = pil2tensor(pil_images_with_text)
        cropped_pil_images_with_text_normalised = pil2tensor(cropped_pil_images_with_text_normalised)
        tensor_masks = tensor2Mask(pil2tensor(pil_images_masks))

        return (tensor_images,tensor_masks,cropped_pil_images_with_text_normalised,subtitle_coord,)
