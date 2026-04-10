import json
import os
import random
import sqlite3
import shutil
import tempfile

CONFIG_FILE = 'config.json'

# 浏览器支持
try:
    import browser_cookie3
    BROWSER_COOKIE_AVAILABLE = True
except ImportError:
    BROWSER_COOKIE_AVAILABLE = False

# Selenium 支持
try:
    from selenium import webdriver
    from selenium.webdriver.edge.service import Service as EdgeService
    from selenium.webdriver.edge.options import Options as EdgeOptions
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

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
        # 使用 Edge 浏览器（Windows 自带）
        edge_options = EdgeOptions()
        edge_options.add_argument('--disable-gpu')
        edge_options.add_argument('--no-sandbox')
        edge_options.add_argument('--disable-dev-shm-usage')
        edge_options.add_argument('--start-maximized')

        # 启用性能日志以拦截网络请求
        edge_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

        driver = webdriver.Edge(options=edge_options)
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
        if not any(k in cookie_dict for k in ['sessionid', 'passport_csrf_token', 'ttwid', 'LOGIN_STATUS']):
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
    import requests

    collections = []

    try:
        # 先访问收藏夹页面，确保Cookie有效
        print("  正在访问收藏夹页面...")
        driver.get('https://www.douyin.com/user/self?from_tab_name=main&showSubTab=favorite_folder&showTab=favorite_collection')
        time.sleep(4)

        # 从Selenium获取当前所有Cookie
        selenium_cookies = driver.get_cookies()
        cookie_dict = {c['name']: c['value'] for c in selenium_cookies}
        cookie_str = '; '.join([f"{k}={v}" for k, v in cookie_dict.items()])

        # 获取User-Agent
        ua = driver.execute_script("return navigator.userAgent")

        # 直接用requests调用收藏夹列表API
        headers = {
            'User-Agent': ua,
            'Referer': 'https://www.douyin.com/',
            'Cookie': cookie_str,
        }

        # 尝试多个可能的API端点
        api_urls = [
            'https://www.douyin.com/aweme/v1/web/collects/list/?device_platform=webapp&aid=6383&channel=channel_pc_web',
            'https://www.douyin.com/aweme/v1/web/collects/list/?device_platform=webapp&aid=6383&channel=channel_pc_web&count=20&cursor=0',
        ]

        for api_url in api_urls:
            try:
                resp = requests.get(api_url, headers=headers, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    collects_list = data.get('collects_list', [])
                    if collects_list:
                        for item in collects_list:
                            coll_id = item.get('collects_id') or item.get('collects_id_str')
                            coll_name = item.get('collects_name')
                            if coll_id and coll_name:
                                collections.append({'id': str(coll_id), 'name': coll_name})
                        if collections:
                            print(f"  成功获取到 {len(collections)} 个收藏夹")
                            return collections
            except Exception as e:
                continue

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

    # 方法1: 使用 Selenium 自动获取（最可靠，可同时获取收藏夹）
    if SELENIUM_AVAILABLE:
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

    # 方法2: 使用 browser_cookie3 库（不支持获取收藏夹）
    if BROWSER_COOKIE_AVAILABLE:
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
