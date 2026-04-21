"""MCP (Model Context Protocol) 客户端实现

MCP是一种标准协议，允许AI模型与外部工具/服务进行通信。
这里使用 StdIO (标准输入/输出) 方式与 MCP 服务进行进程间通信。

工作原理:
1. 启动 MCP 服务作为子进程 (如 amap-mcp-server)
2. 通过 JSON-RPC 协议在 stdin/stdout 上发送请求和接收响应
3. 支持列出工具、调用工具等操作

MCP 协议消息格式:
- 请求: {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
- 响应: {"jsonrpc": "2.0", "id": 1, "result": {...}}

MCP 服务必须实现的接口:
- tools/list: 列出所有可用工具
- tools/call: 调用指定工具
"""

import json
import subprocess
import threading
from typing import Any, Dict, List, Optional


class StdioMCPClient:
    """基于 StdIO 的 MCP 客户端
    
    通过子进程启动 MCP 服务，使用 JSON-RPC 协议进行通信
    
    Attributes:
        command: 启动 MCP 服务的命令列表，如 ["uvx", "amap-mcp-server"]
        env: 环境变量字典，会传递给子进程
        timeout: 调用工具的超时时间(秒)
    """
    
    def __init__(
        self,
        command: List[str],
        env: Optional[Dict[str, str]] = None,
        timeout: int = 60
    ):
        """初始化 MCP 客户端
        
        Args:
            command: 启动命令列表，如 ["uvx", "amap-mcp-server"]
            env: 环境变量，会合并到子进程的环境变量中
            timeout: 调用超时时间(秒)
        """
        self.command = command
        self.env = env or {}
        self.timeout = timeout
        
        # 进程管理
        self._process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        
        # 消息ID计数器 (用于 JSON-RPC 请求)
        self._id_counter = 0
        
        # 等待响应的字典 {(id): threading.Event}
        self._pending: Dict[int, threading.Event] = {}
        # 响应结果缓存 {(id): response}
        self._responses: Dict[int, Any] = {}
    
    def start(self) -> None:
        """启动 MCP 服务子进程

        创建一个子进程运行 MCP 服务，建立双向通信管道
        """
        import os
        import time

        # 合并环境变量: 继承系统环境 (PATH等) + 自定义环境 (API Key等)
        full_env = os.environ.copy()
        full_env.update(self.env)

        # 在 Windows 上，使用 shell=True 以便找到 PATH 中的命令
        is_windows = os.name == "nt"

        # 尝试不同的启动方式
        cmd = self.command

        if is_windows:
            # Windows: 转为字符串命令，使用 shell=True
            cmd = " ".join(cmd)

        # 启动子进程
        self._process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=full_env,
            text=True,
            bufsize=1,
            shell=is_windows,
        )

        # 启动读取线程，异步接收 MCP 服务的响应
        self._read_thread = threading.Thread(target=self._read_output, daemon=True)
        self._read_thread.start()

        # 启动 stderr 读取线程，消费错误输出避免缓冲区满
        self._stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
        self._stderr_thread.start()

        # 等待 MCP 服务初始化完成 (首次调用需要准备时间)
        print(f"[WAIT] 等待 MCP 服务初始化...")
        time.sleep(5)

        # 检查进程是否异常退出
        if self._process.poll() is not None:
            stderr_output = self._process.stderr.read()
            raise RuntimeError(f"MCP服务启动失败，退出码: {self._process.returncode}\nstderr: {stderr_output}")

        print(f"[SUCCESS] MCP服务已启动: {' '.join(self.command)}")
    
    def _read_output(self) -> None:
        """读取 MCP 服务输出的专用线程
        
        持续从 stdout 读取响应，根据 id 分发到对应的等待者
        """
        while self._process and self._process.stdout:
            try:
                line = self._process.stdout.readline()
                if not line:
                    # EOF 表示进程结束
                    break
                
                # 解析 JSON-RPC 响应
                response = json.loads(line)
                msg_id = response.get("id")
                
                if msg_id is not None and msg_id in self._pending:
                    # 找到对应的等待者，存入结果并唤醒
                    self._responses[msg_id] = response
                    self._pending[msg_id].set()
                    
            except json.JSONDecodeError as e:
                print(f"[WARNING] 解析MCP响应失败: {e}")
            except Exception as e:
                print(f"[WARNING] 读取MCP输出异常: {e}")

    def _read_stderr(self) -> None:
        """读取 MCP 服务错误输出的专用线程

        消费 stderr 输出，避免缓冲区满导致进程阻塞
        """
        while self._process and self._process.stderr:
            try:
                line = self._process.stderr.readline()
                if not line:
                    break
                # 打印错误信息便于调试
                print(f"[SEARCH] [MCP stderr] {line.strip()}")
            except Exception:
                break
    
    def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """发送 JSON-RPC 请求到 MCP 服务
        
        Args:
            method: 方法名，如 "tools/list", "tools/call"
            params: 方法参数
            
        Returns:
            解析后的响应结果
            
        Raises:
            RuntimeError: MCP服务未启动或响应超时
        """
        if not self._process or not self._process.stdin:
            raise RuntimeError("MCP服务未启动")
        
        # 生成唯一消息ID
        self._id_counter += 1
        msg_id = self._id_counter
        
        # 构建 JSON-RPC 请求
        request = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "method": method,
            "params": params or {}
        }
        
        # 创建等待事件
        event = threading.Event()
        self._pending[msg_id] = event
        self._responses[msg_id] = None
        
        try:
            with self._lock:
                # 发送请求到子进程
                request_json = json.dumps(request) + "\n"
                self._process.stdin.write(request_json)
                self._process.stdin.flush()
            
            # 等待响应 (带超时)
            if not event.wait(timeout=self.timeout):
                raise TimeoutError(f"MCP调用超时 ({self.timeout}秒): {method}")
            
            # 获取响应结果
            response = self._responses.get(msg_id)
            if response is None:
                raise RuntimeError(f"MCP响应为空: {method}")
            
            # 检查错误
            if "error" in response:
                raise RuntimeError(f"MCP错误: {response['error']}")
            
            return response.get("result")
            
        finally:
            # 清理等待状态
            self._pending.pop(msg_id, None)
            self._responses.pop(msg_id, None)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """列出 MCP 服务提供的所有工具
        
        Returns:
            工具列表，每个工具包含 name, description, inputSchema 等
        """
        result = self._send_request("tools/list")
        return result.get("tools", [])
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用指定的 MCP 工具
        
        Args:
            tool_name: 工具名称 (如 "poi_search", "weather")
            arguments: 工具参数 (根据工具的 inputSchema 传递)
            
        Returns:
            工具执行结果
        """
        return self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })
    
    def stop(self) -> None:
        """停止 MCP 服务子进程"""
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
            print("🔴 MCP服务已停止")
    
    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.stop()
