import requests
from tqdm import tqdm
import json
import os
import hashlib
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import ensure_config, get_headers, get_config
from config import DEFAULT_USER_AGENTS, DEFAULT_REFERER, APP_DIR


class DouyinDownloader:
    """抖音收藏夹下载器 - 优化版"""

    # 视频画质优先级（从高到低）
    VIDEO_QUALITY_PRIORITY = [
        'play_addr_h264_1080p',
        'play_addr_h264_720p',
        'play_addr_h264',
        'play_addr_1080p',
        'play_addr_720p',
        'play_addr',
        'download_addr'
    ]

    def __init__(self, config, max_workers=8):
        self.config = config
        self.headers = get_headers(config)
        self.collects_id = config.get('collects_id', '')
        self.max_workers = max_workers

        # 创建 Session 复用连接
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # 视频下载专用 headers
        self.video_headers = self._get_video_headers()

        # 已下载缓存（内存中）
        self.downloaded_cache = {}  # {author_clean: set(md5)}
        self.download_count = {}    # {author_clean: int}
        self.cache_lock = threading.Lock()
        self.file_lock = threading.Lock()

        # 基础目录
        self.base_dir = os.path.join(APP_DIR, '抖音收藏夹下载')
        os.makedirs(self.base_dir, exist_ok=True)

        # 初始化缓存
        self._init_cache()

    def _get_video_headers(self):
        """获取视频下载headers，从config读取User-Agent保持一致"""
        return {
            "User-Agent": self.headers.get("User-Agent", ""),
            "Referer": "https://www.douyin.com/",
            "Accept": "*/*",
            "Accept-Encoding": "identity",
            "Range": "bytes=0-",
            "sec-fetch-dest": "video",
            "sec-fetch-mode": "no-cors",
            "sec-fetch-site": "cross-site"
        }

    def _init_cache(self):
        """初始化已下载缓存，读取所有log.txt到内存"""
        if not os.path.exists(self.base_dir):
            return

        for author_dir in os.listdir(self.base_dir):
            author_path = os.path.join(self.base_dir, author_dir)
            if os.path.isdir(author_path):
                log_path = os.path.join(author_path, 'log.txt')
                if os.path.exists(log_path):
                    try:
                        with open(log_path, 'r', encoding='utf-8') as f:
                            md5_set = set(line.strip() for line in f if line.strip())
                            self.downloaded_cache[author_dir] = md5_set
                            # 计算已下载数量（排除log.txt）
                            file_count = len([f for f in os.listdir(author_path) if f != 'log.txt'])
                            self.download_count[author_dir] = file_count
                    except Exception as e:
                        print(f"读取 {author_dir} 的log.txt失败: {e}")

    def clean_filename(self, filename):
        """清理文件名，移除或替换Windows文件系统不允许的字符"""
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        filename = filename.strip(' .')
        return filename if filename else "未知作者"

    def get_md5(self, uri):
        """计算uri的MD5"""
        if isinstance(uri, str):
            uri = uri.encode("utf-8")
        m = hashlib.md5()
        m.update(uri)
        return m.hexdigest()

    def _is_downloaded(self, author_clean, md5_hash):
        """检查是否已下载（线程安全）"""
        with self.cache_lock:
            if author_clean in self.downloaded_cache:
                return md5_hash in self.downloaded_cache[author_clean]
            return False

    def _mark_downloaded(self, author_clean, md5_hash, author_path):
        """标记为已下载（线程安全）"""
        with self.cache_lock:
            # 更新内存缓存
            if author_clean not in self.downloaded_cache:
                self.downloaded_cache[author_clean] = set()
            self.downloaded_cache[author_clean].add(md5_hash)

            # 更新下载计数
            if author_clean not in self.download_count:
                self.download_count[author_clean] = 0
            file_num = self.download_count[author_clean]
            self.download_count[author_clean] += 1

        # 写入log.txt（文件锁保护）
        with self.file_lock:
            log_path = os.path.join(author_path, 'log.txt')
            try:
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(f'{md5_hash}\n')
            except Exception as e:
                print(f"写入log.txt失败: {e}")

        return file_num

    def _get_next_file_num(self, author_clean):
        """获取下一个文件编号（线程安全）"""
        with self.cache_lock:
            if author_clean not in self.download_count:
                self.download_count[author_clean] = 0
            file_num = self.download_count[author_clean]
            self.download_count[author_clean] += 1
            return file_num

    def fetch_all_collections(self):
        """获取用户所有收藏夹列表"""
        print("正在获取收藏夹列表...")

        # 尝试多个可能的API端点
        endpoints = [
            'https://www.douyin.com/aweme/v1/web/collects/list/',
            'https://www.douyin.com/aweme/v1/web/collects/user/all/',
            'https://www.douyin.com/aweme/v1/web/collects/query/',
        ]

        for endpoint in endpoints:
            try:
                url = f'{endpoint}?device_platform=webapp&aid=6383&channel=channel_pc_web'
                response = self.session.get(url, timeout=30)

                if response.status_code == 200:
                    response_data = response.json()
                    collections = self._parse_collections_list(response_data)
                    if collections:
                        print(f"成功获取到 {len(collections)} 个收藏夹")
                        return collections
            except Exception as e:
                print(f"尝试端点 {endpoint} 时出错: {e}")
                continue

        # 如果API端点都失败，提供备选方案
        print("\n无法自动获取收藏夹列表，请使用备选方案：")
        print("1. 手动输入收藏夹ID")
        print("2. 或者尝试在浏览器中打开收藏夹页面，然后刷新页面")
        print("   在开发者工具的Network标签中查找 collects/video/list 请求")
        print("   从URL参数中复制 collects_id 的值\n")

        return []

    def _parse_collections_list(self, response_data):
        """解析收藏夹列表响应"""
        collections = []

        # 尝试多种可能的响应结构
        if isinstance(response_data, dict):
            # 结构1: data -> collects 或类似
            data = response_data.get('data', {})
            if isinstance(data, dict):
                collects_list = data.get('collects', []) or data.get('collects_list', [])
                if collects_list:
                    for item in collects_list:
                        if isinstance(item, dict):
                            coll_id = item.get('collects_id') or item.get('id') or item.get('coll_id')
                            coll_name = item.get('collects_name') or item.get('name') or item.get('title')
                            if coll_id and coll_name:
                                collections.append({
                                    'id': str(coll_id),
                                    'name': coll_name
                                })

            # 结构2: 直接在response_data中
            if not collections:
                collects_list = response_data.get('collects', []) or response_data.get('collects_list', [])
                if collects_list:
                    for item in collects_list:
                        if isinstance(item, dict):
                            coll_id = item.get('collects_id') or item.get('id') or item.get('coll_id')
                            coll_name = item.get('collects_name') or item.get('name') or item.get('title')
                            if coll_id and coll_name:
                                collections.append({
                                    'id': str(coll_id),
                                    'name': coll_name
                                })

        return collections

    def fetch_collections(self):
        """获取指定收藏夹的内容"""
        if not self.collects_id:
            print("错误: 未设置收藏夹ID")
            return []

        cursor = 0
        all_media = []

        print(f"正在获取收藏夹内容 (ID: {self.collects_id})...")

        for i in range(17):
            url = f'https://www.douyin.com/aweme/v1/web/collects/video/list/?device_platform=webapp&aid=6383&channel=channel_pc_web&collects_id={self.collects_id}&cursor={cursor}'

            try:
                response = self.session.get(url, timeout=30)
                if response.status_code != 200:
                    print(f"请求失败，状态码: {response.status_code}")
                    break

                response_data = response.json()
                aweme_list = response_data.get('aweme_list')

                if not aweme_list:
                    print(f"第{i+1}页没有更多数据，停止爬取")
                    break

                print(f"正在处理第{i+1}页，包含{len(aweme_list)}个内容")
                media_list = self._parse_aweme_list(aweme_list)
                all_media.extend(media_list)
                cursor += 30

                # 添加延迟，避免请求过于频繁
                time.sleep(1)

            except Exception as e:
                print(f"处理第{i+1}页时出错: {e}")
                break

        print(f"共获取到 {len(all_media)} 个媒体文件")
        return all_media

    def _parse_aweme_list(self, aweme_list):
        """解析抖音返回的视频/图片列表"""
        media_list = []

        for video in tqdm(aweme_list, desc='解析媒体信息'):
            author = video['author']['nickname']

            if video.get('images'):  # 图文类型
                for img in video['images']:
                    if img.get('url_list') and len(img['url_list']) > 0:
                        media_list.append({
                            "author": author,
                            "type": "jpg",
                            "uri": img['uri'],
                            "url": img['url_list'][0]
                        })

            elif video.get('video'):  # 视频类型
                video_urls = self._get_highest_quality_video(video['video'])

                if video_urls:
                    media_list.append({
                        "author": author,
                        "type": "mp4",
                        "uri": video['video'].get('play_addr_h264', {}).get('uri', 'unknown'),
                        "url": video_urls[0],
                        "backup_urls": video_urls[1:]
                    })
                else:
                    print(f"警告: 视频 {video.get('aweme_id', 'unknown')} 没有可用的下载URL")

                # 封面图片
                if video['video'].get('cover') and video['video']['cover'].get('url_list'):
                    cover_urls = video['video']['cover']['url_list']
                    # 选择较高质量的封面
                    cover_url = cover_urls[1] if len(cover_urls) > 1 else cover_urls[0]
                    media_list.append({
                        "author": author,
                        "type": "jpg",
                        "uri": video['video']['cover']['uri'],
                        "url": cover_url
                    })

        return media_list

    def _get_highest_quality_video(self, video_data):
        """获取最高画质的视频URL列表"""
        all_urls = []

        # 按优先级检查各种画质
        for quality_key in self.VIDEO_QUALITY_PRIORITY:
            if video_data.get(quality_key) and video_data[quality_key].get('url_list'):
                urls = [url for url in video_data[quality_key]['url_list'] if url and url.startswith('http')]
                if urls:
                    all_urls.extend(urls)
                    # 如果找到了高优先级的，继续收集但优先使用高优先级的
                    # 不break，继续收集其他作为备用

        # 去重但保持顺序
        seen = set()
        unique_urls = []
        for url in all_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        return unique_urls

    def download_media(self, media_list):
        """并发下载所有媒体文件"""
        if not media_list:
            print("未获取到媒体文件")
            return

        print(f"总共需要下载 {len(media_list)} 个文件")
        print(f"使用 {self.max_workers} 个线程并发下载")

        success_count = 0
        failed_count = 0
        skipped_count = 0

        # 使用线程池并发下载
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_media = {executor.submit(self._download_single, media): media for media in media_list}

            # 处理结果
            for future in tqdm(as_completed(future_to_media), total=len(media_list), desc='下载进度'):
                media = future_to_media[future]
                try:
                    result = future.result()
                    if result == 'success':
                        success_count += 1
                    elif result == 'skipped':
                        skipped_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    print(f"下载 {media.get('uri', 'unknown')} 时出错: {e}")
                    failed_count += 1

        print(f"\n下载完成！成功: {success_count} 个，跳过: {skipped_count} 个，失败: {failed_count} 个")

    def _download_single(self, media):
        """下载单个媒体文件（线程安全）"""
        author = media['author']
        media_type = media['type']
        uri = media['uri']
        url = media['url']
        backup_urls = media.get('backup_urls', [])

        # 清理作者名称
        author_clean = self.clean_filename(author)
        author_path = os.path.join(self.base_dir, author_clean)

        # 计算MD5
        md5_hash = self.get_md5(uri)

        # 检查是否已下载
        if self._is_downloaded(author_clean, md5_hash):
            return 'skipped'

        # 确保作者目录存在
        os.makedirs(author_path, exist_ok=True)

        # 确保log.txt存在
        log_path = os.path.join(author_path, 'log.txt')
        if not os.path.exists(log_path):
            with open(log_path, 'w', encoding='utf-8') as f:
                pass

        # 获取文件编号
        file_num = self._get_next_file_num(author_clean)
        file_path = os.path.join(author_path, f'{file_num}.{media_type}')

        # 尝试下载
        max_retries = 3
        for retry in range(max_retries):
            try:
                current_url = url
                headers = self.video_headers if media_type == 'mp4' else self.headers

                if media_type == 'mp4':
                    # 视频下载（流式）
                    response = self.session.get(current_url, headers=headers, timeout=60, stream=True)

                    # 如果主URL失败，尝试备用URL
                    if response.status_code not in [200, 206] and backup_urls:
                        for backup_url in backup_urls:
                            response = self.session.get(backup_url, headers=headers, timeout=60, stream=True)
                            if response.status_code in [200, 206]:
                                current_url = backup_url
                                break
                else:
                    # 图片下载
                    response = self.session.get(current_url, timeout=30)

                if response.status_code in [200, 206]:
                    # 流式写入文件
                    file_size = 0
                    with open(file_path, 'wb') as f:
                        if media_type == 'mp4':
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                                    file_size += len(chunk)
                        else:
                            f.write(response.content)
                            file_size = len(response.content)

                    # 检查文件大小
                    if media_type == 'mp4' and file_size < 1024:
                        print(f"警告: 视频文件过小({file_size}字节)，可能下载失败")
                        if retry < max_retries - 1:
                            continue
                        else:
                            return 'failed'

                    # 标记为已下载
                    self._mark_downloaded(author_clean, md5_hash, author_path)
                    return 'success'
                else:
                    print(f"下载失败，状态码: {response.status_code}")
                    if retry == max_retries - 1:
                        return 'failed'

            except Exception as e:
                if retry == max_retries - 1:
                    print(f"下载失败: {e}")
                    return 'failed'
                else:
                    time.sleep(2)  # 重试前等待

        return 'failed'

    def verify_downloads(self):
        """验证下载的文件（只验证本次新增的）"""
        print("\n正在验证下载的文件...")

        total_files = 0
        valid_files = 0
        invalid_files = 0

        for author_dir in os.listdir(self.base_dir):
            author_path = os.path.join(self.base_dir, author_dir)
            if os.path.isdir(author_path):
                for file_name in os.listdir(author_path):
                    if file_name != 'log.txt':
                        file_path = os.path.join(author_path, file_name)
                        total_files += 1

                        try:
                            file_size = os.path.getsize(file_path)
                            if file_name.endswith('.mp4'):
                                if file_size > 102400:  # > 100KB
                                    valid_files += 1
                                else:
                                    print(f"无效视频文件: {author_dir}/{file_name} (大小: {file_size}字节)")
                                    invalid_files += 1
                            elif file_name.endswith('.jpg'):
                                if file_size > 10240:  # > 10KB
                                    valid_files += 1
                                else:
                                    print(f"无效图片文件: {author_dir}/{file_name} (大小: {file_size}字节)")
                                    invalid_files += 1
                            else:
                                valid_files += 1
                        except Exception as e:
                            print(f"检查文件时出错 {file_path}: {e}")
                            invalid_files += 1

        print(f"文件验证完成！")
        print(f"总文件数: {total_files}")
        print(f"有效文件: {valid_files}")
        print(f"无效文件: {invalid_files}")


def main():
    # 先创建一个临时下载器用于配置（只初始化Session，不初始化缓存）
    # 创建一个临时配置用于初始化
    temp_config = get_config() or {}
    if not temp_config.get('user_agent'):
        temp_config['user_agent'] = DEFAULT_USER_AGENTS[0]
    if not temp_config.get('referer'):
        temp_config['referer'] = DEFAULT_REFERER

    # 创建临时下载器用于获取收藏夹列表
    temp_downloader = None
    try:
        temp_downloader = DouyinDownloader(temp_config, max_workers=1)
    except Exception:
        pass

    # 加载配置
    config = ensure_config(temp_downloader)
    if not config:
        print("配置加载失败，程序退出")
        return

    # 创建正式下载器
    downloader = DouyinDownloader(config, max_workers=8)

    # 获取收藏夹内容
    media_list = downloader.fetch_collections()

    # 下载媒体文件
    downloader.download_media(media_list)

    # 验证下载
    downloader.verify_downloads()


if __name__ == '__main__':
    main()
