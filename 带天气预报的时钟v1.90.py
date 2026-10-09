import os
# 清除代理环境变量，避免SSL代理错误
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(proxy_var, None)
import sys  # 虽然本版本不再使用重启
import tkinter as tk
import tkinter.font as tkFont   # ← 新增这一行
from tkinter import messagebox
import math
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import threading
import configparser
import pyttsx3
import queue  # 用于顺序播报队列
import pygame  # 用于播放 mp3
import time    # 用于后台线程中阻塞播放
import logging
import re
import pymysql  # 新增：用于连接 MySQL 数据库
import json
import subprocess  # 用于PowerShell TTS调用
import webbrowser  # 用于打开网页
try:
    import markdown
    import html2text
    MARKDOWN_AVAILABLE = True
except ImportError:
    print("Warning: markdown and html2text not available. News will display as plain text.")
    MARKDOWN_AVAILABLE = False


def render_markdown_to_text(text_widget, markdown_content):
    """将Markdown内容渲染到Text控件中，支持丰富格式"""
    text_widget.config(state=tk.NORMAL)
    text_widget.delete(1.0, tk.END)

    try:
        # 配置文本标签样式
        text_widget.tag_configure("h1", font=("Microsoft YaHei", 16, "bold"), foreground="#2E86AB", spacing1=10, spacing3=5)
        text_widget.tag_configure("h2", font=("Microsoft YaHei", 14, "bold"), foreground="#A23B72", spacing1=8, spacing3=4)
        text_widget.tag_configure("h3", font=("Microsoft YaHei", 12, "bold"), foreground="#F18F01", spacing1=6, spacing3=3)
        text_widget.tag_configure("bold", font=("Microsoft YaHei", 11, "bold"))
        text_widget.tag_configure("italic", font=("Microsoft YaHei", 11, "italic"))
        text_widget.tag_configure("code", font=("Consolas", 10), background="#f0f0f0", relief="solid", borderwidth=1)
        text_widget.tag_configure("quote", font=("Microsoft YaHei", 11), foreground="#666666", lmargin1=20, lmargin2=20, background="#f9f9f9")
        text_widget.tag_configure("link", font=("Microsoft YaHei", 11), foreground="blue", underline=True)
        text_widget.tag_configure("hr", font=("Microsoft YaHei", 11), foreground="#cccccc")
        text_widget.tag_configure("list", font=("Microsoft YaHei", 11), lmargin1=20, lmargin2=30)
        text_widget.tag_configure("list_item", font=("Microsoft YaHei", 11), lmargin1=30, lmargin2=40)

        # 处理Markdown内容
        lines = markdown_content.split('\n')
        in_code_block = False
        code_block_content = []

        for line in lines:
            original_line = line
            line = line.rstrip()

            # 处理代码块
            if line.startswith('```'):
                if in_code_block:
                    # 结束代码块
                    code_text = '\n'.join(code_block_content)
                    text_widget.insert(tk.END, code_text + '\n', "code")
                    code_block_content = []
                    in_code_block = False
                else:
                    # 开始代码块
                    in_code_block = True
                continue

            if in_code_block:
                code_block_content.append(line)
                continue

            if not line:
                # 空行
                text_widget.insert(tk.END, '\n')
                continue

            # 处理水平线
            if line.strip() in ['---', '***', '___']:
                text_widget.insert(tk.END, '─' * 50 + '\n', "hr")
                continue

            # 处理标题
            if line.startswith('### '):
                text_widget.insert(tk.END, line[4:] + '\n', "h3")
            elif line.startswith('## '):
                text_widget.insert(tk.END, line[3:] + '\n', "h2")
            elif line.startswith('# '):
                text_widget.insert(tk.END, line[2:] + '\n', "h1")
            # 处理引用
            elif line.startswith('> '):
                text_widget.insert(tk.END, line[2:] + '\n', "quote")
            # 处理有序列表
            elif re.match(r'^\d+\.\s+', line):
                list_text = re.sub(r'^\d+\.\s+', '• ', line)
                process_inline_markdown_line(text_widget, list_text, "list_item")
                text_widget.insert(tk.END, '\n')
            # 处理无序列表
            elif line.strip().startswith(('* ', '- ', '+ ')):
                list_text = line.strip()[2:]  # 移除列表标记
                text_widget.insert(tk.END, '• ', "list_item")
                process_inline_markdown_line(text_widget, list_text, "list_item")
                text_widget.insert(tk.END, '\n')
            # 处理行内代码行
            elif line.strip().startswith('`') and line.strip().endswith('`') and line.count('`') == 2:
                text_widget.insert(tk.END, line.strip()[1:-1] + '\n', "code")
            else:
                # 处理普通段落的行内格式
                process_inline_markdown_line(text_widget, line, "normal")
                text_widget.insert(tk.END, '\n')

    except Exception as e:
        print(f"Markdown渲染失败: {e}")
        # 发生错误时，显示原始内容
        text_widget.delete(1.0, tk.END)
        text_widget.insert(1.0, markdown_content)

    text_widget.config(state=tk.DISABLED)


def process_inline_markdown_line(text_widget, line, base_tag="normal"):
    """处理单行内的Markdown格式"""
    import re

    # 处理粗体 **text**
    bold_pattern = r'\*\*(.*?)\*\*'
    # 处理斜体 *text* (避免与粗体冲突)
    italic_pattern = r'(?<!\*)\*([^*\n]+?)\*(?!\*)'
    # 处理行内代码 `code`
    code_pattern = r'`([^`\n]+?)`'
    # 处理链接 [text](url)
    link_pattern = r'\[([^\]]+)\]\([^\)]+\)'

    pos = 0

    while pos < len(line):
        # 查找所有格式标记
        matches = []

        # 查找粗体
        for match in re.finditer(bold_pattern, line[pos:]):
            matches.append(('bold', match.start() + pos, match.end() + pos, match.group(1)))

        # 查找斜体
        for match in re.finditer(italic_pattern, line[pos:]):
            matches.append(('italic', match.start() + pos, match.end() + pos, match.group(1)))

        # 查找行内代码
        for match in re.finditer(code_pattern, line[pos:]):
            matches.append(('code', match.start() + pos, match.end() + pos, match.group(1)))

        # 查找链接
        for match in re.finditer(link_pattern, line[pos:]):
            matches.append(('link', match.start() + pos, match.end() + pos, match.group(1)))

        if not matches:
            # 没有更多格式，插入剩余文本
            text_widget.insert(tk.END, line[pos:], base_tag)
            break

        # 按位置排序，处理最早的匹配
        matches.sort(key=lambda x: x[1])
        format_type, start, end, content = matches[0]

        # 插入格式前的普通文本
        if start > pos:
            text_widget.insert(tk.END, line[pos:start], base_tag)

        # 插入格式化文本
        if base_tag == "list_item":
            # 列表项中的格式化文本也要保持列表缩进
            combined_tags = (base_tag, format_type)
            text_widget.insert(tk.END, content, combined_tags)
        else:
            text_widget.insert(tk.END, content, format_type)

        pos = end


def process_inline_markdown(text_widget, line):
    """处理行内Markdown格式（保留用于兼容性）"""
    process_inline_markdown_line(text_widget, line, "normal")
    return True


# MySQL 数据库连接函数，增加了超时参数
def get_db_connection():
    """Connect to an optional user-configured MySQL news database.

    Credentials come from environment variables first, then config.ini. No
    database endpoint or credential is bundled in the public source.
    """
    env_names = {
        "host": "SOFIA_NEWS_DB_HOST",
        "user": "SOFIA_NEWS_DB_USER",
        "password": "SOFIA_NEWS_DB_PASSWORD",
        "database": "SOFIA_NEWS_DB_NAME",
        "port": "SOFIA_NEWS_DB_PORT",
    }
    values = {}
    for key, env_name in env_names.items():
        env_value = os.environ.get(env_name, "").strip()
        try:
            config_value = config.get("news_database", key, fallback="").strip()
        except NameError:
            config_value = ""
        values[key] = env_value or config_value

    required = ("host", "user", "password", "database")
    missing = [key for key in required if not values[key]]
    if missing:
        raise RuntimeError(
            "新闻数据库尚未配置。请在 config.ini 的 [news_database] 中填写连接信息，"
            "或设置 SOFIA_NEWS_DB_* 环境变量。"
        )

    return pymysql.connect(
        host=values["host"],
        user=values["user"],
        password=values["password"],
        database=values["database"],
        port=int(values["port"] or "3306"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
        read_timeout=30,
        autocommit=True,
    )

def news_db_is_configured():
    """Return whether all required optional news-database settings exist."""
    env_names = {
        "host": "SOFIA_NEWS_DB_HOST",
        "user": "SOFIA_NEWS_DB_USER",
        "password": "SOFIA_NEWS_DB_PASSWORD",
        "database": "SOFIA_NEWS_DB_NAME",
    }
    for key, env_name in env_names.items():
        value = os.environ.get(env_name, "").strip()
        try:
            value = value or config.get("news_database", key, fallback="").strip()
        except NameError:
            value = value or ""
        if not value:
            return False
    return True

# 导入 watchdog 模块
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# 配置日志记录
logging.basicConfig(filename="clock.log", level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

# 默认 config.ini 内容
DEFAULT_CONFIG = """
[api]
openweathermap_key = YOUR_API_KEY

[city_mapping]
北京 = 101010200
上海 = 101020100
杭州 = 101210101
禹州 = 101180405
济宁 = 101120701
广州 = 101280101
深圳 = 101280601
成都 = 101270101
重庆 = 101040100
武汉 = 101200101
南京 = 101190101
西安 = 101110101
天津 = 101030100
苏州 = 101190401
郑州 = 101180101
长沙 = 101250101
青岛 = 101120201
沈阳 = 101070101
哈尔滨 = 101050101
大连 = 101070201
厦门 = 101230201
昆明 = 101290101
合肥 = 101220101
宁波 = 101210401
福州 = 101230101
济南 = 101120101
南昌 = 101240101
长春 = 101060101
石家庄 = 101090101
太原 = 101100101
贵阳 = 101260101
兰州 = 101160101
南宁 = 101300101
海口 = 101310101
银川 = 101170101
西宁 = 101150101
乌鲁木齐 = 101130101
呼和浩特 = 101080101
拉萨 = 101140101
香港 = 101320101
澳门 = 101330101
"""

if not os.path.exists("config.ini"):
    with open("config.ini", "w", encoding="utf-8") as f:
        f.write(DEFAULT_CONFIG.strip())

config = configparser.ConfigParser()
config.read("config.ini", encoding="utf-8")
city_mapping = dict(config.items("city_mapping"))

DEFAULT_REMINDERS = """08:00
开始一天
dingdong.mp3
12:00
午间休息
dingdong.mp3
18:00
结束今天的安排
dingdong.mp3
"""

# 夏令时使用同一份通用示例，用户可在提醒编辑器中自行修改。
SUMMER_REMINDERS = """08:00
开始一天
dingdong.mp3
12:00
午间休息
dingdong.mp3
18:00
结束今天的安排
dingdong.mp3
"""

def choose_reminder_config():
    choice = None
    def set_choice(val):
        nonlocal choice
        choice = val
        dialog.destroy()
    def auto_select():
        nonlocal choice
        if choice is None:
            current_month = datetime.now().month
            if 5 <= current_month <= 10:
                choice = "夏令时"
            else:
                choice = "冬令时"
            dialog.destroy()
    dialog = tk.Toplevel()
    dialog.title("提醒配置选项")
    dialog.resizable(False, False)
    label = tk.Label(dialog, text="请选择提醒配置：\n【冬令时】、【夏令时】、【其他】", font=("Arial", 12))
    label.pack(padx=20, pady=20)
    button_frame = tk.Frame(dialog)
    button_frame.pack(padx=20, pady=10)
    winter_btn = tk.Button(button_frame, text="冬令时", width=10, command=lambda: set_choice("冬令时"))
    winter_btn.grid(row=0, column=0, padx=5)
    summer_btn = tk.Button(button_frame, text="夏令时", width=10, command=lambda: set_choice("夏令时"))
    summer_btn.grid(row=0, column=1, padx=5)
    other_btn = tk.Button(button_frame, text="其他", width=10, command=lambda: set_choice("其他"))
    other_btn.grid(row=0, column=2, padx=5)
    dialog.update_idletasks()
    w = dialog.winfo_width()
    h = dialog.winfo_height()
    sw = dialog.winfo_screenwidth()
    sh = dialog.winfo_screenheight()
    x = (sw - w) // 2
    y = (sh - h) // 2
    dialog.geometry(f"+{x}+{y}")
    dialog.after(8000, auto_select)
    dialog.transient(tk._default_root)
    dialog.grab_set()
    dialog.wait_window()
    return choice

def normalize_time(t):
    t = t.strip().replace(" ", "").replace("时", ":").replace("分", "").replace("点", ":")
    if "半" in t:
        t = re.sub(r"(\d+)(半)", r"\1:30", t)
    if re.match(r"^\d{3,4}$", t):
        if len(t) == 3:
            t = f"0{t[0]}:{t[1:]}"
        if len(t) == 4:
            t = f"{t[:2]}:{t[2:]}"
    elif re.match(r"^\d+[:：]\d+$", t):
        t = t.replace("：", ":")
    t = re.sub(r"(\d+)[-](\d+)", r"\1:\2", t)
    try:
        datetime.strptime(t, "%H:%M")
    except ValueError:
        return None
    return t

def load_reminders():
    reminders = []
    if os.path.exists("reminders.ini"):
        if os.path.getsize("reminders.ini") == 0:
            logging.info("reminders.ini 文件存在但为空，不加载任何提醒事项。")
        else:
            try:
                with open("reminders.ini", "r", encoding="utf-8-sig") as f:
                    lines = f.read().splitlines()
                lines = [line.strip() for line in lines if line.strip()]
                for i in range(0, len(lines), 3):
                    if i + 2 < len(lines):
                        t = normalize_time(lines[i])
                        content = lines[i+1]
                        mp3_file = lines[i+2] if lines[i+2] else "dingdong.mp3"
                        if not t or not content:
                            continue
                        reminders.append((t, content, mp3_file))
                reminders.sort(key=lambda x: (int(x[0].split(":")[0]), int(x[0].split(":")[1])))
            except (IOError, ValueError) as e:
                logging.error(f"读取 reminders.ini 文件出错，使用默认提醒配置: {e}")
                reminders = []
    else:
        config_choice = choose_reminder_config()
        if config_choice is None:
            current_month = datetime.now().month
            if 5 <= current_month <= 10:
                config_choice = "夏令时"
            else:
                config_choice = "冬令时"
        if config_choice == "冬令时":
            with open("reminders.ini", "w", encoding="utf-8") as f:
                f.write(DEFAULT_REMINDERS.strip())
            logging.info("reminders.ini 文件不存在，选择【冬令时】，使用默认提醒配置重新创建。")
        elif config_choice == "夏令时":
            with open("reminders.ini", "w", encoding="utf-8") as f:
                f.write(SUMMER_REMINDERS.strip())
            logging.info("reminders.ini 文件不存在，选择【夏令时】，使用夏令时提醒配置重新创建。")
        elif config_choice == "其他":
            with open("reminders.ini", "w", encoding="utf-8") as f:
                f.write("")
            logging.info("reminders.ini 文件不存在，选择【其他】，生成空白的 reminders.ini。")
        if os.path.getsize("reminders.ini") == 0:
            logging.info("reminders.ini 文件为空，不加载任何提醒事项。")
        else:
            try:
                with open("reminders.ini", "r", encoding="utf-8-sig") as f:
                    lines = f.read().splitlines()
                lines = [line.strip() for line in lines if line.strip()]
                for i in range(0, len(lines), 3):
                    if i + 2 < len(lines):
                        t = normalize_time(lines[i])
                        content = lines[i+1]
                        mp3_file = lines[i+2] if lines[i+2] else "dingdong.mp3"
                        if not t or not content:
                            continue
                        reminders.append((t, content, mp3_file))
                reminders.sort(key=lambda x: (int(x[0].split(":")[0]), int(x[0].split(":")[1])))
            except (IOError, ValueError) as e:
                logging.error(f"读取 reminders.ini 文件出错: {e}")
                reminders = []
    return reminders

# ==================== 天气数据源管理类 v1.90 ====================
class WeatherDataManager:
    """
    天气数据管理器 - 支持多数据源、自动容错、智能缓存
    数据源优先级：中国天气网 > 中国天气网API > wttr.in > sojson备用源
    """

    def __init__(self):
        self.cache = {}  # 天气缓存 {city_code: {"data": ..., "time": ..., "source": ...}}
        self.cache_ttl = 600  # 缓存有效期10分钟
        self.last_successful_source = None  # 上次成功的数据源
        self.source_failure_count = {}  # 数据源失败计数
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
        # 创建不使用系统代理的session (trust_env=False 彻底禁用系统代理)
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.verify = False

    def get_random_ua(self):
        """获取随机User-Agent"""
        import random
        return random.choice(self.user_agents)

    def is_cache_valid(self, city_code):
        """检查缓存是否有效"""
        if city_code not in self.cache:
            return False
        cache_time = self.cache[city_code].get("time", 0)
        return (time.time() - cache_time) < self.cache_ttl

    def get_cached_weather(self, city_code):
        """获取缓存的天气数据"""
        if self.is_cache_valid(city_code):
            return self.cache[city_code].get("data")
        return None

    def set_cache(self, city_code, data, source):
        """设置天气缓存"""
        self.cache[city_code] = {
            "data": data,
            "time": time.time(),
            "source": source
        }

    def get_weather(self, city_code, city_name=""):
        """
        获取天气信息 - 多数据源自动切换
        返回格式: "天气描述 温度°C" 或 "好心情"
        """
        # 1. 先检查缓存
        cached = self.get_cached_weather(city_code)
        if cached:
            logging.info(f"使用缓存的天气数据: {city_name}")
            return cached

        # 2. 按优先级尝试各数据源
        sources = [
            ("weather.com.cn", self._fetch_from_weather_com_cn),
            ("weather.com.cn_api", self._fetch_from_weather_api),
            ("wttr.in", self._fetch_from_wttr),
            ("sojson", self._fetch_from_sojson),
        ]

        # 如果上次有成功的数据源，优先使用
        if self.last_successful_source:
            sources.sort(key=lambda x: 0 if x[0] == self.last_successful_source else 1)

        for source_name, fetch_func in sources:
            # 跳过连续失败超过3次的数据源（5分钟后重试）
            fail_info = self.source_failure_count.get(source_name, {"count": 0, "time": 0})
            if fail_info["count"] >= 3 and (time.time() - fail_info["time"]) < 300:
                continue

            try:
                result = fetch_func(city_code, city_name)
                if result and result != "好心情":
                    self.set_cache(city_code, result, source_name)
                    self.last_successful_source = source_name
                    self.source_failure_count[source_name] = {"count": 0, "time": 0}
                    logging.info(f"天气数据获取成功 [{source_name}]: {city_name} - {result}")
                    return result
            except Exception as e:
                logging.warning(f"数据源 [{source_name}] 获取失败: {e}")
                fail_info = self.source_failure_count.get(source_name, {"count": 0, "time": 0})
                self.source_failure_count[source_name] = {
                    "count": fail_info["count"] + 1,
                    "time": time.time()
                }

        logging.error(f"所有天气数据源均失败: {city_name} (如开启VPN，请尝试关闭或设置分流)")
        return "好心情"

    def _fetch_from_weather_com_cn(self, city_code, city_name=""):
        """数据源1: 中国天气网网页爬取"""
        url = f"http://www.weather.com.cn/weather1d/{city_code}.shtml"
        headers = {"User-Agent": self.get_random_ua()}
        response = self.session.get(url, headers=headers, timeout=8)
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.text, 'html.parser')

        tem_tag = soup.find('p', class_='tem')
        wea_tag = soup.find('p', class_='wea')

        if tem_tag and wea_tag:
            temperature = tem_tag.find('span')
            temperature = temperature.text.strip() if temperature else ""
            weather = wea_tag.text.strip()
            if temperature and weather:
                return f"{weather} {temperature}°C"

        # 尝试备用选择器
        today_weather = soup.select_one('.today .wea')
        today_tem = soup.select_one('.today .tem span')
        if today_weather and today_tem:
            return f"{today_weather.text.strip()} {today_tem.text.strip()}°C"

        return None

    def _fetch_from_weather_api(self, city_code, city_name=""):
        """数据源2: 中国天气网API接口"""
        url = f"http://d1.weather.com.cn/sk_2d/{city_code}.html"
        headers = {
            "User-Agent": self.get_random_ua(),
            "Referer": "http://www.weather.com.cn/"
        }
        response = self.session.get(url, headers=headers, timeout=8)
        response.encoding = "utf-8"

        # 解析JSONP格式响应
        text = response.text
        if text.startswith("var dataSK="):
            json_str = text.replace("var dataSK=", "").strip()
            if json_str.endswith(";"):
                json_str = json_str[:-1]
            data = json.loads(json_str)
            temp = data.get("temp", "")
            weather = data.get("weather", "")
            if temp and weather:
                return f"{weather} {temp}°C"

        return None

    def _fetch_from_wttr(self, city_code, city_name=""):
        """数据源3: wttr.in国际天气服务"""
        if not city_name:
            return None

        # wttr.in支持中文城市名
        url = f"https://wttr.in/{city_name}?format=%C+%t&lang=zh"
        headers = {"User-Agent": self.get_random_ua()}
        response = self.session.get(url, headers=headers, timeout=10)
        response.encoding = "utf-8"

        result = response.text.strip()
        if result and "Unknown" not in result and "Error" not in result:
            # 格式化结果，移除多余符号
            result = result.replace("+", "").replace("°C", "°C")
            return result

        return None

    def _fetch_from_sojson(self, city_code, city_name=""):
        """数据源4: sojson天气API (备用)"""
        if not city_name:
            return None

        try:
            url = f"http://t.weather.sojson.com/api/weather/city/{city_code}"
            headers = {"User-Agent": self.get_random_ua()}
            response = self.session.get(url, headers=headers, timeout=8)
            data = response.json()

            if data.get("status") == 200:
                weather_data = data.get("data", {})
                wendu = weather_data.get("wendu", "")
                forecast = weather_data.get("forecast", [])
                if forecast:
                    today = forecast[0]
                    weather_type = today.get("type", "")
                    if wendu and weather_type:
                        return f"{weather_type} {wendu}°C"
        except:
            pass

        return None


# 创建全局天气管理器实例
weather_manager = WeatherDataManager()


def get_weather_info_from_web(city_code, city_name=""):
    """
    获取天气信息 - v1.90增强版
    使用多数据源自动切换，支持缓存和容错
    """
    # 从city_mapping获取城市名（如果未提供）
    if not city_name:
        for name, code in city_mapping.items():
            if code == city_code:
                city_name = name
                break

    return weather_manager.get_weather(city_code, city_name)

def get_weekly_weather_info(city_code):
    try:
        url = f"http://www.weather.com.cn/weather/{city_code}.shtml"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=5)
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.text, 'html.parser')
        forecast_div = soup.find('div', id='7d')
        if forecast_div:
            ul = forecast_div.find('ul')
            if ul:
                li_list = ul.find_all('li')
                forecast_list = []
                for li in li_list:
                    date_tag = li.find('h1')
                    date_text = date_tag.text.strip() if date_tag else ""
                    wea_tag = li.find('p', class_='wea')
                    wea_text = wea_tag.text.strip() if wea_tag else ""
                    tem_tag = li.find('p', class_='tem')
                    if tem_tag:
                        high_temp_tag = tem_tag.find('span')
                        high_temp = high_temp_tag.text.strip() if high_temp_tag else ""
                        low_temp_tag = tem_tag.find('i')
                        low_temp = low_temp_tag.text.strip() if low_temp_tag else ""
                        tem_text = f"最高温度: {high_temp}°C，最低温度: {low_temp}"
                    else:
                        tem_text = ""
                    forecast_list.append(f"{date_text}: {wea_text} {tem_text}")
                return "\n".join(forecast_list)
            else:
                return "无法获取一周天气预报"
        else:
            return "无法获取一周天气预报"
    except Exception as e:
        logging.error(f"获取一周天气预报出错: {e}")
        return "无法获取一周天气预报"

def get_detailed_weather_info(city_code):
    try:
        url = f"http://www.weather.com.cn/weather/{city_code}.shtml"
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            response.encoding = "utf-8"
            soup = BeautifulSoup(response.text, "html.parser")
            today_info = {}
            today = soup.select_one(".today")
            if today:
                today_info["日期"] = today.select_one("h1").get_text(strip=True) if today.select_one("h1") else "无信息"
                today_info["天气"] = today.select_one(".wea").get_text(strip=True) if today.select_one(".wea") else "无信息"
            else:
                today_info["日期"] = "无信息"
                today_info["天气"] = "无信息"
            tem = soup.select_one(".tem")
            if tem:
                high_temp_tag = tem.find("span")
                low_temp_tag = tem.find("i")
                if high_temp_tag and low_temp_tag:
                    high_temp = high_temp_tag.get_text(strip=True)
                    low_temp = low_temp_tag.get_text(strip=True)
                    today_info["温度"] = f"最高温度: {high_temp}°C，最低温度: {low_temp}"
                else:
                    today_info["温度"] = tem.get_text(strip=True)
            else:
                today_info["温度"] = "无信息"
            win = soup.select_one(".win")
            if win:
                span_win = win.select_one("span")
                today_info["风向"] = span_win["title"] if span_win and span_win.has_attr("title") else "无信息"
                today_info["风速"] = win.select_one("i").get_text(strip=True) if win.select_one("i") else "无信息"
            else:
                today_info["风向"] = "无信息"
                today_info["风速"] = "无信息"
            details = soup.select(".clearfix > li")
            for item in details:
                title_elem = item.select_one("p.tit")
                if title_elem:
                    key = title_elem.get_text(strip=True)
                else:
                    em_elem = item.select_one("em")
                    key = em_elem.get_text(strip=True) if em_elem else ""
                if not key or key in ["未知", "/"]:
                    continue
                desc_elem = item.select_one("p.con")
                if desc_elem:
                    value = desc_elem.get_text(strip=True)
                else:
                    span_elem = item.select_one("span")
                    value = span_elem.get_text(strip=True) if span_elem else "无信息"
                today_info[key] = value
            lifestyle_items = soup.select(".lifestyle li")
            if lifestyle_items:
                lifestyle_info = {}
                for item in lifestyle_items:
                    title_elem = item.select_one("p.tit")
                    desc_elem = item.select_one("p.con")
                    if title_elem:
                        key = title_elem.get_text(strip=True)
                        value = desc_elem.get_text(strip=True) if desc_elem else "无信息"
                        lifestyle_info[key] = value
                today_info["生活指数"] = lifestyle_info if lifestyle_info else "无信息"
            else:
                today_info["生活指数"] = "无信息"
            sun = soup.select_one(".sun")
            if sun:
                today_info["日出"] = sun.select_one(".sun-up").get_text(strip=True) if sun.select_one(".sun-up") else "无信息"
                today_info["日落"] = sun.select_one(".sun-down").get_text(strip=True) if sun.select_one(".sun-down") else "无信息"
            else:
                today_info["日出"] = "无信息"
                today_info["日落"] = "无信息"
            return today_info
        except requests.exceptions.RequestException as e:
            print(f"请求失败: {e}")
            return None
        except Exception as e:
            print(f"解析失败: {e}")
            return None
    except Exception as e:
        print(f"发生了未捕获的异常: {e}")
        return None

# 以下为 TTS 部分改进，增加中英文支持

def contains_chinese(text):
    return re.search("[\u4e00-\u9fff]", text) is not None

def set_voice_for_text(engine, text):
    if not engine:
        return
    try:
        voices = engine.getProperty('voices')
        if not voices:
            return
        if contains_chinese(text):
            for voice in voices:
                if 'Chinese' in voice.name or 'Huihui' in voice.name or 'Yaoyao' in voice.name:
                    engine.setProperty('voice', voice.id)
                    return
        else:
            for voice in voices:
                if "David" in voice.name or "Zira" in voice.name or "Alex" in voice.name:
                    engine.setProperty('voice', voice.id)
                    return
    except Exception as e:
        print(f"设置语音失败: {e}")

def preprocess_text(text):
    text = text.replace("；", ", ")
    if not (text.endswith("。") or text.endswith(".")):
        text += "。"
    return text

def filter_rich_text(text):
    """
    移除常见的富文本格式符号，例如 '#'、'*'、'_'、'~'、'`'、'>'、'[' 和 ']' 等，
    以确保播报文本中不包含这些格式控制字符。
    """
    return re.sub(r'[#\*\_\~\`\>\[\]]', '', text)


class SmoothClock:

    def clamp(self, v, mn, mx):
        return max(mn, min(v, mx))

    def __init__(self, root):
        self.root = root
        self.root.title("平滑时钟 —— 爬虫版天气预报")
        window_width = 600
        window_height = 600
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        center_x = (screen_width - window_width) // 2
        center_y = (screen_height - window_height) // 2
        offset = 420
        x = center_x + offset
        y = center_y
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.overrideredirect(True)  # 恢复无边框设置，隐藏标题栏
        self.root.wm_attributes("-transparentcolor", "magenta")
        self.root.attributes("-topmost", True)
        self.opacity = 1.0  # 默认设为不透明
        self.root.attributes("-alpha", self.opacity)
        # 移除窗口大小调整限制，因为无边框窗口不能通过拖拽边框调整大小
        # self.root.minsize(200, 200)
        # self.root.resizable(True, True)

        self.canvas = tk.Canvas(root, bg="magenta", width=window_width, height=window_height, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.root.update_idletasks()

        self.canvas.bind("<Configure>", self.on_resize)
        self.canvas.bind("<ButtonPress-1>", self.start_move)
        self.canvas.bind("<B1-Motion>", self.do_move)
        self.canvas.bind("<ButtonRelease-1>", self.end_move)
        self.canvas.bind("<Motion>", self.on_mouse_motion)
        self.canvas.bind("<Button-3>", self.show_context_menu)
        self.canvas.bind("<Double-Button-1>", self.show_about)

        # 添加缩放相关的变量
        self.is_scaling = False
        self.scale_start_pos = None
        self.scale_start_radius = None
        self.scale_start_factor = 1.0  # 缩放开始时的因子
        self.user_scale_factor = 1.0  # 用户自定义缩放因子
        self.temp_scale_factor = 1.0  # 临时缩放因子（拖动过程中使用）
        self.last_window_resize_time = 0  # 上次窗口调整时间



        self.weather_info = "加载天气信息..."
        self.weather_after_id = None
        self.last_weather_broadcast_hour = -1

        # 初始化TTS引擎，如果失败则禁用语音功能
        try:
            self.engine = pyttsx3.init('sapi5')
            self.engine.setProperty('rate', 172)
            self.engine.setProperty('volume', 1.0)
            self.tts_available = True
        except Exception as e:
            print(f"TTS引擎初始化失败: {e}")
            self.engine = None
            self.tts_available = False

        self.announcement_queue = queue.Queue()
        self.announcement_thread = threading.Thread(target=self.process_announcements, daemon=True)
        self.announcement_thread.start()
        self.chime_active = False
        self.chime_mode = "quarter"  # 默认刻点报时（每15分钟）
        # 可选模式："quarter"=15分钟, "half"=30分钟, "hour"=60分钟, "custom"=自定义
        self.custom_chime_interval = 15  # 自定义间隔（分钟）
        self.custom_intervals_history = []  # 历史自定义间隔值，初始为空
        self.last_announced = None
        self.reminders = load_reminders()
        self.reminder_active = True
        self.last_reminder_announced = set()
        self.current_reminder_minute = None
        self.weather_broadcast_active = True

        self.on_resize()
        self.base_radius = self.radius

        # 计算文本显示的初始位置，参照 update_clock 中的逻辑
        text_radius = self.radius - 35
        date_x = self.center_x
        date_y = self.center_y - text_radius + 20  # 与 update_clock 中一致
        brand_y = date_y + 20
        weather_x = self.center_x
        weather_y = self.center_y + text_radius - 20

        self.date_id = self.canvas.create_text(date_x, date_y,
                                                text="", font=("Arial", 12),
                                                fill="navy", tag="date")
        self.brand_id = self.canvas.create_text(date_x, brand_y,
                                                 text="Sofia 2025", font=("Arial", 8, "bold"),
                                                 fill="#0F52BA", tag="brand")
        self.weather_id = self.canvas.create_text(weather_x, weather_y,
                                                   text=self.weather_info, font=("Arial", 12),
                                                   fill="darkgreen", tag="weather")

        self.news_broadcast_active = news_db_is_configured()
        self.news_broadcast_count = 1
        self.news_broadcast_start_time = 5
        self.news_broadcast_end_time = 22
        self.news_broadcast_time_point = 31
        self.news_broadcast_interval = 60
        self.last_news_broadcast_cycle = ""
        self.last_news_broadcast_total = -9999  # 用于记录上一次新闻播报的总分钟数

        self.news_table = "info"  # 默认使用数据库中的 info 表

        # 初始化新闻播报的下一次触发时间
        now = datetime.now()
        current_total_minutes = now.hour * 60 + now.minute
        # 初始触发时间以当前小时的用户设定分钟值为基准
        initial_trigger = now.hour * 60 + self.news_broadcast_time_point
        # 如果初始触发时间已经过去，则调整到下一个小时
        if initial_trigger < current_total_minutes:
            initial_trigger += 60
        self.news_broadcast_next_trigger = initial_trigger

        self.news_cache = []
        self.played_news_ids = set()

        # 创建地区选择按钮（纯文字按钮，透明背景）
        self.city_index = 0  # 当前城市索引
        self.city_names = list(city_mapping.keys())
        self.frequently_used_cities = ["北京", "上海", "杭州", "广州", "成都"]  # 常用城市
        city_var.set(self.city_names[self.city_index])  # 设置初始值

        # 获取白色背景色（与表盘一致）
        white_bg = "#F8F9FA"  # 使用与表盘相同的柔和白色

        self.city_button = tk.Button(
            root, text=self.city_names[self.city_index],
            font=("微软雅黑", 11, "bold"), command=self.cycle_city,
            relief="flat", bd=0, bg=white_bg, fg="#2C3E50",
            cursor="hand2", highlightthickness=0,
            activebackground=white_bg, activeforeground="#34495E"
        )
        self.city_button_id = self.canvas.create_window(0, 0, window=self.city_button, tags="control")

        # 为城市按钮绑定额外事件和悬停效果
        self.city_button.bind("<Button-3>", self.show_city_menu)  # 右键菜单
        self.city_button.bind("<MouseWheel>", self.scroll_city)   # 滚轮切换
        self.city_button.bind("<Enter>", lambda e: self.city_button.config(fg="#34495E"))
        self.city_button.bind("<Leave>", lambda e: self.city_button.config(fg="#2C3E50"))

        # 报时按钮（白色背景按钮）
        self.chime_active = False
        self.chime_button = tk.Button(
            root, text="报时", font=("微软雅黑", 11, "bold"),
            command=self.toggle_chime,
            relief="flat", bd=0, bg=white_bg, fg="#2C3E50",
            cursor="hand2", highlightthickness=0,
            activebackground=white_bg, activeforeground="#34495E"
        )
        self.chime_button_id = self.canvas.create_window(0, 0, window=self.chime_button, tags="control")

        # 为报时按钮绑定右键菜单事件
        self.chime_button.bind("<Button-3>", self.show_chime_menu)

        # 作息报时按钮（白色背景按钮）
        self.reminder_active = True
        self.reminder_button = tk.Button(
            root, text="作息报时", font=("微软雅黑", 11, "bold"),
            command=self.toggle_reminder,
            relief="flat", bd=0, bg=white_bg, fg="#2C3E50",
            cursor="hand2", highlightthickness=0,
            activebackground=white_bg, activeforeground="#34495E"
        )
        self.reminder_button_id = self.canvas.create_window(0, 0, window=self.reminder_button, tags="control")
        self.update_reminder_button_style()

        # 创建新闻按钮（白色背景按钮）
        self.news_button = tk.Button(
            root, text="新闻", font=("微软雅黑", 11, "bold"),
            command=self.show_news_browser,
            relief="flat", bd=0, bg=white_bg, fg="#2C3E50",
            cursor="hand2", highlightthickness=0,
            activebackground=white_bg, activeforeground="#34495E"
        )
        self.news_button_id = self.canvas.create_window(0, 0, window=self.news_button, tags="control")

        # 为所有按钮添加悬停效果
        self.setup_button_hover_effects()

        self.on_resize()
        self.update_clock()
        self.update_weather()

    def setup_button_hover_effects(self):
        """设置所有按钮的悬停效果（仅文字颜色变化）"""
        # 新闻按钮悬停效果
        self.news_button.bind("<Enter>", lambda e: self.news_button.config(fg="#34495E"))
        self.news_button.bind("<Leave>", lambda e: self.news_button.config(fg="#2C3E50"))

    def process_announcements(self):
        while True:
            text = self.announcement_queue.get()
            if text is None:
                break

            # 使用独立线程和进程的方式来避免TTS引擎冲突
            success = False

            # 方法1：尝试使用新的TTS引擎实例
            try:
                import gc

                # 强制垃圾回收，清理之前的TTS实例
                gc.collect()

                # 创建全新的TTS引擎
                fresh_engine = pyttsx3.init()
                fresh_engine.setProperty('rate', 172)
                fresh_engine.setProperty('volume', 1.0)

                # 预处理文本
                processed_text = preprocess_text(text)
                set_voice_for_text(fresh_engine, processed_text)

                # 先播放提示音
                if os.path.isfile("dingdong.mp3"):
                    play_sound_mp3_blocking("dingdong.mp3")

                # TTS播报
                fresh_engine.say(processed_text)
                fresh_engine.runAndWait()

                # 立即清理
                fresh_engine.stop()
                del fresh_engine
                gc.collect()

                success = True

            except Exception as e:
                logging.error(f"TTS方法失败: {e}")

            # 方法2：如果TTS失败，使用Windows自带的说话功能
            if not success:
                try:
                    import subprocess

                    # 先播放提示音
                    if os.path.isfile("dingdong.mp3"):
                        play_sound_mp3_blocking("dingdong.mp3")

                    # 使用Windows PowerShell的Text-to-Speech功能
                    processed_text = preprocess_text(text)

                    # PowerShell命令来调用Windows TTS
                    ps_command = f'Add-Type -AssemblyName System.speech; $speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; $speak.Rate = 2; $speak.Speak("{processed_text}");'

                    # 在后台执行PowerShell命令
                    subprocess.run(["powershell", "-Command", ps_command],
                                 capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)

                    success = True

                except Exception as ps_error:
                    logging.error(f"PowerShell TTS失败: {ps_error}")

            # 方法3：完全失败时的提示
            if not success:
                try:
                    if os.path.isfile("dingdong.mp3"):
                        play_sound_mp3_blocking("dingdong.mp3")
                    else:
                        logging.warning(f"播报失败且无提示音文件: {text}")
                except Exception as final_error:
                    logging.error(f"最终播报失败: {final_error} - {text}")

    def enqueue_announcement(self, text):
        self.announcement_queue.put(text)

    def cycle_city(self):
        """循环切换城市"""
        self.city_index = (self.city_index + 1) % len(self.city_names)
        current_city = self.city_names[self.city_index]
        city_var.set(current_city)
        self.city_button.config(text=current_city)

    def scroll_city(self, event):
        """鼠标滚轮切换城市"""
        if event.delta > 0:  # 向上滚动
            self.city_index = (self.city_index - 1) % len(self.city_names)
        else:  # 向下滚动
            self.city_index = (self.city_index + 1) % len(self.city_names)

        current_city = self.city_names[self.city_index]
        city_var.set(current_city)
        self.city_button.config(text=current_city)

    def show_city_menu(self, event):
        """显示城市选择菜单"""
        menu = tk.Menu(self.root, tearoff=0)

        # 添加常用城市
        menu.add_command(label="== 常用城市 ==", state="disabled")
        for city in self.frequently_used_cities:
            if city in self.city_names:
                menu.add_command(label=f"📍 {city}", command=lambda c=city: self.select_city_direct(c))

        menu.add_separator()

        # 添加搜索功能
        menu.add_command(label="🔍 搜索城市...", command=self.search_city)

        menu.add_separator()

        # 添加所有城市（分组显示）
        menu.add_command(label="== 所有城市 ==", state="disabled")

        # 将城市按首字母分组
        city_groups = {}
        for city in self.city_names:
            first_char = city[0] if city else 'Z'
            if first_char not in city_groups:
                city_groups[first_char] = []
            city_groups[first_char].append(city)

        # 只显示前20个城市，避免菜单过长
        count = 0
        for first_char in sorted(city_groups.keys()):
            if count >= 20:
                menu.add_command(label="... 更多城市请使用搜索", state="disabled")
                break
            for city in sorted(city_groups[first_char]):
                if count >= 20:
                    break
                is_current = "✓ " if city == city_var.get() else "   "
                menu.add_command(label=f"{is_current}{city}", command=lambda c=city: self.select_city_direct(c))
                count += 1

        # 显示菜单
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def select_city_direct(self, city_name):
        """直接选择指定城市"""
        if city_name in self.city_names:
            self.city_index = self.city_names.index(city_name)
            city_var.set(city_name)
            self.city_button.config(text=city_name)

    def search_city(self):
        """搜索并选择城市"""
        search_window = tk.Toplevel(self.root)
        search_window.title("搜索城市")
        search_window.geometry("300x400")
        search_window.resizable(False, True)

        # 居中显示
        search_window.update_idletasks()
        width = search_window.winfo_width()
        height = search_window.winfo_height()
        x = (search_window.winfo_screenwidth() - width) // 2
        y = (search_window.winfo_screenheight() - height) // 2
        search_window.geometry(f"{width}x{height}+{x}+{y}")

        # 搜索框
        search_frame = tk.Frame(search_window)
        search_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(search_frame, text="搜索城市:", font=("Arial", 10)).pack(anchor="w")
        search_entry = tk.Entry(search_frame, font=("Arial", 12))
        search_entry.pack(fill=tk.X, pady=5)

        # 结果列表
        result_frame = tk.Frame(search_window)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        tk.Label(result_frame, text="城市列表:", font=("Arial", 10)).pack(anchor="w")

        # 创建列表框和滚动条
        list_frame = tk.Frame(result_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        city_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=("Arial", 11))
        city_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=city_listbox.yview)

        # 初始填充所有城市
        def update_city_list(filter_text=""):
            city_listbox.delete(0, tk.END)
            filtered_cities = [city for city in self.city_names if filter_text.lower() in city.lower()]
            for city in filtered_cities:
                city_listbox.insert(tk.END, city)

        update_city_list()

        # 搜索功能
        def on_search_change(*args):
            filter_text = search_entry.get()
            update_city_list(filter_text)

        search_entry.bind('<KeyRelease>', on_search_change)

        # 选择功能
        def on_city_select(event):
            selection = city_listbox.curselection()
            if selection:
                selected_city = city_listbox.get(selection[0])
                self.select_city_direct(selected_city)
                search_window.destroy()

        city_listbox.bind('<Double-Button-1>', on_city_select)

        # 按钮
        button_frame = tk.Frame(search_window)
        button_frame.pack(fill=tk.X, padx=10, pady=5)

        def select_and_close():
            selection = city_listbox.curselection()
            if selection:
                selected_city = city_listbox.get(selection[0])
                self.select_city_direct(selected_city)
            search_window.destroy()

        tk.Button(button_frame, text="选择", command=select_and_close, bg="lightgreen").pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="取消", command=search_window.destroy, bg="lightgray").pack(side=tk.LEFT, padx=5)

        # 设置焦点到搜索框
        search_entry.focus_set()
        search_window.transient(self.root)
        search_window.grab_set()

    def show_news_browser(self):
        """显示Sofia新闻浏览器"""
        try:
            # 获取当前设置的新闻数量，默认144条
            if not hasattr(self, 'news_display_count'):
                self.news_display_count = 144

            # 从数据库查询指定数量的Sofia新闻
            news_data = self.fetch_sofia_news(self.news_display_count)

            # 创建新闻浏览窗口
            news_window = tk.Toplevel(self.root)
            news_window.title(f"Sofia新闻浏览器 - 显示 {self.news_display_count} 条")
            news_window.geometry("800x600")
            news_window.resizable(True, True)

            # 智能定位：计算时钟窗口位置，避免重叠
            clock_x = self.root.winfo_x()
            clock_y = self.root.winfo_y()
            clock_width = self.root.winfo_width()
            clock_height = self.root.winfo_height()
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()

            # 先计算内容框的黄金比例尺寸以确定总窗口高度需求
            golden_ratio = 1.618
            total_width = 800 - 40  # 减去边距
            right_width = int(total_width * golden_ratio / (1 + golden_ratio))  # 较大部分
            content_width = right_width - 20  # 减少边距
            content_height = int(content_width * golden_ratio)  # 黄金比例高度

            # 计算实际需要的窗口尺寸
            news_width = 800
            news_height = max(600, content_height + 250)  # 增加底部按钮区域空间

            # 确保窗口不超过屏幕高度，留出更多空间给任务栏和标题栏
            if news_height > screen_height - 80:  # 增加任务栏和标题栏空间
                news_height = screen_height - 80

            # 计算Y坐标时，增加向上的偏移量，确保底部按钮可见
            upward_offset = 100  # 增加向上偏移到100像素
            bottom_margin = 100  # 确保底部有100像素边距

            # 优先尝试放在时钟右侧
            right_x = clock_x + clock_width + 10  # 10像素间距
            if right_x + news_width <= screen_width:
                # 右侧有足够空间
                news_x = right_x
                # 确保窗口不会超出屏幕底部，优先向上调整
                max_y = screen_height - news_height - bottom_margin
                news_y = max(0, min(clock_y - upward_offset, max_y))
            else:
                # 右侧空间不够，尝试左侧
                left_x = clock_x - news_width - 10  # 10像素间距
                if left_x >= 0:
                    # 左侧有足够空间
                    news_x = left_x
                    max_y = screen_height - news_height - bottom_margin
                    news_y = max(0, min(clock_y - upward_offset, max_y))
                else:
                    # 左右都放不下，居中显示，更大幅度向上偏移
                    news_x = max(0, (screen_width - news_width) // 2)
                    # 居中时向上偏移更多，确保按钮可见
                    center_y_with_offset = (screen_height - news_height) // 2 - upward_offset
                    news_y = max(0, center_y_with_offset)

            news_window.geometry(f"{news_width}x{news_height}+{news_x}+{news_y}")

            # 主框架
            main_frame = tk.Frame(news_window)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # 标题
            title_label = tk.Label(main_frame, text="📰 Sofia新闻 - 最新资讯",
                                  font=("Microsoft YaHei", 16, "bold"), fg="#2E86AB")
            title_label.pack(pady=(0, 10))

            # 创建左右分栏，使用前面计算好的黄金分割比例
            paned_window = tk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
            paned_window.pack(fill=tk.BOTH, expand=True)

            # 使用前面计算好的黄金分割比例宽度
            left_width = int(total_width / (1 + golden_ratio))  # 较小部分

            # 左侧新闻列表（较窄）
            left_frame = tk.Frame(paned_window)
            paned_window.add(left_frame, width=left_width)

            # 右侧内容显示（较宽，符合黄金分割）
            right_frame = tk.Frame(paned_window)
            paned_window.add(right_frame, width=right_width)

            # 新闻列表标题和设置区域
            header_frame = tk.Frame(left_frame)
            header_frame.pack(fill=tk.X, pady=(0, 5))

            tk.Label(header_frame, text="新闻列表:", font=("Microsoft YaHei", 12, "bold")).pack(side=tk.LEFT)

            # 数量设置控件
            setting_frame = tk.Frame(header_frame)
            setting_frame.pack(side=tk.RIGHT)

            tk.Label(setting_frame, text="显示:", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=(0, 2))

            # 数量输入框
            self.count_var = tk.IntVar(value=self.news_display_count)
            count_entry = tk.Entry(setting_frame, textvariable=self.count_var, font=("Microsoft YaHei", 9),
                                  width=6, justify="center")
            count_entry.pack(side=tk.LEFT, padx=(0, 2))

            tk.Label(setting_frame, text="条", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=(0, 5))

            # 应用按钮
            apply_button = tk.Button(setting_frame, text="应用", font=("Microsoft YaHei", 9),
                                   command=lambda: self.apply_news_count(news_window),
                                   bg="#2196F3", fg="white", padx=8, pady=2)
            apply_button.pack(side=tk.LEFT, padx=(0, 2))

            # 快捷按钮下拉
            quick_button = tk.Button(setting_frame, text="▼", font=("Microsoft YaHei", 8),
                                   command=lambda: self.show_quick_settings(quick_button, news_window),
                                   bg="#757575", fg="white", padx=5, pady=2)
            quick_button.pack(side=tk.LEFT)

            # 验证输入
            def validate_count(*args):
                try:
                    count = self.count_var.get()
                    if 1 <= count <= 6765:
                        count_entry.config(bg="white")
                        apply_button.config(state="normal")
                    else:
                        count_entry.config(bg="#ffcccc")
                        apply_button.config(state="disabled")
                except:
                    count_entry.config(bg="#ffcccc")
                    apply_button.config(state="disabled")

            self.count_var.trace("w", validate_count)

            # 绑定回车键
            count_entry.bind("<Return>", lambda e: self.apply_news_count(news_window))

            # 状态提示
            status_frame = tk.Frame(left_frame)
            status_frame.pack(fill=tk.X, pady=(0, 5))

            self.status_label = tk.Label(status_frame, text=f"当前加载了 {len(news_data) if news_data else 0} 条新闻",
                                        font=("Microsoft YaHei", 8), fg="gray")
            self.status_label.pack(anchor="w")

            # 新闻列表框
            list_frame = tk.Frame(left_frame)
            list_frame.pack(fill=tk.BOTH, expand=True)

            list_scrollbar = tk.Scrollbar(list_frame)
            list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            news_listbox = tk.Listbox(list_frame, yscrollcommand=list_scrollbar.set,
                                     font=("Microsoft YaHei", 10), activestyle="dotbox")
            news_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            list_scrollbar.config(command=news_listbox.yview)

            # 右侧内容显示区域的标题和提示
            content_header_frame = tk.Frame(right_frame)
            content_header_frame.pack(fill=tk.X, padx=10, pady=(0, 5))

            tk.Label(content_header_frame, text="新闻内容:", font=("Microsoft YaHei", 12, "bold")).pack(anchor="w")

            # Markdown支持状态提示
            status_text = "📝 支持丰富Markdown格式"
            status_color = "green"

            tk.Label(content_header_frame, text=status_text, font=("Microsoft YaHei", 9),
                    fg=status_color).pack(anchor="w")

            # 内容显示框，使用黄金分割比例设置高宽比
            content_frame = tk.Frame(right_frame, bg="#FAFAFA")
            content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

            # 创建内容文本框和滚动条
            content_scrollbar = tk.Scrollbar(content_frame)
            content_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            content_text = tk.Text(content_frame, yscrollcommand=content_scrollbar.set,
                                  font=("Microsoft YaHei", 11), wrap=tk.WORD, state=tk.DISABLED,
                                  bg="#FAFAFA", fg="#333333", padx=10, pady=10)
            content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            content_scrollbar.config(command=content_text.yview)

            # 填充新闻列表
            if news_data:
                for i, news in enumerate(news_data):
                    title = news.get('keyword', f'新闻{i+1}')[:50]  # 限制标题长度
                    if len(news.get('keyword', '')) > 50:
                        title += '...'
                    news_listbox.insert(tk.END, title)

                # 选择事件处理
                def on_news_select(event):
                    selection = news_listbox.curselection()
                    if selection:
                        index = selection[0]
                        selected_news = news_data[index]

                        # 显示新闻内容
                        title = selected_news.get('keyword', '无标题')
                        content = selected_news.get('info', '无内容')
                        news_id = selected_news.get('id', 'N/A')

                        # 构建带标题的Markdown内容
                        markdown_content = f"# {title}\n\n"
                        markdown_content += f"**新闻ID:** {news_id}\n\n"
                        markdown_content += "---\n\n"
                        markdown_content += content

                        # 使用Markdown渲染函数显示内容
                        render_markdown_to_text(content_text, markdown_content)

                news_listbox.bind('<<ListboxSelect>>', on_news_select)

                # 默认选中第一条新闻
                if news_data:
                    news_listbox.selection_set(0)
                    news_listbox.event_generate('<<ListboxSelect>>')

            else:
                news_listbox.insert(tk.END, "暂无新闻数据")
                render_markdown_to_text(content_text, "# 暂无新闻内容\n\n请稍后刷新或检查数据库连接。")

            # 底部按钮
            button_frame = tk.Frame(news_window)
            button_frame.pack(fill=tk.X, padx=10, pady=10)

            refresh_button = tk.Button(button_frame, text="刷新", font=("Microsoft YaHei", 11),
                                      command=lambda: self.refresh_news_browser(news_window),
                                      bg="#4CAF50", fg="white", padx=15)
            refresh_button.pack(side=tk.LEFT, padx=(0, 10))

            close_button = tk.Button(button_frame, text="关闭", font=("Microsoft YaHei", 11),
                                    command=news_window.destroy, bg="#f44336", fg="white", padx=15)
            close_button.pack(side=tk.RIGHT)

            # 设置窗口属性
            news_window.transient(self.root)

        except Exception as e:
            messagebox.showerror("错误", f"无法打开新闻浏览器: {e}")

    def fetch_sofia_news(self, limit=144):
        """从数据库获取Sofia新闻"""
        try:
            connection = get_db_connection()
            connection.ping(reconnect=True)
            with connection.cursor() as cursor:
                # 查询最新的Sofia新闻
                if not re.fullmatch(r"[A-Za-z0-9_]+", self.news_table):
                    raise ValueError("新闻数据表名称只能包含英文字母、数字和下划线")
                sql = f"SELECT id, keyword, info FROM `{self.news_table}` ORDER BY id DESC LIMIT {int(limit)}"
                cursor.execute(sql)
                results = cursor.fetchall()

                # 转换为字典列表 (results已经是字典格式，因为使用了DictCursor)
                news_list = []
                for row in results:
                    news_list.append({
                        'id': row['id'],
                        'keyword': row['keyword'],
                        'info': row['info']
                    })

                print(f"成功获取 {len(news_list)} 条Sofia新闻")
                return news_list

        except Exception as e:
            print(f"获取Sofia新闻失败: {e}")
            return []

    def refresh_news_browser(self, news_window):
        """刷新新闻浏览器"""
        news_window.destroy()
        self.show_news_browser()

    def apply_news_count(self, news_window):
        """应用新闻数量设置"""
        try:
            count = self.count_var.get()
            if 1 <= count <= 6765:
                self.news_display_count = count
                news_window.destroy()
                self.show_news_browser()
            else:
                messagebox.showerror("错误", "请输入1-6765之间的数字")
        except:
            messagebox.showerror("错误", "请输入有效的数字")

    def show_quick_settings(self, button, news_window):
        """显示快捷设置菜单"""
        menu = tk.Menu(self.root, tearoff=0)

        # 添加Fibonacci序列的常用值
        fibonacci_values = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597, 2584, 4181, 6765]

        menu.add_command(label="== 常用数量 ==", state="disabled")

        for value in fibonacci_values:
            is_current = "✓ " if value == self.news_display_count else "   "
            menu.add_command(
                label=f"{is_current}{value}条",
                command=lambda v=value: self.set_news_count_direct(v, news_window)
            )

        # 显示菜单
        try:
            # 获取按钮在屏幕上的位置
            button_x = button.winfo_rootx()
            button_y = button.winfo_rooty() + button.winfo_height()
            menu.tk_popup(button_x, button_y)
        finally:
            menu.grab_release()

    def set_news_count(self, parent_window):
        """显示设置新闻数量的对话框"""
        dialog = tk.Toplevel(parent_window)
        dialog.title("设置新闻显示数量")
        dialog.geometry("300x150")
        dialog.resizable(False, False)

        # 居中显示
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() - width) // 2
        y = (dialog.winfo_screenheight() - height) // 2
        dialog.geometry(f"{width}x{height}+{x}+{y}")

        # 输入框
        tk.Label(dialog, text="设置新闻显示数量:", font=("Microsoft YaHei", 12)).pack(pady=10)
        tk.Label(dialog, text="(范围: 1-6765条)", font=("Microsoft YaHei", 9), fg="gray").pack()

        count_var = tk.IntVar(value=self.news_display_count)
        entry = tk.Entry(dialog, textvariable=count_var, font=("Microsoft YaHei", 12), width=10, justify="center")
        entry.pack(pady=10)
        entry.select_range(0, tk.END)
        entry.focus_set()

        # 按钮
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)

        def confirm_count():
            try:
                count = count_var.get()
                if 1 <= count <= 6765:
                    self.news_display_count = count
                    dialog.destroy()
                    parent_window.destroy()  # 关闭当前新闻浏览器
                    self.show_news_browser()  # 重新打开新闻浏览器
                else:
                    messagebox.showerror("错误", "请输入1-6765之间的数字")
            except:
                messagebox.showerror("错误", "请输入有效的数字")

        def cancel_count():
            dialog.destroy()

        tk.Button(button_frame, text="确定", command=confirm_count, bg="lightgreen", padx=15).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="取消", command=cancel_count, bg="lightgray", padx=15).pack(side=tk.LEFT, padx=5)

        # 绑定回车键
        dialog.bind('<Return>', lambda e: confirm_count())
        dialog.bind('<Escape>', lambda e: cancel_count())

        # 设置为模态对话框
        dialog.transient(parent_window)
        dialog.grab_set()

    def set_news_count_direct(self, count, parent_window):
        """直接设置新闻数量"""
        self.news_display_count = count
        parent_window.destroy()  # 关闭当前新闻浏览器
        self.show_news_browser()  # 重新打开新闻浏览器


    def show_chime_menu(self, event):
        """显示报时选择菜单"""
        menu = tk.Menu(self.root, tearoff=0)

        # 添加标题
        menu.add_command(label="== 报时选择 ==", state="disabled")

        # 四个报时选项
        chime_options = [
            ("quarter", "刻点报时", "每15分钟报时"),
            ("half", "半点报时", "每30分钟报时"),
            ("hour", "整点报时", "每60分钟报时"),
            ("custom", "任意时段报时", f"每{self.custom_chime_interval}分钟报时")
        ]

        for mode, title, description in chime_options:
            is_current = "✓ " if self.chime_mode == mode else "   "
            menu.add_command(
                label=f"{is_current}{title} ({description})",
                command=lambda m=mode: self.select_chime_mode(m)
            )

        menu.add_separator()

        # 自定义时长设置
        if self.chime_mode == "custom":
            menu.add_command(label="设置自定义时长...", command=self.set_custom_chime_interval)
        else:
            menu.add_command(label="设置自定义时长...", command=self.set_custom_chime_interval, state="normal")

        # 显示菜单
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def select_chime_mode(self, mode):
        """选择报时模式"""
        self.chime_mode = mode
        # 重置报时状态，使新模式立即生效
        self.last_announced = None
        # 重置1分钟报时的专用状态
        if hasattr(self, 'last_chime_time'):
            self.last_chime_time = ''
        # 更新按钮显示
        self.update_chime_button_style()

    def set_custom_chime_interval(self):
        """设置自定义报时间隔"""
        dialog = tk.Toplevel(self.root)
        dialog.title("设置自定义报时间隔")

        # 动态计算对话框高度
        base_height = 180
        history_height = 80 if self.custom_intervals_history else 0
        dialog_height = base_height + history_height

        dialog.geometry(f"350x{dialog_height}")
        dialog.resizable(False, False)

        # 居中显示
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() - width) // 2
        y = (dialog.winfo_screenheight() - height) // 2
        dialog.geometry(f"{width}x{height}+{x}+{y}")

        # 输入框
        tk.Label(dialog, text="设置报时间隔 (分钟):", font=("微软雅黑", 12)).pack(pady=10)
        tk.Label(dialog, text="(范围: 1-1440分钟)", font=("微软雅黑", 9), fg="gray").pack()

        # 输入框和当前值
        input_frame = tk.Frame(dialog)
        input_frame.pack(pady=10)

        interval_var = tk.IntVar(value=self.custom_chime_interval)
        entry = tk.Entry(input_frame, textvariable=interval_var, font=("微软雅黑", 12), width=10, justify="center")
        entry.pack(side=tk.LEFT)
        entry.select_range(0, tk.END)
        entry.focus_set()

        # 历史值快速选择（仅在有历史记录时显示）
        if self.custom_intervals_history:
            history_frame = tk.Frame(dialog)
            history_frame.pack(pady=(5, 10))

            tk.Label(history_frame, text="快速选择:", font=("微软雅黑", 10), fg="gray").pack(anchor="w")

            # 显示最近的历史值（去重并排序）
            unique_history = sorted(list(set(self.custom_intervals_history)))[-6:]  # 最多显示6个

            buttons_frame = tk.Frame(history_frame)
            buttons_frame.pack()

            for i, hist_interval in enumerate(unique_history):
                def set_history_value(val=hist_interval):
                    interval_var.set(val)
                    entry.selection_clear()

                # 高亮当前选中的值
                bg_color = "lightblue" if hist_interval == self.custom_chime_interval else "lightgray"

                btn = tk.Button(buttons_frame, text=f"{hist_interval}分钟",
                               command=set_history_value, font=("微软雅黑", 9),
                               bg=bg_color, padx=8, pady=2)
                btn.grid(row=i//3, column=i%3, padx=2, pady=2)

        # 确认和取消按钮（总是显示在底部）
        button_frame = tk.Frame(dialog)
        button_frame.pack(side=tk.BOTTOM, pady=10)

        def confirm_interval():
            try:
                interval = interval_var.get()
                if 1 <= interval <= 1440:  # 1分钟到24小时
                    self.custom_chime_interval = interval

                    # 将新值添加到历史记录中（避免重复）
                    if interval not in self.custom_intervals_history:
                        self.custom_intervals_history.append(interval)
                        # 限制历史记录数量，保留最近的10个
                        if len(self.custom_intervals_history) > 10:
                            self.custom_intervals_history.pop(0)

                    # 自动切换到自定义模式并重置报时状态
                    self.chime_mode = "custom"
                    self.last_announced = None
                    # 更新按钮显示以反映新的模式
                    self.update_chime_button_style()
                    dialog.destroy()
                else:
                    messagebox.showerror("错误", "请输入1-1440之间的数字")
            except:
                messagebox.showerror("错误", "请输入有效的数字")

        def cancel_interval():
            dialog.destroy()

        tk.Button(button_frame, text="确定", command=confirm_interval, bg="lightgreen", padx=15).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="取消", command=cancel_interval, bg="lightgray", padx=15).pack(side=tk.LEFT, padx=5)

        # 绑定回车键
        dialog.bind('<Return>', lambda e: confirm_interval())
        dialog.bind('<Escape>', lambda e: cancel_interval())

        # 设置为模态对话框
        dialog.transient(self.root)
        dialog.grab_set()

    def toggle_chime(self):
        self.chime_active = not self.chime_active
        self.update_chime_button_style()


    def update_chime_button_style(self):
        # 根据当前缩放决定按钮文字
        is_small_size = self.user_scale_factor < 1.0  # 小于默认大小

        if self.chime_active:
            chime_text = "报时开" if is_small_size else "报时开"
        else:
            chime_text = "报时关" if is_small_size else "报时关"

        # 使用白色背景色和统一的文字颜色
        white_bg = "#F8F9FA"  # 与表盘相同的柔和白色
        fg_color = "#2C3E50"  # 统一使用深灰蓝色
        hover_color = "#34495E"

        # 更新按钮外观（白色背景，仅文字，字体大小自适应）
        self.chime_button.config(
            bg=white_bg, fg=fg_color, text=chime_text,
            font=("微软雅黑", self.get_current_button_font_size(), "bold"),
            relief="flat", bd=0, highlightthickness=0,
            activebackground=white_bg, activeforeground=hover_color
        )

        # 重新绑定悬停效果（仅改变文字颜色）
        self.chime_button.bind("<Enter>", lambda e: self.chime_button.config(fg=hover_color))
        self.chime_button.bind("<Leave>", lambda e: self.chime_button.config(fg=fg_color))

    def toggle_reminder(self):
        self.reminder_active = not self.reminder_active
        self.update_reminder_button_style()

    def update_reminder_button_style(self):
        # 根据当前缩放决定按钮文字
        is_small_size = self.user_scale_factor < 1.0  # 小于默认大小

        if self.reminder_active:
            reminder_text = "作息开" if is_small_size else "作息开"
        else:
            reminder_text = "作息关" if is_small_size else "作息关"

        # 使用白色背景色和统一的文字颜色
        white_bg = "#F8F9FA"  # 与表盘相同的柔和白色
        fg_color = "#2C3E50"  # 统一使用深灰蓝色
        hover_color = "#34495E"

        # 更新按钮外观（白色背景，仅文字，字体大小自适应）
        self.reminder_button.config(
            bg=white_bg, fg=fg_color, text=reminder_text,
            font=("微软雅黑", self.get_current_button_font_size(), "bold"),
            relief="flat", bd=0, highlightthickness=0,
            activebackground=white_bg, activeforeground=hover_color
        )

        # 重新绑定悬停效果（仅改变文字颜色）
        self.reminder_button.bind("<Enter>", lambda e: self.reminder_button.config(fg=hover_color))
        self.reminder_button.bind("<Leave>", lambda e: self.reminder_button.config(fg=fg_color))

    def get_current_button_font_size(self):
        """获取当前按钮应该使用的字体大小（随表盘大小变化）"""
        if hasattr(self, 'radius'):
            # 根据表盘半径计算字体大小，范围从8到18
            base_size = max(8, min(18, int(self.radius * 0.045)))
            return base_size
        else:
            return 11  # 默认字体大小

    def on_mouse_motion(self, event):
        """鼠标移动时改变光标样式"""
        if self.is_on_clock_rim(event.x, event.y):
            self.root.config(cursor="sizing")
        else:
            self.root.config(cursor="")

    def end_move(self, event):
        """鼠标释放时重置状态"""
        if self.is_scaling:
            # 缩放结束时，确认缩放因子并调整窗口大小
            self.user_scale_factor = self.temp_scale_factor
            self.adjust_window_size()

        self.is_scaling = False
        self.scale_start_pos = None
        self.root.config(cursor="")

    def adjust_window_size(self):
        """调整窗口大小以适应当前表盘尺寸"""
        # 获取屏幕尺寸
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # 计算需要的窗口大小
        base_radius = 150
        current_radius = base_radius * self.user_scale_factor
        margin = 120  # 为控件和透明度按钮预留边距
        needed_size = int(current_radius * 2 + margin)

        # 确保窗口不超过屏幕尺寸
        max_window_size = min(screen_width, screen_height) - 50
        window_size = min(needed_size, max_window_size)

        # 获取当前窗口位置和大小
        current_x = self.root.winfo_x()
        current_y = self.root.winfo_y()
        current_width = self.root.winfo_width()
        current_height = self.root.winfo_height()

        # 计算新位置，保持窗口中心不变
        new_x = current_x - (window_size - current_width) // 2
        new_y = current_y - (window_size - current_height) // 2

        # 确保窗口不超出屏幕边界
        new_x = max(0, min(new_x, screen_width - window_size))
        new_y = max(0, min(new_y, screen_height - window_size))

        # 更新窗口几何属性
        self.root.geometry(f"{window_size}x{window_size}+{new_x}+{new_y}")

        # 重新绘制界面
        self.root.after_idle(self.on_resize)

    def on_resize_internal_only(self):
        """内部重绘方法，只更新表盘大小，不调整窗口"""
        # 获取画布尺寸和中心点
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        w, h = max(w, 100), max(h, 100)
        self.center_x, self.center_y = w // 2, h // 2

        # 使用临时缩放因子计算半径
        base_radius = 150
        target_radius = int(base_radius * self.temp_scale_factor)
        max_radius_by_window = min(w, h) // 2 - 60
        self.radius = min(target_radius, max_radius_by_window)

        # 重新绘制表盘和控件
        self.canvas.delete("all")
        self.draw_clock_face()
        self.draw_transparency_controls()

        # 更新文本和控件位置（简化版本）
        self.update_display_elements()

    def update_display_elements(self):
        """更新显示元素的位置和字体"""
        # 计算字体大小
        def clamp(v, mn, mx): return max(mn, min(v, mx))
        date_sz    = clamp(int(self.radius * 0.06),  6, 20)
        brand_sz   = clamp(int(self.radius * 0.045), 5, 14)
        weather_sz = clamp(int(self.radius * 0.055), 6, 18)
        widget_sz  = clamp(int(self.radius * 0.04),  6, 14)

        # 创建字体对象
        import tkinter.font as tkFont
        date_font    = tkFont.Font(family="Arial", size=date_sz)
        brand_font   = tkFont.Font(family="Arial", size=brand_sz, weight="bold")
        weather_font = tkFont.Font(family="Arial", size=weather_sz)
        widget_font  = tkFont.Font(family="Arial", size=widget_sz)

        # 文字布局
        r = self.radius
        date_y    = self.center_y - r * 0.65
        brand_y   = self.center_y - r * 0.55
        weather_y = self.center_y + r * 0.65

        # 创建文本元素
        if hasattr(self, 'date_id'):
            self.canvas.delete(self.date_id)
        if hasattr(self, 'brand_id'):
            self.canvas.delete(self.brand_id)
        if hasattr(self, 'weather_id'):
            self.canvas.delete(self.weather_id)

        self.date_id = self.canvas.create_text(
            self.center_x, date_y, text="", font=date_font, fill="navy", tag="date"
        )
        self.brand_id = self.canvas.create_text(
            self.center_x, brand_y, text="Sofia 2025", font=brand_font, fill="#0F52BA", tag="brand"
        )
        self.weather_id = self.canvas.create_text(
            self.center_x, weather_y, text=self.weather_info, font=weather_font, fill="darkgreen", tag="weather"
        )

        # 为品牌文字绑定点击事件
        self.canvas.tag_bind("brand", "<Button-1>", self.open_sofia_platform)
        self.canvas.tag_bind("brand", "<Enter>", lambda e: self.canvas.config(cursor="hand2"))
        self.canvas.tag_bind("brand", "<Leave>", lambda e: self.canvas.config(cursor=""))

    def is_on_clock_rim(self, x, y):
        """检查鼠标是否在表盘外圈上"""
        if not hasattr(self, 'radius'):
            return False
        distance = math.sqrt((x - self.center_x) ** 2 + (y - self.center_y) ** 2)
        rim_tolerance = 20  # 外圈检测范围
        return self.radius - rim_tolerance <= distance <= self.radius + rim_tolerance

    def start_move(self, event):
        # 检查是否在表盘外圈上
        if self.is_on_clock_rim(event.x, event.y):
            # 开始缩放模式
            self.is_scaling = True
            self.scale_start_pos = (event.x, event.y)
            self.scale_start_radius = self.radius
            self.scale_start_factor = self.user_scale_factor  # 记录开始时的缩放因子
            self.temp_scale_factor = self.user_scale_factor    # 初始化临时因子
            self.root.config(cursor="sizing")
        else:
            # 开始移动模式
            self.is_scaling = False
            self.offset_x = event.x_root - self.root.winfo_x()
            self.offset_y = event.y_root - self.root.winfo_y()
            self.root.config(cursor="fleur")

    def do_move(self, event):
        if self.is_scaling:
            # 缩放模式：只更新表盘大小，不调整窗口
            if self.scale_start_pos:
                start_x, start_y = self.scale_start_pos
                # 计算从中心到起始位置的距离
                start_distance = math.sqrt((start_x - self.center_x) ** 2 + (start_y - self.center_y) ** 2)
                # 计算从中心到当前位置的距离
                current_distance = math.sqrt((event.x - self.center_x) ** 2 + (event.y - self.center_y) ** 2)

                if start_distance > 0:
                    # 根据距离变化计算缩放变化
                    scale_change = current_distance / start_distance

                    # 获取屏幕尺寸用于限制
                    screen_width = self.root.winfo_screenwidth()
                    screen_height = self.root.winfo_screenheight()
                    screen_min = min(screen_width, screen_height)

                    # 计算目标缩放因子
                    target_factor = self.scale_start_factor * scale_change

                    # 计算对应的半径
                    base_radius = 150
                    target_radius = base_radius * target_factor
                    max_screen_radius = screen_min * 0.45
                    min_radius = 50

                    # 限制半径范围
                    target_radius = max(min_radius, min(max_screen_radius, target_radius))

                    # 更新临时缩放因子
                    self.temp_scale_factor = target_radius / base_radius

                    # 只重绘表盘，不调整窗口大小
                    self.on_resize_internal_only()
        else:
            # 移动模式：移动窗口位置
            new_x = event.x_root - self.offset_x
            new_y = event.y_root - self.offset_y
            self.root.geometry(f"+{new_x}+{new_y}")

    def show_context_menu(self, event):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="设置提醒事项", command=self.open_reminders_editor)
        menu.add_command(label="修改城市配置文件", command=self.open_config)
        current_city = city_var.get()
        menu.add_command(label=f"{current_city} 今日天气预报", command=self.show_today_weather)
        menu.add_command(label=f"{current_city} 一周天气预报", command=self.show_weekly_weather)
        if self.weather_broadcast_active:
            menu.add_command(label="整点播报天气预报开 ✅", state="disabled", command=self.enable_weather_broadcast)
            menu.add_command(label="整点播报天气预报关", command=self.disable_weather_broadcast)
        else:
            menu.add_command(label="整点播报天气预报开", command=self.enable_weather_broadcast)
            menu.add_command(label="整点播报天气预报关 ✅", state="disabled", command=self.disable_weather_broadcast)
        if self.news_broadcast_active:
            menu.add_command(label="播放Sofia新闻开启 ✅", state="disabled", command=self.enable_news_broadcast)
            menu.add_command(label="播放Sofia新闻关闭", command=self.disable_news_broadcast)
        else:
            menu.add_command(label="播放Sofia新闻开启", command=self.enable_news_broadcast)
            menu.add_command(label="播放Sofia新闻关闭 ✅", state="disabled", command=self.disable_news_broadcast)
        menu.add_command(label="设置新闻播报选项", command=self.set_news_broadcast_options)
        menu.add_command(label="输入用户自定义新闻数据表", command=self.set_custom_news_table)
        menu.add_command(label="软件说明", command=self.show_manual)
        menu.add_separator()
        menu.add_command(label="退出", command=self.root.destroy)

        # 屏幕边界检查，防止菜单超出屏幕
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # 估算菜单高度（每个菜单项约25像素，加上边距）
        menu_item_count = 13  # 实际菜单项数量
        estimated_menu_height = menu_item_count * 25 + 10
        estimated_menu_width = 250  # 估算菜单宽度

        # 计算菜单位置，确保不超出屏幕边界
        menu_x = event.x_root
        menu_y = event.y_root

        # 检查右边界
        if menu_x + estimated_menu_width > screen_width:
            menu_x = screen_width - estimated_menu_width

        # 检查左边界
        if menu_x < 0:
            menu_x = 0

        # 检查底部边界
        if menu_y + estimated_menu_height > screen_height:
            menu_y = screen_height - estimated_menu_height

        # 检查顶部边界（关键修复：防止菜单顶部超出屏幕）
        if menu_y < 0:
            menu_y = 0

        menu.tk_popup(menu_x, menu_y)

    def enable_weather_broadcast(self):
        self.weather_broadcast_active = True
        messagebox.showinfo("提示", "整点播报天气预报功能已开启。")

    def disable_weather_broadcast(self):
        self.weather_broadcast_active = False
        messagebox.showinfo("提示", "整点播报天气预报功能已关闭。")

    def enable_news_broadcast(self):
        if not news_db_is_configured():
            messagebox.showwarning("新闻播报未配置", "请先在 config.ini 的 [news_database] 中填写数据库连接信息。")
            return
        self.news_broadcast_active = news_db_is_configured()
        messagebox.showinfo("提示", "播放Sofia新闻功能已开启。")

    def disable_news_broadcast(self):
        self.news_broadcast_active = False
        messagebox.showinfo("提示", "播放Sofia新闻功能已关闭。")

    def open_config(self):
        try:
            os.startfile("config.ini")
            logging.info("打开 config.ini 文件。")
        except Exception as e:
            logging.error(f"无法打开 config.ini: {e}")
            messagebox.showerror("错误", f"无法打开 config.ini: {e}")

    def refresh_reminders_editor(self):
        """
        重新加载 reminders.ini 文件，更新提醒编辑器中的文本和分组颜色。
        """
        if hasattr(self, 'reminders_editor_text_widget') and self.reminders_editor_text_widget.winfo_exists():
            try:
                with open("reminders.ini", "r", encoding="utf-8-sig") as f:
                    lines = f.readlines()
                self.reminders_editor_text_widget.delete("1.0", tk.END)
                for i, line in enumerate(lines):
                    self.reminders_editor_text_widget.insert(tk.END, line)
                    # 每3行设置一次颜色，交替使用两种背景色
                    color = "#f0fff0" if (i // 3) % 2 == 0 else "#ffdcdc"
                    start_index = f"{i+1}.0"
                    end_index = f"{i+1}.end"
                    self.reminders_editor_text_widget.tag_add(f"group_{i//3}", start_index, end_index)
                    self.reminders_editor_text_widget.tag_config(f"group_{i//3}", background=color)
            except Exception as e:
                logging.error(f"刷新提醒编辑器出错: {e}")


    def open_reminders_editor(self):
        try:
            editor_width = 400
            editor_height = 600
            root_x = self.root.winfo_rootx()
            root_y = self.root.winfo_rooty()
            clock_left = self.center_x - self.radius
            clock_right = self.center_x + self.radius
            clock_top = self.center_y - self.radius
            clock_bottom = self.center_y + self.radius
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()

            # 水平位置计算（保持原逻辑）
            right_pos = root_x + clock_right
            available_right = screen_width - right_pos
            left_pos = root_x + clock_left - editor_width
            if available_right >= left_pos:
                editor_x = right_pos
            else:
                editor_x = left_pos

            # 垂直位置计算（修复：确保窗口始终在屏幕内）
            # 优先放在钟表盘下方
            preferred_y = root_y + clock_bottom + 10  # 钟表盘底部下方10像素

            # 检查是否超出屏幕底部
            if preferred_y + editor_height <= screen_height:
                editor_y = preferred_y
            else:
                # 如果下方空间不够，尝试放在钟表盘上方
                top_y = root_y + clock_top - editor_height - 10  # 钟表盘顶部上方10像素
                if top_y >= 0:
                    editor_y = top_y
                else:
                    # 如果上下都不够，则确保窗口顶部不超出屏幕，底部尽量可见
                    editor_y = 0  # 强制从屏幕顶部开始
                    # 如果窗口高度超过屏幕高度，调整高度
                    if editor_height > screen_height:
                        editor_height = screen_height - 20

            editor = tk.Toplevel(self.root)
            editor.title("提醒编辑器")
            editor.geometry(f"{editor_width}x{editor_height}+{editor_x}+{editor_y}")
            editor.resizable(True, True)

            button_frame = tk.Frame(editor)
            button_frame.pack(side=tk.TOP, anchor="ne", fill=tk.X)

            text_frame = tk.Frame(editor)
            text_frame.pack(fill=tk.BOTH, expand=True)

            v_scroll = tk.Scrollbar(text_frame, orient=tk.VERTICAL)
            h_scroll = tk.Scrollbar(text_frame, orient=tk.HORIZONTAL)

            text_widget = tk.Text(
                text_frame,
                wrap="none",
                yscrollcommand=v_scroll.set,
                xscrollcommand=h_scroll.set,
                font=("Arial", 12)
            )
            v_scroll.config(command=text_widget.yview)
            h_scroll.config(command=text_widget.xview)
            v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
            h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
            text_widget.pack(fill=tk.BOTH, expand=True)

            # 保存提醒编辑器的文本控件引用，便于后续刷新
            self.reminders_editor_text_widget = text_widget
            self.reminders_editor = editor

            def parse_reminders(text):
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                reminders_list = []
                for i in range(0, len(lines), 3):
                    if i + 2 < len(lines):
                        reminders_list.append((lines[i], lines[i+1], lines[i+2]))
                return reminders_list

            def save_reminders():
                new_content = text_widget.get("1.0", tk.END).strip()
                try:
                    with open("reminders.ini", "w", encoding="utf-8") as f:
                        f.write(new_content)
                    self.reminders = load_reminders()
                    logging.info("提醒配置通过内置编辑器更新成功。")
                    messagebox.showinfo("保存成功", "提醒已保存并刷新配置。")
                    editor.destroy()
                except Exception as e:
                    logging.error(f"保存提醒失败: {e}")
                    messagebox.showerror("错误", f"保存提醒失败: {e}")

            def delete_first_config():
                current_text = text_widget.get("1.0", tk.END)
                current_reminders = parse_reminders(current_text)
                if current_reminders:
                    deleted_reminder = current_reminders[0]
                    confirmation = messagebox.askyesno("删除提醒",
                        f"确定删除以下提醒吗？\n\n时间: {deleted_reminder[0]}\n内容: {deleted_reminder[1]}\n铃声: {deleted_reminder[2]}")
                    if confirmation:
                        remaining_reminders = current_reminders[1:]
                        new_text = "\n".join([f"{r[0]}\n{r[1]}\n{r[2]}" for r in remaining_reminders])
                        # 同时更新文件
                        with open("reminders.ini", "w", encoding="utf-8") as f:
                            f.write(new_text)
                        self.reminders = load_reminders()
                        logging.info("删除了最先的一条提醒")
                        # 调用刷新函数，确保编辑器显示最新内容和颜色
                        self.refresh_reminders_editor()

            button_style = {"bg": "lightblue", "fg": "black", "padx": 5, "pady": 5}

            insert_button = tk.Button(button_frame, text="插入新配置", command=self.insert_new_config, **button_style)
            insert_button.pack(side=tk.LEFT, padx=10, pady=5)

            delete_button = tk.Button(button_frame, text="删除最先提醒", command=delete_first_config, **button_style)
            delete_button.pack(side=tk.LEFT, padx=10, pady=5)

            save_button = tk.Button(button_frame, text="保存新配置", command=save_reminders, **button_style)
            save_button.pack(side=tk.LEFT, padx=10, pady=5)

            help_button = tk.Button(button_frame, text="帮助", command=lambda: messagebox.showinfo("提醒编辑器帮助",
                "1. 每条提醒占用3行：提醒时间、提醒内容、铃声文件。\n2. 请勿留空，否则可能无法解析。"), **button_style)
            help_button.pack(side=tk.LEFT, padx=10, pady=5)

            if os.path.exists("reminders.ini"):
                with open("reminders.ini", "r", encoding="utf-8-sig") as f:
                    lines = f.readlines()
            else:
                lines = []

            for i, line in enumerate(lines):
                text_widget.insert(tk.END, line)
                color = "#f0fff0" if (i // 3) % 2 == 0 else "#ffdcdc"
                start_index = f"{i+1}.0"
                end_index = f"{i+1}.end"
                text_widget.tag_add(f"group_{i//3}", start_index, end_index)
                text_widget.tag_config(f"group_{i//3}", background=color)

            editor.protocol("WM_DELETE_WINDOW", editor.destroy)
        except Exception as e:
            logging.error(f"打开提醒编辑器出错: {e}")
            messagebox.showerror("错误", f"无法打开提醒编辑器: {e}")


    def refresh_reminders_editor(self):
        """
        重新加载 reminders.ini 文件，更新提醒编辑器中的文本和颜色配置。
        """
        if hasattr(self, 'reminders_editor_text_widget') and self.reminders_editor_text_widget.winfo_exists():
            try:
                with open("reminders.ini", "r", encoding="utf-8-sig") as f:
                    lines = f.readlines()
                self.reminders_editor_text_widget.delete("1.0", tk.END)
                for i, line in enumerate(lines):
                    self.reminders_editor_text_widget.insert(tk.END, line)
                    # 每3行设置一次颜色，交替使用两种背景色
                    color = "#f0fff0" if (i // 3) % 2 == 0 else "#ffdcdc"
                    start_index = f"{i+1}.0"
                    end_index = f"{i+1}.end"
                    self.reminders_editor_text_widget.tag_add(f"group_{i//3}", start_index, end_index)
                    self.reminders_editor_text_widget.tag_config(f"group_{i//3}", background=color)
            except Exception as e:
                logging.error(f"刷新提醒编辑器出错: {e}")

    def delete_first_reminder(self):
        if not os.path.exists("reminders.ini"):
            messagebox.showwarning("警告", "reminders.ini 文件不存在。")
            return
        with open("reminders.ini", "r", encoding="utf-8-sig") as f:
            lines = f.read().splitlines()
        lines = [line.strip() for line in lines if line.strip()]
        if len(lines) < 3:
            messagebox.showwarning("警告", "没有足够的提醒项可删除。")
            return
        first_reminder = (lines[0], lines[1], lines[2])
        confirm = messagebox.askyesno("删除提醒",
            f"确定删除以下提醒吗？\n\n时间: {first_reminder[0]}\n内容: {first_reminder[1]}\n铃声: {first_reminder[2]}")
        if confirm:
            remaining_lines = lines[3:]
            new_content = "\n".join(remaining_lines)
            with open("reminders.ini", "w", encoding="utf-8") as f:
                f.write(new_content)
            self.reminders = load_reminders()
            logging.info("删除了最先的一条提醒")
            messagebox.showinfo("删除成功", "已删除最先的提醒项。")
            # 刷新提醒编辑器中的显示内容及颜色配置
            self.refresh_reminders_editor()

    def insert_new_config(self):
        insert_window = tk.Toplevel(self.root)
        insert_window.title("插入新配置")
        width, height = 300, 180
        sw = insert_window.winfo_screenwidth()
        sh = insert_window.winfo_screenheight()
        x = (sw - width) // 2
        y = (sh - height) // 2
        insert_window.geometry(f"{width}x{height}+{x}+{y}")

        label_time = tk.Label(insert_window, text="提醒时间:")
        label_time.grid(row=0, column=0, padx=5, pady=5, sticky="e")
        current_hour = datetime.now().hour
        current_minute = datetime.now().minute
        hour_spinbox = tk.Spinbox(insert_window, from_=0, to=23, width=3, format="%02.0f")
        hour_spinbox.delete(0, "end")
        hour_spinbox.insert(0, f"{current_hour:02d}")
        hour_spinbox.grid(row=0, column=1, padx=(5, 0), pady=5, sticky="w")
        minute_spinbox = tk.Spinbox(insert_window, from_=0, to=59, width=3, format="%02.0f")
        minute_spinbox.delete(0, "end")
        minute_spinbox.insert(0, f"{current_minute:02d}")
        minute_spinbox.grid(row=0, column=2, padx=(5, 5), pady=5, sticky="w")

        label_content = tk.Label(insert_window, text="提醒内容:")
        label_content.grid(row=1, column=0, padx=5, pady=5, sticky="e")
        entry_content = tk.Entry(insert_window)
        entry_content.insert(0, "输入提醒内容")
        entry_content.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="we")

        label_sound = tk.Label(insert_window, text="铃声:")
        label_sound.grid(row=2, column=0, padx=5, pady=5, sticky="e")
        entry_sound = tk.Entry(insert_window)
        entry_sound.insert(0, "dingdong.mp3")
        entry_sound.grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky="we")

        def confirm_insert():
            new_time = f"{int(hour_spinbox.get()):02d}:{int(minute_spinbox.get()):02d}"
            new_content = entry_content.get().strip()
            new_sound = entry_sound.get().strip()
            new_block = f"{new_time}\n{new_content}\n{new_sound}\n"
            if os.path.exists("reminders.ini"):
                with open("reminders.ini", "r", encoding="utf-8-sig") as f:
                    current_content = f.read()
            else:
                current_content = ""
            updated_content = new_block + current_content
            with open("reminders.ini", "w", encoding="utf-8") as f:
                f.write(updated_content)
            self.reminders = load_reminders()
            messagebox.showinfo("插入成功", "新提醒配置已插入。")
            # 刷新提醒编辑器中的显示内容及颜色配置
            self.refresh_reminders_editor()
            insert_window.destroy()

        def cancel_insert():
            insert_window.destroy()

        confirm_button = tk.Button(insert_window, text="确认", command=confirm_insert)
        confirm_button.grid(row=3, column=0, padx=5, pady=10)
        cancel_button = tk.Button(insert_window, text="取消", command=cancel_insert)
        cancel_button.grid(row=3, column=1, padx=5, pady=10)


    def refresh_config(self, auto=False):
        try:
            config.read("config.ini", encoding="utf-8")
            global city_mapping
            city_mapping = dict(config.items("city_mapping"))
            # 更新城市列表和按钮文本
            self.city_names = list(city_mapping.keys())
            # 更新常用城市列表，确保都在新的城市列表中
            self.frequently_used_cities = [city for city in self.frequently_used_cities if city in self.city_names]
            if self.city_index >= len(self.city_names):
                self.city_index = 0
            current_city = self.city_names[self.city_index] if self.city_names else "未知"
            city_var.set(current_city)
            self.city_button.config(text=current_city)
            self.reminders = load_reminders()
            self.update_weather_immediately()
            logging.info("配置刷新成功。")
            if not auto:
                messagebox.showinfo("刷新配置", "配置刷新成功！")
        except Exception as e:
            logging.error(f"配置刷新失败: {e}")
            if not auto:
                messagebox.showerror("错误", f"刷新配置失败: {e}")

    def show_today_weather(self):
        current_city = city_var.get()
        if current_city in city_mapping:
            city_code = city_mapping[current_city]
            detailed_info = get_detailed_weather_info(city_code)
            if detailed_info:
                info_lines = [f"{key}: {value}" for key, value in detailed_info.items()]
                info_str = "\n".join(info_lines)
            else:
                info_str = "无法获取详细天气信息。"
        else:
            info_str = "当前选择的城市没有配置对应的城市代码。"

        weather_win = tk.Toplevel(self.root)
        weather_win.title("今日天气预报")
        weather_win.geometry("400x480")
        weather_win.resizable(False, False)

        weather_win.update_idletasks()
        win_width = weather_win.winfo_width()
        win_height = weather_win.winfo_height()
        screen_width = weather_win.winfo_screenwidth()
        screen_height = weather_win.winfo_screenheight()
        x = (screen_width - win_width) // 2
        y = (screen_height - win_height) // 2
        weather_win.geometry(f"{win_width}x{win_height}+{x}+{y}")

        header_label = tk.Label(weather_win, text=f"{current_city} 今日天气预报",
                                font=("Helvetica", 18, "bold"), fg="darkblue")
        header_label.pack(pady=20)

        content_label = tk.Label(weather_win, text=info_str,
                                 font=("Helvetica", 14), justify="left", anchor="w")
        content_label.pack(padx=20, pady=10, fill="both", expand=True)

        close_button = tk.Button(weather_win, text="关闭", font=("Helvetica", 16), command=weather_win.destroy)
        close_button.pack(pady=20)

    def show_weekly_weather(self):
        current_city = city_var.get()
        if current_city in city_mapping:
            city_code = city_mapping[current_city]
            weekly_info = get_weekly_weather_info(city_code)
            info_str = weekly_info if weekly_info else "无法获取一周天气预报。"
        else:
            info_str = "当前选择的城市没有配置对应的城市代码。"

        weather_win = tk.Toplevel(self.root)
        weather_win.title("一周天气预报")
        weather_win.geometry("460x480")
        weather_win.resizable(False, False)

        weather_win.update_idletasks()
        win_width = weather_win.winfo_width()
        win_height = weather_win.winfo_height()
        screen_width = weather_win.winfo_screenwidth()
        screen_height = weather_win.winfo_screenheight()
        x = (screen_width - win_width) // 2
        y = (screen_height - win_height) // 2
        weather_win.geometry(f"{win_width}x{win_height}+{x}+{y}")

        header_label = tk.Label(weather_win, text=f"{current_city} 一周天气预报",
                                font=("Helvetica", 18, "bold"), fg="darkblue")
        header_label.pack(pady=20)

        content_label = tk.Label(weather_win, text=info_str,
                                 font=("Helvetica", 11), justify="left", anchor="w")
        content_label.pack(padx=20, pady=10, fill="both", expand=True)

        close_button = tk.Button(weather_win, text="关闭", font=("Helvetica", 16), command=weather_win.destroy)
        close_button.pack(pady=20)

    def set_news_broadcast_options(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("新闻播报选项设置")
        dialog.resizable(False, False)

        # 先构建对话框内容，再设置位置
        tk.Label(dialog, text="单次播放新闻条数 (1-10):").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        count_var = tk.IntVar(value=self.news_broadcast_count)
        tk.Spinbox(dialog, from_=1, to=10, textvariable=count_var, width=5).grid(row=0, column=1, padx=5, pady=5)

        tk.Label(dialog, text="播放开始时间 (小时,1-24):").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        start_var = tk.IntVar(value=self.news_broadcast_start_time)
        tk.Spinbox(dialog, from_=1, to=24, textvariable=start_var, width=5).grid(row=1, column=1, padx=5, pady=5)

        tk.Label(dialog, text="播放结束时间 (小时,1-24):").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        end_var = tk.IntVar(value=self.news_broadcast_end_time)
        tk.Spinbox(dialog, from_=1, to=24, textvariable=end_var, width=5).grid(row=2, column=1, padx=5, pady=5)

        tk.Label(dialog, text="首次播放触发点 (分钟,1-60):").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        point_var = tk.IntVar(value=self.news_broadcast_time_point)
        tk.Spinbox(dialog, from_=1, to=60, textvariable=point_var, width=5).grid(row=3, column=1, padx=5, pady=5)

        tk.Label(dialog, text="播放时间间隔 (分钟,5-6000):").grid(row=4, column=0, padx=5, pady=5, sticky="e")
        interval_var = tk.IntVar(value=self.news_broadcast_interval)
        tk.Spinbox(dialog, from_=5, to=6000, textvariable=interval_var, width=5).grid(row=4, column=1, padx=5, pady=5)

        def on_ok():
            try:
                if start_var.get() >= end_var.get():
                    messagebox.showerror("错误", "播放开始时间必须小于结束时间。")
                    return
                self.news_broadcast_count = count_var.get()
                self.news_broadcast_start_time = start_var.get()
                self.news_broadcast_end_time = end_var.get()
                self.news_broadcast_time_point = point_var.get()
                self.news_broadcast_interval = interval_var.get()

                # 重新计算下一次触发时间
                now = datetime.now()
                current_total_minutes = now.hour * 60 + now.minute
                initial_trigger = now.hour * 60 + self.news_broadcast_time_point
                if initial_trigger < current_total_minutes:
                    initial_trigger += 60
                self.news_broadcast_next_trigger = initial_trigger

                print("新的触发时间：", self.news_broadcast_next_trigger)  # 调试输出

                dialog.destroy()
                messagebox.showinfo("设置成功", "新闻播报选项已更新。")
            except Exception as e:
                print("on_ok 异常：", e)
                messagebox.showerror("错误", f"设置过程中发生异常：{e}")

        # Create the buttons AFTER defining on_ok and while dialog is still in scope:
        tk.Button(dialog, text="确定", command=on_ok).grid(row=5, column=0, padx=5, pady=10)
        tk.Button(dialog, text="取消", command=dialog.destroy).grid(row=5, column=1, padx=5, pady=10)

        # 智能定位：避开表盘，确保对话框可见
        dialog.update_idletasks()
        dialog_width = dialog.winfo_reqwidth()
        dialog_height = dialog.winfo_reqheight()
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()

        # 获取表盘位置和大小
        clock_x = self.root.winfo_x()
        clock_y = self.root.winfo_y()
        clock_width = self.root.winfo_width()
        clock_height = self.root.winfo_height()

        # 尝试在表盘右侧放置对话框
        right_x = clock_x + clock_width + 20
        if right_x + dialog_width <= screen_width:
            dialog_x = right_x
            dialog_y = max(0, min(clock_y, screen_height - dialog_height))
        else:
            # 右侧空间不够，尝试左侧
            left_x = clock_x - dialog_width - 20
            if left_x >= 0:
                dialog_x = left_x
                dialog_y = max(0, min(clock_y, screen_height - dialog_height))
            else:
                # 左右都不够，尝试上方或下方
                if clock_y >= dialog_height + 20:
                    # 表盘上方有空间
                    dialog_x = max(0, min(clock_x, screen_width - dialog_width))
                    dialog_y = clock_y - dialog_height - 20
                elif clock_y + clock_height + 20 + dialog_height <= screen_height:
                    # 表盘下方有空间
                    dialog_x = max(0, min(clock_x, screen_width - dialog_width))
                    dialog_y = clock_y + clock_height + 20
                else:
                    # 最后选择：屏幕中央，但偏向左上角避免完全重叠
                    dialog_x = max(50, (screen_width - dialog_width) // 3)
                    dialog_y = max(50, (screen_height - dialog_height) // 3)

        dialog.geometry(f"{dialog_width}x{dialog_height}+{dialog_x}+{dialog_y}")

        # 设置为模态对话框，但确保位置正确后再grab
        dialog.transient(self.root)
        dialog.grab_set()


    def load_news_cache(self, limit=None):
        """
        加载新闻数据，默认按新闻播报条数的 3 倍查询，
        可通过参数 limit 指定查询条数。
        """
        try:
            connection = get_db_connection()
            connection.ping(reconnect=True)
            with connection.cursor() as cursor:
                if limit is None:
                    limit = self.news_broadcast_count * 3
                # 使用 self.news_table 替代固定的 info 表
                if not re.fullmatch(r"[A-Za-z0-9_]+", self.news_table):
                    raise ValueError("新闻数据表名称只能包含英文字母、数字和下划线")
                sql = f"SELECT id, keyword, info FROM `{self.news_table}` ORDER BY id DESC LIMIT {int(limit)}"
                cursor.execute(sql)
                news = cursor.fetchall()
            connection.close()
            return news
        except Exception as e:
            logging.error(f"加载新闻失败: {e}")
            return []

    def set_custom_news_table(self):
        # 新建自定义输入对话框窗口
        dialog = tk.Toplevel(self.root)
        dialog.title("自定义新闻数据表")
        dialog.resizable(False, False)
        # 创建标签和输入框
        label = tk.Label(dialog, text="请输入自定义新闻数据表名称：", font=("Arial", 12))
        label.pack(padx=20, pady=10)
        entry = tk.Entry(dialog, font=("Arial", 12))
        entry.insert(0, self.news_table)
        entry.pack(padx=20, pady=5)

        # 定义确定按钮的回调函数
        def on_ok():
            table = entry.get().strip()
            if table:
                try:
                    connection = get_db_connection()
                    with connection.cursor() as cursor:
                        cursor.execute("SHOW TABLES LIKE %s", (table,))
                        result = cursor.fetchone()
                    connection.close()
                    if result:
                        self.news_table = table
                        messagebox.showinfo("提示", f"已使用自定义新闻数据表: {table}")
                    else:
                        messagebox.showwarning("警告", f"表 {table} 不存在，继续使用默认数据表")
                except Exception as e:
                    logging.error(f"检查数据表出错: {e}")
                    messagebox.showerror("错误", f"检查数据表时出错：{e}")
            dialog.destroy()

        # 创建按钮框架和按钮
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        ok_button = tk.Button(button_frame, text="确定", width=8, command=on_ok)
        ok_button.pack(side=tk.LEFT, padx=10)
        cancel_button = tk.Button(button_frame, text="取消", width=8, command=dialog.destroy)
        cancel_button.pack(side=tk.LEFT, padx=10)

        # 居中显示该弹窗：更新布局后获取窗口尺寸，并计算居中坐标
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() - width) // 2
        y = (dialog.winfo_screenheight() - height) // 2
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        dialog.transient(self.root)
        dialog.grab_set()
        self.root.wait_window(dialog)

    def clear_old_news_cache(self, news_list, played_ids):
        """
        过滤已播报过的新闻，返回未播报的新闻列表。
        """
        return [news for news in news_list if int(news["id"]) not in played_ids]



    def broadcast_news(self):
        # 加载当前周已播放的新闻ID记录
        played_data = load_played_ids()
        played_ids = set(played_data.get("ids", []))

        # 定义依次尝试的 LIMIT 值：第一次使用新闻播报条数的21倍，然后987，最后2584
        query_limits = [self.news_broadcast_count * 21, 987, 2584]
        unplayed_news = []
        new_cache = None

        # 依次尝试不同的 LIMIT 值进行查询
        for limit in query_limits:
            new_cache = self.load_news_cache(limit=limit)
            if not new_cache:
                continue
            unplayed_news = self.clear_old_news_cache(new_cache, played_ids)
            if unplayed_news:
                break

        # 如果所有查询均未返回未播报新闻
        if not unplayed_news:
            if new_cache:
                broadcast_items = [max(new_cache, key=lambda x: int(x["id"]))]
            else:
                return  # 无任何新闻则退出播报
        else:
            # 如果已有播放记录，优先选择ID大于最大已播报ID的新新闻
            if played_ids:
                max_played = max(played_ids)
                new_news = [news for news in unplayed_news if int(news["id"]) > max_played]
                candidates = new_news if new_news else unplayed_news
            else:
                candidates = unplayed_news

            # 从候选新闻中选取最新的几条（按ID降序）
            broadcast_items = sorted(candidates, key=lambda x: int(x["id"]), reverse=True)[:self.news_broadcast_count]

        # 更新播放记录，防止重复播报
        for record in broadcast_items:
            played_ids.add(int(record["id"]))
        played_data["ids"] = list(played_ids)
        save_played_ids(played_data)

        # 组合播报文本
        announcements = [
            f"新闻标题: {record.get('keyword', '')}；内容: {record.get('info', '')}"
            for record in broadcast_items
        ]
        announcement_text = "； ".join(announcements)

        # 过滤富文本格式符号
        announcement_text = filter_rich_text(announcement_text)

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        full_announcement = f"现在是: {current_time}。下面播报索菲亚最新新闻：{announcement_text}。"

        # 同样对最终文本进行过滤
        full_announcement = filter_rich_text(full_announcement)

        self.enqueue_announcement(full_announcement)




    #def check_and_broadcast_news_immediately(self):
    #    now = datetime.now()
    #    cycle = now.strftime("%Y-%m-%d %H:%M")
    #    if self.news_broadcast_active and self.news_broadcast_start_time <= now.hour < self.news_broadcast_end_time:
    #        # 检查当前小时中，从设定的分钟点开始，每隔news_broadcast_interval分钟触发
    #        if now.minute >= self.news_broadcast_time_point:
    #            if (now.minute - self.news_broadcast_time_point) % self.news_broadcast_interval == 0 and now.second < 2:
    #                if self.last_news_broadcast_cycle != cycle:
    #                    self.last_news_broadcast_cycle = cycle
    #                    threading.Thread(target=self.broadcast_news, daemon=True).start()

    def open_sofia_platform(self, event):
        """打开Sofia数智平台"""
        try:
            url = os.environ.get("SOFIA_PLATFORM_URL", "").strip()
            if not url:
                url = config.get("links", "sofia_platform_url", fallback="").strip()
            if not url.startswith(("https://", "http://")):
                messagebox.showinfo("提示", "请先在 config.ini 的 [links] 中配置平台网址。")
                return
            webbrowser.open(url)
            logging.info("已打开Sofia数智平台")
        except Exception as e:
            logging.error(f"打开Sofia数智平台失败: {e}")
            messagebox.showerror("错误", f"无法打开Sofia数智平台: {e}")

    def show_about(self, event):
        current_tags = self.canvas.gettags("current")
        if "opacity_up" in current_tags or "opacity_down" in current_tags:
            return
        messagebox.showinfo("关于 Sofia 时钟 v1.90", "一个可自定义的桌面时钟，支持天气显示、语音播报和日程提醒。\n公开版本不含预设的私人数据库连接信息。")

    def show_manual(self):
        # 创建专用的说明窗口
        manual_window = tk.Toplevel(self.root)
        manual_window.title("Sofia时钟 - 软件说明")
        manual_window.geometry("700x600")
        manual_window.resizable(True, True)

        # 居中显示
        manual_window.update_idletasks()
        width = manual_window.winfo_width()
        height = manual_window.winfo_height()
        x = (manual_window.winfo_screenwidth() - width) // 2
        y = (manual_window.winfo_screenheight() - height) // 2
        manual_window.geometry(f"{width}x{height}+{x}+{y}")

        # 创建滚动文本框
        main_frame = tk.Frame(manual_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 标题
        title_label = tk.Label(main_frame, text="📚 Sofia时钟 软件使用说明",
                              font=("Arial", 18, "bold"), fg="#2E86AB")
        title_label.pack(pady=(0, 15))

        # 创建滚动文本区域
        text_frame = tk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        # 滚动条
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 文本框
        text_widget = tk.Text(text_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set,
                             font=("Microsoft YaHei", 11), bg="#FAFAFA", fg="#333333",
                             padx=15, pady=15, spacing1=3, spacing2=2, spacing3=3)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text_widget.yview)

        # 软件说明内容
        manual_content = """🌟 功能特色

📊 智能时钟显示
• 平滑圆形表盘设计，秒针流畅移动
• 支持鼠标拖拽调整位置和大小
• 透明度可调，不影响其他应用使用
• 自适应字体大小，清晰易读

🌤️ 实时天气预报
• 多城市天气支持，涵盖全国主要城市
• 今日天气、详细预报、一周预报
• 整点自动播报天气信息
• 网络爬虫实时获取最新数据

⏰ 智能提醒系统
• 支持冬令时/夏令时配置切换
• 自定义提醒时间和内容
• 多种铃声选择，个性化提醒
• 内置编辑器，方便管理提醒事项

📰 新闻播报功能
• 每日5-22点自动播报最新新闻
• 可配置播报频率和条数
• MySQL数据库存储，防重复播报
• 支持自定义新闻数据源

🔧 配置管理
• 实时监控配置文件变更
• 自动刷新设置，无需重启
• 可视化配置界面，操作简便

━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 快速使用指南

🎯 城市选择（多种方式）：
• 左键点击城市按钮 → 循环切换
• 鼠标滚轮 → 快速前后切换
• 右键点击 → 显示完整城市菜单
• 搜索功能 → 输入城市名快速定位

⚙️ 表盘调整：
• 拖拽中心 → 移动时钟位置
• 拖拽边缘 → 调整时钟大小
• 右侧按钮 → 调整透明度

🎵 功能开关：
• 报时开/关 → 智能报时开关状态（支持多种模式）
  - 左键：开启/关闭报时功能
  - 右键：选择报时模式（刻点/半点/整点/自定义）
• 作息开/关 → 按预设时间提醒开关状态
• 按钮文字直接显示当前状态，无需额外提示

🔔 报时模式选择：
• 刻点报时 → 每15分钟报时一次 (00、15、30、45分)
• 半点报时 → 每30分钟报时一次 (00、30分)
• 整点报时 → 每小时报时一次 (仅整点)
• 任意时段报时 → 用户自定义时长 (1-1440分钟)

📝 右键菜单功能：
• 设置提醒事项 → 管理日程安排
• 查看天气预报 → 详细天气信息
• 新闻播报设置 → 个性化新闻配置
• 城市配置管理 → 添加/删除城市

━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 配置文件说明

📁 config.ini
• 存储城市名称与代码映射
• 用于天气数据获取
• 可手动添加新城市

📁 reminders.ini
• 每3行为一组提醒设置：
  第1行：提醒时间 (如 08:30)
  第2行：提醒内容 (如 上课时间到)
  第3行：铃声文件 (如 dingdong.mp3)

📁 id.json
• 记录已播报的新闻ID
• 按月自动重置，避免重复

━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 新闻播报设置详解

📱 设置入口：
• 右键时钟 → "设置新闻播报选项"

⚙️ 配置参数说明：
• 单次播放新闻条数 (1-10条)
  - 每次播报的新闻数量
  - 推荐设置：1-3条

• 播放开始时间 (1-24小时)
  - 每日开始播报的小时数
  - 默认：5点 (早上5:00)

• 播放结束时间 (1-24小时)
  - 每日停止播报的小时数
  - 默认：22点 (晚上22:00)

• 首次播放触发点 (1-60分钟)
  - 每小时第几分钟开始播报
  - 默认：31分钟 (如 5:31, 6:31...)

• 播放时间间隔 (5-6000分钟)
  - 两次播报之间的间隔时间
  - 默认：60分钟 (每小时一次)

🔄 设置示例：
【场景1 - 办公室使用】
• 开始时间：8点，结束时间：18点
• 触发点：0分钟，间隔：120分钟
• 效果：8:00, 10:00, 12:00, 14:00, 16:00播报

【场景2 - 学校使用】
• 开始时间：6点，结束时间：22点
• 触发点：30分钟，间隔：180分钟
• 效果：6:30, 9:30, 12:30, 15:30, 18:30, 21:30播报

【场景3 - 家庭使用】
• 开始时间：7点，结束时间：21点
• 触发点：15分钟，间隔：240分钟
• 效果：7:15, 11:15, 15:15, 19:15播报

💡 使用技巧：
• 避开重要会议时间设置播报
• 间隔时间不要过短，建议≥30分钟
• 可设置为0条暂停播报，保持其他功能

━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 使用技巧

🎨 界面个性化：
• 调整透明度适应不同背景
• 缩放大小适应屏幕尺寸
• 置顶显示，随时查看时间
• 统一的按钮样式，简洁美观

📱 便捷操作：
• 双击显示软件说明
• 右键快速访问所有功能
• 滚轮快速切换城市
• 直观的开关状态显示

🔊 音频提醒：
• 支持MP3格式铃声
• 可自定义铃声文件
• TTS语音播报功能

📊 新闻播报优化：
• 根据使用场景调整播报频率
• 利用常用城市快速切换
• 自定义数据表获取特定新闻

🎯 界面美化：
• 去除不必要的阴影效果
• 聚焦的按钮文字显示
• 统一的颜色主题设计
• 清晰的状态指示方式

━━━━━━━━━━━━━━━━━━━━━━━━━━

👥 开发信息

🏫 开发团队：枫泾中学数智化应用研究小组
项目反馈请通过 GitHub 仓库的 Issues 页面提交。
🗓️ 版本信息：Sofia时钟 v1.88 (2025.12)
🎯 最新更新：品牌"Sofia 2025"文字可点击打开Sofia数智平台

💝 感谢使用Sofia时钟！
如有问题或建议，欢迎通过邮件联系我们。"""

        # 插入内容
        text_widget.insert(tk.END, manual_content)
        text_widget.config(state=tk.DISABLED)  # 设为只读

        # 配置文本样式
        text_widget.tag_configure("title", font=("Microsoft YaHei", 16, "bold"), foreground="#2E86AB")
        text_widget.tag_configure("section", font=("Microsoft YaHei", 14, "bold"), foreground="#A23B72")
        text_widget.tag_configure("highlight", font=("Microsoft YaHei", 12, "bold"), foreground="#F18F01")

        # 关闭按钮
        button_frame = tk.Frame(manual_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        close_button = tk.Button(button_frame, text="关闭", font=("Microsoft YaHei", 12),
                                command=manual_window.destroy, bg="#4CAF50", fg="white",
                                padx=20, pady=8)
        close_button.pack(side=tk.RIGHT)

        # 设置窗口属性
        manual_window.transient(self.root)
        manual_window.focus_set()


    def on_resize(self, event=None):
        # —— 1. 计算画布尺寸和中心点 ——
        if event:
            w, h = event.width, event.height
        else:
            w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        w, h = max(w, 100), max(h, 100)
        self.center_x, self.center_y = w // 2, h // 2

        # —— 2. 自动计算最佳半径，基于固定基础值和用户缩放 ——
        base_radius = 150  # 固定基础半径

        # 计算目标半径
        target_radius = int(base_radius * self.user_scale_factor)

        # 获取窗口尺寸作为参考
        max_radius_by_window = min(w, h) // 2 - 60  # 窗口限制的最大半径

        # 使用目标半径，但确保不超过窗口允许的范围
        self.radius = min(target_radius, max_radius_by_window)

        # —— 3. 预先计算控制按钮尺寸和间距，基于半径比例 ——
        btn_size = self.clamp(int(target_radius * 0.08), 10, 35)  # 按钮大小随半径缩放
        spacing  = self.clamp(int(target_radius * 0.02),  3, 15)  # 间距随半径缩放

        # —— 4. 确保透明度按钮在画布内 ——
        max_r = int((w - spacing - btn_size - 10) / 2)
        self.radius = min(self.radius, max_r)

        # —— 5. 动态字体大小，完全基于半径比例 ——
        def clamp(v, mn, mx): return max(mn, min(v, mx))
        date_sz    = clamp(int(self.radius * 0.06),  8, 22)   # 日期字体（略微增大）
        brand_sz   = clamp(int(self.radius * 0.045), 6, 16)   # 品牌字体
        weather_sz = clamp(int(self.radius * 0.055), 8, 20)   # 天气字体（略微增大）
        widget_sz  = clamp(int(self.radius * 0.04),  8, 16)   # 控件字体（略微增大）
        number_sz  = clamp(int(self.radius * 0.08),  10, 28)  # 时钟数字（略微增大）

        # 使用更优美的字体和样式
        self.date_font    = tkFont.Font(family="微软雅黑", size=date_sz, weight="bold")
        self.brand_font   = tkFont.Font(family="Georgia", size=brand_sz, weight="bold", slant="italic")
        self.weather_font = tkFont.Font(family="微软雅黑", size=weather_sz)
        self.number_font  = tkFont.Font(family="Times New Roman", size=number_sz, weight="bold")
        self.widget_font  = tkFont.Font(family="微软雅黑", size=widget_sz, weight="bold")

        # —— 6. 重绘表盘和控件 ——
        self.canvas.delete("all")
        self.draw_clock_face()
        self.draw_transparency_controls()

        # —— 7. 文字布局，位置基于半径比例，添加增强阴影效果 ——
        r = self.radius
        date_y    = self.center_y - r * 0.65    # 日期位置
        brand_y   = self.center_y - r * 0.55    # 品牌位置
        remind_y  = self.center_y - r * 0.35    # 提醒按钮
        chime_y   = self.center_y + r * 0.35    # 报时按钮
        news_x    = self.center_x + r * 0.75    # 新闻按钮（3点位置）
        weather_y = self.center_y + r * 0.65    # 天气位置

        # 创建文本元素（无阴影）

        # 日期文字
        self.date_id = self.canvas.create_text(
            self.center_x, date_y, text="", font=self.date_font,
            fill="#1A252F", tag="date"
        )

        # 品牌文字
        self.brand_id = self.canvas.create_text(
            self.center_x, brand_y, text="Sofia 2025", font=self.brand_font,
            fill="#7D3C98", tag="brand"
        )

        # 为品牌文字绑定点击事件
        self.canvas.tag_bind("brand", "<Button-1>", self.open_sofia_platform)
        self.canvas.tag_bind("brand", "<Enter>", lambda e: self.canvas.config(cursor="hand2"))
        self.canvas.tag_bind("brand", "<Leave>", lambda e: self.canvas.config(cursor=""))

        # 天气文字
        self.weather_id = self.canvas.create_text(
            self.center_x, weather_y, text=self.weather_info, font=self.weather_font,
            fill="#1E8449", tag="weather"
        )

        # —— 8. 控件位置和字体自适应 ——
        # 计算当前按钮字体大小（基于表盘半径）
        current_button_font_size = self.get_current_button_font_size()
        bold_widget_font = tkFont.Font(family="微软雅黑", size=current_button_font_size, weight="bold")

        # 白色背景色（与表盘一致）
        white_bg = "#F8F9FA"  # 使用与表盘相同的柔和白色

        # 根据表盘大小调整按钮文字显示逻辑
        is_small_size = self.user_scale_factor < 1.0  # 小于默认大小

        # 更新城市按钮的字体和样式
        if hasattr(self, 'city_button'):
            self.city_button.config(
                font=bold_widget_font,
                bg=white_bg, fg="#2C3E50",
                activebackground=white_bg, activeforeground="#34495E"
            )

        # 更新新闻按钮的字体和样式
        if hasattr(self, 'news_button'):
            self.news_button.config(
                font=bold_widget_font,
                bg=white_bg, fg="#2C3E50",
                activebackground=white_bg, activeforeground="#34495E"
            )

        # 更新按钮样式（保持当前状态的颜色），这会处理文字变化和字体自适应
        if hasattr(self, 'chime_button') and hasattr(self, 'chime_active'):
            self.update_chime_button_style()
        if hasattr(self, 'reminder_button') and hasattr(self, 'reminder_active'):
            self.update_reminder_button_style()

        # 控件位置基于半径计算，只处理城市选择控件
        widget_offset = r * 0.8
        city_x = max(20, self.center_x - widget_offset)

        if hasattr(self, "city_button"):
            self.city_button_id = self.canvas.create_window(
                city_x, self.center_y, window=self.city_button, tags="control"
            )
        # 移除大小选择控件的处理
        # if hasattr(self, "size_option_widget"):
        #     size_x = min(w - 20, self.center_x + widget_offset)
        #     self.size_option_id = self.canvas.create_window(
        #         size_x, self.center_y, window=self.size_option_widget, tags="control"
        #     )
        if hasattr(self, "reminder_button"):
            self.reminder_button_id = self.canvas.create_window(
                self.center_x, remind_y, window=self.reminder_button, tags="control"
            )
        if hasattr(self, "chime_button"):
            self.chime_button_id = self.canvas.create_window(
                self.center_x, chime_y, window=self.chime_button, tags="control"
            )
        if hasattr(self, "news_button"):
            self.news_button_id = self.canvas.create_window(
                news_x, self.center_y, window=self.news_button, tags="control"
            )

        self.canvas.tag_lower("control")


    def draw_clock_face(self):
        # 添加外部阴影效果
        shadow_offset = max(3, int(self.radius * 0.02))
        self.canvas.create_oval(
            self.center_x - self.radius + shadow_offset,
            self.center_y - self.radius + shadow_offset,
            self.center_x + self.radius + shadow_offset,
            self.center_y + self.radius + shadow_offset,
            fill="#E0E0E0", outline="", tags="shadow"
        )

        # 外圈边框，使用渐变效果的模拟
        outline_width = max(3, int(self.radius * 0.015))
        self.canvas.create_oval(
            self.center_x - self.radius,
            self.center_y - self.radius,
            self.center_x + self.radius,
            self.center_y + self.radius,
            fill="#F8F9FA",  # 更柔和的白色背景
            outline="#2C3E50",  # 深蓝灰色边框
            width=outline_width
        )

        # 内圈装饰
        inner_radius = int(self.radius * 0.95)
        self.canvas.create_oval(
            self.center_x - inner_radius,
            self.center_y - inner_radius,
            self.center_x + inner_radius,
            self.center_y + inner_radius,
            fill="", outline="#BDC3C7", width=1
        )

        # 画刻度线，使用更精美的设计
        for i in range(60):
            angle = math.radians(i * 6 - 90)
            is_hour = (i % 5 == 0)

            if is_hour:
                # 时刻度：更粗、更长、使用深色
                inner_length = int(self.radius * 0.18)
                outer_length = int(self.radius * 0.05)
                line_width = max(2, int(self.radius * 0.012))
                color = "#2C3E50"
            else:
                # 分刻度：细致、使用中等颜色
                inner_length = int(self.radius * 0.12)
                outer_length = int(self.radius * 0.03)
                line_width = max(1, int(self.radius * 0.005))
                color = "#7F8C8D"

            inner = self.radius - inner_length
            outer = self.radius - outer_length

            self.canvas.create_line(
                self.center_x + outer * math.cos(angle),
                self.center_y + outer * math.sin(angle),
                self.center_x + inner * math.cos(angle),
                self.center_y + inner * math.sin(angle),
                width=line_width,
                fill=color,
                capstyle=tk.ROUND
            )

        # 绘制优美的 12 小时数字（排除3和9点位置，避免被按钮遮挡）
        text_r = int(self.radius * 0.75)
        for hour in range(12):
            angle = math.radians(hour * 30 - 90)
            x = self.center_x + text_r * math.cos(angle)
            y = self.center_y + text_r * math.sin(angle)
            num = 12 if hour == 0 else hour

            # 跳过3点和9点位置，避免与按钮重叠
            if num == 3 or num == 9:
                continue

            # 为重要时间（12、6）使用不同样式
            if num in [12, 6]:
                font_color = "#E74C3C"  # 红色突出
                font_weight = "bold"
            else:
                font_color = "#2C3E50"  # 深蓝灰
                font_weight = "normal"

            # 创建数字文本，带有轻微阴影效果
            shadow_font = tkFont.Font(family="Arial", size=int(self.number_font.actual("size")), weight=font_weight)

            # 阴影文字
            self.canvas.create_text(
                x + 1, y + 1,
                text=str(num),
                font=shadow_font,
                fill="#BDC3C7",
                tags="dial_number_shadow"
            )

            # 主文字
            self.canvas.create_text(
                x, y,
                text=str(num),
                font=shadow_font,
                fill=font_color,
                tags="dial_number"
            )

        # 精美的中心装饰
        center_outer_size = max(8, int(self.radius * 0.025))
        center_inner_size = max(4, int(self.radius * 0.015))

        # 外层中心圆（金属质感）
        self.canvas.create_oval(
            self.center_x - center_outer_size, self.center_y - center_outer_size,
            self.center_x + center_outer_size, self.center_y + center_outer_size,
            fill="#34495E", outline="#2C3E50", width=2
        )

        # 内层中心圆（亮点）
        self.canvas.create_oval(
            self.center_x - center_inner_size, self.center_y - center_inner_size,
            self.center_x + center_inner_size, self.center_y + center_inner_size,
            fill="#ECF0F1", outline=""
        )

    def draw_transparency_controls(self):
        # 动态计算按钮尺寸和间距，随 radius 缩放
        button_size = self.clamp(int(self.radius * 0.08), 15, 45)  # 稍微增大
        spacing     = self.clamp(int(self.radius * 0.02),  8, 25)   # 增加间距
        x = self.center_x + self.radius + spacing

        up_y   = self.center_y - button_size - spacing
        down_y = self.center_y + spacing

        # 绘制美化的上箭头按钮（增加透明度）
        # 阴影效果
        self.canvas.create_polygon(
            x + 2,                up_y + button_size + 2,
            x + button_size + 2,  up_y + button_size + 2,
            x + button_size/2 + 2, up_y + 2,
            fill='#BDC3C7', outline='', tags="opacity_up_shadow"
        )
        # 主按钮
        self.canvas.create_polygon(
            x,                up_y + button_size,
            x + button_size,  up_y + button_size,
            x + button_size/2, up_y,
            fill='#3498DB', outline='#2980B9', width=2, tags="opacity_up"
        )
        # 高光效果
        self.canvas.create_polygon(
            x + button_size/4, up_y + button_size*0.75,
            x + button_size*0.75, up_y + button_size*0.75,
            x + button_size/2, up_y + button_size*0.25,
            fill='#5DADE2', outline='', tags="opacity_up_highlight"
        )

        # 绘制美化的下箭头按钮（降低透明度）
        # 阴影效果
        self.canvas.create_polygon(
            x + 2,                down_y + 2,
            x + button_size + 2,  down_y + 2,
            x + button_size/2 + 2, down_y + button_size + 2,
            fill='#BDC3C7', outline='', tags="opacity_down_shadow"
        )
        # 主按钮
        self.canvas.create_polygon(
            x,                down_y,
            x + button_size,  down_y,
            x + button_size/2, down_y + button_size,
            fill='#E67E22', outline='#D35400', width=2, tags="opacity_down"
        )
        # 高光效果
        self.canvas.create_polygon(
            x + button_size/4, down_y + button_size*0.25,
            x + button_size*0.75, down_y + button_size*0.25,
            x + button_size/2, down_y + button_size*0.75,
            fill='#F39C12', outline='', tags="opacity_down_highlight"
        )

        # 绑定事件（包括高光和阴影元素）
        for tag in ["opacity_up", "opacity_up_shadow", "opacity_up_highlight"]:
            self.canvas.tag_bind(tag, "<Button-1>", self.increase_opacity)
        for tag in ["opacity_down", "opacity_down_shadow", "opacity_down_highlight"]:
            self.canvas.tag_bind(tag, "<Button-1>", self.decrease_opacity)

        # 添加悬停效果
        self.setup_transparency_button_hover_effects()

    def setup_transparency_button_hover_effects(self):
        """为透明度按钮添加悬停效果"""
        def on_up_enter(event):
            self.canvas.itemconfig("opacity_up", fill="#2980B9")
        def on_up_leave(event):
            self.canvas.itemconfig("opacity_up", fill="#3498DB")
        def on_down_enter(event):
            self.canvas.itemconfig("opacity_down", fill="#D35400")
        def on_down_leave(event):
            self.canvas.itemconfig("opacity_down", fill="#E67E22")

        for tag in ["opacity_up", "opacity_up_shadow", "opacity_up_highlight"]:
            self.canvas.tag_bind(tag, "<Enter>", on_up_enter)
            self.canvas.tag_bind(tag, "<Leave>", on_up_leave)
        for tag in ["opacity_down", "opacity_down_shadow", "opacity_down_highlight"]:
            self.canvas.tag_bind(tag, "<Enter>", on_down_enter)
            self.canvas.tag_bind(tag, "<Leave>", on_down_leave)



    def increase_opacity(self, event):
        if self.opacity < 1.0:
            self.opacity = min(1.0, self.opacity + 0.1)
            self.root.attributes("-alpha", self.opacity)

    def decrease_opacity(self, event):
        if self.opacity > 0.1:
            self.opacity = max(0.05, self.opacity - 0.1)
            self.root.attributes("-alpha", self.opacity)

    def draw_hand(self, angle, length, width, color, shadow=True):
        x = self.center_x + length * math.cos(angle)
        y = self.center_y + length * math.sin(angle)

        if shadow:
            # 绘制指针阴影
            shadow_offset = max(1, int(width * 0.3))
            self.canvas.create_line(
                self.center_x + shadow_offset, self.center_y + shadow_offset,
                x + shadow_offset, y + shadow_offset,
                width=width, fill="#BDC3C7", tag="hand_shadow",
                capstyle=tk.ROUND
            )

        # 绘制主指针
        return self.canvas.create_line(
            self.center_x, self.center_y, x, y,
            width=width, fill=color, tag="hand",
            capstyle=tk.ROUND
        )

    def update_weather(self):
        def fetch():
            try:
                current_city = city_var.get()
                if current_city in city_mapping:
                    city_code = city_mapping[current_city]
                else:
                    city_code = ""
                if city_code:
                    info = get_weather_info_from_web(city_code)
                    self.weather_info = f"{current_city}: {info}"
                else:
                    self.weather_info = "心情晴好"
            except Exception as e:
                logging.error(f"更新天气信息出错: {e}")
                self.weather_info = "好心情"
        threading.Thread(target=fetch, daemon=True).start()
        if self.weather_after_id is not None:
            self.root.after_cancel(self.weather_after_id)
        self.weather_after_id = self.root.after(600000, self.update_weather)

    def update_weather_immediately(self):
        if self.weather_after_id is not None:
            self.root.after_cancel(self.weather_after_id)
        self.update_weather()

    def announce_time(self, hour, minute):
        # 统一通过TTS队列处理时间播报
        text = f"现在是北京时间{hour}点{minute}分"
        self.enqueue_announcement(text)

    def announce_reminder(self, hour, minute, content, mp3_file):
        def play_in_background():
            play_sound_mp3_blocking(mp3_file)
            text = f"现在是北京时间{hour}点{minute}分，索菲亚提醒您{content}"
            self.enqueue_announcement(text)
        threading.Thread(target=play_in_background, daemon=True).start()

    def update_clock(self):
        now = datetime.now()

        # 先计算日期与星期字符串
        date_str = now.strftime("%m-%d")
        weekday_map = {0: "星期一", 1: "星期二", 2: "星期三",
                       3: "星期四", 4: "星期五", 5: "星期六", 6: "星期日"}
        weekday_str = weekday_map[now.weekday()]

        # 计算时钟指针角度
        hour = now.hour % 12 + now.minute / 60.0
        minute = now.minute + now.second / 60.0
        second = now.second + now.microsecond / 1e6
        hour_angle = math.radians(hour * 30 - 90)
        minute_angle = math.radians(minute * 6 - 90)
        second_angle = math.radians(second * 6 - 90)

        # 更新已有的文本对象（包括阴影）
        date_text = f"{date_str} {weekday_str}"
        weather_text = self.weather_info

        # 更新文字
        self.canvas.itemconfig(self.date_id, text=date_text)
        self.canvas.itemconfig(self.brand_id, text="Sofia 2025")
        self.canvas.itemconfig(self.weather_id, text=weather_text)

        # 确保品牌文字的点击事件绑定
        self.canvas.tag_bind("brand", "<Button-1>", self.open_sofia_platform)
        self.canvas.tag_bind("brand", "<Enter>", lambda e: self.canvas.config(cursor="hand2"))
        self.canvas.tag_bind("brand", "<Leave>", lambda e: self.canvas.config(cursor=""))

        # 删除旧的指针（假设钟面部分用 tag "hand" 和 "hand_shadow" 标记）
        self.canvas.delete("hand")
        self.canvas.delete("hand_shadow")

        # 绘制时针、分针、秒针，长度和宽度基于半径比例，使用更优美的颜色
        hour_width = max(5, int(self.radius * 0.025))   # 时针宽度（略微增加）
        minute_width = max(3, int(self.radius * 0.018)) # 分针宽度
        second_width = max(1, int(self.radius * 0.008)) # 秒针宽度

        # 使用更优美的颜色方案
        self.draw_hand(hour_angle, self.radius * 0.5, hour_width, "#2C3E50")      # 时针：深蓝灰
        self.draw_hand(minute_angle, self.radius * 0.75, minute_width, "#34495E")  # 分针：中蓝灰
        self.draw_hand(second_angle, self.radius * 0.85, second_width, "#E74C3C", shadow=False)  # 秒针：红色，无阴影

        # 绘制秒针尾巴，长度也随半径缩放，添加阴影
        tail_length = max(12, int(self.radius * 0.1))  # 尾巴长度增加

        # 秒针尾巴阴影
        shadow_offset = 1
        self.canvas.create_line(
            self.center_x - tail_length * math.cos(second_angle) + shadow_offset,
            self.center_y - tail_length * math.sin(second_angle) + shadow_offset,
            self.center_x + shadow_offset,
            self.center_y + shadow_offset,
            width=second_width, fill="#BDC3C7", tag="hand_shadow"
        )

        # 秒针尾巴主体
        self.canvas.create_line(
            self.center_x - tail_length * math.cos(second_angle),
            self.center_y - tail_length * math.sin(second_angle),
            self.center_x,
            self.center_y,
            width=second_width, fill="#E74C3C", tag="hand"
        )

        # 以下处理其他功能（如报时、提醒、天气播报、新闻播报）：
        if self.chime_active:
            should_announce = False

            # 根据不同的报时模式判断是否需要播报
            if self.chime_mode == "quarter":  # 刻点报时 - 每15分钟
                should_announce = now.minute % 15 == 0 and now.second < 2
                if should_announce and self.last_announced != (now.hour, now.minute):
                    self.announce_time(now.hour, now.minute)
                    self.last_announced = (now.hour, now.minute)
                elif now.minute % 15 != 0:
                    self.last_announced = None

            elif self.chime_mode == "half":   # 半点报时 - 每30分钟
                should_announce = now.minute % 30 == 0 and now.second < 2
                if should_announce and self.last_announced != (now.hour, now.minute):
                    self.announce_time(now.hour, now.minute)
                    self.last_announced = (now.hour, now.minute)
                elif now.minute % 30 != 0:
                    self.last_announced = None

            elif self.chime_mode == "hour":   # 整点报时 - 每60分钟
                should_announce = now.minute == 0 and now.second < 2
                if should_announce and self.last_announced != (now.hour, now.minute):
                    self.announce_time(now.hour, now.minute)
                    self.last_announced = (now.hour, now.minute)
                elif now.minute != 0:
                    self.last_announced = None

            elif self.chime_mode == "custom": # 自定义时长
                # 统一使用总分钟数方式，避免各种边界情况
                total_minutes = now.hour * 60 + now.minute

                # 计算从今日0点开始的分钟数是否符合间隔
                should_announce = (total_minutes % self.custom_chime_interval == 0) and (now.second < 2)

                # 使用简单的时间字符串作为唯一标识
                current_time_key = f"{now.hour:02d}:{now.minute:02d}"

                if should_announce:
                    # 检查这个时间点是否已经报时过
                    last_chime = getattr(self, 'last_chime_time', '')

                    if last_chime != current_time_key:
                        self.announce_time(now.hour, now.minute)
                        self.last_chime_time = current_time_key
                else:
                    # 不在报时时间点时，清除标记以准备下次报时
                    if hasattr(self, 'last_chime_time'):
                        # 只有当时间已经过了当前标记的时间才清除，避免过早清除
                        last_chime = getattr(self, 'last_chime_time', '')
                        if last_chime and last_chime != current_time_key:
                            # 检查当前时间是否已经超过了上次报时时间
                            if last_chime < current_time_key or now.second >= 10:
                                self.last_chime_time = ''

        if self.reminder_active:
            current_minute = now.strftime("%H:%M")
            if self.current_reminder_minute != current_minute:
                self.last_reminder_announced = set()
                self.current_reminder_minute = current_minute
            for r_time, content, mp3_file in self.reminders:
                if r_time == current_minute and (r_time, content) not in self.last_reminder_announced:
                    h, m = map(int, r_time.split(":"))
                    self.announce_reminder(h, m, content, mp3_file)
                    self.last_reminder_announced.add((r_time, content))

        if self.weather_broadcast_active:
            if 6 <= now.hour <= 18 and now.minute == 0 and now.second < 2:
                if self.last_weather_broadcast_hour != now.hour:
                    self.broadcast_weather()
                    self.last_weather_broadcast_hour = now.hour

        current_total_minutes = now.hour * 60 + now.minute
        if self.news_broadcast_active:
            if now.hour < self.news_broadcast_start_time or now.hour >= self.news_broadcast_end_time:
                default_trigger = self.news_broadcast_start_time * 60 + self.news_broadcast_time_point
                if now.hour >= self.news_broadcast_end_time:
                    default_trigger += 24 * 60
                self.news_broadcast_next_trigger = default_trigger
            else:
                if current_total_minutes >= self.news_broadcast_next_trigger and now.second < 2:
                    threading.Thread(target=self.broadcast_news, daemon=True).start()
                    self.news_broadcast_next_trigger += self.news_broadcast_interval
                    if self.news_broadcast_next_trigger >= self.news_broadcast_end_time * 60:
                        self.news_broadcast_next_trigger = (self.news_broadcast_start_time * 60 +
                                                            self.news_broadcast_time_point +
                                                            24 * 60)

        self.canvas.tag_lower("control")
        self.root.after(200, self.update_clock)


    def broadcast_weather(self):
        current_city = city_var.get()
        if current_city in city_mapping:
            city_code = city_mapping[current_city]
            today_weather = get_weather_info_from_web(city_code)
            weekly_weather = get_weekly_weather_info(city_code)
            announcement = f"索菲亚为您播报{current_city}地区的天气预报：今日天气：{today_weather}；一周天气：{weekly_weather}。祝您一天好心情！"
            self.enqueue_announcement(announcement)
        else:
            self.enqueue_announcement("当前选择的城市没有配置对应的城市代码。")

def play_sound_mp3_blocking(mp3_file):
    if not os.path.isfile(mp3_file):
        return
    try:
        pygame.mixer.music.load(mp3_file)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
    except Exception as e:
        logging.error(f"播放音频出错: {e}")

class ConfigFileHandler(FileSystemEventHandler):
    def __init__(self, clock):
        self.clock = clock
    def on_modified(self, event):
        if not event.is_directory:
            filename = os.path.basename(event.src_path)
            if filename in ["config.ini", "reminders.ini"]:
                logging.info(f"检测到 {filename} 发生修改，自动刷新配置。")
                self.clock.root.after(0, self.clock.refresh_config, True)

def get_current_month():
    """
    返回当前月份标识，格式为 "YYYY-MM"，例如 "2025-04"
    """
    return datetime.now().strftime("%Y-%m")

def load_played_ids():
    """
    加载保存的播放记录，返回一个字典，格式为：
    {"month": "YYYY-MM", "ids": [id1, id2, ...]}
    如果文件不存在或者保存的月份标识不是当前月份，则返回空记录。
    """
    filename = "id.json"
    current_month = get_current_month()
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = {"month": current_month, "ids": []}
        # 如果保存的月份标识不是当前月份，则重置记录
        if data.get("month") != current_month:
            data = {"month": current_month, "ids": []}
    else:
        data = {"month": current_month, "ids": []}
    return data

def save_played_ids(data):
    """
    保存播放记录到 id.json 文件中。
    """
    filename = "id.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f)


if __name__ == "__main__":
    pygame.mixer.init()
    root = tk.Tk()
    city_var = tk.StringVar(root, value="金山")
    # 移除size_var，改用拖拽缩放
    # size_var = tk.StringVar(root, value="中")
    clock = SmoothClock(root)
    city_var.trace_add("write", lambda *args: clock.update_weather_immediately())
    # 移除size_var的事件绑定
    # size_var.trace_add("write", lambda *args: clock.on_resize())
    observer = Observer()
    event_handler = ConfigFileHandler(clock)
    observer.schedule(event_handler, path=".", recursive=False)
    observer.start()
    def on_closing():
        observer.stop()
        observer.join()
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
