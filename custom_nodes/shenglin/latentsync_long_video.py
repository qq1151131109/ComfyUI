"""
LatentSync 长视频生成节点
实现稳定的长视频生成方案：低帧率生成 + 智能分段 + 后期插帧
"""

import torch
import numpy as np
import os
import json
import tempfile
import shutil
from typing import List, Dict, Tuple, Optional
import folder_paths
import comfy.model_management
from PIL import Image
import torchaudio
import cv2


class AudioSegmentAnalyzer:
    """音频分析和智能切分"""
    
    @staticmethod
    def analyze_audio(audio_data: Dict, target_segment_duration: float = 2.0, fps: int = 8) -> List[Dict]:
        """
        分析音频并在自然断点处切分
        
        Args:
            audio_data: 包含 waveform 和 sample_rate 的字典
            target_segment_duration: 目标片段时长（秒）
            fps: 视频帧率
            
        Returns:
            分段信息列表
        """
        waveform = audio_data['waveform']
        sample_rate = audio_data['sample_rate']
        
        # 转换为单声道以便分析
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)
        
        # 计算音频总时长
        total_duration = waveform.shape[-1] / sample_rate
        
        # 计算能量包络（用于检测静音）
        window_size = int(0.05 * sample_rate)  # 50ms窗口
        energy = torch.nn.functional.avg_pool1d(
            waveform.abs().unsqueeze(0), 
            kernel_size=window_size, 
            stride=window_size//2
        ).squeeze()
        
        # 找到静音点（能量低于阈值）
        energy_threshold = torch.quantile(energy, 0.1)  # 底部10%作为静音
        silence_mask = energy < energy_threshold
        
        # 查找潜在的切分点
        segments = []
        current_time = 0
        segment_id = 0
        
        while current_time < total_duration:
            # 目标结束时间
            target_end = min(current_time + target_segment_duration, total_duration)
            
            # 在目标时间附近寻找静音点（±0.3秒范围）
            search_start = max(target_end - 0.3, current_time + 1.0)
            search_end = min(target_end + 0.3, total_duration)
            
            # 转换为采样点索引
            start_idx = int(search_start * sample_rate / (window_size//2))
            end_idx = int(search_end * sample_rate / (window_size//2))
            
            # 在搜索范围内找到最长的静音段
            best_split_time = target_end
            if start_idx < end_idx and end_idx <= len(silence_mask):
                silence_region = silence_mask[start_idx:end_idx]
                if torch.any(silence_region):
                    # 找到静音段的中点
                    silence_indices = torch.where(silence_region)[0]
                    if len(silence_indices) > 0:
                        mid_silence = silence_indices[len(silence_indices)//2]
                        best_split_time = search_start + (mid_silence * window_size // 2) / sample_rate
            
            # 确保片段长度合理（至少1秒，最多3秒）
            segment_duration = best_split_time - current_time
            if segment_duration < 1.0 and current_time + 1.0 < total_duration:
                best_split_time = min(current_time + 2.0, total_duration)
            elif segment_duration > 3.0:
                best_split_time = current_time + 2.0
            
            # 创建片段信息
            segment = {
                'id': segment_id,
                'start_time': current_time,
                'end_time': best_split_time,
                'duration': best_split_time - current_time,
                'frame_count': 16,  # 固定16帧
                'fps': fps,
                'start_sample': int(current_time * sample_rate),
                'end_sample': int(best_split_time * sample_rate)
            }
            segments.append(segment)
            
            current_time = best_split_time
            segment_id += 1
            
            # 如果已经到达结尾，退出
            if current_time >= total_duration - 0.1:
                break
        
        return segments


class VideoSegmentManager:
    """管理视频片段的生成和存储"""
    
    def __init__(self, work_dir: str):
        self.work_dir = work_dir
        self.segments_dir = os.path.join(work_dir, "segments")
        os.makedirs(self.segments_dir, exist_ok=True)
        self.metadata_file = os.path.join(work_dir, "metadata.json")
        self.metadata = {"segments": [], "status": "processing"}
        
    def save_segment(self, segment_id: int, frames: torch.Tensor, segment_info: Dict):
        """保存视频片段"""
        segment_path = os.path.join(self.segments_dir, f"segment_{segment_id:04d}.pt")
        torch.save({
            'frames': frames,
            'info': segment_info
        }, segment_path)
        
        # 更新元数据
        segment_info['file_path'] = segment_path
        segment_info['saved'] = True
        self.metadata['segments'].append(segment_info)
        self._save_metadata()
        
    def load_segment(self, segment_id: int) -> Optional[torch.Tensor]:
        """加载视频片段"""
        segment_path = os.path.join(self.segments_dir, f"segment_{segment_id:04d}.pt")
        if os.path.exists(segment_path):
            data = torch.load(segment_path)
            return data['frames']
        return None
        
    def _save_metadata(self):
        """保存元数据"""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
            
    def get_progress(self) -> Dict:
        """获取生成进度"""
        total = len(self.metadata['segments'])
        completed = sum(1 for s in self.metadata['segments'] if s.get('saved', False))
        return {
            'total': total,
            'completed': completed,
            'percentage': (completed / total * 100) if total > 0 else 0
        }


class VideoPostProcessor:
    """视频后处理和拼接"""
    
    @staticmethod
    def concatenate_segments(segment_frames: List[torch.Tensor], fade_frames: int = 2) -> torch.Tensor:
        """
        拼接视频片段，可选淡入淡出
        
        Args:
            segment_frames: 片段帧列表
            fade_frames: 淡入淡出的帧数
            
        Returns:
            拼接后的完整视频帧
        """
        if not segment_frames:
            return torch.empty(0)
            
        # 如果只有一个片段，直接返回
        if len(segment_frames) == 1:
            return segment_frames[0]
            
        result_frames = []
        
        for i, frames in enumerate(segment_frames):
            if i == 0:
                # 第一个片段，直接添加
                result_frames.append(frames)
            else:
                # 后续片段，添加淡入淡出过渡
                if fade_frames > 0 and len(result_frames) > 0:
                    # 获取前一片段的最后几帧和当前片段的前几帧
                    prev_end = result_frames[-1][-fade_frames:] if len(result_frames[-1]) >= fade_frames else result_frames[-1]
                    curr_start = frames[:fade_frames] if len(frames) >= fade_frames else frames
                    
                    # 创建淡入淡出权重
                    fade_weights = torch.linspace(1, 0, fade_frames).view(-1, 1, 1, 1).to(frames.device)
                    
                    # 混合帧
                    if len(prev_end) == len(curr_start) == fade_frames:
                        blended = prev_end * fade_weights + curr_start * (1 - fade_weights)
                        # 替换前一片段的最后几帧
                        if len(result_frames[-1]) >= fade_frames:
                            result_frames[-1] = torch.cat([result_frames[-1][:-fade_frames], blended])
                        # 添加当前片段剩余的帧
                        result_frames.append(frames[fade_frames:])
                    else:
                        # 如果帧数不匹配，直接拼接
                        result_frames.append(frames)
                else:
                    # 不使用淡入淡出，直接拼接
                    result_frames.append(frames)
        
        # 拼接所有帧
        return torch.cat(result_frames, dim=0)
    
    @staticmethod
    def apply_color_correction(frames: torch.Tensor) -> torch.Tensor:
        """
        应用全局色彩校正以保持一致性
        
        Args:
            frames: 视频帧 (N, H, W, C)
            
        Returns:
            色彩校正后的帧
        """
        # 计算全局统计信息
        mean_color = frames.mean(dim=(0, 1, 2), keepdim=True)
        std_color = frames.std(dim=(0, 1, 2), keepdim=True)
        
        # 目标值（中性灰和标准偏差）
        target_mean = 0.5
        target_std = 0.2
        
        # 应用标准化和重新缩放
        normalized = (frames - mean_color) / (std_color + 1e-7)
        corrected = normalized * target_std + target_mean
        
        # 裁剪到有效范围
        return torch.clamp(corrected, 0, 1)


class LatentSyncLongVideoNode:
    """
    LatentSync 长视频生成节点
    使用智能分段策略生成任意长度的视频
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("AUDIO",),
                "latent_sync_model": ("LATENTSYNC_MODEL",),  # 假设有预加载的模型
                "fps": ("INT", {"default": 8, "min": 4, "max": 30, "step": 1}),
                "segment_duration": ("FLOAT", {"default": 2.0, "min": 1.0, "max": 3.0, "step": 0.1}),
                "guidance_scale": ("FLOAT", {"default": 7.5, "min": 1.0, "max": 20.0, "step": 0.5}),
                "num_inference_steps": ("INT", {"default": 25, "min": 10, "max": 50, "step": 1}),
                "fade_frames": ("INT", {"default": 2, "min": 0, "max": 5, "step": 1}),
                "apply_color_correction": ("BOOLEAN", {"default": True}),
                "seed": ("INT", {"default": -1, "min": -1, "max": 2**32 - 1}),
            },
            "optional": {
                "work_directory": ("STRING", {"default": ""}),
            }
        }
    
    RETURN_TYPES = ("IMAGE", "AUDIO", "VHS_VIDEOINFO")
    RETURN_NAMES = ("frames", "audio", "video_info")
    FUNCTION = "generate_long_video"
    CATEGORY = "shenglin/视频生成"
    
    def generate_long_video(self, audio, latent_sync_model, fps=8, segment_duration=2.0, 
                           guidance_scale=7.5, num_inference_steps=25, fade_frames=2,
                           apply_color_correction=True, seed=-1, work_directory=""):
        """
        生成长视频的主函数
        """
        # 设置工作目录
        if not work_directory:
            work_directory = tempfile.mkdtemp(prefix="latentsync_long_")
        os.makedirs(work_directory, exist_ok=True)
        
        # 设置随机种子
        if seed == -1:
            seed = torch.randint(0, 2**32 - 1, (1,)).item()
        torch.manual_seed(seed)
        
        # 初始化管理器
        segment_manager = VideoSegmentManager(work_directory)
        
        # 分析音频并切分
        print(f"分析音频并切分为约{segment_duration}秒的片段...")
        segments = AudioSegmentAnalyzer.analyze_audio(audio, segment_duration, fps)
        print(f"音频已切分为{len(segments)}个片段")
        
        # 存储所有生成的片段
        all_frames = []
        
        # 逐段生成视频
        for segment in segments:
            print(f"\n生成片段 {segment['id'] + 1}/{len(segments)}...")
            print(f"  时间范围: {segment['start_time']:.2f}s - {segment['end_time']:.2f}s")
            
            # 提取音频片段
            audio_segment = {
                'waveform': audio['waveform'][:, segment['start_sample']:segment['end_sample']],
                'sample_rate': audio['sample_rate']
            }
            
            try:
                # 生成视频片段（这里需要调用实际的LatentSync模型）
                # 注意：这是一个占位符，实际使用时需要替换为真实的模型调用
                frames = self._generate_segment(
                    latent_sync_model, 
                    audio_segment, 
                    fps=fps,
                    guidance_scale=guidance_scale,
                    num_inference_steps=num_inference_steps
                )
                
                # 保存片段
                segment_manager.save_segment(segment['id'], frames, segment)
                all_frames.append(frames)
                
                # 清理显存
                if comfy.model_management.VRAM_state == comfy.model_management.VRAMState.LOW_VRAM:
                    comfy.model_management.soft_empty_cache()
                
            except Exception as e:
                print(f"  生成片段 {segment['id']} 失败: {str(e)}")
                # 使用黑帧填充失败的片段
                black_frames = torch.zeros((16, 512, 512, 3))
                all_frames.append(black_frames)
            
            # 显示进度
            progress = segment_manager.get_progress()
            print(f"  进度: {progress['completed']}/{progress['total']} ({progress['percentage']:.1f}%)")
        
        # 拼接所有片段
        print("\n拼接视频片段...")
        final_frames = VideoPostProcessor.concatenate_segments(all_frames, fade_frames)
        
        # 应用色彩校正
        if apply_color_correction:
            print("应用色彩校正...")
            final_frames = VideoPostProcessor.apply_color_correction(final_frames)
        
        # 创建视频信息
        video_info = {
            'fps': fps,
            'frame_count': len(final_frames),
            'duration': len(final_frames) / fps,
            'width': 512,
            'height': 512,
            'segment_count': len(segments),
            'work_directory': work_directory
        }
        
        print(f"\n视频生成完成！")
        print(f"  总帧数: {video_info['frame_count']}")
        print(f"  总时长: {video_info['duration']:.2f}秒")
        print(f"  工作目录: {work_directory}")
        
        return (final_frames, audio, video_info)
    
    def _generate_segment(self, model, audio_segment, fps, guidance_scale, num_inference_steps):
        """
        生成单个视频片段的占位函数
        实际使用时需要替换为真实的LatentSync调用
        """
        # 这里应该调用实际的LatentSync模型
        # 返回16帧的视频张量 (16, H, W, C)
        
        # 临时返回随机帧作为示例
        return torch.rand((16, 512, 512, 3))


# 用于测试的简化节点
class LatentSyncLongVideoSimpleNode:
    """
    简化版的长视频生成节点，用于测试工作流
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("AUDIO",),
                "images": ("IMAGE",),  # 接收LatentSync生成的图像
                "fps": ("INT", {"default": 8, "min": 4, "max": 30, "step": 1}),
                "segment_duration": ("FLOAT", {"default": 2.0, "min": 1.0, "max": 3.0, "step": 0.1}),
            }
        }
    
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "process_long_video"
    CATEGORY = "shenglin/视频生成"
    
    def process_long_video(self, audio, images, fps=8, segment_duration=2.0):
        """
        处理LatentSync输出，实现长视频逻辑
        """
        # 分析音频
        segments = AudioSegmentAnalyzer.analyze_audio(audio, segment_duration, fps)
        
        # 根据音频长度循环视频
        audio_duration = audio['waveform'].shape[-1] / audio['sample_rate']
        video_duration = len(images) / fps
        
        if audio_duration > video_duration:
            # 循环视频以匹配音频长度
            repeat_times = int(np.ceil(audio_duration / video_duration))
            extended_images = images.repeat(repeat_times, 1, 1, 1)
            # 裁剪到精确的帧数
            target_frames = int(audio_duration * fps)
            extended_images = extended_images[:target_frames]
            return (extended_images,)
        else:
            return (images,)


NODE_CLASS_MAPPINGS = {
    "LatentSyncLongVideo": LatentSyncLongVideoNode,
    "LatentSyncLongVideoSimple": LatentSyncLongVideoSimpleNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LatentSyncLongVideo": "LatentSync长视频生成",
    "LatentSyncLongVideoSimple": "LatentSync长视频简化版",
}