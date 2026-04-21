"""增强版 MCP 服务诊断脚本

用于测试 amap-mcp-server 是否能正常启动和工作
使用方法: python test/mcp_service_debug.py
"""

import json
import subprocess
import sys
import time
import os
import threading

def read_output(stream, prefix, results):
    """持续读取流并存储结果"""
    try:
        for line in iter(stream.readline, ''):
            if line:
                results.append((prefix, line.strip()))
    except:
        pass

def test_amap_mcp():
    """测试 amap-mcp-server 是否正常工作"""

    print("=" * 60)
    print("🔍 开始增强版 MCP 服务诊断...")
    print("=" * 60)

    # 检查 uvx 是否安装
    print("\n1️⃣ 检查 uvx 是否安装...")
    try:
        result = subprocess.run(
            "uvx --version",
            capture_output=True,
            text=True,
            shell=True
        )
        print(f"   uvx 版本: {result.stdout.strip()}")
    except FileNotFoundError:
        print("   ❌ uvx 未找到！请先安装 uv: pip install uv")
        return False

    # 尝试启动 amap-mcp-server 并发送测试请求
    print("\n2️⃣ 尝试启动 amap-mcp-server 并测试...")

    env = os.environ.copy()
    env["AMAP_MAPS_API_KEY"] = "ac1ea698f217441726200df366c84b73"

    try:
        # 启动进程
        process = subprocess.Popen(
            "uvx amap-mcp-server",
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            shell=True
        )

        print("   ⏳ 等待服务启动...")

        # 启动读取线程
        stdout_lines = []
        stderr_lines = []
        stdout_thread = threading.Thread(target=read_output, args=(process.stdout, "stdout", stdout_lines))
        stderr_thread = threading.Thread(target=read_output, args=(process.stderr, "stderr", stderr_lines))
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        stdout_thread.start()
        stderr_thread.start()

        # 等待服务初始化
        time.sleep(3)

        # 检查进程状态
        if process.poll() is not None:
            print("   ❌ 进程已退出")
            for prefix, line in stderr_lines:
                print(f"      [{prefix}] {line}")
            return False

        print("   ✅ 服务进程正在运行")
        print(f"\n   已收集的输出 ({len(stdout_lines)} stdout, {len(stderr_lines)} stderr):")

        for prefix, line in stdout_lines[:10]:
            print(f"      [{prefix}] {line[:100]}")
        for prefix, line in stderr_lines[:10]:
            print(f"      [{prefix}] {line[:100]}")

        # 发送 tools/list 请求
        print("\n3️⃣ 发送 tools/list 请求...")
        request = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }) + "\n"

        process.stdin.write(request)
        process.stdin.flush()
        print(f"   ✅ 已发送请求")

        # 等待响应，设置较短的超时以便观察
        print("   ⏳ 等待响应 (10秒)...")

        for i in range(10):
            time.sleep(1)
            # 检查新输出
            new_stdout = len(stdout_lines)
            new_stderr = len(stderr_lines)
            if new_stdout > 10 or new_stderr > 10:
                print(f"\n   📋 新输出 (第{i+1}秒):")
                for prefix, line in stdout_lines[10:]:
                    print(f"      [{prefix}] {line[:200]}")
                for prefix, line in stderr_lines[10:]:
                    print(f"      [{prefix}] {line[:200]}")

            # 检查是否有响应
            if stdout_lines:
                last_line = stdout_lines[-1]
                if last_line[0] == "stdout" and "jsonrpc" in last_line[1]:
                    print(f"   ✅ 收到响应!")
                    response = json.loads(last_line[1])
                    if "result" in response:
                        tools = response["result"].get("tools", [])
                        print(f"   📋 可用工具数量: {len(tools)}")
                        for tool in tools[:5]:
                            print(f"      - {tool.get('name', 'unknown')}")
                        return True

        print("\n   ❌ 超时，未收到有效响应")
        print(f"\n   最终输出 ({len(stdout_lines)} stdout, {len(stderr_lines)} stderr):")
        for prefix, line in stdout_lines:
            print(f"      [{prefix}] {line[:200]}")
        for prefix, line in stderr_lines:
            print(f"      [{prefix}] {line[:200]}")

        return False

    except Exception as e:
        print(f"   ❌ 启动失败: {e}")
        return False
    finally:
        if 'process' in locals() and process.poll() is None:
            process.terminate()
            process.wait(timeout=5)

    return False


if __name__ == "__main__":
    success = test_amap_mcp()

    print("\n" + "=" * 60)
    if success:
        print("✅ MCP 服务诊断通过！")
    else:
        print("❌ MCP 服务诊断失败，请查看上述错误信息")
    print("=" * 60)

    sys.exit(0 if success else 1)
