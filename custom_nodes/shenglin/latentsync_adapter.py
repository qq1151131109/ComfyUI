"""
LatentSync 长视频适配器
用于将现有的 LatentSync 节点与长视频生成逻辑连接
"""

import torch
import numpy as np
import os
import tempfile
import folder_paths
import comfy.model_management
from .latentsync_long_video import AudioSegmentAnalyzer, VideoPostProcessor


class LatentSyncSegmentAdapter:
    """
    将音频切分为适合 LatentSync 的片段
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("AUDIO",),
                "segment_duration": ("FLOAT", {
                    "default": 2.0, 
                    "min": 1.0, 
                    "max": 3.0, 
                    "step": 0.1,
                    "display": "slider"
                }),
                "target_fps": ("INT", {
                    "default": 8,
                    "min": 4,
                    "max": 30,
                    "step": 1,
                    "display": "slider"
                }),
                "segment_index": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 999,
                    "step": 1
                }),
            }
        }
    
    RETURN_TYPES = ("AUDIO", "INT", "SEGMENT_INFO")
    RETURN_NAMES = ("audio_segment", "total_segments", "segment_info")
    FUNCTION = "extract_segment"
    CATEGORY = "shenglin/视频生成"
    
    def extract_segment(self, audio, segment_duration=2.0, target_fps=8, segment_index=0):
        """
        提取指定索引的音频片段
        """
        # 分析并切分音频
        segments = AudioSegmentAnalyzer.analyze_audio(audio, segment_duration, target_fps)
        
        # 确保索引有效
        if segment_index >= len(segments):
            print(f"警告：片段索引 {segment_index} 超出范围，使用最后一个片段")
            segment_index = len(segments) - 1
        
        segment = segments[segment_index]
        
        # 提取音频片段
        audio_segment = {
            'waveform': audio['waveform'][:, segment['start_sample']:segment['end_sample']],
            'sample_rate': audio['sample_rate']
        }
        
        # 片段信息
        segment_info = {
            'index': segment_index,
            'total': len(segments),
            'start_time': segment['start_time'],
            'end_time': segment['end_time'],
            'duration': segment['duration'],
            'fps': target_fps
        }
        
        print(f"提取片段 {segment_index + 1}/{len(segments)}")
        print(f"时间: {segment['start_time']:.2f}s - {segment['end_time']:.2f}s")
        
        return (audio_segment, len(segments), segment_info)


class LatentSyncVideoLooper:
    """
    循环视频以匹配音频长度
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "audio": ("AUDIO",),
                "fps": ("FLOAT", {
                    "default": 8.0,
                    "min": 1.0,
                    "max": 60.0,
                    "step": 0.1
                }),
                "loop_mode": (["repeat", "reverse", "smooth"],),
            }
        }
    
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "loop_video"
    CATEGORY = "shenglin/视频生成"
    
    def loop_video(self, images, audio, fps=8.0, loop_mode="repeat"):
        """
        循环视频帧以匹配音频长度
        """
        # 计算音频和视频时长
        audio_duration = audio['waveform'].shape[-1] / audio['sample_rate']
        video_duration = len(images) / fps
        
        if audio_duration <= video_duration:
            # 视频已经足够长
            return (images,)
        
        # 计算需要的总帧数
        target_frames = int(np.ceil(audio_duration * fps))
        current_frames = len(images)
        
        if loop_mode == "repeat":
            # 简单重复
            repeat_times = int(np.ceil(target_frames / current_frames))
            extended = images.repeat(repeat_times, 1, 1, 1)[:target_frames]
            
        elif loop_mode == "reverse":
            # 正反循环
            forward = images
            backward = torch.flip(images[1:-1], dims=[0])  # 去掉首尾避免重复
            cycle = torch.cat([forward, backward], dim=0)
            
            repeat_times = int(np.ceil(target_frames / len(cycle)))
            extended = cycle.repeat(repeat_times, 1, 1, 1)[:target_frames]
            
        elif loop_mode == "smooth":
            # 平滑循环（在结尾和开头之间创建过渡）
            extended_list = [images]
            remaining_frames = target_frames - current_frames
            
            while remaining_frames > 0:
                # 创建从最后一帧到第一帧的过渡
                transition_frames = min(remaining_frames, 8)  # 最多8帧过渡
                if transition_frames > 1:
                    weights = torch.linspace(0, 1, transition_frames).view(-1, 1, 1, 1).to(images.device)
                    transition = images[-1:] * (1 - weights) + images[0:1] * weights
                    extended_list.append(transition)
                    remaining_frames -= transition_frames
                
                # 添加完整循环
                if remaining_frames > 0:
                    frames_to_add = min(remaining_frames, current_frames)
                    extended_list.append(images[:frames_to_add])
                    remaining_frames -= frames_to_add
            
            extended = torch.cat(extended_list, dim=0)
        
        print(f"视频循环: {current_frames}帧 -> {len(extended)}帧 ({video_duration:.2f}s -> {audio_duration:.2f}s)")
        
        return (extended,)


class LatentSyncBatchProcessor:
    """
    批量处理多个视频片段并拼接
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "fade_frames": ("INT", {
                    "default": 2,
                    "min": 0,
                    "max": 10,
                    "step": 1
                }),
                "apply_color_correction": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "segment1": ("IMAGE",),
                "segment2": ("IMAGE",),
                "segment3": ("IMAGE",),
                "segment4": ("IMAGE",),
                "segment5": ("IMAGE",),
                "segment6": ("IMAGE",),
                "segment7": ("IMAGE",),
                "segment8": ("IMAGE",),
            }
        }
    
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "concatenate_segments"
    CATEGORY = "shenglin/视频生成"
    
    def concatenate_segments(self, fade_frames=2, apply_color_correction=True, **kwargs):
        """
        拼接多个视频片段
        """
        # 收集所有非空片段
        segments = []
        for i in range(1, 9):
            segment_key = f"segment{i}"
            if segment_key in kwargs and kwargs[segment_key] is not None:
                segments.append(kwargs[segment_key])
        
        if not segments:
            raise ValueError("至少需要一个视频片段")
        
        print(f"拼接 {len(segments)} 个视频片段...")
        
        # 拼接片段
        concatenated = VideoPostProcessor.concatenate_segments(segments, fade_frames)
        
        # 应用色彩校正
        if apply_color_correction and len(segments) > 1:
            print("应用色彩校正...")
            concatenated = VideoPostProcessor.apply_color_correction(concatenated)
        
        print(f"拼接完成：总帧数 {len(concatenated)}")
        
        return (concatenated,)


class AudioSegmentInfo:
    """
    显示音频分段信息
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("AUDIO",),
                "segment_duration": ("FLOAT", {
                    "default": 2.0,
                    "min": 1.0,
                    "max": 3.0,
                    "step": 0.1
                }),
                "fps": ("INT", {
                    "default": 8,
                    "min": 4,
                    "max": 30,
                    "step": 1
                }),
            }
        }
    
    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("segment_info", "total_segments")
    FUNCTION = "analyze_audio"
    CATEGORY = "shenglin/视频生成"
    OUTPUT_NODE = True
    
    def analyze_audio(self, audio, segment_duration=2.0, fps=8):
        """
        分析音频并返回分段信息
        """
        segments = AudioSegmentAnalyzer.analyze_audio(audio, segment_duration, fps)
        
        # 格式化输出信息
        info_lines = [
            f"音频总时长: {audio['waveform'].shape[-1] / audio['sample_rate']:.2f}秒",
            f"目标片段时长: {segment_duration}秒",
            f"总片段数: {len(segments)}",
            "",
            "片段详情:"
        ]
        
        for seg in segments:
            info_lines.append(
                f"  片段 {seg['id'] + 1}: {seg['start_time']:.2f}s - {seg['end_time']:.2f}s "
                f"(时长: {seg['duration']:.2f}s)"
            )
        
        info_text = "\n".join(info_lines)
        
        return (info_text, len(segments))


# 注册节点
NODE_CLASS_MAPPINGS = {
    "LatentSyncSegmentAdapter": LatentSyncSegmentAdapter,
    "LatentSyncVideoLooper": LatentSyncVideoLooper,
    "LatentSyncBatchProcessor": LatentSyncBatchProcessor,
    "AudioSegmentInfo": AudioSegmentInfo,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LatentSyncSegmentAdapter": "LatentSync音频分段",
    "LatentSyncVideoLooper": "LatentSync视频循环",
    "LatentSyncBatchProcessor": "LatentSync批量拼接",
    "AudioSegmentInfo": "音频分段信息",
}