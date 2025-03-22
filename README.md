# 文章管理系统

一个支持Markdown和LaTeX的前端文章管理系统，具有AI自动总结功能。

## 功能特点

- Markdown渲染与编辑
- LaTeX公式支持
- 代码高亮
- 可折叠侧边栏导航
- AI自动总结文章内容
- 双击编辑功能

## 系统结构

- 前端：HTML5, JavaScript, CSS
- 后端：Python Flask (用于AI总结功能)

## 使用说明

### 启动后端服务

1. 确保已安装Python 3.6+
2. 进入backend目录
3. 安装依赖: `pip install -r requirements.txt`
4. 运行服务: `python app.py` 或双击 `start.bat`

### 启动前端

使用任意HTTP服务器启动前端，例如：

```
# 如果已安装Python
python -m http.server

# 如果已安装Node.js
npx serve
```

然后在浏览器中访问: http://localhost:8000 (或其他端口)

### 使用方法

- 通过左侧导航栏浏览不同文章
- AI会自动总结当前页面内容
- 双击文章区域可进入编辑模式
- 使用Ctrl+S保存编辑，按Esc退出编辑模式

## 注意事项

- 后端服务必须在前端访问之前启动
- 确保后端API地址在app.js中配置正确
- 默认API地址为: http://localhost:5000 