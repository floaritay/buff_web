"""
BUFF自动化工具 Web应用
整合三个脚本的功能到Web界面
"""
from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
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

# 加载环境变量
dotenv.load_dotenv()

app = Flask(__name__)

# 启用CORS，允许前端从Gitee Pages访问
CORS(app, resources={r"/*": {"origins": ["*"]}})

tasks = {}
task_counter = 0
task_lock = threading.Lock()
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

def run_buyer_task(task_id, params):
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
        
        buyer = BuffBuyer(game="csgo")
        
        if cookie:
            buyer.set_cookie(cookie)
            # 存储到环境变量，而不是文件
            os.environ['BUFF_COOKIE'] = cookie
        else:
            # 从环境变量获取cookie
            cookie = os.environ.get('BUFF_COOKIE', '')
            if cookie:
                buyer.set_cookie(cookie)
        
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

def run_charm_searcher_task(task_id, params, script_type):
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
            # 存储到环境变量，而不是文件
            os.environ['BUFF_COOKIE'] = cookie
        else:
            # 从环境变量获取cookie
            cookie = os.environ.get('BUFF_COOKIE', '')
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
    return render_template('index.html')

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
    
    thread = threading.Thread(target=run_buyer_task, args=(task_id, params))
    thread.daemon = True
    thread.start()
    
    return jsonify({'task_id': task_id})

@app.route('/api/tasks/charm/austin', methods=['POST'])
def start_austin_task():
    global task_counter
    params = request.json
    
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
    
    thread = threading.Thread(target=run_charm_searcher_task, args=(task_id, params, 'austin'))
    thread.daemon = True
    thread.start()
    
    return jsonify({'task_id': task_id})

@app.route('/api/tasks/charm/budapest', methods=['POST'])
def start_budapest_task():
    global task_counter
    params = request.json
    
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
    
    thread = threading.Thread(target=run_charm_searcher_task, args=(task_id, params, 'budapest'))
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
    os.makedirs('templates', exist_ok=True)
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
