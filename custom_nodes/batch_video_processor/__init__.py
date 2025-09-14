"""
批量视频处理扩展
支持批量上传、切分处理、批量下载视频文件
"""

from .nodes import (
    BatchVideoLoader, BatchVideoComposer, BatchVideoCutter, 
    BatchVideoCropper, VideoNormalizer, TraverseVideoConcatenator,
    BatchVideoDownloader, VideoStaticCleaner, GameHighlightExtractor,
    VideoThumbnailGenerator, BatchLLMGenerator, BatchTTSGenerator,
    SmartVideoCutterWithAudio
)

# 节点映射
NODE_CLASS_MAPPINGS = {
    "BatchVideoLoader": BatchVideoLoader,
    "BatchVideoComposer": BatchVideoComposer,
    "BatchVideoCutter": BatchVideoCutter,
    "BatchVideoCropper": BatchVideoCropper,
    "VideoNormalizer": VideoNormalizer,
    "TraverseVideoConcatenator": TraverseVideoConcatenator,
    "BatchVideoDownloader": BatchVideoDownloader,
    "VideoStaticCleaner": VideoStaticCleaner,
    "GameHighlightExtractor": GameHighlightExtractor,
    "VideoThumbnailGenerator": VideoThumbnailGenerator,
    "BatchLLMGenerator": BatchLLMGenerator,
    "BatchTTSGenerator": BatchTTSGenerator,
    "SmartVideoCutterWithAudio": SmartVideoCutterWithAudio,
}

# 节点显示名称
NODE_DISPLAY_NAME_MAPPINGS = {
    "BatchVideoLoader": "🎬 批量素材加载器",
    "BatchVideoComposer": "🎞️ 批量视频合成器", 
    "BatchVideoCutter": "✂️ 批量视频切分器",
    "BatchVideoCropper": "🔲 批量视频裁剪器",
    "VideoNormalizer": "⚖️ 视频标准化处理器",
    "TraverseVideoConcatenator": "🔗 遍历拼接处理器",
    "BatchVideoDownloader": "📥 批量视频下载器",
    "VideoStaticCleaner": "🧹 视频静止片段清理器",
    "GameHighlightExtractor": "🎮 游戏精彩片段提取器",
    "VideoThumbnailGenerator": "🖼️ 视频缩略图生成器",
    "BatchLLMGenerator": "🤖 批量LLM文案生成器",
    "BatchTTSGenerator": "🎤 批量TTS语音生成器", 
    "SmartVideoCutterWithAudio": "🎵 智能视频音频切分器",
}

# 指定前端扩展目录
WEB_DIRECTORY = "js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]