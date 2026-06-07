"""兼容入口 - 转发到 scripts/buff_buyer.py"""
import importlib.util, sys, os

_entry = os.path.join(os.path.dirname(__file__), "scripts", "buff_buyer.py")
try:
    spec = importlib.util.spec_from_file_location("scripts.buff_buyer", _entry)
    if spec is None:
        raise FileNotFoundError(f"找不到入口文件: {_entry}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
except Exception as e:
    print(f"[错误] 无法加载入口脚本: {e}")
    sys.exit(1)
