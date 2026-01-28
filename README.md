#                     python批量爬取抖音收藏夹图片和视频

 **目录**

[功能展示](#功能展示)

[代码](#代码)

[如何使用](#如何使用)

[环境准备](#环境准备)

[指定要下载的文件夹](#指定要下载的文件夹)

[收藏夹id](#收藏夹id)

[User-Agent、Cookie、Referer](#User-Agent、Cookie、Referer)

------



# 功能展示

# ![img](https://i-blog.csdnimg.cn/direct/88e8469c57a9462b8c197a2f6365d800.png)![点击并拖拽以移动](data:image/gif;base64,R0lGODlhAQABAPABAP///wAAACH5BAEKAAAALAAAAAABAAEAAAICRAEAOw==)![img](https://i-blog.csdnimg.cn/direct/8dfaca673131451b8ea94e44ea27457f.png)![点击并拖拽以移动](data:image/gif;base64,R0lGODlhAQABAPABAP///wAAACH5BAEKAAAALAAAAAABAAEAAAICRAEAOw==)编代码

```python
import requests
from tqdm import tqdm
import json
import os
import hashlib

# 收藏夹请求头
header = {
    "User-Agent": "",
    "Referer": "",
    "Cookie": ""
}
# 收藏夹id
collects_id = ''
# 指针
cursor = 0
# 收藏夹url
url = 'https://www.douyin.com/aweme/v1/web/collects/video/list/?device_platform=webapp&aid=6383&channel=channel_pc_web&collects_id={collects_id}&cursor={cursor}'
# 收藏夹

images = []


# 处理数据
def Date():
    # 指针
    cursor = 0
    # 意味着最多扫描 17*30 = 510 个视频（接近500个）
    for i in range(17):
        _url = url.format(collects_id=collects_id, cursor = cursor)
        try:
            dy_rs = requests.get(url=_url, headers=header, timeout=30)
            if dy_rs.status_code != 200:
                print(f"请求失败，状态码: {dy_rs.status_code}")
                break
                
            response_data = dy_rs.json()
            if response_data.get('aweme_list') is None or len(response_data['aweme_list']) == 0:
                print(f"第{i+1}页没有更多数据，停止爬取")
                break
            else:
                print(f"正在处理第{i+1}页，包含{len(response_data['aweme_list'])}个内容")
                getUrl(response_data)
                cursor += 30
                
                # 添加延迟，避免请求过于频繁
                import time
                time.sleep(1)
                
        except Exception as e:
            print(f"处理第{i+1}页时出错: {e}")
            break

# 获取视频/图片url
def getUrl(res_json):
    for video in tqdm(res_json['aweme_list'], desc='获取视频/图片url'):
        # print(json.dumps(video, sort_keys=True, indent=2))
        # 获取作者 name
        author = video['author']['nickname']
        # 获取文案
        # ptitle = video['desc']
        if video.get('images'):  # 图文类型
            for img in video['images']:
                # 添加安全检查，确保url_list存在且不为空
                if img.get('url_list') and len(img['url_list']) > 0:
                    images.append({"author": author, "type": "jpg", "uri": img['uri'], "url": img['url_list'][0]})
                else:
                    print(f"警告: 图片 {img.get('uri', 'unknown')} 的url_list为空或不存在")
        elif video.get('video'):  # 视频类型
            # 尝试多种视频URL格式
            video_urls = []
            
            # 方法1: play_addr_h264
            if video['video'].get('play_addr_h264') and video['video']['play_addr_h264'].get('url_list'):
                for url_item in video['video']['play_addr_h264']['url_list']:
                    if url_item and url_item.startswith('http'):
                        video_urls.append(url_item)
            
            # 方法2: play_addr
            if video['video'].get('play_addr') and video['video']['play_addr'].get('url_list'):
                for url_item in video['video']['play_addr']['url_list']:
                    if url_item and url_item.startswith('http'):
                        video_urls.append(url_item)
            
            # 方法3: download_addr
            if video['video'].get('download_addr') and video['video']['download_addr'].get('url_list'):
                for url_item in video['video']['download_addr']['url_list']:
                    if url_item and url_item.startswith('http'):
                        video_urls.append(url_item)
            
            # 如果找到视频URL，添加到下载列表
            if video_urls:
                # 选择第一个可用的URL
                images.append({"author": author, "type": "mp4", "uri": video['video'].get('play_addr_h264', {}).get('uri', 'unknown'),
                               "url": video_urls[0], "backup_urls": video_urls[1:]})
            else:
                print(f"警告: 视频 {video.get('aweme_id', 'unknown')} 没有可用的下载URL")
            
            # 封面图片url - 添加安全检查
            if video['video'].get('cover') and video['video']['cover'].get('url_list') and len(video['video']['cover']['url_list']) > 1:
                images.append({"author": author, "type": "jpg", "uri": video['video']['cover']['uri'],
                               "url": video['video']['cover']['url_list'][1]})
            else:
                print(f"警告: 视频 {video.get('aweme_id', 'unknown')} 的cover url_list为空或元素不足")


# 下载图片和视频
def download_media(images):
    if len(images) == 0:
        print("未获取到 视频url")
        return
    
    print(f"总共需要下载 {len(images)} 个文件")
    
    # 创建抖音收藏夹下载文件夹 在脚本当前目录
    if not os.path.exists('抖音收藏夹下载'):
        os.makedirs('抖音收藏夹下载')

    # 统计下载结果
    success_count = 0
    failed_count = 0
    
    for im in tqdm(images, desc='正在下载'):
        try:
            # 清理作者名称，确保文件夹名称合法
            clean_author = clean_filename(im["author"])
            # 创建 博主文件夹，存放同个博主的内容
            if not os.path.exists(f'抖音收藏夹下载/{clean_author}'):
                os.makedirs(f'抖音收藏夹下载/{clean_author}')
                open(f'抖音收藏夹下载/{clean_author}/log.txt', "w").close()

            # 判断 当前url是否已经下载过
            downloaded = False
            md5 = f'{get_md5(im["uri"])}\n'
            with open(f'抖音收藏夹下载/{clean_author}/log.txt', 'r', encoding='utf-8') as f:
                file_lines = f.readlines()
            for _md5 in file_lines:
                if _md5 == md5:
                    downloaded = True
                    break

            # 如果没下载过则下载
            if not downloaded:
                num_png = len(os.listdir(f'抖音收藏夹下载/{clean_author}'))
                file_path = f'抖音收藏夹下载/{clean_author}/{num_png}.{im["type"]}'
                
                # 添加重试机制
                max_retries = 3
                for retry in range(max_retries):
                    try:
                        # 为视频下载添加特殊的请求头
                        if im["type"] == "mp4":
                            video_headers = {
                                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
                                "Referer": "https://www.douyin.com/",
                                "Accept": "*/*",
                                "Accept-Encoding": "identity",
                                "Range": "bytes=0-",
                                "sec-fetch-dest": "video",
                                "sec-fetch-mode": "no-cors",
                                "sec-fetch-site": "cross-site"
                            }
                            
                            # 尝试主URL
                            current_url = im["url"]
                            response = requests.get(url=current_url, headers=video_headers, timeout=60, stream=True)
                            
                            # 如果主URL失败，尝试备用URL
                            if response.status_code not in [200, 206] and im.get("backup_urls"):
                                for backup_url in im["backup_urls"]:
                                    print(f"主URL失败，尝试备用URL: {backup_url[:50]}...")
                                    response = requests.get(url=backup_url, headers=video_headers, timeout=60, stream=True)
                                    if response.status_code in [200, 206]:
                                        current_url = backup_url
                                        break
                        else:
                            response = requests.get(url=im["url"], timeout=30)
                        
                        if response.status_code == 200 or response.status_code == 206:
                            # 检查文件大小，过滤掉过小的文件（可能是错误页面）
                            content_length = len(response.content)
                            if im["type"] == "mp4" and content_length < 1024:  # 视频小于1KB可能是错误
                                print(f"警告: 视频文件过小({content_length}字节)，可能下载失败")
                                if retry < max_retries - 1 and im.get("backup_urls"):
                                    print(f"尝试备用URL...")
                                    continue
                                else:
                                    failed_count += 1
                                    break
                            
                            with open(file_path, 'wb') as f:
                                f.write(response.content)
                            
                            # 记录下载成功
                            with open(f'抖音收藏夹下载/{clean_author}/log.txt', 'a', encoding='utf-8') as f:
                                f.write(f'{md5}')
                            
                            success_count += 1
                            break  # 下载成功，跳出重试循环
                        else:
                            print(f"下载失败，状态码: {response.status_code}")
                            if retry == max_retries - 1:
                                failed_count += 1
                            
                    except Exception as e:
                        if retry == max_retries - 1:
                            print(f"下载失败: {e}")
                            failed_count += 1
                        else:
                            print(f"第{retry+1}次重试下载...")
                            import time
                            time.sleep(2)  # 重试前等待2秒
                            
        except Exception as e:
            print(f"处理文件时出错: {e}")
            failed_count += 1
    
    print(f"\n下载完成！成功: {success_count} 个，失败: {failed_count} 个")


def get_md5(url):
    # 因为python3运行内存中编码方式为unicode，所以将url md5压缩之前首先需要编码为utf8。
    if isinstance(url, str):
        url = url.encode("utf-8")
    m = hashlib.md5()
    m.update(url)
    return m.hexdigest()


def clean_filename(filename):
    """清理文件名，移除或替换Windows文件系统不允许的字符"""
    # Windows不允许的字符: < > : " | ? * \ /
    invalid_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    # 移除首尾的空格和点
    filename = filename.strip(' .')
    # 如果文件名为空，使用默认名称
    if not filename:
        filename = "未知作者"
    return filename


def verify_downloads():
    """验证下载的文件是否完整"""
    print("\n正在验证下载的文件...")
    
    if not os.path.exists('抖音收藏夹下载'):
        print("下载文件夹不存在")
        return
    
    total_files = 0
    valid_files = 0
    invalid_files = 0
    
    for author_dir in os.listdir('抖音收藏夹下载'):
        author_path = os.path.join('抖音收藏夹下载', author_dir)
        if os.path.isdir(author_path):
            for file_name in os.listdir(author_path):
                if file_name != 'log.txt':
                    file_path = os.path.join(author_path, file_name)
                    total_files += 1
                    
                    try:
                        file_size = os.path.getsize(file_path)
                        if file_name.endswith('.mp4'):
                            # 视频文件应该大于100KB
                            if file_size > 102400:
                                valid_files += 1
                            else:
                                print(f"无效视频文件: {author_dir}/{file_name} (大小: {file_size}字节)")
                                invalid_files += 1
                        elif file_name.endswith('.jpg'):
                            # 图片文件应该大于10KB
                            if file_size > 10240:
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


Date()
download_media(images)
verify_downloads()
```

![点击并拖拽以移动](data:image/gif;base64,R0lGODlhAQABAPABAP///wAAACH5BAEKAAAALAAAAAABAAEAAAICRAEAOw==)

# 如何使用

## 环境准备

这里默认准备好了python的运行环境，具体可以参考[pycharm从安装到全副武装，学起来才嗖嗖的快，图片超多，因为过度详细！_pycharm下载和环境配置-CSDN博客](https://blog.csdn.net/weixin_46211269/article/details/119934323?ops_request_misc=%7B%22request%5Fid%22%3A%22902aa9ca8d1faeea80b5196c2b12f4b7%22%2C%22scm%22%3A%2220140713.130102334..%22%7D&request_id=902aa9ca8d1faeea80b5196c2b12f4b7&biz_id=0&utm_medium=distribute.pc_search_result.none-task-blog-2~all~top_positive~default-1-119934323-null-null.142^v102^pc_search_result_base1&utm_term=pycharm安装教程&spm=1018.2226.3001.4187)

## 指定要下载的文件夹

在代码里面填入以下用户自己的参数即可

### 收藏夹id

1. 进入收藏夹页面
2. f12 --> 网络(network) --> 筛选器输入`list`
3. 刷新页面
    ![img](https://i-blog.csdnimg.cn/direct/39cfd3f1481a476c94a0e19e658121c2.png)![点击并拖拽以移动](data:image/gif;base64,R0lGODlhAQABAPABAP///wAAACH5BAEKAAAALAAAAAABAAEAAAICRAEAOw==)​
4. 将想要下载的收藏夹名字 一个一个试着搜索，搜索到了的文件就是对应收藏夹url响应内容
    ![img](https://i-blog.csdnimg.cn/direct/3643cd2fbea54e62b493a805880bd1d5.png)![点击并拖拽以移动](data:image/gif;base64,R0lGODlhAQABAPABAP///wAAACH5BAEKAAAALAAAAAABAAEAAAICRAEAOw==)​



### User-Agent、Cookie、Referer

还是刚刚找到收藏夹id的位置，点击标头，请求标头，里面就有这三个参数了，复制到代码里面即可

![img](https://i-blog.csdnimg.cn/direct/691e41714cbd4ba0ab8ea32f978ef791.png)![点击并拖拽以移动](data:image/gif;base64,R0lGODlhAQABAPABAP///wAAACH5BAEKAAAALAAAAAABAAEAAAICRAEAOw==)

### ![img](https://i-blog.csdnimg.cn/direct/3cf870d627f244af8108378406fdf4f6.png)![点击并拖拽以移动](data:image/gif;base64,R0lGODlhAQABAPABAP///wAAACH5BAEKAAAALAAAAAABAAEAAAICRAEAOw==)



### ![img](https://i-blog.csdnimg.cn/direct/8a86ca1e56fe49708ea45403e9214d9e.png)![点击并拖拽以移动](data:image/gif;base64,R0lGODlhAQABAPABAP///wAAACH5BAEKAAAALAAAAAABAAEAAAICRAEAOw==)

可以在代码的同级目录下建立  抖音收藏夹下载  的文件夹，视频和图片会自动按照博主名称保存在里面

### ![img](https://i-blog.csdnimg.cn/direct/3bdef7ae5e6d4334aea57f434426a625.png)