#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bilibili 视频关键词筛选爬取工具
支持：标题关键词筛选、简介关键词筛选、准确匹配、批量下载

Author: OpenClaw
Date: 2026-03-22
"""

import argparse
import json
import sys
from typing import List, Dict, Optional
import requests

# 尝试导入 bilibili_api，如果没有则提示安装
try:
    from bilibili_api import video, sync
    BILIBILI_API_AVAILABLE = True
except ImportError:
    BILIBILI_API_AVAILABLE = False

SEARCH_API = "https://api.bilibili.com/x/web-interface/search/all"
SEARCH_TYPE = "video"

class BilibiliVideoSpider:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
    
    def search_videos(self, keyword: str, page: int = 1, page_size: int = 30) -> List[Dict]:
        """搜索视频"""
        params = {
            "keyword": keyword,
            "page": page,
            "page_size": page_size,
            "search_type": SEARCH_TYPE
        }
        
        try:
            resp = self.session.get(SEARCH_API, params=params)
            data = resp.json()
            
            if data["code"] != 0:
                print(f"搜索错误: {data['message']}")
                return []
            
            # 提取视频结果
            result = []
            if "result" in data["data"] and "video" in data["data"]["result"]:
                result = data["data"]["result"]["video"]
            
            return result
        except Exception as e:
            print(f"请求异常: {e}")
            return []
    
    def filter_by_title(self, videos: List[Dict], keywords: List[str]) -> List[Dict]:
        """按标题关键词筛选"""
        if not keywords:
            return videos
        
        filtered = []
        for video in videos:
            title = video.get("title", "").lower()
            # 所有关键词都必须出现在标题中
            if all(k.lower() in title for k in keywords):
                filtered.append(video)
        
        return filtered
    
    def filter_by_description(self, videos: List[Dict], keywords: List[str]) -> List[Dict]:
        """按简介关键词筛选"""
        if not keywords:
            return videos
        
        filtered = []
        for video in videos:
            desc = video.get("description", "").lower()
            if all(k.lower() in desc for k in keywords):
                filtered.append(video)
        
        return filtered
    
    def get_video_url(self, bvid: str) -> str:
        """获取视频链接"""
        return f"https://www.bilibili.com/video/{bvid}/"
    
    def format_result(self, video: Dict) -> Dict:
        """格式化输出结果"""
        return {
            "bvid": video.get("bvid"),
            "aid": video.get("aid"),
            "title": video.get("title"),
            "description": video.get("description"),
            "author": video.get("author"),
            "duration": video.get("duration"),
            "play": video.get("play"),
            "video_url": self.get_video_url(video.get("bvid")),
            "pic": video.get("pic")
        }
    
    def search_and_filter(
        self,
        search_keyword: str,
        title_keywords: Optional[List[str]] = None,
        desc_keywords: Optional[List[str]] = None,
        max_pages: int = 5,
        page_size: int = 30
    ) -> List[Dict]:
        """完整搜索筛选流程"""
        all_results = []
        
        for page in range(1, max_pages + 1):
            print(f"正在搜索第 {page} 页...", file=sys.stderr)
            videos = self.search_videos(search_keyword, page, page_size)
            if not videos:
                break
            
            # 筛选
            if title_keywords:
                videos = self.filter_by_title(videos, title_keywords)
            if desc_keywords:
                videos = self.filter_by_description(videos, desc_keywords)
            
            # 格式化
            for v in videos:
                all_results.append(self.format_result(v))
        
        return all_results
    
    def download_video(self, bvid: str, output_dir: str = "./download", quality: Optional[int] = None) -> bool:
        """
        下载单个视频 - 独立实现，不依赖bilibili-api内置下载，兼容所有版本
        自己获取URL -> 自己下载 -> 自己用ffmpeg合并
        """
        if not BILIBILI_API_AVAILABLE:
            print("错误: bilibili-api-python 未安装，请先运行 pip install bilibili-api-python")
            return False
        
        import subprocess
        from urllib.parse import urlparse
        
        try:
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 1. 获取视频信息和下载链接
            v = video.Video(bvid=bvid)
            if quality:
                download_urls = sync(v.get_download_url(qn=quality))
            else:
                download_urls = sync(v.get_download_url())
            
            # download_urls 结构: (video_url, audio_url, quality_title)
            if not download_urls or len(download_urls) < 2:
                print(f"下载 {bvid} 失败: 获取下载链接失败，可能需要登录")
                return False
            
            video_url = download_urls[0]
            audio_url = download_urls[1]
            quality_name = download_urls[2] if len(download_urls) >= 3 else "unknown"
            
            print(f"  画质: {quality_name}")
            
            # 2. 下载视频
            video_path = os.path.join(output_dir, f"{bvid}_video.m4s")
            print(f"  正在下载视频...")
            resp_video = self.session.get(video_url, stream=True)
            if resp_video.status_code != 200:
                print(f"  视频下载失败: HTTP {resp_video.status_code}")
                return False
            
            with open(video_path, 'wb') as f:
                for chunk in resp_video.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)
            
            # 3. 下载音频
            audio_path = os.path.join(output_dir, f"{bvid}_audio.m4a")
            print(f"  正在下载音频...")
            resp_audio = self.session.get(audio_url, stream=True)
            if resp_audio.status_code != 200:
                print(f"  音频下载失败: HTTP {resp_audio.status_code}")
                return False
            
            with open(audio_path, 'wb') as f:
                for chunk in resp_audio.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)
            
            # 4. 获取视频标题，作为最终文件名
            video_info = sync(v.get_info())
            title = video_info.get("title", bvid)
            # 替换文件名不允许的字符
            safe_title = "".join([c if c not in r'<>:"/\|?*' else '_' for c in title])
            output_path = os.path.join(output_dir, f"{safe_title}.mp4")
            
            # 5. ffmpeg 合并
            print(f"  正在合并视频音频...")
            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-i', audio_path,
                '-c', 'copy',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"  ffmpeg合并失败: {result.stderr[:100]}...")
                return False
            
            # 6. 删除临时文件
            try:
                os.remove(video_path)
                os.remove(audio_path)
            except:
                pass
            
            print(f"  ✓ 完成: {output_path}")
            return True
            
        except Exception as e:
            print(f"下载 {bvid} 失败: {str(e)}")
            if "403" in str(e) or "Forbidden" in str(e):
                print("  → 原因可能: 需要登录Bilibili才能下载，请确认SESSDATA正确")
            return False
    
    def batch_download(self, videos: List[Dict], output_dir: str = "./download", limit: Optional[int] = None, quality: Optional[int] = None) -> int:
        """批量下载"""
        if limit and limit > 0:
            videos = videos[:limit]
        
        success_count = 0
        for i, v in enumerate(videos):
            print(f"\n正在下载 ({i+1}/{len(videos)}): {v['title']}")
            print(f"链接: {v['video_url']}")
            if self.download_video(v["bvid"], output_dir, quality):
                success_count += 1
        
        return success_count


def main():
    parser = argparse.ArgumentParser(description="Bilibili 视频关键词筛选爬取工具")
    parser.add_argument("-s", "--search", required=True, help="搜索关键词（用于B站初步搜索）")
    parser.add_argument("-t", "--title", nargs="*", help="标题必须包含的关键词，可多个")
    parser.add_argument("-d", "--desc", nargs="*", help="简介必须包含的关键词，可多个")
    parser.add_argument("-p", "--pages", type=int, default=5, help="搜索最大页数，默认5")
    parser.add_argument("-o", "--output", help="输出结果保存到文件，默认输出到控制台")
    parser.add_argument("--download", action="store_true", help="是否下载匹配到的视频")
    parser.add_argument("--download-dir", default="./download", help="下载目录，默认 ./download")
    parser.add_argument("--limit", type=int, help="限制下载数量，不限制则下载全部")
    parser.add_argument("--quality", type=int, help="下载画质 (127=8K, 126=杜比, 125=1080P+, 80=1080P, 64=720P)")
    
    args = parser.parse_args()
    
    spider = BilibiliVideoSpider()
    
    print(f"搜索关键词: {args.search}")
    if args.title:
        print(f"标题筛选: {', '.join(args.title)}")
    if args.desc:
        print(f"简介筛选: {', '.join(args.desc)}")
    
    results = spider.search_and_filter(
        search_keyword=args.search,
        title_keywords=args.title,
        desc_keywords=args.desc,
        max_pages=args.pages
    )
    
    print(f"\n找到 {len(results)} 个匹配视频:\n")
    
    # 输出结果
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"结果已保存到 {args.output}")
    else:
        for i, v in enumerate(results, 1):
            print(f"{i}. {v['title']}")
            print(f"   UP主: {v['author']}   播放: {v['play']}")
            print(f"   链接: {v['video_url']}")
            if v['description']:
                desc_preview = v['description'][:100] + "..." if len(v['description']) > 100 else v['description']
                print(f"   简介: {desc_preview}")
            print()
    
    # 下载
    if args.download and results:
        if not BILIBILI_API_AVAILABLE:
            print("\n警告: bilibili-api-python 未安装，无法下载。请先安装:")
            print("  pip install bilibili-api-python")
        else:
            limit_str = f"最多 {args.limit} 个" if args.limit else "全部"
            print(f"\n开始下载{limit_str}...")
            success = spider.batch_download(
                results,
                output_dir=args.download_dir,
                limit=args.limit,
                quality=args.quality
            )
            print(f"\n下载完成，成功 {success}/{len(results)} 个")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
