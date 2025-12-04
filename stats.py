import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk, filedialog, messagebox
import platform
import datetime
import os
import json
import time
import psutil
from collections import deque
import sys
import io
import threading
import numpy as np
import socket
import subprocess
import ctypes
import sys

# === ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА ===
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    # Запускаем себя с правами администратора
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(sys.argv), None, 1
    )
    sys.exit()

# === ПИКСЕЛЬНЫЙ СТИЛЬ ===
COLORS = {
    "bg_dark": "#000000",
    "bg_card": "#0a0a0a",
    "bg_hover": "#1a1a1a",
    "border": "#333333",
    "text_primary": "#ffffff",
    "text_secondary": "#cccccc",
    "text_muted": "#888888",
    "cpu_color": "#ff5555",
    "gpu_color": "#aa55ff",
    "ram_color": "#55aaff",
    "disk_color": "#55ffaa",
    "net_color": "#ffaa55",
    "temp_cool": "#55aaff",
    "temp_warm": "#ffaa55",
    "temp_hot": "#ff5555",
    "success": "#00ff88",
    "warning": "#ffaa00",
    "danger": "#ff5555",
    "info": "#55aaff",
    "battery_full": "#00ff88",
    "battery_medium": "#ffaa00",
    "battery_low": "#ff5555",
    "fps_good": "#00ff88",
    "fps_medium": "#ffaa00",
    "fps_low": "#ff5555",
    "ping_good": "#00ff88",
    "ping_medium": "#ffaa00",
    "ping_bad": "#ff5555",
}

# === ШРИФТЫ ===
PIXEL_FONT = ("Consolas", 10)
PIXEL_FONT_BOLD = ("Consolas", 10, "bold")
PIXEL_FONT_TITLE = ("Consolas", 12, "bold")
PIXEL_FONT_SMALL = ("Consolas", 9)

# === Глобальный логгер ===
def safe_print(message):
    try:
        if 'log_text' in globals() and hasattr(log_text, 'insert'):
            log_text.insert("end", message + "\n", "log")
            log_text.see("end")
        else:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")
    except Exception as e:
        print(f"Ошибка safe_print: {str(e)}")

# === Перехват вывода ===
class TextRedirect(io.StringIO):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        self.buffer = ""

    def write(self, s):
        try:
            self.buffer += s
            if '\n' in self.buffer:
                lines = self.buffer.split('\n')
                for line in lines[:-1]:
                    if line.strip():
                        tag = "error" if any(keyword in line.lower() for keyword in ["error", "traceback", "fail", "critical"]) else "log"
                        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
                        self.text_widget.insert("end", f"[{timestamp}] {line}\n", tag)
                        self.text_widget.see("end")
                self.buffer = lines[-1]
        except Exception as e:
            print(f"Ошибка TextRedirect: {str(e)}")

    def flush(self):
        pass

# === GPU ИНФОРМАЦИЯ ===
def get_gpu_info():
    """Получение информации о видеокартах"""
    gpu_info = []
    
    # Пробуем через nvidia-smi для NVIDIA
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=name,temperature.gpu,utilization.gpu,memory.total,memory.used', '--format=csv,noheader,nounits'],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            for i, line in enumerate(lines):
                parts = line.split(', ')
                if len(parts) >= 5:
                    name = parts[0].strip()
                    temp = float(parts[1].strip())
                    load = float(parts[2].strip())
                    mem_total = float(parts[3].strip())
                    mem_used = float(parts[4].strip())
                    
                    gpu_data = {
                        'id': i,
                        'name': name,
                        'load': load,
                        'temperature': temp,
                        'memory_total': mem_total,
                        'memory_used': mem_used,
                        'memory_free': mem_total - mem_used,
                        'driver': 'NVIDIA',
                        'active': load > 5
                    }
                    
                    # Определение цвета для температуры
                    if temp > 85:
                        gpu_data['temp_color'] = COLORS['temp_hot']
                    elif temp > 75:
                        gpu_data['temp_color'] = COLORS['temp_warm']
                    else:
                        gpu_data['temp_color'] = COLORS['temp_cool']
                    
                    # Определение цвета для загрузки
                    if load > 90:
                        gpu_data['load_color'] = COLORS['danger']
                    elif load > 70:
                        gpu_data['load_color'] = COLORS['warning']
                    else:
                        gpu_data['load_color'] = COLORS['success']
                    
                    gpu_info.append(gpu_data)
            
            safe_print(f"✅ Обнаружено видеокарт NVIDIA: {len(gpu_info)}")
            return gpu_info
    except:
        pass
    
    # Пробуем через dxdiag для Windows
    try:
        import wmi
        w = wmi.WMI()
        gpu_devices = w.Win32_VideoController()
        
        for i, gpu in enumerate(gpu_devices):
            gpu_data = {
                'id': i,
                'name': gpu.Name,
                'load': 0,  # Недоступно через WMI
                'temperature': 0,  # Недоступно через WMI
                'memory_total': 0,
                'memory_used': 0,
                'memory_free': 0,
                'driver': gpu.DriverVersion if hasattr(gpu, 'DriverVersion') else 'Unknown',
                'active': True,
                'temp_color': COLORS['temp_cool'],
                'load_color': COLORS['success']
            }
            
            # Пытаемся получить память
            try:
                if hasattr(gpu, 'AdapterRAM'):
                    mem_bytes = int(gpu.AdapterRAM)
                    gpu_data['memory_total'] = mem_bytes / (1024 * 1024)  # MB
            except:
                pass
            
            gpu_info.append(gpu_data)
        
        safe_print(f"✅ Обнаружено видеокарт через WMI: {len(gpu_info)}")
        return gpu_info
        
    except Exception as e:
        safe_print(f"⚠️ Ошибка получения информации GPU: {str(e)}")
    
    return gpu_info

# === ФУНКЦИИ ДЛЯ ОВЕРЛЕЯ ===
def get_fps():
    """Получение FPS (пока заглушка)"""
    try:
        # Временная заглушка - всегда показывает 60 FPS
        fps = 60
        
        if fps > 100:
            color = COLORS['fps_good']
            status = "Отлично"
        elif fps > 60:
            color = COLORS['fps_medium']
            status = "Хорошо"
        elif fps > 30:
            color = COLORS['fps_low']
            status = "Средне"
        else:
            color = COLORS['danger']
            status = "Плохо"
        
        return {
            'value': fps,
            'color': color,
            'status': status
        }
    except Exception as e:
        safe_print(f"⚠️ Ошибка получения FPS: {str(e)}")
        return None

def get_ping():
    """Получение пинга"""
    try:
        # Пинг к Google DNS
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        
        start_time = time.time()
        try:
            sock.connect(('8.8.8.8', 53))
            ping_ms = (time.time() - start_time) * 1000
        except:
            ping_ms = 50  # Значение по умолчанию если не удалось
        
        sock.close()
        
        if ping_ms < 30:
            color = COLORS['ping_good']
            status = "Отлично"
        elif ping_ms < 60:
            color = COLORS['ping_medium']
            status = "Хорошо"
        elif ping_ms < 100:
            color = COLORS['ping_bad']
            status = "Средне"
        else:
            color = COLORS['danger']
            status = "Плохо"
        
        return {
            'value': int(ping_ms),
            'color': color,
            'status': status
        }
        
    except Exception as e:
        safe_print(f"⚠️ Ошибка получения пинга: {str(e)}")
        return None

# === БАТАРЕЯ ===
def get_battery_info():
    """Получение информации о батарее"""
    try:
        battery = psutil.sensors_battery()
        if battery:
            battery_info = {
                'percent': battery.percent,
                'plugged': battery.power_plugged,
                'time_left': battery.secsleft if hasattr(battery, 'secsleft') else None
            }
            
            # Определение цвета батареи
            if battery.percent > 70:
                battery_info['color'] = COLORS['battery_full']
            elif battery.percent > 30:
                battery_info['color'] = COLORS['battery_medium']
            else:
                battery_info['color'] = COLORS['battery_low']
                
            # Определение статуса
            if battery.power_plugged:
                battery_info['status'] = "Заряжается" if battery.percent < 100 else "Заряжена"
            else:
                battery_info['status'] = "Разряжается"
            
            return battery_info
    except Exception as e:
        safe_print(f"⚠️ Ошибка получения информации о батарее: {str(e)}")
    
    # Если батареи нет (стационарный ПК)
    return {
        'percent': 100,
        'plugged': True,
        'time_left': None,
        'color': COLORS['battery_full'],
        'status': 'Питание от сети'
    }

# === Функция перевода байтов ===
def get_size(bytes_value: float) -> str:
    try:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"
    except Exception as e:
        return f"Ошибка: {str(e)}"

# === НАСТРОЙКА ОКНА ===
root = tk.Tk()
root.title("█▄ SYSTEM TERMINAL v1.0 ██")
root.geometry("1200x800")
root.minsize(1000, 600)
root.configure(bg=COLORS['bg_dark'])

# === СТИЛЬ TTK ===
style = ttk.Style()
style.theme_use("clam")

# Конфигурация стилей для пиксельного дизайна
style.configure("Pixel.TFrame", background=COLORS['bg_card'], relief="flat", borderwidth=2)
style.configure("Pixel.TLabel", background=COLORS['bg_card'], foreground=COLORS['text_primary'], 
                font=PIXEL_FONT)
style.configure("Pixel.TButton", background=COLORS['bg_card'], foreground=COLORS['text_primary'],
                font=PIXEL_FONT, borderwidth=1, relief="raised")
style.map("Pixel.TButton",
          background=[('active', COLORS['bg_hover'])],
          foreground=[('active', COLORS['success'])])

# === ВЕРХНЯЯ ПАНЕЛЬ ===
header_frame = ttk.Frame(root, style="Pixel.TFrame")
header_frame.pack(fill="x", padx=5, pady=5)

# Заголовок в стиле терминала
title_label = tk.Label(header_frame, text="╔══════════════════════════════════════════════════════╗", 
                       bg=COLORS['bg_dark'], fg=COLORS['text_primary'], font=PIXEL_FONT)
title_label.pack()

title_label = tk.Label(header_frame, text="║                SYSTEM TERMINAL v1.0                  ║", 
                       bg=COLORS['bg_dark'], fg=COLORS['success'], font=PIXEL_FONT_TITLE)
title_label.pack()

title_label = tk.Label(header_frame, text="╚══════════════════════════════════════════════════════╝", 
                       bg=COLORS['bg_dark'], fg=COLORS['text_primary'], font=PIXEL_FONT)
title_label.pack()

# Кнопки управления
button_frame = ttk.Frame(header_frame, style="Pixel.TFrame")
button_frame.pack(fill="x", pady=10)

def save_report():
    """Сохранение отчета в файл"""
    file_path = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[
            ("Текстовый файл", "*.txt"),
            ("JSON файл", "*.json"),
            ("Все файлы", "*.*")
        ],
        title="Сохранить отчет о системе"
    )
    
    if not file_path:
        return
    
    try:
        report_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "system": {
                "os": platform.system(),
                "version": platform.version(),
                "architecture": platform.architecture()[0],
                "hostname": platform.node(),
                "processor": platform.processor(),
                "python_version": platform.python_version()
            },
            "cpu": {
                "cores_physical": psutil.cpu_count(logical=False),
                "cores_logical": psutil.cpu_count(logical=True),
                "frequency": psutil.cpu_freq().current if psutil.cpu_freq() else 0
            },
            "memory": {
                "total": psutil.virtual_memory().total,
                "used": psutil.virtual_memory().used,
                "percent": psutil.virtual_memory().percent
            },
            "gpu": [],
            "disks": [],
            "network": {}
        }
        
        # GPU информация
        gpus = get_gpu_info()
        for gpu in gpus:
            report_data["gpu"].append({
                "name": gpu.get('name', 'Unknown'),
                "load": gpu.get('load', 0),
                "temperature": gpu.get('temperature', 0),
                "memory_total": gpu.get('memory_total', 0),
                "memory_used": gpu.get('memory_used', 0)
            })
        
        # Диски
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                report_data["disks"].append({
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "total": usage.total,
                    "used": usage.used,
                    "percent": usage.percent
                })
            except:
                pass
        
        with open(file_path, 'w', encoding='utf-8') as f:
            if file_path.endswith('.json'):
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            else:
                f.write("╔══════════════════════════════════════════════════════╗\n")
                f.write("║              SYSTEM DIAGNOSTIC REPORT               ║\n")
                f.write("╚══════════════════════════════════════════════════════╝\n\n")
                f.write(f"Generated: {datetime.datetime.now()}\n\n")
                
                f.write("=== SYSTEM INFORMATION ===\n")
                f.write(f"OS: {platform.system()} {platform.version()}\n")
                f.write(f"Architecture: {platform.architecture()[0]}\n")
                f.write(f"Hostname: {platform.node()}\n")
                f.write(f"Processor: {platform.processor()}\n")
                f.write(f"Python: {platform.python_version()}\n\n")
                
                f.write("=== CPU INFORMATION ===\n")
                f.write(f"Cores: {psutil.cpu_count(logical=False)} physical, {psutil.cpu_count(logical=True)} logical\n")
                f.write(f"Frequency: {psutil.cpu_freq().current if psutil.cpu_freq() else 'N/A'} MHz\n\n")
                
                f.write("=== MEMORY INFORMATION ===\n")
                vm = psutil.virtual_memory()
                f.write(f"Total: {get_size(vm.total)}\n")
                f.write(f"Used: {get_size(vm.used)} ({vm.percent:.1f}%)\n\n")
                
                if gpus:
                    f.write("=== GPU INFORMATION ===\n")
                    for gpu in gpus:
                        f.write(f"{gpu.get('name', 'Unknown')}:\n")
                        f.write(f"  Load: {gpu.get('load', 0):.1f}%\n")
                        f.write(f"  Temperature: {gpu.get('temperature', 0):.1f}°C\n")
                        if gpu.get('memory_total', 0) > 0:
                            f.write(f"  Memory: {gpu.get('memory_used', 0):.1f}/{gpu.get('memory_total', 0):.1f} MB\n\n")
        
        safe_print(f"✅ Отчет сохранен: {file_path}")
        
    except Exception as e:
        safe_print(f"❌ Ошибка сохранения отчета: {str(e)}")

# Создание кнопок в стиле терминала
def create_pixel_button(parent, text, command, color=COLORS['text_primary']):
    btn = tk.Label(parent, text=f"[ {text} ]", bg=COLORS['bg_card'], fg=color, 
                   font=PIXEL_FONT_BOLD, cursor="hand2", relief="raised", bd=1)
    btn.bind("<Button-1>", lambda e: command())
    btn.bind("<Enter>", lambda e: btn.config(bg=COLORS['bg_hover']))
    btn.bind("<Leave>", lambda e: btn.config(bg=COLORS['bg_card']))
    return btn

btn_refresh = create_pixel_button(button_frame, "🔄 ОБНОВИТЬ", lambda: refresh_all(), COLORS['success'])
btn_refresh.pack(side="left", padx=5)

btn_save = create_pixel_button(button_frame, "💾 СОХРАНИТЬ", save_report, COLORS['info'])
btn_save.pack(side="left", padx=5)

btn_exit = create_pixel_button(button_frame, "⏻ ВЫХОД", root.quit, COLORS['danger'])
btn_exit.pack(side="right", padx=5)

# === ВКЛАДКИ ===
notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, padx=5, pady=5)

# Настройка стиля вкладок в пиксельном стиле
style.configure("Pixel.TNotebook", background=COLORS['bg_dark'], borderwidth=0)
style.configure("Pixel.TNotebook.Tab", 
                background=COLORS['bg_card'],
                foreground=COLORS['text_secondary'],
                padding=(15, 5),
                font=PIXEL_FONT)
style.map("Pixel.TNotebook.Tab",
          background=[("selected", COLORS['bg_hover'])],
          foreground=[("selected", COLORS['text_primary'])])

# === ВКЛАДКА 1: СИСТЕМНЫЙ МОНИТОР ===
monitor_frame = tk.Frame(notebook, bg=COLORS['bg_dark'])
notebook.add(monitor_frame, text="📟 МОНИТОР")

# Сетка для карточек
monitor_grid = tk.Frame(monitor_frame, bg=COLORS['bg_dark'])
monitor_grid.pack(fill="both", expand=True, padx=10, pady=10)

def create_pixel_card(parent, title, row, column, colspan=1, color=COLORS['text_primary']):
    """Создание карточки в пиксельном стиле"""
    card = tk.Frame(parent, bg=COLORS['bg_card'], relief="sunken", bd=1)
    card.grid(row=row, column=column, columnspan=colspan, sticky="nsew", padx=5, pady=5)
    
    # Заголовок карточки
    title_frame = tk.Frame(card, bg=COLORS['bg_hover'])
    title_frame.pack(fill="x", padx=1, pady=1)
    
    tk.Label(title_frame, text=f"▌ {title}", bg=COLORS['bg_hover'], fg=color,
             font=PIXEL_FONT_BOLD, anchor="w").pack(side="left", padx=5)
    
    # Контент
    content_frame = tk.Frame(card, bg=COLORS['bg_card'])
    content_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    return content_frame

# Настройка grid
for i in range(3):
    monitor_grid.columnconfigure(i, weight=1)
for i in range(3):
    monitor_grid.rowconfigure(i, weight=1)

# Карточка: Система
sys_card = create_pixel_card(monitor_grid, "⚙️ СИСТЕМА", 0, 0, color=COLORS['text_primary'])
sys_labels = {}

# Карточка: Процессор
cpu_card = create_pixel_card(monitor_grid, "⚡ ЦП", 0, 1, color=COLORS['cpu_color'])
cpu_labels = {}

# Карточка: Память
ram_card = create_pixel_card(monitor_grid, "🧠 ОЗУ", 0, 2, color=COLORS['ram_color'])
ram_labels = {}

# Карточка: Диски
disk_card = create_pixel_card(monitor_grid, "💾 ДИСКИ", 1, 0, color=COLORS['disk_color'])

# Карточка: Видеокарты
gpu_card = create_pixel_card(monitor_grid, "🎮 ВИДЕОКАРТЫ", 1, 1, color=COLORS['gpu_color'])

# Карточка: Сеть
net_card = create_pixel_card(monitor_grid, "🌐 СЕТЬ", 1, 2, color=COLORS['net_color'])

# Карточка: Батарея
battery_card = create_pixel_card(monitor_grid, "🔋 БАТАРЕЯ", 2, 0, color=COLORS['battery_full'])

# Карточка: Температуры
temp_card = create_pixel_card(monitor_grid, "🌡️ ТЕМПЕРАТУРЫ", 2, 1, color=COLORS['temp_hot'])

# Карточка: FPS/Пинг
fps_card = create_pixel_card(monitor_grid, "📹 FPS/ПИНГ", 2, 2, color=COLORS['fps_good'])

# === ВКЛАДКА 2: ГРАФИКИ ===
graphs_frame = tk.Frame(notebook, bg=COLORS['bg_dark'])
notebook.add(graphs_frame, text="📈 ГРАФИКИ")

# Контейнер для графиков
graphs_container = tk.Frame(graphs_frame, bg=COLORS['bg_dark'])
graphs_container.pack(fill="both", expand=True, padx=10, pady=10)

# Графики в пиксельном стиле
graph_titles = [
    ("⚡ CPU ЗАГРУЗКА", COLORS['cpu_color']),
    ("🧠 RAM ИСПОЛЬЗОВАНИЕ", COLORS['ram_color']),
    ("🎮 GPU ЗАГРУЗКА", COLORS['gpu_color']),
    ("🌐 СЕТЕВАЯ АКТИВНОСТЬ", COLORS['net_color'])
]

graph_canvases = []
for i, (title, color) in enumerate(graph_titles):
    frame = tk.Frame(graphs_container, bg=COLORS['bg_card'], relief="sunken", bd=1)
    frame.pack(fill="both", expand=True if i == len(graph_titles)-1 else False, pady=(0, 10))
    
    # Заголовок графика
    title_label = tk.Label(frame, text=f"▌ {title}", bg=COLORS['bg_hover'], fg=color,
                          font=PIXEL_FONT_BOLD, anchor="w")
    title_label.pack(fill="x", padx=1, pady=1)
    
    # Холст для графика
    canvas = tk.Canvas(frame, bg=COLORS['bg_card'], height=120, highlightthickness=0)
    canvas.pack(fill="both", expand=True, padx=10, pady=10)
    graph_canvases.append(canvas)

# === ВКЛАДКА 3: ПРОЦЕССЫ ===
processes_frame = tk.Frame(notebook, bg=COLORS['bg_dark'])
notebook.add(processes_frame, text="🔍 ПРОЦЕССЫ")

# Таблица процессов в пиксельном стиле
process_tree_frame = tk.Frame(processes_frame, bg=COLORS['bg_dark'])
process_tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

# Используем Text widget вместо Treeview для пиксельного стиля
process_text = tk.Text(process_tree_frame, bg=COLORS['bg_card'], fg=COLORS['text_primary'],
                      font=PIXEL_FONT_SMALL, wrap="none", insertbackground=COLORS['success'],
                      height=25, relief="sunken", bd=1)
process_text.pack(side="left", fill="both", expand=True)

# Полоса прокрутки
scrollbar = tk.Scrollbar(process_tree_frame, bg=COLORS['bg_card'], 
                        troughcolor=COLORS['bg_dark'], command=process_text.yview)
scrollbar.pack(side="right", fill="y")
process_text.config(yscrollcommand=scrollbar.set)

# === ВКЛАДКА 4: ЛОГИ ===
logs_frame = tk.Frame(notebook, bg=COLORS['bg_dark'])
notebook.add(logs_frame, text="📋 ЛОГИ")

log_text = tk.Text(logs_frame, bg=COLORS['bg_card'], fg=COLORS['text_primary'],
                   font=PIXEL_FONT_SMALL, wrap="word", insertbackground=COLORS['success'],
                   relief="sunken", bd=1)
log_text.pack(fill="both", expand=True, padx=10, pady=10)

# Настройка тегов для логов
log_text.tag_config("log", foreground=COLORS['text_muted'])
log_text.tag_config("info", foreground=COLORS['info'])
log_text.tag_config("success", foreground=COLORS['success'])
log_text.tag_config("warning", foreground=COLORS['warning'])
log_text.tag_config("error", foreground=COLORS['danger'])

# Перенаправление вывода
sys.stdout = TextRedirect(log_text)
sys.stderr = TextRedirect(log_text)

# === ДАННЫЕ ДЛЯ ГРАФИКОВ ===
MAX_POINTS = 150
cpu_data = deque([0] * MAX_POINTS, maxlen=MAX_POINTS)
ram_data = deque([0] * MAX_POINTS, maxlen=MAX_POINTS)
gpu_data = deque([0] * MAX_POINTS, maxlen=MAX_POINTS)
net_down_data = deque([0] * MAX_POINTS, maxlen=MAX_POINTS)
net_up_data = deque([0] * MAX_POINTS, maxlen=MAX_POINTS)
net_last = psutil.net_io_counters()

# === ФУНКЦИИ ОБНОВЛЕНИЯ ===
def update_system_info():
    """Обновление системной информации"""
    try:
        # Системная информация
        sys_info = {
            "ОС": f"{platform.system()} {platform.release()}",
            "Версия": platform.version(),
            "Архитектура": platform.architecture()[0],
            "Имя ПК": platform.node(),
            "Время загрузки": datetime.datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M:%S'),
            "Время работы": str(datetime.timedelta(seconds=int(time.time() - psutil.boot_time()))),
            "Python": platform.python_version()
        }
        
        # Процессор
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_info = {
            "Модель": platform.processor() or "Неизвестно",
            "Ядра/Потоки": f"{psutil.cpu_count(logical=False)}/{psutil.cpu_count(logical=True)}",
            "Загрузка": f"{cpu_percent:.1f}%",
            "Частота": f"{psutil.cpu_freq().current:.0f} МГц" if psutil.cpu_freq() else "N/A"
        }
        
        # Память
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        ram_info = {
            "Всего": get_size(vm.total),
            "Использовано": f"{get_size(vm.used)} ({vm.percent:.1f}%)",
            "Доступно": get_size(vm.available),
            "SWAP": f"{get_size(swap.used)}/{get_size(swap.total)}" if swap.total > 0 else "Отключен"
        }
        
        # Диски
        disk_info = ""
        try:
            for part in psutil.disk_partitions():
                if part.fstype and 'cdrom' not in part.opts:
                    try:
                        usage = psutil.disk_usage(part.mountpoint)
                        usage_percent = usage.percent
                        disk_info += f"{part.device}: {get_size(usage.used)}/{get_size(usage.total)} ({usage_percent:.1f}%)\n"
                    except:
                        disk_info += f"{part.device}: недоступно\n"
        except Exception as e:
            disk_info = f"Ошибка: {str(e)}"
        
        # Сеть
        net_io = psutil.net_io_counters()
        net_info = {
            "Отправлено": get_size(net_io.bytes_sent),
            "Получено": get_size(net_io.bytes_recv),
            "Пакеты": f"{net_io.packets_sent}/{net_io.packets_recv}",
            "Соединения": len(psutil.net_connections())
        }
        
        # ВИДЕОКАРТЫ
        gpus = get_gpu_info()
        gpu_text = ""
        
        if gpus:
            for gpu in gpus:
                active_indicator = " ⭐ АКТИВНА" if gpu.get('active', False) else ""
                gpu_name = gpu.get('name', 'Unknown GPU')
                gpu_load = gpu.get('load', 0)
                gpu_temp = gpu.get('temperature', 0)
                gpu_mem_used = gpu.get('memory_used', 0)
                gpu_mem_total = gpu.get('memory_total', 0)
                
                gpu_text += f"{gpu_name[:25]}{active_indicator}\n"
                gpu_text += f"  Загрузка: {gpu_load:.1f}%\n"
                if gpu_temp > 0:
                    gpu_text += f"  Температура: {gpu_temp:.1f}°C\n"
                if gpu_mem_total > 0:
                    gpu_text += f"  Память: {gpu_mem_used:.0f}/{gpu_mem_total:.0f} MB\n"
                gpu_text += "\n"
        else:
            gpu_text = "Видеокарты не обнаружены"
        
        # Батарея
        battery = get_battery_info()
        battery_text = ""
        if battery:
            battery_text += f"Заряд: {battery['percent']}%\n"
            battery_text += f"Статус: {battery['status']}\n"
            if battery['time_left'] and battery['time_left'] > 0:
                if battery['time_left'] != 4294967295:  # Не POWER_TIME_UNLIMITED
                    hours = battery['time_left'] // 3600
                    minutes = (battery['time_left'] % 3600) // 60
                    battery_text += f"Осталось: {hours}ч {minutes}м\n"
        else:
            battery_text = "Батарея не обнаружена"
        
        # Температуры
        temp_text = ""
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    if entries:
                        for entry in entries:
                            if hasattr(entry, 'current') and entry.current:
                                temp_text += f"{name} {entry.label or ''}: {entry.current:.1f}°C\n"
            else:
                temp_text = "Датчики температуры не найдены\n"
                temp_text += "Для Windows используйте OpenHardwareMonitor"
        except AttributeError:
            temp_text = "Датчики температуры не доступны\n"
            temp_text += "В Windows используйте OpenHardwareMonitor"
        except Exception as e:
            temp_text = f"Ошибка: {str(e)}"
        
        # FPS и Пинг
        fps_ping_text = ""
        
        fps_data = get_fps()
        if fps_data:
            fps_ping_text += f"FPS: {fps_data['value']} ({fps_data['status']})\n"
        else:
            fps_ping_text += "FPS: не доступен\n"
        
        ping_data = get_ping()
        if ping_data:
            fps_ping_text += f"Пинг: {ping_data['value']}мс ({ping_data['status']})\n"
        else:
            fps_ping_text += "Пинг: не доступен\n"
        
        # Обновление интерфейса
        update_pixel_card(sys_card, sys_info, sys_labels, COLORS['text_primary'])
        update_pixel_card(cpu_card, cpu_info, cpu_labels, COLORS['cpu_color'])
        update_pixel_card(ram_card, ram_info, ram_labels, COLORS['ram_color'])
        update_card_text(disk_card, disk_info, COLORS['disk_color'])
        update_card_text(gpu_card, gpu_text, COLORS['gpu_color'])
        update_card_text(net_card, format_dict_to_text(net_info), COLORS['net_color'])
        update_card_text(battery_card, battery_text, COLORS['battery_full'])
        update_card_text(temp_card, temp_text, COLORS['temp_hot'])
        update_card_text(fps_card, fps_ping_text, COLORS['fps_good'])
        
    except Exception as e:
        safe_print(f"❌ Ошибка обновления системной информации: {str(e)}")

def update_pixel_card(card, data_dict, labels_dict, color):
    """Обновление содержимого карточки в пиксельном стиле"""
    # Очистка предыдущих данных
    for widget in card.winfo_children():
        widget.destroy()
    
    # Добавление новых данных
    for key, value in data_dict.items():
        frame = tk.Frame(card, bg=COLORS['bg_card'])
        frame.pack(fill="x", pady=1)
        
        key_label = tk.Label(frame, text=f"{key}:", bg=COLORS['bg_card'], 
                           fg=COLORS['text_secondary'], font=PIXEL_FONT_SMALL, anchor="w", width=15)
        key_label.pack(side="left")
        
        value_label = tk.Label(frame, text=str(value), bg=COLORS['bg_card'], 
                             fg=color, font=PIXEL_FONT_SMALL, anchor="w")
        value_label.pack(side="left")
        
        labels_dict[key] = (key_label, value_label)

def update_card_text(card, text, color):
    """Обновление текста в карточке"""
    # Очистка предыдущих данных
    for widget in card.winfo_children():
        widget.destroy()
    
    # Добавление нового текста
    for line in text.strip().split('\n'):
        if line.strip():  # Пропускаем пустые строки
            label = tk.Label(card, text=line, bg=COLORS['bg_card'], 
                           fg=color, font=PIXEL_FONT_SMALL, anchor="w", justify="left")
            label.pack(anchor="w", pady=0)

def format_dict_to_text(data_dict):
    """Форматирование словаря в текст"""
    text = ""
    for key, value in data_dict.items():
        text += f"{key}: {value}\n"
    return text

def update_processes():
    """Обновление списка процессов"""
    try:
        process_text.config(state="normal")
        process_text.delete("1.0", "end")
        
        # Заголовок таблицы
        header = "PID       ПРОЦЕСС                      ПОЛЬЗОВАТЕЛЬ     CPU%     RAM(MB)     СОСТОЯНИЕ\n"
        process_text.insert("end", header, "header")
        process_text.insert("end", "─" * 80 + "\n")
        
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status']):
            try:
                info = proc.info
                processes.append({
                    'pid': info['pid'],
                    'name': info['name'][:25] if info['name'] else 'N/A',
                    'user': info['username'][:12] if info['username'] else 'SYSTEM',
                    'cpu': info['cpu_percent'] or 0.0,
                    'ram': proc.memory_info().rss / 1024 / 1024 if hasattr(proc, 'memory_info') else 0,
                    'status': info['status'] or 'unknown'
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Сортировка по CPU
        processes.sort(key=lambda x: x['cpu'], reverse=True)
        
        # Добавление в текстовое поле
        for proc in processes[:40]:
            cpu_percent = proc['cpu']
            if cpu_percent > 70:
                cpu_color = COLORS['danger']
            elif cpu_percent > 30:
                cpu_color = COLORS['warning']
            else:
                cpu_color = COLORS['success']
            
            ram_mb = proc['ram']
            if ram_mb > 500:
                ram_color = COLORS['danger']
            elif ram_mb > 100:
                ram_color = COLORS['warning']
            else:
                ram_color = COLORS['success']
            
            line = f"{proc['pid']:<8} {proc['name']:<28} {proc['user']:<16} "
            
            process_text.insert("end", line)
            process_text.insert("end", f"{cpu_percent:>6.1f}", "cpu_color")
            process_text.insert("end", "     ")
            process_text.insert("end", f"{ram_mb:>8.1f}", "ram_color")
            process_text.insert("end", f"     {proc['status']}\n")
            
            # Создаем теги с разными цветами для каждой строки
            process_text.tag_config("cpu_color", foreground=cpu_color)
            process_text.tag_config("ram_color", foreground=ram_color)
        
        process_text.tag_config("header", foreground=COLORS['text_primary'], font=PIXEL_FONT_BOLD)
        process_text.config(state="disabled")
        
    except Exception as e:
        safe_print(f"❌ Ошибка обновления процессов: {str(e)}")

def update_graphs():
    """Обновление графиков в пиксельном стиле"""
    try:
        global net_last
        
        # Получение данных
        cpu_percent = psutil.cpu_percent(interval=None)
        ram_percent = psutil.virtual_memory().percent
        
        # GPU данные
        gpu_percent = 0
        gpus = get_gpu_info()
        if gpus:
            gpu_percent = sum(gpu.get('load', 0) for gpu in gpus) / max(len(gpus), 1)
        
        # Сетевые данные
        net_current = psutil.net_io_counters()
        down_speed = (net_current.bytes_recv - net_last.bytes_recv) / 1024
        up_speed = (net_current.bytes_sent - net_last.bytes_sent) / 1024
        net_last = net_current
        
        # Добавление данных
        cpu_data.append(cpu_percent)
        ram_data.append(ram_percent)
        gpu_data.append(gpu_percent)
        net_down_data.append(min(down_speed, 10000))
        net_up_data.append(min(up_speed, 10000))
        
        # Отрисовка графиков
        all_graphs = [cpu_data, ram_data, gpu_data]
        colors = [COLORS['cpu_color'], COLORS['ram_color'], COLORS['gpu_color']]
        titles = ["CPU", "RAM", "GPU"]
        
        for i in range(3):
            draw_pixel_graph(graph_canvases[i], all_graphs[i], colors[i], titles[i], "%")
        
        # График сети
        draw_network_graph(graph_canvases[3], net_down_data, net_up_data)
        
    except Exception as e:
        safe_print(f"❌ Ошибка обновления графиков: {str(e)}")
    
    root.after(1000, update_graphs)

def draw_pixel_graph(canvas, data, color, title, unit):
    """Отрисовка графика в пиксельном стиле"""
    canvas.delete("all")
    
    w = canvas.winfo_width()
    h = canvas.winfo_height()
    
    if w < 10 or h < 10:
        return
    
    # Фон
    canvas.create_rectangle(0, 0, w, h, fill=COLORS['bg_card'], outline="")
    
    # Сетка
    for i in range(0, 101, 25):
        y = h - 20 - (i / 100) * (h - 40)
        canvas.create_line(30, y, w - 10, y, fill=COLORS['border'], width=1)
    
    # График
    if len(data) > 1:
        points = []
        for i, value in enumerate(data):
            x = 30 + (i / len(data)) * (w - 40)
            y = h - 20 - (value / 100) * (h - 40) if value <= 100 else h - 60
            points.extend([x, y])
        
        if len(points) >= 4:
            canvas.create_line(points, fill=color, width=3, smooth=False)
    
    # Текущее значение
    last_value = data[-1] if data else 0
    canvas.create_text(w - 10, 10, text=f"{last_value:.0f}{unit}", anchor="ne",
                      fill=color, font=PIXEL_FONT_BOLD)
    
    # Заголовок
    canvas.create_text(10, 10, text=title, anchor="nw",
                      fill=COLORS['text_primary'], font=PIXEL_FONT)

def draw_network_graph(canvas, down_data, up_data):
    """Отрисовка сетевого графика"""
    canvas.delete("all")
    
    w = canvas.winfo_width()
    h = canvas.winfo_height()
    
    if w < 10 or h < 10:
        return
    
    # Фон
    canvas.create_rectangle(0, 0, w, h, fill=COLORS['bg_card'], outline="")
    
    # Максимальное значение
    max_val = max(max(down_data or [0]), max(up_data or [0]), 1)
    
    # Графики
    if len(down_data) > 1 and len(up_data) > 1:
        points_down = []
        for i, value in enumerate(down_data):
            x = 30 + (i / len(down_data)) * (w - 40)
            y = h - 20 - (value / max_val) * (h - 40) if max_val > 0 else h - 20
            points_down.extend([x, y])
        
        if len(points_down) >= 4:
            canvas.create_line(points_down, fill=COLORS['info'], width=2, smooth=False)
        
        points_up = []
        for i, value in enumerate(up_data):
            x = 30 + (i / len(up_data)) * (w - 40)
            y = h - 20 - (value / max_val) * (h - 40) if max_val > 0 else h - 20
            points_up.extend([x, y])
        
        if len(points_up) >= 4:
            canvas.create_line(points_up, fill=COLORS['net_color'], width=2, smooth=False)
    
    # Легенда
    last_down = down_data[-1] if down_data else 0
    last_up = up_data[-1] if up_data else 0
    canvas.create_text(w - 10, 10, text=f"⬇{last_down:.0f} ⬆{last_up:.0f}", anchor="ne",
                      fill=COLORS['text_primary'], font=PIXEL_FONT_BOLD)
    
    # Заголовок
    canvas.create_text(10, 10, text="СЕТЬ", anchor="nw",
                      fill=COLORS['net_color'], font=PIXEL_FONT)

def refresh_all():
    """Полное обновление всех данных"""
    safe_print("█▄ ЗАПУСК ПОЛНОГО ОБНОВЛЕНИЯ ДАННЫХ...")
    
    threading.Thread(target=update_system_info, daemon=True).start()
    threading.Thread(target=update_processes, daemon=True).start()
    
    safe_print("✅ ОБНОВЛЕНИЕ ДАННЫХ ЗАПУЩЕНО")

# === ЗАПУСК ПРИЛОЖЕНИЯ ===
safe_print("╔══════════════════════════════════════════════════════╗")
safe_print("║          SYSTEM TERMINAL v1.0 ЗАПУСКАЕТСЯ           ║")
safe_print("╚══════════════════════════════════════════════════════╝")
safe_print(f"ОС: {platform.system()} {platform.release()}")
safe_print(f"Python: {platform.python_version()}")
safe_print(f"Права администратора: {'✅ ЕСТЬ' if is_admin() else '❌ НЕТ'}")
safe_print("=" * 60)

# Первоначальная загрузка данных
refresh_all()

# Запуск графиков
root.after(1000, update_graphs)

# Информация о горячих клавишах
safe_print("█▄ ГОРЯЧИЕ КЛАВИШИ:")
safe_print("  F5 - Обновить все данные")
safe_print("  Ctrl+S - Сохранить отчет")
safe_print("  Ctrl+Q - Выйти")

# Привязка горячих клавиш
root.bind("<F5>", lambda e: refresh_all())
root.bind("<Control-s>", lambda e: save_report())
root.bind("<Control-q>", lambda e: root.quit())

# Запуск основного цикла
safe_print("✅ ПРИЛОЖЕНИЕ ГОТОВО К РАБОТЕ!")

# Скрываем консольное окно если оно есть
try:
    import ctypes
    # Получаем handle консольного окна
    kernel32 = ctypes.WinDLL('kernel32')
    console_window = kernel32.GetConsoleWindow()
    if console_window:
        # Скрываем консольное окно
        user32 = ctypes.WinDLL('user32')
        user32.ShowWindow(console_window, 0)
except:
    pass

try:
    root.mainloop()
except KeyboardInterrupt:
    safe_print("🛑 ПРИЛОЖЕНИЕ ОСТАНОВЛЕНО ПОЛЬЗОВАТЕЛЕМ")
except Exception as e:
    safe_print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {str(e)}")
