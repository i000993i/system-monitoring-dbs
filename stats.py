import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk, filedialog
import platform
import psutil
import datetime
import os
from collections import deque
import sys
import io
import json
import time

# === Глобальный логгер ===
def safe_print(message):
    try:
        if 'log_text' in globals() and 'insert' in dir(log_text):
            log_text.insert("end", message + "\n", "log")
            log_text.see("end")
        else:
            print(message)
    except:
        print(message)

# === Перехват вывода ===
class TextRedirect(io.StringIO):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def write(self, s):
        self.text_widget.insert("end", s, "error" if "Traceback" in s or "Error" in s else "log")
        self.text_widget.see("end")

    def flush(self):
        pass

# === WMI (только Windows) ===
wmi_available = False
try:
    import wmi
    c = wmi.WMI()
    wmi_available = True
except Exception as e:
    safe_print(f"⚠️ WMI недоступен: {e}")

# === Функция перевода байтов ===
def get_size(bytes_value: float) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"

# === Настройка окна ===
root = tk.Tk()
root.title("📊 Мониторинг ПК + Инвентаризация")
root.geometry("1000x700")
root.minsize(850, 550)
root.configure(bg="#0a0a0a")

# === Верхняя панель вкладок ===
notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, padx=8, pady=8)

# === Шрифты ===
title_font = tkfont.Font(family="Consolas", size=12, weight="bold")
info_font = tkfont.Font(family="Consolas", size=9)
mono_font = tkfont.Font(family="Consolas", size=9)

# === Стиль ===
style = ttk.Style()
style.theme_use("clam")
style.configure("TNotebook", background="#0a0a0a", foreground="white")
style.configure("TNotebook.Tab", background="#1e1e1e", foreground="#00ffaa", padding=(12, 6))
style.map("TNotebook.Tab",
          background=[("selected", "#005f5f")],
          foreground=[("selected", "#00ffff")])

# === Цветовые теги ===
def add_tags(text_widget):
    text_widget.tag_config("good", foreground="#00ff88")
    text_widget.tag_config("warn", foreground="#ffaa00")
    text_widget.tag_config("crit", foreground="#ff5555")
    text_widget.tag_config("header", foreground="#00aaff", font=("Consolas", 12, "bold"))
    text_widget.tag_config("high", foreground="#ff3333")
    text_widget.tag_config("med", foreground="#ffcc00")
    text_widget.tag_config("low", foreground="#00ccff")
    text_widget.tag_config("log", foreground="#cccccc")

# === Вкладки ===
info_frame = tk.Frame(notebook, bg="#0a0a0a")
notebook.add(info_frame, text="🖥️ Инфо")
tk.Label(info_frame, text="ПОЛНАЯ ИНВЕНТАРИЗАЦИЯ СИСТЕМЫ", font=title_font, fg="#00aaff", bg="#0a0a0a").pack(pady=8)
info_text = tk.Text(info_frame, font=info_font, fg="#00ff88", bg="#111", insertbackground="green", wrap="word", relief="flat", highlightthickness=0)
scroll_info = tk.Scrollbar(info_frame, command=info_text.yview)
info_text.pack(side="left", fill="both", expand=True, padx=10, pady=10)
scroll_info.pack(side="right", fill="y")
info_text.config(yscrollcommand=scroll_info.set)
add_tags(info_text)

proc_frame = tk.Frame(notebook, bg="#0a0a0a")
notebook.add(proc_frame, text="🧩 Процессы")
tk.Label(proc_frame, text="АКТИВНЫЕ ПРОЦЕССЫ", font=title_font, fg="#ff9900", bg="#0a0a0a").pack(pady=8)
proc_text = tk.Text(proc_frame, font=info_font, fg="#00ff88", bg="#111", insertbackground="green", wrap="word", relief="flat", highlightthickness=0)
scroll_proc = tk.Scrollbar(proc_frame, command=proc_text.yview)
proc_text.pack(side="left", fill="both", expand=True, padx=10, pady=10)
scroll_proc.pack(side="right", fill="y")
proc_text.config(yscrollcommand=scroll_proc.set)
add_tags(proc_text)

net_frame = tk.Frame(notebook, bg="#0a0a0a")
notebook.add(net_frame, text="🌐 Сеть")
tk.Label(net_frame, text="СЕТЕВЫЕ ПОДКЛЮЧЕНИЯ", font=title_font, fg="#00ccff", bg="#0a0a0a").pack(pady=8)
net_text = tk.Text(net_frame, font=info_font, fg="#00ff88", bg="#111", insertbackground="green", wrap="word", relief="flat", highlightthickness=0)
scroll_net = tk.Scrollbar(net_frame, command=net_text.yview)
net_text.pack(side="left", fill="both", expand=True, padx=10, pady=10)
scroll_net.pack(side="right", fill="y")
net_text.config(yscrollcommand=scroll_net.set)
add_tags(net_text)

log_frame = tk.Frame(notebook, bg="#0a0a0a")
notebook.add(log_frame, text="📄 Логи")
tk.Label(log_frame, text="ОТЛАДКА", font=title_font, fg="#ffffff", bg="#0a0a0a").pack(pady=8)
log_text = tk.Text(log_frame, font=mono_font, fg="#00ff88", bg="#111", insertbackground="white", wrap="word", relief="sunken", highlightbackground="#333", state="normal")
scroll_log = tk.Scrollbar(log_frame, command=log_text.yview)
log_text.pack(side="left", fill="both", expand=True, padx=10, pady=10)
scroll_log.pack(side="right", fill="y")
log_text.config(yscrollcommand=scroll_log.set)
add_tags(log_text)

# Перенаправление вывода
sys.stdout = TextRedirect(log_text)
sys.stderr = TextRedirect(log_text)
safe_print("✅ Приложение запущено")
safe_print(f"ОС: {platform.system()} | Python: {platform.python_version()}")

# === Функции вывода ===
def insert_line(text: str, tag: str = "good", target="info"):
    widget = {"info": info_text, "proc": proc_text, "net": net_text, "log": log_text}[target]
    widget.insert("end", text + "\n", tag)

def header(title: str, target="info"):
    sep = "─" * 60
    insert_line(f"┌{sep}┐", "header", target)
    insert_line(f"{title:^62}", "header", target)
    insert_line(f"└{sep}┘", "header", target)
    insert_line("", target)

# === Кнопка "Сохранить отчёт" ===
def save_report():
    file_path = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("Текст", "*.txt"), ("Все", "*.*")],
        title="Сохранить отчёт"
    )
    if not file_path: return
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("📋 ОТЧЁТ О СИСТЕМЕ\n")
            f.write(f"Дата: {datetime.datetime.now()}\n\n")
            sections = {"Информация": info_text, "Процессы": proc_text, "Сеть": net_text}
            for name, widget in sections.items():
                f.write(f"=== {name} ===\n")
                f.write(widget.get("1.0", "end-1c") + "\n\n")
        safe_print(f"✅ Отчёт сохранён: {file_path}")
    except Exception as e:
        safe_print(f"❌ Ошибка: {e}")

btn_save = tk.Button(root, text="💾 Отчёт", font=("Arial", 10), bg="#0088cc", fg="white", command=save_report)
btn_save.pack(pady=4)

# === Сбор данных ===
def collect_system_info():
    info_text.config(state="normal")
    info_text.delete("1.0", "end")
    safe_print("🔄 Сбор данных: Инфо...")
    # ... (вся ваша логика остаётся без изменений) ...
    header("🌐 ОПЕРАЦИОННАЯ СИСТЕМА")
    insert_line(f"Система: {platform.system()}")
    insert_line(f"Версия: {platform.version()}")
    insert_line(f"Архитектура: {platform.architecture()[0]}")
    insert_line(f"Имя ПК: {platform.node()}")
    insert_line("")
    header("⚙️ ПРОЦЕССОР")
    insert_line(f"Модель: {platform.processor() or 'Неизвестно'}")
    insert_line(f"Ядер: {psutil.cpu_count(logical=False)} | Потоков: {psutil.cpu_count(logical=True)}")
    if psutil.cpu_freq():
        insert_line(f"Частота: {psutil.cpu_freq().max:.0f} МГц")
    insert_line("")
    header("🧠 RAM")
    vm = psutil.virtual_memory()
    insert_line(f"Объём: {get_size(vm.total)}")
    insert_line(f"Используется: {get_size(vm.used)} ({vm.percent:.1f}%)", "good" if vm.percent < 80 else "warn")
    if wmi_available:
        try:
            mems = c.Win32_PhysicalMemory()
            insert_line(f"Модулей RAM: {len(mems)}")
            for i, mem in enumerate(mems):
                cap = get_size(int(mem.Capacity))
                speed = f"{mem.ConfiguredClockSpeed} МГц" if hasattr(mem, 'ConfiguredClockSpeed') else "—"
                insert_line(f"  Модуль {i+1}: {cap} | {speed}")
        except Exception as e:
            insert_line(f"  ⚠️ Ошибка RAM: {e}", "warn")
    insert_line("")
    # Материнская плата, BIOS, GPU — аналогично, кратко
    if wmi_available:
        header("🔌 МАТЕРИНСКАЯ ПЛАТА")
        try:
            base = c.Win32_BaseBoard()[0]
            insert_line(f"Производитель: {base.Manufacturer}")
            insert_line(f"Модель: {base.Product}")
        except: insert_line("❌ Не получено", "warn")

        header("💾 BIOS")
        try:
            bios = c.Win32_BIOS()[0]
            insert_line(f"Производитель: {bios.Manufacturer}")
            insert_line(f"Версия: {bios.SMBIOSBIOSVersion}")
        except: insert_line("❌ Не получено", "warn")

        header("🎮 ВИДЕОКАРТА")
        try:
            for gpu in c.Win32_VideoController():
                insert_line(f"Модель: {gpu.Name}")
                if hasattr(gpu, 'AdapterRAM'):
                    ram_mb = int(gpu.AdapterRAM) / 1024 / 1024
                    insert_line(f"Память: {ram_mb:.0f} МБ")
        except: insert_line("❌ Не получено", "warn")
    else:
        insert_line("🔧 WMI недоступен — нет данных о плате/GPU", "warn")
    safe_print("✅ Информация собрана")
    info_text.config(state="disabled")

def collect_processes():
    proc_text.config(state="normal")
    proc_text.delete("1.0", "end")
    safe_print("🔄 Сбор: Процессы...")
    header("🧩 ПРОЦЕССЫ", "proc")
    insert_line("PID | Имя | CPU% | RAM (MB)", "header", "proc")
    processes = []
    try:
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
            processes.append({
                'pid': p.info['pid'],
                'name': p.info['name'][:18],
                'cpu': p.info['cpu_percent'] or 0,
                'ram': p.info['memory_info'].rss / 1024 / 1024
            })
        processes.sort(key=lambda x: x['cpu'], reverse=True)
        for proc in processes[:25]:
            color = "high" if proc['cpu'] > 50 else "med" if proc['cpu'] > 10 else "low"
            insert_line(f"{proc['pid']:5} | {proc['name']:<18} | {proc['cpu']:5.1f} | {proc['ram']:7.1f}", color, "proc")
    except Exception as e:
        insert_line(f"Ошибка: {e}", "crit", "proc")
    safe_print("✅ Процессы собраны")
    proc_text.config(state="disabled")

def collect_network_connections():
    net_text.config(state="normal")
    net_text.delete("1.0", "end")
    safe_print("🔄 Сбор: Сеть...")
    header("🌐 ПОДКЛЮЧЕНИЯ", "net")
    insert_line("Протокол | Локальный | Удалённый | Статус | Процесс", "header", "net")
    try:
        for conn in psutil.net_connections(kind='inet')[:30]:
            laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "::"
            raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "-"
            state = "✅" if conn.status == 'ESTABLISHED' else "👂" if conn.status == 'LISTEN' else "⏳"
            proto = "TCP" if conn.type == 1 else "UDP"
            try:
                proc_name = psutil.Process(conn.pid).name() if conn.pid else "Система"
            except:
                proc_name = "Неизв."
            insert_line(f"{proto:6} | {laddr[:15]:<15} | {raddr[:15]:<15} | {state:4} | {proc_name[:12]}", "good", "net")
    except Exception as e:
        insert_line(f"Ошибка: {e}", "crit", "net")
    safe_print("✅ Сеть собрана")
    net_text.config(state="disabled")

# === Графики ===
MAX_POINTS = 150
net_down = deque([0]*MAX_POINTS, maxlen=MAX_POINTS)
net_up = deque([0]*MAX_POINTS, maxlen=MAX_POINTS)
cpu_usage = deque([0]*MAX_POINTS, maxlen=MAX_POINTS)
ram_usage = deque([0]*MAX_POINTS, maxlen=MAX_POINTS)
net_old = psutil.net_io_counters()

def update_graphs():
    global net_old
    try:
        new_net = psutil.net_io_counters()
        down = (new_net.bytes_recv - net_old.bytes_recv) / 1024
        up = (new_net.bytes_sent - net_old.bytes_sent) / 1024
        net_down.append(max(0, min(down, 8000)))
        net_up.append(max(0, min(up, 8000)))
        net_old = new_net
        cpu_usage.append(psutil.cpu_percent(interval=None))
        ram_usage.append(psutil.virtual_memory().percent)

        canvas.delete("all")
        w = max(canvas.winfo_width(), 400)
        h = 240

        def draw(data, y, col, label):
            points = []
            for i, val in enumerate(data):
                x = i * (w / MAX_POINTS)
                point_y = y - (val / 100) * (h - 40)
                points.extend([x, point_y])
            if len(points) > 2:
                canvas.create_line(points, fill=col, width=2, smooth=True)
            canvas.create_text(70, y - 15, text=label, fill=col, font=info_font)

        draw(net_down, 50, "#00ccff", "⬇ КБ/с")
        draw(net_up, 100, "#00ffaa", "⬆ Отпр.")
        draw(cpu_usage, 150, "#ff5555", "📊 CPU %")
        draw(ram_usage, 200, "#ffaa33", "🧠 RAM %")
    except Exception as e:
        safe_print(f"❌ График: {e}")

    root.after(1000, update_graphs)

graph_frame = tk.Frame(notebook, bg="#0a0a0a")
notebook.add(graph_frame, text="📈 Мониторинг")
tk.Label(graph_frame, text="РЕАЛЬНОЕ ВРЕМЯ: CPU | RAM | СЕТЬ", font=title_font, fg="#ff9900", bg="#0a0a0a").pack(pady=8)
canvas = tk.Canvas(graph_frame, bg="#111", height=240, highlightthickness=0)
canvas.pack(fill="both", expand=True, padx=15, pady=8)

# ========================================
# 🎮 ОВЕРЛЕЙ (HUD) — ИСПРАВЛЕН
# ========================================
config_file = "overlay_config.json"
default_config = {"x": 50, "y": 50, "width": 240, "height": 110}

try:
    overlay_config = json.load(open(config_file)) if os.path.exists(config_file) else default_config
except:
    overlay_config = default_config

# === Оверлей: НЕ закрывается крестиком, только F8 ===
overlay = tk.Toplevel(root)
overlay.title("🎮 HUD")
overlay.geometry(f"{overlay_config['width']}x{overlay_config['height']}+{overlay_config['x']}+{overlay_config['y']}")
overlay.overrideredirect(True)  # Убираем рамку и крестик
overlay.attributes("-topmost", True)
overlay.attributes("-alpha", 0.93)
overlay.configure(bg="black")

# Защита от закрытия
overlay.protocol("WM_DELETE_WINDOW", lambda: None)  # Игнорировать крестик

overlay_label = tk.Label(
    overlay,
    text="Загрузка...",
    font=("Consolas", 9),
    fg="#00ff88",
    bg="black",
    justify="left",
    anchor="nw",
    padx=10,
    pady=8
)
overlay_label.pack(fill="both", expand=True)

minimize_btn = tk.Label(overlay, text="◀", font=("Arial", 10, "bold"), fg="gray", bg="black", cursor="hand2")
minimize_btn.place(relx=1.0, rely=1.0, anchor="se", x=-5, y=-5)

is_overlay_minimized = False
current_full_text = ""
current_minimized_text = ""

def toggle_minimize():
    global is_overlay_minimized
    overlay_label.config(text=current_minimized_text if is_overlay_minimized else current_full_text)
    minimize_btn.config(text="▶" if is_overlay_minimized else "◀")
    overlay.geometry("240x20" if is_overlay_minimized else f"{overlay_config['width']}x{overlay_config['height']}")
    is_overlay_minimized = not is_overlay_minimized

def save_pos(e):
    pos = overlay.winfo_geometry().split('+')
    try:
        overlay_config.update({"x": int(pos[1]), "y": int(pos[2])})
        with open(config_file, "w") as f:
            json.dump(overlay_config, f)
    except: pass

overlay_label.bind("<Button-1>", lambda e: [setattr(overlay, '_x', e.x), setattr(overlay, '_y', e.y)])
overlay_label.bind("<B1-Motion>", lambda e: overlay.geometry(f'+{e.x_root - overlay._x}+{e.y_root - overlay._y}'))
minimize_btn.bind("<Button-1>", lambda e: toggle_minimize())
overlay.bind("<ButtonRelease-1>", save_pos)

# === F8: только для оверлея, НЕ закрывает программу ===
def toggle_overlay(event=None):
    if overlay.state() == "withdrawn":
        overlay.deiconify()
    else:
        overlay.withdraw()

root.bind("<F8>", toggle_overlay)
overlay.bind("<F8>", toggle_overlay)  # Для удобства

# === Обновление оверлея ===
def update_overlay():
    global current_full_text, current_minimized_text

    if not hasattr(update_overlay, 'last_time'):
        update_overlay.last_time = time.time()
        fps = 0
    else:
        now = time.time()
        fps = int(1 / (now - update_overlay.last_time)) if (now - update_overlay.last_time) > 0 else 60
        update_overlay.last_time = now

    cpu = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory()
    ram_p = ram.percent

    temp = "N/A"
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            if "coretemp" in temps:
                temp = max(t.current for t in temps["coretemp"])
            elif "cpu_thermal" in temps:
                temp = temps["cpu_thermal"][0].current
    except: pass

    color = "#ff3333" if isinstance(temp, (int, float)) and temp > 80 else \
            "#ffaa00" if isinstance(temp, (int, float)) and temp > 65 else "#00ff88"
    temp = f"{temp:.0f}" if isinstance(temp, (int, float)) else "N/A"

    battery = psutil.sensors_battery()
    battery_str = f"🔋{battery.percent}%" if battery else ""

    current_minimized_text = f"FPS:{fps:3d} | CPU:{cpu:4.1f}% | RAM:{ram_p:4.1f}%"
    current_full_text = (
        f"FPS: {fps:3d} | CPU: {cpu:4.1f}%\n"
        f"RAM: {ram_p:4.1f}% | {ram.used//1024//1024:4d}/{ram.total//1024//1024:4d} MB\n"
        f"Temp: {temp}°C       | {battery_str}"
    )

    overlay_label.config(text=current_minimized_text if is_overlay_minimized else current_full_text, fg=color)
    overlay.after(500, update_overlay)

# === ЗАПУСК ===
safe_print("🚀 Запуск сбора данных...")
collect_system_info()
collect_processes()
collect_network_connections()

root.after(100, update_graphs)
root.after(100, update_overlay)

safe_print("🟢 Приложение готово. F8 — показать/скрыть оверлей.")
root.mainloop()
