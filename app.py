#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bilibili 视频关键词筛选爬取工具 - Web界面版本
Author: OpenClaw
Date: 2026-03-22
"""

from flask import Flask, render_template_string, request, jsonify, send_file
import os
import json
import sys
from datetime import datetime
from typing import List, Dict, Optional
import requests

# 尝试导入 bilibili_api
try:
    from bilibili_api import video, sync, user
    BILIBILI_API_AVAILABLE = True
except ImportError:
    BILIBILI_API_AVAILABLE = False

app = Flask(__name__)

# 默认输出文件夹
DEFAULT_OUTPUT_DIR = "./output"

# 创建输出目录
os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)


class BilibiliVideoSpider:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
    
    def search_videos(self, keyword: str, page: int = 1, page_size: int = 30) -> List[Dict]:
        """搜索视频"""
        SEARCH_API = "https://api.bilibili.com/x/web-interface/search/all"
        params = {
            "keyword": keyword,
            "page": page,
            "page_size": page_size,
            "search_type": "video"
        }
        
        try:
            resp = self.session.get(SEARCH_API, params=params)
            data = resp.json()
            
            if data["code"] != 0:
                return []
            
            result = []
            if "result" in data["data"] and "video" in data["data"]["result"]:
                result = data["data"]["result"]["video"]
            
            return [self.format_result(v) for v in result]
        except Exception as e:
            print(f"搜索异常: {e}")
            return []
    
    def get_user_videos(self, mid: int, max_pages: int = 5) -> List[Dict]:
        """获取UP主所有视频"""
        if not BILIBILI_API_AVAILABLE:
            return []
        
        try:
            u = user.User(uid=mid)
            all_videos = []
            
            for page in range(1, max_pages + 1):
                try:
                    data = sync(u.get_videos(pn=page))
                    # bilibili-api 返回结构: data['list']['vlist'] 正确
                    videos = data.get("list", {}).get("vlist", [])
                    if not videos:
                        break
                    for v in videos:
                        formatted = {
                            "bvid": v.get("bvid"),
                            "aid": v.get("aid"),
                            "title": v.get("title"),
                            "description": v.get("description", ""),
                            "author": v.get("author"),
                            "duration": v.get("duration"),
                            "play": v.get("play"),
                            "video_url": f"https://www.bilibili.com/video/{v.get('bvid')}/",
                            "pic": v.get("pic")
                        }
                        all_videos.append(formatted)
                except Exception as e:
                    print(f"获取UP主视频第{page}页异常: {e}")
                    break
            
            return all_videos
        except Exception as e:
            print(f"获取UP主视频异常: {e}")
            return []
    
    def filter_by_title(self, videos: List[Dict], keywords: List[str]) -> List[Dict]:
        """按标题关键词筛选"""
        if not keywords:
            return videos
        
        filtered = []
        for video in videos:
            title = video.get("title", "").lower()
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
    
    def format_result(self, video: Dict) -> Dict:
        """格式化输出结果"""
        return {
            "bvid": video.get("bvid"),
            "aid": video.get("aid"),
            "title": video.get("title"),
            "description": video.get("description", ""),
            "author": video.get("author"),
            "duration": video.get("duration"),
            "play": video.get("play"),
            "video_url": self.get_video_url(video.get("bvid")),
            "pic": video.get("pic")
        }
    
    def get_video_url(self, bvid: str) -> str:
        return f"https://www.bilibili.com/video/{bvid}/"
    
    def search_and_filter(
        self,
        search_keyword: str,
        title_keywords: List[str],
        desc_keywords: List[str],
        max_pages: int = 5
    ) -> List[Dict]:
        """完整搜索筛选流程"""
        all_results = []
        
        for page in range(1, max_pages + 1):
            videos = self.search_videos(search_keyword, page, 30)
            if not videos:
                break
            
            if title_keywords:
                videos = self.filter_by_title(videos, title_keywords)
            if desc_keywords:
                videos = self.filter_by_description(videos, desc_keywords)
            
            all_results.extend(videos)
        
        return all_results
    
    def download_video(self, bvid: str, output_dir: str = "./download", quality: Optional[int] = None) -> bool:
        """下载单个视频"""
        if not BILIBILI_API_AVAILABLE:
            return False
        
        try:
            v = video.Video(bvid=bvid)
            if quality:
                sync(v.download(output=output_dir, qn=quality))
            else:
                sync(v.download(output=output_dir))
            return True
        except Exception as e:
            print(f"下载 {bvid} 失败: {e}")
            return False
    
    def batch_download(self, videos: List[Dict], output_dir: str = "./download", limit: Optional[int] = None, quality: Optional[int] = None) -> int:
        """批量下载"""
        if limit and limit > 0:
            videos = videos[:limit]
        
        success_count = 0
        for v in videos:
            print(f"正在下载: {v['title']}")
            if self.download_video(v["bvid"], output_dir, quality):
                success_count += 1
        
        return success_count


spider = BilibiliVideoSpider()

# HTML模板
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bilibili 视频关键词筛选爬取工具</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: #f5f5f5;
            line-height: 1.6;
        }
        .container {
            max-width: 1200px;
            margin: 20px auto;
            padding: 20px;
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 30px;
        }
        .tabs {
            display: flex;
            margin-bottom: 20px;
            border-bottom: 2px solid #ddd;
        }
        .tab {
            padding: 10px 20px;
            cursor: pointer;
            border: 1px solid #ddd;
            border-bottom: 2px solid #ddd;
            margin-bottom: -2px;
            background-color: #eee;
            border-radius: 8px 8px 0 0;
            margin-right: 5px;
        }
        .tab.active {
            background-color: #fff;
            border-bottom: 2px solid #fff;
            color: #00a1d6;
            font-weight: bold;
        }
        .tab-content {
            display: none;
            background-color: #fff;
            padding: 20px;
            border-radius: 0 0 8px 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .tab-content.active {
            display: block;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #555;
        }
        input, select, textarea {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        button {
            background-color: #00a1d6;
            color: #fff;
            border: none;
            padding: 12px 30px;
            border-radius: 4px;
            font-size: 16px;
            cursor: pointer;
        }
        button:hover {
            background-color: #008cc4;
        }
        button:disabled {
            background-color: #ccc;
            cursor: not-allowed;
        }
        .result-count {
            margin: 15px 0;
            font-size: 16px;
            color: #333;
        }
        .video-list {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .video-card {
            border: 1px solid #eee;
            border-radius: 8px;
            overflow: hidden;
            background-color: #fafafa;
            transition: transform 0.2s;
        }
        .video-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        .video-thumbnail {
            width: 100%;
            height: 158px;
            object-fit: cover;
        }
        .video-info {
            padding: 15px;
        }
        .video-title {
            font-weight: bold;
            margin-bottom: 8px;
            color: #333;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }
        .video-author {
            color: #666;
            font-size: 14px;
            margin-bottom: 5px;
        }
        .video-play {
            color: #999;
            font-size: 12px;
        }
        .video-link {
            display: inline-block;
            margin-top: 10px;
            color: #00a1d6;
            text-decoration: none;
            font-size: 14px;
        }
        .video-link:hover {
            text-decoration: underline;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #999;
        }
        .error {
            color: #e74c3c;
            padding: 15px;
            background-color: #fdecea;
            border-radius: 4px;
            margin: 10px 0;
        }
        .success {
            color: #27ae60;
            padding: 15px;
            background-color: #eafaf1;
            border-radius: 4px;
            margin: 10px 0;
        }
        .quality-options {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }
        .quality-option {
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            cursor: pointer;
            text-align: center;
        }
        .quality-option:hover {
            background-color: #f0f0f0;
        }
        .quality-option.selected {
            background-color: #00a1d6;
            color: #fff;
            border-color: #00a1d6;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📺 Bilibili 视频关键词筛选爬取工具</h1>
        
        <div class="tabs">
            <div class="tab active" onclick="switchTab('search')">关键词搜索</div>
            <div class="tab" onclick="switchTab('user')">UP主爬取</div>
            <div class="tab" onclick="switchTab('download')">批量下载</div>
        </div>
        
        <!-- 关键词搜索 -->
        <div id="search" class="tab-content active">
            <form id="searchForm" onsubmit="event.preventDefault(); doSearch();">
                <div class="form-group">
                    <label for="searchKeyword">搜索关键词 (必填)</label>
                    <input type="text" id="searchKeyword" placeholder="例如: Python教程" required>
                </div>
                <div class="form-group">
                    <label for="titleKeywords">标题必须包含的关键词 (空格分隔，可选)</label>
                    <input type="text" id="titleKeywords" placeholder="例如: 零基础 2026">
                </div>
                <div class="form-group">
                    <label for="descKeywords">简介必须包含的关键词 (空格分隔，可选)</label>
                    <input type="text" id="descKeywords" placeholder="例如: 项目实战">
                </div>
                <div class="form-group">
                    <label for="maxPages">最大搜索页数</label>
                    <input type="number" id="maxPages" value="5" min="1" max="20">
                </div>
                <button type="submit">开始搜索</button>
            </form>
            
            <div id="searchResult"></div>
        </div>
        
        <!-- UP主爬取 -->
        <div id="user" class="tab-content">
            <form id="userForm" onsubmit="event.preventDefault(); doUserSearch();">
                <div class="form-group">
                    <label for="mid">UP主 ID / 空间链接</label>
                    <input type="text" id="mid" placeholder="例如: 123456 或者 https://space.bilibili.com/123456" required>
                </div>
                <div class="form-group">
                    <label for="maxPagesUser">最大获取页数 (每页30个视频)</label>
                    <input type="number" id="maxPagesUser" value="5" min="1" max="50">
                </div>
                <div class="form-group">
                    <label for="titleKeywordsUser">标题筛选关键词 (空格分隔，可选)</label>
                    <input type="text" id="titleKeywordsUser" placeholder="留空则不筛选">
                </div>
                <div class="form-group">
                    <label for="descKeywordsUser">简介筛选关键词 (空格分隔，可选)</label>
                    <input type="text" id="descKeywordsUser" placeholder="留空则不筛选">
                </div>
                <button type="submit">获取UP主视频</button>
            </form>
            
            <div id="userResult"></div>
        </div>
        
        <!-- 批量下载 -->
        <div id="download" class="tab-content">
            <form id="downloadForm" onsubmit="event.preventDefault(); doDownload();">
                <div class="form-group">
                    <label>选择下载画质</label>
                    <div class="quality-options">
                        <div class="quality-option selected" onclick="selectQuality(0, '自动最高')">自动最高</div>
                        <div class="quality-option" onclick="selectQuality(127, '8K')">8K</div>
                        <div class="quality-option" onclick="selectQuality(126, '杜比')">杜比</div>
                        <div class="quality-option" onclick="selectQuality(125, '1080P+')">1080P+</div>
                        <div class="quality-option" onclick="selectQuality(80, '1080P')">1080P</div>
                        <div class="quality-option" onclick="selectQuality(64, '720P')">720P</div>
                        <div class="quality-option" onclick="selectQuality(32, '480P')">480P</div>
                        <div class="quality-option" onclick="selectQuality(16, '360P')">360P</div>
                    </div>
                    <input type="hidden" id="quality" value="0">
                </div>
                <div class="form-group">
                    <label for="downloadLimit">限制下载数量 (0=不限制)</label>
                    <input type="number" id="downloadLimit" value="0" min="0" max="100">
                </div>
                <div class="form-group">
                    <label for="outputDir">输出文件夹</label>
                    <input type="text" id="outputDir" value="./download" placeholder="下载保存目录">
                </div>
                <p><strong>注意:</strong> 需要先在搜索页面或UP主页面得到筛选结果才能下载</p>
                <button type="submit">开始批量下载</button>
            </form>
            
            <div id="downloadResult"></div>
        </div>
    </div>

<script>
let currentResults = [];

function switchTab(tabName) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.querySelector(`.tab[onclick="switchTab('${tabName}')"]`).classList.add('active');
    document.getElementById(tabName).classList.add('active');
}

function selectQuality(qn, text) {
    document.querySelectorAll('.quality-option').forEach(o => o.classList.remove('selected'));
    event.target.classList.add('selected');
    document.getElementById('quality').value = qn;
}

function parseKeywords(str) {
    if (!str.trim()) return [];
    return str.trim().split(/\s+/);
}

function renderResults(results) {
    if (results.length === 0) {
        return `<div class="error">没有找到匹配的视频</div>`;
    }
    
    let html = `<div class="result-count">找到 ${results.length} 个匹配视频:</div>`;
    html += `<div class="video-list">`;
    
    results.forEach(v => {
        html += `
        <div class="video-card">
            <img class="video-thumbnail" src="${v.pic}" alt="${v.title}" loading="lazy">
            <div class="video-info">
                <div class="video-title">${v.title}</div>
                <div class="video-author">UP主: ${v.author}</div>
                <div class="video-play">播放: ${v.play}</div>
                <a href="${v.video_url}" target="_blank" class="video-link">👉 打开视频</a>
            </div>
        </div>`;
    });
    
    html += `</div>`;
    
    // 保存结果供下载使用
    currentResults = results;
    
    // 保存到文件
    saveResultsToFile(results);
    
    return html;
}

function saveResultsToFile(results) {
    fetch('/api/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(results)
    }).then(resp => resp.json()).then(data => {
        console.log('结果已保存到', data.path);
    });
}

async function doSearch() {
    const keyword = document.getElementById('searchKeyword').value;
    const titleKeywords = parseKeywords(document.getElementById('titleKeywords').value);
    const descKeywords = parseKeywords(document.getElementById('descKeywords').value);
    const maxPages = parseInt(document.getElementById('maxPages').value);
    
    const resultDiv = document.getElementById('searchResult');
    resultDiv.innerHTML = `<div class="loading">正在搜索，请稍候...</div>`;
    
    try {
        const resp = await fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                keyword: keyword,
                title_keywords: titleKeywords,
                desc_keywords: descKeywords,
                max_pages: maxPages
            })
        });
        
        const data = await resp.json();
        
        if (data.error) {
            resultDiv.innerHTML = `<div class="error">${data.error}</div>`;
            return;
        }
        
        resultDiv.innerHTML = renderResults(data.results);
    } catch (e) {
        resultDiv.innerHTML = `<div class="error">请求出错: ${e.message}</div>`;
    }
}

async function doUserSearch() {
    let midStr = document.getElementById('mid').value.trim();
    // 从URL提取mid
    const midMatch = midStr.match(/space\.bilibili\.com\/(\d+)/);
    if (midMatch) {
        midStr = midMatch[1];
    }
    const mid = parseInt(midStr);
    
    if (isNaN(mid)) {
        document.getElementById('userResult').innerHTML = `<div class="error">UP主ID格式不正确，请输入数字ID或空间链接</div>`;
        return;
    }
    
    const maxPages = parseInt(document.getElementById('maxPagesUser').value);
    const titleKeywords = parseKeywords(document.getElementById('titleKeywordsUser').value);
    const descKeywords = parseKeywords(document.getElementById('descKeywordsUser').value);
    
    const resultDiv = document.getElementById('userResult');
    resultDiv.innerHTML = `<div class="loading">正在获取UP主视频，请稍候...</div>`;
    
    try {
        const resp = await fetch('/api/user', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                mid: mid,
                title_keywords: titleKeywords,
                desc_keywords: descKeywords,
                max_pages: maxPages
            })
        });
        
        const data = await resp.json();
        
        if (data.error) {
            resultDiv.innerHTML = `<div class="error">${data.error}</div>`;
            return;
        }
        
        resultDiv.innerHTML = renderResults(data.results);
    } catch (e) {
        resultDiv.innerHTML = `<div class="error">请求出错: ${e.message}</div>`;
    }
}

async function doDownload() {
    if (currentResults.length === 0) {
        document.getElementById('downloadResult').innerHTML = `<div class="error">请先在搜索或UP主页面获取筛选结果再下载</div>`;
        return;
    }
    
    let quality = parseInt(document.getElementById('quality').value);
    const limit = parseInt(document.getElementById('downloadLimit').value);
    const outputDir = document.getElementById('outputDir').value || './download';
    
    if (quality === 0) {
        quality = null;
    }
    
    const resultDiv = document.getElementById('downloadResult');
    resultDiv.innerHTML = `<div class="loading">开始下载，请稍候... (这可能需要很长时间，取决于视频数量和大小)</div>`;
    
    try {
        const resp = await fetch('/api/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                quality: quality,
                limit: limit > 0 ? limit : null,
                output_dir: outputDir
            })
        });
        
        const data = await resp.json();
        
        if (data.error) {
            resultDiv.innerHTML = `<div class="error">${data.error}</div>`;
            return;
        }
        
        resultDiv.innerHTML = `<div class="success">下载完成！成功 ${data.success}/${data.total} 个，保存到 ${data.output_dir}</div>`;
    } catch (e) {
        resultDiv.innerHTML = `<div class="error">下载出错: ${e.message}</div>`;
    }
}
</script>
</body>
</html>
'''


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/search', methods=['POST'])
def api_search():
    data = request.get_json()
    keyword = data.get('keyword', '')
    title_keywords = data.get('title_keywords', [])
    desc_keywords = data.get('desc_keywords', [])
    max_pages = data.get('max_pages', 5)
    
    if not keyword:
        return jsonify({"error": "搜索关键词不能为空"})
    
    results = spider.search_and_filter(keyword, title_keywords, desc_keywords, max_pages)
    return jsonify({"results": results})


@app.route('/api/user', methods=['POST'])
def api_user():
    data = request.get_json()
    mid = data.get('mid', 0)
    title_keywords = data.get('title_keywords', [])
    desc_keywords = data.get('desc_keywords', [])
    max_pages = data.get('max_pages', 5)
    
    if not BILIBILI_API_AVAILABLE:
        return jsonify({"error": "bilibili-api-python 未安装，请运行 pip install bilibili-api-python"})
    
    if mid <= 0:
        return jsonify({"error": "UP主ID不正确"})
    
    videos = spider.get_user_videos(mid, max_pages)
    
    if title_keywords:
        videos = spider.filter_by_title(videos, title_keywords)
    if desc_keywords:
        videos = spider.filter_by_description(videos, desc_keywords)
    
    return jsonify({"results": videos})


@app.route('/api/save', methods=['POST'])
def api_save():
    results = request.get_json()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"bili_results_{timestamp}.json"
    filepath = os.path.join(DEFAULT_OUTPUT_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    txt_filepath = os.path.join(DEFAULT_OUTPUT_DIR, f"bili_results_{timestamp}.txt")
    with open(txt_filepath, 'w', encoding='utf-8') as f:
        for i, v in enumerate(results, 1):
            f.write(f"{i}. {v['title']}\n")
            f.write(f"   UP主: {v['author']}\n")
            f.write(f"   链接: {v['video_url']}\n")
            if v['description']:
                f.write(f"   简介: {v['description'][:100]}\n")
            f.write("\n")
    
    return jsonify({
        "success": True,
        "json_path": filepath,
        "txt_path": txt_filepath
    })


@app.route('/api/download', methods=['POST'])
def api_download():
    global currentResults
    
    data = request.get_json()
    quality = data.get('quality')
    limit = data.get('limit')
    output_dir = data.get('output_dir', './download')
    
    if not BILIBILI_API_AVAILABLE:
        return jsonify({"error": "bilibili-api-python 未安装，请运行 pip install bilibili-api-python 后才能下载"})
    
    if not currentResults:
        return jsonify({"error": "没有筛选结果，请先搜索"})
    
    os.makedirs(output_dir, exist_ok=True)
    success_count = spider.batch_download(currentResults, output_dir, limit, quality)
    
    return jsonify({
        "success": success_count,
        "total": len(currentResults) if limit is None else min(limit, len(currentResults)),
        "output_dir": output_dir
    })


if __name__ == '__main__':
    print("🚀 Bilibili 视频关键词筛选爬取工具 Web 启动")
    print("📝 访问: http://127.0.0.1:5000")
    print("💾 结果默认保存到: ./output/")
    print("💾 视频默认保存到: ./download/")
    app.run(host='0.0.0.0', port=5000, debug=False)
