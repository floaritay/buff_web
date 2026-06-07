"""Flask 价格监控仪表盘 + 工具执行"""

import json
import os
import subprocess
import threading
import uuid
from collections import deque

from flask import Flask, Response, jsonify, render_template, request

from buff.db import (
    get_all_monitored,
    get_price_history,
    get_purchase_history,
    get_purchase_stats,
    init_db,
)

app = Flask(__name__, template_folder="templates")
_db_conn = None

# ── 工具执行管理 ────────────────────────────────────────────────

_tasks = {}  # task_id -> {"proc": Popen, "lines": deque, "status": str}
_lock = threading.Lock()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TOOLS = {
    "item_buyer": {
        "name": "指定饰品购买",
        "script": os.path.join("scripts", "item_buyer.py"),
        "params": [
            {"name": "goods_id", "label": "goods_id 或 URL", "required": True},
            {"name": "max_price", "label": "最高价格（元）", "default": "1.0"},
            {"name": "max_items", "label": "最大购买数量", "default": "5"},
            {"name": "interval", "label": "轮询间隔（秒，0=单次）", "default": "0"},
            {"name": "dry_run", "label": "模拟模式", "type": "checkbox"},
        ],
    },
    "graffiti": {
        "name": "涂鸦饰品购买",
        "script": os.path.join("scripts", "buff_buyer.py"),
        "params": [
            {"name": "max_price", "label": "最高价格（元）", "default": "0.05"},
            {"name": "max_items", "label": "最大购买数量", "default": "10"},
            {"name": "dry_run", "label": "模拟模式", "type": "checkbox"},
        ],
    },
    "charm_searcher": {
        "name": "挂件搜枪",
        "script": os.path.join("scripts", "buff_charm_searcher.py"),
        "params": [
            {"name": "event", "label": "赛事（austin / budapest）", "required": True},
            {"name": "max_price", "label": "最高价格（元）", "default": "0.3"},
            {"name": "max_items", "label": "最大购买数量", "default": "10"},
            {"name": "dry_run", "label": "模拟模式", "type": "checkbox"},
        ],
    },
}


def _stream_reader(task_id, proc):
    """后台线程：读取子进程输出并存入 task 的 lines 队列"""
    try:
        for raw_line in iter(proc.stdout.readline, ""):
            line = raw_line.rstrip("\n\r")
            with _lock:
                if task_id in _tasks:
                    _tasks[task_id]["lines"].append(line)
        proc.wait()
        with _lock:
            if task_id in _tasks:
                _tasks[task_id]["status"] = "finished"
                _tasks[task_id]["returncode"] = proc.returncode
                _tasks[task_id]["lines"].append(f"[进程退出，返回码 {proc.returncode}]")
    except Exception as e:
        with _lock:
            if task_id in _tasks:
                _tasks[task_id]["status"] = "error"
                _tasks[task_id]["lines"].append(f"[错误: {e}]")


def get_db():
    global _db_conn
    if _db_conn is None:
        _db_conn = init_db()
    return _db_conn


# ── 页面 ────────────────────────────────────────────────────────


@app.route("/")
def index():
    return render_template("dashboard.html", tools=TOOLS)


# ── 数据 API ────────────────────────────────────────────────────


@app.route("/api/stats")
def api_stats():
    days = request.args.get("days", type=int)
    stats = get_purchase_stats(get_db(), days)
    return jsonify(stats)


@app.route("/api/monitored")
def api_monitored():
    items = get_all_monitored(get_db())
    return jsonify(items)


@app.route("/api/prices/<goods_id>")
def api_prices(goods_id):
    days = request.args.get("days", 30, type=int)
    history = get_price_history(get_db(), goods_id, days)
    return jsonify(history)


@app.route("/api/history")
def api_history():
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)
    history = get_purchase_history(get_db(), limit, offset)
    return jsonify(history)


# ── 工具执行 API ────────────────────────────────────────────────


@app.route("/api/tools")
def api_tools():
    return jsonify({k: {"name": v["name"], "params": v["params"]} for k, v in TOOLS.items()})


@app.route("/api/run", methods=["POST"])
def api_run():
    data = request.json or {}
    tool_id = data.get("tool")
    if tool_id not in TOOLS:
        return jsonify({"error": f"未知工具: {tool_id}"}), 400

    tool = TOOLS[tool_id]
    script_path = os.path.join(BASE_DIR, tool["script"])
    if not os.path.exists(script_path):
        return jsonify({"error": f"脚本不存在: {script_path}"}), 500

    cmd = ["python", "-u", script_path]
    for param in tool["params"]:
        val = data.get(param["name"])
        if param.get("type") == "checkbox":
            if val:
                cmd.append(f"--{param['name'].replace('_', '-')}")
        elif val:
            cmd.append(f"--{param['name'].replace('_', '-')}")
            cmd.append(str(val))

    task_id = uuid.uuid4().hex[:8]
    env = os.environ.copy()
    env["BUFF_NON_INTERACTIVE"] = "1"
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=BASE_DIR,
        env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )

    with _lock:
        _tasks[task_id] = {
            "proc": proc,
            "lines": deque(maxlen=5000),
            "status": "running",
            "cmd": cmd,
            "tool": tool_id,
        }

    t = threading.Thread(target=_stream_reader, args=(task_id, proc), daemon=True)
    t.start()

    return jsonify({"task_id": task_id, "cmd": cmd})


@app.route("/api/run/<task_id>/stream")
def api_run_stream(task_id):
    def generate():
        last_idx = 0
        while True:
            with _lock:
                task = _tasks.get(task_id)
                if not task:
                    yield f"data: {json.dumps({'error': '任务不存在'})}\n\n"
                    return
                lines = list(task["lines"])
                status = task["status"]

            new_lines = lines[last_idx:]
            for line in new_lines:
                yield f"data: {json.dumps({'line': line})}\n\n"
            last_idx = len(lines)

            if status in ("finished", "error", "stopped"):
                yield f"data: {json.dumps({'status': status, 'returncode': task.get('returncode')})}\n\n"
                return

            import time
            time.sleep(0.3)

    return Response(generate(), mimetype="text/event-stream")


@app.route("/api/run/<task_id>/stop", methods=["POST"])
def api_run_stop(task_id):
    with _lock:
        task = _tasks.get(task_id)
        if not task:
            return jsonify({"error": "任务不存在"}), 404
        if task["status"] != "running":
            return jsonify({"error": "任务未在运行"}), 400

    proc = task["proc"]
    try:
        if os.name == "nt":
            proc.terminate()
        else:
            import signal
            proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)
    except Exception:
        proc.kill()

    with _lock:
        task["status"] = "stopped"
        task["lines"].append("[用户终止]")

    return jsonify({"ok": True})


@app.route("/api/run/<task_id>/status")
def api_run_status(task_id):
    with _lock:
        task = _tasks.get(task_id)
        if not task:
            return jsonify({"error": "任务不存在"}), 404
        return jsonify({
            "status": task["status"],
            "lines_count": len(task["lines"]),
            "returncode": task.get("returncode"),
        })


# ── 工厂函数 ────────────────────────────────────────────────────


def create_app(db_path: str = "buff_data.db"):
    global _db_conn
    _db_conn = init_db(db_path)
    return app
