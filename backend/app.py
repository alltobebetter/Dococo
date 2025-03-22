from flask import Flask, request, Response, jsonify
from flask_cors import CORS
import requests
import json
import hashlib
import os
import time
import threading
import glob
import re
import urllib.parse

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# AI API 配置信息
AI_API = {
    "baseURL": "https://api.gptgod.online/v1/chat/completions",
    "apiKey": "sk-91g5VZZfJOOVlm9OppDT3GrMk0T5qlSFboEOMZamiKIaEvJg",
    "model": "gpt-4o-mini"
}

# 获取当前脚本所在的目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# 文章内容目录 - 改为项目根目录的绝对路径
CONTENT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

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
        response = requests.get(REMOTE_CACHE_URL, timeout=5)
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
        
        response = requests.get(update_url, timeout=5)
        
        if response.status_code == 200:
            app.logger.info(f"成功更新远程缓存: {content_hash[:8]}...")
            return True
        else:
            app.logger.error(f"更新远程缓存失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        app.logger.error(f"更新远程缓存出错: {str(e)}")
        return False

def get_article_files():
    """
    获取所有文章文件路径
    """
    global articles_cache, articles_cache_time
    
    # 如果缓存有效，直接返回缓存
    current_time = time.time()
    if articles_cache is not None and current_time - articles_cache_time < ARTICLES_CACHE_TTL:
        return articles_cache
    
    try:
        articles = []
        
        # 先尝试直接搜索所有md文件
        md_files = glob.glob(os.path.join(CONTENT_DIR, "*.md"))
        app.logger.info(f"目录中找到 {len(md_files)} 个md文件: {', '.join([os.path.basename(f) for f in md_files])}")
        
        for file_path in md_files:
            file_name = os.path.basename(file_path)
            if file_name != "content.md":  # 暂时排除content.md
                articles.append(file_name)
                app.logger.info(f"添加文件: {file_name}")
        
        # 从content.md获取文件列表（如果存在但没在目录中被找到的文件）
        content_file_path = os.path.join(CONTENT_DIR, "content.md")
        
        app.logger.info(f"尝试读取content.md文件: {content_file_path}")
        app.logger.info(f"文件存在: {os.path.exists(content_file_path)}")
        
        # 如果content.md存在，从中读取文件列表
        if os.path.exists(content_file_path):
            with open(content_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                app.logger.info(f"成功读取content.md文件，内容长度: {len(content)}")
                
                # 提取markdown链接格式: [text](file.md)
                links = re.findall(r'\[.*?\]\((.*?\.md)\)', content)
                app.logger.info(f"从content.md中提取了 {len(links)} 个文件链接")
                
                for link in links:
                    file_name = os.path.basename(link)
                    full_path = os.path.join(CONTENT_DIR, link)
                    if os.path.exists(full_path) and file_name not in articles:
                        articles.append(file_name)
                        app.logger.info(f"从content.md添加额外文件: {file_name}")
                    elif not os.path.exists(full_path):
                        app.logger.warning(f"content.md中引用的文件不存在: {full_path}")
        
        # 更新缓存
        articles_cache = articles
        articles_cache_time = current_time
        
        app.logger.info(f"总共找到 {len(articles)} 个文章文件: {', '.join(articles)}")
        return articles
        
    except Exception as e:
        app.logger.error(f"获取文章列表失败: {str(e)}")
        return []

def search_in_file(file_path, query):
    """
    在单个文件中搜索内容
    """
    file_name = os.path.basename(file_path)
    app.logger.info(f"搜索文件: {file_name}")
    
    # 首先检查文件名是否包含搜索词
    file_name_match = query.lower() in file_name.lower()
    if file_name_match:
        app.logger.info(f"文件名包含搜索词: {file_name}")
    
    try:
        if not os.path.exists(file_path):
            app.logger.warning(f"文件不存在: {file_path}")
            if file_name_match:
                # 如果文件名匹配但文件不存在，仍然返回结果
                return {
                    "file": file_name,
                    "title": file_name,
                    "context": f"文件名中包含搜索词: {file_name}"
                }
            return None
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            app.logger.info(f"读取文件成功，内容长度: {len(content)}")
            
            # 提取文件标题
            title = file_name
            title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            if title_match:
                title = title_match.group(1)
                app.logger.info(f"提取到标题: {title}")
            
            # 检查标题中是否包含搜索词
            title_match = query.lower() in title.lower()
            if title_match:
                app.logger.info(f"标题包含搜索词: {title}")
            
            # 检查内容中是否包含搜索词
            content_match = query.lower() in content.lower()
            if content_match:
                app.logger.info(f"内容包含搜索词")
            
            # 如果文件名、标题或内容中包含搜索词
            if file_name_match or title_match or content_match:
                app.logger.info(f"在文件中找到匹配: {file_name}")
                
                # 如果内容中有匹配，提取上下文
                if content_match:
                    query_lower = query.lower()
                    content_lower = content.lower()
                    pos = content_lower.find(query_lower)
                    start = max(0, pos - 50)
                    end = min(len(content), pos + len(query) + 50)
                    
                    # 提取匹配上下文
                    context = content[start:end]
                    if start > 0:
                        context = "..." + context
                    if end < len(content):
                        context = context + "..."
                    
                    app.logger.info(f"提取到内容上下文")
                    
                # 如果内容中没有匹配，但标题中有
                elif title_match:
                    context = f"标题中包含搜索词: {title}"
                    app.logger.info(f"匹配在标题中: {context}")
                
                # 如果内容和标题中都没有匹配，但文件名中有
                else:
                    context = f"文件名中包含搜索词: {file_name}"
                    app.logger.info(f"匹配在文件名中: {context}")
                
                return {
                    "file": file_name,
                    "title": title,
                    "context": context
                }
            
            app.logger.info(f"文件中没有找到匹配: {file_name}")
            return None
            
    except Exception as e:
        app.logger.error(f"搜索文件 {file_path} 失败: {str(e)}")
        # 如果文件读取失败但文件名匹配，仍然返回结果
        if file_name_match:
            return {
                "file": file_name,
                "title": file_name,
                "context": f"文件名中包含搜索词: {file_name} (文件内容读取失败)"
            }
        return None

@app.route('/api/search', methods=['GET'])
def search_articles():
    """
    搜索文章内容的API
    接收查询参数，返回匹配的文章列表
    """
    try:
        # 获取查询参数
        query = request.args.get('query', '')
        app.logger.info(f"收到搜索请求，关键词: '{query}'")
        
        if not query or len(query.strip()) < 1:  # 至少1个字符就开始搜索
            return jsonify([])
        
        # 获取所有文章文件
        article_files = get_article_files()
        app.logger.info(f"找到 {len(article_files)} 个文件进行搜索")
        
        # 在所有文件中进行搜索
        results = []
        for article in article_files:
            file_path = os.path.join(CONTENT_DIR, article)
            result = search_in_file(file_path, query)
            if result:
                results.append(result)
        
        app.logger.info(f"搜索结果: {len(results)} 个匹配项")
        return jsonify(results)
    
    except Exception as e:
        app.logger.error(f"搜索处理出错: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/summary', methods=['POST'])
def generate_summary():
    """
    生成AI总结的接口
    接收文章内容，返回AI生成的总结
    如果有缓存，则直接返回缓存的总结
    """
    try:
        # 获取请求数据
        content = request.json.get('content')
        if not content:
            return jsonify({"error": "内容不能为空"}), 400
        
        # 生成内容哈希作为缓存键
        content_hash = get_content_hash(content)
        
        # 检查缓存
        cache = load_cache()
        cache_exists = content_hash in cache
        
        # 如果缓存存在，模拟流式响应
        if cache_exists:
            app.logger.info(f"使用缓存: {content_hash[:8]}...")
            
            def generate_from_cache():
                # 模拟流式响应的速度
                cached_summary = cache[content_hash]["summary"]
                # 每次发送的字符数
                chunk_size = 5
                
                for i in range(0, len(cached_summary), chunk_size):
                    chunk = cached_summary[i:i+chunk_size]
                    yield f"data: {{\"choices\":[{{\"delta\":{{\"content\":\"{chunk}\"}}}}]}}\n\n"
                    time.sleep(0.05)  # 模拟生成延迟
                
                yield "data: [DONE]\n\n"
            
            return Response(generate_from_cache(), mimetype='text/event-stream')
        
        # 准备AI API请求
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
            "stream": True
        }
        
        # 存储完整的总结文本以便缓存
        complete_summary = ""
        
        # 流式请求到AI API
        def generate():
            nonlocal complete_summary
            
            response = requests.post(
                AI_API["baseURL"],
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {AI_API['apiKey']}"
                },
                json=payload,
                stream=True
            )
            
            # 检查响应状态
            if response.status_code != 200:
                yield f"data: {{\"error\": \"API请求失败: {response.status_code}\"}}\n\n"
                return
            
            # 流式转发响应
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        # 转发到客户端
                        yield f"{line}\n\n"
                        
                        # 收集完整的总结文本
                        data = line[6:]  # 移除 "data: " 前缀
                        if data != '[DONE]':
                            try:
                                json_data = json.loads(data)
                                content_delta = json_data.get('choices', [{}])[0].get('delta', {}).get('content', '')
                                complete_summary += content_delta
                            except json.JSONDecodeError:
                                pass
            
            # 保存到远程缓存
            if complete_summary:
                current_time = time.time()
                save_cache_entry(content_hash, complete_summary, current_time)
                app.logger.info(f"保存到远程缓存: {content_hash[:8]}...")
        
        # 返回流式响应
        return Response(generate(), mimetype='text/event-stream')
    
    except Exception as e:
        app.logger.error(f"处理总结请求出错: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 