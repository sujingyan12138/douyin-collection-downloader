import requests
from tqdm import tqdm
import json
import os
import hashlib

# 收藏夹请求头
header = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0",
    "Referer": "https://www.douyin.com/user/self?from_tab_name=main&showSubTab=favorite_folder&showTab=favorite_collection",
    "Cookie": "SEARCH_RESULT_LIST_TYPE=%22single%22; hevc_supported=true; bd_ticket_guard_client_web_domain=2; enter_pc_once=1; UIFID=30ff7b230d01f3ed4fd5546706fc508e0725b8a99e0ba4197a991a959864baf0a147a14ae43c4497055540a41a0b67e39c9e1c9393ad734368ab84196b6c5a626a3f5f753785d0fb51bf273843de00a8acf4dfc0b33813227adef4445e4287d77518cb69cea4180a1b441769d1a27dda8a2f82d31d2259939068b69f809a98fd97a52a938e1adc0518efcda0cedaa34f1b34d98374afa5fb8cff43e06626e650; d_ticket=be4ceca4a080a0c247a2e64bba89c355436ab; passport_assist_user=Cjxii1Zm6Gbkz1KoX7pUNKJuDIoh3dbjASanqH_eb__Grl8Cy8Lj-tov7_pp15B9SIj1Ih6bdS0ZFehWX1UaSgo8AAAAAAAAAAAAAE-ATLEnDLZNNhuWsqnQD0H8j5hIvaXsvCpbM5NsHyx2Ha1-KQpoGouVoSHt7etPFn2MEOXo_A0Yia_WVCABIgEDjVHsGw%3D%3D; uid_tt=ec66a13b2e841d8670bc75fc12c9c3e1; uid_tt_ss=ec66a13b2e841d8670bc75fc12c9c3e1; sid_tt=c7295dca4c16ff978a2913eab1fb9914; sessionid=c7295dca4c16ff978a2913eab1fb9914; sessionid_ss=c7295dca4c16ff978a2913eab1fb9914; is_staff_user=false; _bd_ticket_crypt_cookie=557a379be2ce331259703cb2e9a2c29a; login_time=1758500621966; live_use_vvc=%22false%22; my_rd=2; is_dash_user=1; session_tlb_tag_bk=sttt%7C10%7CxyldykwW_5eKKRPqsfuZFP________-ufAfH4CEHWxgwXZDDdlcEr-76sjoR-K3ZPEPet1U1Lk0%3D; enter_pc_first_on_day=20251210; __druidClientInfo=JTdCJTIyY2xpZW50V2lkdGglMjIlM0E0MzklMkMlMjJjbGllbnRIZWlnaHQlMjIlM0E4NDklMkMlMjJ3aWR0aCUyMiUzQTQzOSUyQyUyMmhlaWdodCUyMiUzQTg0OSUyQyUyMmRldmljZVBpeGVsUmF0aW8lMjIlM0ExLjYyMDAwMDEyMzk3NzY2MTElMkMlMjJ1c2VyQWdlbnQlMjIlM0ElMjJNb3ppbGxhJTJGNS4wJTIwKFdpbmRvd3MlMjBOVCUyMDEwLjAlM0IlMjBXaW42NCUzQiUyMHg2NCklMjBBcHBsZVdlYktpdCUyRjUzNy4zNiUyMChLSFRNTCUyQyUyMGxpa2UlMjBHZWNrbyklMjBDaHJvbWUlMkYxNDMuMC4wLjAlMjBTYWZhcmklMkY1MzcuMzYlMjBFZGclMkYxNDMuMC4wLjAlMjIlN0Q=; __live_version__=%221.1.4.6396%22; sid_guard=c7295dca4c16ff978a2913eab1fb9914%7C1767445358%7C5184000%7CWed%2C+04-Mar-2026+13%3A02%3A38+GMT; session_tlb_tag=sttt%7C3%7CxyldykwW_5eKKRPqsfuZFP_________JtTXBZj8xaNtKeRJ9O9QNGQVSRSHeqnvngoVBJGYvuXQ%3D; sid_ucp_v1=1.0.0-KDA3ZDAyMzFlOWZlNjg3YWY1M2NkMmU3OTJkNTFlZTAwNjE0ODRlY2YKHwjMqM6w-AEQ7qbkygYY7zEgDDCPk9zMBTgCQPEHSAQaAmxxIiBjNzI5NWRjYTRjMTZmZjk3OGEyOTEzZWFiMWZiOTkxNA; ssid_ucp_v1=1.0.0-KDA3ZDAyMzFlOWZlNjg3YWY1M2NkMmU3OTJkNTFlZTAwNjE0ODRlY2YKHwjMqM6w-AEQ7qbkygYY7zEgDDCPk9zMBTgCQPEHSAQaAmxxIiBjNzI5NWRjYTRjMTZmZjk3OGEyOTEzZWFiMWZiOTkxNA; PhoneResumeUidCacheV1=%7B%2266673939532%22%3A%7B%22time%22%3A1767493112776%2C%22blockingTime%22%3A1767752323491%2C%22noClick%22%3A0%7D%7D; publish_badge_show_info=%220%2C0%2C0%2C1768470372127%22; passport_csrf_token=120067de92411a937b0f7d2d58bdeb47; passport_csrf_token_default=120067de92411a937b0f7d2d58bdeb47; SelfTabRedDotControl=%5B%7B%22id%22%3A%227553183502452131892%22%2C%22u%22%3A22%2C%22c%22%3A21%7D%2C%7B%22id%22%3A%227550155493776295970%22%2C%22u%22%3A23%2C%22c%22%3A0%7D%2C%7B%22id%22%3A%227567320688214673418%22%2C%22u%22%3A20%2C%22c%22%3A19%7D%2C%7B%22id%22%3A%227543662639080015882%22%2C%22u%22%3A133%2C%22c%22%3A132%7D%2C%7B%22id%22%3A%227522321694816471076%22%2C%22u%22%3A79%2C%22c%22%3A79%7D%2C%7B%22id%22%3A%227213584394785654822%22%2C%22u%22%3A49%2C%22c%22%3A49%7D%5D; strategyABtestKey=%221768889630.337%22; ttwid=1%7CsPPkPUrD929XH3RrMqTmidFzoendRP8LdP2gCrGPt8s%7C1768889632%7C0ede004f8e5d5484d1e56cd1cf0867a4d64246ba69a34f4e579a76a524ae8cbd; __security_mc_1_s_sdk_crypt_sdk=def0648f-4ac4-937a; __security_mc_1_s_sdk_cert_key=c8108017-40b4-8ed9; __security_mc_1_s_sdk_sign_data_key_web_protect=bf6c6d2f-4aab-b346; FOLLOW_NUMBER_YELLOW_POINT_INFO=%22MS4wLjABAAAAAwZt5cR6Zpne2EihzXkVktsg2TmeB5YJpQ9HOuzr6aM%2F1768924800000%2F0%2F0%2F1768893654341%22; gulu_source_res=eyJwX2luIjoiZDk4YTY2N2IxZTM2YjNjODRhZmU3NmYwODBmNzZkNzNjMWE2ODljMDQxNmNmMzg1MDk3ZDZhYTRkZjYwY2YyNyJ9; playRecommendGuideTagCount=3; totalRecommendGuideTagCount=43; volume_info=%7B%22isMute%22%3Atrue%2C%22isUserMute%22%3Afalse%2C%22volume%22%3A0.985%7D; stream_recommend_feed_params=%22%7B%5C%22cookie_enabled%5C%22%3Atrue%2C%5C%22screen_width%5C%22%3A1581%2C%5C%22screen_height%5C%22%3A988%2C%5C%22browser_online%5C%22%3Atrue%2C%5C%22cpu_core_num%5C%22%3A32%2C%5C%22device_memory%5C%22%3A8%2C%5C%22downlink%5C%22%3A9%2C%5C%22effective_type%5C%22%3A%5C%224g%5C%22%2C%5C%22round_trip_time%5C%22%3A0%7D%22; FOLLOW_LIVE_POINT_INFO=%22MS4wLjABAAAAAwZt5cR6Zpne2EihzXkVktsg2TmeB5YJpQ9HOuzr6aM%2F1768924800000%2F0%2F0%2F1768893895011%22; sdk_source_info=7e276470716a68645a606960273f276364697660272927676c715a6d6069756077273f2771777060272927666d776a68605a607d71606b766c6a6b5a7666776c7571273f275e58272927666a6b766a69605a696c6061273f27636469766027292762696a6764695a7364776c6467696076273f275e582729277672715a646971273f2763646976602729277f6b5a666475273f2763646976602729276d6a6e5a6b6a716c273f2763646976602729276c6b6f5a7f6367273f27636469766027292771273f27353633353536363c3d3d333234272927676c715a75776a716a666a69273f2763646976602778; bit_env=SFAQ8v97Scgyu7KTKCGJyFYFgawp0dC5vGZZqBoTLRqWN1n-ULFUv7HBzZt4d_xjAxNmKmI0U13phR3xt6PlZpB8N-SX6ybSZ_sjjfbhAwP1AXrjAH8Y-71JCPBPMREocaQIbAnOqnfvCcN8HsgYTLHcfiPk-L_WNuPSlAKjI_6posJSoed5owWc9WcENRacT3QYbCOiSy_zZXZNpG6D3mp8K5kl-UC5wkQShEWmHIApPuRfDTOanqcrqkUp6NcIecB_AF5k6pHykpJqLRK9-P94IoVLYV_He-Dpb91ln2TK7T4-GaMNBDaHQ0wo2EMdbMz3mok6u72OUEfkmIKYB2apummxUrVjXB9QPlonQFC-0bK0j8_gqjPM2MIaaijQc0vH7I2IBtinhvAP2ynpu-DOK-1vxTHw393NOt6X7cTjbbRhEeqrS3RUmNAsGRZNU-koTcgyj2QDHCO2rKYAACQhbLVBRBlJpn5B_w8z505m5MOAy33Js1o6DBUsoYkD1Xo_9yiFa5MO3yz4vj6BsPSFYMEhw-68GcvJ4jsgS64%3D; bd_ticket_guard_client_data=eyJiZC10aWNrZXQtZ3VhcmQtdmVyc2lvbiI6MiwiYmQtdGlja2V0LWd1YXJkLWl0ZXJhdGlvbi12ZXJzaW9uIjoxLCJiZC10aWNrZXQtZ3VhcmQtcmVlLXB1YmxpYy1rZXkiOiJCSGt4SHZWbXpSN0dXVXlhclNOdnhoWTczMGsrQnFHdXBTVVl3T0UxOUc4bUJjdjZZQXd1aHJ1em5MSnEwZFFtQUIwQ2NFUDV0R2VwYmxzTUVKc1VzRjQ9IiwiYmQtdGlja2V0LWd1YXJkLXdlYi12ZXJzaW9uIjoyfQ%3D%3D; home_can_add_dy_2_desktop=%221%22; odin_tt=81a5e86c729e78d76c5000fb177df88601f187ea1991d21188b92c916e6bc6a7dcf775e882de7f7ad060d573fec7ade7; bd_ticket_guard_client_data_v2=eyJyZWVfcHVibGljX2tleSI6IkJIa3hIdlZtelI3R1dVeWFyU052eGhZNzMwaytCcUd1cFNVWXdPRTE5RzhtQmN2NllBd3VocnV6bkxKcTBkUW1BQjBDY0VQNXRHZXBibHNNRUpzVXNGND0iLCJ0c19zaWduIjoidHMuMi43NGJjNWI0NjRhMWNlYTM2M2ZiMDU0NmI4ZDEzZDliMTU3OGFhZTQ2OTg3MDI2ZjE0NmNiNDQ5NmFiMDVhNTRiYzRmYmU4N2QyMzE5Y2YwNTMxODYyNGNlZGExNDkxMWNhNDA2ZGVkYmViZWRkYjJlMzBmY2U4ZDRmYTAyNTc1ZCIsInJlcV9jb250ZW50Ijoic2VjX3RzIiwicmVxX3NpZ24iOiJLc2d2bDN6WGpTSTdZaEZKUDRBc3Y1SEhsM3YvOXd6anh3VGlRUlpoS0M4PSIsInNlY190cyI6IiNRTUJjcVFOL3Q4SlczVC9lTFZ1UTlJN2FhTWtSNHFjMzAvWGN3dmhCcGJNTllaWUFTZmpvVjVBZi8rT3EifQ%3D%3D; stream_player_status_params=%22%7B%5C%22is_auto_play%5C%22%3A0%2C%5C%22is_full_screen%5C%22%3A0%2C%5C%22is_full_webscreen%5C%22%3A0%2C%5C%22is_mute%5C%22%3A0%2C%5C%22is_speed%5C%22%3A1%2C%5C%22is_visible%5C%22%3A1%7D%22; biz_trace_id=2a3e8e39; IsDouyinActive=true"
}
# 收藏夹id
collects_id = '7597335900623918897'
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
