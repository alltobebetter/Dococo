document.addEventListener('DOMContentLoaded', function() {
    // 初始化应用
    initApp();
    
    // 监听哈希变化以实现路由
    window.addEventListener('hashchange', handleRouteChange);
    
    // 初始化侧边栏切换功能
    initSidebarToggle();
    
    // 初始化直接编辑功能
    initDirectEditFeature();
    
    // 初始化搜索功能
    initSearchFeature();
    
    // 防止左侧导航栏滚动传播到右侧内容
    preventScrollPropagation();
});

// 当前文件路径
let currentFilePath = '';
// 是否处于编辑状态
let isEditing = false;
// 后端API地址
const BACKEND_API = {
    baseURL: '',  // 空字符串表示使用相对路径
    summaryEndpoint: '/api/summary',
    searchEndpoint: '/api/search'
};
// 搜索防抖计时器
let searchDebounceTimer = null;

/**
 * 初始化应用
 */
function initApp() {
    // 加载content.md文件来获取目录和标题
    loadContentFile();
    
    // 处理初始路由
    handleRouteChange();
}

/**
 * 初始化直接编辑功能
 */
function initDirectEditFeature() {
    const articleContainer = document.getElementById('article-container');
    
    // 默认不可编辑
    articleContainer.contentEditable = false;
    
    // 监听双击事件进入编辑模式
    articleContainer.addEventListener('dblclick', function(e) {
        // 如果不是编辑模式，则进入编辑模式
        if (!isEditing) {
            isEditing = true;
            articleContainer.contentEditable = true;
            articleContainer.classList.add('editable');
            
            // 为了确保能够输入文字，需要手动设置焦点
            setTimeout(() => {
                // 聚焦到被双击的位置
                const selection = window.getSelection();
                const range = document.createRange();
                range.setStart(e.target, 0);
                selection.removeAllRanges();
                selection.addRange(range);
            }, 0);
        }
    });
    
    // 内容区域失去焦点时
    articleContainer.addEventListener('blur', function() {
        // 短暂延迟，避免与点击链接冲突
        setTimeout(() => {
            if (isEditing) {
                exitEditMode();
            }
        }, 100);
    });
    
    // 监听键盘事件，Ctrl+S保存，Escape退出
    document.addEventListener('keydown', function(e) {
        if (!isEditing) return;
        
        if (e.ctrlKey && e.key === 's') {
            e.preventDefault(); // 阻止浏览器默认保存行为
            saveCurrentContent();
            exitEditMode();
        } else if (e.key === 'Escape') {
            e.preventDefault();
            exitEditMode();
        }
    });
    
    // 退出编辑模式
    function exitEditMode() {
        isEditing = false;
        articleContainer.contentEditable = false;
        articleContainer.classList.remove('editable');
    }
    
    // 保存当前内容
    function saveCurrentContent() {
        // 获取编辑后的内容
        const editedContent = articleContainer.innerHTML;
        
        // 转换回Markdown
        let markdown = htmlToMarkdown(editedContent);
        
        // 保存文件
        saveMarkdownFile(currentFilePath, markdown);
    }
}

/**
 * 将HTML转换回Markdown (简化版)
 * @param {string} html - HTML内容
 * @returns {string} - Markdown内容
 */
function htmlToMarkdown(html) {
    // 创建临时容器来处理HTML
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    
    // 提取文本内容 (简单版本)
    const text = tempDiv.innerText;
    
    // 实际应用中，这里应该使用更复杂的转换逻辑
    // 例如使用 turndown.js 等库来正确处理格式
    
    return text;
}

/**
 * 保存Markdown文件
 * @param {string} filePath - 文件路径
 * @param {string} content - 文件内容
 */
function saveMarkdownFile(filePath, content) {
    // 在实际应用中，这里应该发送请求到服务器保存文件
    // 由于这是纯前端应用，我们可以使用localStorage模拟保存
    // 或者使用下载功能让用户手动保存文件
    
    // 提示用户保存成功
    alert('内容已保存！\n\n在真实环境中，这里会将编辑后的内容保存到服务器。\n当前为演示模式，内容不会真正保存。请手动复制需要保存的内容。');
    
    // 创建下载链接（可选功能）
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filePath.split('/').pop();
    a.click();
    URL.revokeObjectURL(url);
}

/**
 * 初始化侧边栏切换功能
 */
function initSidebarToggle() {
    const toggleButton = document.getElementById('toggle-sidebar');
    const sidebar = document.getElementById('sidebar');
    const contentArea = document.getElementById('content-area');
    
    // 检查是否有保存的侧边栏状态
    const isSidebarCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    
    // 应用保存的状态
    if (isSidebarCollapsed) {
        sidebar.classList.add('collapsed');
        contentArea.classList.add('expanded');
        toggleButton.classList.add('active');
    }
    
    // 添加点击事件监听
    toggleButton.addEventListener('click', function() {
        // 切换侧边栏状态
        sidebar.classList.toggle('collapsed');
        contentArea.classList.toggle('expanded');
        toggleButton.classList.toggle('active');
        
        // 保存状态到本地存储
        const isCollapsed = sidebar.classList.contains('collapsed');
        localStorage.setItem('sidebarCollapsed', isCollapsed);
    });
}

/**
 * 加载content.md文件获取目录和标题
 */
function loadContentFile() {
    console.log('尝试加载content.md文件');
    fetch('/content.md')
        .then(response => {
            if (!response.ok) {
                console.error(`content.md加载失败，状态码: ${response.status}`);
                throw new Error('content.md文件加载失败');
            }
            return response.text();
        })
        .then(content => {
            console.log(`成功加载content.md，内容长度: ${content.length}`);
            parseContentFile(content);
        })
        .catch(error => {
            console.error(`content.md加载出错: ${error.message}`);
            document.getElementById('toc-list').innerHTML = `
                <li class="error">目录加载失败：${error.message}</li>
            `;
        });
}

/**
 * 解析content.md文件内容
 * @param {string} content - content.md的内容
 */
function parseContentFile(content) {
    // 将内容按行分割
    const lines = content.trim().split('\n');
    
    if (lines.length === 0) {
        return;
    }
    
    // 第一行是标题，格式为 [标题]
    const titleMatch = lines[0].match(/\[(.*?)\]/);
    if (titleMatch && titleMatch[1]) {
        document.getElementById('site-title').textContent = titleMatch[1];
        document.title = titleMatch[1]; // 更新网页标题
    }
    
    // 其余行是目录项，格式为 [显示内容][相对路径]
    const menuItems = [];
    for (let i = 1; i < lines.length; i++) {
        // 匹配 [显示内容][路径] 格式
        const match = lines[i].match(/\[(.*?)\]\[(.*?)\]/);
        if (match) {
            const displayText = match[1];
            const path = match[2];
            
            if (path) {
                // 如果显示内容为空，则使用文件名作为显示内容
                let label = displayText;
                if (!displayText) {
                    // 从路径中提取文件名，并去掉扩展名
                    const fileName = path.split('/').pop().split('.')[0];
                    label = fileName.charAt(0).toUpperCase() + fileName.slice(1); // 首字母大写
                }
                
                menuItems.push({ 
                    label: label, 
                    path: path 
                });
            }
        }
    }
    
    // 生成目录HTML
    createTocMenu(menuItems);
}

/**
 * 根据菜单项创建目录
 * @param {Array} menuItems - 目录项
 */
function createTocMenu(menuItems) {
    const tocList = document.getElementById('toc-list');
    tocList.innerHTML = '';
    
    menuItems.forEach(item => {
        const li = document.createElement('li');
        
        // 构建路由路径
        let routePath;
        if (item.path.endsWith('.md')) {
            // 如果以.md结尾，去掉扩展名
            routePath = '#/' + item.path.slice(0, -3);
        } else {
            routePath = '#/' + item.path;
        }
        
        li.innerHTML = `<a href="${routePath}">${item.label}</a>`;
        tocList.appendChild(li);
        
        // 为移动端添加点击事件，自动隐藏侧边栏
        const link = li.querySelector('a');
        link.addEventListener('click', function(e) {
            console.log('目录项被点击');
            // 检查是否为移动设备（屏幕宽度小于768px）
            if (window.innerWidth <= 768) {
                console.log('移动端检测到点击，隐藏侧边栏');
                // 延迟执行以确保路由变化先发生
                setTimeout(function() {
                    // 自动隐藏侧边栏
                    const sidebar = document.getElementById('sidebar');
                    const contentArea = document.getElementById('content-area');
                    const toggleButton = document.getElementById('toggle-sidebar');
                    
                    sidebar.classList.add('collapsed');
                    contentArea.classList.add('expanded');
                    toggleButton.classList.add('active');
                    
                    // 保存状态到本地存储
                    localStorage.setItem('sidebarCollapsed', 'true');
                }, 50);
            }
        });
    });
    
    // 更新当前活动链接
    updateActiveLink();
}

/**
 * 更新当前活动链接的样式
 */
function updateActiveLink() {
    const currentHash = window.location.hash;
    
    // 清除之前的活动状态
    const links = document.querySelectorAll('#toc-list a');
    links.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === currentHash) {
            link.classList.add('active');
        }
    });
}

/**
 * 处理路由变化
 */
function handleRouteChange() {
    const articleContainer = document.getElementById('article-container');
    const aiSummaryContent = document.getElementById('ai-summary-content');
    
    articleContainer.innerHTML = '<div class="loading">加载中...</div>';
    
    // 重置编辑状态
    isEditing = false;
    articleContainer.classList.remove('editable');
    
    // 隐藏AI总结区域
    aiSummaryContent.classList.add('hidden');
    aiSummaryContent.innerHTML = '';
    
    // 更新活动链接样式
    updateActiveLink();
    
    // 获取当前路由，格式为 "#/filename"
    let hash = window.location.hash;
    console.log(`当前路由: ${hash}`);
    
    // 如果没有路由或者是首页，默认加载 home.md
    if (!hash || hash === '#/' || hash === '#/home') {
        hash = '#/home';
        loadMarkdownFile('/home.md');
        currentFilePath = '/home.md';
    } else {
        // 从路由中提取文件名
        let fileName = hash.substring(2);
        
        // 如果没有扩展名，则添加.md
        if (!fileName.includes('.')) {
            fileName += '.md';
        }
        
        // 确保文件名以/开头
        if (!fileName.startsWith('/')) {
            fileName = '/' + fileName;
        }
        
        console.log(`准备加载文件: ${fileName}`);
        loadMarkdownFile(fileName);
        currentFilePath = fileName;
    }
}

/**
 * 加载Markdown文件
 * @param {string} fileName - 文件名
 */
function loadMarkdownFile(fileName) {
    // 确保文件名以/开头，确保绝对路径
    const filePath = fileName.startsWith('/') ? fileName : `/${fileName}`;
    
    console.log(`尝试加载文件: ${filePath}`);
    
    fetch(filePath)
        .then(response => {
            if (!response.ok) {
                console.error(`文件加载失败，状态码: ${response.status}`);
                throw new Error(`文件加载失败: ${fileName}`);
            }
            return response.text();
        })
        .then(markdownContent => {
            console.log(`成功加载文件，内容长度: ${markdownContent.length}`);
            renderMarkdown(markdownContent);
            // 当文章渲染完成后，自动进行总结
            setTimeout(() => {
                autoGenerateSummary();
            }, 500); // 延迟500ms确保文章内容已完全渲染
        })
        .catch(error => {
            console.error(`加载文件出错: ${error.message}`);
            document.getElementById('article-container').innerHTML = `
                <div class="error">
                    <h2>加载失败</h2>
                    <p>${error.message}</p>
                    <p>请确认文件存在并且可访问。</p>
                </div>
            `;
        });
}

/**
 * 渲染Markdown内容
 * @param {string} markdownContent - Markdown文本内容
 */
function renderMarkdown(markdownContent) {
    // 保存数学公式，防止被marked解析
    const mathExpressions = [];
    let processedMarkdown = markdownContent.replace(/(\$\$[\s\S]+?\$\$|\$[\s\S]+?\$)/g, function(match) {
        const id = mathExpressions.length;
        mathExpressions.push(match);
        return `MATH_EXPRESSION_${id}`;
    });
    
    // 配置marked选项
    marked.setOptions({
        highlight: function(code, lang) {
            // 使用highlight.js进行代码高亮
            if (lang && hljs.getLanguage(lang)) {
                return hljs.highlight(code, { language: lang }).value;
            }
            return hljs.highlightAuto(code).value;
        },
        breaks: true,
        gfm: true
    });
    
    // 将Markdown转换为HTML
    let htmlContent = marked.parse(processedMarkdown);
    
    // 恢复数学公式
    htmlContent = htmlContent.replace(/MATH_EXPRESSION_(\d+)/g, function(match, id) {
        return mathExpressions[parseInt(id)];
    });
    
    // 显示HTML内容
    document.getElementById('article-container').innerHTML = htmlContent;
    
    // 渲染LaTeX公式
    renderMathInElement(document.getElementById('article-container'), {
        delimiters: [
            {left: '$$', right: '$$', display: true},
            {left: '$', right: '$', display: false},
            {left: '\\(', right: '\\)', display: false},
            {left: '\\[', right: '\\]', display: true}
        ],
        throwOnError: false,
        output: 'html',
        trust: true,
        strict: false
    });
    
    // 为所有链接添加目标属性
    const links = document.querySelectorAll('#article-container a');
    links.forEach(link => {
        // 如果是内部链接（以#开头），不做处理
        if (!link.getAttribute('href').startsWith('#')) {
            link.setAttribute('target', '_blank');
            link.setAttribute('rel', 'noopener noreferrer');
        }
    });
}

/**
 * 自动生成内容总结
 */
function autoGenerateSummary() {
    const articleContainer = document.getElementById('article-container');
    const aiSummaryContent = document.getElementById('ai-summary-content');
    
    // 如果是编辑模式，不生成总结
    if (isEditing) {
        return;
    }
    
    // 获取文章内容
    const articleContent = articleContainer.innerText;
    
    // 如果内容太短则不生成总结
    if (articleContent.length < 100) {
        return;
    }
    
    // 显示总结界面
    aiSummaryContent.innerHTML = '<div class="summary-loading">生成中...</div>';
    aiSummaryContent.classList.remove('hidden');
    
    // 请求总结生成
    fetchSummaryFromBackend(articleContent)
        .then(summary => {
            aiSummaryContent.innerHTML = summary;
            aiSummaryContent.classList.remove('hidden');
        })
        .catch(error => {
            console.error('AI总结失败:', error);
            aiSummaryContent.innerHTML = '<div class="summary-error">总结生成失败</div>';
        });
}

/**
 * 从后端请求AI总结
 * @param {string} content - 需要总结的内容
 * @returns {Promise<string>} - 返回AI总结的内容
 */
function fetchSummaryFromBackend(content) {
    console.log('发送内容到后端，长度:', content.length);
    
    return new Promise((resolve, reject) => {
        // 显示进度提示
        const aiSummaryContent = document.getElementById('ai-summary-content');
        aiSummaryContent.innerHTML = '<div class="summary-loading">AI正在思考中...</div>';
        aiSummaryContent.classList.remove('hidden');
        
        // 构建API请求
        const apiURL = `${BACKEND_API.baseURL}${BACKEND_API.summaryEndpoint}`;
        console.log('请求URL:', apiURL);
        
        // 发送POST请求到后端
        fetch(apiURL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ content: content })
        })
        .then(response => {
            if (!response.ok) {
                console.error('后端请求失败:', response.status);
                throw new Error(`后端请求失败: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                throw new Error(`AI API错误: ${data.error}`);
            }
            
            if (data.summary) {
                resolve(data.summary);
            } else {
                throw new Error('无法获取AI总结');
            }
        })
        .catch(error => {
            console.error('AI总结失败:', error);
            reject(error);
        });
    });
}

/**
 * 初始化搜索功能
 */
function initSearchFeature() {
    const searchInput = document.getElementById('search-input');
    const searchResults = document.getElementById('search-results');
    
    // 实时搜索（输入时带防抖）
    searchInput.addEventListener('input', function() {
        const query = this.value.trim();
        
        // 清除之前的防抖计时器
        if (searchDebounceTimer) {
            clearTimeout(searchDebounceTimer);
        }
        
        // 如果搜索框为空，隐藏结果
        if (!query) {
            searchResults.classList.add('hidden');
            searchResults.innerHTML = '';
            return;
        }
        
        // 设置防抖计时器，300ms后执行搜索
        searchDebounceTimer = setTimeout(() => {
            performSearch(query);
        }, 300);
    });
    
    // 点击其他区域隐藏搜索结果
    document.addEventListener('click', function(e) {
        if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
            searchResults.classList.add('hidden');
        }
    });
    
    // 搜索框获得焦点时，如果有内容，显示结果
    searchInput.addEventListener('focus', function() {
        if (this.value.trim() && searchResults.children.length > 0) {
            searchResults.classList.remove('hidden');
        }
    });
}

/**
 * 执行搜索功能
 * @param {string} query - 查询字符串
 */
function performSearch(query) {
    const searchResults = document.getElementById('search-results');
    
    if (!query || query.trim() === '') {
        searchResults.innerHTML = '';
        searchResults.classList.add('hidden');
        return;
    }
    
    // 显示搜索结果区域
    searchResults.classList.remove('hidden');
    searchResults.innerHTML = '<div class="search-loading">搜索中...</div>';
    
    // 构建API URL
    const searchUrl = `${BACKEND_API.baseURL}${BACKEND_API.searchEndpoint}?query=${encodeURIComponent(query)}`;
    console.log('执行搜索，URL:', searchUrl);
    
    // 发送搜索请求
    fetch(searchUrl)
        .then(response => {
            if (!response.ok) {
                throw new Error(`搜索请求失败: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.length === 0) {
                searchResults.innerHTML = '<div class="no-results">未找到结果</div>';
                return;
            }
            
            // 构建搜索结果HTML
            let resultsHtml = '<ul class="search-results-list">';
            
            data.forEach(result => {
                resultsHtml += `
                    <li class="search-result-item">
                        <a href="#/${result.file.replace('.md', '')}" class="search-result-link">
                            <h3>${result.title}</h3>
                            <p>${result.context}</p>
                        </a>
                    </li>
                `;
            });
            
            resultsHtml += '</ul>';
            searchResults.innerHTML = resultsHtml;
            
            // 为搜索结果添加点击事件
            document.querySelectorAll('.search-result-link').forEach(link => {
                link.addEventListener('click', function() {
                    searchResults.classList.add('hidden');
                    document.getElementById('search-input').value = '';
                });
            });
        })
        .catch(error => {
            console.error('搜索失败:', error);
            searchResults.innerHTML = '<div class="search-error">搜索失败</div>';
        });
}

/**
 * 防止左侧栏滚动事件传播到右侧内容区域
 */
function preventScrollPropagation() {
    const tocNav = document.getElementById('toc-nav');
    
    if (tocNav) {
        tocNav.addEventListener('wheel', function(event) {
            const maxScrollTop = tocNav.scrollHeight - tocNav.clientHeight;
            const currentScrollTop = tocNav.scrollTop;
            
            // 到达顶部且继续向上滚动，或到达底部且继续向下滚动时，阻止事件传播
            if ((currentScrollTop <= 0 && event.deltaY < 0) || 
                (currentScrollTop >= maxScrollTop && event.deltaY > 0)) {
                event.preventDefault();
                event.stopPropagation();
            }
        }, { passive: false });
    }
} 