# Bilibili 视频关键词筛选爬取工具

功能：
- ✅ B站关键词搜索视频
- ✅ 标题关键词精准筛选（支持多个关键词，必须全部匹配）
- ✅ 简介关键词精准筛选（支持多个关键词，必须全部匹配）
- ✅ 输出匹配视频链接
- ✅ 批量自动下载视频（支持限制下载数量、选择画质）

## 安装依赖

```bash
pip install requests
# 如果需要下载功能，还需要安装：
pip install bilibili-api-python
```

系统需要安装 ffmpeg 用于视频合并：
```bash
# Ubuntu/Debian
apt install ffmpeg

# CentOS/RHEL
yum install ffmpeg
```

## 使用方法

### 仅搜索筛选（不下载）

```bash
# 基本搜索
python bili_spider.py -s "python教程"

# 标题必须同时包含 "基础" 和 "2024"
python bili_spider.py -s "python教程" -t 基础 2024

# 标题+简介双重筛选
python bili_spider.py -s "python教程" -t 基础 -d 项目实战

# 保存结果到JSON文件
python bili_spider.py -s "python教程" -t 基础 -o results.json
```

### 搜索+自动下载

```bash
# 搜索筛选后下载全部匹配视频
python bili_spider.py -s "python教程" -t 基础 --download

# 限制最多下载 5 个，画质选择 1080P
python bili_spider.py -s "python教程" -t 基础 --download --limit 5 --quality 80

# 指定下载目录
python bili_spider.py -s "python教程" --download --download-dir ~/Videos/bilibili
```

### 参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `-s`, `--search` | 搜索关键词（必填） | `-s "Python教程"` |
| `-t`, `--title` | 标题必须包含的关键词，可多个 | `-t 基础 2024` |
| `-d`, `--desc` | 简介必须包含的关键词，可多个 | `-d 项目实战` |
| `-p`, `--pages` | 搜索最大页数，默认5 | `-p 10` |
| `-o`, `--output` | 结果保存到JSON文件 | `-o out.json` |
| `--download` | 是否下载视频 | `--download` |
| `--download-dir` | 下载目录，默认 `./download` | `--download-dir ~/Downloads` |
| `--limit` | 限制下载数量 | `--limit 10` |
| `--quality` | 下载画质 | `127=8K, 126=杜比, 125=1080P+, 80=1080P, 64=720P` |

## 关于 Chrome 下载插件配合

如果你已经有 Chrome 浏览器的 Bilibili 下载插件，可以：
1. 先运行筛选：`python bili_spider.py -s "关键词" -t "标题关键词" -o results.json`
2. 在得到的结果中复制视频链接
3. 在 Chrome 中使用插件下载

本工具也内置了直接下载功能，不需要插件即可完成爬取+下载全流程。

## 画质参数对照表

| qn 值 | 画质 |
|-------|------|
| 127 | 8K |
| 126 | 杜比视界 |
| 125 | 1080P+ |
| 80 | 1080P |
| 64 | 720P |
| 32 | 480P |
| 16 | 360P |

不指定 `--quality` 时，自动选择最高可用画质。
