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


// 处理文件上传 - 使用ComfyUI原生API自动上传
async function processFiles(files, nodeContext) {
    try {
        // 生成会话文件夹名称
        const now = new Date();
        const timestamp = now.toISOString().slice(0, 19).replace('T', '_').replace(/:/g, '-');
        const sessionFolder = `batch_upload_${timestamp}`;
        
        // 显示上传进度
        const statusElement = document.createElement("div");
        statusElement.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: #007acc;
            color: white;
            padding: 15px 25px;
            border-radius: 8px;
            z-index: 10000;
            font-family: Arial, sans-serif;
            min-width: 300px;
            text-align: center;
        `;
        statusElement.innerHTML = `
            <div>正在上传 ${files.length} 个文件...</div>
            <div style="margin-top: 10px; font-size: 12px;">会话: ${sessionFolder}</div>
        `;
        document.body.appendChild(statusElement);
        
        let uploadedCount = 0;
        let failedCount = 0;
        
        // 逐个上传文件
        for (const file of files) {
            try {
                const formData = new FormData();
                formData.append('image', file, file.name);
                formData.append('type', 'input');
                formData.append('subfolder', `batch_uploads/${sessionFolder}`);
                
                const response = await fetch('/upload/image', {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    uploadedCount++;
                    statusElement.innerHTML = `
                        <div>上传进度: ${uploadedCount}/${files.length}</div>
                        <div style="margin-top: 5px; font-size: 12px;">当前: ${file.name}</div>
                        <div style="margin-top: 5px; font-size: 12px;">会话: ${sessionFolder}</div>
                    `;
                } else {
                    failedCount++;
                    console.warn(`上传失败: ${file.name}, 状态: ${response.status}`);
                }
            } catch (error) {
                failedCount++;
                console.error(`上传文件 ${file.name} 时出错:`, error);
            }
        }
        
        // 显示完成状态
        if (failedCount === 0) {
            statusElement.style.background = "#28a745";
            statusElement.innerHTML = `
                <div>✅ 上传完成！</div>
                <div style="margin-top: 5px; font-size: 12px;">成功: ${uploadedCount} 个文件</div>
                <div style="margin-top: 5px; font-size: 12px;">会话: ${sessionFolder}</div>
            `;
        } else {
            statusElement.style.background = "#ffc107";
            statusElement.innerHTML = `
                <div>⚠️ 部分上传完成</div>
                <div style="margin-top: 5px; font-size: 12px;">成功: ${uploadedCount}, 失败: ${failedCount}</div>
                <div style="margin-top: 5px; font-size: 12px;">会话: ${sessionFolder}</div>
            `;
        }
        
        // 自动设置节点参数
        if (nodeContext && uploadedCount > 0) {
            const pathWidget = nodeContext.widgets.find(w => w.name === "input_folder_path");
            if (pathWidget) {
                pathWidget.value = ""; // 清空路径，让节点自动查找最新会话
            }
            
            // 触发界面更新
            if (nodeContext.onResize) {
                nodeContext.onResize(nodeContext.size);
            }
        }
        
        console.log(`✅ 批量上传完成: ${uploadedCount} 成功, ${failedCount} 失败 → 会话: ${sessionFolder}`);
        
        // 5秒后移除状态提示
        setTimeout(() => {
            if (document.body.contains(statusElement)) {
                document.body.removeChild(statusElement);
            }
        }, 5000);
        
    } catch (error) {
        console.error('批量上传过程出错:', error);
        alert(`上传失败: ${error.message}`);
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
                    // 检查节点是否已执行并有输出 - 通过UI显示的结果检查
                    console.log("🐛 下载按钮被点击，检查节点状态...");
                    console.log("🐛 节点对象:", this);
                    console.log("🐛 节点images:", this.images);
                    console.log("🐛 节点widgets_values:", this.widgets_values);
                    
                    // 方法1: 检查是否有images输出
                    if (this.images && this.images.length > 0) {
                        // 如果有images输出，说明节点已执行，尝试构造下载链接
                        console.log("✅ 检测到节点已执行，尝试下载...");
                        // 使用外网IP地址构造下载URL模式
                        const baseUrl = "http://103.231.86.148:9000/view";
                        // 从images中获取filename，这通常包含我们生成的zip文件名
                        if (this.images[0] && this.images[0].filename) {
                            const filename = this.images[0].filename;
                            const downloadUrl = `${baseUrl}?filename=${encodeURIComponent(filename)}&type=output`;
                            console.log(`🔗 构造下载链接: ${downloadUrl}`);
                            
                            // 直接打开下载链接
                            const link = document.createElement('a');
                            link.href = downloadUrl;
                            link.download = filename;
                            link.style.display = 'none';
                            document.body.appendChild(link);
                            link.click();
                            document.body.removeChild(link);
                            console.log(`✅ 开始下载: ${filename}`);
                        } else {
                            console.log("❌ 无法获取下载文件信息");
                            alert("无法获取下载文件信息，请重新执行节点！");
                        }
                    } else {
                        console.log("❌ 节点未执行或无输出");
                        alert("请先执行节点生成下载文件！");
                    }
                });
                
                return r;
            };
        }
    }
});

console.log("✅ 批量素材上传器已加载 - 一键上传，自动创建文件夹!");