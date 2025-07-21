#!/usr/bin/env python3
"""
测试 AddSubtitlesToFrames 节点的功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from PIL import Image
import torch
import numpy as np
from add_subtitles_to_frames import AddSubtitlesToFramesNode

def create_test_images(num_frames=10, width=1920, height=1080):
    """创建测试图像"""
    images = []
    for i in range(num_frames):
        # 创建渐变背景
        img = Image.new('RGB', (width, height), color=(100 + i*20, 100, 100))
        images.append(np.array(img))
    
    # 转换为tensor格式 (batch, height, width, channels)
    tensor = torch.tensor(np.stack(images)).float() / 255.0
    return tensor

def create_test_alignment():
    """创建测试字幕时间轴"""
    return [
        {"start": 0.0, "end": 2.0, "value": "你好，世界！这是一个测试长字幕的例子。"},
        {"start": 2.0, "end": 4.0, "value": "这是一个非常长的句子，用来测试自动分割功能是否正常工作。它应该被分成多个部分显示。"},
        {"start": 4.0, "end": 6.0, "value": "Hello, this is a long English sentence that should be split into multiple parts for better display."},
        {"start": 6.0, "end": 8.0, "value": "最后一个测试：中文、English、日本語、한국어混合的长句子！"}
    ]

def test_subtitles():
    """测试字幕功能"""
    print("初始化节点...")
    node = AddSubtitlesToFramesNode()
    
    print("创建测试数据...")
    images = create_test_images()
    alignment = create_test_alignment()
    
    print("可用字体列表:")
    fonts = node.get_language_fonts()
    for font_name in fonts:
        print(f"  - {font_name}")
    
    # 选择一个中文字体
    chinese_font = None
    for font_name in fonts:
        if "中文" in font_name or "chinese" in font_name.lower():
            chinese_font = font_name
            break
    
    if not chinese_font:
        chinese_font = list(fonts.keys())[0] if fonts else "default"
    
    print(f"\n使用字体: {chinese_font}")
    
    print("\n测试参数:")
    print(f"  - 文字颜色: 黄色")
    print(f"  - 背景颜色: 黑色")
    print(f"  - 背景透明度: 0.7")
    print(f"  - 内边距: 15")
    print(f"  - 水平对齐: 居中")
    print(f"  - 垂直位置: 底部")
    
    try:
        # 执行节点处理
        results = node.add_subtitles_to_frames(
            images=images,
            alignment=alignment,
            font_language_family=chinese_font,
            font_size=80,
            font_color="黄色",
            background_color="黑色",
            enable_background=True,
            background_alpha=0.7,
            horizontal_align="居中",
            vertical_position="底部",
            video_fps=1.0,
            padding=15,
            max_width_ratio=0.9,
            auto_wrap=True,
            margin=50,
            max_chars_per_screen=30,
            split_by_sentence=True
        )
        
        processed_images, masks, cropped_subtitles, subtitle_coords = results
        
        print("\n处理完成!")
        print(f"  - 输出图像数量: {processed_images.shape[0]}")
        print(f"  - 蒙版数量: {masks.shape[0]}")
        print(f"  - 字幕坐标: {len(subtitle_coords)}")
        
        # 保存第一帧作为示例
        if processed_images.shape[0] > 0:
            first_frame = processed_images[0].numpy()
            first_frame = (first_frame * 255).astype(np.uint8)
            img = Image.fromarray(first_frame)
            img.save("/tmp/subtitle_test_output.png")
            print(f"\n示例输出已保存到: /tmp/subtitle_test_output.png")
        
        return True
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_subtitles()
    if success:
        print("\n✅ 测试通过!")
    else:
        print("\n❌ 测试失败!")