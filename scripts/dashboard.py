"""BUFF 价格监控仪表盘启动脚本

用法：
    python scripts/dashboard.py
    python scripts/dashboard.py --port 8080 --db buff_data.db
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    parser = argparse.ArgumentParser(description="BUFF 价格监控仪表盘")
    parser.add_argument("--port", type=int, default=5000, help="端口，默认 5000")
    parser.add_argument("--host", default="127.0.0.1", help="主机，默认 127.0.0.1")
    parser.add_argument("--db", default="buff_data.db", help="数据库文件路径")
    args = parser.parse_args()

    try:
        from flask import Flask
    except ImportError:
        print("请先安装 Flask: pip install flask")
        sys.exit(1)

    from buff.dashboard import create_app
    app = create_app(db_path=args.db)

    if args.host == "0.0.0.0":
        print("警告: 绑定到 0.0.0.0 将暴露购买历史到网络，仅建议在受信任的局域网中使用")
    print(f"仪表盘启动: http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
