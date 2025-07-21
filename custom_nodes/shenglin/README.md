# 按秒计算音频时长 节点

这个ComfyUI自定义节点可以直接从音频计算出时长，并将其转换为 FramePackSampler 节点需要的视频时长参数（秒）。特别适合于需要让生成的视频长度与音频长度一致的场景。

## 功能

- 直接从音频输入计算出音频时长
- 可设置帧率和采样窗口大小参数
- 输出视频时长（秒），可直接连接到 FramePackSampler 节点的 total_second_length 参数

## 安装方法

1. 在ComfyUI的根目录下使用以下命令克隆仓库：
```bash
git clone https://github.com/你的用户名/comfyui-audio-duration-converter.git custom_nodes/shenglin
```

2. 重启ComfyUI

## 使用方法

1. 在节点菜单中找到 "shenglin/音频处理" 分类
2. 添加 "按秒计算音频时长" 节点
3. 连接音频输入
4. 设置所需的参数（latent_window_size和fps）
5. 将输出连接到 FramePackSampler 节点的 total_second_length 参数

## 参数说明

- **audio**: 音频输入
- **latent_window_size**: 采样窗口大小，默认为9，应与 FramePackSampler 节点的对应参数相同
- **fps**: 每秒帧数，默认为30

## 输出

- **total_second_length**: 视频时长（秒）

## 工作流程示例

1. 加载音频文件
2. 将音频直接连接到本节点
3. 将本节点的输出连接到 FramePackSampler 节点的 total_second_length 参数

这样可以让生成的视频长度与输入的音频长度匹配，便于创建音视频同步的内容。 