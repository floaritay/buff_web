# 部署指南

本指南说明如何在Github Pages上部署前端，并在后端服务器上部署API服务，以确保cookie不被暴露。

## 1. 前端部署（Github Pages）

### 步骤1：修改API_BASE_URL

在 `index.html` 文件中，修改 `API_BASE_URL` 变量为你的后端服务器地址：

```javascript
// 配置后端服务器URL
const API_BASE_URL = 'https://your-backend-server.com'; // 替换为你的后端服务器地址
```

### 步骤2：提交前端代码到Github

1. 创建一个新的Github仓库（或使用现有仓库）
2. 将前端代码（主要是 `index.html` 文件）提交到仓库
3. 在仓库设置中开启Github Pages
4. 选择 `index.html` 所在的分支和目录，点击「部署」

### 步骤3：访问前端

部署完成后，你可以通过Github Pages提供的URL访问前端界面。

## 2. 后端部署（服务器）

### 2.1 使用Vercel部署（推荐）

#### 步骤1：准备GitHub仓库

1. 创建一个新的GitHub仓库（或使用现有仓库）
2. 将后端代码（包括 `app.py`、`buff_buyer.py`、`buff_charm_searcher*.py`、`requirements.txt` 等文件）提交到GitHub仓库

#### 步骤2：部署到Vercel

1. 登录Vercel账号（通过GitHub关联登录）
2. 点击「Add New Project」
3. 选择你的GitHub仓库
4. 点击「Import」
5. 在「Configure Project」页面：
   - 填写「Project Name」
   - 在「Build Command」中填写：`pip install -r requirements.txt`
   - 在「Output Directory」中留空（Vercel会自动处理）
   - 点击「Deploy」

#### 步骤3：配置环境变量

1. 部署完成后，进入Vercel项目的「Settings」页面
2. 点击「Environment Variables」
3. 添加以下环境变量：
   - `BUFF_COOKIE`：你的BUFF网站Cookie
   - `FLASK_APP`：`app.py`
   - `FLASK_ENV`：`production`
   - `PORT`：`5000`
4. 点击「Save」

#### 步骤4：获取Vercel部署URL

部署完成后，Vercel会提供一个URL，例如 `https://your-project.vercel.app`，这就是你的后端API地址。

### 2.2 使用其他服务器部署

#### 步骤1：准备服务器

1. 选择一个云服务器（如阿里云、腾讯云等）
2. 安装Python 3.6+
3. 安装Git

#### 步骤2：克隆代码

```bash
git clone https://github.com/your-username/your-repo.git
cd your-repo
```

#### 步骤3：安装依赖

```bash
pip install -r requirements.txt
```

#### 步骤4：配置环境变量

1. 复制 `.env.example` 文件为 `.env`：

```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，填写实际值：

```
# BUFF网站的Cookie
BUFF_COOKIE=your_buff_cookie_here

# 后端服务器配置
FLASK_APP=app.py
FLASK_ENV=production

# 服务器端口
PORT=5000
```

#### 步骤5：启动后端服务

##### 使用Flask内置服务器（仅用于测试）

```bash
python app.py
```

##### 使用Gunicorn（推荐用于生产环境）

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

#### 步骤6：配置域名和HTTPS

1. 为后端服务器配置域名
2. 开启HTTPS（推荐使用Let's Encrypt获取免费SSL证书）

## 3. 安全注意事项

1. **不要将cookie提交到版本控制系统**：.env文件已经被添加到.gitignore中，确保不要将其提交。
2. **使用HTTPS**：确保前端和后端都使用HTTPS，防止cookie被窃取。
3. **定期更新cookie**：BUFF网站的cookie有一定的有效期，过期后需要重新获取并更新环境变量。
4. **限制服务器访问**：可以配置防火墙，只允许Gitee Pages的IP访问后端API。

## 4. 故障排查

### 前端无法连接后端

- 检查API_BASE_URL是否正确
- 检查后端服务器是否正在运行
- 检查后端服务器的防火墙设置
- 检查CORS配置是否正确

### Cookie无效

- 检查.env文件中的BUFF_COOKIE是否正确
- 尝试重新获取BUFF网站的cookie
- 检查后端服务器的环境变量是否正确加载

### 部署成功但功能无法使用

- 检查后端服务器的日志
- 检查前端浏览器的控制台日志
- 确保后端服务器可以访问BUFF网站

## 5. 总结

通过将前端部署在Gitee Pages，后端部署在独立服务器上，并使用环境变量存储cookie，可以确保cookie不被暴露，同时提供良好的用户体验。

---

**注意**：本部署方式适用于个人使用，如需在生产环境中大规模部署，建议进一步加强安全措施，如添加认证机制、使用数据库存储配置等。