import os
import random
import time
import ffmpeg
import folder_paths

class VideoConcatNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video_root": ("STRING", {"default": "", "multiline": False, "placeholder": "/path/to/videos"}),
                "label": ("STRING", {"default": "", "multiline": False, "placeholder": "标签/子目录名"}),
                "target_duration": ("FLOAT", {"default": 120.0, "min": 1.0, "max": 600.0, "step": 1.0, "display": "number", "tooltip": "拼接后总时长（秒）"}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("output_video",)
    FUNCTION = "concat_videos"
    CATEGORY = "Video"

    def concat_videos(self, video_root, label, target_duration):
        # 获取目标目录
        target_dir = os.path.join(video_root, label)
        if not os.path.isdir(target_dir):
            raise Exception(f"目录不存在: {target_dir}")
        # 支持的视频格式
        video_exts = [".mp4", ".webm", ".mkv", ".mov", ".avi"]
        # 获取所有视频文件
        files = [f for f in os.listdir(target_dir) if os.path.splitext(f)[1].lower() in video_exts]
        if not files:
            raise Exception(f"子目录下没有可用视频文件: {target_dir}")
        # 打乱顺序
        random.shuffle(files)
        # 依次累加视频，直到总时长接近target_duration
        selected_paths = []
        total = 0.0
        for f in files:
            path = os.path.join(target_dir, f)
            try:
                probe = ffmpeg.probe(path)
                duration = float(probe['format']['duration'])
            except Exception:
                continue
            
            selected_paths.append(path)
            if total + duration > target_duration and selected_paths:
                break
            
        if not selected_paths:
            # 兜底：选第一个视频
            selected_paths = [os.path.join(target_dir, files[0])]
        # 获取临时目录
        temp_dir = folder_paths.get_temp_directory()
        # 生成唯一文件名
        timestamp = int(time.time() * 1000)
        random_num = random.randint(1, 9999)
        # 生成临时输出路径
        merged_path = os.path.join(temp_dir, f"concat_merged_{timestamp}_{random_num}.mp4")
        # 使用ffmpeg-python拼接视频（只拼接视频流，不处理音频）
        streams = []
        for path in selected_paths:
            streams.append(ffmpeg.input(path))
        concat_video = ffmpeg.concat(*[s.video for s in streams], v=1, a=0).node
        output = ffmpeg.output(concat_video[0], merged_path, an=None)
        ffmpeg.run(output, overwrite_output=True)
        # 获取合并后视频时长
        probe = ffmpeg.probe(merged_path)
        duration = float(probe['format']['duration'])
        output_path = merged_path
        # 若总时长超过target_duration，裁剪到target_duration
        if duration > target_duration:
            output_path = os.path.join(temp_dir, f"concat_result_{timestamp}_{random_num}.mp4")
            input_stream = ffmpeg.input(merged_path)
            output = ffmpeg.output(input_stream, output_path, t=target_duration, an=None)
            ffmpeg.run(output, overwrite_output=True)
            os.remove(merged_path)
        return (output_path,)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # 确保节点在输入变化时重新执行
        return float("nan")

