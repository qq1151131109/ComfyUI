import torch
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('按秒计算音频时长')

class 按秒计算音频时长:
    """将音频时长转换为 FramePackSampler 节点所需的参数，用于生成视频"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("AUDIO",),
                "latent_window_size": ("INT", {"default": 9, "min": 1, "max": 33, "step": 1, "tooltip": "采样窗口大小"}),
                "fps": ("INT", {"default": 30, "min": 1, "max": 120, "step": 1, "tooltip": "每秒帧数"}),
            },
        }

    RETURN_TYPES = ("FLOAT",)
    RETURN_NAMES = ("total_second_length",)
    FUNCTION = "convert"
    CATEGORY = "shenglin/音频处理"

    def convert(self, audio, latent_window_size, fps):
        """将音频时长转换为秒单位的视频时长参数"""
        waveform = audio["waveform"]
        sample_rate = audio["sample_rate"]
        
        # 计算音频时长（毫秒）
        duration_ms = int((waveform.shape[-1] / sample_rate) * 1000)
        
        # 计算视频时长（秒）
        duration_sec = duration_ms / 1000.0
        
        # 考虑到 FramePackSampler 的窗口大小和帧率
        # 总帧数 = 时长（秒）* 帧率
        total_frames = duration_sec * fps
        
        logger.info(f"音频时长: {duration_ms}ms, 转换为 {duration_sec}s 视频时长")
        logger.info(f"计算帧数: {total_frames} at {fps} FPS")
        
        return (duration_sec,)

# 节点列表
NODE_CLASS_MAPPINGS = {
    "按秒计算音频时长": 按秒计算音频时长
}

# 显示名称映射
NODE_DISPLAY_NAME_MAPPINGS = {
    "按秒计算音频时长": "按秒计算音频时长"
} 