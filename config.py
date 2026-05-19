import json
import os
import random
import sqlite3
import shutil
import subprocess
import sys
import tempfile
import time
import glob
import builtins

APP_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(APP_DIR, 'config.json')

# 浏览器支持
browser_cookie3 = None
BROWSER_COOKIE_AVAILABLE = False


def _load_browser_cookie3():
    """延迟加载 browser_cookie3，并避开 Windows shadowcopy/WMI 导入失败"""
    global browser_cookie3, BROWSER_COOKIE_AVAILABLE
    if browser_cookie3 is not None:
        return True

    original_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == 'shadowcopy' or name.startswith('shadowcopy.'):
            raise ImportError('shadowcopy disabled')
        return original_import(name, globals, locals, fromlist, level)

    try:
        builtins.__import__ = guarded_import
        import browser_cookie3 as loaded_browser_cookie3
        browser_cookie3 = loaded_browser_cookie3
        BROWSER_COOKIE_AVAILABLE = True
        return True
    except Exception as e:
        print(f"  browser_cookie3 不可用: {e}")
        BROWSER_COOKIE_AVAILABLE = False
        return False
    finally:
        builtins.__import__ = original_import

# Selenium 支持
try:
    from selenium.webdriver.chrome.webdriver import WebDriver as ChromeWebDriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.edge.webdriver import WebDriver as EdgeWebDriver
    from selenium.webdriver.edge.options import Options as EdgeOptions
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# Chrome/Edge DevTools 协议支持（不依赖 chromedriver/msedgedriver）
try:
    import requests
    import websocket
    LOCAL_REQUESTS = requests.Session()
    LOCAL_REQUESTS.trust_env = False
    CDP_AVAILABLE = True
except Exception:
    LOCAL_REQUESTS = None
    CDP_AVAILABLE = False

# 默认 User-Agent 列表
DEFAULT_USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15'
]

DEFAULT_REFERER = 'https://www.douyin.com/'


def get_config():
    """读取配置文件，如果不存在则返回空配置"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"读取配置文件失败: {e}")
    return {}


def save_config(config):
    """保存配置到文件"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        print(f"配置已保存到 {CONFIG_FILE}")
        return True
    except Exception as e:
        print(f"保存配置文件失败: {e}")
        return False


def get_random_user_agent():
    """获取随机的 User-Agent"""
    return random.choice(DEFAULT_USER_AGENTS)


def _print_cookie_failure_hint():
    print("\n自动读取登录态失败，可能原因：")
    print("  1. 浏览器里还没有登录抖音网页版")
    print("  2. 登录态被系统/浏览器加密保护")
    print("  3. 当前登录态不在默认 profile 里")
    print("  4. 需要以当前登录用户身份运行程序")
    print("\n请先确认浏览器里已经打开并登录抖音网页版，再重试。")


def setup_config(downloader=None):
    """交互式配置设置 - 一次登录同时获取Cookie和收藏夹"""
    print("=" * 50)
    print("抖音收藏夹下载器 - 配置向导")
    print("=" * 50)

    config = get_config()
    collections_from_browser = []  # 存储从浏览器获取的收藏夹列表

    # User-Agent（自动设置）
    if not config.get('user_agent'):
        config['user_agent'] = get_random_user_agent()
    print(f"\n1. User-Agent: 已自动设置")

    # Referer（自动设置）
    if not config.get('referer'):
        config['referer'] = DEFAULT_REFERER
    print(f"2. Referer: 已自动设置")

    # Cookie + 收藏夹（一次性获取）
    print("\n3. 登录态和收藏夹设置")
    current_cookie = config.get('cookie', '')
    current_collects_id = config.get('collects_id', '')

    need_login = False
    if current_cookie and current_collects_id and current_collects_id.isdigit():
        print(f"  已有登录态和收藏夹ID: {current_collects_id}")
        use_current = input("  是否继续使用? (y/n, 默认 y): ").strip().lower()
        if use_current not in ('', 'y', 'yes'):
            need_login = True
    else:
        need_login = True

    if need_login:
        print("\n  正在启动浏览器，请登录抖音...")
        print("  登录后程序会自动获取Cookie和收藏夹列表")

        if SELENIUM_AVAILABLE:
            cookie_str, collections_from_browser = get_cookie_from_browser(also_get_collections=True)
            if cookie_str:
                config['cookie'] = cookie_str

                # 如果获取到收藏夹列表，让用户选择
                if collections_from_browser:
                    print(f"\n  成功获取到 {len(collections_from_browser)} 个收藏夹:")
                    config['collects_id'] = _select_from_collections(collections_from_browser)
                else:
                    print("\n  未能自动获取收藏夹列表")
                    config['collects_id'] = input_collects_id()
            else:
                _print_cookie_failure_hint()
                config['cookie'] = input_cookie()
                config['collects_id'] = input_collects_id()
        else:
            print("  Selenium 不可用，请手动配置")
            config['cookie'] = input_cookie()
            config['collects_id'] = input_collects_id()

    # 保存配置
    print("\n" + "=" * 50)
    print("配置摘要:")
    print(f"  User-Agent: {config.get('user_agent', '')[:50]}...")
    print(f"  Referer: {config.get('referer', '')}")
    print(f"  Cookie: {'已设置' if config.get('cookie') else '未设置'}")
    print(f"  收藏夹 ID: {config.get('collects_id', '')}")
    print("=" * 50)

    confirm = input("\n是否保存配置? (y/n, 默认 y): ").strip().lower()
    if confirm in ('', 'y', 'yes'):
        if save_config(config):
            return config
        else:
            print("配置保存失败，但将使用当前配置运行")
            return config
    else:
        print("配置未保存，将使用当前配置运行")
        return config


def _select_from_collections(collections):
    """从收藏夹列表中选择"""
    print("-" * 40)
    for idx, coll in enumerate(collections, 1):
        print(f"  {idx}. {coll['name']} (ID: {coll['id']})")
    print("-" * 40)

    while True:
        choice = input(f"\n  请选择收藏夹 (1-{len(collections)}): ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(collections):
                selected = collections[idx]
                print(f"  已选择: {selected['name']}")
                return selected['id']
            else:
                print(f"  请输入 1 到 {len(collections)} 之间的数字")
        except ValueError:
            # 也支持直接输入收藏夹名称
            for coll in collections:
                if choice == coll['name']:
                    print(f"  已选择: {coll['name']}")
                    return coll['id']
            print("  请输入有效的数字或收藏夹名称")


def _paste_cookie_from_clipboard():
    try:
        import pyperclip
        clipboard_content = pyperclip.paste()
        if clipboard_content and len(clipboard_content) > 50:
            return clipboard_content.strip()
    except Exception:
        pass
    return None


def input_cookie():
    """引导用户输入登录态"""
    clipboard_cookie = _paste_cookie_from_clipboard()
    if clipboard_cookie:
        return clipboard_cookie

    print("\n仍然无法自动获取登录态，请手动粘贴一次。")
    cookie = input("请粘贴 Cookie: ").strip()
    while not cookie:
        print("Cookie 不能为空！")
        cookie = input("请粘贴 Cookie: ").strip()
    return cookie


def input_collects_id():
    """引导用户输入收藏夹 ID"""
    print("\n" + "=" * 50)
    print("需要输入收藏夹ID（纯数字）")
    print("=" * 50)
    print("\n获取方法：")
    print("  1. 打开抖音网页版，进入你的收藏夹")
    print("  2. 按 F12 打开开发者工具，切换到 Network 标签")
    print("  3. 刷新页面，搜索 'collects'")
    print("  4. 找到请求URL中的 collects_id=数字 部分")
    print("  5. 复制那串数字（如：7626651548743030586）")
    print()

    collects_id = input("请粘贴收藏夹ID: ").strip()
    while not collects_id or not collects_id.isdigit():
        if collects_id and not collects_id.isdigit():
            print("错误：收藏夹ID必须是纯数字！")
        else:
            print("收藏夹ID不能为空！")
        collects_id = input("请粘贴收藏夹ID: ").strip()
    return collects_id


def get_headers(config):
    """从配置获取请求头"""
    return {
        "User-Agent": config.get('user_agent', ''),
        "Referer": config.get('referer', ''),
        "Cookie": config.get('cookie', '')
    }


def _cookie_dict_to_string(cookie_dict):
    """把 Cookie 字典转成请求头字符串"""
    return '; '.join([f'{k}={v}' for k, v in cookie_dict.items()])


def _is_douyin_login_cookie(cookie_dict):
    """判断 Cookie 是否包含抖音登录态"""
    return any(k in cookie_dict for k in ['sessionid', 'passport_csrf_token', 'ttwid', 'LOGIN_STATUS'])


def _get_browser_candidates():
    """查找本机可直接启动的 Chrome/Edge 浏览器"""
    candidates = []

    def app_path_from_registry(exe_name):
        if os.name != 'nt':
            return None
        try:
            import winreg
            registry_paths = [
                (winreg.HKEY_CURRENT_USER, rf'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}'),
                (winreg.HKEY_LOCAL_MACHINE, rf'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}'),
            ]
            for root, subkey in registry_paths:
                try:
                    with winreg.OpenKey(root, subkey) as key:
                        value, _ = winreg.QueryValueEx(key, None)
                        if value and os.path.exists(value):
                            return value
                except OSError:
                    continue
        except Exception:
            pass
        return None

    browser_specs = [
        ('Chrome', 'chrome.exe', [
            app_path_from_registry('chrome.exe'),
            os.path.join(os.environ.get('PROGRAMFILES', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
            os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
            *glob.glob(os.path.join(os.environ.get('PROGRAMFILES', ''), 'Google', 'Chrome', 'Application', '*', 'chrome.exe')),
            *glob.glob(os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Google', 'Chrome', 'Application', '*', 'chrome.exe')),
        ]),
        ('Edge', 'msedge.exe', [
            app_path_from_registry('msedge.exe'),
            os.path.join(os.environ.get('PROGRAMFILES', ''), 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
            os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Edge', 'Application', 'msedge.exe'),
            *glob.glob(os.path.join(os.environ.get('PROGRAMFILES', ''), 'Microsoft', 'Edge', 'Application', '*', 'msedge.exe')),
            *glob.glob(os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Microsoft', 'Edge', 'Application', '*', 'msedge.exe')),
        ]),
    ]

    seen_paths = set()
    for browser_name, command_name, paths in browser_specs:
        which_path = shutil.which(command_name)
        if which_path:
            paths.insert(0, which_path)

        for path in paths:
            if path and os.path.exists(path):
                normalized = os.path.normcase(os.path.abspath(path))
                if normalized not in seen_paths:
                    seen_paths.add(normalized)
                    candidates.append((browser_name, path))
                break

    return candidates


def _get_debug_json(port, endpoint, timeout=2):
    url = f'http://127.0.0.1:{port}{endpoint}'
    resp = LOCAL_REQUESTS.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _wait_for_cdp(port, timeout_seconds=20):
    deadline = time.time() + timeout_seconds
    last_error = None
    while time.time() < deadline:
        try:
            _get_debug_json(port, '/json/version', timeout=1)
            return True
        except Exception as e:
            last_error = e
            time.sleep(0.5)
    if last_error:
        print(f"  浏览器调试端口未就绪: {last_error}")
    return False


def _get_first_page_ws_url(port):
    targets = _get_debug_json(port, '/json/list', timeout=2)
    page_targets = [t for t in targets if t.get('type') == 'page' and t.get('webSocketDebuggerUrl')]
    for target in page_targets:
        if 'douyin.com' in (target.get('url') or ''):
            return target['webSocketDebuggerUrl']
    if page_targets:
        return page_targets[0]['webSocketDebuggerUrl']
    return None


def _cdp_call(ws, call_id, method, params=None):
    payload = {'id': call_id, 'method': method}
    if params is not None:
        payload['params'] = params
    ws.send(json.dumps(payload))

    while True:
        data = json.loads(ws.recv())
        if data.get('id') == call_id:
            if 'error' in data:
                raise RuntimeError(data['error'])
            return data.get('result', {})


def _read_cookies_from_cdp(port):
    ws_url = _get_first_page_ws_url(port)
    if not ws_url:
        raise RuntimeError('未找到可读取 Cookie 的浏览器页面')

    ws = websocket.create_connection(ws_url, timeout=8, http_proxy_host=None, http_proxy_port=None)
    try:
        call_id = 1
        try:
            _cdp_call(ws, call_id, 'Network.enable')
        except Exception:
            pass

        call_id += 1
        try:
            cookie_result = _cdp_call(ws, call_id, 'Network.getAllCookies')
        except Exception:
            call_id += 1
            cookie_result = _cdp_call(ws, call_id, 'Storage.getCookies')

        call_id += 1
        ua_result = _cdp_call(
            ws,
            call_id,
            'Runtime.evaluate',
            {'expression': 'navigator.userAgent', 'returnByValue': True},
        )
        user_agent = ua_result.get('result', {}).get('value') or DEFAULT_USER_AGENTS[0]
    finally:
        try:
            ws.close()
        except Exception:
            pass

    cookie_dict = {}
    for cookie in cookie_result.get('cookies', []):
        domain = (cookie.get('domain') or '').lower()
        if 'douyin.com' in domain or 'iesdouyin.com' in domain:
            cookie_dict[cookie.get('name')] = cookie.get('value', '')

    return cookie_dict, user_agent


def _close_cdp_browser(port):
    try:
        version_info = _get_debug_json(port, '/json/version', timeout=1)
        ws_url = version_info.get('webSocketDebuggerUrl')
        if not ws_url:
            return
        ws = websocket.create_connection(ws_url, timeout=3, http_proxy_host=None, http_proxy_port=None)
        try:
            _cdp_call(ws, 1, 'Browser.close')
        finally:
            try:
                ws.close()
            except Exception:
                pass
    except Exception:
        pass


def _terminate_process(process):
    if not process or process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=5)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass


def _start_cdp_browser(browser_name, browser_path, port, user_data_dir):
    args = [
        browser_path,
        f'--remote-debugging-port={port}',
        f'--user-data-dir={user_data_dir}',
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-popup-blocking',
        'https://www.douyin.com',
    ]
    print(f"  正在启动 {browser_name} 浏览器...")
    return subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _start_profile_browser(browser_name, browser_path, user_data_dir):
    args = [
        browser_path,
        f'--user-data-dir={user_data_dir}',
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-popup-blocking',
        'https://www.douyin.com',
    ]
    print(f"  正在启动 {browser_name} 浏览器...")
    return subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _get_profile_cookie_paths(user_data_dir):
    patterns = [
        os.path.join(user_data_dir, 'Default', 'Network', 'Cookies'),
        os.path.join(user_data_dir, 'Default', 'Cookies'),
        os.path.join(user_data_dir, '*', 'Network', 'Cookies'),
        os.path.join(user_data_dir, '*', 'Cookies'),
    ]
    paths = []
    for pattern in patterns:
        for path in glob.glob(pattern):
            if os.path.isfile(path) and path not in paths:
                paths.append(path)
    return paths


def _read_cookies_from_profile(browser_name, user_data_dir):
    if not _load_browser_cookie3():
        return {}

    key_file = os.path.join(user_data_dir, 'Local State')
    cookie_paths = _get_profile_cookie_paths(user_data_dir)
    if not cookie_paths:
        print("  未找到浏览器 Cookie 数据库")
        return {}

    if browser_name.lower() == 'edge':
        browser_func = browser_cookie3.edge
    else:
        browser_func = browser_cookie3.chrome

    last_error = None
    for cookie_file in cookie_paths:
        try:
            cookie_jar = browser_func(
                cookie_file=cookie_file,
                key_file=key_file if os.path.exists(key_file) else None,
            )
            cookie_dict = _extract_douyin_cookie(cookie_jar)
            if cookie_dict:
                return cookie_dict
        except Exception as e:
            last_error = e
            continue

    if last_error:
        print(f"  读取临时浏览器 Cookie 失败: {last_error}")
    return {}


def _get_cookie_with_temp_profile(also_get_collections=False):
    """使用临时浏览器 profile 登录，再直接读取 Cookie 数据库"""
    candidates = _get_browser_candidates()
    if not candidates:
        return (None, []) if also_get_collections else None
    if not _load_browser_cookie3():
        return (None, []) if also_get_collections else None

    print("\n  将打开一个全新的 Chrome/Edge 登录窗口")
    print("  登录成功后，请关闭这个浏览器窗口，再回到本窗口按回车")
    print("  这个方式不需要 chromedriver，也不会读取你的常用浏览器 profile")
    input("  按回车键继续...")

    last_error = None
    for browser_name, browser_path in candidates:
        process = None
        user_data_dir = tempfile.mkdtemp(prefix='douyin_profile_')
        try:
            process = _start_profile_browser(browser_name, browser_path, user_data_dir)
            print(f"\n  {browser_name} 已打开，请登录抖音网页版")
            print("  登录成功后请关闭浏览器窗口，然后回到这里按回车")
            input("  按回车键继续...")

            _terminate_process(process)
            process = None
            time.sleep(1)

            cookie_dict = _read_cookies_from_profile(browser_name, user_data_dir)
            if not _is_douyin_login_cookie(cookie_dict):
                print("  未检测到登录态，请确认刚才已经登录抖音网页版")
                continue

            collections = []
            if also_get_collections:
                print("\n  正在获取收藏夹列表...")
                try:
                    collections = _fetch_collections_with_cookie(cookie_dict, DEFAULT_USER_AGENTS[0])
                except Exception as e:
                    print(f"  获取收藏夹列表失败: {e}")
                if collections:
                    print(f"  成功获取到 {len(collections)} 个收藏夹")

            return (cookie_dict, collections) if also_get_collections else cookie_dict
        except Exception as e:
            last_error = e
            print(f"  {browser_name} 临时登录方式失败: {e}")
        finally:
            _terminate_process(process)
            try:
                shutil.rmtree(user_data_dir, ignore_errors=True)
            except Exception:
                pass

    if last_error:
        print(f"  临时浏览器登录方式失败: {last_error}")
    return (None, []) if also_get_collections else None


def _fetch_collections_with_cookie(cookie_dict, user_agent):
    """使用 Cookie 直接请求收藏夹列表"""
    collections = []
    cookie_str = _cookie_dict_to_string(cookie_dict)

    headers = {
        'User-Agent': user_agent or DEFAULT_USER_AGENTS[0],
        'Referer': 'https://www.douyin.com/',
        'Cookie': cookie_str,
    }

    api_urls = [
        'https://www.douyin.com/aweme/v1/web/collects/list/?device_platform=webapp&aid=6383&channel=channel_pc_web',
        'https://www.douyin.com/aweme/v1/web/collects/list/?device_platform=webapp&aid=6383&channel=channel_pc_web&count=20&cursor=0',
    ]

    for api_url in api_urls:
        try:
            resp = requests.get(api_url, headers=headers, timeout=15)
            if resp.status_code != 200:
                continue

            data = resp.json()
            collects_list = data.get('collects_list', [])
            if not collects_list and isinstance(data.get('data'), dict):
                collects_list = data['data'].get('collects_list', []) or data['data'].get('collects', [])

            for item in collects_list:
                coll_id = item.get('collects_id') or item.get('collects_id_str') or item.get('id')
                coll_name = item.get('collects_name') or item.get('name') or item.get('title')
                if coll_id and coll_name:
                    collections.append({'id': str(coll_id), 'name': coll_name})

            if collections:
                break
        except Exception:
            continue

    seen_ids = set()
    unique_collections = []
    for coll in collections:
        if coll['id'] not in seen_ids:
            seen_ids.add(coll['id'])
            unique_collections.append(coll)
    return unique_collections


def _get_cookie_with_cdp(also_get_collections=False):
    """使用 Chrome/Edge DevTools 协议获取 Cookie，不依赖浏览器 driver"""
    if not CDP_AVAILABLE:
        return (None, []) if also_get_collections else None

    candidates = _get_browser_candidates()
    if not candidates:
        print("  未找到可直接启动的 Chrome 或 Edge 浏览器")
        return (None, []) if also_get_collections else None

    print("\n  将直接打开 Chrome/Edge 登录窗口（无需 chromedriver）")
    print("  登录成功后回到本窗口按回车，程序会读取 Cookie 并关闭这个登录窗口")
    input("  按回车键继续...")

    last_error = None
    for browser_name, browser_path in candidates:
        process = None
        active_port = None
        user_data_dir = tempfile.mkdtemp(prefix='douyin_login_')
        try:
            for port in range(9222, 9253):
                process = _start_cdp_browser(browser_name, browser_path, port, user_data_dir)
                if _wait_for_cdp(port):
                    active_port = port
                    print(f"\n  {browser_name} 已打开，请在浏览器中登录抖音账号...")
                    print("  登录成功后回到这里按回车")
                    input("  按回车键继续...")

                    cookie_dict, user_agent = _read_cookies_from_cdp(port)
                    if not _is_douyin_login_cookie(cookie_dict):
                        print("  未检测到登录态，请确保已登录抖音网页版")
                        return (None, []) if also_get_collections else None

                    collections = []
                    if also_get_collections:
                        print("\n  正在获取收藏夹列表...")
                        collections = _fetch_collections_with_cookie(cookie_dict, user_agent)
                        if collections:
                            print(f"  成功获取到 {len(collections)} 个收藏夹")

                    return (cookie_dict, collections) if also_get_collections else cookie_dict

                _terminate_process(process)
                process = None

        except Exception as e:
            last_error = e
            print(f"  {browser_name} 登录窗口方式失败: {e}")
        finally:
            if active_port is not None:
                _close_cdp_browser(active_port)
                time.sleep(0.5)
            _terminate_process(process)
            try:
                shutil.rmtree(user_data_dir, ignore_errors=True)
            except Exception:
                pass

    if last_error:
        print(f"  浏览器登录窗口方式失败: {last_error}")
    return (None, []) if also_get_collections else None


def _create_selenium_options(options_class):
    """创建 Selenium 浏览器配置"""
    options = options_class()
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--start-maximized')

    # 启用性能日志以拦截网络请求
    options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    return options


def _start_selenium_browser():
    """按 Edge、Chrome 顺序启动可用浏览器"""
    browsers = [
        ('Edge', EdgeWebDriver, EdgeOptions),
        ('Chrome', ChromeWebDriver, ChromeOptions),
    ]

    last_error = None
    for browser_name, driver_factory, options_class in browsers:
        try:
            print(f"  正在尝试启动 {browser_name} 浏览器...")
            driver = driver_factory(options=_create_selenium_options(options_class))
            print(f"  已启动 {browser_name} 浏览器")
            return driver
        except Exception as e:
            last_error = e
            print(f"  {browser_name} 启动失败: {e}")

    if last_error:
        raise last_error
    raise RuntimeError("未找到可用的 Edge 或 Chrome 浏览器")


def _get_cookie_with_selenium(also_get_collections=False):
    """使用 Selenium 打开浏览器让用户登录，获取 Cookie

    Args:
        also_get_collections: 是否同时获取收藏夹列表

    Returns:
        如果 also_get_collections=False: 返回 cookie_dict 或 None
        如果 also_get_collections=True: 返回 (cookie_dict, collections_list) 或 (None, [])
    """
    if not SELENIUM_AVAILABLE:
        return (None, []) if also_get_collections else None

    print("\n  即将打开浏览器窗口，请在浏览器中登录抖音账号")
    print("  登录成功后，程序会自动获取登录态并关闭浏览器")
    input("  按回车键继续...")

    driver = None
    try:
        driver = _start_selenium_browser()
        driver.get('https://www.douyin.com')

        print("\n  浏览器已打开，请登录抖音账号...")
        print("  登录成功后，按回车键继续")
        input("  按回车键继续...")

        # 获取 Cookie
        cookies = driver.get_cookies()
        cookie_dict = {}
        if cookies:
            for c in cookies:
                cookie_dict[c['name']] = c['value']

        # 检查是否有登录态
        if not _is_douyin_login_cookie(cookie_dict):
            print("  未检测到登录态，请确保已登录")
            if driver:
                driver.quit()
            return (None, []) if also_get_collections else None

        # 如果需要获取收藏夹列表
        collections = []
        if also_get_collections:
            print("\n  正在获取收藏夹列表...")
            collections = _fetch_collections_with_selenium(driver)

        driver.quit()

        if also_get_collections:
            return (cookie_dict, collections)
        return cookie_dict

    except Exception as e:
        print(f"  Selenium 获取失败: {e}")
        if driver:
            try:
                driver.quit()
            except:
                pass
        return (None, []) if also_get_collections else None


def _fetch_collections_with_selenium(driver):
    """使用已登录的Selenium浏览器获取收藏夹列表"""
    import time

    collections = []

    try:
        # 先访问收藏夹页面，确保Cookie有效
        print("  正在访问收藏夹页面...")
        driver.get('https://www.douyin.com/user/self?from_tab_name=main&showSubTab=favorite_folder&showTab=favorite_collection')
        time.sleep(4)

        # 从Selenium获取当前所有Cookie
        selenium_cookies = driver.get_cookies()
        cookie_dict = {c['name']: c['value'] for c in selenium_cookies}

        # 获取User-Agent
        ua = driver.execute_script("return navigator.userAgent")

        collections = _fetch_collections_with_cookie(cookie_dict, ua)
        if collections:
            print(f"  成功获取到 {len(collections)} 个收藏夹")
            return collections

        # 如果API直接调用失败，尝试从性能日志获取
        print("  API直接调用失败，尝试从页面日志获取...")
        collections = _extract_collections_from_performance_logs(driver)

    except Exception as e:
        print(f"  获取收藏夹列表失败: {e}")

    return collections


def _extract_collections_from_performance_logs(driver):
    """从Selenium性能日志中提取收藏夹数据"""
    import json

    collections = []

    try:
        # 获取性能日志
        logs = driver.get_log('performance')
        print(f"  获取到 {len(logs)} 条性能日志")

        for log_entry in logs:
            try:
                log_data = json.loads(log_entry['message'])
                message = log_data.get('message', {})
                method = message.get('method', '')

                # 查找网络响应
                if method == 'Network.responseReceived':
                    params = message.get('params', {})
                    response = params.get('response', {})
                    url = response.get('url', '')

                    # 检查是否是收藏夹列表API (包含 collects 和 list)
                    if 'collects' in url and 'list' in url:
                        print(f"  找到收藏夹API: {url[:100]}...")
                        request_id = params.get('requestId')

                        # 尝试获取响应体
                        try:
                            response_body = driver.execute_cdp_cmd(
                                'Network.getResponseBody',
                                {'requestId': request_id}
                            )
                            body = response_body.get('body', '')
                            if body:
                                data = json.loads(body)
                                # 直接查找 collects_list
                                collects_list = data.get('collects_list', [])
                                if collects_list:
                                    for item in collects_list:
                                        coll_id = item.get('collects_id') or item.get('collects_id_str')
                                        coll_name = item.get('collects_name')
                                        if coll_id and coll_name:
                                            collections.append({
                                                'id': str(coll_id),
                                                'name': coll_name
                                            })
                                    print(f"  从API响应中提取到 {len(collections)} 个收藏夹")
                                    if collections:
                                        break  # 找到就退出
                        except Exception as e:
                            pass

            except Exception as e:
                continue

    except Exception as e:
        print(f"  性能日志分析失败: {e}")

    # 去重
    seen_ids = set()
    unique_collections = []
    for coll in collections:
        if coll['id'] not in seen_ids:
            seen_ids.add(coll['id'])
            unique_collections.append(coll)

    return unique_collections


def _load_cookie_jar(browser_func):
    """尝试读取浏览器 Cookie 账户数据"""
    try:
        return browser_func()
    except Exception as e:
        return None


def _extract_douyin_cookie(cookie_jar):
    cookie_dict = {}
    for cookie in cookie_jar:
        domain = (cookie.domain or '').lower()
        if 'douyin.com' in domain or 'iesdouyin.com' in domain:
            cookie_dict[cookie.name] = cookie.value
    return cookie_dict


def get_cookie_from_browser(also_get_collections=False):
    """尝试从浏览器自动读取抖音Cookie

    Args:
        also_get_collections: 是否同时获取收藏夹列表

    Returns:
        如果 also_get_collections=False: 返回 cookie_string 或 None
        如果 also_get_collections=True: 返回 (cookie_string, collections_list)
    """

    # 方法1: 临时浏览器 profile 登录后读取 Cookie 数据库（不依赖 driver/本地端口）
    if _get_browser_candidates():
        print("  尝试临时浏览器登录方式...")
        result = _get_cookie_with_temp_profile(also_get_collections=also_get_collections)

        if also_get_collections:
            cookie_dict, collections = result
            if cookie_dict:
                print(f"[OK] 成功获取到 {len(cookie_dict)} 个登录态 Cookie")
                if collections:
                    print(f"[OK] 成功获取到 {len(collections)} 个收藏夹")
                return (_cookie_dict_to_string(cookie_dict), collections)
        elif result:
            print(f"[OK] 成功获取到 {len(result)} 个登录态 Cookie")
            return _cookie_dict_to_string(result)

    # 方法2: 直接启动 Chrome/Edge 并通过 DevTools 协议读取 Cookie（不依赖 driver）
    cdp_browser_candidates = _get_browser_candidates() if CDP_AVAILABLE else []
    if CDP_AVAILABLE:
        print("  尝试直接打开 Chrome/Edge 登录窗口...")
        result = _get_cookie_with_cdp(also_get_collections=also_get_collections)

        if also_get_collections:
            cookie_dict, collections = result
            if cookie_dict:
                print(f"[OK] 成功获取到 {len(cookie_dict)} 个登录态 Cookie")
                if collections:
                    print(f"[OK] 成功获取到 {len(collections)} 个收藏夹")
                return (_cookie_dict_to_string(cookie_dict), collections)
        elif result:
            print(f"[OK] 成功获取到 {len(result)} 个登录态 Cookie")
            return _cookie_dict_to_string(result)

    # 方法3: 使用 Selenium 自动获取（需要浏览器 driver）
    if SELENIUM_AVAILABLE and not cdp_browser_candidates:
        print("  尝试 Selenium 自动检测...")
        result = _get_cookie_with_selenium(also_get_collections=also_get_collections)

        if also_get_collections:
            cookie_dict, collections = result
            if cookie_dict:
                print(f"[OK] 成功获取到 {len(cookie_dict)} 个登录态 Cookie")
                if collections:
                    print(f"[OK] 成功获取到 {len(collections)} 个收藏夹")
                return (_cookie_dict_to_string(cookie_dict), collections)
            return (None, [])
        else:
            if result:
                print(f"[OK] 成功获取到 {len(result)} 个登录态 Cookie")
                return _cookie_dict_to_string(result)
    elif SELENIUM_AVAILABLE and cdp_browser_candidates:
        print("  已尝试直接浏览器登录方式，跳过需要 driver 的 Selenium 方式")

    # 方法4: 使用 browser_cookie3 库（不支持获取收藏夹）
    if _load_browser_cookie3():
        browsers = [
            ('Chrome', browser_cookie3.chrome),
            ('Edge', browser_cookie3.edge),
            ('Firefox', browser_cookie3.firefox),
        ]

        for browser_name, browser_func in browsers:
            print(f"  尝试 {browser_name}...")

            cookie_jar = _load_cookie_jar(browser_func)
            if cookie_jar:
                cookie_dict = _extract_douyin_cookie(cookie_jar)
                if cookie_dict:
                    print(f"[OK] 成功从 {browser_name} 读取到登录态")
                    cookie_str = _cookie_dict_to_string(cookie_dict)
                    if also_get_collections:
                        return (cookie_str, [])  # browser_cookie3 无法获取收藏夹
                    return cookie_str

    if also_get_collections:
        return (None, [])
    return None


def check_config(config):
    """检查配置是否完整"""
    required_fields = ['user_agent', 'referer', 'cookie', 'collects_id']
    missing = [field for field in required_fields if not config.get(field, '').strip()]
    return missing


def select_collection_interactive(downloader):
    """交互式选择收藏夹"""
    print("\n" + "=" * 50)
    print("获取收藏夹列表...")
    print("=" * 50)

    collections = downloader.fetch_all_collections()

    if not collections:
        print("\n无法自动获取收藏夹列表，请输入收藏夹名称或ID")
        return input_collects_id()

    # 显示收藏夹列表
    print("\n你的收藏夹列表:")
    print("-" * 50)
    for idx, coll in enumerate(collections, 1):
        print(f"  {idx}. {coll['name']} (ID: {coll['id']})")
    print("-" * 50)

    # 让用户选择
    while True:
        choice = input(f"\n请选择收藏夹 (输入序号 1-{len(collections)}): ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(collections):
                selected = collections[idx]
                print(f"\n已选择收藏夹: {selected['name']}")
                return selected['id']
            else:
                print(f"请输入 1 到 {len(collections)} 之间的数字")
        except ValueError:
            print("请输入有效的数字")


def ensure_config(downloader=None):
    """确保配置存在且完整，不完整则引导配置"""
    config = get_config()
    missing = check_config(config)

    if missing:
        print(f"配置不完整，缺少: {', '.join(missing)}")
        print("请完成配置向导\n")
        config = setup_config(downloader)
    else:
        print("配置已加载，使用保存的设置")
        print(f"  收藏夹 ID: {config.get('collects_id')}")
        print(f"  User-Agent: {config.get('user_agent', '')[:50]}...")

    # 再次检查
    missing = check_config(config)
    if missing:
        print(f"错误: 配置仍然不完整，缺少: {', '.join(missing)}")
        print("请重新运行程序进行配置")
        return None

    return config


if __name__ == '__main__':
    setup_config()
