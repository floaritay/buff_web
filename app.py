"""
BUFF自动化工具 Web应用
整合三个脚本的功能到Web界面
"""
from flask import Flask, render_template, request, jsonify, Response, session, redirect, url_for
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import threading
import time
import json
import os
import sys
import schedule
from io import StringIO
from croniter import croniter
from datetime import datetime
import dotenv
import hashlib

# 加载环境变量
dotenv.load_dotenv()

app = Flask(__name__)

# 设置密钥
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

# 启用CORS，允许前端从Gitee Pages访问
CORS(app, resources={r"/*": {"origins": ["*"]}}, supports_credentials=True)

# 初始化Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

# 模拟用户存储
users = {}
user_cookies = {}

# 用户类
class User(UserMixin):
    def __init__(self, user_id, username, password_hash):
        self.id = user_id
        self.username = username
        self.password_hash = password_hash

# 用户加载回调
@login_manager.user_loader
def load_user(user_id):
    return users.get(user_id)

tasks = {}
task_counter = 0
task_lock = threading.Lock()

# Vercel 环境下使用 /tmp 目录存储文件
if os.environ.get('VERCEL') == '1':
    history_file = "/tmp/task_history.json"
else:
    history_file = "task_history.json"

scheduled_tasks = []
scheduler_running = False

class TaskOutputRedirector:
    def __init__(self, task_id):
        self.task_id = task_id
        self.buffer = []
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
    
    def write(self, text):
        if text.strip():
            with task_lock:
                if self.task_id in tasks:
                    tasks[self.task_id]['output'].append(text)
                    # 限制输出长度
                    if len(tasks[self.task_id]['output']) > 1000:
                        tasks[self.task_id]['output'] = tasks[self.task_id]['output'][-500:]
        self.original_stdout.write(text)
    
    def flush(self):
        self.original_stdout.flush()

def run_buyer_task(task_id, params, user_id):
    """运行购买脚本任务"""
    from buff_buyer import BuffBuyer, load_cookie, load_tried_items, save_tried_items, save_cookie
    
    redirector = TaskOutputRedirector(task_id)
    sys.stdout = redirector
    sys.stderr = redirector
    
    try:
        with task_lock:
            tasks[task_id]['status'] = 'running'
        
        print(f"=== 开始执行购买任务 ===")
        print(f"参数: {params}")
        
        max_price = float(params.get('max_price', 0.05))
        max_items = int(params.get('max_items', 10))
        cookie = params.get('cookie', '')
        
        # 如果没有提供cookie，从环境变量获取
        if not cookie:
            cookie = os.environ.get('BUFF_COOKIE', '')
        
        buyer = BuffBuyer(game="csgo")
        
        if cookie:
            buyer.set_cookie(cookie)
            print(f"已设置Cookie: {cookie[:30]}...")
        else:
            print("警告: 未提供Cookie")
        
        if not buyer.test_login():
            print("登录失败，请检查Cookie")
            with task_lock:
                tasks[task_id]['status'] = 'failed'
            return
        
        tried_items = load_tried_items()
        buyer.run(max_price=max_price, max_items=max_items, tried_items=tried_items)
        save_tried_items(tried_items)
        
        with task_lock:
            tasks[task_id]['status'] = 'completed'
            save_task_to_history(tasks[task_id])
        
    except Exception as e:
        print(f"任务执行异常: {e}")
        import traceback
        traceback.print_exc()
        with task_lock:
            tasks[task_id]['status'] = 'failed'
            save_task_to_history(tasks[task_id])
    finally:
        sys.stdout = redirector.original_stdout
        sys.stderr = redirector.original_stderr

def run_charm_searcher_task(task_id, params, script_type, user_id):
    """运行挂件搜枪脚本任务"""
    redirector = TaskOutputRedirector(task_id)
    sys.stdout = redirector
    sys.stderr = redirector
    
    try:
        with task_lock:
            tasks[task_id]['status'] = 'running'
        
        print(f"=== 开始执行挂件搜枪任务 ({script_type}) ===")
        print(f"参数: {params}")
        
        max_price = float(params.get('max_price', 0.3))
        max_pages = int(params.get('max_pages', 18))
        max_items = int(params.get('max_items', 10))
        cookie = params.get('cookie', '')
        
        if script_type == 'austin':
            from buff_charm_searcher_austin import BuffCharmSearcher, load_cookie, load_tried_items, save_tried_items, save_cookie
            tried_items_file = "charm_tried_items.json"
        else:
            from buff_charm_searcher_budapest import BuffCharmSearcher, load_cookie, load_tried_items, save_tried_items, save_cookie
            tried_items_file = "charm_tried_items_budapest.json"
        
        searcher = BuffCharmSearcher(game="csgo")
        
        if cookie:
            searcher.set_cookie(cookie)
            # 存储到用户存储空间
            if user_id:
                user_cookies[user_id] = cookie
        else:
            # 从用户存储空间获取cookie
            if user_id:
                cookie = user_cookies.get(user_id, '')
                if cookie:
                    searcher.set_cookie(cookie)
        
        if not searcher.test_login():
            print("登录失败，请检查Cookie")
            with task_lock:
                tasks[task_id]['status'] = 'failed'
            return
        
        tried_items = load_tried_items(file_path=tried_items_file)
        searcher.run(max_price=max_price, max_pages=max_pages, max_items=max_items, tried_items=tried_items)
        save_tried_items(tried_items, file_path=tried_items_file)
        
        with task_lock:
            tasks[task_id]['status'] = 'completed'
            save_task_to_history(tasks[task_id])
        
    except Exception as e:
        print(f"任务执行异常: {e}")
        import traceback
        traceback.print_exc()
        with task_lock:
            tasks[task_id]['status'] = 'failed'
            save_task_to_history(tasks[task_id])
    finally:
        sys.stdout = redirector.original_stdout
        sys.stderr = redirector.original_stderr

@app.route('/')
def index():
    """返回静态的index.html文件"""
    try:
        # 获取当前文件所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        index_path = os.path.join(current_dir, 'index.html')
        
        with open(index_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Error loading page: {str(e)}", 500

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    with task_lock:
        return jsonify(list(tasks.values()))

@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    with task_lock:
        if task_id in tasks:
            return jsonify(tasks[task_id])
        return jsonify({'error': 'Task not found'}), 404

@app.route('/api/tasks/buyer', methods=['POST'])
def start_buyer_task():
    global task_counter
    params = request.json
    
    # 获取当前用户ID
    user_id = current_user.id if current_user.is_authenticated else None
    
    with task_lock:
        task_counter += 1
        task_id = f"buyer_{task_counter}"
        tasks[task_id] = {
            'id': task_id,
            'type': 'buyer',
            'params': params,
            'status': 'pending',
            'output': [],
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    thread = threading.Thread(target=run_buyer_task, args=(task_id, params, user_id))
    thread.daemon = True
    thread.start()
    
    return jsonify({'task_id': task_id})

@app.route('/api/tasks/charm/austin', methods=['POST'])
def start_austin_task():
    global task_counter
    params = request.json
    
    # 获取当前用户ID
    user_id = current_user.id if current_user.is_authenticated else None
    
    with task_lock:
        task_counter += 1
        task_id = f"charm_austin_{task_counter}"
        tasks[task_id] = {
            'id': task_id,
            'type': 'charm_austin',
            'params': params,
            'status': 'pending',
            'output': [],
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    thread = threading.Thread(target=run_charm_searcher_task, args=(task_id, params, 'austin', user_id))
    thread.daemon = True
    thread.start()
    
    return jsonify({'task_id': task_id})

@app.route('/api/tasks/charm/budapest', methods=['POST'])
def start_budapest_task():
    global task_counter
    params = request.json
    
    # 获取当前用户ID
    user_id = current_user.id if current_user.is_authenticated else None
    
    with task_lock:
        task_counter += 1
        task_id = f"charm_budapest_{task_counter}"
        tasks[task_id] = {
            'id': task_id,
            'type': 'charm_budapest',
            'params': params,
            'status': 'pending',
            'output': [],
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    thread = threading.Thread(target=run_charm_searcher_task, args=(task_id, params, 'budapest', user_id))
    thread.daemon = True
    thread.start()
    
    return jsonify({'task_id': task_id})

@app.route('/api/tasks/<task_id>/output', methods=['GET'])
def get_task_output(task_id):
    with task_lock:
        if task_id in tasks:
            return jsonify({'output': tasks[task_id]['output'], 'status': tasks[task_id]['status']})
        return jsonify({'error': 'Task not found'}), 404

@app.route('/api/tasks/<task_id>/stream')
def stream_task_output(task_id):
    def generate():
        last_len = 0
        timeout_counter = 0
        max_timeout = 240  # 最多运行2分钟（240次 * 0.5秒）
        
        while True:
            with task_lock:
                if task_id not in tasks:
                    yield f"data: {json.dumps({'done': True})}\n\n"
                    break
                
                task = tasks[task_id]
                new_output = task['output'][last_len:]
                last_len = len(task['output'])
                
                if new_output:
                    yield f"data: {json.dumps({'output': new_output, 'status': task['status']})}\n\n"
                
                if task['status'] in ['completed', 'failed']:
                    yield f"data: {json.dumps({'done': True, 'status': task['status']})}\n\n"
                    break
            
            time.sleep(0.5)
            timeout_counter += 1
            if timeout_counter > max_timeout:
                yield f"data: {json.dumps({'done': True, 'status': 'timeout'})}\n\n"
                break
    
    return Response(generate(), mimetype='text/event-stream')

def save_task_to_history(task):
    """保存任务到历史记录"""
    try:
        history = []
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        
        history.insert(0, {
            'id': task['id'],
            'type': task['type'],
            'params': task['params'],
            'status': task['status'],
            'created_at': task['created_at'],
            'output': task['output'][-200:]
        })
        
        if len(history) > 100:
            history = history[:100]
        
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存历史记录失败: {e}")

@app.route('/api/history', methods=['GET'])
def get_history():
    try:
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            return jsonify(history)
        return jsonify([])
    except Exception as e:
        return jsonify([])

@app.route('/api/history', methods=['DELETE'])
def clear_history():
    try:
        if os.path.exists(history_file):
            os.remove(history_file)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/tasks', methods=['DELETE'])
def clear_tasks():
    task_type = request.args.get('type', None)
    try:
        with task_lock:
            if task_type:
                task_types_map = {
                    'buyer': 'buyer',
                    'austin': 'charm_austin',
                    'budapest': 'charm_budapest'
                }
                target_type = task_types_map.get(task_type)
                if target_type:
                    tasks_to_remove = [tid for tid, t in tasks.items() if t['type'] == target_type]
                    for tid in tasks_to_remove:
                        del tasks[tid]
            else:
                tasks.clear()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/schedule', methods=['GET'])
def get_scheduled_tasks():
    return jsonify(scheduled_tasks)

@app.route('/api/schedule', methods=['POST'])
def add_scheduled_task():
    scheduler_id = len(scheduled_tasks) + 1
    task_data = request.json
    now = datetime.now()
    try:
        iter = croniter(task_data['cron'], now)
        next_run = iter.get_next(datetime)
    except:
        next_run = None
    
    scheduled_tasks.append({
        'id': scheduler_id,
        'type': task_data['type'],
        'params': task_data['params'],
        'cron': task_data['cron'],
        'enabled': True,
        'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'next_run': next_run.strftime('%Y-%m-%d %H:%M:%S') if next_run else None,
        'last_run': None
    })
    return jsonify({'success': True, 'id': scheduler_id})

@app.route('/api/schedule/<int:task_id>', methods=['DELETE'])
def delete_scheduled_task(task_id):
    global scheduled_tasks
    scheduled_tasks = [t for t in scheduled_tasks if t['id'] != task_id]
    return jsonify({'success': True})

@app.route('/api/auth/register', methods=['POST'])
def register():
    """用户注册"""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'success': False, 'message': '用户名和密码不能为空'}), 400
        
        # 检查用户名是否已存在
        for user in users.values():
            if user.username == username:
                return jsonify({'success': False, 'message': '用户名已存在'}), 400
        
        # 创建新用户
        user_id = str(len(users) + 1)
        password_hash = hashlib.md5(password.encode()).hexdigest()
        user = User(user_id, username, password_hash)
        users[user_id] = user
        user_cookies[user_id] = ''
        
        # 登录用户
        login_user(user)
        
        return jsonify({'success': True, 'message': '注册成功', 'user': {'id': user_id, 'username': username}})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'success': False, 'message': '用户名和密码不能为空'}), 400
        
        # 查找用户
        for user in users.values():
            if user.username == username:
                # 验证密码
                if user.password_hash == hashlib.md5(password.encode()).hexdigest():
                    login_user(user)
                    return jsonify({'success': True, 'message': '登录成功', 'user': {'id': user.id, 'username': user.username}})
                else:
                    return jsonify({'success': False, 'message': '密码错误'}), 400
        
        return jsonify({'success': False, 'message': '用户不存在'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    """用户注销"""
    try:
        logout_user()
        return jsonify({'success': True, 'message': '注销成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/auth/status', methods=['GET'])
def get_auth_status():
    """获取认证状态"""
    if current_user.is_authenticated:
        return jsonify({'authenticated': True, 'user': {'id': current_user.id, 'username': current_user.username}})
    else:
        return jsonify({'authenticated': False})

@app.route('/api/cookie', methods=['POST'])
def save_cookie_api():
    """保存cookie - Vercel环境下使用环境变量"""
    try:
        data = request.json
        cookie = data.get('cookie', '')
        if cookie:
            # 在 Vercel 环境下保存到环境变量（临时）
            if os.environ.get('VERCEL') == '1':
                os.environ['BUFF_COOKIE'] = cookie
            else:
                # 本地环境保存到文件
                with open('cookie.txt', 'w', encoding='utf-8') as f:
                    f.write(cookie)
            return jsonify({'success': True, 'message': 'Cookie保存成功'})
        return jsonify({'success': False, 'message': 'Cookie不能为空'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/cookie', methods=['GET'])
def get_cookie_api():
    """获取当前保存的cookie"""
    try:
        # Vercel 环境从环境变量读取
        if os.environ.get('VERCEL') == '1':
            cookie = os.environ.get('BUFF_COOKIE', '')
        else:
            # 本地环境从文件读取
            cookie_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookie.txt')
            if os.path.exists(cookie_path):
                with open(cookie_path, 'r', encoding='utf-8') as f:
                    cookie = f.read().strip()
            else:
                cookie = ''
        return jsonify({'cookie': cookie[:20] + '...' if len(cookie) > 20 else cookie})
    except Exception as e:
        return jsonify({'cookie': '', 'error': str(e)})

def run_scheduled_task(task_info):
    """执行定时任务"""
    global task_counter
    task_type = task_info['type']
    params = task_info['params']
    
    with task_lock:
        task_counter += 1
        if task_type == 'buyer':
            task_id = f"buyer_{task_counter}"
            full_type = 'buyer'
        elif task_type == 'austin':
            task_id = f"charm_austin_{task_counter}"
            full_type = 'charm_austin'
        elif task_type == 'budapest':
            task_id = f"charm_budapest_{task_counter}"
            full_type = 'charm_budapest'
        else:
            return
        
        tasks[task_id] = {
            'id': task_id,
            'type': full_type,
            'params': params,
            'status': 'pending',
            'output': [],
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    if task_type == 'buyer':
        thread = threading.Thread(target=run_buyer_task, args=(task_id, params))
    elif task_type == 'austin':
        thread = threading.Thread(target=run_charm_searcher_task, args=(task_id, params, 'austin'))
    elif task_type == 'budapest':
        thread = threading.Thread(target=run_charm_searcher_task, args=(task_id, params, 'budapest'))
    
    thread.daemon = True
    thread.start()

def run_scheduler():
    """定时任务调度器"""
    global scheduler_running, scheduled_tasks
    scheduler_running = True
    while scheduler_running:
        try:
            now = datetime.now()
            for task in scheduled_tasks:
                if not task.get('enabled', True):
                    continue
                
                next_run_str = task.get('next_run')
                if not next_run_str:
                    continue
                
                try:
                    next_run = datetime.strptime(next_run_str, '%Y-%m-%d %H:%M:%S')
                except:
                    continue
                
                if now >= next_run:
                    print(f"执行定时任务: {task['id']} - {task['type']}")
                    run_scheduled_task(task)
                    task['last_run'] = time.strftime('%Y-%m-%d %H:%M:%S')
                    
                    try:
                        iter = croniter(task['cron'], next_run)
                        new_next = iter.get_next(datetime)
                        task['next_run'] = new_next.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        task['next_run'] = None
        except Exception as e:
            print(f"调度器错误: {e}")
            import traceback
            traceback.print_exc()
        
        time.sleep(30)

if __name__ == '__main__':
    # 本地开发环境启动调度器
    if os.environ.get('VERCEL') != '1':
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
