import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk, filedialog
import platform
import datetime
import os
import wmi
import psutil
from collections import deque
import sys
import io
import json
import time

# === Глобальный логгер ===
def safe_print(message):
    try:
        if 'log_text' in globals() and hasattr(log_text, 'insert'):
            log_text.insert("end", message + "\n", "log")
            log_text.see("end")
        else:
            print(message)
    except Exception as e:
        print(f"Ошибка safe_print: {str(e)}")

# === Перехват вывода ===
class TextRedirect(io.StringIO):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def write(self, s):
        try:
            if s.strip():
                tag = "error" if "Traceback" in s or "Error" in s else "log"
                self.text_widget.insert("end", s, tag)
                self.text_widget.see("end")
        except Exception as e:
            print(f"Ошибка TextRedirect: {str(e)}")

    def flush(self):
        pass

# === WMI (только Windows) ===
wmi_available = False
wmi_module = None

if platform.system() == "Windows":
    try:
        import wmi
        wmi_module = wmi.WMI()
        wmi_available = True
        safe_print("✅ WMI подключен")
    except ImportError as e:
        safe_print(f"⚠️ WMI не установлен: {str(e)}")
    except Exception as e:
        safe_print(f"⚠️ Ошибка WMI: {str(e)}")
else:
    safe_print("ℹ️ WMI доступен только для Windows")

# === Функция перевода байтов ===
def get_size(bytes_value: float) -> str:
    try:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"
    except Exception as e:
        return f"Ошибка: {str(e)}"

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
    try:
        text_widget.tag_config("good", foreground="#00ff88")
        text_widget.tag_config("warn", foreground="#ffaa00")
        text_widget.tag_config("crit", foreground="#ff5555")
        text_widget.tag_config("header", foreground="#00aaff", font=("Consolas", 12, "bold"))
        text_widget.tag_config("high", foreground="#ff3333")
        text_widget.tag_config("med", foreground="#ffcc00")
        text_widget.tag_config("low", foreground="#00ccff")
        text_widget.tag_config("log", foreground="#cccccc")
        text_widget.tag_config("error", foreground="#ff5555")
    except Exception as e:
        safe_print(f"Ошибка add_tags: {str(e)}")

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
safe_print(f"Используется psutil v{psutil.__version__}")

# === Функции вывода ===
def insert_line(text: str, tag: str = "good", target="info"):
    try:
        widget = {"info": info_text, "proc": proc_text, "net": net_text, "log": log_text}[target]
        widget.insert("end", text + "\n", tag)
    except KeyError as e:
        safe_print(f"Ошибка insert_line: неверный target '{target}'")
    except Exception as e:
        safe_print(f"Ошибка insert_line: {str(e)}")

def header(title: str, target="info"):
    try:
        sep = "─" * 60
        insert_line(f"┌{sep}┐", "header", target)
        insert_line(f"{title:^62}", "header", target)
        insert_line(f"└{sep}┘", "header", target)
        insert_line("", target)
    except Exception as e:
        safe_print(f"Ошибка header: {str(e)}")

# === Кнопка "Сохранить отчёт" ===
def save_report():
    file_path = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("Текст", "*.txt"), ("JSON", "*.json"), ("Все", "*.*")],
        title="Сохранить отчёт"
    )
    
    if not file_path:
        safe_print("❌ Сохранение отменено пользователем")
        return False
    
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("📋 ОТЧЁТ О СИСТЕМЕ\n")
            f.write(f"Дата: {datetime.datetime.now()}\n")
            f.write(f"Система: {platform.system()} {platform.version()}\n\n")
            
            sections = {"Информация": info_text, "Процессы": proc_text, "Сеть": net_text}
            for name, widget in sections.items():
                f.write(f"=== {name} ===\n")
                content = widget.get("1.0", "end-1c")
                if content.strip():
                    f.write(content + "\n\n")
                else:
                    f.write("(нет данных)\n\n")
        
        safe_print(f"✅ Отчёт сохранён: {file_path}")
        return True
    except PermissionError as e:
        safe_print(f"❌ Ошибка доступа к файлу: {str(e)}")
        return False
    except OSError as e:
        safe_print(f"❌ Ошибка файловой системы: {str(e)}")
        return False
    except Exception as e:
        safe_print(f"❌ Ошибка сохранения: {str(e)}")
        return False

btn_save = tk.Button(root, text="💾 Отчёт", font=("Arial", 10), bg="#0088cc", fg="white", command=save_report)
btn_save.pack(pady=4)

# === Сбор данных с использованием psutil ===
def collect_system_info():
    try:
        info_text.config(state="normal")
        info_text.delete("1.0", "end")
        safe_print("🔄 Сбор данных: Инфо...")
        
        header("🌐 ОПЕРАЦИОННАЯ СИСТЕМА")
        insert_line(f"Система: {platform.system()}")
        insert_line(f"Версия: {platform.version()}")
        try:
            insert_line(f"Архитектура: {platform.architecture()[0]}")
        except Exception as e:
            insert_line(f"Архитектура: ошибка ({str(e)})")
        insert_line(f"Имя ПК: {platform.node()}")
        
        try:
            boot_time = datetime.datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M:%S')
            insert_line(f"Время загрузки: {boot_time}")
        except Exception as e:
            insert_line(f"Время загрузки: ошибка ({str(e)})")
        
        insert_line("")
        
        header("⚙️ ПРОЦЕССОР")
        try:
            cpu_brand = platform.processor() or 'Неизвестно'
            insert_line(f"Модель: {cpu_brand}")
        except Exception as e:
            insert_line(f"Модель: ошибка ({str(e)})")
        
        try:
            cores_physical = psutil.cpu_count(logical=False)
            cores_logical = psutil.cpu_count(logical=True)
            insert_line(f"Ядер: {cores_physical} | Потоков: {cores_logical}")
        except Exception as e:
            insert_line(f"Ядра/потоки: ошибка ({str(e)})")
        
        try:
            cpu_freq = psutil.cpu_freq()
            if cpu_freq:
                insert_line(f"Текущая частота: {cpu_freq.current:.0f} МГц")
                insert_line(f"Максимальная частота: {cpu_freq.max:.0f} МГц")
        except Exception as e:
            insert_line(f"Частота CPU: ошибка ({str(e)})")
        
        try:
            cpu_usage = psutil.cpu_percent(interval=0.1)
            insert_line(f"Загрузка CPU: {cpu_usage:.1f}%")
        except Exception as e:
            insert_line(f"Загрузка CPU: ошибка ({str(e)})")
        
        insert_line("")
        
        header("🧠 RAM")
        try:
            vm = psutil.virtual_memory()
            insert_line(f"Объём RAM: {get_size(vm.total)}")
            
            ram_percent = vm.percent
            tag = "good" if ram_percent < 70 else "warn" if ram_percent < 90 else "crit"
            insert_line(f"Используется: {get_size(vm.used)} ({ram_percent:.1f}%)", tag)
            insert_line(f"Доступно: {get_size(vm.available)}")
        except Exception as e:
            insert_line(f"Ошибка RAM: {str(e)}", "crit")
        
        try:
            swap = psutil.swap_memory()
            if swap.total > 0:
                insert_line(f"Swap: {get_size(swap.total)} | Используется: {get_size(swap.used)} ({swap.percent:.1f}%)")
        except Exception as e:
            insert_line(f"Ошибка Swap: {str(e)}", "warn")
        
        if wmi_available and wmi_module:
            try:
                mems = wmi_module.Win32_PhysicalMemory()
                insert_line(f"Модулей RAM: {len(mems)}")
                for i, mem in enumerate(mems):
                    try:
                        cap = get_size(int(mem.Capacity))
                        speed = f"{mem.ConfiguredClockSpeed} МГц" if hasattr(mem, 'ConfiguredClockSpeed') else "—"
                        insert_line(f"  Модуль {i+1}: {cap} | {speed}")
                    except Exception as e:
                        insert_line(f"  ⚠️ Ошибка модуля {i+1}: {str(e)}", "warn")
            except Exception as e:
                insert_line(f"  ⚠️ Ошибка RAM через WMI: {str(e)}", "warn")
        
        insert_line("")
        
        header("💾 ДИСКИ")
        try:
            partitions = psutil.disk_partitions()
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    insert_line(f"{partition.device} ({partition.fstype}) -> {partition.mountpoint}")
                    insert_line(f"  Всего: {get_size(usage.total)} | Свободно: {get_size(usage.free)} ({usage.percent:.1f}% занято)")
                except PermissionError as e:
                    insert_line(f"  ⚠️ Нет доступа к {partition.mountpoint}", "warn")
                except Exception as e:
                    insert_line(f"  Ошибка чтения {partition.mountpoint}: {str(e)}", "warn")
        except Exception as e:
            insert_line(f"Ошибка чтения дисков: {str(e)}", "warn")
        
        insert_line("")
        
        # Материнская плата, BIOS, GPU — через WMI
        if wmi_available and wmi_module:
            try:
                header("🔌 МАТЕРИНСКАЯ ПЛАТА")
                baseboards = wmi_module.Win32_BaseBoard()
                if baseboards:
                    base = baseboards[0]
                    insert_line(f"Производитель: {base.Manufacturer or 'Неизвестно'}")
                    insert_line(f"Модель: {base.Product or 'Неизвестно'}")
                    insert_line(f"Серийный номер: {base.SerialNumber or 'Неизвестно'}")
            except Exception as e:
                insert_line(f"Ошибка получения данных о материнской плате: {str(e)}", "warn")

            try:
                header("💾 BIOS")
                bioses = wmi_module.Win32_BIOS()
                if bioses:
                    bios = bioses[0]
                    insert_line(f"Производитель: {bios.Manufacturer or 'Неизвестно'}")
                    insert_line(f"Версия: {bios.SMBIOSBIOSVersion or 'Неизвестно'}")
                    insert_line(f"Дата: {bios.ReleaseDate or 'Неизвестно'}")
            except Exception as e:
                insert_line(f"Ошибка получения данных о BIOS: {str(e)}", "warn")

            try:
                header("🎮 ВИДЕОКАРТА")
                gpus = wmi_module.Win32_VideoController()
                for i, gpu in enumerate(gpus):
                    insert_line(f"GPU {i+1}: {gpu.Name or 'Неизвестно'}")
                    if hasattr(gpu, 'AdapterRAM') and gpu.AdapterRAM:
                        try:
                            ram_mb = int(gpu.AdapterRAM) / 1024 / 1024
                            insert_line(f"  Память: {ram_mb:.0f} МБ")
                        except Exception as e:
                            insert_line(f"  Ошибка памяти GPU: {str(e)}")
                    if hasattr(gpu, 'DriverVersion'):
                        insert_line(f"  Драйвер: {gpu.DriverVersion}")
            except Exception as e:
                insert_line(f"Ошибка получения данных о GPU: {str(e)}", "warn")
        else:
            insert_line("🔧 WMI недоступен — нет данных о плате/GPU", "warn")
        
        safe_print("✅ Информация о системе собрана")
    
    except Exception as e:
        safe_print(f"❌ Критическая ошибка в collect_system_info: {str(e)}")
        insert_line(f"❌ Критическая ошибка: {str(e)}", "crit")
    
    finally:
        try:
            info_text.config(state="disabled")
        except Exception:
            pass

def collect_processes():
    try:
        proc_text.config(state="normal")
        proc_text.delete("1.0", "end")
        safe_print("🔄 Сбор данных: Процессы...")
        header("🧩 АКТИВНЫЕ ПРОЦЕССЫ", "proc")
        insert_line("PID | Имя | CPU% | RAM (MB) | Пользователь", "header", "proc")
        processes = []
        
        try:
            for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'username']):
                try:
                    processes.append({
                        'pid': p.info['pid'],
                        'name': p.info['name'][:20],
                        'cpu': p.info['cpu_percent'] or 0,
                        'ram': p.info['memory_info'].rss / 1024 / 1024 if p.info['memory_info'] else 0,
                        'user': p.info['username'][:12] if p.info['username'] else 'SYSTEM'
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    continue
                except Exception as e:
                    safe_print(f"Ошибка процесса {p.info.get('pid', 'N/A')}: {str(e)}")
            
            # Обновляем CPU процент для всех процессов
            try:
                psutil.cpu_percent(interval=0.1)  # Первый вызов игнорируется
                time.sleep(0.1)
                
                for p in processes:
                    try:
                        proc = psutil.Process(p['pid'])
                        p['cpu'] = proc.cpu_percent(interval=0)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                    except Exception as e:
                        safe_print(f"Ошибка обновления CPU для PID {p['pid']}: {str(e)}")
            except Exception as e:
                safe_print(f"Ошибка обновления CPU процентов: {str(e)}")
            
            processes.sort(key=lambda x: x['cpu'], reverse=True)
            
            for proc in processes[:30]:
                color = "high" if proc['cpu'] > 50 else "med" if proc['cpu'] > 10 else "low"
                insert_line(f"{proc['pid']:6} | {proc['name']:<20} | {proc['cpu']:5.1f} | {proc['ram']:7.1f} | {proc['user']:<12}", color, "proc")
            
            # Статистика
            insert_line("", "proc")
            insert_line(f"Всего процессов: {len(processes)}", "header", "proc")
            
        except Exception as e:
            insert_line(f"Ошибка сбора процессов: {str(e)}", "crit", "proc")
        
        safe_print("✅ Процессы собраны")
    
    except Exception as e:
        safe_print(f"❌ Критическая ошибка в collect_processes: {str(e)}")
    
    finally:
        try:
            proc_text.config(state="disabled")
        except Exception:
            pass

def collect_network_connections():
    try:
        net_text.config(state="normal")
        net_text.delete("1.0", "end")
        safe_print("🔄 Сбор данных: Сеть...")
        header("🌐 СЕТЕВЫЕ ПОДКЛЮЧЕНИЯ", "net")
        
        try:
            # Сетевые интерфейсы
            header("📡 СЕТЕВЫЕ ИНТЕРФЕЙСЫ", "net")
            interfaces = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            
            for iface, addrs in interfaces.items():
                try:
                    insert_line(f"📶 {iface}:", "header", "net")
                    if iface in stats:
                        stat = stats[iface]
                        status_text = '✅ ВКЛ' if stat.isup else '❌ ВЫКЛ'
                        tag = "good" if stat.isup else "warn"
                        insert_line(f"  Статус: {status_text} | MTU: {stat.mtu}", tag, "net")
                    
                    for addr in addrs:
                        try:
                            if addr.family == psutil.AF_INET:
                                insert_line(f"  IPv4: {addr.address}/{addr.netmask}", "good", "net")
                            elif addr.family == psutil.AF_INET6:
                                insert_line(f"  IPv6: {addr.address}", "good", "net")
                            elif addr.family == psutil.AF_LINK:
                                insert_line(f"  MAC: {addr.address}", "good", "net")
                        except Exception as e:
                            insert_line(f"  Ошибка адреса: {str(e)}", "warn", "net")
                except Exception as e:
                    insert_line(f"Ошибка интерфейса {iface}: {str(e)}", "warn", "net")
            
            insert_line("", "net")
            
            # Активные подключения
            header("🔗 АКТИВНЫЕ ПОДКЛЮЧЕНИЯ", "net")
            insert_line("Протокол | Локальный адрес | Удалённый адрес | Статус | PID", "header", "net")
            
            connections = []
            try:
                connections = psutil.net_connections(kind='inet')
            except psutil.AccessDenied as e:
                insert_line(f"⚠️ Требуются права администратора: {str(e)}", "warn", "net")
            except Exception as e:
                insert_line(f"⚠️ Ошибка получения подключений: {str(e)}", "warn", "net")
            
            for conn in connections[:40]:
                try:
                    laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "0.0.0.0:0"
                    raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "-"
                    
                    status_map = {
                        'ESTABLISHED': '✅',
                        'LISTEN': '👂',
                        'TIME_WAIT': '⏳',
                        'CLOSE_WAIT': '⌛'
                    }
                    status_icon = status_map.get(conn.status, '❓')
                    
                    proto = "TCP" if conn.type == 1 else "UDP"
                    
                    proc_name = "Система"
                    if conn.pid:
                        try:
                            proc = psutil.Process(conn.pid)
                            proc_name = proc.name()[:15]
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            proc_name = f"[{conn.pid}]"
                        except Exception:
                            proc_name = f"PID:{conn.pid}"
                    
                    color = "good" if conn.status == 'ESTABLISHED' else "warn" if conn.status == 'LISTEN' else "low"
                    insert_line(f"{proto:6} | {laddr:<20} | {raddr:<20} | {status_icon} {conn.status:<10} | {proc_name}", color, "net")
                except Exception as e:
                    safe_print(f"Ошибка обработки подключения: {str(e)}")
                    continue
            
            # Сетевая статистика
            insert_line("", "net")
            header("📊 СЕТЕВАЯ СТАТИСТИКА", "net")
            
            try:
                net_io = psutil.net_io_counters()
                insert_line(f"Отправлено: {get_size(net_io.bytes_sent)}", "good", "net")
                insert_line(f"Получено: {get_size(net_io.bytes_recv)}", "good", "net")
                insert_line(f"Пакеты отправлено: {net_io.packets_sent}", "good", "net")
                insert_line(f"Пакеты получено: {net_io.packets_recv}", "good", "net")
                insert_line(f"Ошибки отправки: {net_io.errout}", "warn" if net_io.errout > 0 else "good", "net")
                insert_line(f"Ошибки получения: {net_io.errin}", "warn" if net_io.errin > 0 else "good", "net")
            except Exception as e:
                insert_line(f"Ошибка сетевой статистики: {str(e)}", "warn", "net")
            
        except Exception as e:
            insert_line(f"Критическая ошибка сети: {str(e)}", "crit", "net")
        
        safe_print("✅ Сетевые данные собраны")
    
    except Exception as e:
        safe_print(f"❌ Критическая ошибка в collect_network_connections: {str(e)}")
    
    finally:
        try:
            net_text.config(state="disabled")
        except Exception:
            pass

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
            try:
                points = []
                for i, val in enumerate(data):
                    x = i * (w / MAX_POINTS)
                    point_y = y - (val / 100) * (h - 40)
                    points.extend([x, point_y])
                if len(points) > 2:
                    canvas.create_line(points, fill=col, width=2, smooth=True)
                canvas.create_text(70, y - 15, text=label, fill=col, font=info_font)
            except Exception as e:
                safe_print(f"Ошибка draw графиков: {str(e)}")

        draw(net_down, 50, "#00ccff", "⬇ КБ/с")
        draw(net_up, 100, "#00ffaa", "⬆ КБ/с")
        draw(cpu_usage, 150, "#ff5555", "📊 CPU %")
        draw(ram_usage, 200, "#ffaa33", "🧠 RAM %")
        
        # Добавляем легенду
        canvas.create_text(w - 80, 20, text="Реальное время", fill="#ffffff", font=("Consolas", 9))
        
    except Exception as e:
        safe_print(f"❌ Ошибка обновления графиков: {str(e)}")

    root.after(1000, update_graphs)

graph_frame = tk.Frame(notebook, bg="#0a0a0a")
notebook.add(graph_frame, text="📈 Мониторинг")
tk.Label(graph_frame, text="РЕАЛЬНОЕ ВРЕМЯ: CPU | RAM | СЕТЬ", font=title_font, fg="#ff9900", bg="#0a0a0a").pack(pady=8)
canvas = tk.Canvas(graph_frame, bg="#111", height=240, highlightthickness=0)
canvas.pack(fill="both", expand=True, padx=15, pady=8)

# ========================================
# 🎮 ОВЕРЛЕЙ (HUD)
# ========================================
config_file = "overlay_config.json"
default_config = {"x": 50, "y": 50, "width": 240, "height": 110}

try:
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            overlay_config = json.load(f)
    else:
        overlay_config = default_config
except Exception as e:
    safe_print(f"⚠️ Ошибка загрузки конфига оверлея: {str(e)}")
    overlay_config = default_config

overlay = tk.Toplevel(root)
overlay.title("🎮 HUD")
overlay.geometry(f"{overlay_config['width']}x{overlay_config['height']}+{overlay_config['x']}+{overlay_config['y']}")
overlay.overrideredirect(True)
overlay.attributes("-topmost", True)
overlay.attributes("-alpha", 0.93)
overlay.configure(bg="black")

overlay.protocol("WM_DELETE_WINDOW", lambda: None)

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
    try:
        global is_overlay_minimized
        if is_overlay_minimized:
            overlay_label.config(text=current_full_text)
            minimize_btn.config(text="◀")
            overlay.geometry(f"{overlay_config['width']}x{overlay_config['height']}")
        else:
            overlay_label.config(text=current_minimized_text)
            minimize_btn.config(text="▶")
            overlay.geometry("240x20")
        
        is_overlay_minimized = not is_overlay_minimized
    except Exception as e:
        safe_print(f"Ошибка toggle_minimize: {str(e)}")

def save_pos(event=None):
    try:
        pos = overlay.winfo_geometry().split('+')
        overlay_config.update({
            "x": int(pos[1]),
            "y": int(pos[2]),
            "width": overlay.winfo_width(),
            "height": overlay.winfo_height()
        })
        with open(config_file, "w") as f:
            json.dump(overlay_config, f)
    except Exception as e:
        safe_print(f"⚠️ Ошибка сохранения позиции оверлея: {str(e)}")

overlay_label.bind("<Button-1>", lambda e: [setattr(overlay, '_x', e.x), setattr(overlay, '_y', e.y)])
overlay_label.bind("<B1-Motion>", lambda e: overlay.geometry(f'+{e.x_root - overlay._x}+{e.y_root - overlay._y}'))
minimize_btn.bind("<Button-1>", lambda e: toggle_minimize())
overlay.bind("<ButtonRelease-1>", save_pos)

def toggle_overlay(event=None):
    try:
        if overlay.state() == "withdrawn":
            overlay.deiconify()
        else:
            overlay.withdraw()
    except Exception as e:
        safe_print(f"Ошибка toggle_overlay: {str(e)}")

root.bind("<F8>", toggle_overlay)
overlay.bind("<F8>", toggle_overlay)

def update_overlay():
    global current_full_text, current_minimized_text

    try:
        if not hasattr(update_overlay, 'last_time'):
            update_overlay.last_time = time.time()
            update_overlay.frame_count = 0
            fps = 0
        else:
            update_overlay.frame_count += 1
            now = time.time()
            if now - update_overlay.last_time >= 1.0:
                fps = update_overlay.frame_count
                update_overlay.frame_count = 0
                update_overlay.last_time = now
            else:
                fps = int(1 / (now - update_overlay.last_time)) if (now - update_overlay.last_time) > 0 else 0

        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory()
        ram_p = ram.percent

        temp = None
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for key in ['coretemp', 'cpu_thermal', 'acpitz', 'k10temp']:
                    if key in temps and temps[key]:
                        temp = max(t.current for t in temps[key] if hasattr(t, 'current'))
                        break
        except AttributeError:
            # psutil.sensors_temperatures() может быть недоступен на некоторых системах
            temp = None
        except Exception as e:
            safe_print(f"Ошибка температуры: {str(e)}")
            temp = None

        color = "#ff3333" if temp and temp > 80 else \
                "#ffaa00" if temp and temp > 65 else "#00ff88"
        temp_str = f"{temp:.0f}°C" if temp else "N/A"

        battery = None
        try:
            battery = psutil.sensors_battery()
        except Exception as e:
            safe_print(f"Ошибка батареи: {str(e)}")
            battery = None
        
        battery_str = f"🔋{battery.percent}%" if battery and hasattr(battery, 'percent') else ""

        disk_usage = None
        try:
            disk = psutil.disk_usage('/' if platform.system() != 'Windows' else 'C:\\')
            disk_usage = disk.percent
        except Exception as e:
            disk_usage = None

        current_minimized_text = f"FPS:{fps:3d} | CPU:{cpu:4.1f}% | RAM:{ram_p:4.1f}%"
        
        full_text_lines = [
            f"FPS: {fps:3d} | CPU: {cpu:4.1f}%",
            f"RAM: {ram_p:4.1f}% | {ram.used//1024//1024:4d}/{ram.total//1024//1024:4d} MB",
            f"Temp: {temp_str:8} | {battery_str}"
        ]
        
        if disk_usage:
            full_text_lines.append(f"Disk: {disk_usage:4.1f}% занято")
        
        current_full_text = "\n".join(full_text_lines)

        overlay_label.config(text=current_minimized_text if is_overlay_minimized else current_full_text, fg=color)
    
    except Exception as e:
        safe_print(f"Ошибка update_overlay: {str(e)}")
    
    finally:
        try:
            overlay.after(500, update_overlay)
        except Exception as e:
            safe_print(f"Ошибка планирования update_overlay: {str(e)}")

# === Кнопка обновления данных ===
def refresh_all():
    try:
        safe_print("🔄 Обновление всех данных...")
        collect_system_info()
        collect_processes()
        collect_network_connections()
        safe_print("✅ Все данные обновлены")
    except Exception as e:
        safe_print(f"❌ Ошибка при обновлении данных: {str(e)}")

btn_refresh = tk.Button(root, text="🔄 Обновить", font=("Arial", 10), bg="#22aa22", fg="white", command=refresh_all)
btn_refresh.pack(pady=4)

# === Запуск ===
safe_print("🚀 Запуск сбора данных...")
refresh_all()

root.after(100, update_graphs)
root.after(100, update_overlay)

safe_print("🟢 Приложение готово. F8 — показать/скрыть оверлей.")
safe_print("🔄 Автоматическое обновление графиков каждую секунду")

try:
    root.mainloop()
except KeyboardInterrupt:
    safe_print("🛑 Приложение остановлено пользователем")
except Exception as e:
    safe_print(f"❌ Критическая ошибка в mainloop: {str(e)}")
