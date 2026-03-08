# 部署指南

本指南说明如何在Github Pages上部署前端，并在Vercel上部署后端API服务，以确保cookie不被暴露。

## 1. 前端部署（Github Pages）

### 步骤1：修改API_BASE_URL

在 `index.html` 文件中，修改 `API_BASE_URL` 变量为你的Vercel部署地址：

```javascript
// 配置后端服务器URL
const API_BASE_URL = 'https://your-project.vercel.app'; // 替换为你的Vercel部署URL
```

### 步骤2：提交前端代码到Github

1. 创建一个新的Github仓库（或使用现有仓库）
2. 将前端代码（主要是 `index.html` 文件）提交到仓库
3. 在仓库设置中开启Github Pages
4. 选择 `index.html` 所在的分支和目录，点击「部署」

### 步骤3：访问前端

部署完成后，你可以通过Github Pages提供的URL访问前端界面。

## 2. 后端部署（Vercel）

### 步骤1：准备GitHub仓库

1. 创建一个新的GitHub仓库（或使用现有仓库）
2. 将后端代码提交到GitHub仓库，包括：
   - `app.py` - Flask Web应用主文件
   - `buff_buyer.py` - 涂鸦购买脚本
   - `buff_charm_searcher_austin.py` - Austin挂件搜枪脚本
   - `buff_charm_searcher_budapest.py` - Budapest挂件搜枪脚本
   - `requirements.txt` - Python依赖包
   - `vercel.json` - Vercel配置文件

### 步骤2：部署到Vercel

1. 登录Vercel账号（通过GitHub关联登录）
2. 点击「Add New Project」
3. 选择你的GitHub仓库
4. 点击「Import」
5. 在「Configure Project」页面：
   - 填写「Project Name」
   - 在「Build Command」中填写：`pip install -r requirements.txt`
   - 在「Output Directory」中留空（Vercel会自动处理）
   - 点击「Deploy」

### 步骤3：配置环境变量

1. 部署完成后，进入Vercel项目的「Settings」页面
2. 点击「Environment Variables」
3. 添加以下环境变量：
   - `SECRET_KEY`：用于Flask会话加密的密钥
   - `FLASK_APP`：`app.py`
   - `FLASK_ENV`：`production`
   - `PORT`：`5000`
4. 点击「Save」

### 步骤4：获取Vercel部署URL

部署完成后，Vercel会提供一个URL，例如 `https://your-project.vercel.app`，这就是你的后端API地址。

## 3. 代码适配说明

为了在Vercel上成功部署，项目代码做了以下适配：

### 3.1 后端代码适配

1. **修改了index函数**：
   - 原来使用 `render_template` 渲染模板，在Vercel上可能找不到模板文件
   - 修改为直接读取并返回 `index.html` 文件的内容
   - 添加了详细的错误处理和调试信息，便于排查问题

2. **添加了用户认证系统**：
   - 使用 `Flask-Login` 实现用户登录/注册/注销功能
   - 为每个用户创建独立的cookie存储空间，避免多个用户共用cookie
   - 修改了cookie存储方式，从环境变量改为用户独立存储

3. **修复了线程中的用户认证问题**：
   - 在Flask中，`current_user` 是一个上下文变量，只能在请求上下文中使用
   - 修改为在请求处理函数中获取 `user_id`，然后将其作为参数传递给线程函数
   - 确保在单独线程中也能正确处理用户认证

4. **添加了Vercel配置文件**：
   - 创建了 `vercel.json` 文件，配置Vercel如何构建和部署Flask应用
   - 指定了 `app.py` 作为应用入口

5. **更新了依赖**：
   - 在 `requirements.txt` 中添加了 `Flask-Login>=0.6.2` 依赖

### 3.2 前端代码适配

1. **修改了API调用**：
   - 将所有API调用的基础URL改为 `API_BASE_URL` 变量
   - 添加了 `credentials: 'include'`，确保认证信息能够正确传递

2. **添加了用户认证界面**：
   - 添加了登录/注册模态框
   - 在页面头部显示用户信息和登录/注销按钮
   - 实现了用户状态检查和认证相关的JavaScript函数

3. **修复了SSE（Server-Sent Events）连接**：
   - 由于 `EventSource` 不支持设置 `credentials` 选项
   - 使用 `fetch` API和 `ReadableStream` 模拟SSE，确保认证信息能够正确传递

4. **添加了cookie输入模态框**：
   - 当登录失败时，自动弹出cookie输入模态框
   - 实现了cookie保存功能，将cookie发送到后端存储

## 4. 安全注意事项

1. **不要将cookie提交到版本控制系统**：.env文件已经被添加到.gitignore中，确保不要将其提交。
2. **使用HTTPS**：确保前端和后端都使用HTTPS，防止cookie被窃取。
3. **定期更新cookie**：BUFF网站的cookie有一定的有效期，过期后需要重新获取并更新。
4. **限制服务器访问**：可以配置Vercel的访问控制，只允许特定域名访问后端API。
5. **数据安全**：用户数据存储在服务器内存中，服务器重启后数据会丢失，确保不要存储重要数据。

## 5. 故障排查

### 前端无法连接后端

- 检查 `API_BASE_URL` 是否正确
- 检查Vercel部署是否成功
- 检查Vercel项目的日志，查看是否有错误信息
- 检查CORS配置是否正确

### Cookie无效

- 尝试重新获取BUFF网站的cookie
- 检查前端是否正确弹出cookie输入模态框
- 检查后端是否正确保存cookie

### 部署成功但功能无法使用

- 检查Vercel项目的日志
- 检查前端浏览器的控制台日志
- 确保Vercel服务器可以访问BUFF网站
- 检查环境变量是否正确设置

## 6. 总结

通过将前端部署在Gitee Pages，后端部署在Vercel上，并使用用户认证系统实现cookie的独立存储，可以确保cookie不被暴露，同时提供良好的用户体验。

项目代码已经做了必要的适配，确保在Vercel上能够正常运行。如果在部署过程中遇到任何问题，请参考故障排查部分或查看Vercel的部署日志。

---

**注意**：本部署方式适用于个人使用，如需在生产环境中大规模部署，建议进一步加强安全措施，如添加数据库存储、实现更完善的用户管理功能等。