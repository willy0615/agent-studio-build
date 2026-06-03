# API Key 配置指南

## 重要提示

**⚠️ .env 文件已被 .gitignore 排除，不会被 Git 追踪**

---

## 配置方式（推荐顺序）

### 方式1：系统环境变量（推荐生产环境）

**Windows PowerShell**:
```powershell
# 临时设置（当前会话）
$env:NVIDIA_API_KEY="nvapi-your-key-here"

# 永久设置（用户级别）
[Environment]::SetEnvironmentVariable("NVIDIA_API_KEY", "nvapi-your-key-here", "User")

# 永久设置（系统级别，需要管理员）
[Environment]::SetEnvironmentVariable("NVIDIA_API_KEY", "nvapi-your-key-here", "Machine")
```

**Linux/Mac**:
```bash
# 临时设置
export NVIDIA_API_KEY="nvapi-your-key-here"

# 永久设置（添加到 ~/.bashrc 或 ~/.zshrc）
echo 'export NVIDIA_API_KEY="nvapi-your-key-here"' >> ~/.bashrc
source ~/.bashrc
```

---

### 方式2：.env 文件（开发环境）

1. 复制模板文件：
   ```bash
   cp .env.example .env
   ```

2. 编辑 `.env` 文件，填入你的 API Key：
   ```
   NVIDIA_API_KEY=nvapi-your-key-here
   ```

---

## 获取 API Key

访问 [NVIDIA NIM](https://build.nvidia.com/) 注册并获取 API Key。

---

## 安全注意事项

1. **永远不要提交 .env 文件到 Git**
   - .gitignore 已配置排除 .env
   - 如有疑问，运行：`git status` 确认 .env 未被追踪

2. **不要在代码中硬编码 API Key**
   - 已通过 config.py 从环境变量读取

3. **生产环境建议**
   - 使用系统环境变量
   - 或使用密钥管理服务（Azure Key Vault、AWS Secrets Manager）

4. **如果密钥泄露**
   - 立即在 NVIDIA NIM 平台重新生成新密钥
   - 更新环境变量或 .env 文件

---

## 验证配置

运行以下命令验证配置是否正确：

```bash
cd E:\AgentProject
python -c "from app.config import NVIDIA_API_KEY; print('API Key configured:', 'Yes' if NVIDIA_API_KEY else 'No')"
```

---

## 当前状态

✅ .gitignore 已配置
✅ .env.example 模板已创建
✅ config.py 支持环境变量优先
⚠️ .env 文件包含实际密钥（仅限本地开发，不要共享或提交）
