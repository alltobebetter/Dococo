from flask import Flask, request, Response, jsonify
from flask_cors import CORS
import requests
import json
import hashlib
import os
import time
import threading
import urllib.parse
import traceback
import logging

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})  # 允许所有来源访问API

# 设置日志级别
logging.basicConfig(level=logging.DEBUG)
app.logger = logging.getLogger(__name__)

# AI API 配置信息
AI_API = {
    "baseURL": "https://api.gptgod.online/v1/chat/completions",
    "apiKey": "sk-91g5VZZfJOOVlm9OppDT3GrMk0T5qlSFboEOMZamiKIaEvJg",
    "model": "gpt-4o-mini"
}

# 获取当前脚本所在的目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# 文章内容目录 - 设置为项目根目录
CONTENT_DIR = os.path.join(os.environ.get('VERCEL_ROOT_DIR', SCRIPT_DIR), '..')
app.logger.info(f"内容目录设置为: {CONTENT_DIR}")

# 远程缓存配置
REMOTE_CACHE_URL = "https://dococo.vchat.xin/dococo.json"
REMOTE_UPDATE_URL = "https://dococo.vchat.xin/"
REMOTE_UPDATE_PASSWORD = "K9$mPx7!vL2qW8&nR5tY3@jF1*bQ4zG"

# 缓存锁，防止并发写入冲突
cache_lock = threading.Lock()

# 文章目录缓存
articles_cache = None
articles_cache_time = 0
ARTICLES_CACHE_TTL = 60  # 60秒缓存有效期

def get_content_hash(content):
    """
    根据内容生成唯一的哈希值，用作缓存的键
    """
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def load_cache():
    """
    从远程URL加载缓存
    """
    try:
        response = requests.get(REMOTE_CACHE_URL, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            app.logger.error(f"加载远程缓存失败: HTTP {response.status_code}")
            return {}
    except Exception as e:
        app.logger.error(f"加载远程缓存出错: {str(e)}")
        return {}

def save_cache_entry(content_hash, summary, timestamp):
    """
    将新的缓存条目保存到远程服务器
    """
    try:
        # 使用URL参数更新远程缓存
        params = {
            'time': timestamp,
            'md5': content_hash,
            'summary': summary,
            'pass': REMOTE_UPDATE_PASSWORD
        }
        
        # 构建完整URL并发送请求
        encoded_params = urllib.parse.urlencode(params)
        update_url = f"{REMOTE_UPDATE_URL}?{encoded_params}"
        
        response = requests.get(update_url, timeout=10)
        
        if response.status_code == 200:
            app.logger.info(f"成功更新远程缓存: {content_hash[:8]}...")
            return True
        else:
            app.logger.error(f"更新远程缓存失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        app.logger.error(f"更新远程缓存出错: {str(e)}")
        return False

# 主路由处理器 - 捕获所有API请求
@app.route('/api/<path:path>', methods=['GET', 'POST', 'OPTIONS'])
def api_handler(path):
    """
    处理所有API请求的路由
    """
    app.logger.info(f"收到API请求: {path}, 方法: {request.method}")
    
    # 处理预检请求
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        return response
    
    try:
        if path == 'summary':
            return generate_summary()
        elif path == 'search':
            return search_content()
        elif path == 'health':
            return jsonify({"status": "ok", "timestamp": time.time()})
        else:
            app.logger.error(f"未知的API路径: {path}")
            return jsonify({"error": f"未知的API路径: {path}"}), 404
    except Exception as e:
        app.logger.error(f"处理API请求时出错: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

def search_content():
    """
    搜索API接口
    根据查询参数搜索文章内容
    """
    try:
        # 获取查询参数
        query = request.args.get('query', '')
        app.logger.info(f"搜索查询: {query}")
        
        if not query:
            return jsonify({"error": "查询参数不能为空"}), 400
        
        # 返回模拟搜索结果
        search_results = [
            {
                "file": "home.md",
                "title": "首页",
                "context": f"这是一个包含查询词 '{query}' 的示例搜索结果。由于Vercel环境限制，无法读取目录下的文件进行真实搜索。"
            },
            {
                "file": "example.md",
                "title": "示例文章",
                "context": f"另一个包含查询词 '{query}' 的示例结果。请使用本地开发环境进行完整功能测试。"
            }
        ]
        
        response = jsonify(search_results)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    
    except Exception as e:
        app.logger.error(f"搜索处理出错: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

def generate_summary():
    """
    生成AI总结的接口
    """
    try:
        # 确保是POST请求
        if request.method != 'POST':
            return jsonify({"error": "只支持POST请求"}), 405
        
        # 获取请求数据
        content = request.json.get('content')
        app.logger.info(f"收到总结请求，内容长度: {len(content) if content else 0}")
        
        if not content:
            return jsonify({"error": "内容不能为空"}), 400
        
        # 生成内容哈希作为缓存键
        content_hash = get_content_hash(content)
        app.logger.info(f"内容哈希值: {content_hash[:8]}...")
        
        # 检查缓存
        cache = load_cache()
        app.logger.info(f"缓存加载完成，条目数: {len(cache)}")
        
        cache_exists = content_hash in cache
        app.logger.info(f"缓存存在: {cache_exists}")
        
        # 如果缓存存在，直接返回缓存的摘要
        if cache_exists:
            app.logger.info(f"使用缓存: {content_hash[:8]}...")
            cached_summary = cache[content_hash]["summary"]
            
            # Vercel环境中简化处理，不使用流式响应
            return jsonify({
                "summary": cached_summary
            })
        
        # 准备AI API请求
        app.logger.info(f"准备请求AI API，模型: {AI_API['model']}")
        
        # 在Vercel环境中，简化请求，不使用流式响应
        payload = {
            "model": AI_API["model"],
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个专业的内容总结助手。请用中文简洁地总结用户提供的内容，生成连续的文本，不要使用分点形式，不要换行，总结不超过100字。"
                },
                {
                    "role": "user",
                    "content": content
                }
            ],
            "stream": False  # 在Vercel环境中禁用流式响应
        }
        
        # 发送请求到AI API
        try:
            app.logger.info(f"发送请求到 {AI_API['baseURL']}")
            response = requests.post(
                AI_API["baseURL"],
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {AI_API['apiKey']}"
                },
                json=payload,
                timeout=30
            )
            
            # 检查响应状态
            if response.status_code != 200:
                error_msg = f"AI API请求失败: {response.status_code}"
                app.logger.error(error_msg)
                app.logger.error(f"响应内容: {response.text}")
                return jsonify({"error": error_msg}), 500
            
            # 解析响应
            api_response = response.json()
            app.logger.info(f"AI API响应成功，状态码: {response.status_code}")
            
            # 提取摘要文本
            summary = api_response['choices'][0]['message']['content']
            app.logger.info(f"AI总结完成，长度: {len(summary)}")
            
            # 保存到远程缓存
            current_time = time.time()
            save_result = save_cache_entry(content_hash, summary, current_time)
            app.logger.info(f"缓存保存结果: {'成功' if save_result else '失败'}")
            
            # 返回摘要
            return jsonify({
                "summary": summary
            })
            
        except Exception as e:
            app.logger.error(f"处理AI API请求时出错: {str(e)}")
            app.logger.error(traceback.format_exc())
            return jsonify({"error": f"AI API请求出错: {str(e)}"}), 500
    
    except Exception as e:
        app.logger.error(f"处理总结请求出错: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

# 主页路由
@app.route('/')
def index():
    return """
    <html>
        <head><title>Python API</title></head>
        <body>
            <h1>Python API服务运行中</h1>
            <p>这是后端API服务，请使用前端页面访问完整功能。</p>
            <p><a href="/api/health">健康检查</a></p>
        </body>
    </html>
    """

# 这一段是为本地开发用的
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 