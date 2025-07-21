""" 
@title: IndexTTS for ComfyUI
@author: ComfyUI-Index-TTS
@description: ComfyUI接口的工业级零样本文本到语音合成系统
"""

import os
import sys

# 确保当前目录在导入路径中
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 导入节点定义
from .nodes import IndexTTSNode
from .audio_enhancement import AudioCleanupNode
from .timbre_audio_loader import TimbreAudioLoader
from .novel_text_parser import NovelTextStructureNode  # 导入小说文本结构化节点
from .index_tts_pro import IndexTTSProNode  # 导入增强版TTS节点

# 注册ComfyUI节点
NODE_CLASS_MAPPINGS = {
    "IndexTTSNode": IndexTTSNode,
    "AudioCleanupNode": AudioCleanupNode,
    "TimbreAudioLoader": TimbreAudioLoader,
    "NovelTextStructureNode": NovelTextStructureNode,  # 添加小说文本结构化节点
    "IndexTTSProNode": IndexTTSProNode,             # 添加增强版TTS节点
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "IndexTTSNode": "Index TTS",
    "AudioCleanupNode": "Audio Cleaner",
    "TimbreAudioLoader": "Timbre音频加载器",
    "NovelTextStructureNode": "小说文本结构化",   # 添加小说文本结构化节点显示名称
    "IndexTTSProNode": "Index TTS Pro",         # 添加增强版TTS节点显示名称
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
