import mss
import numpy as np
import cv2
import time
import keyboard
import pyautogui
import win32gui
import os
import winsound
import wave
import audioop
import io
import sys
import requests
import tkinter as tk
from threading import Thread
from tkinter import messagebox, Toplevel, Scale, HORIZONTAL
from tkinter import ttk
import subprocess
import json
import uuid
from pynput.keyboard import Key, Controller as PynputKeyboardController, KeyCode

pyautogui.FAILSAFE = False

pynput_kb = PynputKeyboardController()

# ====================================================================
# BÖLÜM A: GLOBAL AYARLAR VE MOD KONFİGÜRASYONLARI
# ====================================================================

APP_NAME = "MilenSoftware"

GLOBAL_CONFIG = {}
PERSISTENT_SETTINGS_PATH = "persistent_settings.json"
ALARM_SOUND_PATH = "alert.wav"
ALARM_SOUND_PATH_FULL = ""

TARGET_FPS = 2.0
TARGET_FRAME_TIME = 1.0 / TARGET_FPS
CURRENT_VERSION = "2.0.1"

GITHUB_REPO_OWNER = "merterbir"
GITHUB_REPO_NAME = "AutoClicker-Updates"
VERSION_CHECK_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/main/latest_version.json"
NEW_EXE_FILENAME = "AutoClicker.exe"

MOD_TEMPLATES = {
    "METEOR": {
        "title": "Meteor Tarama",
        "lower_color": np.array([112, 50, 20]),
        "upper_color": np.array([160, 90, 140]),
        "min_area": 80,
        "blocker_path": "meteorBlocker.png",
        "is_visible": True
    },
    "ZUNG": {
        "title": "Zung Tarama",
        "lower_color": np.array([0, 150, 150]),
        "upper_color": np.array([10, 255, 255]),
        "min_area": 100,
        "blocker_path": "zungblocker.png",
        "is_visible": True
    },
    "KIZIL": {
        "title": "Kızıl Orman Güney Tarama",
        "lower_color": np.array([0, 60, 70]),
        "upper_color": np.array([10, 200, 200]),
        "min_area": 1000,
        "blocker_path": "kizilblocker.png",
        "is_visible": True
    }
}

ACTIVE_MOD_INSTANCES = []

ALERT_IMAGE_PATHS = {
    "tic": "tic.png",
    "message": "message.png",
    "control": "control.png"
}
ALERT_THRESHOLD = 0.80
ALERT_CHECK_INTERVAL = 0.5
ALERT_COOLDOWN = 3.0
PAUSE_ON_ALERT_SECONDS = 5.0
ALARM_VOLUME = 0.16

# ====================================================================
# B: YARDIMCI FONKSİYONLAR
# ====================================================================

def get_appdata_base_dir():
    app_data_path = os.environ.get('APPDATA')
    if app_data_path:
        app_name = APP_NAME.replace(" ", "_")
        base_dir = os.path.join(app_data_path, app_name)
    else:
        base_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
    os.makedirs(base_dir, exist_ok=True)
    return base_dir


def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        if relative_path != PERSISTENT_SETTINGS_PATH:
            return os.path.join(sys._MEIPASS, relative_path)

    if relative_path == PERSISTENT_SETTINGS_PATH:
        try:
            base_dir = get_appdata_base_dir()
            return os.path.join(base_dir, relative_path)
        except Exception:
            pass

    base_path = os.path.abspath(os.path.dirname(sys.argv[0]))
    return os.path.join(base_path, relative_path)


def get_alert_user_path(filename: str) -> str:
    base_dir = get_appdata_base_dir()
    return os.path.join(base_dir, filename)


def get_default_config():
    return {
        "APP_CONFIG": {
            "APP_TITLE": "Python Otomasyon Botu",
            "GLOBAL_AUTOCLICK_TEXT": "Global Oto Tıkla Aktif",
            "MODES_FRAME_TITLE": "Tarama Modları",
            "ALERT_FRAME_TITLE": "Alert ve Aksiyon Ayarları",
            "STOP_ON_ALERT_TEXT": "Alert Bulunduğunda Bot Durdurulsun",
            "SETTINGS_BUTTON_TEXT": "⚙️ Ayarlar",
            "VERSION_CHECK_TEXT": "Güncelleme Kontrol Et",
            "START_BUTTON_TEXT": "Başlat",
            "STOP_BUTTON_TEXT": "DURDUR",
            "REGION_BUTTON_TEXT": "Bölge Seç (3 sn)",
            "STATUS_INITIAL_TEXT": "Kapalı. Modları başlatmak için yanındaki butonu kullanın."
        },
        "MOD_VISIBILITY": {
            "METEOR": True,
            "ZUNG": True,
            "KIZIL": True
        },
        "ALERT_TEXTS": {
            "tic": "Tic (Kritik) Bulunursa",
            "message": "Message (Kritik) Bulunursa",
            "control": "Control (Kritik) Bulunursa"
        },
        "SYSTEM_SETTINGS": {
            "ALARM_VOLUME": 0.16,
            "stop_on_alert_main": False,
            "stop_on_tic": True,
            "stop_on_message": True,
            "stop_on_control": True
        },
        "SAVED_INSTANCES": []
    }


def _merge_config(default_data, loaded_data):
    merged = default_data.copy()

    for key in merged:
        if key in loaded_data and isinstance(merged[key], dict) and isinstance(loaded_data[key], dict):
            merged[key] = _merge_config(merged[key], loaded_data[key])
        elif key in loaded_data and type(merged[key]) == type(loaded_data[key]):
            merged[key] = loaded_data[key]
        elif key == "SAVED_INSTANCES" and isinstance(loaded_data.get(key), list):
            merged[key] = loaded_data[key]

    return merged


def load_config():
    global GLOBAL_CONFIG, ALARM_VOLUME, ACTIVE_MOD_INSTANCES

    default_config = get_default_config()
    GLOBAL_CONFIG = default_config.copy()

    config_path = resource_path(PERSISTENT_SETTINGS_PATH)
    loaded_config = None

    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
        except Exception:
            loaded_config = None

    if loaded_config:
        GLOBAL_CONFIG = _merge_config(default_config, loaded_config)
    else:
        GLOBAL_CONFIG = default_config.copy()

    ALARM_VOLUME = GLOBAL_CONFIG["SYSTEM_SETTINGS"]["ALARM_VOLUME"]
    ACTIVE_MOD_INSTANCES = GLOBAL_CONFIG["SAVED_INSTANCES"]

    if not os.path.exists(config_path) or not loaded_config:
        save_config(GLOBAL_CONFIG)


def save_config(new_config):
    global GLOBAL_CONFIG
    GLOBAL_CONFIG = new_config
    config_path = resource_path(PERSISTENT_SETTINGS_PATH)

    save_data = {
        "SYSTEM_SETTINGS": GLOBAL_CONFIG["SYSTEM_SETTINGS"],
        "SAVED_INSTANCES": GLOBAL_CONFIG["SAVED_INSTANCES"],
        "MOD_VISIBILITY": GLOBAL_CONFIG["MOD_VISIBILITY"],
    }

    try:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception:
        return False


load_config()

ALARM_SOUND_PATH_FULL = resource_path(ALARM_SOUND_PATH)
alarm_wave_data = None


def load_alarm_sound():
    global alarm_wave_data
    if os.path.exists(ALARM_SOUND_PATH_FULL):
        try:
            with wave.open(ALARM_SOUND_PATH_FULL, "rb") as wf:
                params = wf.getparams()
                frames = wf.readframes(params.nframes)
            alarm_wave_data = (frames, params.sampwidth, params.nchannels, params.framerate)
        except:
            alarm_wave_data = None


load_alarm_sound()


def play_alert_sound():
    if alarm_wave_data is None:
        return
    frames, sampwidth, nchannels, framerate = alarm_wave_data
    vol = max(0.0, min(1.5, ALARM_VOLUME))
    scaled = audioop.mul(frames, sampwidth, vol)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(nchannels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(framerate)
        wf.writeframes(scaled)
    winsound.PlaySound(buf.getvalue(), winsound.SND_MEMORY)


def get_active_window_rect():
    hwnd = win32gui.GetForegroundWindow()
    if hwnd == 0:
        return None
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    return (left + 8, top + 30, right - 8, bottom - 8)


# ================== PYNPUT KLAVYE HELPERLARI ==================

def press_char_key(c: str, hold: float = 0.03):
    try:
        key = KeyCode.from_char(c)
        pynput_kb.press(key)
        time.sleep(hold)
        pynput_kb.release(key)
    except Exception:
        pass


def press_ctrl_g(hold: float = 0.03):
    try:
        pynput_kb.press(Key.ctrl)
        key_g = KeyCode.from_char('g')
        pynput_kb.press(key_g)
        time.sleep(hold)
        pynput_kb.release(key_g)
        pynput_kb.release(Key.ctrl)
    except Exception:
        pass


# ====================================================================
# C: GÖRSEL YAKALAMA SINIFLARI
# ====================================================================

class AreaSelector:
    def __init__(self, master, callback, filename):
        self.master = master
        self.callback = callback
        self.filename = filename
        self.start_x = None
        self.start_y = None
        self.rect = None
        self.snip_tool = None

        self.screen_width = self.master.winfo_screenwidth()
        self.screen_height = self.master.winfo_screenheight()

        self.snip_tool = Toplevel(self.master)
        self.snip_tool.title("Alan Seçimi")
        self.snip_tool.geometry(f"{self.screen_width}x{self.screen_height}+0+0")

        self.snip_tool.overrideredirect(True)
        self.snip_tool.attributes("-alpha", 0.5)
        self.snip_tool.attributes("-topmost", True)
        self.snip_tool.focus_force()

        self.canvas = tk.Canvas(self.snip_tool, cursor="tcross", bg='black', bd=0, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

        self.snip_tool.bind("<Escape>", self.on_escape)

    def on_escape(self, event=None):
        try:
            self.snip_tool.destroy()
        except Exception:
            pass
        try:
            self.master.deiconify()
        except Exception:
            pass
        messagebox.showinfo("Bilgi", "Ekran görüntüsü alma iptal edildi (ESC).")

    def on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect:
            self.canvas.delete(self.rect)

    def on_mouse_drag(self, event):
        self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(
            self.start_x,
            self.start_y,
            event.x,
            event.y,
            outline='red',
            width=2,
            dash=(3, 2),
            fill='black'
        )

    def on_button_release(self, event):
        end_x, end_y = event.x, event.y

        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)

        if x2 - x1 < 5 or y2 - y1 < 5:
            try:
                self.snip_tool.destroy()
            except Exception:
                pass
            try:
                self.master.deiconify()
            except Exception:
                pass
            messagebox.showinfo("Bilgi", "Seçim iptal edildi. Çok küçük bir alan seçtiniz.")
            return

        root_x = self.snip_tool.winfo_rootx()
        root_y = self.snip_tool.winfo_rooty()

        screen_x1 = x1 + root_x
        screen_y1 = y1 + root_y
        screen_x2 = x2 + root_x
        screen_y2 = y2 + root_y

        try:
            self.snip_tool.destroy()
        except Exception:
            pass

        monitor = {
            "top": int(screen_y1),
            "left": int(screen_x1),
            "width": int(screen_x2 - screen_x1),
            "height": int(screen_y2 - screen_y1),
        }

        try:
            sct = mss.mss()
            sct_img = sct.grab(monitor)

            img_np = np.array(sct_img)
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)
            img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

            save_path = get_alert_user_path(self.filename)
            cv2.imwrite(save_path, img_gray)
        except Exception as e:
            try:
                self.master.deiconify()
            except Exception:
                pass
            messagebox.showerror("Hata", f"Görsel kaydedilemedi: {e}")
            return

        self.callback(self.filename)


class ColorRegionSelector:
    """
    Bir mod için pencere içi renk tarama alanını seçmek için kullanılan sınıf.
    Sadece ilgili pencerenin alanını karartır.
    """
    def __init__(self, master, callback, region_rect):
        self.master = master
        self.callback = callback
        self.region_rect = region_rect
        self.start_x = None
        self.start_y = None
        self.rect = None

        X1, Y1, X2, Y2 = region_rect
        w = X2 - X1
        h = Y2 - Y1

        self.snip_tool = Toplevel(self.master)
        self.snip_tool.title("Renk Alanı Seçimi")
        self.snip_tool.geometry(f"{w}x{h}+{X1}+{Y1}")
        self.snip_tool.overrideredirect(True)
        self.snip_tool.attributes("-alpha", 0.5)
        self.snip_tool.attributes("-topmost", True)
        self.snip_tool.focus_force()

        self.canvas = tk.Canvas(self.snip_tool, cursor="tcross", bg='black', bd=0, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

        self.snip_tool.bind("<Escape>", self.on_escape)

    def on_escape(self, event=None):
        try:
            self.snip_tool.destroy()
        except Exception:
            pass
        messagebox.showinfo("Bilgi", "Renk alanı seçimi iptal edildi (ESC).")

    def on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect:
            self.canvas.delete(self.rect)

    def on_mouse_drag(self, event):
        self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(
            self.start_x,
            self.start_y,
            event.x,
            event.y,
            outline='yellow',
            width=2,
            dash=(3, 2),
            fill='black'
        )

    def on_button_release(self, event):
        end_x, end_y = event.x, event.y

        x1 = min(self.start_x, end_x)
        y1 = min(self.start_y, end_y)
        x2 = max(self.start_x, end_x)
        y2 = max(self.start_y, end_y)

        if x2 - x1 < 5 or y2 - y1 < 5:
            try:
                self.snip_tool.destroy()
            except Exception:
                pass
            messagebox.showinfo("Bilgi", "Renk alanı seçimi iptal edildi. Çok küçük bir alan.")
            return

        root_x = self.snip_tool.winfo_rootx()
        root_y = self.snip_tool.winfo_rooty()

        screen_x1 = x1 + root_x
        screen_y1 = y1 + root_y
        screen_x2 = x2 + root_x
        screen_y2 = y2 + root_y

        try:
            self.snip_tool.destroy()
        except Exception:
            pass

        self.callback(screen_x1, screen_y1, screen_x2, screen_y2)


# ====================================================================
# D: ANA UYGULAMA SINIFI
# ====================================================================

class AutoClickerApp:
    def __init__(self, master):
        self.master = master
        master.title(f"{GLOBAL_CONFIG['APP_CONFIG']['APP_TITLE']} v{CURRENT_VERSION} (Eş Zamanlı)")

        self.alert_templates = self._load_alert_templates()
        self.next_alert_check_time = 0.0
        self.next_alert_allowed_time = 0.0
        self.paused_until = 0.0

        self.status_text = tk.StringVar(value=GLOBAL_CONFIG['APP_CONFIG']['STATUS_INITIAL_TEXT'])
        self.auto_click_state = tk.BooleanVar(value=True)

        sys_settings = GLOBAL_CONFIG["SYSTEM_SETTINGS"]
        self.stop_on_alert_main = tk.BooleanVar(value=sys_settings.get("stop_on_alert_main", False))
        self.stop_on_tic = tk.BooleanVar(value=sys_settings.get("stop_on_tic", True))
        self.stop_on_message = tk.BooleanVar(value=sys_settings.get("stop_on_message", True))
        self.stop_on_control = tk.BooleanVar(value=sys_settings.get("stop_on_control", True))

        self.mode_status_vars = {}
        self.mode_control_frames = {}
        self.color_region_use_vars = {}

        self.debug_window = None

        # ==== SKILL OTOMASYONU ====
        self.skill_master_var = tk.BooleanVar(value=False)
        self.skill_hava_var = tk.BooleanVar(value=False)   # Hava Kılıcı (4)
        self.skill_ofke_var = tk.BooleanVar(value=False)   # Öfke (3)
        self.skill_common_minutes_var = tk.StringVar(value="3")  # Ortak süre (dk)

        self.skill_manager_thread = None
        self.skill_manager_running = False
        self.skill_sequence_active = False
        self.skill_last_rotation_time = 0.0  # Son skill yakma zamanı

        self.setup_ui()
        master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        for mod_instance in ACTIVE_MOD_INSTANCES:
            mod_instance["is_running"] = False

        self._save_persistent_settings()
        self.master.destroy()
        sys.exit(0)
    
    def toggle_bot(self, mod_instance):
        """Tek bir modu başlat / durdur."""
        app_config = GLOBAL_CONFIG['APP_CONFIG']

        # ÇALIŞTIR
        if not mod_instance.get("is_running"):
            # Bölge seçilmemişse uyar
            if mod_instance.get("region_rect") is None:
                messagebox.showerror(
                    "Hata",
                    f"{mod_instance['title']} için önce Bölge Seç yapın!"
                )
                return

            mod_instance["is_running"] = True
            # Buton görünümü
            if mod_instance.get("start_stop_btn"):
                mod_instance["start_stop_btn"].config(
                    text=app_config['STOP_BUTTON_TEXT'],
                    bg="red"
                )
            # Durum yazısı
            if mod_instance["id"] in self.mode_status_vars:
                self.mode_status_vars[mod_instance["id"]].set("ÇALIŞIYOR")

            # Bot thread’i
            t = Thread(target=self.bot_loop, args=(mod_instance,), daemon=True)
            mod_instance["thread"] = t
            t.start()

            self._update_global_status()
        # DURDUR
        else:
            mod_instance["is_running"] = False
            if mod_instance.get("start_stop_btn"):
                mod_instance["start_stop_btn"].config(
                    text=app_config['START_BUTTON_TEXT'],
                    bg="green"
                )
            if mod_instance["id"] in self.mode_status_vars:
                self.mode_status_vars[mod_instance["id"]].set("DURDURULDU")

            self._update_global_status()


    def _save_persistent_settings(self):
        global ALARM_VOLUME

        saved_instances = []
        for instance in ACTIVE_MOD_INSTANCES:
            saved_instance = instance.copy()
            saved_instance.pop("is_running", None)
            saved_instance.pop("thread", None)
            saved_instance.pop("start_stop_btn", None)
            saved_instance.pop("color_btn", None)
            if isinstance(saved_instance.get("region_rect"), tuple):
                saved_instance["region_rect"] = list(saved_instance["region_rect"])
            if isinstance(saved_instance.get("color_region"), tuple):
                saved_instance["color_region"] = list(saved_instance["color_region"])
            saved_instances.append(saved_instance)

        current_system_settings = GLOBAL_CONFIG.get("SYSTEM_SETTINGS", {})
        current_system_settings["ALARM_VOLUME"] = ALARM_VOLUME
        current_system_settings["stop_on_alert_main"] = self.stop_on_alert_main.get()
        current_system_settings["stop_on_tic"] = self.stop_on_tic.get()
        current_system_settings["stop_on_message"] = self.stop_on_message.get()
        current_system_settings["stop_on_control"] = self.stop_on_control.get()

        GLOBAL_CONFIG["SYSTEM_SETTINGS"] = current_system_settings
        GLOBAL_CONFIG["SAVED_INSTANCES"] = saved_instances

        save_config(GLOBAL_CONFIG)

    def _load_alert_templates(self):
        templates = {}
        for key, p in ALERT_IMAGE_PATHS.items():
            user_path = get_alert_user_path(p)
            if os.path.exists(user_path):
                full_path = user_path
            else:
                full_path = resource_path(p)

            if os.path.exists(full_path):
                t = cv2.imread(full_path, cv2.IMREAD_GRAYSCALE)
                if t is not None:
                    templates[key] = t
        return templates

    def open_settings(self):
        self._save_persistent_settings()
        SettingsWindow(self.master, self)

    def open_debug(self):
        if self.debug_window is not None:
            try:
                if self.debug_window.root.winfo_exists():
                    self.debug_window.root.lift()
                    return
            except Exception:
                self.debug_window = None

        self.debug_window = DebugWindow(self.master)

    def setup_ui(self):
        # Her şeyi temizle
        for widget in self.master.winfo_children():
            widget.destroy()

        app_config = GLOBAL_CONFIG['APP_CONFIG']

        # Üst bar (Debug + Ayarlar)
        top_frame = tk.Frame(self.master)
        top_frame.pack(pady=5, padx=15, fill=tk.X)

        tk.Button(
            top_frame,
            text=app_config['SETTINGS_BUTTON_TEXT'],
            command=self.open_settings,
            bg="light gray",
            width=12
        ).pack(side=tk.RIGHT, padx=(5, 0))

        tk.Button(
            top_frame,
            text="🐞 Debug",
            command=self.open_debug,
            bg="light gray",
            width=10
        ).pack(side=tk.RIGHT)

        # Status
        tk.Label(
            self.master,
            textvariable=self.status_text,
            fg="blue",
            font=('Arial', 10, 'bold')
        ).pack(pady=5, fill=tk.X)

        # Ana Notebook (Tarama / Skill)
        main_notebook = ttk.Notebook(self.master)
        main_notebook.pack(pady=5, padx=10, fill='both', expand=True)

        # === TARMA TAB ===
        modes_tab = ttk.Frame(main_notebook)
        main_notebook.add(modes_tab, text="Tarama")

        modes_container = tk.LabelFrame(
            modes_tab,
            text=app_config['MODES_FRAME_TITLE'],
            padx=10,
            pady=10
        )
        modes_container.pack(side=tk.LEFT, padx=15, pady=10, fill=tk.Y)

        add_frame = tk.Frame(modes_container)
        add_frame.pack(pady=5)

        for key, template in MOD_TEMPLATES.items():
            if GLOBAL_CONFIG.get("MOD_VISIBILITY", {}).get(key, True):
                add_func = lambda k=key, t=template['title']: self.add_new_mod_instance(k, t)
                tk.Button(
                    add_frame,
                    text=f"+ Yeni {template['title']}",
                    command=add_func,
                    bg="yellow",
                    fg="black"
                ).pack(side=tk.LEFT, padx=5)

        self.mod_instances_frame = tk.Frame(modes_container)
        self.mod_instances_frame.pack(pady=10, fill=tk.X)

        tk.Checkbutton(
            modes_container,
            text=app_config['GLOBAL_AUTOCLICK_TEXT'],
            variable=self.auto_click_state
        ).pack(pady=5, anchor='w')

        # Uyuyan mod instance'larını yeniden UI'ye yerleştir
        self.mode_status_vars = {}
        for instance in ACTIVE_MOD_INSTANCES:
            if isinstance(instance.get("region_rect"), list):
                instance["region_rect"] = tuple(instance["region_rect"])
            if isinstance(instance.get("color_region"), list):
                instance["color_region"] = tuple(instance["color_region"])
            if "use_color_region" not in instance:
                instance["use_color_region"] = False
            instance["is_running"] = False
            instance["thread"] = None
            instance["start_stop_btn"] = None
            instance["color_btn"] = None
            self._create_mode_control_frame(self.mod_instances_frame, instance)

        # Sağ tarafta küçük bilgi
        info_frame = tk.Frame(modes_tab)
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        tk.Label(
            info_frame,
            text="Alert / bot durdurma ayarlarını değiştirmek için sağ üstten 'Ayarlar' menüsüne gidin.",
            wraplength=260,
            justify='left',
            fg="gray"
        ).pack(anchor='n', pady=5)

        # === SKILL TAB ===
        skill_tab = ttk.Frame(main_notebook)
        main_notebook.add(skill_tab, text="Skill")

        self._build_skill_ui(skill_tab)

        # Alt kısım: Güncelleme
        tk.Button(
            self.master,
            text=f"{app_config['VERSION_CHECK_TEXT']} (v{CURRENT_VERSION})",
            command=self.start_update_check_thread,
            bg="light blue"
        ).pack(pady=5, fill=tk.X, padx=15)

    # ================== SKILL UI ==================

    def _build_skill_ui(self, parent):
        skill_frame = tk.LabelFrame(parent, text="Skill Otomasyonu", padx=10, pady=10)
        skill_frame.pack(padx=15, pady=10, fill=tk.BOTH, expand=True)

        self.skill_options_frame = skill_frame

        self.skill_master_cb = tk.Checkbutton(
            skill_frame,
            text="Skill Otomasyonunu Aktif Et",
            variable=self.skill_master_var,
            command=self._on_skill_master_toggle
        )
        self.skill_master_cb.pack(anchor='w')

        skill_inner = tk.Frame(skill_frame)
        skill_inner.pack(anchor='w', pady=5)

        self.skill_hava_cb = tk.Checkbutton(
            skill_inner,
            text="Hava Kılıcı (4)",
            variable=self.skill_hava_var
        )
        self.skill_hava_cb.pack(anchor='w')

        self.skill_ofke_cb = tk.Checkbutton(
            skill_inner,
            text="Öfke (3)",
            variable=self.skill_ofke_var
        )
        self.skill_ofke_cb.pack(anchor='w')

        time_frame = tk.Frame(skill_frame)
        time_frame.pack(anchor='w', pady=5)

        tk.Label(time_frame, text="Ortak Süre (dk):").pack(side=tk.LEFT)
        self.skill_minutes_entry = tk.Entry(
            time_frame,
            width=5,
            textvariable=self.skill_common_minutes_var
        )
        self.skill_minutes_entry.pack(side=tk.LEFT, padx=4)

        info_label = tk.Label(
            skill_frame,
            text="Not: Hangi skill işaretliyse hepsi aynı süreyle kullanılacak.\n"
                 "Her aktif mod için sırayla Sağ Tık → CTRL+G → 3/4 → CTRL+G uygulanır.",
            justify="left",
            fg="gray"
        )
        info_label.pack(anchor='w', pady=4)

        self.skill_manual_button = tk.Button(
            skill_frame,
            text="▶ Skillleri Şimdi Kullan",
            command=self.manual_trigger_skills
        )
        self.skill_manual_button.pack(anchor='w', pady=(4, 0))

        self._update_skill_options_visibility()

    def _on_skill_master_toggle(self):
        if self.skill_master_var.get():
            if not self.skill_manager_running:
                self.skill_manager_running = True
                self.skill_manager_thread = Thread(target=self.skill_manager_loop, daemon=True)
                self.skill_manager_thread.start()
        else:
            self.skill_manager_running = False
        self._update_skill_options_visibility()

    def _update_skill_options_visibility(self):
        state = tk.NORMAL if self.skill_master_var.get() else tk.DISABLED
        for widget in [self.skill_hava_cb, self.skill_ofke_cb, self.skill_minutes_entry, self.skill_manual_button]:
            widget.config(state=state)

    def skill_manager_loop(self):
        """
        Skill timer'ını yönetir.
        - Süre dolunca:
          * Aktif modları alır
          * Sırayla her mod için blocker var mı bakar
          * İlk blocker OLMAYAN mod bulunduğunda
            tüm aktif modlar için skill sekansı çalıştırır.
        """
        while self.skill_manager_running:
            try:
                if not self.skill_master_var.get():
                    break

                if not (self.skill_hava_var.get() or self.skill_ofke_var.get()):
                    time.sleep(1.0)
                    continue

                active_mods = [
                    m for m in ACTIVE_MOD_INSTANCES
                    if m.get("is_running") and m.get("region_rect") is not None
                ]
                if not active_mods:
                    time.sleep(1.0)
                    continue

                try:
                    m = float(self.skill_common_minutes_var.get().replace(",", "."))
                    if m <= 0:
                        time.sleep(1.0)
                        continue
                    interval = m * 60.0
                except ValueError:
                    time.sleep(1.0)
                    continue

                now = time.time()

                if self.skill_sequence_active:
                    time.sleep(1.0)
                    continue

                if now - self.skill_last_rotation_time < interval:
                    time.sleep(1.0)
                    continue

                # Süre doldu → blocker kontrolü
                sct = mss.mss()
                triggered = False
                for mod in active_mods:
                    X1, Y1, X2, Y2 = mod["region_rect"]
                    monitor_region = {
                        "top": Y1,
                        "left": X1,
                        "width": X2 - X1,
                        "height": Y2 - Y1
                    }

                    no_blocker = True
                    if mod.get("blocker_path"):
                        try:
                            no_blocker = not self.check_blocker(sct, mod, monitor_region)
                        except Exception:
                            no_blocker = True

                    if no_blocker:
                        Thread(
                            target=self.run_skill_rotation_for_all_active_mods,
                            daemon=True
                        ).start()
                        triggered = True
                        break

                if triggered:
                    time.sleep(1.0)
                else:
                    time.sleep(3.0)

            except Exception:
                time.sleep(1.0)

        self.skill_manager_running = False

    def manual_trigger_skills(self):
        """Timer beklemeden skill rotasyonunu tek seferlik çalıştır."""
        if self.skill_sequence_active:
            self.status_text.set("Skill sekansı zaten çalışıyor.")
            return

        if not (self.skill_hava_var.get() or self.skill_ofke_var.get()):
            self.status_text.set("Skill yok: Hava veya Öfke işaretli değil.")
            return

        active_mods = [
            m for m in ACTIVE_MOD_INSTANCES
            if m.get("is_running") and m.get("region_rect") is not None
        ]
        if not active_mods:
            self.status_text.set("Aktif mod yok: En az bir mod başlatmalısınız.")
            return

        t = Thread(target=self.run_skill_rotation_for_all_active_mods, daemon=True)
        t.start()

    def run_skill_rotation_for_all_active_mods(self):
        """Aktif tüm modlar için sırayla skill sekansı uygular (tarama thread'lerini öldürmeden)."""
        if self.skill_sequence_active:
            return

        keys_to_press = []
        if self.skill_ofke_var.get():
            keys_to_press.append('3')
        if self.skill_hava_var.get():
            keys_to_press.append('4')

        if not keys_to_press:
            return

        active_mods = [
            m for m in ACTIVE_MOD_INSTANCES
            if m.get("is_running") and m.get("region_rect") is not None
        ]
        if not active_mods:
            return

        self.skill_sequence_active = True
        try:
            for mod in active_mods:
                self.run_skill_sequence_for_mod(mod, keys_to_press)
                time.sleep(0.1)

            self.skill_last_rotation_time = time.time()
        finally:
            self.skill_sequence_active = False

    def run_skill_sequence_for_mod(self, mod_instance, keys_to_press):
        """Tek bir mod için: sağ tık → CTRL+G → skill tuşları → CTRL+G (pynput ile)."""
        try:
            region = mod_instance.get("region_rect")
            if not region:
                return

            X1, Y1, X2, Y2 = region
            cx = int((X1 + X2) / 2)
            cy = int((Y1 + Y2) / 2)

            try:
                pyautogui.moveTo(cx, cy, duration=0.1)
                pyautogui.click(cx, cy, button='right')
                time.sleep(0.2)
            except Exception:
                pass

            press_ctrl_g()
            time.sleep(1.0)

            for key in keys_to_press:
                press_char_key(key)
                time.sleep(3.0)

            press_ctrl_g()
            time.sleep(0.3)

        except Exception:
            pass

    # ================== MOD YÖNETİMİ ==================

    def add_new_mod_instance(self, mod_key, mod_title):
        template = MOD_TEMPLATES[mod_key]
        instance_id = str(uuid.uuid4())
        instance_count = len([m for m in ACTIVE_MOD_INSTANCES if m['mod_key'] == mod_key]) + 1

        new_instance = {
            "id": instance_id,
            "mod_key": mod_key,
            "title": f"{mod_title} #{instance_count}",
            "lower_color": template["lower_color"].tolist(),
            "upper_color": template["upper_color"].tolist(),
            "region_rect": None,
            "min_area": template["min_area"],
            "blocker_path": template["blocker_path"],
            "color_region": None,
            "use_color_region": False,
            "is_running": False,
            "thread": None,
            "start_stop_btn": None,
            "color_btn": None
        }

        ACTIVE_MOD_INSTANCES.append(new_instance)
        self._create_mode_control_frame(self.mod_instances_frame, new_instance)
        self.master.update_idletasks()

    def _create_mode_control_frame(self, parent, mod_instance):
        if mod_instance["id"] in self.mode_control_frames:
            return

        app_config = GLOBAL_CONFIG['APP_CONFIG']

        frame = tk.LabelFrame(parent, text=mod_instance["title"], padx=5, pady=5)
        frame.pack(pady=5, fill=tk.X)
        self.mode_control_frames[mod_instance["id"]] = frame

        initial_status = "Bölge Seçildi" if mod_instance["region_rect"] else "Bölge Seçilmeli"
        status_var = tk.StringVar(value=initial_status)
        self.mode_status_vars[mod_instance["id"]] = status_var
        tk.Label(frame, textvariable=status_var, fg="dark green").pack(anchor='w')

        btn_frame = tk.Frame(frame)
        btn_frame.pack(pady=5)

        start_stop_func = lambda m=mod_instance: self.toggle_bot(m)
        start_stop_btn = tk.Button(
            btn_frame,
            text=app_config['START_BUTTON_TEXT'],
            command=start_stop_func,
            bg="green",
            fg="white"
        )
        start_stop_btn.pack(side=tk.LEFT, padx=5)
        mod_instance["start_stop_btn"] = start_stop_btn

        region_func = lambda m=mod_instance: self.trigger_delayed_scan_region(m)
        tk.Button(btn_frame, text=app_config['REGION_BUTTON_TEXT'], command=region_func).pack(side=tk.LEFT, padx=5)

        use_var = tk.BooleanVar(value=mod_instance.get("use_color_region", False))
        self.color_region_use_vars[mod_instance["id"]] = use_var

        color_region_func = lambda m=mod_instance: self.trigger_color_region_selection(m)
        color_btn = tk.Button(btn_frame, text="Renk Alanı Seç", command=color_region_func)
        mod_instance["color_btn"] = color_btn

        def on_use_color_toggle(m=mod_instance, var=use_var, btn=color_btn):
            m["use_color_region"] = var.get()
            if var.get():
                btn.pack(side=tk.LEFT, padx=5)
            else:
                btn.pack_forget()
                m["color_region"] = None

        chk = tk.Checkbutton(
            frame,
            text="Renk alanını kısıtla",
            variable=use_var,
            command=on_use_color_toggle
        )
        chk.pack(anchor='w')

        if use_var.get():
            color_btn.pack(side=tk.LEFT, padx=5)

        remove_func = lambda m=mod_instance: self.remove_mod_instance(m)
        tk.Button(btn_frame, text="X Kaldır", command=remove_func, bg="orange").pack(side=tk.LEFT, padx=15)

    def remove_mod_instance(self, mod_instance):
        if mod_instance.get("is_running"):
            self.toggle_bot(mod_instance)

        if messagebox.askyesno("Onay", f"'{mod_instance['title']}' modunu kaldırmak istediğinizden emin misiniz?"):
            frame = self.mode_control_frames.pop(mod_instance["id"], None)
            if frame:
                frame.destroy()

            if mod_instance in ACTIVE_MOD_INSTANCES:
                ACTIVE_MOD_INSTANCES.remove(mod_instance)

            self._update_global_status()
            self._save_persistent_settings()

    def _update_global_status(self):
        active_count = sum(1 for conf in ACTIVE_MOD_INSTANCES if conf.get("is_running"))
        if active_count > 0:
            self.status_text.set(
                f"{active_count} mod aktif. Global Tıklama: {'AÇIK' if self.auto_click_state.get() else 'KAPALI'}"
            )
        else:
            self.status_text.set(GLOBAL_CONFIG['APP_CONFIG']['STATUS_INITIAL_TEXT'])

    def trigger_delayed_scan_region(self, mod_instance):
        self.status_text.set("3 saniye içinde taramak istediğiniz pencereye tıklayın/geçin...")
        self.master.update()
        self.master.after(3000, lambda: self.update_scan_region(mod_instance))

    def update_scan_region(self, mod_instance):
        r = get_active_window_rect()

        if r:
            mod_instance["region_rect"] = r
            X1, Y1, X2, Y2 = r

            pyautogui.FAILSAFE = False
            try:
                pyautogui.moveTo(X1 + 10, Y1 + 10, duration=0.1)
                pyautogui.dragTo(X2 - 10, Y2 - 10, duration=0.5, button='right')
            except Exception:
                pass
            pyautogui.FAILSAFE = True

            self.status_text.set(f"{mod_instance['title']} için tarama bölgesi ayarlandı.")
            self.mode_status_vars[mod_instance["id"]].set("Bölge Seçildi")
            self._save_persistent_settings()
        else:
            self.status_text.set("Hata: Aktif pencere bulunamadı. Lütfen tekrar deneyin.")

    def trigger_color_region_selection(self, mod_instance):
        if mod_instance.get("region_rect") is None:
            messagebox.showerror("Hata", "Önce pencere bölgesini (Bölge Seç) belirleyin.")
            return

        if not mod_instance.get("use_color_region", False):
            messagebox.showinfo("Bilgi", "Önce 'Renk alanını kısıtla' kutusunu işaretleyin.")
            return

        ColorRegionSelector(
            self.master,
            callback=lambda x1, y1, x2, y2, m=mod_instance: self._color_region_selected(m, x1, y1, x2, y2),
            region_rect=mod_instance["region_rect"]
        )

    def _color_region_selected(self, mod_instance, sx1, sy1, sx2, sy2):
        X1, Y1, X2, Y2 = mod_instance["region_rect"]

        sx1 = max(X1, min(sx1, X2 - 1))
        sx2 = max(X1 + 1, min(sx2, X2))
        sy1 = max(Y1, min(sy1, Y2 - 1))
        sy2 = max(Y1 + 1, min(sy2, Y2))

        rel_left = sx1 - X1
        rel_top = sy1 - Y1
        width = sx2 - sx1
        height = sy2 - sy1

        color_region_tuple = (rel_left, rel_top, width, height)
        mod_instance["color_region"] = color_region_tuple
        self.status_text.set(f"{mod_instance['title']} için renk alanı seçildi.")
        self._save_persistent_settings()

    def _check_alert_and_action(self, gray):
        now = time.time()
        if now < self.next_alert_allowed_time:
            return False

        alert_checks = {
            "tic": self.stop_on_tic.get(),
            "message": self.stop_on_message.get(),
            "control": self.stop_on_control.get()
        }

        found_alert_for_stop = False

        for key, template in self.alert_templates.items():
            res = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
            _, mv, _, _ = cv2.minMaxLoc(res)

            if mv >= ALERT_THRESHOLD:
                self.master.after(0, lambda k=key: self.status_text.set(
                    f"!!! KRİTİK ALERT !!! {k.upper()}.png bulundu!"
                ))
                play_alert_sound()
                self.next_alert_allowed_time = now + ALERT_COOLDOWN

                if self.stop_on_alert_main.get() and alert_checks.get(key, False):
                    self.master.after(0, self.stop_all_bots)
                    found_alert_for_stop = True
                    break

                self.paused_until = now + PAUSE_ON_ALERT_SECONDS
                break

        return found_alert_for_stop

    def stop_all_bots(self):
        app_config = GLOBAL_CONFIG['APP_CONFIG']
        for mod_instance in ACTIVE_MOD_INSTANCES:
            if mod_instance.get("is_running"):
                mod_instance["is_running"] = False

                self.master.after(
                    0,
                    lambda m=mod_instance: m["start_stop_btn"].config(
                        text=app_config['START_BUTTON_TEXT'],
                        bg="green"
                    )
                )
                self.master.after(
                    0,
                    lambda m=mod_instance: self.mode_status_vars[m["id"]].set("KRİTİK HATA")
                )

        self.master.after(0, lambda: self.status_text.set("KRİTİK ALERT: Tüm botlar kapatıldı."))
        self.master.after(0, self._update_global_status)

    def check_blocker(self, sct, mod_instance, monitor_region):
        mod_key = mod_instance.get("mod_key")
        if not mod_key:
            return False

        user_blocker_name = f"{mod_key.lower()}Blocker.jpg"
        user_blocker_path = get_alert_user_path(user_blocker_name)
        full_blocker_path = None

        if os.path.exists(user_blocker_path):
            full_blocker_path = user_blocker_path
        else:
            blocker_path = mod_instance.get("blocker_path")
            if not blocker_path:
                return False
            full_blocker_path = resource_path(blocker_path)

        blocker_template = cv2.imread(full_blocker_path, cv2.IMREAD_GRAYSCALE)
        if blocker_template is None:
            return False

        img = sct.grab(monitor_region)
        f = cv2.cvtColor(np.array(img), cv2.COLOR_BGRA2BGR)
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)

        res = cv2.matchTemplate(g, blocker_template, cv2.TM_CCOEFF_NORMED)
        _, mv, _, _ = cv2.minMaxLoc(res)

        return mv >= mod_instance.get("blocker_threshold", 0.70)

    def bot_loop(self, mod_instance):
        sct = mss.mss()

        X1, Y1, X2, Y2 = mod_instance["region_rect"]
        monitor_region = {"top": Y1, "left": X1, "width": X2 - X1, "height": Y2 - Y1}

        LOWER_COLOR = np.array(mod_instance["lower_color"])
        UPPER_COLOR = np.array(mod_instance["upper_color"])
        MIN_AREA = mod_instance["min_area"]

        action_due = True
        next_blocker_check_time = 0.0

        while mod_instance.get("is_running"):
            loop_start_time = time.time()

            if self.skill_sequence_active:
                time.sleep(TARGET_FRAME_TIME)
                continue

            try:
                img = sct.grab(monitor_region)
                frame = cv2.cvtColor(np.array(img), cv2.COLOR_BGRA2BGR)
                hsv_full = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                gray_full = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                if time.time() >= self.next_alert_check_time:
                    if self._check_alert_and_action(gray_full):
                        break
                    self.next_alert_check_time = time.time() + ALERT_CHECK_INTERVAL

                now = time.time()
                paused = now < self.paused_until

                if paused:
                    time.sleep(TARGET_FRAME_TIME)
                    continue

                h_full, w_full = frame.shape[:2]

                use_color = mod_instance.get("use_color_region", False)
                color_region = mod_instance.get("color_region") if use_color else None

                if color_region:
                    rel_left, rel_top, c_w, c_h = color_region

                    rel_left = int(max(0, min(rel_left, w_full - 1)))
                    rel_top = int(max(0, min(rel_top, h_full - 1)))
                    c_w = int(max(1, min(c_w, w_full - rel_left)))
                    c_h = int(max(1, min(c_h, h_full - rel_top)))

                    hsv = hsv_full[rel_top:rel_top + c_h, rel_left:rel_left + c_w]
                    detect_offset_x = rel_left
                    detect_offset_y = rel_top
                    region_cx_local = c_w / 2
                    region_cy_local = c_h / 2
                else:
                    hsv = hsv_full
                    detect_offset_x = 0
                    detect_offset_y = 0
                    region_cx_local = w_full / 2
                    region_cy_local = h_full / 2

                mask = cv2.inRange(hsv, LOWER_COLOR, UPPER_COLOR)
                k = np.ones((3, 3), np.uint8)
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)

                merge_kernel = np.ones((15, 15), np.uint8)
                mask_merged = cv2.dilate(mask, merge_kernel, iterations=2)
                mask_merged = cv2.erode(mask_merged, merge_kernel, iterations=1)
                contours, _ = cv2.findContours(mask_merged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                candidate = []
                for cnt in contours:
                    area = cv2.contourArea(cnt)
                    if area >= MIN_AREA:
                        x, y, w, h = cv2.boundingRect(cnt)
                        candidate.append((x, y, w, h))

                best = None
                if candidate:
                    best_dist = float('inf')
                    for (x, y, w, h) in candidate:
                        cx = x + w / 2
                        cy = y + h / 2
                        d = (cx - region_cx_local) ** 2 + (cy - region_cy_local) ** 2
                        if d < best_dist:
                            best_dist = d
                            best = (x, y, w, h, cx, cy)

                if mod_instance.get("blocker_path") and not action_due and now >= next_blocker_check_time:
                    blocker_present = self.check_blocker(sct, mod_instance, monitor_region)
                    if not blocker_present:
                        action_due = True
                    else:
                        next_blocker_check_time = now + 3.0

                if best and action_due:
                    x, y, w, h, cx_local, cy_local = best
                    cx_global = detect_offset_x + cx_local
                    cy_global = detect_offset_y + cy_local

                    sx = int(X1 + cx_global)
                    sy = int(Y1 + cy_global)

                    pyautogui.moveTo(sx, sy)

                    if self.auto_click_state.get():
                        pyautogui.click()
                        self.master.after(
                            0,
                            lambda m=mod_instance: self.status_text.set(f"Tıklandı: {m['title']}")
                        )
                    else:
                        self.master.after(
                            0,
                            lambda m=mod_instance: self.status_text.set(f"Taşındı: {m['title']}")
                        )

                    if mod_instance.get("blocker_path"):
                        action_due = False
                        next_blocker_check_time = now + 3.0
                    else:
                        action_due = True

            except Exception:
                pass

            elapsed_time = time.time() - loop_start_time
            sleep_time = TARGET_FRAME_TIME - elapsed_time
            if sleep_time > 0:
                time.sleep(sleep_time)

        if not self.master.winfo_exists():
            return

        status = "HATA" if mod_instance.get("is_running") else "DURDURULDU"

        if mod_instance["id"] in self.mode_status_vars:
            self.master.after(0, lambda: self.mode_status_vars[mod_instance["id"]].set(status))

        self.master.after(0, self._update_global_status)

    # ====================================================================
    # E: GÜNCELLEME
    # ====================================================================

    def start_update_check_thread(self):
        self.status_text.set("Güncellemeler kontrol ediliyor...")
        self.master.update_idletasks()
        Thread(target=self._check_for_updates, daemon=True).start()

    def _check_for_updates(self):
        try:
            response = requests.get(VERSION_CHECK_URL, timeout=5)
            response.raise_for_status()
            latest_info = response.json()

            latest_version = latest_info["latest_version"]
            download_url = latest_info["download_url"]

            if latest_version > CURRENT_VERSION:
                self.master.after(0, lambda: self._prompt_and_download(latest_version, download_url))
            else:
                self.status_text.set(f"Zaten en son sürüme sahipsiniz. (v{CURRENT_VERSION})")

        except requests.RequestException:
            self.status_text.set("Güncelleme kontrolü başarısız oldu. İnternet veya URL'yi kontrol edin.")

    def _prompt_and_download(self, version, url):
        if messagebox.askyesno(
            "Güncelleme Mevcut",
            f"Yeni sürüm v{version} mevcut. İndirip uygulamak ister misiniz? (Uygulama yeniden başlatılacaktır)"
        ):
            self.status_text.set("Güncelleme İndiriliyor...")
            Thread(target=self._download_and_install_update, args=(url, version), daemon=True).start()

    def _download_and_install_update(self, url, version):
        try:
            base_dir = os.path.dirname(os.path.abspath(sys.executable))
            zip_name = f"update_{version}.zip"
            temp_zip_path = os.path.join(base_dir, zip_name)
            batch_path = os.path.join(base_dir, "update_installer.bat")

            r = requests.get(url, stream=True, timeout=15)
            r.raise_for_status()

            with open(temp_zip_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            with open(temp_zip_path, "rb") as check:
                sig = check.read(2)

            if sig != b"PK":
                messagebox.showerror(
                    "Güncelleme Hatası",
                    "İndirilen dosya ZIP formatında değil (ilk byte'lar 'PK' değil).\n"
                    "Muhtemelen GitHub RAW linki HTML hata sayfası döndürdü."
                )
                self.status_text.set("ZIP hatalı, güncelleme iptal edildi.")
                try:
                    os.remove(temp_zip_path)
                except Exception:
                    pass
                return

            self.status_text.set("İndirme tamamlandı. Kurulum hazırlanıyor...")
            self.master.update_idletasks()

            script_content = f"""@echo off
echo Kurulum Baslatiliyor...
cd /d "%~dp0"
echo Calisma klasoru: %CD%

set ZIP_NAME={zip_name}
set NEW_EXE={NEW_EXE_FILENAME}

set TEMP_DIR=update_%RANDOM%_%RANDOM%
mkdir "%TEMP_DIR%"

echo Arsiv cikartiliyor: %ZIP_NAME% -> %TEMP_DIR%
powershell -NoLogo -NoProfile -Command "try {{ Expand-Archive -LiteralPath '%ZIP_NAME%' -DestinationPath '%TEMP_DIR%' -Force; exit 0 }} catch {{ Write-Host 'PowerShell Hata:' $_.Exception.Message; exit 1 }}"

echo Expand-Archive cikis kodu: %ERRORLEVEL%
if %ERRORLEVEL% NEQ 0 (
    echo HATA: Expand-Archive sirasinda hata olustu.
    goto CLEANUP
)

if not exist "%TEMP_DIR%\\%NEW_EXE%" (
    echo HATA: %TEMP_DIR% klasorunde %NEW_EXE% bulunamadi.
    goto CLEANUP
)

echo Eski exe uzerine yazmak icin bekleniyor...
timeout /t 2 /nobreak >nul

echo Yeni exe tasiniyor...
move /Y "%TEMP_DIR%\\%NEW_EXE%" "%NEW_EXE%"

if %ERRORLEVEL% NEQ 0 (
    echo HATA: %NEW_EXE% uzerine yazilamadi (dosya kilitli olabilir).
    goto CLEANUP
)

:CLEANUP
echo Gecici klasor/dosya temizleniyor...
if exist "%TEMP_DIR%\\" rmdir /s /q "%TEMP_DIR%"
if exist "%TEMP_DIR%" del /f /q "%TEMP_DIR%"

echo Zip dosyasi siliniyor...
if exist "%ZIP_NAME%" del /f /q "%ZIP_NAME%"

echo Yeni exe baslatiliyor (varsa)...
if exist "%NEW_EXE%" start "" "%NEW_EXE%"

echo.
echo --- GUNCELLEYICI BITTI ---
echo Konsolu kapatmak icin bir tusa basin...
pause >nul
"""

            with open(batch_path, "w", encoding="utf-8") as f:
                f.write(script_content)

            subprocess.Popen(
                [batch_path],
                cwd=base_dir,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )

            self.master.quit()

        except Exception as e:
            self.status_text.set("Güncelleme/Kurulum sırasında kritik hata oluştu.")
            messagebox.showerror("Hata", f"Güncelleme başarısız oldu: {e}")
            self.status_text.set(f"Güncelleme Başarısız. (v{CURRENT_VERSION})")


# ====================================================================
# F: AYARLAR PENCERESİ
# ====================================================================

class SettingsWindow:
    def __init__(self, master, app_instance):
        global ALARM_VOLUME
        self.app = app_instance
        self.settings_root = Toplevel(master)
        self.settings_root.title("Gelişmiş Ayarlar")
        self.settings_root.geometry("520x560")
        self.settings_root.transient(master)
        self.settings_root.grab_set()

        self.master = master
        self.current_config = GLOBAL_CONFIG.copy()

        self.local_volume_value = tk.DoubleVar(value=ALARM_VOLUME)

        tk.Button(
            self.settings_root,
            text="Ayarları Kaydet ve Kapat",
            command=self._save_and_close,
            bg="red",
            fg="white",
            font=('Arial', 10, 'bold'),
            width=25
        ).pack(pady=10)

        self.notebook = ttk.Notebook(self.settings_root)
        self.notebook.pack(pady=5, padx=10, fill='both', expand=True)

        self._create_general_settings_tab()
        self._create_image_settings_tab()

    def _create_general_settings_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text='Genel Ayarlar')

        # Ses
        volume_frame = tk.LabelFrame(tab, text="Alarm Ses Seviyesi (0-100)", padx=10, pady=5)
        volume_frame.pack(pady=10, fill=tk.X, padx=10)

        self.volume_scale = Scale(
            volume_frame,
            from_=0,
            to=100,
            orient=HORIZONTAL,
            length=350,
            command=self._update_volume_setting
        )
        self.volume_scale.set(int(self.local_volume_value.get() * 100))
        self.volume_scale.pack()

        # Mod görünürlüğü
        visibility_frame = tk.LabelFrame(tab, text="Ana Sayfada Gösterilecek Yeni Mod Butonları", padx=10, pady=5)
        visibility_frame.pack(pady=10, fill=tk.X, padx=10)

        self.visibility_vars = {}
        for mod_key, conf in MOD_TEMPLATES.items():
            is_visible = self.current_config.get("MOD_VISIBILITY", {}).get(mod_key, True)
            var = tk.BooleanVar(value=is_visible)
            self.visibility_vars[mod_key] = var
            tk.Checkbutton(visibility_frame, text=conf["title"], variable=var).pack(anchor='w')

        # Alert / Bot durdurma
        alert_frame = tk.LabelFrame(tab, text="Alert ve Bot Durdurma Ayarları", padx=10, pady=5)
        alert_frame.pack(pady=10, fill=tk.X, padx=10)

        tk.Checkbutton(
            alert_frame,
            text="Alert Bulunduğunda Bot Durdurulsun",
            variable=self.app.stop_on_alert_main
        ).pack(anchor='w')

        sub_frame = tk.Frame(alert_frame)
        sub_frame.pack(anchor='w', padx=20, pady=5)

        alert_texts = GLOBAL_CONFIG.get("ALERT_TEXTS", {})
        tk.Checkbutton(
            sub_frame,
            text=alert_texts.get("tic", "Tic (Kritik) Bulunursa"),
            variable=self.app.stop_on_tic
        ).pack(anchor='w')
        tk.Checkbutton(
            sub_frame,
            text=alert_texts.get("message", "Message (Kritik) Bulunursa"),
            variable=self.app.stop_on_message
        ).pack(anchor='w')
        tk.Checkbutton(
            sub_frame,
            text=alert_texts.get("control", "Control (Kritik) Bulunursa"),
            variable=self.app.stop_on_control
        ).pack(anchor='w')

    def _create_image_settings_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text='Görsel Ayarları')

        tk.Label(
            tab,
            text=(
                "Alert görsellerini ve mod blocker görsellerini buradan yeniden yakalayabilirsiniz.\n"
                "(Dosyalar AppData içinde saklanır, güncellemelerden etkilenmez.)"
            ),
            wraplength=430
        ).pack(pady=10)

        # Alert görselleri
        alert_frame = tk.LabelFrame(tab, text="Alert Görselleri", padx=10, pady=5)
        alert_frame.pack(pady=5, fill=tk.X, padx=10)

        alert_texts = GLOBAL_CONFIG.get("ALERT_TEXTS", {})

        self._create_image_setting_button(alert_frame, "tic.png", alert_texts.get("tic", "Tic Görseli"))
        self._create_image_setting_button(alert_frame, "message.png", alert_texts.get("message", "Message Görseli"))
        self._create_image_setting_button(alert_frame, "control.png", alert_texts.get("control", "Control Görseli"))

        # Mod Blocker görselleri
        blocker_frame = tk.LabelFrame(tab, text="Mod Blocker Görselleri", padx=10, pady=5)
        blocker_frame.pack(pady=10, fill=tk.X, padx=10)

        for mod_key, conf in MOD_TEMPLATES.items():
            self._create_blocker_setting_button(blocker_frame, mod_key, conf["title"])

    def _create_blocker_setting_button(self, parent_frame, mod_key, title_text):
        filename = f"{mod_key.lower()}Blocker.jpg"
        btn_func = lambda f=filename: self.start_blocker_area_selection(f)
        tk.Button(
            parent_frame,
            text=f"📷 {title_text} Blocker",
            command=btn_func
        ).pack(pady=3, fill=tk.X)

    def _update_volume_setting(self, value):
        volume = float(value) / 100.0
        self.local_volume_value.set(volume)

    def _create_image_setting_button(self, parent_frame, filename, text):
        btn_func = lambda f=filename: self.start_area_selection(f)
        tk.Button(parent_frame, text=f"📷 {text}", command=btn_func).pack(pady=3, fill=tk.X)

    def start_area_selection(self, filename):
        try:
            self.settings_root.grab_release()
        except Exception:
            pass
        self.settings_root.withdraw()
        AreaSelector(self.settings_root, self._alert_capture_completed, filename)

    def start_blocker_area_selection(self, filename):
        try:
            self.settings_root.grab_release()
        except Exception:
            pass
        self.settings_root.withdraw()
        AreaSelector(self.settings_root, self._blocker_capture_completed, filename)

    def _alert_capture_completed(self, filename):
        try:
            self.settings_root.deiconify()
            self.settings_root.grab_set()
        except Exception:
            pass

        self.app.alert_templates = self.app._load_alert_templates()
        messagebox.showinfo("Başarılı", f"'{filename}' alert görseli başarıyla güncellendi ve kaydedildi.")

    def _blocker_capture_completed(self, filename):
        try:
            self.settings_root.deiconify()
            self.settings_root.grab_set()
        except Exception:
            pass

        messagebox.showinfo("Başarılı", f"'{filename}' blocker görseli başarıyla güncellendi ve kaydedildi.")

    def _save_and_close(self):
        global ALARM_VOLUME

        # Mod görünürlüğü
        for mod_key, var in self.visibility_vars.items():
            self.current_config["MOD_VISIBILITY"][mod_key] = var.get()

        # Ses
        new_volume = self.local_volume_value.get()
        self.current_config["SYSTEM_SETTINGS"]["ALARM_VOLUME"] = new_volume
        ALARM_VOLUME = new_volume

        # Alert ayarları
        self.current_config["SYSTEM_SETTINGS"]["stop_on_alert_main"] = self.app.stop_on_alert_main.get()
        self.current_config["SYSTEM_SETTINGS"]["stop_on_tic"] = self.app.stop_on_tic.get()
        self.current_config["SYSTEM_SETTINGS"]["stop_on_message"] = self.app.stop_on_message.get()
        self.current_config["SYSTEM_SETTINGS"]["stop_on_control"] = self.app.stop_on_control.get()

        if save_config(self.current_config):
            messagebox.showinfo("Başarılı", "Ayarlar kaydedildi. Arayüz yeniden çiziliyor.")
        else:
            messagebox.showerror("Hata", "Ayarlar kaydedilemedi! persistent_settings.json yazılabilir mi?")

        self.app.setup_ui()

        self.settings_root.destroy()
        self.app.master.grab_release()


# ====================================================================
# H: DEBUG PENCERESİ
# ====================================================================

class DebugWindow:
    def __init__(self, master):
        self.master = master
        self.root = Toplevel(master)
        self.root.title("Debug - HSV Canlı Görüntü")
        self.root.geometry("360x330")
        self.root.resizable(False, False)

        self.debug_region_rect = None
        self.debug_running = False
        self.debug_thread = None

        self.lower_h_var = tk.StringVar(value="0")
        self.lower_s_var = tk.StringVar(value="150")
        self.lower_v_var = tk.StringVar(value="150")

        self.upper_h_var = tk.StringVar(value="10")
        self.upper_s_var = tk.StringVar(value="255")
        self.upper_v_var = tk.StringVar(value="255")

        self.min_area_var = tk.StringVar(value="80")

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self):
        tk.Label(
            self.root,
            text="1) 3 sn içinde pencere seç\n2) HSV aralığı ve min area gir\n3) Debug Başlat",
            justify="left"
        ).pack(pady=5)

        self.region_label = tk.Label(self.root, text="Bölge: Henüz seçilmedi", fg="red")
        self.region_label.pack(pady=2)

        tk.Button(
            self.root,
            text="Bölge Seç (3 sn)",
            command=self.trigger_debug_region
        ).pack(pady=5)

        hsv_frame = tk.LabelFrame(self.root, text="HSV Aralığı", padx=5, pady=5)
        hsv_frame.pack(pady=5, fill=tk.X, padx=10)

        lower_row = tk.Frame(hsv_frame)
        lower_row.pack(anchor='w', pady=2)
        tk.Label(lower_row, text="Alt (H,S,V):").pack(side=tk.LEFT)
        tk.Entry(lower_row, width=4, textvariable=self.lower_h_var).pack(side=tk.LEFT, padx=2)
        tk.Entry(lower_row, width=4, textvariable=self.lower_s_var).pack(side=tk.LEFT, padx=2)
        tk.Entry(lower_row, width=4, textvariable=self.lower_v_var).pack(side=tk.LEFT, padx=2)

        upper_row = tk.Frame(hsv_frame)
        upper_row.pack(anchor='w', pady=2)
        tk.Label(upper_row, text="Üst (H,S,V): ").pack(side=tk.LEFT)
        tk.Entry(upper_row, width=4, textvariable=self.upper_h_var).pack(side=tk.LEFT, padx=2)
        tk.Entry(upper_row, width=4, textvariable=self.upper_s_var).pack(side=tk.LEFT, padx=2)
        tk.Entry(upper_row, width=4, textvariable=self.upper_v_var).pack(side=tk.LEFT, padx=2)

        area_frame = tk.Frame(self.root)
        area_frame.pack(pady=5)
        tk.Label(area_frame, text="Min Area:").pack(side=tk.LEFT)
        tk.Entry(area_frame, width=6, textvariable=self.min_area_var).pack(side=tk.LEFT, padx=3)

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Debug Başlat", command=self.start_debug).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Debug Durdur", command=self.stop_debug).pack(side=tk.LEFT, padx=5)

    def trigger_debug_region(self):
        self.region_label.config(text="Bölge: 3 sn içinde hedef pencereye geç...", fg="orange")
        self.root.update()
        self.root.after(3000, self._set_debug_region)

    def _set_debug_region(self):
        r = get_active_window_rect()
        if r:
            self.debug_region_rect = r
            self.region_label.config(text=f"Bölge: {r}", fg="green")
        else:
            self.region_label.config(text="Bölge: Aktif pencere bulunamadı", fg="red")

    def _get_params(self):
        try:
            lh = int(self.lower_h_var.get())
            ls = int(self.lower_s_var.get())
            lv = int(self.lower_v_var.get())
            uh = int(self.upper_h_var.get())
            us = int(self.upper_s_var.get())
            uv = int(self.upper_v_var.get())
            min_area = int(self.min_area_var.get())
        except ValueError:
            lh, ls, lv = 0, 0, 0
            uh, us, uv = 179, 255, 255
            min_area = 80

        lh = max(0, min(179, lh))
        uh = max(0, min(179, uh))
        ls = max(0, min(255, ls))
        us = max(0, min(255, us))
        lv = max(0, min(255, lv))
        uv = max(0, min(255, uv))
        min_area = max(1, min_area)

        lower = np.array([lh, ls, lv], dtype=np.uint8)
        upper = np.array([uh, us, uv], dtype=np.uint8)
        return lower, upper, min_area

    def start_debug(self):
        if self.debug_running:
            return
        if self.debug_region_rect is None:
            messagebox.showinfo("Bilgi", "Önce bir bölge seçmelisiniz.")
            return

        self.debug_running = True
        self.debug_thread = Thread(target=self.debug_loop, daemon=True)
        self.debug_thread.start()

    def stop_debug(self):
        self.debug_running = False
        try:
            cv2.destroyWindow("Debug Preview")
        except Exception:
            pass

    def debug_loop(self):
        sct = mss.mss()

        while self.debug_running:
            r = self.debug_region_rect
            if not r:
                time.sleep(0.1)
                continue

            X1, Y1, X2, Y2 = r
            monitor = {"top": Y1, "left": X1, "width": X2 - X1, "height": Y2 - Y1}

            try:
                img = sct.grab(monitor)
                frame = cv2.cvtColor(np.array(img), cv2.COLOR_BGRA2BGR)
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

                lower, upper, min_area = self._get_params()

                mask = cv2.inRange(hsv, lower, upper)
                k = np.ones((3, 3), np.uint8)
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)

                merge_kernel = np.ones((15, 15), np.uint8)
                mask_merged = cv2.dilate(mask, merge_kernel, iterations=2)
                mask_merged = cv2.erode(mask_merged, merge_kernel, iterations=1)

                contours, _ = cv2.findContours(mask_merged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                vis = frame.copy()
                for cnt in contours:
                    area = cv2.contourArea(cnt)
                    if area >= min_area:
                        x, y, w, h = cv2.boundingRect(cnt)
                        cv2.rectangle(vis, (x, y), (x + w, y + h), (0, 0, 255), 2)

                cv2.imshow("Debug Preview", vis)
                cv2.waitKey(1)

            except Exception:
                pass

            time.sleep(0.05)

        try:
            cv2.destroyWindow("Debug Preview")
        except Exception:
            pass

    def on_close(self):
        self.stop_debug()
        self.root.destroy()


# ====================================================================
# G: UYGULAMA BAŞLANGICI
# ====================================================================

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = AutoClickerApp(root)
        root.mainloop()
    except Exception as e:
        print(f"Uygulama başlatma hatası: {e}")
