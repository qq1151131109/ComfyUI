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


class VideoStaticCleaner(io.ComfyNode):
    """视频静止片段清理器 - 自动检测并移除卡帧和静止片段"""
    
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="VideoStaticCleaner",
            display_name="视频静止片段清理器",
            category="batch_video",
            description="自动检测并移除视频中的卡帧、静止片段，提升视频流畅度",
            inputs=[
                io.String.Input("video_folder", tooltip="视频文件夹路径"),
                io.Float.Input("static_threshold", default=0.02, tooltip="静止判定阈值(0-1，越小越敏感)"),
                io.Int.Input("min_static_duration", default=3, tooltip="最小静止时长(秒)"),
                io.Bool.Input("enable_preview", default=True, tooltip="生成清理报告"),
                io.String.Input("output_prefix", default="清理版", tooltip="输出前缀"),
            ],
            outputs=[
                io.String.Output("output_folder", display_name="输出文件夹"),
                io.Int.Output("processed_count", display_name="处理数量"),
                io.String.Output("cleaning_report", display_name="清理报告"),
            ],
        )
    
    @classmethod
    def execute(cls, video_folder, static_threshold=0.02, min_static_duration=3, 
                enable_preview=True, output_prefix="清理版"):
        import os
        import time
        import json
        from pathlib import Path
        
        try:
            # 验证输入文件夹
            if not os.path.exists(video_folder):
                raise ValueError(f"视频文件夹不存在: {video_folder}")
            
            # 扫描视频文件
            video_files = []
            for ext in ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v']:
                pattern = os.path.join(video_folder, f"*{ext}")
                import glob
                video_files.extend(glob.glob(pattern))
                video_files.extend(glob.glob(pattern.upper()))
            
            if not video_files:
                raise ValueError(f"在文件夹中未找到视频文件: {video_folder}")
            
            # 创建输出文件夹
            timestamp = int(time.time())
            output_folder = os.path.join(folder_paths.get_temp_directory(), f"{output_prefix}_静止清理_{timestamp}")
            os.makedirs(output_folder, exist_ok=True)
            
            processed_count = 0
            failed_files = []
            cleaning_stats = []
            
            print(f"[视频静止片段清理器] 开始处理 {len(video_files)} 个视频文件")
            print(f"[视频静止片段清理器] 静止阈值: {static_threshold}, 最小时长: {min_static_duration}秒")
            
            for video_file in video_files:
                try:
                    video_name = Path(video_file).stem
                    output_filename = f"{video_name}_{output_prefix}.mp4"
                    output_path = os.path.join(output_folder, output_filename)
                    
                    print(f"[视频静止片段清理器] 处理: {video_name}")
                    
                    # 检测静止片段
                    static_segments = cls._detect_static_segments(
                        video_file, static_threshold, min_static_duration
                    )
                    
                    if static_segments:
                        print(f"[视频静止片段清理器] {video_name}: 发现 {len(static_segments)} 个静止片段")
                        
                        # 移除静止片段并导出
                        success = cls._export_video_without_segments(video_file, static_segments, output_path)
                        
                        if success:
                            # 计算清理统计
                            total_removed = sum(end - start for start, end in static_segments)
                            original_duration = cls._get_video_duration(video_file)
                            cleaned_duration = original_duration - total_removed if original_duration else 0
                            
                            cleaning_stats.append({
                                "file": video_name,
                                "original_duration": round(original_duration, 2),
                                "cleaned_duration": round(cleaned_duration, 2),
                                "removed_duration": round(total_removed, 2),
                                "static_segments": len(static_segments),
                                "compression_ratio": round((1 - total_removed / original_duration) * 100, 1) if original_duration > 0 else 0
                            })
                            
                            processed_count += 1
                            print(f"[视频静止片段清理器] 完成: {output_filename} (移除 {total_removed:.1f}秒)")
                        else:
                            failed_files.append(video_name)
                            print(f"[视频静止片段清理器] 导出失败: {video_name}")
                    else:
                        # 没有静止片段，直接复制
                        print(f"[视频静止片段清理器] {video_name}: 未发现静止片段，直接复制")
                        import shutil
                        shutil.copy2(video_file, output_path)
                        
                        original_duration = cls._get_video_duration(video_file)
                        cleaning_stats.append({
                            "file": video_name,
                            "original_duration": round(original_duration, 2),
                            "cleaned_duration": round(original_duration, 2),
                            "removed_duration": 0,
                            "static_segments": 0,
                            "compression_ratio": 100.0
                        })
                        processed_count += 1
                        
                except Exception as e:
                    failed_files.append(video_name)
                    print(f"[视频静止片段清理器] 处理失败: {video_name}, 错误: {str(e)}")
            
            # 生成清理报告
            report = cls._generate_cleaning_report(cleaning_stats, failed_files, enable_preview)
            
            # 保存报告到文件
            if enable_preview:
                report_path = os.path.join(output_folder, "cleaning_report.json")
                with open(report_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        "summary": report,
                        "details": cleaning_stats,
                        "failed_files": failed_files
                    }, f, ensure_ascii=False, indent=2)
            
            print(f"[视频静止片段清理器] 处理完成: 成功 {processed_count}/{len(video_files)} 个文件")
            
            return io.NodeOutput(output_folder, processed_count, report)
            
        except Exception as e:
            error_msg = f"视频静止片段清理器执行失败: {str(e)}"
            print(f"[视频静止片段清理器] 错误: {error_msg}")
            return io.NodeOutput("", 0, error_msg)
    
    @classmethod
    def _detect_static_segments(cls, video_path, threshold=0.02, min_duration=3.0):
        """检测静止片段 - 基于感知哈希"""
        try:
            import cv2
            import imagehash
            from PIL import Image
            
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return []
            
            # 获取视频信息
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            duration = frame_count / fps if fps > 0 else 0
            
            if duration == 0:
                cap.release()
                return []
            
            # 采样间隔（每秒采样）
            sample_interval = 1.0
            prev_hash = None
            static_start = None
            static_segments = []
            
            sample_time = 0.0
            while sample_time < duration:
                # 跳转到指定时间点
                cap.set(cv2.CAP_PROP_POS_MSEC, sample_time * 1000)
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 计算感知哈希
                cur_hash = cls._phash_frame_hd(frame)
                
                if prev_hash is not None:
                    # 计算归一化汉明距离
                    distance = (prev_hash - cur_hash) / float(cur_hash.hash.size)
                    
                    if distance <= threshold:  # 静止
                        if static_start is None:
                            static_start = sample_time
                    else:  # 有变化
                        if static_start is not None:
                            static_duration = sample_time - static_start
                            if static_duration >= min_duration:
                                static_segments.append((static_start, sample_time))
                        static_start = None
                
                prev_hash = cur_hash
                sample_time += sample_interval
            
            # 处理视频结尾的静止片段
            if static_start is not None:
                if duration - static_start >= min_duration:
                    static_segments.append((static_start, duration))
            
            cap.release()
            return static_segments
            
        except Exception as e:
            print(f"[视频静止片段清理器] 静止片段检测失败: {str(e)}")
            return []
    
    @classmethod
    def _phash_frame_hd(cls, frame):
        """高精度感知哈希"""
        try:
            import cv2
            import imagehash
            from PIL import Image
            
            # 转为灰度图
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # CLAHE增强对比度
            gray_single = cv2.cvtColor(gray, cv2.COLOR_RGB2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            eq = clahe.apply(gray_single)
            
            # Unsharp mask锐化
            blur = cv2.GaussianBlur(eq, (3, 3), 0)
            sharp = cv2.addWeighted(eq, 1.5, blur, -0.5, 0)
            
            # 转为PIL图像并计算哈希
            pil_img = Image.fromarray(sharp)
            return imagehash.phash(pil_img, hash_size=16, highfreq_factor=8)
            
        except Exception as e:
            print(f"[视频静止片段清理器] 哈希计算失败: {str(e)}")
            # 降级到简单哈希
            try:
                pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                return imagehash.phash(pil_img)
            except:
                return None
    
    @classmethod
    def _export_video_without_segments(cls, video_path, segments, output_path):
        """使用FFmpeg移除静止片段"""
        try:
            import ffmpeg
            
            # 获取视频时长
            duration = cls._get_video_duration(video_path)
            if duration is None:
                return False
            
            # 计算保留的时间段
            keep_ranges = cls._invert_segments(segments, duration)
            if not keep_ranges:
                return False
            
            # 构造select表达式
            expr = '+'.join([f'between(t,{s},{e})' for s, e in keep_ranges])
            
            # 检查是否有音频流
            has_audio = cls._has_audio_stream(video_path)
            
            inp = ffmpeg.input(video_path)
            
            # 视频流处理
            v = inp.video.filter('select', expr).filter('setpts', 'N/FRAME_RATE/TB')
            
            if has_audio:
                # 音频流处理
                a = inp.audio.filter('aselect', expr).filter('asetpts', 'N/SR/TB')
                out = ffmpeg.output(
                    v, a, output_path,
                    vcodec='libx264', acodec='aac', 
                    preset='fast',
                    **{'b:v': '2000k', 'b:a': '128k'}
                )
            else:
                out = ffmpeg.output(
                    v, output_path,
                    vcodec='libx264', 
                    preset='fast',
                    **{'b:v': '2000k'}
                )
            
            out = out.overwrite_output()
            out.run(quiet=True)
            
            # 验证输出文件
            return os.path.exists(output_path) and os.path.getsize(output_path) > 0
            
        except Exception as e:
            print(f"[视频静止片段清理器] FFmpeg处理失败: {str(e)}")
            return False
    
    @classmethod
    def _get_video_duration(cls, video_path):
        """获取视频时长"""
        try:
            import ffmpeg
            probe = ffmpeg.probe(video_path)
            return float(probe['format']['duration'])
        except:
            return None
    
    @classmethod
    def _has_audio_stream(cls, video_path):
        """检查视频是否有音频流"""
        try:
            import ffmpeg
            probe = ffmpeg.probe(video_path)
            for stream in probe.get('streams', []):
                if stream.get('codec_type') == 'audio':
                    return True
            return False
        except:
            return False
    
    @classmethod
    def _invert_segments(cls, segments, duration):
        """将需要移除的时间段转换为需要保留的时间段"""
        if not segments:
            return [(0.0, duration)]
        
        segments = sorted(segments, key=lambda x: x[0])
        keep = []
        prev = 0.0
        
        for start, end in segments:
            start = max(0.0, start)
            end = min(duration, end)
            if start > prev:
                keep.append((prev, start))
            prev = max(prev, end)
        
        if prev < duration:
            keep.append((prev, duration))
        
        return [(round(s, 3), round(e, 3)) for s, e in keep if e - s > 0.1]
    
    @classmethod
    def _generate_cleaning_report(cls, stats, failed_files, enable_preview):
        """生成清理报告"""
        if not stats and not failed_files:
            return "未处理任何文件"
        
        total_files = len(stats) + len(failed_files)
        successful_files = len(stats)
        
        if successful_files > 0:
            total_original = sum(s['original_duration'] for s in stats)
            total_removed = sum(s['removed_duration'] for s in stats)
            avg_compression = sum(s['compression_ratio'] for s in stats) / successful_files
            
            report = f"""静止片段清理完成报告：
✅ 成功处理: {successful_files}/{total_files} 个文件
📊 时长统计: 原始 {total_original:.1f}秒 → 清理后 {total_original-total_removed:.1f}秒
🗑️  移除时长: {total_removed:.1f}秒 ({(total_removed/total_original*100):.1f}%)
📈 平均压缩率: {avg_compression:.1f}%"""
            
            if failed_files:
                report += f"\n❌ 失败文件: {len(failed_files)} 个"
        else:
            report = f"处理失败: {len(failed_files)} 个文件未能成功处理"
        
        return report


class GameHighlightExtractor(io.ComfyNode):
    """游戏精彩片段提取器 - 基于模板匹配自动识别游戏局次"""
    
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="GameHighlightExtractor",
            display_name="游戏精彩片段提取器",
            category="batch_video",
            description="基于模板匹配和OCR识别游戏开始/结束，自动提取完整游戏局次",
            inputs=[
                io.String.Input("video_folder", tooltip="视频文件夹路径"),
                io.Image.Input("start_template", optional=True, tooltip="开始模板图片（可选）"),
                io.Image.Input("end_template", optional=True, tooltip="结束模板图片（可选）"),
                io.String.Input("start_keywords", default="开始,start,准备,ready,倒计时", tooltip="开始关键词（逗号分隔）"),
                io.String.Input("end_keywords", default="结束,game over,胜利,victory,再来一局", tooltip="结束关键词（逗号分隔）"),
                io.Float.Input("template_threshold", default=0.8, tooltip="模板匹配阈值(0-1)"),
                io.Float.Input("ocr_confidence", default=0.7, tooltip="OCR识别置信度(0-1)"),
                io.Int.Input("start_offset", default=0, tooltip="开始帧后延迟秒数"),
                io.Int.Input("end_offset", default=0, tooltip="结束帧后延迟秒数"),
                io.Int.Input("min_game_duration", default=10, tooltip="最小游戏时长(秒)"),
                io.Int.Input("max_game_duration", default=300, tooltip="最大游戏时长(秒)"),
                io.Bool.Input("enable_ocr", default=True, tooltip="启用OCR文字识别"),
                io.String.Input("output_prefix", default="游戏局次", tooltip="输出前缀"),
            ],
            outputs=[
                io.String.Output("output_folder", display_name="输出文件夹"),
                io.Int.Output("total_sessions", display_name="游戏局次总数"),
                io.String.Output("extraction_report", display_name="提取报告"),
            ],
        )
    
    @classmethod
    def execute(cls, video_folder, start_template=None, end_template=None,
                start_keywords="开始,start,准备,ready,倒计时", end_keywords="结束,game over,胜利,victory,再来一局",
                template_threshold=0.8, ocr_confidence=0.7, start_offset=0, end_offset=0,
                min_game_duration=10, max_game_duration=300, enable_ocr=True, output_prefix="游戏局次"):
        
        import os
        import time
        import json
        from pathlib import Path
        
        try:
            # 验证输入文件夹
            if not os.path.exists(video_folder):
                raise ValueError(f"视频文件夹不存在: {video_folder}")
            
            # 扫描视频文件
            video_files = []
            for ext in ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v']:
                pattern = os.path.join(video_folder, f"*{ext}")
                import glob
                video_files.extend(glob.glob(pattern))
                video_files.extend(glob.glob(pattern.upper()))
            
            if not video_files:
                raise ValueError(f"在文件夹中未找到视频文件: {video_folder}")
            
            # 处理模板图片
            start_template_cv = cls._convert_image_to_cv(start_template) if start_template is not None else None
            end_template_cv = cls._convert_image_to_cv(end_template) if end_template is not None else None
            
            # 处理关键词
            start_words = [w.strip().lower() for w in start_keywords.split(',') if w.strip()]
            end_words = [w.strip().lower() for w in end_keywords.split(',') if w.strip()]
            
            # 创建输出文件夹
            timestamp = int(time.time())
            output_folder = os.path.join(folder_paths.get_temp_directory(), f"{output_prefix}_提取_{timestamp}")
            os.makedirs(output_folder, exist_ok=True)
            
            total_sessions = 0
            extraction_stats = []
            
            print(f"[游戏精彩片段提取器] 开始处理 {len(video_files)} 个视频文件")
            print(f"[游戏精彩片段提取器] 模板: 开始{'有' if start_template_cv is not None else '无'}, 结束{'有' if end_template_cv is not None else '无'}")
            print(f"[游戏精彩片段提取器] 偏移: 开始+{start_offset}秒, 结束+{end_offset}秒")
            
            for video_file in video_files:
                try:
                    video_name = Path(video_file).stem
                    print(f"[游戏精彩片段提取器] 处理视频: {video_name}")
                    
                    # 检测游戏事件
                    events = []
                    
                    # 模板匹配检测
                    if start_template_cv is not None or end_template_cv is not None:
                        template_events = cls._detect_template_events(
                            video_file, start_template_cv, end_template_cv, template_threshold
                        )
                        events.extend(template_events)
                    
                    # OCR文字识别检测
                    if enable_ocr and (start_words or end_words):
                        ocr_events = cls._detect_ocr_events(
                            video_file, start_words, end_words, ocr_confidence
                        )
                        events.extend(ocr_events)
                    
                    if not events:
                        print(f"[游戏精彩片段提取器] {video_name}: 未检测到游戏事件")
                        continue
                    
                    # 合并和排序事件
                    events = sorted(events, key=lambda x: x['time'])
                    print(f"[游戏精彩片段提取器] {video_name}: 检测到 {len(events)} 个事件")
                    
                    # 配对游戏局次
                    sessions = cls._pair_game_sessions(
                        events, min_game_duration, max_game_duration, start_offset, end_offset
                    )
                    
                    if not sessions:
                        print(f"[游戏精彩片段提取器] {video_name}: 未找到有效的游戏局次")
                        continue
                    
                    print(f"[游戏精彩片段提取器] {video_name}: 找到 {len(sessions)} 个游戏局次")
                    
                    # 创建视频输出目录
                    video_output_dir = os.path.join(output_folder, video_name)
                    os.makedirs(video_output_dir, exist_ok=True)
                    
                    # 提取游戏片段
                    extracted_count = 0
                    for i, session in enumerate(sessions):
                        output_filename = f"game_session_{i+1:03d}.mp4"
                        output_path = os.path.join(video_output_dir, output_filename)
                        
                        success = cls._extract_video_segment(
                            video_file, session['start'], session['end'], output_path
                        )
                        
                        if success:
                            extracted_count += 1
                            print(f"[游戏精彩片段提取器] 提取: {output_filename} ({session['duration']:.1f}秒)")
                        else:
                            print(f"[游戏精彩片段提取器] 提取失败: {output_filename}")
                    
                    # 统计信息
                    extraction_stats.append({
                        "file": video_name,
                        "total_sessions": len(sessions),
                        "extracted_sessions": extracted_count,
                        "total_duration": sum(s['duration'] for s in sessions),
                        "events_detected": len(events)
                    })
                    
                    total_sessions += extracted_count
                    
                except Exception as e:
                    print(f"[游戏精彩片段提取器] 处理失败: {video_name}, 错误: {str(e)}")
            
            # 生成提取报告
            report = cls._generate_extraction_report(extraction_stats)
            
            # 保存详细报告
            report_path = os.path.join(output_folder, "extraction_report.json")
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "summary": report,
                    "details": extraction_stats,
                    "settings": {
                        "start_offset": start_offset,
                        "end_offset": end_offset,
                        "min_game_duration": min_game_duration,
                        "max_game_duration": max_game_duration,
                        "template_threshold": template_threshold,
                        "ocr_confidence": ocr_confidence
                    }
                }, f, ensure_ascii=False, indent=2)
            
            print(f"[游戏精彩片段提取器] 处理完成: 共提取 {total_sessions} 个游戏局次")
            
            return io.NodeOutput(output_folder, total_sessions, report)
            
        except Exception as e:
            error_msg = f"游戏精彩片段提取器执行失败: {str(e)}"
            print(f"[游戏精彩片段提取器] 错误: {error_msg}")
            return io.NodeOutput("", 0, error_msg)
    
    @classmethod
    def _convert_image_to_cv(cls, image_tensor):
        """将ComfyUI图像张量转换为OpenCV格式"""
        try:
            import cv2
            import numpy as np
            import torch
            
            if image_tensor is None:
                return None
            
            # ComfyUI图像格式: [batch, height, width, channels] (0-1 float)
            if isinstance(image_tensor, torch.Tensor):
                # 取第一个batch
                img_array = image_tensor[0].cpu().numpy()
            else:
                img_array = image_tensor[0] if len(image_tensor.shape) == 4 else image_tensor
            
            # 转换为0-255范围
            if img_array.max() <= 1.0:
                img_array = (img_array * 255).astype(np.uint8)
            
            # 转换为BGR格式 (OpenCV默认)
            if len(img_array.shape) == 3 and img_array.shape[2] == 3:
                # RGB to BGR
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            return img_array
            
        except Exception as e:
            print(f"[游戏精彩片段提取器] 图像转换失败: {str(e)}")
            return None
    
    @classmethod
    def _detect_template_events(cls, video_path, start_template, end_template, threshold):
        """模板匹配检测游戏事件"""
        try:
            import cv2
            
            cap = cv2.VideoCapture(video_path)
            events = []
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = 0
            
            # 每秒检测一次
            sample_interval = max(1, int(fps))
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                if frame_count % sample_interval != 0:
                    continue
                
                current_time = frame_count / fps
                
                # 检测开始模板
                if start_template is not None:
                    result = cv2.matchTemplate(frame, start_template, cv2.TM_CCOEFF_NORMED)
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                    
                    if max_val >= threshold:
                        events.append({
                            "time": current_time,
                            "event": "start",
                            "method": "template",
                            "template": "start_template",
                            "confidence": max_val
                        })
                
                # 检测结束模板
                if end_template is not None:
                    result = cv2.matchTemplate(frame, end_template, cv2.TM_CCOEFF_NORMED)
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                    
                    if max_val >= threshold:
                        events.append({
                            "time": current_time,
                            "event": "end",
                            "method": "template",
                            "template": "end_template",
                            "confidence": max_val
                        })
            
            cap.release()
            return events
            
        except Exception as e:
            print(f"[游戏精彩片段提取器] 模板检测失败: {str(e)}")
            return []
    
    @classmethod
    def _detect_ocr_events(cls, video_path, start_words, end_words, confidence_threshold):
        """OCR文字识别检测游戏事件"""
        try:
            import cv2
            import easyocr
            
            reader = easyocr.Reader(['ch_sim', 'en'])
            cap = cv2.VideoCapture(video_path)
            events = []
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = 0
            
            # 每2秒检测一次（OCR较慢）
            sample_interval = max(1, int(fps * 2))
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                if frame_count % sample_interval != 0:
                    continue
                
                current_time = frame_count / fps
                
                try:
                    # OCR识别
                    results = reader.readtext(frame)
                    
                    for (bbox, text, confidence) in results:
                        if confidence < confidence_threshold:
                            continue
                        
                        text_lower = text.lower().strip()
                        
                        # 检测开始关键词
                        if any(keyword in text_lower for keyword in start_words):
                            events.append({
                                "time": current_time,
                                "event": "start",
                                "method": "ocr",
                                "text": text,
                                "confidence": confidence
                            })
                        
                        # 检测结束关键词
                        elif any(keyword in text_lower for keyword in end_words):
                            events.append({
                                "time": current_time,
                                "event": "end",
                                "method": "ocr", 
                                "text": text,
                                "confidence": confidence
                            })
                
                except Exception:
                    continue
            
            cap.release()
            return events
            
        except ImportError:
            print("[游戏精彩片段提取器] 警告: easyocr未安装，跳过OCR检测")
            return []
        except Exception as e:
            print(f"[游戏精彩片段提取器] OCR检测失败: {str(e)}")
            return []
    
    @classmethod
    def _pair_game_sessions(cls, events, min_duration, max_duration, start_offset, end_offset):
        """配对游戏开始和结束事件"""
        sessions = []
        
        # 合并相近的同类事件（去重）
        merged_events = cls._merge_nearby_events(events, gap=3.0)
        
        i = 0
        while i < len(merged_events) - 1:
            current_event = merged_events[i]
            
            if current_event['event'] == 'start':
                # 查找下一个结束事件
                for j in range(i + 1, len(merged_events)):
                    next_event = merged_events[j]
                    
                    if next_event['event'] == 'end':
                        # 计算实际的开始和结束时间（应用偏移）
                        actual_start = max(0, current_event['time'] + start_offset)
                        actual_end = next_event['time'] + end_offset
                        duration = actual_end - actual_start
                        
                        # 验证时长是否合理
                        if min_duration <= duration <= max_duration:
                            sessions.append({
                                "start": actual_start,
                                "end": actual_end,
                                "duration": duration,
                                "start_event": current_event,
                                "end_event": next_event
                            })
                        
                        i = j  # 跳到结束事件位置
                        break
                else:
                    i += 1
            else:
                i += 1
        
        return sessions
    
    @classmethod
    def _merge_nearby_events(cls, events, gap=3.0):
        """合并时间相近的同类事件"""
        if not events:
            return events
        
        merged = []
        events = sorted(events, key=lambda x: x['time'])
        
        current_event = events[0]
        
        for event in events[1:]:
            # 如果是同类事件且时间相近，选择置信度更高的
            if (event['event'] == current_event['event'] and 
                event['time'] - current_event['time'] <= gap):
                
                if event.get('confidence', 0) > current_event.get('confidence', 0):
                    current_event = event
            else:
                merged.append(current_event)
                current_event = event
        
        merged.append(current_event)
        return merged
    
    @classmethod
    def _extract_video_segment(cls, video_path, start_time, end_time, output_path):
        """提取视频片段"""
        try:
            import ffmpeg
            
            duration = end_time - start_time
            
            (
                ffmpeg
                .input(video_path, ss=start_time, t=duration)
                .output(output_path, vcodec='libx264', acodec='aac', preset='fast')
                .overwrite_output()
                .run(quiet=True)
            )
            
            # 验证输出文件
            return os.path.exists(output_path) and os.path.getsize(output_path) > 0
            
        except Exception as e:
            print(f"[游戏精彩片段提取器] 视频提取失败: {str(e)}")
            return False
    
    @classmethod
    def _generate_extraction_report(cls, stats):
        """生成提取报告"""
        if not stats:
            return "未提取任何游戏局次"
        
        total_videos = len(stats)
        successful_videos = len([s for s in stats if s['extracted_sessions'] > 0])
        total_sessions = sum(s['extracted_sessions'] for s in stats)
        total_duration = sum(s['total_duration'] for s in stats)
        
        report = f"""游戏精彩片段提取完成报告：
🎮 处理视频: {successful_videos}/{total_videos} 个成功
🎯 提取局次: {total_sessions} 个游戏局次
⏱️ 总时长: {total_duration:.1f} 秒 ({total_duration/60:.1f} 分钟)
📊 平均每视频: {total_sessions/successful_videos:.1f} 个局次"""
        
        if successful_videos < total_videos:
            failed_videos = total_videos - successful_videos
            report += f"\n❌ 失败视频: {failed_videos} 个"
        
        return report


class VideoThumbnailGenerator(io.ComfyNode):
    """视频缩略图生成器 - 智能生成视频封面，支持文字叠加和多尺寸输出"""
    
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="VideoThumbnailGenerator",
            display_name="视频缩略图生成器",
            category="batch_video",
            description="智能选择精彩帧生成视频缩略图，支持文字叠加和统一模板",
            inputs=[
                io.String.Input("video_folder", tooltip="视频文件夹路径"),
                io.String.Input("title_template", default="{filename}", tooltip="标题模板，支持{filename}, {index}, {duration}等变量"),
                io.String.Input("font_path", optional=True, tooltip="字体文件路径（可选，使用默认字体）"),
                io.Int.Input("font_size", default=48, tooltip="字体大小"),
                io.String.Input("font_color", default="white", tooltip="字体颜色(white/black/red/blue等)"),
                io.String.Input("outline_color", default="black", tooltip="字体描边颜色"),
                io.Int.Input("outline_width", default=3, tooltip="字体描边宽度"),
                io.String.Input("text_position", default="bottom-center", tooltip="文字位置(top-left/top-center/top-right/center/bottom-left/bottom-center/bottom-right)"),
                io.String.Input("frame_selection", default="middle", tooltip="帧选择策略(first/middle/last/brightest/highest_contrast/most_colorful)"),
                io.Float.Input("frame_offset", default=0.0, tooltip="帧偏移比例(0.0-1.0)"),
                io.String.Input("output_sizes", default="1920x1080,1280x720,640x360", tooltip="输出尺寸列表(逗号分隔)"),
                io.String.Input("output_format", default="jpg", tooltip="输出格式(jpg/png)"),
                io.Int.Input("output_quality", default=90, tooltip="输出质量(1-100)"),
                io.Bool.Input("add_gradient", default=True, tooltip="添加文字背景渐变"),
                io.String.Input("output_prefix", default="缩略图", tooltip="输出前缀"),
            ],
            outputs=[
                io.String.Output("output_folder", display_name="输出文件夹"),
                io.Int.Output("generated_count", display_name="生成数量"),
                io.String.Output("generation_report", display_name="生成报告"),
            ],
        )
    
    @classmethod
    def execute(cls, video_folder, title_template="{filename}", font_path=None, font_size=48,
                font_color="white", outline_color="black", outline_width=3, text_position="bottom-center",
                frame_selection="middle", frame_offset=0.0, output_sizes="1920x1080,1280x720,640x360",
                output_format="jpg", output_quality=90, add_gradient=True, output_prefix="缩略图"):
        
        import os
        import time
        import json
        from pathlib import Path
        
        try:
            # 验证输入文件夹
            if not os.path.exists(video_folder):
                raise ValueError(f"视频文件夹不存在: {video_folder}")
            
            # 扫描视频文件
            video_files = []
            for ext in ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v']:
                pattern = os.path.join(video_folder, f"*{ext}")
                import glob
                video_files.extend(glob.glob(pattern))
                video_files.extend(glob.glob(pattern.upper()))
            
            if not video_files:
                raise ValueError(f"在文件夹中未找到视频文件: {video_folder}")
            
            # 解析输出尺寸
            try:
                sizes = []
                for size_str in output_sizes.split(','):
                    size_str = size_str.strip()
                    if 'x' in size_str:
                        w, h = map(int, size_str.split('x'))
                        sizes.append((w, h))
                if not sizes:
                    sizes = [(1920, 1080)]  # 默认尺寸
            except:
                sizes = [(1920, 1080)]  # 解析失败使用默认
            
            # 创建输出文件夹
            timestamp = int(time.time())
            output_folder = os.path.join(folder_paths.get_temp_directory(), f"{output_prefix}_生成_{timestamp}")
            os.makedirs(output_folder, exist_ok=True)
            
            generated_count = 0
            generation_stats = []
            
            print(f"[视频缩略图生成器] 开始处理 {len(video_files)} 个视频文件")
            print(f"[视频缩略图生成器] 输出尺寸: {sizes}")
            print(f"[视频缩略图生成器] 帧选择策略: {frame_selection}")
            
            for i, video_file in enumerate(video_files):
                try:
                    video_name = Path(video_file).stem
                    print(f"[视频缩略图生成器] 处理视频: {video_name} ({i+1}/{len(video_files)})")
                    
                    # 获取视频信息
                    video_info = cls._get_video_info(video_file)
                    if not video_info:
                        print(f"[视频缩略图生成器] 无法获取视频信息: {video_name}")
                        continue
                    
                    duration = video_info.get('duration', 0)
                    
                    # 提取关键帧
                    frame_time = cls._calculate_frame_time(duration, frame_selection, frame_offset)
                    frame_image = cls._extract_frame(video_file, frame_time)
                    
                    if frame_image is None:
                        print(f"[视频缩略图生成器] 帧提取失败: {video_name}")
                        continue
                    
                    # 生成标题文字
                    title_text = cls._generate_title(title_template, video_name, i+1, duration)
                    
                    # 生成不同尺寸的缩略图
                    size_count = 0
                    for width, height in sizes:
                        try:
                            # 调整图像尺寸
                            resized_frame = cls._resize_frame(frame_image, width, height)
                            
                            # 添加文字叠加
                            final_image = cls._add_text_overlay(
                                resized_frame, title_text, font_path, font_size,
                                font_color, outline_color, outline_width,
                                text_position, add_gradient
                            )
                            
                            # 保存缩略图
                            output_filename = f"{video_name}_{width}x{height}.{output_format}"
                            output_path = os.path.join(output_folder, output_filename)
                            
                            success = cls._save_image(final_image, output_path, output_format, output_quality)
                            if success:
                                size_count += 1
                                print(f"[视频缩略图生成器] 生成: {output_filename}")
                            else:
                                print(f"[视频缩略图生成器] 保存失败: {output_filename}")
                        
                        except Exception as e:
                            print(f"[视频缩略图生成器] 尺寸处理失败 {width}x{height}: {str(e)}")
                    
                    if size_count > 0:
                        generation_stats.append({
                            "file": video_name,
                            "sizes_generated": size_count,
                            "total_sizes": len(sizes),
                            "title": title_text,
                            "frame_time": frame_time,
                            "duration": duration
                        })
                        generated_count += size_count
                    
                except Exception as e:
                    print(f"[视频缩略图生成器] 处理失败: {video_name}, 错误: {str(e)}")
            
            # 生成报告
            report = cls._generate_report(generation_stats, len(video_files), len(sizes))
            
            # 保存详细报告
            report_path = os.path.join(output_folder, "generation_report.json")
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "summary": report,
                    "details": generation_stats,
                    "settings": {
                        "title_template": title_template,
                        "frame_selection": frame_selection,
                        "output_sizes": output_sizes,
                        "output_format": output_format,
                        "font_size": font_size,
                        "text_position": text_position
                    }
                }, f, ensure_ascii=False, indent=2)
            
            print(f"[视频缩略图生成器] 处理完成: 共生成 {generated_count} 张缩略图")
            
            return io.NodeOutput(output_folder, generated_count, report)
            
        except Exception as e:
            error_msg = f"视频缩略图生成器执行失败: {str(e)}"
            print(f"[视频缩略图生成器] 错误: {error_msg}")
            return io.NodeOutput("", 0, error_msg)
    
    @classmethod
    def _get_video_info(cls, video_path):
        """获取视频基本信息"""
        try:
            import ffmpeg
            probe = ffmpeg.probe(video_path)
            video_stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            return {
                'duration': float(probe['format']['duration']),
                'width': int(video_stream['width']),
                'height': int(video_stream['height']),
                'fps': eval(video_stream['r_frame_rate'])
            }
        except Exception as e:
            print(f"[视频缩略图生成器] 视频信息获取失败: {str(e)}")
            return None
    
    @classmethod
    def _calculate_frame_time(cls, duration, strategy, offset):
        """计算要提取的帧时间点"""
        if strategy == "first":
            return max(0.1, duration * 0.01)  # 避免黑屏
        elif strategy == "last":
            return max(0, duration * 0.95)  # 避免结束黑屏
        elif strategy == "middle":
            return duration * 0.5
        else:
            # 对于其他策略，先使用中间位置，后续可以改为智能分析
            return duration * (0.3 + offset * 0.4)  # 0.3-0.7范围
    
    @classmethod
    def _extract_frame(cls, video_path, time_point):
        """从视频中提取指定时间点的帧"""
        try:
            import cv2
            
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return None
            
            # 跳转到指定时间点
            cap.set(cv2.CAP_PROP_POS_MSEC, time_point * 1000)
            ret, frame = cap.read()
            cap.release()
            
            if ret and frame is not None:
                return frame
            else:
                return None
                
        except Exception as e:
            print(f"[视频缩略图生成器] 帧提取失败: {str(e)}")
            return None
    
    @classmethod
    def _resize_frame(cls, frame, target_width, target_height):
        """调整帧尺寸，保持宽高比"""
        try:
            import cv2
            
            h, w = frame.shape[:2]
            
            # 计算缩放比例
            scale = min(target_width / w, target_height / h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            
            # 缩放图像
            resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
            
            # 创建目标尺寸的画布（黑色背景）
            canvas = cv2.zeros((target_height, target_width, 3), dtype=resized.dtype)
            
            # 计算居中位置
            x_offset = (target_width - new_w) // 2
            y_offset = (target_height - new_h) // 2
            
            # 将缩放后的图像放到画布中心
            canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
            
            return canvas
            
        except Exception as e:
            print(f"[视频缩略图生成器] 图像缩放失败: {str(e)}")
            return frame
    
    @classmethod
    def _generate_title(cls, template, filename, index, duration):
        """生成标题文字"""
        try:
            # 可用变量
            variables = {
                'filename': Path(filename).stem,
                'index': str(index),
                'duration': f"{int(duration//60):02d}:{int(duration%60):02d}",
                'duration_sec': str(int(duration))
            }
            
            title = template
            for var, value in variables.items():
                title = title.replace(f'{{{var}}}', value)
            
            return title
            
        except Exception as e:
            print(f"[视频缩略图生成器] 标题生成失败: {str(e)}")
            return filename
    
    @classmethod
    def _add_text_overlay(cls, image, text, font_path, font_size, font_color,
                          outline_color, outline_width, position, add_gradient):
        """添加文字叠加"""
        try:
            import cv2
            import numpy as np
            from PIL import Image, ImageDraw, ImageFont
            
            # 转换为PIL格式
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(pil_image)
            
            # 加载字体
            try:
                if font_path and os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, font_size)
                else:
                    # 尝试使用系统字体
                    font = ImageFont.load_default()
                    # 如果可能，尝试加载更好的字体
                    try:
                        font = ImageFont.truetype("arial.ttf", font_size)
                    except:
                        pass
            except:
                font = ImageFont.load_default()
            
            # 获取文字尺寸
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # 计算文字位置
            img_width, img_height = pil_image.size
            x, y = cls._calculate_text_position(position, img_width, img_height, text_width, text_height)
            
            # 添加渐变背景
            if add_gradient:
                cls._add_text_gradient(draw, x, y, text_width, text_height, img_width, img_height)
            
            # 颜色映射
            color_map = {
                'white': (255, 255, 255),
                'black': (0, 0, 0),
                'red': (255, 0, 0),
                'blue': (0, 0, 255),
                'green': (0, 255, 0),
                'yellow': (255, 255, 0)
            }
            
            text_color = color_map.get(font_color.lower(), (255, 255, 255))
            stroke_color = color_map.get(outline_color.lower(), (0, 0, 0))
            
            # 绘制文字（带描边）
            draw.text((x, y), text, font=font, fill=text_color, 
                     stroke_width=outline_width, stroke_fill=stroke_color)
            
            # 转换回OpenCV格式
            return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
        except Exception as e:
            print(f"[视频缩略图生成器] 文字叠加失败: {str(e)}")
            return image
    
    @classmethod
    def _calculate_text_position(cls, position, img_w, img_h, text_w, text_h):
        """计算文字位置"""
        margin = 20
        
        positions = {
            'top-left': (margin, margin),
            'top-center': (img_w // 2 - text_w // 2, margin),
            'top-right': (img_w - text_w - margin, margin),
            'center': (img_w // 2 - text_w // 2, img_h // 2 - text_h // 2),
            'bottom-left': (margin, img_h - text_h - margin),
            'bottom-center': (img_w // 2 - text_w // 2, img_h - text_h - margin),
            'bottom-right': (img_w - text_w - margin, img_h - text_h - margin)
        }
        
        return positions.get(position, positions['bottom-center'])
    
    @classmethod
    def _add_text_gradient(cls, draw, x, y, text_w, text_h, img_w, img_h):
        """添加文字背景渐变"""
        try:
            from PIL import Image, ImageDraw
            import numpy as np
            
            # 创建渐变背景区域
            gradient_height = text_h + 40
            gradient_y = max(0, y - 20)
            
            # 创建渐变（从透明到半透明黑色）
            gradient = Image.new('RGBA', (img_w, gradient_height), (0, 0, 0, 0))
            gradient_draw = ImageDraw.Draw(gradient)
            
            for i in range(gradient_height):
                alpha = int(100 * (i / gradient_height))  # 渐变透明度
                color = (0, 0, 0, alpha)
                gradient_draw.line([(0, i), (img_w, i)], fill=color)
            
            # 这里简化处理，直接绘制半透明矩形
            overlay = Image.new('RGBA', (img_w, img_h), (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.rectangle([0, gradient_y, img_w, gradient_y + gradient_height], 
                                 fill=(0, 0, 0, 80))
            
        except Exception as e:
            print(f"[视频缩略图生成器] 渐变背景失败: {str(e)}")
    
    @classmethod
    def _save_image(cls, image, output_path, format_type, quality):
        """保存图像文件"""
        try:
            import cv2
            
            if format_type.lower() == 'png':
                success = cv2.imwrite(output_path, image, [cv2.IMWRITE_PNG_COMPRESSION, 9])
            else:  # jpg
                success = cv2.imwrite(output_path, image, [cv2.IMWRITE_JPEG_QUALITY, quality])
            
            return success and os.path.exists(output_path) and os.path.getsize(output_path) > 0
            
        except Exception as e:
            print(f"[视频缩略图生成器] 图像保存失败: {str(e)}")
            return False
    
    @classmethod
    def _generate_report(cls, stats, total_videos, total_sizes):
        """生成处理报告"""
        if not stats:
            return "未生成任何缩略图"
        
        successful_videos = len(stats)
        total_generated = sum(s['sizes_generated'] for s in stats)
        expected_total = total_videos * total_sizes
        
        report = f"""缩略图生成完成报告：
🎨 处理视频: {successful_videos}/{total_videos} 个成功
📸 生成缩略图: {total_generated}/{expected_total} 张
📊 成功率: {(total_generated/expected_total*100):.1f}%
⭐ 平均每视频: {total_generated/successful_videos:.1f} 张缩略图"""
        
        if successful_videos < total_videos:
            failed_videos = total_videos - successful_videos
            report += f"\n❌ 失败视频: {failed_videos} 个"
        
        return report


class SmartAudioBasedCutter(io.ComfyNode):
    """批量视频切分器-按音频时长切分 - 根据音频和引流视频自动计算切分时长"""
    
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="SmartAudioBasedCutter",
            display_name="批量视频切分器-按音频时长切分",
            category="batch_video",
            description="根据音频文件和引流视频智能计算切分时长",
            inputs=[
                io.String.Input(
                    "video_folder", 
                    tooltip="视频文件夹路径"
                ),
                io.String.Input(
                    "audio_folder", 
                    tooltip="音频文件夹路径"
                ),
                io.String.Input(
                    "trailer_folder", 
                    optional=True,
                    tooltip="引流视频文件夹路径(可选)"
                ),
                io.Bool.Input(
                    "skip_short_segments", 
                    default=True,
                    tooltip="跳过过短片段"
                ),
                io.String.Input(
                    "output_prefix", 
                    default="智能切分", 
                    tooltip="输出前缀"
                ),
            ],
            outputs=[
                io.String.Output("output_folder", display_name="文件夹路径"),
                io.Int.Output("total_segments", display_name="总片段数"),
                io.Float.Output("calculated_duration", display_name="计算时长"),
                io.String.Output("summary", display_name="处理摘要"),
            ],
        )

    @classmethod
    def execute(cls, video_folder: str, audio_folder: str, trailer_folder: str = None,
                skip_short_segments: bool = True, output_prefix: str = "智能切分") -> io.NodeOutput:
        
        import random
        
        # 创建输出文件夹
        output_dir = folder_paths.get_output_directory()
        output_folder = create_output_folder(output_dir, output_prefix)
        
        # 扫描各类文件
        if not os.path.exists(video_folder):
            return io.NodeOutput(output_folder, 0, 0.0, "错误：视频文件夹不存在")
        
        if not os.path.exists(audio_folder):
            return io.NodeOutput(output_folder, 0, 0.0, "错误：音频文件夹不存在")
        
        video_files = scan_video_files(video_folder)
        audio_files = scan_media_files(audio_folder, ['audio'])['audio']
        
        if not video_files:
            return io.NodeOutput(output_folder, 0, 0.0, "错误：未找到视频文件")
            
        if not audio_files:
            return io.NodeOutput(output_folder, 0, 0.0, "错误：未找到音频文件")
        
        print(f"找到 {len(video_files)} 个视频文件")
        print(f"找到 {len(audio_files)} 个音频文件")
        
        # 计算智能切分时长
        try:
            # 随机选择一个音频文件作为时长参考
            reference_audio = random.choice(audio_files)
            audio_duration = get_video_duration(reference_audio)  # 音频也可以用这个函数
            print(f"参考音频时长: {audio_duration:.2f}秒")
            
            calculated_duration = audio_duration
            strategy_info = f"使用音频时长: {audio_duration:.2f}秒"
            
            # 如果有引流视频文件夹，进行智能计算
            if trailer_folder and os.path.exists(trailer_folder):
                trailer_files = scan_video_files(trailer_folder)
                if trailer_files:
                    # 随机选择一个引流视频作为参考
                    reference_trailer = random.choice(trailer_files)
                    print(f"参考引流视频: {os.path.basename(reference_trailer)}")
                    
                    # 检查引流视频是否有音频
                    trailer_info = get_video_info(reference_trailer)
                    has_audio = any(stream.get('codec_type') == 'audio' for stream in trailer_info.get('streams', []))
                    
                    if has_audio:
                        # 引流视频有音频：切分时长 = 音频时长
                        calculated_duration = audio_duration
                        strategy_info = f"引流视频有音频，使用音频时长: {calculated_duration:.2f}秒"
                        print("引流视频有音频，使用完整音频时长")
                    else:
                        # 引流视频无音频：切分时长 = 音频时长 - 引流视频时长
                        trailer_duration = get_video_duration(reference_trailer)
                        calculated_duration = audio_duration - trailer_duration
                        strategy_info = f"引流视频无音频，计算时长: {audio_duration:.2f} - {trailer_duration:.2f} = {calculated_duration:.2f}秒"
                        print(f"引流视频无音频，计算时长: {calculated_duration:.2f}秒")
                        
                        if calculated_duration <= 0:
                            return io.NodeOutput(output_folder, 0, calculated_duration, 
                                               f"错误：引流视频时长({trailer_duration:.2f}s) >= 音频时长({audio_duration:.2f}s)")
            
        except Exception as e:
            return io.NodeOutput(output_folder, 0, 0.0, f"时长计算失败: {str(e)}")
        
        print(f"最终切分时长: {calculated_duration:.2f}秒")
        
        # 开始批量切分视频
        total_segments = 0
        processed_videos = 0
        
        for video_file in video_files:
            try:
                video_name = Path(video_file).stem
                video_duration = get_video_duration(video_file)
                
                if video_duration < calculated_duration:
                    if skip_short_segments:
                        print(f"跳过短视频: {video_name} ({video_duration:.2f}s < {calculated_duration:.2f}s)")
                        continue
                    else:
                        print(f"处理短视频: {video_name} ({video_duration:.2f}s)")
                
                # 创建视频输出目录
                video_output_dir = os.path.join(output_folder, video_name)
                os.makedirs(video_output_dir, exist_ok=True)
                
                # 计算可以切分的段数
                num_segments = int(video_duration // calculated_duration)
                if num_segments == 0 and not skip_short_segments:
                    num_segments = 1  # 至少切一段
                
                print(f"处理视频: {video_name}, 将切分为 {num_segments} 段")
                
                # 切分视频
                segments_created = 0
                import ffmpeg
                
                for i in range(num_segments):
                    start_time = i * calculated_duration
                    segment_duration = min(calculated_duration, video_duration - start_time)
                    
                    if segment_duration < calculated_duration * 0.5 and skip_short_segments:
                        print(f"跳过过短片段: {segment_duration:.2f}s")
                        continue
                    
                    output_filename = f"segment_{i+1:03d}.mp4"
                    output_path = os.path.join(video_output_dir, output_filename)
                    
                    try:
                        (
                            ffmpeg
                            .input(video_file, ss=start_time, t=segment_duration)
                            .output(output_path, vcodec='libx264', acodec='aac')
                            .overwrite_output()
                            .run(quiet=True)
                        )
                        segments_created += 1
                        print(f"✓ 完成: {output_filename}")
                    except Exception as e:
                        print(f"✗ 切分失败 {output_filename}: {e}")
                
                if segments_created > 0:
                    total_segments += segments_created
                    processed_videos += 1
                
            except Exception as e:
                print(f"✗ 处理视频失败: {os.path.basename(video_file)} - {e}")
        
        summary = f"""智能音频时长切分完成！
{strategy_info}
输出文件夹: {output_folder}
处理视频: {processed_videos}/{len(video_files)} 个
总片段数: {total_segments}
每段时长: {calculated_duration:.2f}秒"""
        
        return io.NodeOutput(output_folder, total_segments, calculated_duration, summary)


class VideoNormalizer(io.ComfyNode):
    """视频标准化器 - 统一视频格式为TikTok标准（720x1280）"""
    
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="VideoNormalizer",
            display_name="视频标准化器",
            category="batch_video",
            description="将视频标准化为TikTok格式：720x1280分辨率，30fps，统一编码参数",
            inputs=[
                io.String.Input("input_folder", tooltip="输入视频文件夹路径"),
                io.Int.Input("target_width", default=720, tooltip="目标宽度"),
                io.Int.Input("target_height", default=1280, tooltip="目标高度"),
                io.Int.Input("target_fps", default=30, tooltip="目标帧率"),
                io.String.Input("output_prefix", default="标准化", tooltip="输出文件名前缀"),
                io.Bool.Input("keep_aspect_ratio", default=True, tooltip="保持宽高比（添加黑边）"),
            ],
            outputs=[
                io.String.Output("output_folder", display_name="输出文件夹"),
                io.Int.Output("processed_count", display_name="处理数量"),
                io.String.Output("summary", display_name="处理摘要"),
            ],
        )
    
    @classmethod
    def execute(cls, input_folder, target_width=720, target_height=1280, target_fps=30, 
                output_prefix="标准化", keep_aspect_ratio=True):
        import os
        import tempfile
        from pathlib import Path
        from .utils import scan_media_files
        import ffmpeg
        import time
        
        try:
            # 验证输入文件夹
            if not os.path.exists(input_folder):
                raise ValueError(f"输入文件夹不存在: {input_folder}")
            
            # 扫描视频文件
            media_files = scan_media_files(input_folder, file_types=['video'])
            video_files = media_files.get('video', [])
            if not video_files:
                raise ValueError(f"在文件夹中未找到视频文件: {input_folder}")
            
            # 创建输出文件夹
            timestamp = int(time.time())
            output_folder = os.path.join(folder_paths.get_temp_directory(), f"{output_prefix}_视频标准化_{timestamp}")
            os.makedirs(output_folder, exist_ok=True)
            
            processed_count = 0
            failed_files = []
            
            print(f"[视频标准化器] 开始处理 {len(video_files)} 个视频文件")
            print(f"[视频标准化器] 目标格式: {target_width}x{target_height}@{target_fps}fps")
            
            for video_file in video_files:
                try:
                    video_name = Path(video_file).stem
                    output_filename = f"{video_name}_标准化.mp4"
                    output_path = os.path.join(output_folder, output_filename)
                    
                    # 获取原视频信息
                    probe = ffmpeg.probe(video_file)
                    video_stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
                    original_width = int(video_stream['width'])
                    original_height = int(video_stream['height'])
                    
                    print(f"[视频标准化器] 处理: {video_name} ({original_width}x{original_height})")
                    
                    # 创建输入流
                    input_stream = ffmpeg.input(video_file)
                    
                    if keep_aspect_ratio:
                        # 保持宽高比，添加黑边
                        video_filter = input_stream.video.filter('scale', f'{target_width}:{target_height}:force_original_aspect_ratio=decrease').filter('pad', target_width, target_height, '(ow-iw)/2', '(oh-ih)/2')
                    else:
                        # 拉伸到目标尺寸
                        video_filter = input_stream.video.filter('scale', target_width, target_height)
                    
                    # 设置帧率
                    video_filter = video_filter.filter('fps', fps=target_fps)
                    
                    # 音频处理
                    audio_filter = input_stream.audio
                    
                    # 输出视频
                    (
                        ffmpeg
                        .output(
                            video_filter,
                            audio_filter,
                            output_path,
                            vcodec='libx264',
                            preset='fast',
                            **{'profile:v': 'main'},
                            acodec='aac',
                            ar=44100,
                            ac=2,
                            **{'b:v': '2000k', 'maxrate': '2500k', 'bufsize': '5000k'}  # 视频比特率控制
                        )
                        .overwrite_output()
                        .run(quiet=True)
                    )
                    
                    # 验证输出文件
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        processed_count += 1
                        print(f"[视频标准化器] 完成: {output_filename}")
                    else:
                        failed_files.append(video_name)
                        print(f"[视频标准化器] 失败: {video_name} (输出文件无效)")
                        
                except Exception as e:
                    failed_files.append(video_name)
                    print(f"[视频标准化器] 处理失败: {video_name}, 错误: {str(e)}")
            
            # 生成摘要
            summary = f"视频标准化完成: 成功 {processed_count}/{len(video_files)} 个文件"
            if failed_files:
                summary += f", 失败: {len(failed_files)} 个文件"
            
            print(f"[视频标准化器] {summary}")
            
            return io.NodeOutput(output_folder, processed_count, summary)
            
        except Exception as e:
            error_msg = f"视频标准化器执行失败: {str(e)}"
            print(f"[视频标准化器] 错误: {error_msg}")
            # 返回空结果但不抛出异常，让工作流继续
            return io.NodeOutput("", 0, error_msg)


class SmartAudioMixer(io.ComfyNode):
    """智能音频合成器 - 随机选择音频并与视频音频混合"""
    
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="SmartAudioMixer",
            display_name="智能音频合成器",
            category="batch_video",
            description="随机选择音频文件，智能与视频音频混合，支持音量控制",
            inputs=[
                io.String.Input("video_folder", tooltip="视频文件夹路径"),
                io.String.Input("audio_folder", tooltip="音频文件夹路径"),
                io.Bool.Input("mute_original", default=False, tooltip="是否静音原视频音频"),
                io.Float.Input("original_volume", default=50.0, tooltip="原视频音量 (0-100)"),
                io.Float.Input("background_volume", default=80.0, tooltip="背景音频音量 (0-100)"),
                io.String.Input("output_prefix", default="音频合成", tooltip="输出文件名前缀"),
            ],
            outputs=[
                io.String.Output("output_folder", display_name="输出文件夹"),
                io.Int.Output("processed_count", display_name="处理数量"),
                io.String.Output("summary", display_name="处理摘要"),
            ],
        )
    
    @classmethod
    def execute(cls, video_folder, audio_folder, mute_original=False, original_volume=50.0, 
                background_volume=80.0, output_prefix="音频合成"):
        import os
        import random
        import time
        from pathlib import Path
        from .utils import scan_media_files
        import ffmpeg
        
        try:
            # 验证输入文件夹
            if not os.path.exists(video_folder):
                raise ValueError(f"视频文件夹不存在: {video_folder}")
            if not os.path.exists(audio_folder):
                raise ValueError(f"音频文件夹不存在: {audio_folder}")
            
            # 扫描文件
            video_files = scan_media_files(video_folder, file_types=['video']).get('video', [])
            audio_files = scan_media_files(audio_folder, file_types=['audio']).get('audio', [])
            
            if not video_files:
                raise ValueError(f"在文件夹中未找到视频文件: {video_folder}")
            if not audio_files:
                raise ValueError(f"在文件夹中未找到音频文件: {audio_folder}")
            
            # 创建输出文件夹
            timestamp = int(time.time())
            output_folder = os.path.join(folder_paths.get_temp_directory(), f"{output_prefix}_音频合成_{timestamp}")
            os.makedirs(output_folder, exist_ok=True)
            
            processed_count = 0
            failed_files = []
            
            print(f"[智能音频合成器] 开始处理 {len(video_files)} 个视频文件")
            print(f"[智能音频合成器] 可用音频: {len(audio_files)} 个")
            print(f"[智能音频合成器] 音量设置: 原视频={original_volume}%, 背景音频={background_volume}%")
            
            for video_file in video_files:
                try:
                    video_name = Path(video_file).stem
                    output_filename = f"{video_name}_音频合成.mp4"
                    output_path = os.path.join(output_folder, output_filename)
                    
                    # 随机选择一个音频文件
                    selected_audio = random.choice(audio_files)
                    audio_name = Path(selected_audio).name
                    
                    print(f"[智能音频合成器] 处理: {video_name} + {audio_name}")
                    
                    # 获取视频时长
                    video_probe = ffmpeg.probe(video_file)
                    video_duration = float(video_probe['streams'][0]['duration'])
                    
                    # 创建输入流
                    video_input = ffmpeg.input(video_file)
                    audio_input = ffmpeg.input(selected_audio)
                    
                    # 处理音频：循环播放背景音频以匹配视频长度
                    background_audio = audio_input.audio.filter('aloop', loop=-1, size=2**31-1).filter('atrim', duration=video_duration)
                    
                    if mute_original:
                        # 只使用背景音频
                        mixed_audio = background_audio.filter('volume', background_volume/100.0)
                    else:
                        # 混合原视频音频和背景音频
                        original_audio = video_input.audio.filter('volume', original_volume/100.0)
                        background_audio = background_audio.filter('volume', background_volume/100.0)
                        mixed_audio = ffmpeg.filter([original_audio, background_audio], 'amix', inputs=2, duration='longest')
                    
                    # 输出视频
                    (
                        ffmpeg
                        .output(
                            video_input.video,
                            mixed_audio,
                            output_path,
                            vcodec='libx264',
                            acodec='aac',
                            preset='fast',
                            ar=44100,
                            ac=2
                        )
                        .overwrite_output()
                        .run(quiet=True)
                    )
                    
                    # 验证输出文件
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        processed_count += 1
                        print(f"[智能音频合成器] 完成: {output_filename}")
                    else:
                        failed_files.append(video_name)
                        print(f"[智能音频合成器] 失败: {video_name} (输出文件无效)")
                        
                except Exception as e:
                    failed_files.append(video_name)
                    print(f"[智能音频合成器] 处理失败: {video_name}, 错误: {str(e)}")
            
            # 生成摘要
            summary = f"音频合成完成: 成功 {processed_count}/{len(video_files)} 个文件"
            if failed_files:
                summary += f", 失败: {len(failed_files)} 个文件"
            
            print(f"[智能音频合成器] {summary}")
            
            return io.NodeOutput(output_folder, processed_count, summary)
            
        except Exception as e:
            error_msg = f"智能音频合成器执行失败: {str(e)}"
            print(f"[智能音频合成器] 错误: {error_msg}")
            return io.NodeOutput("", 0, error_msg)


class BatchSubtitleGenerator(io.ComfyNode):
    """批量字幕生成器 - 支持预设字幕和AI生成字幕"""
    
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="BatchSubtitleGenerator",
            display_name="批量字幕生成器",
            category="batch_video",
            description="为视频批量添加字幕，支持预设字幕文件和AI生成字幕",
            inputs=[
                io.String.Input("video_folder", tooltip="视频文件夹路径"),
                io.String.Input("subtitle_folder", optional=True, tooltip="预设字幕文件夹路径（可选）"),
                io.Bool.Input("enable_ai_subtitles", default=False, tooltip="启用AI字幕生成"),
                io.String.Input("subtitle_style", default="default", tooltip="字幕样式"),
                io.Int.Input("font_size", default=24, tooltip="字体大小"),
                io.String.Input("font_color", default="white", tooltip="字体颜色"),
                io.String.Input("outline_color", default="black", tooltip="描边颜色"),
                io.Int.Input("outline_width", default=2, tooltip="描边宽度"),
                io.String.Input("output_prefix", default="字幕版", tooltip="输出文件名前缀"),
            ],
            outputs=[
                io.String.Output("output_folder", display_name="输出文件夹"),
                io.Int.Output("processed_count", display_name="处理数量"),
                io.String.Output("summary", display_name="处理摘要"),
            ],
        )
    
    @classmethod
    def execute(cls, video_folder, subtitle_folder=None, enable_ai_subtitles=False, 
                subtitle_style="default", font_size=24, font_color="white", 
                outline_color="black", outline_width=2, output_prefix="字幕版"):
        import os
        import random
        import time
        from pathlib import Path
        from .utils import scan_media_files
        import ffmpeg
        
        try:
            # 验证输入文件夹
            if not os.path.exists(video_folder):
                raise ValueError(f"视频文件夹不存在: {video_folder}")
            
            # 扫描视频文件
            video_files = scan_media_files(video_folder, file_types=['video']).get('video', [])
            if not video_files:
                raise ValueError(f"在文件夹中未找到视频文件: {video_folder}")
            
            # 扫描字幕文件
            subtitle_files = []
            if subtitle_folder and os.path.exists(subtitle_folder):
                # 支持的字幕格式
                subtitle_extensions = ['.srt', '.ass', '.vtt', '.sub']
                for ext in subtitle_extensions:
                    pattern = os.path.join(subtitle_folder, f"*{ext}")
                    import glob
                    subtitle_files.extend(glob.glob(pattern))
                    subtitle_files.extend(glob.glob(pattern.upper()))
                print(f"[批量字幕生成器] 找到 {len(subtitle_files)} 个预设字幕文件")
            
            # 创建输出文件夹
            timestamp = int(time.time())
            output_folder = os.path.join(folder_paths.get_temp_directory(), f"{output_prefix}_字幕生成_{timestamp}")
            os.makedirs(output_folder, exist_ok=True)
            
            processed_count = 0
            failed_files = []
            
            print(f"[批量字幕生成器] 开始处理 {len(video_files)} 个视频文件")
            print(f"[批量字幕生成器] AI字幕: {'启用' if enable_ai_subtitles else '禁用'}")
            print(f"[批量字幕生成器] 字幕样式: {font_size}px {font_color} 描边{outline_color}")
            
            for video_file in video_files:
                try:
                    video_name = Path(video_file).stem
                    output_filename = f"{video_name}_{output_prefix}.mp4"
                    output_path = os.path.join(output_folder, output_filename)
                    
                    print(f"[批量字幕生成器] 处理: {video_name}")
                    
                    # 创建输入流
                    video_input = ffmpeg.input(video_file)
                    
                    # 选择字幕方式
                    subtitle_applied = False
                    
                    # 优先使用预设字幕文件
                    if subtitle_files:
                        selected_subtitle = random.choice(subtitle_files)
                        subtitle_name = Path(selected_subtitle).name
                        print(f"[批量字幕生成器] 使用预设字幕: {subtitle_name}")
                        
                        try:
                            # 使用字幕文件
                            (
                                ffmpeg
                                .output(
                                    video_input,
                                    output_path,
                                    vf=f"subtitles={selected_subtitle}:force_style='FontSize={font_size},PrimaryColour=&H{cls._color_to_hex(font_color)},OutlineColour=&H{cls._color_to_hex(outline_color)},Outline={outline_width}'",
                                    vcodec='libx264',
                                    acodec='aac',
                                    preset='fast'
                                )
                                .overwrite_output()
                                .run(quiet=True)
                            )
                            subtitle_applied = True
                        except Exception as subtitle_error:
                            print(f"[批量字幕生成器] 预设字幕失败: {str(subtitle_error)}")
                    
                    # 如果预设字幕失败或未启用，尝试AI字幕
                    if not subtitle_applied and enable_ai_subtitles:
                        print(f"[批量字幕生成器] 尝试AI字幕生成")
                        try:
                            ai_subtitle_path = cls._generate_ai_subtitles(video_file, output_folder)
                            if ai_subtitle_path:
                                (
                                    ffmpeg
                                    .output(
                                        video_input,
                                        output_path,
                                        vf=f"subtitles={ai_subtitle_path}:force_style='FontSize={font_size},PrimaryColour=&H{cls._color_to_hex(font_color)},OutlineColour=&H{cls._color_to_hex(outline_color)},Outline={outline_width}'",
                                        vcodec='libx264',
                                        acodec='aac',
                                        preset='fast'
                                    )
                                    .overwrite_output()
                                    .run(quiet=True)
                                )
                                subtitle_applied = True
                                print(f"[批量字幕生成器] AI字幕生成成功")
                            else:
                                print(f"[批量字幕生成器] AI字幕生成失败")
                        except Exception as ai_error:
                            print(f"[批量字幕生成器] AI字幕失败: {str(ai_error)}")
                    
                    # 如果都失败了，直接复制视频
                    if not subtitle_applied:
                        print(f"[批量字幕生成器] 无字幕，直接复制视频")
                        (
                            ffmpeg
                            .output(video_input, output_path, vcodec='libx264', acodec='aac', preset='fast')
                            .overwrite_output()
                            .run(quiet=True)
                        )
                    
                    # 验证输出文件
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        processed_count += 1
                        print(f"[批量字幕生成器] 完成: {output_filename}")
                    else:
                        failed_files.append(video_name)
                        print(f"[批量字幕生成器] 失败: {video_name} (输出文件无效)")
                        
                except Exception as e:
                    failed_files.append(video_name)
                    print(f"[批量字幕生成器] 处理失败: {video_name}, 错误: {str(e)}")
            
            # 生成摘要
            summary = f"字幕生成完成: 成功 {processed_count}/{len(video_files)} 个文件"
            if failed_files:
                summary += f", 失败: {len(failed_files)} 个文件"
            
            print(f"[批量字幕生成器] {summary}")
            
            return io.NodeOutput(output_folder, processed_count, summary)
            
        except Exception as e:
            error_msg = f"批量字幕生成器执行失败: {str(e)}"
            print(f"[批量字幕生成器] 错误: {error_msg}")
            return io.NodeOutput("", 0, error_msg)
    
    @classmethod
    def _color_to_hex(cls, color_name):
        """将颜色名转换为FFmpeg字幕使用的十六进制格式"""
        color_map = {
            'white': 'FFFFFF',
            'black': '000000',
            'red': '0000FF',
            'green': '00FF00',
            'blue': 'FF0000',
            'yellow': '00FFFF',
            'cyan': 'FFFF00',
            'magenta': 'FF00FF',
        }
        return color_map.get(color_name.lower(), 'FFFFFF')
    
    @classmethod  
    def _generate_ai_subtitles(cls, video_file, temp_dir):
        """使用AI生成字幕文件（需要安装whisper或其他语音识别库）"""
        try:
            # 这里是AI字幕生成的占位实现
            # 实际使用时需要安装 openai-whisper 或其他语音识别库
            print(f"[批量字幕生成器] AI字幕生成功能需要安装whisper库")
            print(f"[批量字幕生成器] 可以运行: pip install openai-whisper")
            
            # 尝试导入whisper（如果已安装）
            try:
                import whisper
                
                # 提取音频
                audio_path = os.path.join(temp_dir, f"temp_audio_{int(time.time())}.wav")
                ffmpeg.input(video_file).output(audio_path, acodec='pcm_s16le', ar=16000).overwrite_output().run(quiet=True)
                
                # 使用whisper生成字幕
                model = whisper.load_model("base")
                result = model.transcribe(audio_path)
                
                # 生成SRT字幕文件
                subtitle_path = os.path.join(temp_dir, f"ai_subtitle_{int(time.time())}.srt")
                with open(subtitle_path, 'w', encoding='utf-8') as f:
                    for i, segment in enumerate(result['segments']):
                        start_time = cls._format_timestamp(segment['start'])
                        end_time = cls._format_timestamp(segment['end'])
                        text = segment['text'].strip()
                        
                        f.write(f"{i+1}\n")
                        f.write(f"{start_time} --> {end_time}\n")
                        f.write(f"{text}\n\n")
                
                # 清理临时音频文件
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                
                return subtitle_path
                
            except ImportError:
                print(f"[批量字幕生成器] whisper库未安装，跳过AI字幕生成")
                return None
                
        except Exception as e:
            print(f"[批量字幕生成器] AI字幕生成失败: {str(e)}")
            return None
    
    @classmethod
    def _format_timestamp(cls, seconds):
        """将秒数转换为SRT时间戳格式"""
        import time
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"


class BatchLLMGenerator(io.ComfyNode):
    """批量文案生成器 - 基于LLM批量生成文案内容"""
    
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="BatchLLMGenerator", 
            display_name="批量文案生成器",
            category="batch_video",
            description="基于LLM批量生成文案",
            inputs=[
                # LLM配置
                io.String.Input("model", default="gpt-3.5-turbo", tooltip="模型名称"),
                io.String.Input("api_key", optional=True, tooltip="API密钥"),
                io.String.Input("base_url", optional=True, tooltip="API地址"),
                
                # 批量生成配置  
                io.String.Input("prompt_template", multiline=True,
                               default="为{topic}写一段解说词，要求生动有趣，朗读时间15-25秒",
                               tooltip="文案模板，用{topic}占位"),
                io.String.Input("topics", multiline=True,
                               tooltip="主题列表，每行一个"),
                io.Float.Input("temperature", default=0.7, tooltip="创作随机性 (0-1)"),
                io.Int.Input("max_length", default=500, tooltip="最大文案长度"),
                
                io.String.Input("output_prefix", default="批量文案", tooltip="输出前缀"),
            ],
            outputs=[
                io.String.Output("content_folder", display_name="文案文件夹"),
                io.Int.Output("generated_count", display_name="生成数量"),
                io.String.Output("summary", display_name="生成摘要"),
            ],
        )
    
    @classmethod
    def execute(cls, model="gpt-3.5-turbo", api_key=None, base_url=None, 
                prompt_template="为{topic}写一段解说词", topics="", temperature=0.7, max_length=500,
                output_prefix="批量文案"):
        import os
        import time
        import json
        import openai
        from pathlib import Path
        
        try:
            # 解析主题列表
            topic_list = [t.strip() for t in topics.split('\n') if t.strip()]
            if not topic_list:
                raise ValueError("主题列表不能为空")
            
            # 配置OpenAI客户端
            if api_key:
                client_api_key = api_key
            else:
                # 尝试从环境变量获取
                import os
                client_api_key = os.environ.get("OPENAI_API_KEY")
                if not client_api_key:
                    raise ValueError("未提供API密钥")
            
            if base_url:
                client_base_url = base_url if base_url.endswith('/') else base_url + '/'
            else:
                client_base_url = "https://api.openai.com/v1/"
            
            # 创建OpenAI客户端
            from openai import OpenAI
            client = OpenAI(
                api_key=client_api_key,
                base_url=client_base_url
            )
            
            # 创建输出文件夹
            timestamp = int(time.time())
            output_folder = os.path.join(folder_paths.get_temp_directory(), f"{output_prefix}_{timestamp}")
            os.makedirs(output_folder, exist_ok=True)
            
            generated_count = 0
            failed_topics = []
            content_list = []
            
            print(f"[批量文案生成器] 开始生成 {len(topic_list)} 个文案")
            
            # 批量生成文案
            for i, topic in enumerate(topic_list):
                try:
                    # 构建完整的prompt
                    full_prompt = prompt_template.format(topic=topic)
                    
                    print(f"[批量文案生成器] 生成文案 {i+1}/{len(topic_list)}: {topic}")
                    
                    # 调用LLM API
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": "你是一个专业的文案创作者，擅长创作生动有趣的视频解说词。"},
                            {"role": "user", "content": full_prompt}
                        ],
                        temperature=temperature,
                        max_tokens=max_length,
                        timeout=30
                    )
                    
                    content = response.choices[0].message.content.strip()
                    
                    # 保存文案到文件
                    content_filename = f"content_{i+1:03d}.txt"
                    content_path = os.path.join(output_folder, content_filename)
                    
                    with open(content_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    # 保存到内容列表
                    content_data = {
                        'index': i + 1,
                        'topic': topic,
                        'content': content,
                        'filename': content_filename,
                        'length': len(content)
                    }
                    content_list.append(content_data)
                    
                    generated_count += 1
                    print(f"[批量文案生成器] ✓ 完成: {topic} ({len(content)}字)")
                    
                    # 避免API限制，添加小延迟
                    time.sleep(0.5)
                    
                except Exception as e:
                    failed_topics.append(f"{topic}: {str(e)}")
                    print(f"[批量文案生成器] ✗ 失败: {topic} - {str(e)}")
            
            # 保存内容索引文件
            index_file = os.path.join(output_folder, "content_index.json")
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'generated_time': timestamp,
                    'total_count': len(topic_list),
                    'success_count': generated_count,
                    'failed_count': len(failed_topics),
                    'model_info': {
                        'model': model,
                        'temperature': temperature,
                        'max_length': max_length
                    },
                    'contents': content_list,
                    'failed_topics': failed_topics
                }, f, indent=2, ensure_ascii=False)
            
            # 生成摘要
            summary = f"文案生成完成: 成功 {generated_count}/{len(topic_list)} 个"
            if failed_topics:
                summary += f", 失败 {len(failed_topics)} 个"
            
            total_chars = sum(len(content['content']) for content in content_list)
            avg_chars = total_chars // generated_count if generated_count > 0 else 0
            summary += f", 平均长度 {avg_chars} 字"
            
            print(f"[批量文案生成器] {summary}")
            
            return io.NodeOutput(output_folder, generated_count, summary)
            
        except Exception as e:
            error_msg = f"批量文案生成器执行失败: {str(e)}"
            print(f"[批量文案生成器] 错误: {error_msg}")
            return io.NodeOutput("", 0, error_msg)


class BatchTTSGenerator(io.ComfyNode):
    """批量TTS生成器 - 批量TTS语音合成"""
    
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="BatchTTSGenerator",
            display_name="批量TTS生成器", 
            category="batch_video",
            description="批量TTS语音合成",
            inputs=[
                # 内容输入
                io.String.Input("content_folder", tooltip="文案文件夹路径"),
                
                # TTS引擎选择
                io.Combo.Input("tts_engine", 
                               options=["IndexTTS", "OpenAI-TTS"], 
                               default="OpenAI-TTS", tooltip="TTS引擎"),
                
                # IndexTTS配置
                io.String.Input("speaker_audio", optional=True, tooltip="说话人音频文件路径(IndexTTS)"),
                io.Float.Input("temperature", default=0.8, tooltip="随机性(IndexTTS)"),
                io.Int.Input("max_mel_tokens", default=1500, tooltip="最大长度(IndexTTS)"),
                io.Bool.Input("enable_emotion", default=False, tooltip="启用情绪控制(IndexTTS)"),
                io.String.Input("emotion_text", default="", tooltip="情绪提示词(IndexTTS)"),
                
                # OpenAI TTS配置
                io.String.Input("openai_voice", default="alloy", tooltip="OpenAI语音"),
                io.String.Input("openai_model", default="tts-1", tooltip="OpenAI模型"),
                io.String.Input("openai_api_key", optional=True, tooltip="OpenAI API密钥"),
                io.String.Input("openai_base_url", optional=True, tooltip="OpenAI API地址"),
                
                io.String.Input("output_prefix", default="批量TTS", tooltip="输出前缀"),
            ],
            outputs=[
                io.String.Output("audio_folder", display_name="音频文件夹"),
                io.Int.Output("generated_count", display_name="生成数量"),
                io.String.Output("summary", display_name="TTS摘要"),
            ],
        )
    
    @classmethod
    def execute(cls, content_folder, tts_engine="OpenAI-TTS", 
                speaker_audio=None, temperature=0.8, max_mel_tokens=1500, 
                enable_emotion=False, emotion_text="",
                openai_voice="alloy", openai_model="tts-1", 
                openai_api_key=None, openai_base_url=None,
                output_prefix="批量TTS"):
        import os
        import time
        import json
        from pathlib import Path
        
        try:
            # 验证内容文件夹
            if not os.path.exists(content_folder):
                raise ValueError(f"文案文件夹不存在: {content_folder}")
            
            # 读取文案文件
            content_files = []
            for file in os.listdir(content_folder):
                if file.endswith('.txt') and file.startswith('content_'):
                    content_files.append(os.path.join(content_folder, file))
            
            if not content_files:
                raise ValueError(f"在文件夹中未找到文案文件: {content_folder}")
            
            # 按文件名排序确保顺序
            content_files.sort()
            
            # 读取内容索引文件（如果存在）
            content_data_list = []
            index_file = os.path.join(content_folder, "content_index.json")
            if os.path.exists(index_file):
                with open(index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                    content_data_list = index_data.get('contents', [])
            
            # 创建输出文件夹
            timestamp = int(time.time())
            output_folder = os.path.join(folder_paths.get_temp_directory(), f"{output_prefix}_{timestamp}")
            os.makedirs(output_folder, exist_ok=True)
            
            generated_count = 0
            failed_files = []
            audio_info_list = []
            
            print(f"[批量TTS生成器] 开始处理 {len(content_files)} 个文案文件")
            print(f"[批量TTS生成器] 使用TTS引擎: {tts_engine}")
            
            # 批量生成语音
            for i, content_file in enumerate(content_files):
                try:
                    # 读取文案内容
                    with open(content_file, 'r', encoding='utf-8') as f:
                        content_text = f.read().strip()
                    
                    if not content_text:
                        print(f"[批量TTS生成器] ⚠️ 跳过空文案: {os.path.basename(content_file)}")
                        continue
                    
                    # 获取对应的内容数据
                    content_data = None
                    if i < len(content_data_list):
                        content_data = content_data_list[i]
                    
                    file_basename = Path(content_file).stem
                    audio_filename = f"tts_{i+1:03d}.wav"
                    audio_path = os.path.join(output_folder, audio_filename)
                    
                    print(f"[批量TTS生成器] 生成语音 {i+1}/{len(content_files)}: {file_basename}")
                    
                    # 根据选择的引擎生成语音
                    if tts_engine == "IndexTTS":
                        success = cls._generate_indexts_audio(
                            content_text, audio_path, speaker_audio, 
                            temperature, max_mel_tokens, enable_emotion, emotion_text
                        )
                    else:  # OpenAI-TTS
                        success = cls._generate_openai_tts_audio(
                            content_text, audio_path, openai_voice, openai_model,
                            openai_api_key, openai_base_url
                        )
                    
                    if success:
                        # 获取音频时长
                        audio_duration = cls._get_audio_duration(audio_path)
                        
                        audio_info = {
                            'index': i + 1,
                            'content_file': os.path.basename(content_file),
                            'audio_file': audio_filename,
                            'content_length': len(content_text),
                            'audio_duration': audio_duration,
                            'content_data': content_data
                        }
                        audio_info_list.append(audio_info)
                        
                        generated_count += 1
                        print(f"[批量TTS生成器] ✓ 完成: {audio_filename} ({audio_duration:.1f}s)")
                    else:
                        failed_files.append(os.path.basename(content_file))
                        print(f"[批量TTS生成器] ✗ 失败: {file_basename}")
                        
                except Exception as e:
                    failed_files.append(os.path.basename(content_file))
                    print(f"[批量TTS生成器] ✗ 处理失败: {os.path.basename(content_file)} - {str(e)}")
            
            # 保存音频索引文件
            audio_index_file = os.path.join(output_folder, "audio_index.json")
            with open(audio_index_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'generated_time': timestamp,
                    'tts_engine': tts_engine,
                    'total_count': len(content_files),
                    'success_count': generated_count,
                    'failed_count': len(failed_files),
                    'engine_config': {
                        'tts_engine': tts_engine,
                        'openai_voice': openai_voice if tts_engine == "OpenAI-TTS" else None,
                        'speaker_audio': speaker_audio if tts_engine == "IndexTTS" else None
                    },
                    'audio_info': audio_info_list,
                    'failed_files': failed_files
                }, f, indent=2, ensure_ascii=False)
            
            # 生成摘要
            summary = f"TTS生成完成: 成功 {generated_count}/{len(content_files)} 个"
            if failed_files:
                summary += f", 失败 {len(failed_files)} 个"
            
            if audio_info_list:
                avg_duration = sum(info['audio_duration'] for info in audio_info_list) / len(audio_info_list)
                summary += f", 平均时长 {avg_duration:.1f}s"
            
            print(f"[批量TTS生成器] {summary}")
            
            return io.NodeOutput(output_folder, generated_count, summary)
            
        except Exception as e:
            error_msg = f"批量TTS生成器执行失败: {str(e)}"
            print(f"[批量TTS生成器] 错误: {error_msg}")
            return io.NodeOutput("", 0, error_msg)
    
    @classmethod
    def _generate_indexts_audio(cls, text, output_path, speaker_audio, temperature, max_mel_tokens, enable_emotion, emotion_text):
        """使用IndexTTS生成音频"""
        try:
            # 这里需要调用IndexTTS的接口
            # 由于IndexTTS可能没有安装，先返回False表示不支持
            print(f"[批量TTS生成器] IndexTTS暂未集成，请使用OpenAI-TTS")
            return False
        except Exception as e:
            print(f"[批量TTS生成器] IndexTTS生成失败: {str(e)}")
            return False
    
    @classmethod
    def _generate_openai_tts_audio(cls, text, output_path, voice, model, api_key, base_url):
        """使用OpenAI TTS生成音频"""
        try:
            import torchaudio
            from openai import OpenAI
            
            # 配置API
            if api_key:
                client_api_key = api_key
            else:
                import os
                client_api_key = os.environ.get("OPENAI_API_KEY")
                if not client_api_key:
                    raise ValueError("未提供OpenAI API密钥")
            
            if base_url:
                client_base_url = base_url if base_url.endswith('/') else base_url + '/'
            else:
                client_base_url = "https://api.openai.com/v1/"
            
            # 创建OpenAI客户端
            client = OpenAI(
                api_key=client_api_key,
                base_url=client_base_url
            )
            
            # 调用TTS API
            response = client.audio.speech.create(
                model=model,
                voice=voice,
                input=text
            )
            
            # 保存音频文件
            with open(output_path, "wb") as f:
                f.write(response.content)
            
            return os.path.exists(output_path) and os.path.getsize(output_path) > 0
            
        except Exception as e:
            print(f"[批量TTS生成器] OpenAI TTS生成失败: {str(e)}")
            return False
    
    @classmethod
    def _get_audio_duration(cls, audio_path):
        """获取音频文件时长"""
        try:
            import torchaudio
            waveform, sample_rate = torchaudio.load(audio_path)
            duration = waveform.shape[1] / sample_rate
            return float(duration)
        except Exception as e:
            print(f"[批量TTS生成器] 获取音频时长失败: {str(e)}")
            return 0.0


class SmartVideoCutterWithAudio(io.ComfyNode):
    """智能视频裁切器带音频融合 - 一对一处理确保不混乱"""
    
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="SmartVideoCutterWithAudio",
            display_name="智能视频裁切+音频融合器",
            category="batch_video", 
            description="按音频时长裁切视频并直接融合音频，确保一一对应",
            inputs=[
                # 输入源
                io.String.Input("video_folder", tooltip="视频文件夹路径"),
                io.String.Input("audio_folder", tooltip="TTS音频文件夹路径"),
                
                # 裁切策略
                io.Combo.Input("video_selection", 
                               options=["顺序循环", "随机选择", "按名称匹配"], 
                               default="顺序循环", tooltip="视频选择策略"),
                io.Bool.Input("skip_short_videos", default=True, tooltip="跳过过短视频"),
                io.Float.Input("min_video_duration", default=10.0, tooltip="最小视频时长要求"),
                
                # 音频融合配置
                io.Bool.Input("enable_audio_mix", default=True, tooltip="启用音频融合"),
                io.Float.Input("tts_volume", default=90.0, tooltip="TTS音量 (0-100)"),
                io.Float.Input("original_volume", default=20.0, tooltip="原视频音量 (0-100)"),
                io.Float.Input("bg_music_volume", default=30.0, tooltip="背景音乐音量 (0-100)"),
                io.String.Input("bg_music_folder", optional=True, tooltip="背景音乐文件夹(可选)"),
                
                io.String.Input("output_prefix", default="智能裁切", tooltip="输出前缀"),
            ],
            outputs=[
                io.String.Output("output_folder", display_name="输出文件夹"),
                io.Int.Output("processed_count", display_name="处理数量"),
                io.String.Output("pairing_info", display_name="配对信息"),
                io.String.Output("summary", display_name="处理摘要"),
            ],
        )
    
    @classmethod
    def execute(cls, video_folder, audio_folder, video_selection="顺序循环", 
                skip_short_videos=True, min_video_duration=10.0,
                enable_audio_mix=True, tts_volume=90.0, original_volume=20.0, 
                bg_music_volume=30.0, bg_music_folder=None, output_prefix="智能裁切"):
        import os
        import time
        import json
        import random
        from pathlib import Path
        from .utils import scan_media_files
        import ffmpeg
        
        try:
            # 1. 验证输入文件夹
            if not os.path.exists(video_folder):
                raise ValueError(f"视频文件夹不存在: {video_folder}")
            if not os.path.exists(audio_folder):
                raise ValueError(f"音频文件夹不存在: {audio_folder}")
            
            # 2. 扫描音频和视频文件
            audio_files = scan_media_files(audio_folder, ['audio'])['audio']
            video_files = scan_media_files(video_folder, ['video'])['video']
            bg_music_files = []
            if bg_music_folder and os.path.exists(bg_music_folder):
                bg_music_files = scan_media_files(bg_music_folder, ['audio'])['audio']
            
            if not audio_files:
                raise ValueError(f"未找到音频文件: {audio_folder}")
            if not video_files:
                raise ValueError(f"未找到视频文件: {video_folder}")
            
            # 按文件名排序，确保TTS音频的顺序
            audio_files.sort(key=lambda x: os.path.basename(x))
            
            print(f"[智能视频裁切+音频融合器] 找到 {len(audio_files)} 个音频文件")
            print(f"[智能视频裁切+音频融合器] 找到 {len(video_files)} 个视频文件")
            if bg_music_files:
                print(f"[智能视频裁切+音频融合器] 找到 {len(bg_music_files)} 个背景音乐")
            
            # 3. 建立视频-音频配对关系
            video_audio_pairs = cls._create_video_audio_pairs(
                video_files, audio_files, video_selection
            )
            
            # 创建输出文件夹
            timestamp = int(time.time())
            output_folder = os.path.join(folder_paths.get_temp_directory(), f"{output_prefix}_{timestamp}")
            os.makedirs(output_folder, exist_ok=True)
            
            processed_count = 0
            failed_count = 0
            pairing_info_list = []
            
            print(f"[智能视频裁切+音频融合器] 开始处理 {len(video_audio_pairs)} 个配对")
            
            # 4. 逐个处理每个配对
            for i, (video_file, audio_file) in enumerate(video_audio_pairs):
                try:
                    # 获取音频时长作为裁切时长
                    audio_duration = cls._get_audio_duration(audio_file)
                    video_duration = cls._get_video_duration(video_file)
                    
                    audio_name = Path(audio_file).stem
                    video_name = Path(video_file).stem
                    
                    print(f"[智能视频裁切+音频融合器] 处理配对 {i+1}/{len(video_audio_pairs)}")
                    print(f"  音频: {os.path.basename(audio_file)} ({audio_duration:.1f}s)")
                    print(f"  视频: {os.path.basename(video_file)} ({video_duration:.1f}s)")
                    
                    # 检查视频是否够长
                    if skip_short_videos and video_duration < max(audio_duration, min_video_duration):
                        print(f"  ⚠️ 跳过过短视频: {video_name}")
                        continue
                    
                    # 生成输出文件名
                    output_filename = f"{output_prefix}_{audio_name}.mp4"
                    output_path = os.path.join(output_folder, output_filename)
                    
                    # 记录配对信息
                    pairing_info = {
                        'index': i + 1,
                        'audio_file': os.path.basename(audio_file),
                        'video_file': os.path.basename(video_file),
                        'audio_duration': audio_duration,
                        'video_duration': video_duration,
                        'output_file': output_filename
                    }
                    
                    # 5. 执行裁切+音频融合
                    success = cls._process_single_video_audio_pair(
                        video_file, audio_file, output_path, audio_duration,
                        enable_audio_mix, tts_volume, original_volume, bg_music_volume,
                        bg_music_files
                    )
                    
                    if success:
                        processed_count += 1
                        pairing_info['status'] = 'success'
                        print(f"  ✓ 完成: {output_filename}")
                    else:
                        failed_count += 1
                        pairing_info['status'] = 'failed'
                        print(f"  ✗ 失败: {output_filename}")
                    
                    pairing_info_list.append(pairing_info)
                        
                except Exception as e:
                    failed_count += 1
                    print(f"  ✗ 处理失败: {os.path.basename(audio_file)} - {str(e)}")
                    pairing_info_list.append({
                        'index': i + 1,
                        'audio_file': os.path.basename(audio_file),
                        'video_file': os.path.basename(video_file),
                        'status': 'error',
                        'error': str(e)
                    })
            
            # 保存配对信息文件
            pairing_file = os.path.join(output_folder, "pairing_info.json")
            with open(pairing_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'generated_time': timestamp,
                    'total_pairs': len(video_audio_pairs),
                    'success_count': processed_count,
                    'failed_count': failed_count,
                    'config': {
                        'video_selection': video_selection,
                        'enable_audio_mix': enable_audio_mix,
                        'tts_volume': tts_volume,
                        'original_volume': original_volume,
                        'bg_music_volume': bg_music_volume
                    },
                    'pairings': pairing_info_list
                }, f, indent=2, ensure_ascii=False)
            
            # 生成配对信息摘要
            pairing_summary = cls._format_pairing_summary(pairing_info_list[:5])  # 显示前5个
            summary = f"处理完成: 成功 {processed_count}/{len(video_audio_pairs)} 个视频"
            if failed_count > 0:
                summary += f", 失败 {failed_count} 个"
            
            print(f"[智能视频裁切+音频融合器] {summary}")
            
            return io.NodeOutput(output_folder, processed_count, pairing_summary, summary)
            
        except Exception as e:
            error_msg = f"智能视频裁切+音频融合器执行失败: {str(e)}"
            print(f"[智能视频裁切+音频融合器] 错误: {error_msg}")
            return io.NodeOutput("", 0, "", error_msg)
    
    @classmethod
    def _create_video_audio_pairs(cls, video_files, audio_files, selection_strategy):
        """创建视频-音频配对"""
        pairs = []
        
        if selection_strategy == "顺序循环":
            # 视频循环使用，每个音频对应一个视频
            for i, audio_file in enumerate(audio_files):
                video_file = video_files[i % len(video_files)]
                pairs.append((video_file, audio_file))
        
        elif selection_strategy == "随机选择":
            # 每个音频随机选择一个视频
            for audio_file in audio_files:
                video_file = random.choice(video_files)
                pairs.append((video_file, audio_file))
        
        elif selection_strategy == "按名称匹配":
            # 尝试按文件名匹配，匹配不上的用循环
            for i, audio_file in enumerate(audio_files):
                audio_name = Path(audio_file).stem
                matched_video = None
                
                # 寻找名称相似的视频
                for video_file in video_files:
                    video_name = Path(video_file).stem
                    if audio_name in video_name or video_name in audio_name:
                        matched_video = video_file
                        break
                
                # 没匹配上就用循环策略
                if not matched_video:
                    matched_video = video_files[i % len(video_files)]
                
                pairs.append((matched_video, audio_file))
        
        return pairs
    
    @classmethod
    def _process_single_video_audio_pair(cls, video_file, audio_file, output_path, duration,
                                       enable_audio_mix, tts_vol, orig_vol, bg_vol, bg_music_files):
        """处理单个视频-音频配对"""
        try:
            import ffmpeg
            
            # 创建视频输入流，按音频时长裁切
            video_input = ffmpeg.input(video_file, t=duration)
            
            if not enable_audio_mix:
                # 简单替换：只用TTS音频
                audio_input = ffmpeg.input(audio_file)
                (
                    ffmpeg
                    .output(video_input.video, audio_input.audio, output_path,
                           vcodec='libx264', acodec='aac', preset='fast')
                    .overwrite_output()
                    .run(quiet=True)
                )
            else:
                # 复杂混音：TTS + 原视频音频 + 背景音乐
                tts_input = ffmpeg.input(audio_file)
                
                # 调整TTS音量
                tts_audio = tts_input.audio.filter('volume', tts_vol/100.0)
                
                # 调整原视频音量
                orig_audio = video_input.audio.filter('volume', orig_vol/100.0)
                
                # 混合TTS和原音频
                mixed_audio = ffmpeg.filter([tts_audio, orig_audio], 'amix', inputs=2, duration='longest')
                
                # 如果有背景音乐，再混入
                if bg_music_files and bg_vol > 0:
                    bg_music = random.choice(bg_music_files)
                    bg_input = ffmpeg.input(bg_music, stream_loop=-1, t=duration)
                    bg_audio = bg_input.audio.filter('volume', bg_vol/100.0)
                    mixed_audio = ffmpeg.filter([mixed_audio, bg_audio], 'amix', inputs=2, duration='first')
                
                (
                    ffmpeg
                    .output(video_input.video, mixed_audio, output_path,
                           vcodec='libx264', acodec='aac', preset='fast')
                    .overwrite_output()
                    .run(quiet=True)
                )
            
            return os.path.exists(output_path) and os.path.getsize(output_path) > 0
            
        except Exception as e:
            print(f"[智能视频裁切+音频融合器] FFmpeg处理失败: {str(e)}")
            return False
    
    @classmethod
    def _get_audio_duration(cls, audio_path):
        """获取音频文件时长"""
        try:
            import ffmpeg
            probe = ffmpeg.probe(audio_path)
            duration = float(probe['streams'][0]['duration'])
            return duration
        except Exception as e:
            print(f"获取音频时长失败: {str(e)}")
            return 0.0
    
    @classmethod
    def _get_video_duration(cls, video_path):
        """获取视频文件时长"""
        try:
            import ffmpeg
            probe = ffmpeg.probe(video_path)
            duration = float(probe['streams'][0]['duration'])
            return duration
        except Exception as e:
            print(f"获取视频时长失败: {str(e)}")
            return 0.0
    
    @classmethod
    def _format_pairing_summary(cls, pairing_list):
        """格式化配对信息摘要"""
        if not pairing_list:
            return "无配对信息"
        
        summary_lines = ["配对信息 (前5个):"]
        for pair in pairing_list:
            status_icon = "✓" if pair.get('status') == 'success' else "✗"
            audio_name = pair.get('audio_file', 'unknown')
            video_name = pair.get('video_file', 'unknown')
            duration = pair.get('audio_duration', 0)
            summary_lines.append(f"{status_icon} {audio_name} + {video_name} ({duration:.1f}s)")
        
        return "\n".join(summary_lines)


class BatchVideoCropper(io.ComfyNode):
    """批量视频裁剪器 - 支持实时预览和智能裁剪"""
    
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="BatchVideoCropper",
            display_name="批量视频裁剪器",
            category="batch_video",
            description="批量裁剪视频，支持竖屏转横屏，提供实时预览功能",
            inputs=[
                io.String.Input("video_folder", tooltip="视频文件夹路径"),
                
                # 裁剪模式选择
                io.Combo.Input("crop_mode", 
                               options=["智能居中", "顶部对齐", "底部对齐", "左侧对齐", "右侧对齐", "自定义"], 
                               default="智能居中", 
                               tooltip="裁剪模式"),
                
                # 目标尺寸
                io.Int.Input("target_width", default=1920, tooltip="目标宽度"),
                io.Int.Input("target_height", default=1080, tooltip="目标高度"),
                
                # 自定义裁剪参数
                io.Float.Input("crop_x", default=0.0, tooltip="裁剪X起点（比例0-1）"),
                io.Float.Input("crop_y", default=0.0, tooltip="裁剪Y起点（比例0-1）"),
                io.Float.Input("crop_width", default=1.0, tooltip="裁剪宽度（比例0-1）"),
                io.Float.Input("crop_height", default=1.0, tooltip="裁剪高度（比例0-1）"),
                
                # 预览和处理选项
                io.Bool.Input("generate_preview", default=True, tooltip="生成预览图片"),
                io.String.Input("output_prefix", default="裁剪", tooltip="输出文件名前缀"),
            ],
            outputs=[
                io.String.Output("output_folder", display_name="输出文件夹"),
                io.String.Output("preview_image", display_name="预览图片路径"),
                io.Int.Output("processed_count", display_name="处理数量"),
                io.String.Output("crop_info", display_name="裁剪信息"),
                io.String.Output("summary", display_name="处理摘要"),
            ],
        )
    
    @classmethod
    def execute(cls, video_folder, crop_mode="智能居中", target_width=1920, target_height=1080,
                crop_x=0.0, crop_y=0.0, crop_width=1.0, crop_height=1.0,
                generate_preview=True, output_prefix="裁剪"):
        import os
        import time
        from pathlib import Path
        from .utils import scan_media_files
        import ffmpeg
        
        try:
            # 验证输入文件夹
            if not os.path.exists(video_folder):
                raise ValueError(f"视频文件夹不存在: {video_folder}")
            
            # 扫描视频文件
            video_files = scan_media_files(video_folder, file_types=['video']).get('video', [])
            if not video_files:
                raise ValueError(f"在文件夹中未找到视频文件: {video_folder}")
            
            # 创建输出文件夹
            timestamp = int(time.time())
            output_folder = os.path.join(folder_paths.get_temp_directory(), f"{output_prefix}_视频裁剪_{timestamp}")
            os.makedirs(output_folder, exist_ok=True)
            
            # 获取第一个视频的信息用于计算裁剪参数
            first_video = video_files[0]
            probe = ffmpeg.probe(first_video)
            video_stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            original_width = int(video_stream['width'])
            original_height = int(video_stream['height'])
            
            print(f"[批量视频裁剪器] 原始尺寸: {original_width}x{original_height}")
            print(f"[批量视频裁剪器] 目标尺寸: {target_width}x{target_height}")
            print(f"[批量视频裁剪器] 裁剪模式: {crop_mode}")
            
            # 计算裁剪参数
            if crop_mode == "自定义":
                final_crop_x = crop_x
                final_crop_y = crop_y
                final_crop_w = crop_width
                final_crop_h = crop_height
            else:
                final_crop_x, final_crop_y, final_crop_w, final_crop_h = cls._calculate_smart_crop(
                    original_width, original_height, target_width, target_height, crop_mode
                )
            
            # 转换为像素坐标
            crop_x_px = int(final_crop_x * original_width)
            crop_y_px = int(final_crop_y * original_height)
            crop_w_px = int(final_crop_w * original_width)
            crop_h_px = int(final_crop_h * original_height)
            
            crop_info = f"""裁剪参数:
起点: ({crop_x_px}, {crop_y_px})
尺寸: {crop_w_px}x{crop_h_px}
比例: {final_crop_x:.2f}, {final_crop_y:.2f}, {final_crop_w:.2f}, {final_crop_h:.2f}"""
            
            print(f"[批量视频裁剪器] {crop_info}")
            
            # 生成预览图（如果启用）
            preview_image_path = ""
            if generate_preview:
                preview_image_path = cls._generate_preview(
                    first_video, output_folder, crop_x_px, crop_y_px, 
                    crop_w_px, crop_h_px, target_width, target_height
                )
            
            # 批量处理视频
            processed_count = 0
            failed_files = []
            
            print(f"[批量视频裁剪器] 开始处理 {len(video_files)} 个视频文件")
            
            for video_file in video_files:
                try:
                    video_name = Path(video_file).stem
                    output_filename = f"{video_name}_{output_prefix}.mp4"
                    output_path = os.path.join(output_folder, output_filename)
                    
                    print(f"[批量视频裁剪器] 处理: {video_name}")
                    
                    # 使用FFmpeg进行裁剪和缩放
                    (
                        ffmpeg
                        .input(video_file)
                        .filter('crop', crop_w_px, crop_h_px, crop_x_px, crop_y_px)
                        .filter('scale', target_width, target_height)
                        .output(
                            output_path,
                            vcodec='libx264',
                            acodec='aac',
                            preset='fast',
                            **{'profile:v': 'main'}
                        )
                        .overwrite_output()
                        .run(quiet=True)
                    )
                    
                    # 验证输出文件
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        processed_count += 1
                        print(f"[批量视频裁剪器] 完成: {output_filename}")
                    else:
                        failed_files.append(video_name)
                        print(f"[批量视频裁剪器] 失败: {video_name} (输出文件无效)")
                        
                except Exception as e:
                    failed_files.append(video_name)
                    print(f"[批量视频裁剪器] 处理失败: {video_name}, 错误: {str(e)}")
            
            # 生成摘要
            summary = f"视频裁剪完成: 成功 {processed_count}/{len(video_files)} 个文件"
            if failed_files:
                summary += f", 失败: {len(failed_files)} 个文件"
            
            print(f"[批量视频裁剪器] {summary}")
            
            return io.NodeOutput(output_folder, preview_image_path, processed_count, crop_info, summary)
            
        except Exception as e:
            error_msg = f"批量视频裁剪器执行失败: {str(e)}"
            print(f"[批量视频裁剪器] 错误: {error_msg}")
            return io.NodeOutput("", "", 0, "", error_msg)
    
    @classmethod
    def _calculate_smart_crop(cls, orig_w, orig_h, target_w, target_h, mode):
        """计算智能裁剪参数"""
        # 计算目标宽高比
        target_ratio = target_w / target_h
        orig_ratio = orig_w / orig_h
        
        if orig_ratio > target_ratio:
            # 原视频更宽，需要裁剪宽度
            crop_h = orig_h
            crop_w = int(orig_h * target_ratio)
            
            if mode == "智能居中":
                crop_x = (orig_w - crop_w) // 2
                crop_y = 0
            elif mode == "左侧对齐":
                crop_x = 0
                crop_y = 0
            elif mode == "右侧对齐":
                crop_x = orig_w - crop_w
                crop_y = 0
            else:  # 顶部和底部对齐对于水平裁剪使用居中
                crop_x = (orig_w - crop_w) // 2
                crop_y = 0
        else:
            # 原视频更高，需要裁剪高度
            crop_w = orig_w
            crop_h = int(orig_w / target_ratio)
            
            if mode == "智能居中":
                crop_x = 0
                crop_y = (orig_h - crop_h) // 2
            elif mode == "顶部对齐":
                crop_x = 0
                crop_y = 0
            elif mode == "底部对齐":
                crop_x = 0
                crop_y = orig_h - crop_h
            else:  # 左侧和右侧对齐对于垂直裁剪使用居中
                crop_x = 0
                crop_y = (orig_h - crop_h) // 2
        
        # 转换为比例
        crop_x_ratio = crop_x / orig_w
        crop_y_ratio = crop_y / orig_h
        crop_w_ratio = crop_w / orig_w
        crop_h_ratio = crop_h / orig_h
        
        return crop_x_ratio, crop_y_ratio, crop_w_ratio, crop_h_ratio
    
    @classmethod
    def _generate_preview(cls, video_file, output_folder, crop_x, crop_y, crop_w, crop_h, target_w, target_h):
        """生成预览图片"""
        try:
            preview_path = os.path.join(output_folder, "preview_crop.jpg")
            
            # 提取中间帧并应用裁剪
            (
                ffmpeg
                .input(video_file, ss=1)  # 提取第1秒的帧
                .filter('crop', crop_w, crop_h, crop_x, crop_y)
                .filter('scale', target_w, target_h)
                .output(preview_path, vframes=1)
                .overwrite_output()
                .run(quiet=True)
            )
            
            if os.path.exists(preview_path):
                print(f"[批量视频裁剪器] 预览图已生成: {preview_path}")
                return preview_path
            else:
                return ""
                
        except Exception as e:
            print(f"[批量视频裁剪器] 预览图生成失败: {str(e)}")
            return ""


class BatchVideoComposer(io.ComfyNode):
    """批量视频空间合成器 - 支持多种布局的视频合成"""
    
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="BatchVideoComposer",
            display_name="批量视频空间合成器",
            category="batch_video",
            description="将多个文件夹的视频在空间上进行合成，支持多种布局方式",
            inputs=[
                # 文件夹输入
                io.String.Input("folder_1", tooltip="第一个视频文件夹"),
                io.String.Input("folder_2", tooltip="第二个视频文件夹"),
                io.String.Input("folder_3", optional=True, tooltip="第三个视频文件夹（可选）"),
                io.String.Input("folder_4", optional=True, tooltip="第四个视频文件夹（可选）"),
                
                # 合成布局
                io.Combo.Input("layout_mode", 
                               options=["左右分屏", "上下分屏", "画中画", "四宫格", "九宫格"], 
                               default="左右分屏", 
                               tooltip="合成布局模式"),
                
                # 输出尺寸
                io.Int.Input("output_width", default=1920, tooltip="输出宽度"),
                io.Int.Input("output_height", default=1080, tooltip="输出高度"),
                
                # 边框和间距
                io.Int.Input("border_width", default=0, tooltip="边框宽度（像素）"),
                io.String.Input("border_color", default="black", tooltip="边框颜色"),
                io.Int.Input("gap_size", default=0, tooltip="视频间隙（像素）"),
                
                # 音频处理
                io.Combo.Input("audio_mode", 
                               options=["主视频音频", "混合音频", "静音"], 
                               default="主视频音频", 
                               tooltip="音频处理方式"),
                
                # 视频选择策略
                io.Combo.Input("selection_mode", 
                               options=["按顺序", "随机组合", "时长匹配"], 
                               default="按顺序", 
                               tooltip="视频选择策略"),
                
                io.String.Input("output_prefix", default="合成", tooltip="输出文件名前缀"),
            ],
            outputs=[
                io.String.Output("output_folder", display_name="输出文件夹"),
                io.Int.Output("composed_count", display_name="合成数量"),
                io.String.Output("layout_info", display_name="布局信息"),
                io.String.Output("summary", display_name="处理摘要"),
            ],
        )
    
    @classmethod
    def execute(cls, folder_1, folder_2, folder_3=None, folder_4=None,
                layout_mode="左右分屏", output_width=1920, output_height=1080,
                border_width=0, border_color="black", gap_size=0,
                audio_mode="主视频音频", selection_mode="按顺序", output_prefix="合成"):
        import os
        import random
        import time
        from pathlib import Path
        from .utils import scan_media_files
        import ffmpeg
        
        try:
            # 收集所有输入文件夹
            input_folders = [folder_1, folder_2]
            if folder_3 and os.path.exists(folder_3):
                input_folders.append(folder_3)
            if folder_4 and os.path.exists(folder_4):
                input_folders.append(folder_4)
            
            # 验证文件夹并扫描视频文件
            folder_videos = []
            for i, folder in enumerate(input_folders):
                if not os.path.exists(folder):
                    raise ValueError(f"文件夹 {i+1} 不存在: {folder}")
                
                videos = scan_media_files(folder, file_types=['video']).get('video', [])
                if not videos:
                    raise ValueError(f"文件夹 {i+1} 中未找到视频文件: {folder}")
                
                folder_videos.append(videos)
                print(f"[批量视频合成器] 文件夹 {i+1}: {len(videos)} 个视频")
            
            # 检查布局和文件夹数量匹配
            required_folders = cls._get_required_folders(layout_mode)
            if len(folder_videos) < required_folders:
                raise ValueError(f"布局 '{layout_mode}' 需要至少 {required_folders} 个文件夹，但只提供了 {len(folder_videos)} 个")
            
            # 创建输出文件夹
            timestamp = int(time.time())
            output_folder = os.path.join(folder_paths.get_temp_directory(), f"{output_prefix}_视频合成_{timestamp}")
            os.makedirs(output_folder, exist_ok=True)
            
            # 计算布局信息
            layout_info = cls._calculate_layout(layout_mode, output_width, output_height, gap_size)
            layout_desc = f"布局: {layout_mode}, 输出尺寸: {output_width}x{output_height}"
            if gap_size > 0:
                layout_desc += f", 间隙: {gap_size}px"
            if border_width > 0:
                layout_desc += f", 边框: {border_width}px {border_color}"
            
            print(f"[批量视频合成器] {layout_desc}")
            
            # 生成视频组合
            video_groups = cls._generate_video_groups(folder_videos, selection_mode, required_folders)
            
            composed_count = 0
            failed_count = 0
            
            print(f"[批量视频合成器] 开始合成 {len(video_groups)} 个视频组合")
            
            for i, video_group in enumerate(video_groups):
                try:
                    output_filename = f"{output_prefix}_{i+1:03d}.mp4"
                    output_path = os.path.join(output_folder, output_filename)
                    
                    group_names = [Path(v).name for v in video_group]
                    print(f"[批量视频合成器] 合成组合 {i+1}: {', '.join(group_names)}")
                    
                    # 执行视频合成
                    success = cls._compose_videos(
                        video_group, output_path, layout_info, 
                        output_width, output_height, audio_mode,
                        border_width, border_color, gap_size
                    )
                    
                    if success:
                        composed_count += 1
                        print(f"[批量视频合成器] 完成: {output_filename}")
                    else:
                        failed_count += 1
                        print(f"[批量视频合成器] 失败: {output_filename}")
                        
                except Exception as e:
                    failed_count += 1
                    print(f"[批量视频合成器] 合成失败: 组合 {i+1}, 错误: {str(e)}")
            
            # 生成摘要
            summary = f"视频合成完成: 成功 {composed_count}/{len(video_groups)} 个组合"
            if failed_count > 0:
                summary += f", 失败: {failed_count} 个组合"
            
            print(f"[批量视频合成器] {summary}")
            
            return io.NodeOutput(output_folder, composed_count, layout_desc, summary)
            
        except Exception as e:
            error_msg = f"批量视频合成器执行失败: {str(e)}"
            print(f"[批量视频合成器] 错误: {error_msg}")
            return io.NodeOutput("", 0, "", error_msg)
    
    @classmethod
    def _get_required_folders(cls, layout_mode):
        """获取布局模式需要的最少文件夹数量"""
        layout_requirements = {
            "左右分屏": 2,
            "上下分屏": 2,
            "画中画": 2,
            "四宫格": 4,
            "九宫格": 4,  # 最少4个，可以重复使用
        }
        return layout_requirements.get(layout_mode, 2)
    
    @classmethod
    def _calculate_layout(cls, layout_mode, output_w, output_h, gap_size):
        """计算布局信息"""
        layouts = {
            "左右分屏": [
                {"x": 0, "y": 0, "w": (output_w - gap_size) // 2, "h": output_h},
                {"x": (output_w + gap_size) // 2, "y": 0, "w": (output_w - gap_size) // 2, "h": output_h}
            ],
            "上下分屏": [
                {"x": 0, "y": 0, "w": output_w, "h": (output_h - gap_size) // 2},
                {"x": 0, "y": (output_h + gap_size) // 2, "w": output_w, "h": (output_h - gap_size) // 2}
            ],
            "画中画": [
                {"x": 0, "y": 0, "w": output_w, "h": output_h},  # 主画面
                {"x": output_w - 320 - 20, "y": 20, "w": 320, "h": 180}  # 小画面
            ],
            "四宫格": [
                {"x": 0, "y": 0, "w": (output_w - gap_size) // 2, "h": (output_h - gap_size) // 2},
                {"x": (output_w + gap_size) // 2, "y": 0, "w": (output_w - gap_size) // 2, "h": (output_h - gap_size) // 2},
                {"x": 0, "y": (output_h + gap_size) // 2, "w": (output_w - gap_size) // 2, "h": (output_h - gap_size) // 2},
                {"x": (output_w + gap_size) // 2, "y": (output_h + gap_size) // 2, "w": (output_w - gap_size) // 2, "h": (output_h - gap_size) // 2}
            ],
            "九宫格": [
                {"x": 0, "y": 0, "w": output_w // 3, "h": output_h // 3},
                {"x": output_w // 3, "y": 0, "w": output_w // 3, "h": output_h // 3},
                {"x": 2 * output_w // 3, "y": 0, "w": output_w // 3, "h": output_h // 3},
                {"x": 0, "y": output_h // 3, "w": output_w // 3, "h": output_h // 3},
                {"x": output_w // 3, "y": output_h // 3, "w": output_w // 3, "h": output_h // 3},
                {"x": 2 * output_w // 3, "y": output_h // 3, "w": output_w // 3, "h": output_h // 3},
                {"x": 0, "y": 2 * output_h // 3, "w": output_w // 3, "h": output_h // 3},
                {"x": output_w // 3, "y": 2 * output_h // 3, "w": output_w // 3, "h": output_h // 3},
                {"x": 2 * output_w // 3, "y": 2 * output_h // 3, "w": output_w // 3, "h": output_h // 3}
            ]
        }
        return layouts.get(layout_mode, layouts["左右分屏"])
    
    @classmethod
    def _generate_video_groups(cls, folder_videos, selection_mode, required_folders):
        """生成视频组合"""
        if selection_mode == "按顺序":
            # 按顺序组合，以最少的文件夹为准
            min_count = min(len(videos) for videos in folder_videos)
            groups = []
            for i in range(min_count):
                group = []
                for folder_vids in folder_videos[:required_folders]:
                    group.append(folder_vids[i])
                groups.append(group)
            return groups
            
        elif selection_mode == "随机组合":
            # 随机组合
            max_combinations = 50  # 限制最大组合数
            groups = []
            for _ in range(max_combinations):
                group = []
                for folder_vids in folder_videos[:required_folders]:
                    group.append(random.choice(folder_vids))
                if group not in groups:  # 避免重复
                    groups.append(group)
                if len(groups) >= max_combinations:
                    break
            return groups
            
        elif selection_mode == "时长匹配":
            # 按时长匹配（简化实现，按顺序但尽量匹配时长）
            return cls._generate_video_groups(folder_videos, "按顺序", required_folders)
        
        return []
    
    @classmethod
    def _compose_videos(cls, video_group, output_path, layout_info, output_w, output_h, 
                       audio_mode, border_width, border_color, gap_size):
        """合成视频"""
        try:
            # 创建输入流
            inputs = []
            scaled_streams = []
            
            for i, video_file in enumerate(video_group):
                if i >= len(layout_info):
                    break
                    
                layout = layout_info[i]
                input_stream = ffmpeg.input(video_file)
                inputs.append(input_stream)
                
                # 缩放视频到指定尺寸
                scaled = input_stream.video.filter('scale', layout['w'], layout['h'])
                scaled_streams.append(scaled)
            
            # 创建背景
            if gap_size > 0 or border_width > 0:
                # 创建黑色背景
                background = ffmpeg.input('color=black:size={}x{}:duration=1'.format(output_w, output_h), f='lavfi')
                base_stream = background
            else:
                base_stream = scaled_streams[0]
                scaled_streams = scaled_streams[1:]
            
            # 逐个叠加视频
            result_stream = base_stream
            for i, scaled in enumerate(scaled_streams):
                layout = layout_info[i + (1 if gap_size > 0 or border_width > 0 else 0)]
                result_stream = result_stream.overlay(scaled, x=layout['x'], y=layout['y'])
            
            # 处理音频
            if audio_mode == "主视频音频":
                audio_stream = inputs[0].audio
            elif audio_mode == "混合音频":
                audio_streams = [inp.audio for inp in inputs[:2]]  # 最多混合前两个
                if len(audio_streams) > 1:
                    audio_stream = ffmpeg.filter(audio_streams, 'amix', inputs=len(audio_streams))
                else:
                    audio_stream = audio_streams[0]
            else:  # 静音
                audio_stream = None
            
            # 输出
            output_args = {
                'vcodec': 'libx264',
                'preset': 'fast',
                **{'profile:v': 'main'}
            }
            
            if audio_stream:
                output_args['acodec'] = 'aac'
                (
                    ffmpeg
                    .output(result_stream, audio_stream, output_path, **output_args)
                    .overwrite_output()
                    .run(quiet=True)
                )
            else:
                (
                    ffmpeg
                    .output(result_stream, output_path, **output_args)
                    .overwrite_output()
                    .run(quiet=True)
                )
            
            # 验证输出文件
            return os.path.exists(output_path) and os.path.getsize(output_path) > 0
            
        except Exception as e:
            print(f"[批量视频合成器] 合成失败: {str(e)}")
            return False


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
            SmartAudioBasedCutter,      # 新增：智能音频时长切分器
            VideoNormalizer,            # 新增：视频标准化器
            SmartAudioMixer,            # 新增：智能音频合成器
            BatchSubtitleGenerator,     # 新增：批量字幕生成器
            BatchVideoCropper,          # 新增：批量视频裁剪器
            BatchVideoComposer,         # 新增：批量视频空间合成器
            BatchLLMGenerator,          # 新增：批量文案生成器
            BatchTTSGenerator,          # 新增：批量TTS生成器
            SmartVideoCutterWithAudio,  # 新增：智能视频裁切+音频融合器
            VideoStaticCleaner,         # 新增：视频静止片段清理器
            GameHighlightExtractor,     # 新增：游戏精彩片段提取器
            VideoThumbnailGenerator,    # 新增：视频缩略图生成器
            BatchVideoDownloader,
            BatchFileManager,
        ]