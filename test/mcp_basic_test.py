"""基础 MCP 测试 - 不带环境变量测试

测试 amap-mcp-server 在缺少环境变量时的行为
"""

import subprocess
import sys
import time

print("=" * 60)
print("🔍 测试 amap-mcp-server (不带环境变量)...")
print("=" * 60)

print("\n1️⃣ 启动 amap-mcp-server (不带 AMAP_MAPS_API_KEY)...")
process = subprocess.Popen(
    "uvx amap-mcp-server",
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    shell=True
)

print("   ⏳ 等待 5 秒...")
time.sleep(5)

# 检查进程状态
poll = process.poll()
print(f"\n2️⃣ 进程状态: poll() = {poll}")

if poll is not None:
    print(f"   退出码: {process.returncode}")
    print("\n   📋 stderr 输出:")
    stderr = process.stderr.read()
    print(f"   {stderr}")

    print("\n   📋 stdout 输出:")
    stdout = process.stdout.read()
    print(f"   {stdout}")
else:
    print("   ✅ 进程仍在运行")

    # 尝试发送空行
    print("\n3️⃣ 尝试发送换行...")
    process.stdin.write("\n")
    process.stdin.flush()

    time.sleep(2)
    poll = process.poll()
    print(f"   进程状态: poll() = {poll}")

    print("\n   📋 stderr 输出:")
    stderr = process.stderr.read()
    print(f"   {stderr}")

    print("\n   📋 stdout 输出:")
    stdout = process.stdout.read()
    print(f"   {stdout}")

    # 清理
    process.terminate()
    process.wait(timeout=5)

print("\n" + "=" * 60)
