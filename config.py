import json
import os
import random

CONFIG_FILE = 'config.json'

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


def setup_config():
    """交互式配置设置"""
    print("=" * 50)
    print("抖音收藏夹下载器 - 配置向导")
    print("=" * 50)

    config = get_config()

    # User-Agent
    print("\n1. User-Agent 设置")
    current_ua = config.get('user_agent', '')
    if current_ua:
        print(f"当前 User-Agent: {current_ua[:60]}...")
        use_current = input("是否使用当前 User-Agent? (y/n, 默认 y): ").strip().lower()
        if use_current in ('', 'y', 'yes'):
            pass
        else:
            config['user_agent'] = get_random_user_agent()
            print(f"已自动设置 User-Agent: {config['user_agent'][:60]}...")
    else:
        config['user_agent'] = get_random_user_agent()
        print(f"已自动设置 User-Agent: {config['user_agent'][:60]}...")

    # Referer
    print("\n2. Referer 设置")
    current_referer = config.get('referer', '')
    if current_referer:
        print(f"当前 Referer: {current_referer}")
        use_current = input("是否使用当前 Referer? (y/n, 默认 y): ").strip().lower()
        if use_current in ('', 'y', 'yes'):
            pass
        else:
            config['referer'] = DEFAULT_REFERER
            print(f"已设置 Referer: {config['referer']}")
    else:
        config['referer'] = DEFAULT_REFERER
        print(f"已设置 Referer: {config['referer']}")

    # Cookie
    print("\n3. Cookie 设置")
    current_cookie = config.get('cookie', '')
    if current_cookie:
        print(f"当前 Cookie: {current_cookie[:50]}...")
        use_current = input("是否使用当前 Cookie? (y/n, 默认 y): ").strip().lower()
        if use_current in ('', 'y', 'yes'):
            pass
        else:
            config['cookie'] = input_cookie()
    else:
        config['cookie'] = input_cookie()

    # collects_id
    print("\n4. 收藏夹 ID 设置")
    current_collects_id = config.get('collects_id', '')
    if current_collects_id:
        print(f"当前收藏夹 ID: {current_collects_id}")
        use_current = input("是否使用当前收藏夹 ID? (y/n, 默认 y): ").strip().lower()
        if use_current in ('', 'y', 'yes'):
            pass
        else:
            config['collects_id'] = input_collects_id()
    else:
        config['collects_id'] = input_collects_id()

    # 保存配置
    print("\n" + "=" * 50)
    print("配置摘要:")
    print(f"  User-Agent: {config.get('user_agent', '')[:60]}...")
    print(f"  Referer: {config.get('referer', '')}")
    print(f"  Cookie: {config.get('cookie', '')[:50]}...")
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


def input_cookie():
    """引导用户输入 Cookie"""
    print("\n请从浏览器开发者工具中复制 Cookie:")
    print("  1. 打开抖音网页版并登录")
    print("  2. 按 F12 打开开发者工具")
    print("  3. 切换到 Network (网络) 标签")
    print("  4. 刷新页面，找到任意请求")
    print("  5. 在请求头中找到 Cookie，复制完整内容")
    print()

    # 尝试从剪贴板读取
    try:
        import pyperclip
        try:
            clipboard_content = pyperclip.paste()
            if clipboard_content and len(clipboard_content) > 50:
                print("检测到剪贴板内容，是否使用剪贴板中的 Cookie?")
                use_clipboard = input("(y/n, 默认 y): ").strip().lower()
                if use_clipboard in ('', 'y', 'yes'):
                    print("已使用剪贴板中的 Cookie")
                    return clipboard_content.strip()
        except Exception:
            pass
    except ImportError:
        pass

    cookie = input("请粘贴 Cookie: ").strip()
    while not cookie:
        print("Cookie 不能为空！")
        cookie = input("请粘贴 Cookie: ").strip()
    return cookie


def input_collects_id():
    """引导用户输入收藏夹 ID"""
    print("\n请输入收藏夹 ID:")
    print("  1. 打开抖音网页版，进入收藏夹页面")
    print("  2. 按 F12 打开开发者工具")
    print("  3. 切换到 Network (网络) 标签，筛选器输入 'list'")
    print("  4. 刷新页面，找到 collects/video/list 请求")
    print("  5. 在 URL 参数中找到 collects_id 的值")
    print()

    collects_id = input("请输入收藏夹 ID: ").strip()
    while not collects_id:
        print("收藏夹 ID 不能为空！")
        collects_id = input("请输入收藏夹 ID: ").strip()
    return collects_id


def get_headers(config):
    """从配置获取请求头"""
    return {
        "User-Agent": config.get('user_agent', ''),
        "Referer": config.get('referer', ''),
        "Cookie": config.get('cookie', '')
    }


def check_config(config):
    """检查配置是否完整"""
    required_fields = ['user_agent', 'referer', 'cookie', 'collects_id']
    missing = [field for field in required_fields if not config.get(field, '').strip()]
    return missing


def ensure_config():
    """确保配置存在且完整，不完整则引导配置"""
    config = get_config()
    missing = check_config(config)

    if missing:
        print(f"配置不完整，缺少: {', '.join(missing)}")
        print("请完成配置向导\n")
        config = setup_config()
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
