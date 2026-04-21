"""MCP 服务诊断脚本

用于测试 amap-mcp-server 是否能正常启动和工作
使用方法: python test/mcp_service.py
"""

import json
import subprocess
import sys
import time
import os

def test_amap_mcp():
    """测试 amap-mcp-server 是否正常工作"""

    print("=" * 60)
    print("🔍 开始诊断 MCP 服务...")
    print("=" * 60)

    # 检查 uvx 是否安装
    print("\n1️⃣ 检查 uvx 是否安装...")
    try:
        result = subprocess.run(
            ["uvx", "--version"],
            capture_output=True,
            text=True,
            shell=True
        )
        print(f"   uvx 版本: {result.stdout.strip()}")
    except FileNotFoundError:
        print("   ❌ uvx 未找到！请先安装 uv: pip install uv")
        return False

    # 检查 amap-mcp-server 是否安装
    print("\n2️⃣ 检查 amap-mcp-server 是否安装...")
    try:
        result = subprocess.run(
            ["uvx", "amap-mcp-server", "--help"],
            capture_output=True,
            text=True,
            shell=True,
            timeout=10
        )
        print(f"   amap-mcp-server --help 输出:\n   {result.stdout[:500]}")
    except subprocess.TimeoutExpired:
        print("   ⏳ amap-mcp-server --help 超时 (可能正在下载安装...)")
    except FileNotFoundError:
        print("   ❌ amap-mcp-server 未找到")
        return False

    # 尝试启动 amap-mcp-server 并发送测试请求
    print("\n3️⃣ 尝试启动 amap-mcp-server 并测试...")

    env = os.environ.copy()
    env["AMAP_MAPS_API_KEY"] = "ac1ea698f217441726200df366c84b73"  # 使用你的 Key

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

        print("   ⏳ 等待服务启动 (5秒)...")
        time.sleep(5)

        # 检查进程是否还在运行
        if process.poll() is not None:
            stderr_output = process.stderr.read()
            stdout_output = process.stdout.read()
            print(f"   ❌ 进程已退出，退出码: {process.returncode}")
            print(f"   stderr: {stderr_output[:500]}")
            print(f"   stdout: {stdout_output[:500]}")
            return False

        print("   ✅ 服务进程正在运行")

        # 发送 tools/list 请求
        print("\n4️⃣ 发送 tools/list 请求...")
        request = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }) + "\n"

        try:
            process.stdin.write(request)
            process.stdin.flush()

            # 等待响应
            print("   ⏳ 等待响应 (30秒)...")
            response_line = process.stdout.readline()

            if response_line:
                print(f"   ✅ 收到响应: {response_line[:200]}...")
                response = json.loads(response_line)
                if "result" in response:
                    tools = response["result"].get("tools", [])
                    print(f"   📋 可用工具数量: {len(tools)}")
                    for tool in tools[:5]:
                        print(f"      - {tool.get('name', 'unknown')}")
                    return True
                elif "error" in response:
                    print(f"   ❌ MCP 错误: {response['error']}")
                    return False
            else:
                print("   ❌ 未收到响应")
                # 读取 stderr 看是否有错误
                stderr_output = process.stderr.read()
                if stderr_output:
                    print(f"   stderr: {stderr_output[:500]}")
                return False

        except Exception as e:
            print(f"   ❌ 请求失败: {e}")
            return False

    except Exception as e:
        print(f"   ❌ 启动失败: {e}")
        return False
    finally:
        # 清理进程
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
