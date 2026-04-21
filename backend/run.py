"""后端服务启动脚本

使用方法:
    python run.py

或使用 uvicorn 直接启动:
    uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
"""

import sys
import os

# 获取当前脚本所在目录 (backend/)
current_dir = os.path.dirname(os.path.abspath(__file__))
# 将 backend 目录添加到 Python 路径
sys.path.insert(0, current_dir)
# 设置工作目录为 backend/
os.chdir(current_dir)

if __name__ == "__main__":
    import uvicorn

    # 处理 Windows 控制台编码问题
    if sys.platform == "win32":
        try:
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
        except Exception:
            pass

    print("=" * 60)
    print("STARTING: Smart Trip Planner Backend Service")
    print("=" * 60)
    print(f"\n- Working Directory: {os.getcwd()}")
    print(f"- Python Path: {sys.path[0]}")
    print("\n- Usage:")
    print("   python run.py")
    print("\n- URLs:")
    print("   - API Docs: http://localhost:8001/docs")
    print("   - ReDoc:   http://localhost:8001/redoc")
    print("   - Health: http://localhost:8001/health")
    print("\nPress Ctrl+C to stop")
    print("=" * 60 + "\n")

    uvicorn.run(
        "app.api.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info",
    )
