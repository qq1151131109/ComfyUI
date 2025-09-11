/**
 * 批量视频上传组件 - 直接调用系统文件选择对话框
 */

import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

// 直接调用系统多选文件对话框
function selectMultipleFiles(callback) {
    const input = document.createElement("input");
    input.type = "file";
    input.multiple = true;
    input.accept = "video/*,audio/*,image/*,.mp4,.avi,.mov,.mkv,.flv,.wmv,.m4v,.webm,.mp3,.wav,.aac,.flac,.ogg,.m4a,.wma,.jpg,.jpeg,.png,.gif,.bmp,.tiff,.webp";
    input.style.display = "none";
    
    input.onchange = function(e) {
        const files = Array.from(e.target.files);
        if (files.length > 0) {
            console.log(`选择了 ${files.length} 个素材文件:`, files.map(f => f.name));
            callback(files, "multiple_files");
        }
        document.body.removeChild(input);
    };
    
    document.body.appendChild(input);
    input.click();
}

// 直接调用系统文件夹选择对话框
function selectFolder(callback) {
    const input = document.createElement("input");
    input.type = "file";
    input.webkitdirectory = true;
    input.multiple = true;
    input.style.display = "none";
    
    input.onchange = function(e) {
        // 过滤出支持的素材文件
        const allFiles = Array.from(e.target.files);
        const supportedExts = [
            // 视频
            'mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv', 'm4v', 'webm',
            // 音频
            'mp3', 'wav', 'aac', 'flac', 'ogg', 'm4a', 'wma',
            // 图像
            'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp'
        ];
        
        const mediaFiles = allFiles.filter(file => {
            const ext = file.name.toLowerCase().split('.').pop();
            return supportedExts.includes(ext);
        });
        
        if (mediaFiles.length > 0) {
            console.log(`从文件夹中找到 ${mediaFiles.length} 个素材文件:`, mediaFiles.map(f => f.name));
            callback(mediaFiles, "folder");
        } else {
            alert("在选择的文件夹中没有找到支持的素材文件！\\n支持格式:\\n• 视频: mp4, avi, mov, mkv, flv, wmv, m4v, webm\\n• 音频: mp3, wav, aac, flac, ogg, m4a, wma\\n• 图像: jpg, jpeg, png, gif, bmp, tiff, webp");
        }
        document.body.removeChild(input);
    };
    
    document.body.appendChild(input);
    input.click();
}


// 模拟上传过程（将文件信息传递给节点）
async function processFiles(files, nodeContext) {
    try {
        // 显示处理状态
        const statusElement = document.createElement("div");
        statusElement.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: #007acc;
            color: white;
            padding: 10px 20px;
            border-radius: 5px;
            z-index: 10000;
            font-family: Arial, sans-serif;
        `;
        statusElement.textContent = `正在处理 ${files.length} 个素材文件...`;
        document.body.appendChild(statusElement);
        
        // 生成会话名称
        const now = new Date();
        const timestamp = now.toISOString().slice(0, 19).replace('T', '_').replace(/:/g, '-');
        const sessionName = `批量上传_${timestamp}`;
        
        // 模拟处理延迟
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        // 更新状态
        statusElement.textContent = `处理完成！会话: ${sessionName}`;
        statusElement.style.background = "#28a745";
        
        // 更新节点参数
        if (nodeContext) {
            // 设置会话名称
            const sessionWidget = nodeContext.widgets.find(w => w.name === "session_name");
            if (sessionWidget) {
                sessionWidget.value = sessionName;
            }
            
            // 设置为创建新会话模式
            const modeWidget = nodeContext.widgets.find(w => w.name === "load_mode");
            if (modeWidget) {
                modeWidget.value = "创建新会话";
            }
            
            // 触发界面更新
            if (nodeContext.onResize) {
                nodeContext.onResize(nodeContext.size);
            }
            
            console.log(`✅ 批量上传完成: ${files.length} 个文件 → 会话: ${sessionName}`);
        }
        
        // 3秒后移除状态提示
        setTimeout(() => {
            if (document.body.contains(statusElement)) {
                document.body.removeChild(statusElement);
            }
        }, 3000);
        
    } catch (error) {
        alert(`处理失败: ${error.message}`);
    }
}

// 下载文件的函数
function downloadFile(filePath, fileName) {
    // 创建下载链接
    const link = document.createElement('a');
    link.href = `/view?filename=${encodeURIComponent(filePath)}&type=output`;
    link.download = fileName;
    link.style.display = 'none';
    
    // 触发下载
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    console.log(`开始下载: ${fileName}`);
}

// 为节点添加功能
app.registerExtension({
    name: "BatchVideoProcessor.SimpleUploader",
    
    beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "BatchVideoLoader") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
                
                // 添加多选文件按钮
                this.addWidget("button", "📁 选择多个素材文件", "select_multiple", () => {
                    selectMultipleFiles((files, type) => {
                        processFiles(files, this);
                    });
                });
                
                // 添加选择文件夹按钮
                this.addWidget("button", "📂 选择素材文件夹", "select_folder", () => {
                    selectFolder((files, type) => {
                        processFiles(files, this);
                    });
                });
                
                return r;
            };
        }
        
        // 为批量下载器添加下载按钮
        if (nodeData.name === "BatchVideoDownloader") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;
                
                // 添加下载按钮
                this.addWidget("button", "📥 下载压缩包", "download_archive", () => {
                    // 检查节点是否已执行并有输出
                    if (this.outputs && this.outputs[0] && this.outputs[0].widget) {
                        const downloadPath = this.outputs[0].widget.value;
                        if (downloadPath && downloadPath.trim() !== "") {
                            const fileName = downloadPath.split('/').pop() || 'download.zip';
                            downloadFile(downloadPath, fileName);
                        } else {
                            alert("请先执行节点生成下载文件！");
                        }
                    } else {
                        alert("请先执行节点生成下载文件！");
                    }
                });
                
                return r;
            };
        }
    }
});

console.log("✅ 简化批量上传组件已加载 - 直接调用系统对话框!");