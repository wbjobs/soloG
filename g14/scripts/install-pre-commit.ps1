# 安装代码审查 pre-commit hook
# 使用方法: .\scripts\install-pre-commit.ps1

Write-Host "🔧 安装代码审查 pre-commit hook..." -ForegroundColor Cyan

# 检查是否在 git 仓库中
if (-not (Test-Path ".git")) {
    Write-Host "❌ 错误: 未找到 .git 目录，请在 git 仓库根目录运行此脚本" -ForegroundColor Red
    exit 1
}

# 创建 hooks 目录
$hooksDir = ".git\hooks"
if (-not (Test-Path $hooksDir)) {
    New-Item -ItemType Directory -Path $hooksDir -Force | Out-Null
}

# 复制 pre-commit 脚本
$sourceHook = ".\hooks\pre-commit"
$destHook = "$hooksDir\pre-commit"

if (Test-Path $sourceHook) {
    Copy-Item $sourceHook $destHook -Force
    Write-Host "✅ pre-commit 脚本已复制" -ForegroundColor Green
} else {
    Write-Host "❌ 错误: 未找到 $sourceHook" -ForegroundColor Red
    exit 1
}

# 设置执行权限
& icacls $destHook /grant:r ":(OI)(CI)(RX)" | Out-Null

# 创建环境变量配置文件示例
$envExample = @'
# code-review-cli 环境变量配置
# 复制此文件为 .env 并根据需要修改

# LLM 模型文件路径 (.gguf 格式)
CODE_REVIEW_MODEL=./models/code-review-model.gguf

# 是否使用模拟模式 (true/false)
CODE_REVIEW_MOCK=true

# 启用的规则集 (逗号分隔)
CODE_REVIEW_RULESETS=pep8,eslint

# 严重程度阈值: critical, high, medium, low, info
# 高于或等于此阈值的问题会阻止提交
CODE_REVIEW_SEVERITY=low

# 是否自动修复 (true/false)
CODE_REVIEW_AUTOFIX=false
'@

$envExample | Out-File -FilePath ".env.example" -Encoding utf8
Write-Host "✅ 环境变量配置示例已创建: .env.example" -ForegroundColor Green

Write-Host ""
Write-Host "🎉 pre-commit hook 安装完成！" -ForegroundColor Green
Write-Host ""
Write-Host "接下来的步骤:" -ForegroundColor Yellow
Write-Host "1. 复制 .env.example 为 .env 并配置你的模型路径"
Write-Host "2. 设置环境变量: `$env:CODE_REVIEW_MODEL='./models/your-model.gguf'`"
Write-Host "3. 提交代码时会自动运行代码审查"
Write-Host "4. 如需临时跳过检查，使用: git commit --no-verify"
Write-Host ""
Write-Host "测试 hook:" -ForegroundColor Yellow
Write-Host "  python $destHook examples/bad_code.py"
