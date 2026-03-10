# BUFF Web适配版本说明

## 新版基础文件与Web适配版本的差异

本文档详细说明 `d:\Buff\new\` 目录下的新版基础文件与 `d:\Buff\` 目录下的Web适配版本之间的代码差异。

### 核心差异

| 差异点 | 新版基础文件 (d:\Buff\new\) | Web适配版本 (d:\Buff\) |
|--------|---------------------------|------------------------|
| Cookie存储方式 | 文件存储 (`cookie.txt`) | 环境变量存储 (`BUFF_COOKIE`) |
| 存储位置 | 脚本所在目录的 `cookie.txt` 文件 | 系统环境变量 |
| 加载方式 | 从文件读取 | 从环境变量读取 |

### 具体文件对比

#### 1. buff_buyer.py

**新版基础文件**：
- `save_cookie` 函数：将cookie保存到 `cookie.txt` 文件
- `load_cookie` 函数：从 `cookie.txt` 文件加载cookie

**Web适配版本**：
- `save_cookie` 函数：将cookie保存到 `BUFF_COOKIE` 环境变量
- `load_cookie` 函数：从 `BUFF_COOKIE` 环境变量加载cookie

#### 2. buff_charm_searcher_austin.py

**新版基础文件**：
- `save_cookie` 函数：将cookie保存到 `cookie.txt` 文件
- `load_cookie` 函数：从 `cookie.txt` 文件加载cookie

**Web适配版本**：
- `save_cookie` 函数：将cookie保存到 `BUFF_COOKIE` 环境变量
- `load_cookie` 函数：从 `BUFF_COOKIE` 环境变量加载cookie

#### 3. buff_charm_searcher_budapest.py

**新版基础文件**：
- `save_cookie` 函数：将cookie保存到 `cookie.txt` 文件
- `load_cookie` 函数：从 `cookie.txt` 文件加载cookie

**Web适配版本**：
- `save_cookie` 函数：将cookie保存到 `BUFF_COOKIE` 环境变量
- `load_cookie` 函数：从 `BUFF_COOKIE` 环境变量加载cookie

### 功能一致性

除了Cookie存储方式的差异外，两个版本的其他功能完全一致：

1. **CSRF token处理**：两个版本都实现了相同的CSRF token提取和使用逻辑
2. **购买流程**：两个版本的购买流程完全相同
3. **反爬措施**：两个版本都包含相同的反爬措施
4. **错误处理**：两个版本的错误处理机制相同
5. **请求头设置**：两个版本使用相同的请求头设置

### Web适配的优势

1. **安全性**：环境变量存储cookie比文件存储更安全，避免了敏感信息写入磁盘
2. **部署便利性**：在服务器环境中，环境变量更容易配置和管理
3. **多用户支持**：环境变量可以为不同用户设置不同的cookie值
4. **容器化支持**：在Docker等容器环境中，环境变量是标准的配置方式

### 使用方法

1. **Web适配版本**：通过环境变量 `BUFF_COOKIE` 传入cookie值
2. **新版基础文件**：首次运行时手动输入cookie，后续自动保存到 `cookie.txt` 文件

### 注意事项

- Web适配版本依赖环境变量 `BUFF_COOKIE`，确保在运行前设置此环境变量
- 新版基础文件会在脚本所在目录创建 `cookie.txt` 文件存储cookie
- 两个版本的核心功能完全相同，选择哪个版本取决于部署环境和个人偏好
