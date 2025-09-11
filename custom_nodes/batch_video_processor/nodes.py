"""
批量视频处理节点实现 - 改进版
"""

import os
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List
from typing_extensions import override

import folder_paths
from comfy_api.input import VideoInput
from comfy_api.input_impl import VideoFromFile
from comfy_api.latest import ComfyExtension, io, ui

from .utils import (
    get_video_duration, get_video_info, scan_video_files,
    create_batch_folder, create_output_folder, prepare_end_video,
    cut_single_segment_with_end, create_download_archive,
    clean_old_batches, format_file_size
)


class BatchVideoLoader(io.ComfyNode):
    """批量素材加载器 - 支持视频、音频、图像等多种素材批量上传"""
    
    @classmethod
    def define_schema(cls):
        # 获取输入目录中的视频文件
        input_dir = folder_paths.get_input_directory()
        
        # 扫描batch_uploads文件夹
        batch_upload_dir = os.path.join(input_dir, "batch_uploads")
        folders = []
        if os.path.exists(batch_upload_dir):
            folders = [f for f in os.listdir(batch_upload_dir) 
                      if os.path.isdir(os.path.join(batch_upload_dir, f))]
        
        return io.Schema(
            node_id="BatchVideoLoader",
            display_name="批量素材加载器",
            category="batch_video",
            description="批量上传和加载素材文件 - 支持视频、音频、图像等多种格式",
            inputs=[
                # 无需输入参数，全部通过按钮操作
            ],
            outputs=[
                io.String.Output("output_folder_path", display_name="文件夹路径"),
                io.Int.Output("file_count", display_name="文件数量"),
                io.String.Output("file_list", display_name="文件列表"),
            ],
        )

    @classmethod
    def execute(cls) -> io.NodeOutput:
        input_dir = folder_paths.get_input_directory()
        batch_upload_dir = os.path.join(input_dir, "batch_uploads")
        
        # 默认状态 - 等待上传
        file_list = """批量素材加载器 - 准备就绪

使用说明:
1. 点击「📁 选择多个文件」按钮选择多个素材文件
2. 点击「📂 选择文件夹」按钮选择包含素材的文件夹
3. 支持格式:
   • 视频: mp4, avi, mov, mkv, flv, wmv, m4v, webm
   • 音频: mp3, wav, aac, flac, ogg, m4a, wma
   • 图像: jpg, jpeg, png, gif, bmp, tiff, webp

选择文件后会自动创建会话文件夹，文件路径将显示在输出中。"""
        
        return io.NodeOutput("", 0, file_list)


class RandomVideoConcatenator(io.ComfyNode):
    """完全随机视频拼接器 - 从多个文件夹随机选择视频进行拼接"""
    
    @classmethod
    def define_schema(cls):
        # 创建20个文件夹输入
        inputs = []
        for i in range(1, 21):
            optional = i > 2  # 前两个必填，其他可选
            inputs.append(io.String.Input(f"folder{i}", optional=optional, tooltip=f"文件夹{i}路径{'(可选)' if optional else ''}"))
        
        inputs.extend([
            io.Int.Input(
                "output_count", 
                default=10, 
                min=1, 
                max=500,
                tooltip="输出视频数量"
            ),
            io.String.Input(
                "output_prefix", 
                default="随机拼接", 
                tooltip="输出前缀"
            ),
        ])
        
        return io.Schema(
            node_id="RandomVideoConcatenator",
            display_name="视频拼接-完全随机",
            category="batch_video", 
            description="从多个文件夹中完全随机选择视频进行拼接",
            inputs=inputs,
            outputs=[
                io.String.Output("output_folder", display_name="文件夹路径"),
                io.Int.Output("video_count", display_name="生成数量"),
                io.String.Output("summary", display_name="拼接摘要"),
            ],
        )
    
    @classmethod
    def execute(cls, output_count: int = 10, output_prefix: str = "随机拼接", **kwargs) -> io.NodeOutput:
        import random
        import ffmpeg
        
        # 收集有效文件夹
        folders = []
        for i in range(1, 21):
            folder_key = f"folder{i}"
            if folder_key in kwargs and kwargs[folder_key]:
                folders.append(kwargs[folder_key])
        
        if len(folders) < 2:
            return io.NodeOutput("", 0, "错误：至少需要2个文件夹")
        
        # 验证文件夹并扫描视频
        folder_videos = {}
        for i, folder in enumerate(folders):
            if not os.path.exists(folder):
                return io.NodeOutput("", 0, f"错误：文件夹不存在: {folder}")
            
            videos = scan_video_files(folder)
            if not videos:
                return io.NodeOutput("", 0, f"错误：文件夹中没有视频文件: {folder}")
            
            folder_videos[i] = videos
        
        # 创建输出文件夹
        output_dir = folder_paths.get_output_directory()
        output_folder = create_output_folder(output_dir, output_prefix)
        
        print(f"开始完全随机视频拼接，使用{len(folders)}个文件夹")
        
        successful_count = 0
        
        # 完全随机模式：每次从每个文件夹随机选一个视频
        for i in range(output_count):
            try:
                selected_videos = []
                for folder_idx in folder_videos:
                    selected_videos.append(random.choice(folder_videos[folder_idx]))
                
                output_filename = f"random_concat_{i+1:04d}.mp4"
                output_path = os.path.join(output_folder, output_filename)
                
                if cls._concatenate_videos(selected_videos, output_path):
                    successful_count += 1
                    print(f"✓ 完成随机拼接 {i+1}/{output_count}")
                
            except Exception as e:
                print(f"✗ 随机拼接失败 {i+1}: {e}")
        
        summary = f"""完全随机视频拼接完成！
输出文件夹: {output_folder}
使用文件夹数: {len(folders)}
成功生成: {successful_count} 个视频
总共尝试: {output_count} 次"""
        
        return io.NodeOutput(output_folder, successful_count, summary)
    
    @staticmethod
    def _concatenate_videos(video_paths: List[str], output_path: str) -> bool:
        """拼接多个视频文件"""
        try:
            if len(video_paths) < 2:
                return False
            
            # 创建输入流
            inputs = [ffmpeg.input(video_path) for video_path in video_paths]
            
            # 拼接视频和音频流
            video_streams = [input_stream.video for input_stream in inputs]
            audio_streams = [input_stream.audio for input_stream in inputs]
            
            (
                ffmpeg
                .filter(video_streams + audio_streams, 'concat', n=len(inputs), v=1, a=1)
                .output(output_path, vcodec='libx264', acodec='aac')
                .overwrite_output()
                .run(quiet=True)
            )
            
            return True
            
        except Exception as e:
            print(f"拼接视频失败 {output_path}: {e}")
            return False


class TraverseVideoConcatenator(io.ComfyNode):
    """遍历视频拼接器 - 遍历某个文件夹，其他文件夹随机选择"""
    
    @classmethod
    def define_schema(cls):
        # 创建20个文件夹输入
        inputs = []
        for i in range(1, 21):
            optional = i > 2  # 前两个必填，其他可选
            inputs.append(io.String.Input(f"folder{i}", optional=optional, tooltip=f"文件夹{i}路径{'(可选)' if optional else ''}"))
        
        inputs.extend([
            io.Int.Input(
                "traverse_folder_index", 
                default=1, 
                min=1, 
                max=20,
                tooltip="要遍历的文件夹序号"
            ),
            io.String.Input(
                "output_prefix", 
                default="遍历拼接", 
                tooltip="输出前缀"
            ),
        ])
        
        return io.Schema(
            node_id="TraverseVideoConcatenator",
            display_name="视频拼接-遍历单个文件夹",
            category="batch_video", 
            description="遍历指定文件夹的所有视频，其他文件夹随机选择进行拼接",
            inputs=inputs,
            outputs=[
                io.String.Output("output_folder", display_name="文件夹路径"),
                io.Int.Output("video_count", display_name="生成数量"),
                io.String.Output("summary", display_name="拼接摘要"),
            ],
        )
    
    @classmethod
    def execute(cls, traverse_folder_index: int = 1, output_prefix: str = "遍历拼接", **kwargs) -> io.NodeOutput:
        import random
        import ffmpeg
        
        # 收集有效文件夹
        folders = []
        for i in range(1, 21):
            folder_key = f"folder{i}"
            if folder_key in kwargs and kwargs[folder_key]:
                folders.append(kwargs[folder_key])
        
        if len(folders) < 2:
            return io.NodeOutput("", 0, "错误：至少需要2个文件夹")
        
        if traverse_folder_index > len(folders):
            return io.NodeOutput("", 0, f"错误：遍历文件夹序号{traverse_folder_index}超出范围(最大{len(folders)})")
        
        # 验证文件夹并扫描视频
        folder_videos = {}
        for i, folder in enumerate(folders):
            if not os.path.exists(folder):
                return io.NodeOutput("", 0, f"错误：文件夹不存在: {folder}")
            
            videos = scan_video_files(folder)
            if not videos:
                return io.NodeOutput("", 0, f"错误：文件夹中没有视频文件: {folder}")
            
            folder_videos[i] = videos
        
        # 创建输出文件夹
        output_dir = folder_paths.get_output_directory()
        output_folder = create_output_folder(output_dir, output_prefix)
        
        print(f"开始遍历视频拼接，遍历文件夹{traverse_folder_index}，使用{len(folders)}个文件夹")
        
        successful_count = 0
        
        # 遍历+随机模式：遍历指定文件夹，其他文件夹随机选择
        traverse_videos = folder_videos[traverse_folder_index - 1]  # 转换为0索引
        other_folders = {k: v for k, v in folder_videos.items() if k != traverse_folder_index - 1}
        
        for i, traverse_video in enumerate(traverse_videos):
            try:
                selected_videos = [traverse_video]
                
                # 从其他文件夹随机选择
                for folder_idx in sorted(other_folders.keys()):
                    selected_videos.append(random.choice(other_folders[folder_idx]))
                
                output_filename = f"traverse_concat_{i+1:04d}.mp4"
                output_path = os.path.join(output_folder, output_filename)
                
                if cls._concatenate_videos(selected_videos, output_path):
                    successful_count += 1
                    print(f"✓ 完成遍历拼接 {i+1}/{len(traverse_videos)}")
                
            except Exception as e:
                print(f"✗ 遍历拼接失败 {i+1}: {e}")
        
        summary = f"""遍历视频拼接完成！
输出文件夹: {output_folder}
遍历文件夹: {traverse_folder_index} (共{len(traverse_videos)}个视频)
使用文件夹数: {len(folders)}
成功生成: {successful_count} 个视频"""
        
        return io.NodeOutput(output_folder, successful_count, summary)
    
    @staticmethod
    def _concatenate_videos(video_paths: List[str], output_path: str) -> bool:
        """拼接多个视频文件"""
        try:
            if len(video_paths) < 2:
                return False
            
            # 创建输入流
            inputs = [ffmpeg.input(video_path) for video_path in video_paths]
            
            # 拼接视频和音频流
            video_streams = [input_stream.video for input_stream in inputs]
            audio_streams = [input_stream.audio for input_stream in inputs]
            
            (
                ffmpeg
                .filter(video_streams + audio_streams, 'concat', n=len(inputs), v=1, a=1)
                .output(output_path, vcodec='libx264', acodec='aac')
                .overwrite_output()
                .run(quiet=True)
            )
            
            return True
            
        except Exception as e:
            print(f"拼接视频失败 {output_path}: {e}")
            return False



class BatchVideoCutter(io.ComfyNode):
    """批量视频切分器 - 简化版"""
    
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="BatchVideoCutter",
            display_name="批量切分视频",
            category="batch_video",
            description="批量切分视频文件",
            inputs=[
                io.String.Input(
                    "input_folder", 
                    tooltip="输入视频文件夹路径"
                ),
                io.Float.Input(
                    "cut_duration", 
                    default=30.0, 
                    min=1.0, 
                    max=300.0,
                    step=0.5,
                    tooltip="每段时长(秒)"
                ),
                io.String.Input(
                    "output_prefix", 
                    default="已处理", 
                    tooltip="输出前缀"
                ),
            ],
            outputs=[
                io.String.Output("output_folder", display_name="文件夹路径"),
                io.Int.Output("total_segments", display_name="总片段数"),
                io.String.Output("summary", display_name="处理摘要"),
            ],
        )

    @classmethod
    def execute(cls, input_folder: str, cut_duration: float, output_prefix: str) -> io.NodeOutput:
        
        # 获取输出目录
        output_dir = folder_paths.get_output_directory()
        output_folder = create_output_folder(output_dir, output_prefix)
        
        # 扫描输入文件夹
        if not os.path.exists(input_folder):
            return io.NodeOutput(output_folder, 0, f"错误：输入文件夹不存在")
        
        video_files = scan_video_files(input_folder)
        if not video_files:
            return io.NodeOutput(output_folder, 0, f"未找到视频文件")
        
        print(f"开始处理 {len(video_files)} 个视频文件")
        
        total_segments = 0
        processed_videos = 0
        
        # 简化处理：单线程，基本切分
        for video_file in video_files:
            try:
                segments_count = cls._process_single_video_simple(
                    video_file, cut_duration, output_folder
                )
                if segments_count > 0:
                    total_segments += segments_count
                    processed_videos += 1
                    print(f"✓ 完成: {os.path.basename(video_file)} ({segments_count} 段)")
            except Exception as e:
                print(f"✗ 失败: {os.path.basename(video_file)} - {e}")
        
        summary = f"""处理完成！
输出: {output_folder}
处理: {processed_videos}/{len(video_files)} 个视频
总段数: {total_segments}
时长: {cut_duration}秒/段"""
        
        return io.NodeOutput(output_folder, total_segments, summary)
    
    @staticmethod
    def _process_single_video_simple(video_path: str, cut_duration: float, output_folder: str) -> int:
        """简化的单视频处理"""
        video_name = Path(video_path).stem
        video_duration = get_video_duration(video_path)
        
        if video_duration < cut_duration:
            return 0
        
        num_segments = int(video_duration // cut_duration)
        if num_segments == 0:
            return 0
        
        # 创建视频输出目录
        video_output_dir = os.path.join(output_folder, video_name)
        os.makedirs(video_output_dir, exist_ok=True)
        
        segments_created = 0
        
        # 简单切分（不添加结尾视频）
        import ffmpeg
        for i in range(num_segments):
            start_time = i * cut_duration
            end_time = (i + 1) * cut_duration
            
            if end_time > video_duration:
                end_time = video_duration
            
            output_filename = f"segment_{i+1:03d}.mp4"
            output_path = os.path.join(video_output_dir, output_filename)
            
            try:
                (
                    ffmpeg
                    .input(video_path, ss=start_time, t=end_time-start_time)
                    .output(output_path, vcodec='libx264', acodec='aac')
                    .overwrite_output()
                    .run(quiet=True)
                )
                segments_created += 1
            except Exception as e:
                print(f"切分失败 {output_filename}: {e}")
        
        return segments_created


class BatchVideoDownloader(io.ComfyNode):
    """批量视频下载器 - 简化版"""
    
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="BatchVideoDownloader",
            display_name="批量下载",
            category="batch_video",
            description="打包下载处理后的视频",
            inputs=[
                io.String.Input(
                    "source_folder", 
                    tooltip="源文件夹路径"
                ),
                io.String.Input(
                    "archive_name", 
                    default="处理结果", 
                    tooltip="压缩包名称"
                ),
            ],
            outputs=[
                io.String.Output("download_path", display_name="下载路径"),
                io.String.Output("archive_info", display_name="压缩包信息"),
            ],
            is_output_node=True,
        )

    @classmethod
    def execute(cls, source_folder: str, archive_name: str) -> io.NodeOutput:
        
        if not os.path.exists(source_folder):
            return io.NodeOutput("", f"错误：文件夹不存在 {source_folder}")
        
        # 创建压缩包
        archive_path, file_count, total_size = create_download_archive(
            source_folder, archive_name, "zip", True
        )
        
        if not archive_path:
            return io.NodeOutput("", "创建压缩包失败")
        
        archive_size = os.path.getsize(archive_path)
        archive_info = f"""下载包已创建！
路径: {archive_path}
文件: {file_count} 个
大小: {format_file_size(archive_size)}
压缩率: {(1 - archive_size / total_size) * 100:.1f}%"""
        
        return io.NodeOutput(archive_path, archive_info)


class BatchFileManager(io.ComfyNode):
    """文件管理器 - 简化版"""
    
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="BatchFileManager",
            display_name="文件管理器",
            category="batch_video",
            description="管理批量处理文件",
            inputs=[
                io.Combo.Input(
                    "action", 
                    options=["查看列表", "清理文件"], 
                    default="查看列表",
                    tooltip="管理操作"
                ),
                io.Int.Input(
                    "days_to_keep", 
                    default=7, 
                    min=1, 
                    max=30,
                    tooltip="保留天数"
                ),
            ],
            outputs=[
                io.String.Output("result", display_name="操作结果"),
            ],
        )

    @classmethod
    def execute(cls, action: str, days_to_keep: int) -> io.NodeOutput:
        
        input_dir = folder_paths.get_input_directory()
        output_dir = folder_paths.get_output_directory()
        
        if action == "查看列表":
            # 列出批处理文件夹
            result_lines = ["批处理文件夹列表:\n"]
            
            # 检查输入目录
            batch_upload_dir = os.path.join(input_dir, "batch_uploads")
            if os.path.exists(batch_upload_dir):
                for item in os.listdir(batch_upload_dir):
                    item_path = os.path.join(batch_upload_dir, item)
                    if os.path.isdir(item_path):
                        file_count = len([f for f in os.listdir(item_path) 
                                        if os.path.isfile(os.path.join(item_path, f))])
                        result_lines.append(f"📁 上传: {item} ({file_count} 文件)")
            
            # 检查输出目录
            batch_output_dir = os.path.join(output_dir, "processed_batches")
            if os.path.exists(batch_output_dir):
                for item in os.listdir(batch_output_dir):
                    item_path = os.path.join(batch_output_dir, item)
                    if os.path.isdir(item_path):
                        # 计算子文件夹文件数
                        total_files = 0
                        for root, dirs, files in os.walk(item_path):
                            total_files += len(files)
                        result_lines.append(f"📁 输出: {item} ({total_files} 文件)")
            
            result = "\n".join(result_lines) if len(result_lines) > 1 else "暂无批处理文件"
            
        elif action == "清理文件":
            # 清理旧文件
            cleaned_input = clean_old_batches(input_dir, days_to_keep)
            cleaned_output = clean_old_batches(output_dir, days_to_keep)
            total_cleaned = len(cleaned_input) + len(cleaned_output)
            
            result = f"清理完成！删除了 {total_cleaned} 个过期文件夹"
            if total_cleaned > 0:
                result += f"\n保留了 {days_to_keep} 天内的文件"
        
        else:
            result = f"未知操作: {action}"
        
        return io.NodeOutput(result)


class BatchVideoExtension(ComfyExtension):
    """批量视频处理扩展 - 改进版"""
    
    @override
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [
            BatchVideoLoader,
            RandomVideoConcatenator,
            TraverseVideoConcatenator,
            BatchVideoCutter,
            BatchVideoDownloader,
            BatchFileManager,
        ]