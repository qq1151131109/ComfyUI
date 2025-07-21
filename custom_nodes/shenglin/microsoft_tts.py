import torch
import asyncio
import datetime
import edge_tts
import numpy as np
import torchaudio
import os
import io
import tempfile
import logging
import time
import json
from folder_paths import get_output_directory, get_save_image_path

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('微软语音合成')

# 文件路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
VOICES_CACHE_FILE = os.path.join(CURRENT_DIR, "voices_cache.json")
CACHE_EXPIRY_DAYS = 7  # 缓存有效期（天）

# 默认语音 - 在API连接失败时确保至少有这些语音可用
DEFAULT_VOICES = {
    "zh-CN-XiaoxiaoNeural (Female)": "zh-CN-XiaoxiaoNeural",
    "zh-CN-YunjianNeural (Male)": "zh-CN-YunjianNeural",
    "en-US-AnaNeural (Female)": "en-US-AnaNeural",
    "en-US-GuyNeural (Male)": "en-US-GuyNeural",
}

# 语音字典 - 静态变量，存储所有可用语音
ALL_VOICES = DEFAULT_VOICES.copy()

def load_voices_from_cache():
    """从缓存文件加载语音列表，并检查是否过期"""
    global ALL_VOICES
    try:
        if os.path.exists(VOICES_CACHE_FILE):
            # 检查文件修改时间
            file_mod_time = os.path.getmtime(VOICES_CACHE_FILE)
            current_time = time.time()
            days_old = (current_time - file_mod_time) / (24 * 3600)
            
            # 如果缓存过期，返回False
            if days_old > CACHE_EXPIRY_DAYS:
                logger.info(f'缓存文件已过期 ({days_old:.1f} 天)，需要更新')
                return False
                
            with open(VOICES_CACHE_FILE, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                
                # 兼容旧格式（直接是语音字典）和新格式（包含元数据）
                if isinstance(cache_data, dict):
                    if 'voices' in cache_data:
                        cached_voices = cache_data['voices']
                    else:
                        cached_voices = cache_data
                else:
                    cached_voices = {}
                    
                if cached_voices and len(cached_voices) > 0:
                    logger.info(f'从缓存加载了 {len(cached_voices)} 个语音')
                    # 合并缓存的语音和默认语音
                    ALL_VOICES.update(cached_voices)
                    return True
    except Exception as e:
        logger.error(f'从缓存加载语音失败: {e}')
    return False

# 尝试从缓存加载语音
load_voices_from_cache()

async def get_voices():
    """从Microsoft Edge TTS API获取可用的语音列表"""
    global ALL_VOICES
    try:
        voices = await edge_tts.list_voices()
        if voices:
            # 创建新的语音字典
            new_voices = {}
            for voice in voices:
                try:
                    shortname = voice['ShortName']
                    gender = voice['Gender']
                    locale = voice['Locale']
                    name = shortname[shortname.rfind('-')+1:shortname.find('Neural')]
                    display_name = f"{locale}:{name}({gender})"
                    new_voices[display_name] = shortname
                except KeyError:
                    continue

            logger.info(f"从API获取了 {len(new_voices)} 个可用语音")
            
            # 将新的语音信息保存到缓存文件（包含元数据）
            try:
                cache_data = {
                    'voices': new_voices,
                    'timestamp': time.time(),
                    'count': len(new_voices)
                }
                with open(VOICES_CACHE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
                logger.info(f"语音信息已保存到缓存文件: {VOICES_CACHE_FILE}")
            except Exception as e:
                logger.error(f"保存语音缓存失败: {e}")
            
            # 更新全局语音字典，确保默认语音和新语音都可用
            ALL_VOICES.update(new_voices)
            
            return new_voices
    except Exception as e:
        logger.error(f"获取语音列表失败: {e}")
    return {}

# 只有在缓存不存在或加载失败时才从API获取语音
if not load_voices_from_cache():
    logger.info("缓存不存在或已过期，从API获取语音列表...")
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(get_voices())
        loop.close()
    except Exception as e:
        logger.error(f"初始化获取语音失败: {e}")
        logger.info(f"使用默认语音列表 ({len(ALL_VOICES)} 个语音)")
else:
    logger.info(f"使用缓存的语音列表 ({len(ALL_VOICES)} 个语音)")

async def gen_tts(_text, _voice, _rate, max_retries=3):
    """生成TTS音频并返回字节数据"""
    # 确保文本不为空
    if not _text or _text.strip() == "":
        _text = "测试语音"
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
        temp_path = temp_file.name
    
    exception = None
    # 尝试多次生成语音
    for attempt in range(max_retries):
        try:
            logger.info(f"尝试生成语音 (尝试 {attempt+1}/{max_retries})，语音={_voice}")
            communicate = edge_tts.Communicate(text=_text, voice=_voice, rate=_rate)
            await communicate.save(temp_path)
            
            # 检查文件是否存在且大小大于0
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                # 读取文件内容
                with open(temp_path, 'rb') as f:
                    audio_data = f.read()
                
                # 删除临时文件
                try:
                    os.unlink(temp_path)
                except:
                    pass
                
                return audio_data
            else:
                logger.warning(f"生成的音频文件为空，尝试重试...")
                time.sleep(1)  # 等待1秒再重试
                continue
                
        except edge_tts.exceptions.NoAudioReceived as e:
            logger.warning(f"未收到音频 (尝试 {attempt+1})，切换语音重试: {e}")
            exception = e
            # 如果出现错误，尝试使用默认语音
            if attempt < max_retries - 1:
                # 尝试使用其他语音
                backup_voices = list(DEFAULT_VOICES.values())
                if _voice in backup_voices:
                    backup_voices.remove(_voice)
                if backup_voices:
                    _voice = backup_voices[attempt % len(backup_voices)]
                    logger.info(f"切换到备用语音: {_voice}")
                time.sleep(1)  # 等待1秒再重试
            continue
        except Exception as e:
            logger.error(f"语音生成错误 (尝试 {attempt+1}): {e}")
            exception = e
            if attempt < max_retries - 1:
                time.sleep(1)  # 等待1秒再重试
            continue
    
    # 如果所有尝试都失败，清理并抛出异常
    try:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    except:
        pass
        
    if exception:
        raise exception
    else:
        raise RuntimeError("生成语音失败，所有尝试均未能获取音频数据")

class 微软语音合成:
    """将文本转换为语音，并返回音频数据和音频时长"""

    def __init__(self):
        self.output_dir = os.path.join(get_output_directory(), 'audio')
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    @classmethod
    def INPUT_TYPES(cls):
        # 使用全局语音字典中的所有语音
        VOICES = sorted(list(ALL_VOICES.keys()))
        
        # 先按语言代码排序
        def sort_key(voice_name):
            return voice_name.split(':')[0] if ':' in voice_name else voice_name
            
        VOICES = sorted(VOICES, key=sort_key)
        
        # 确保中文和英文语音在前面
        zh_voices = [v for v in VOICES if v.startswith('zh-')]
        en_voices = [v for v in VOICES if v.startswith('en-')]
        other_voices = [v for v in VOICES if not v.startswith('zh-') and not v.startswith('en-')]
        
        # 重新组织语音列表
        VOICES = zh_voices + en_voices + other_voices
        
        # 不再每次都打印语音数量，减少日志输出
        # logger.info(f"界面显示 {len(VOICES)} 个语音选项")
        
        default_voice = "zh-CN-XiaoxiaoNeural (Female)"
        if default_voice not in VOICES and VOICES:
            default_voice = VOICES[0]
            
        return {
            "required": {
                "voice": (VOICES, {"default": default_voice}),
                "rate": ("INT", {"default": 0, "min": -200, "max": 200, "step": 1, "tooltip": "语速调整 (-200 ~ +200)"}),
                "filename_prefix": ("STRING", {"default": "comfyUI"}),
                "text": ("STRING", {"multiline": True, "default": "您好，这是一段测试语音。"}),
            }
        }
    
    RETURN_TYPES = ("AUDIO", "FLOAT", "STRING")
    RETURN_NAMES = ("音频", "时长(秒)", "文件路径")
    FUNCTION = "text_to_audio"
    OUTPUT_NODE = True
    CATEGORY = "shenglin/音频处理"

    def text_to_audio(self, voice, filename_prefix, text, rate):
        # 从全局语音字典中获取语音ID
        if voice in ALL_VOICES:
            voice_name = ALL_VOICES[voice]
        else:
            # 如果找不到语音，使用默认语音
            logger.warning(f"找不到语音 '{voice}'，使用默认语音")
            voice_name = DEFAULT_VOICES["zh-CN-XiaoxiaoNeural (Female)"]
            
        full_output_folder, filename, counter, subfolder, filename_prefix = get_save_image_path(filename_prefix, self.output_dir)
        _datetime = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
        file = f"{filename}_{_datetime}_{voice_name}.mp3"
        audio_path = os.path.join(full_output_folder, file)
        _rate = str(rate) + "%" if rate < 0 else "+" + str(rate) + "%"
        
        logger.info(f"生成语音文件，声音='{voice_name}'，速率={rate}，路径='{audio_path}'，文本='{text}'")

        try:
            # 使用asyncio运行TTS生成
            audio_data = asyncio.run(gen_tts(text, voice_name, _rate))
            
            # 保存文件
            with open(audio_path, 'wb') as f:
                f.write(audio_data)
                
            # 转换为字节流供torchaudio使用
            audio_bytes = io.BytesIO(audio_data)
            
            # 加载音频并转换为AUDIO格式
            waveform, sample_rate = torchaudio.load(audio_bytes)
            waveform = waveform.unsqueeze(0)  # 添加batch维度 [B, C, T]
            
            # 计算音频时长（秒）
            duration_sec = waveform.shape[-1] / sample_rate
            
            # 创建AUDIO对象
            audio = {
                "waveform": waveform,
                "sample_rate": sample_rate
            }
            
            # 显示UI提示
            ui_info = {
                "ui": {
                    "text": f"音频文件：{audio_path}",
                    'audios': [{'filename': file, 'type': 'output', 'subfolder': 'audio'}]
                }
            }
            
            logger.info(f"音频时长: {duration_sec:.2f}秒")
            
            return (audio, duration_sec, audio_path)
            
        except Exception as e:
            logger.error(f"生成语音失败: {e}")
            # 创建一个空的音频作为回退方案
            empty_waveform = torch.zeros((1, 2, 8000), dtype=torch.float32)  # 1个batch, 2个声道, 8000个采样点 (0.5秒)
            empty_audio = {
                "waveform": empty_waveform,
                "sample_rate": 16000
            }
            return (empty_audio, 0.5, "生成失败")

# 节点列表
NODE_CLASS_MAPPINGS = {
    "微软语音合成": 微软语音合成
}

# 显示名称映射
NODE_DISPLAY_NAME_MAPPINGS = {
    "微软语音合成": "微软语音合成 (Microsoft TTS)"
} 