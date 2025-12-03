# filename: milen_auto_clicker.py
# -*- coding: utf-8 -*-

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
import re
import threading

from PIL import Image, ImageTk
import easyocr

pyautogui.FAILSAFE = False

# ================== GLOBALS ==================
pynput_kb = PynputKeyboardController()
APP_NAME = "MilenSoftware"

GLOBAL_CONFIG = {}
PERSISTENT_SETTINGS_PATH = "persistent_settings.json"
ALARM_SOUND_PATH = "alert.wav"
ALARM_SOUND_PATH_FULL = ""

TARGET_FPS = 2.0
TARGET_FRAME_TIME = 1.0 / TARGET_FPS
CLICK_DELAY_MS = 0
BLOCKER_THRESHOLD = 0.70
BLOCKER_RETRY_SECONDS = 3.0

HARDCODED_OCR_PROFILES = {
    (800, 601): [
        (290, 200, 350, 260),
        (365, 200, 430, 260),
        (450, 200, 513, 260),
        (290, 270, 350, 340),
        (365, 270, 430, 340),
        (445, 270, 513, 340),
        (280, 350, 516, 390),  # ALT METİN
    ],
    (1024, 768): [
        (400, 278, 465, 345), #
        (480, 278, 545, 345),
        (560, 278, 625, 345),
        (400, 360, 465, 430), #
        (475, 360, 545, 430),
        (555, 360, 625, 430),
        (398, 438, 631, 465),  # ALT METİN
    ],
    # İLERİDE ÖRNEK:
    # (1024, 768): [
    #     (... 7 kutu ...),
    # ],
}
# Tolerans: her eksende ±30 piksel kabul edilebilir
HARDCODED_OCR_TOLERANCE = 35

CURRENT_VERSION = "2.0.5"

GITHUB_REPO_OWNER = "merterbir"
GITHUB_REPO_NAME = "AutoClicker-Updates"
VERSION_CHECK_URL = (
    f"https://raw.githubusercontent.com/"
    f"{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/main/latest_version.json"
)
NEW_EXE_FILENAME = "AutoClicker.exe"

MOD_TEMPLATES = {
    "METEOR": {
        "title": "Meteor Tarama",
        "lower_color": np.array([112, 20, 30]),
        "upper_color": np.array([160, 90, 180]),
        "min_area": 400,
        "blocker_path": "meteorBlocker.png",
        "is_visible": False
    },
    "ZUNG": {
        "title": "Zung Tarama",
        "lower_color": np.array([0, 80, 150]),
        "upper_color": np.array([30, 255, 250]),
        "min_area": 700,
        "blocker_path": "zungblocker.png",
        "is_visible": False
    },
    "KIZIL": {
        "title": "Kızıl Orman Güney Tarama",
        "lower_color": np.array([0, 60, 70]),
        "upper_color": np.array([10, 200, 200]),
        "min_area": 1000,
        "blocker_path": "kizilblocker.png",
        "is_visible": False
    },
    "GUATAMA": {
        "title": "Guatama Öfke Tarama",
        "lower_color": np.array([115, 50, 20]),
        "upper_color": np.array([165, 255, 255]),
        "min_area": 700,
        "blocker_path": "guatamablocker.png",
        "is_visible": False
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

alarm_wave_data = None

# ========== OCR GLOBALS ==========
try:
    OCR_READER = easyocr.Reader(['en', 'tr'], gpu=False)
except Exception as e:
    OCR_READER = None

OCR_LOCK = threading.Lock()

# ================== HELPERS ==================
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
    """
    PyInstaller içinde olduğunda _MEIPASS'tan,
    persistent_settings.json için ise AppData'dan okur.
    """
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
        "SKILL_SETTINGS": {
            "skill_master": False,
            "skill_hava": False,
            "skill_ofke": False,
            "skill_common_minutes": "3"
        },
        "PERFORMANCE_SETTINGS": {
            "target_fps": 2.0
        },
        "CLICK_SETTINGS": {
            "click_delay_ms": 0
        },
        "MOD_SETTINGS": {
            "blocker_threshold": 0.70,
            "blocker_retry_seconds": 3.0
        },
        # 🔹 YENİ: OCR CONFIG
        "OCR_CONFIG": {
            # resolution_key -> { "coords": [ (x1,y1,x2,y2) * 7 ] }
            "profiles": {}
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
    global TARGET_FPS, TARGET_FRAME_TIME, CLICK_DELAY_MS, BLOCKER_THRESHOLD, BLOCKER_RETRY_SECONDS

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

    perf_conf = GLOBAL_CONFIG.get("PERFORMANCE_SETTINGS", {})
    TARGET_FPS = float(perf_conf.get("target_fps", TARGET_FPS))
    if TARGET_FPS <= 0:
        TARGET_FPS = 2.0
    TARGET_FRAME_TIME = 1.0 / TARGET_FPS

    click_conf = GLOBAL_CONFIG.get("CLICK_SETTINGS", {})
    CLICK_DELAY_MS = int(click_conf.get("click_delay_ms", CLICK_DELAY_MS))

    mod_conf = GLOBAL_CONFIG.get("MOD_SETTINGS", {})
    BLOCKER_THRESHOLD = float(mod_conf.get("blocker_threshold", BLOCKER_THRESHOLD))
    BLOCKER_RETRY_SECONDS = float(mod_conf.get("blocker_retry_seconds", BLOCKER_RETRY_SECONDS))

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
        "SKILL_SETTINGS": GLOBAL_CONFIG.get("SKILL_SETTINGS", {}),
        "PERFORMANCE_SETTINGS": GLOBAL_CONFIG.get("PERFORMANCE_SETTINGS", {}),
        "CLICK_SETTINGS": GLOBAL_CONFIG.get("CLICK_SETTINGS", {}),
        "MOD_SETTINGS": GLOBAL_CONFIG.get("MOD_SETTINGS", {}),
        "OCR_CONFIG": GLOBAL_CONFIG.get("OCR_CONFIG", {}),
    }

    try:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception:
        return False


load_config()


def load_alarm_sound():
    global alarm_wave_data, ALARM_SOUND_PATH_FULL
    ALARM_SOUND_PATH_FULL = resource_path(ALARM_SOUND_PATH)
    if os.path.exists(ALARM_SOUND_PATH_FULL):
        try:
            with wave.open(ALARM_SOUND_PATH_FULL, "rb") as wf:
                params = wf.getparams()
                frames = wf.readframes(params.nframes)
            alarm_wave_data = (frames, params.sampwidth, params.nchannels, params.framerate)
        except Exception:
            alarm_wave_data = None
    else:
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


# ================== AREA SELECTORS ==================
class AreaSelector:
    """
    Tam ekran overlay ile dikdörtgen seçip,
    ekran görüntüsünü dosyaya kaydeder.
    Alert/blocker görselleri için kullanıyoruz.
    """

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

        self.canvas = tk.Canvas(
            self.snip_tool, cursor="tcross", bg='black', bd=0, highlightthickness=0
        )
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

        self.canvas = tk.Canvas(
            self.snip_tool, cursor="tcross", bg='black', bd=0, highlightthickness=0
        )
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

class OCRSelectionWindow:
    """
    Ayarlanacak OCR koordinatları için:
    - Verilen PIL image üstünde 7 kutu seçtirir
    - Seçim bitince done_callback(coords_list, original_size) çağırır
      coords_list: [(x1,y1,x2,y2), ...] 7 eleman
      original_size: (w, h)
    """
    def __init__(self, master, pil_image, done_callback):
        self.master = master
        self.done_callback = done_callback

        # Gelen argüman **PIL Image** olmak zorunda
        self.img = pil_image.convert("RGB")
        self.img_w, self.img_h = self.img.size

        # Yeni pencere (ayar penceresinin üstüne)
        self.top = tk.Toplevel(master)
        self.top.title("OCR Konfigürasyon - 7 Kutu Seç")
        self.top.attributes("-topmost", True)

        # Ekrana sığdır
        screen_w = self.top.winfo_screenwidth() - 80
        screen_h = self.top.winfo_screenheight() - 160
        ratio = min(screen_w / self.img_w, screen_h / self.img_h, 1.0)
        self.display_w = int(self.img_w * ratio)
        self.display_h = int(self.img_h * ratio)
        self.scale = self.img_w / self.display_w  # geri dönüşte çarpacağız

        self.tk_img = ImageTk.PhotoImage(
            self.img.resize((self.display_w, self.display_h), Image.Resampling.LANCZOS)
        )

        self.canvas = tk.Canvas(self.top, width=self.display_w, height=self.display_h, cursor="cross")
        self.canvas.pack()

        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)

        self.info_label = tk.Label(
            self.top,
            text="1. kutuyu seçin (toplam 7 kutu)",
            font=("Segoe UI", 11, "bold")
        )
        self.info_label.pack(fill="x", pady=4)

        self.boxes = []      # gerçek (orijinal) koordinatlar
        self.temp_rect = None
        self.start_x = 0
        self.start_y = 0

        self.canvas.bind("<ButtonPress-1>", self._box_press)
        self.canvas.bind("<B1-Motion>", self._box_drag)
        self.canvas.bind("<ButtonRelease-1>", self._box_release)

    def _box_press(self, event):
        self.start_x, self.start_y = event.x, event.y
        if self.temp_rect is not None:
            self.canvas.delete(self.temp_rect)
        self.temp_rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, event.x, event.y,
            outline="red", width=2
        )

    def _box_drag(self, event):
        if self.temp_rect is not None:
            self.canvas.coords(self.temp_rect, self.start_x, self.start_y, event.x, event.y)

    def _box_release(self, event):
        x1, y1 = self.start_x, self.start_y
        x2, y2 = event.x, event.y

        # Canvas koordinatlarını normalize et
        x1, x2 = sorted((x1, x2))
        y1, y2 = sorted((y1, y2))

        # Ekran görüntüsü orijinal boyutuna geri dön
        real_x1 = int(x1 * self.scale)
        real_y1 = int(y1 * self.scale)
        real_x2 = int(x2 * self.scale)
        real_y2 = int(y2 * self.scale)

        self.boxes.append((real_x1, real_y1, real_x2, real_y2))

        # Kalıcı yeşil kutu çiz
        self.canvas.create_rectangle(x1, y1, x2, y2, outline="lime", width=2)
        self.canvas.create_text(
            x1 + 10, y1 + 10,
            text=str(len(self.boxes)),
            fill="yellow",
            font=("Segoe UI", 10, "bold")
        )

        # Yeterli kutu seçildi mi?
        if len(self.boxes) < 7:
            self.info_label.config(text=f"{len(self.boxes)+1}. kutuyu seçin (toplam 7)")
        else:
            self.info_label.config(text="Tamamlandı, pencere kapanıyor...")

            # Kutuları x1,y1'e göre sırala (sabit olması için)
            boxes_sorted = sorted(self.boxes, key=lambda b: (b[1], b[0]))  # önce y sonra x

            # Callback → coords_list, original_size
            original_size = (self.img_w, self.img_h)
            try:
                self.done_callback(boxes_sorted, original_size)
            except Exception as e:
                messagebox.showerror("Hata", f"OCR callback hatası: {e}")

            self.top.destroy()


# ================== MAIN APP ==================
class AutoClickerApp:
    def __init__(self, master):
        self.master = master
        master.title(
            f"{GLOBAL_CONFIG['APP_CONFIG']['APP_TITLE']} v{CURRENT_VERSION} (Eş Zamanlı)"
        )

        self.alert_templates = self._load_alert_templates()
        self.next_alert_check_time = 0.0
        self.next_alert_allowed_time = 0.0
        self.paused_until = 0.0

        self.status_text = tk.StringVar(
            value=GLOBAL_CONFIG['APP_CONFIG']['STATUS_INITIAL_TEXT']
        )
        self.auto_click_state = tk.BooleanVar(value=True)

        sys_settings = GLOBAL_CONFIG["SYSTEM_SETTINGS"]
        self.stop_on_alert_main = tk.BooleanVar(
            value=sys_settings.get("stop_on_alert_main", False)
        )
        self.stop_on_tic = tk.BooleanVar(value=sys_settings.get("stop_on_tic", True))
        self.stop_on_message = tk.BooleanVar(value=sys_settings.get("stop_on_message", True))
        self.stop_on_control = tk.BooleanVar(value=sys_settings.get("stop_on_control", True))

        self.mode_status_vars = {}
        self.mode_control_frames = {}
        self.color_region_use_vars = {}

        self.debug_window = None

        # Skill config
        skill_conf = GLOBAL_CONFIG.get("SKILL_SETTINGS", {})
        self.skill_master_var = tk.BooleanVar(value=skill_conf.get("skill_master", False))
        self.skill_hava_var = tk.BooleanVar(value=skill_conf.get("skill_hava", False))
        self.skill_ofke_var = tk.BooleanVar(value=skill_conf.get("skill_ofke", False))
        self.skill_common_minutes_var = tk.StringVar(
            value=str(skill_conf.get("skill_common_minutes", "3"))
        )

        self.skill_manager_thread = None
        self.skill_manager_running = False
        self.skill_sequence_active = False
        self.skill_last_rotation_time = 0.0

        self.setup_ui()
        master.protocol("WM_DELETE_WINDOW", self.on_closing)

    # ---------- Close ----------
    def on_closing(self):
        for mod_instance in ACTIVE_MOD_INSTANCES:
            mod_instance["is_running"] = False
        self._save_persistent_settings()
        self.master.destroy()
        sys.exit(0)
        # ---------- OCR Helpers ----------
    def _ocr_enhance_image(self, gray_np):
        """
        OCR için görüntüyü büyüt + OTSU threshold uygula.
        gray_np: tek kanal (grayscale) numpy array
        """
        if gray_np is None or gray_np.size == 0:
            return gray_np

        scale = 3
        resized = cv2.resize(
            gray_np, None,
            fx=scale, fy=scale,
            interpolation=cv2.INTER_CUBIC
        )
        _, thresh = cv2.threshold(
            resized, 0, 255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        return thresh

    def _ocr_read_text(self, img_processed):
        """
        EasyOCR ile metni oku (global lock ile).
        """
        if OCR_READER is None:
            return ""
        with OCR_LOCK:
            result = OCR_READER.readtext(
                img_processed,
                detail=0,
                paragraph=False
            )
        return " ".join(result).strip()

    def run_control_ocr_for_mod(self, mod_instance):
        """
        Control.png yakalandığında çağrılır.
        - Modun region_rect'ine göre pencereyi çeker
        - KODA GÖMÜLÜ 7 kare profilini kullanarak:
        1) Alt metin alanından hedef string'i çıkarır
        2) 6 kare içinde normalize ederek eşleşeni bulur
        3) Eşleşen karenin ortasına gidip 1 sn sonra tıklar
        - Eşleşme yoksa 3 sn sonra tekrar dener (1 kez).
        """
        if OCR_READER is None:
            self.status_text.set("OCR modeli yüklü değil (easyocr).")
            return

        region = mod_instance.get("region_rect")
        if not region:
            self.status_text.set("OCR için bölge seçilmemiş.")
            return

        X1, Y1, X2, Y2 = region
        w = X2 - X1
        h = Y2 - Y1

        # ----------------- HARDCODED OCR PROFİL SEÇİMİ -----------------
        best_key = None
        best_score = None

        for (pw, ph), boxes in HARDCODED_OCR_PROFILES.items():
            # Her eksende ayrı tolerans kontrolü
            if abs(pw - w) > HARDCODED_OCR_TOLERANCE:
                continue
            if abs(ph - h) > HARDCODED_OCR_TOLERANCE:
                continue

            # Ne kadar yakın? Basit skor: |Δw| + |Δh|
            score = abs(pw - w) + abs(ph - h)
            if best_score is None or score < best_score:
                best_score = score
                best_key = (pw, ph)

        if best_key is None:
            self.status_text.set(
                f"OCR profili bulunamadı. Ekran: {w}x{h}, profiller: "
                f"{[f'{pw}x{ph}' for (pw, ph) in HARDCODED_OCR_PROFILES.keys()]}"
            )
            return

        base_w, base_h = best_key
        base_boxes = HARDCODED_OCR_PROFILES[best_key]

        sx = w / base_w
        sy = h / base_h

        coords_list = []
        for (cx1, cy1, cx2, cy2) in base_boxes:
            coords_list.append((
                int(cx1 * sx),
                int(cy1 * sy),
                int(cx2 * sx),
                int(cy2 * sy),
            ))

        if len(coords_list) != 7:
            self.status_text.set(
                f"HARDCODED OCR profili bozuk: {base_w}x{base_h} → {len(coords_list)} kutu"
            )
            return

        # Debug istersen
        # ----------------- HARDCODED OCR PROFİL SEÇİMİ SONU -----------------

        def _one_try():
            try:
                sct = mss.mss()
                monitor = {"top": Y1, "left": X1, "width": w, "height": h}
                sct_img = sct.grab(monitor)
                img_np = np.array(sct_img)
                img_bgr = cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)
                gray_full = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
                #self.save_ocr_debug_screenshot(img_bgr.copy(), coords_list)
            except Exception as e:
                self.status_text.set(f"OCR ekran görüntüsü hatası: {e}")
                return False, None

            # 7. alan: alt metin
            tx1, ty1, tx2, ty2 = coords_list[6]
            text_crop = gray_full[ty1:ty2, tx1:tx2].copy()
            enhanced_text = self._ocr_enhance_image(text_crop)
            raw_text = self._ocr_read_text(enhanced_text)
            cleaned_text = raw_text.replace("\n", " ").strip()

            # "arasindan X resmini" pattern'i
            target_norm = ""
            candidate_raw = ""
            m = re.search(
                r"arasindan\s+(.*?)\s+(resmini|image)",
                cleaned_text,
                re.IGNORECASE
            )
            if m:
                candidate_raw = m.group(1).strip()
                target_norm = self._ocr_normalize_token(candidate_raw)

            if not target_norm:
                self.status_text.set(f"OCR hedef bulunamadı. Ham: '{cleaned_text}'")
                return False, None

            self.status_text.set(f"OCR hedef: '{target_norm}' (Ham: '{candidate_raw}')")

            # 6 kareyi tara
            for i in range(6):
                bx1, by1, bx2, by2 = coords_list[i]
                box_crop = gray_full[by1:by2, bx1:bx2].copy()
                enhanced_box = self._ocr_enhance_image(box_crop)
                box_raw = self._ocr_read_text(enhanced_box)
                box_norm = self._ocr_normalize_token(box_raw)

                if target_norm and target_norm in box_norm:
                    # Eğer daha önce tıklandıysa → tekrar tıklama yok
                    if mod_instance.get("has_clicked", False):
                        return True, None

                    # tıklama yapıyoruz
                    bx_mid = int((bx1 + bx2) / 2)
                    by_mid = int((by1 + by2) / 2)
                    click_x = X1 + bx_mid
                    click_y = Y1 + by_mid

                    self.status_text.set(f"OCR eşleşmesi: {i+1}. kare (tıklanıyor...)")

                    # işaretle
                    mod_instance["has_clicked"] = True
                    # 10 saniye sonra resetle
                    self.master.after(
                        10000,
                        lambda m=mod_instance: m.update(has_clicked=False)
                    )

                    # tıklama
                    try:
                        pyautogui.moveTo(click_x, click_y, duration=0.2)
                        time.sleep(0.8)
                        pyautogui.click(click_x, click_y)
                    except:
                        pass

                    return True, (click_x, click_y)

            # Hiç eşleşme yok
            self.status_text.set("OCR ile eşleşen kare bulunamadı.")
            return False, None


        # İlk deneme
        ok, pos = _one_try()
        if ok:
            return



        # Eşleşme yoksa 3 sn sonra 1 kez daha dene
        time.sleep(3.0)
        _one_try()

    def save_ocr_debug_screenshot(self, img_bgr, coords_list):
        try:
            # 1-6 kare = yeşil dikdörtgen
            for i in range(6):
                x1, y1, x2, y2 = coords_list[i]
                cv2.rectangle(img_bgr, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(img_bgr, str(i + 1), (x1 + 5, y1 + 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # 7. kare = sarı (alt metin)
            x1, y1, x2, y2 = coords_list[6]
            cv2.rectangle(img_bgr, (x1, y1), (x2, y2), (0, 255, 255), 2)
            cv2.putText(img_bgr, "TXT", (x1 + 5, y1 + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

            # Dosyaya kaydet
            filename = f"ocr_debug_{int(time.time())}.png"
            cv2.imwrite(filename, img_bgr)

        except Exception as e:
            print("OCR debug ekran kaydetme hatası:", e)

    

    def _ocr_normalize_token(self, text):
        """
        Harf/rakam karışımı için normalizasyon:
        - alfasayısal dışı her şeyi at
        - küçült
        - 0->o, 1->l, 5->s
        """
        if not text:
            return ""
        alnum = re.sub(r"[^0-9A-Za-z]", "", text)
        lower = alnum.lower()
        return (
            lower
            .replace("0", "o")
            .replace("1", "l")
            .replace("5", "s")
        )

    # ---------- Toggle per-mod ----------
    def toggle_bot(self, mod_instance):
        app_config = GLOBAL_CONFIG['APP_CONFIG']
        if not mod_instance.get("is_running"):
            if mod_instance.get("region_rect") is None:
                messagebox.showerror(
                    "Hata",
                    f"{mod_instance['title']} için önce Bölge Seç yapın!"
                )
                return

            mod_instance["is_running"] = True
            if mod_instance.get("start_stop_btn"):
                mod_instance["start_stop_btn"].config(
                    text=app_config['STOP_BUTTON_TEXT'],
                    bg="red"
                )
            if mod_instance["id"] in self.mode_status_vars:
                self.mode_status_vars[mod_instance["id"]].set("ÇALIŞIYOR")

            t = Thread(target=self.bot_loop, args=(mod_instance,), daemon=True)
            mod_instance["thread"] = t
            t.start()

            self._update_global_status()
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

    # ---------- Save Persistent ----------
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

        GLOBAL_CONFIG["SKILL_SETTINGS"] = {
            "skill_master": self.skill_master_var.get(),
            "skill_hava": self.skill_hava_var.get(),
            "skill_ofke": self.skill_ofke_var.get(),
            "skill_common_minutes": self.skill_common_minutes_var.get()
        }

        save_config(GLOBAL_CONFIG)

    # ---------- Alert Templates ----------
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

    # ---------- Settings / Debug ----------
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

    # ---------- UI ----------
    def setup_ui(self):
        for widget in self.master.winfo_children():
            widget.destroy()

        app_config = GLOBAL_CONFIG['APP_CONFIG']

        # Üst bar
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

        tk.Label(
            self.master,
            textvariable=self.status_text,
            fg="blue",
            font=('Arial', 10, 'bold')
        ).pack(pady=5, fill=tk.X)

        main_notebook = ttk.Notebook(self.master)
        main_notebook.pack(pady=5, padx=10, fill='both', expand=True)

        # ---- Tarama Tab ----
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
                def _add_func(k=key, t=template['title']):
                    self.add_new_mod_instance(k, t)
                tk.Button(
                    add_frame,
                    text=f"+ Yeni {template['title']}",
                    command=_add_func,
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

        # Kaydedilmiş modları tekrar kur
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

        info_frame = tk.Frame(modes_tab)
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        tk.Label(
            info_frame,
            text="Alert / bot durdurma ayarlarını değiştirmek için sağ üstten 'Ayarlar' menüsüne gidin.",
            wraplength=260,
            justify='left',
            fg="gray"
        ).pack(anchor='n', pady=5)

        # ---- Skill Tab ----
        skill_tab = ttk.Frame(main_notebook)
        main_notebook.add(skill_tab, text="Skill")

        self._build_skill_ui(skill_tab)

        # ---- Version Button ----
        tk.Button(
            self.master,
            text=f"{app_config['VERSION_CHECK_TEXT']} (v{CURRENT_VERSION})",
            command=self.start_update_check_thread,
            bg="light blue"
        ).pack(pady=5, fill=tk.X, padx=15)

    # ---------- Skill UI ----------
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
                self.skill_manager_thread = Thread(
                    target=self.skill_manager_loop,
                    daemon=True
                )
                self.skill_manager_thread.start()
        else:
            self.skill_manager_running = False
        self._update_skill_options_visibility()

    def _update_skill_options_visibility(self):
        state = tk.NORMAL if self.skill_master_var.get() else tk.DISABLED
        for widget in [
            self.skill_hava_cb,
            self.skill_ofke_cb,
            self.skill_minutes_entry,
            self.skill_manual_button
        ]:
            widget.config(state=state)

    # ---------- Skill Manager ----------
    def skill_manager_loop(self):
        """
        Skill timer'ını yönetir.
        - Süre dolunca tüm aktif modlar için skill sekansı tetiklenir.
        - Blocker kontrolü skill otomasyonunu ETKİLEMEZ.
        """
        while self.skill_manager_running:
            try:
                if not self.skill_master_var.get():
                    break

                # Hiç skill seçili değilse boşuna dönme
                if not (self.skill_hava_var.get() or self.skill_ofke_var.get()):
                    time.sleep(1.0)
                    continue

                # Aktif mod yoksa bekle
                active_mods = [
                    m for m in ACTIVE_MOD_INSTANCES
                    if m.get("is_running") and m.get("region_rect") is not None
                ]
                if not active_mods:
                    time.sleep(1.0)
                    continue

                # Süre hesabı
                try:
                    m_val = float(self.skill_common_minutes_var.get().replace(",", "."))
                    if m_val <= 0:
                        time.sleep(1.0)
                        continue
                    interval = m_val * 60.0
                except ValueError:
                    time.sleep(1.0)
                    continue

                now = time.time()

                # Zaten sekans çalışıyorsa bekle
                if self.skill_sequence_active:
                    time.sleep(1.0)
                    continue

                # Süre dolmamışsa bekle
                if now - self.skill_last_rotation_time < interval:
                    time.sleep(1.0)
                    continue

                # ⏱ SÜRE DOLDU → Blocker bakmadan skill rotasyonunu tetikle
                Thread(
                    target=self.run_skill_rotation_for_all_active_mods,
                    daemon=True
                ).start()

                # Hafif bekleme
                time.sleep(1.0)

            except Exception:
                time.sleep(1.0)

        self.skill_manager_running = False

    def manual_trigger_skills(self):
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

    # ---------- Mod Instance ----------
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

        def _start_stop(m=mod_instance):
            self.toggle_bot(m)

        start_stop_btn = tk.Button(
            btn_frame,
            text=app_config['START_BUTTON_TEXT'],
            command=_start_stop,
            bg="green",
            fg="white"
        )
        start_stop_btn.pack(side=tk.LEFT, padx=5)
        mod_instance["start_stop_btn"] = start_stop_btn

        def _region(m=mod_instance):
            self.trigger_delayed_scan_region(m)

        tk.Button(
            btn_frame,
            text=app_config['REGION_BUTTON_TEXT'],
            command=_region
        ).pack(side=tk.LEFT, padx=5)

        use_var = tk.BooleanVar(value=mod_instance.get("use_color_region", False))
        self.color_region_use_vars[mod_instance["id"]] = use_var

        def _color_region(m=mod_instance):
            self.trigger_color_region_selection(m)

        color_btn = tk.Button(btn_frame, text="Renk Alanı Seç", command=_color_region)
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

        def _remove(m=mod_instance):
            self.remove_mod_instance(m)

        tk.Button(
            btn_frame,
            text="X Kaldır",
            command=_remove,
            bg="orange"
        ).pack(side=tk.LEFT, padx=15)

    def remove_mod_instance(self, mod_instance):
        if mod_instance.get("is_running"):
            self.toggle_bot(mod_instance)

        if messagebox.askyesno(
            "Onay",
            f"'{mod_instance['title']}' modunu kaldırmak istediğinizden emin misiniz?"
        ):
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
                f"{active_count} mod aktif. Global Tıklama: "
                f"{'AÇIK' if self.auto_click_state.get() else 'KAPALI'}"
            )
        else:
            self.status_text.set(GLOBAL_CONFIG['APP_CONFIG']['STATUS_INITIAL_TEXT'])

    # ---------- Region Selection ----------
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

    def trigger_ocr_selection_for_region(self, mod_instance):
        r = mod_instance.get("region_rect")
        if not r:
            messagebox.showerror("Hata", "Önce pencere bölgesini seçin.")
            return

        X1, Y1, X2, Y2 = r
        w = X2 - X1
        h = Y2 - Y1

        res_key = f"{w}x{h}"

        sct = mss.mss()
        monitor = {"top": Y1, "left": X1, "width": w, "height": h}
        sct_img = sct.grab(monitor)
        img_np = np.array(sct_img)
        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(img_rgb)

        OCRSelectionWindow(
            self.master,
            pil_image,
            lambda coords, size: self._save_ocr_coords_for_res(res_key, coords, size)
        )

    def trigger_color_region_selection(self, mod_instance):
        if mod_instance.get("region_rect") is None:
            messagebox.showerror("Hata", "Önce pencere bölgesini (Bölge Seç) belirleyin.")
            return

        if not mod_instance.get("use_color_region", False):
            messagebox.showinfo(
                "Bilgi",
                "Önce 'Renk alanını kısıtla' kutusunu işaretleyin."
            )
            return

        ColorRegionSelector(
            self.master,
            callback=lambda x1, y1, x2, y2, m=mod_instance:
                self._color_region_selected(m, x1, y1, x2, y2),
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

    # ---------- Alert / Stop ----------
        # ---------- Alert / Stop ----------
    def _check_alert_and_action(self, gray_full, mod_instance):
        """
        Alert görsellerini tarar.
        - control: OCR tetikler, botları DURDURMAZ, False döner
        - tic / message / control (isteğe bağlı) için:
            stop_on_alert_main + ilgili checkbox açıksa -> tüm botlar durur, True döner
        - 'dead' görülürse her durumda tüm botlar durur, True döner
        """
        try:
            for alert_id, alert_data in self.alert_templates.items():
                # Eski: alert_data direkt template'di
                # Yeni: dict olabilir {"img": template, "threshold": 0.85}
                if isinstance(alert_data, dict):
                    template = alert_data.get("img")
                    threshold = float(alert_data.get("threshold", ALERT_THRESHOLD))
                else:
                    template = alert_data
                    threshold = ALERT_THRESHOLD

                if template is None:
                    continue

                res = cv2.matchTemplate(gray_full, template, cv2.TM_CCOEFF_NORMED)
                loc = np.where(res >= threshold)

                if len(loc[0]) == 0:
                    continue  # bu alert yok, diğerine bak

                # Buraya geldiysek, alert bulundu
                self.status_text.set(f"ALERT YAKALANDI → {alert_id}")

                # ---- CONTROL: OCR çalıştır, botları durdurma ----
                if alert_id == "control":
                    self.status_text.set("CONTROL bulundu → OCR tıklama başlıyor!")
                    Thread(
                        target=self.run_control_ocr_for_mod,
                        args=(mod_instance,),
                        daemon=True
                    ).start()
                    # control için loop’u kırma, sadece OCR thread’i çalışsın
                    return False

                # ---- Diğer alertlerin sesleri ----
                if alert_id == "message":
                    self.status_text.set("MESSAGE tetiklendi (alarm)")
                    winsound.Beep(700, 500)

                if alert_id == "tic":
                    self.status_text.set("TIC tetiklendi (alarm)")
                    winsound.Beep(1000, 300)

                # ---- Hangi durumda botları durduracağız? ----
                should_stop = False

                # Genel "Alert Bulunduğunda Bot Durdurulsun" açık mı?
                if self.stop_on_alert_main.get():
                    if alert_id == "tic" and self.stop_on_tic.get():
                        should_stop = True
                    elif alert_id == "message" and self.stop_on_message.get():
                        should_stop = True
                    elif alert_id == "control" and self.stop_on_control.get():
                        # Şu an CONTROL için durdurma istemiyorsan bunu kaldırabilirsin
                        should_stop = True

                # Özel "dead" alert'i → her durumda durdur
                if alert_id == "dead":
                    should_stop = True

                if should_stop:
                    # Tüm modları durdur
                    self.stop_all_bots()
                    return True

                # Eğer stop etmeyeceksek ama alert tetiklendiyse,
                # o anki mod loop’u için True/False ne istediğine göre karar verebilirsin.
                # Şu an durdurmuyorsak False döndürüyoruz.
                return False

        except Exception as e:
            print("Alert check hatası:", e)

        # Hiçbir alert tetiklenmediyse
        return False




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

        self.master.after(
            0,
            lambda: self.status_text.set("KRİTİK ALERT: Tüm botlar kapatıldı.")
        )
        self.master.after(0, self._update_global_status)

    # ---------- Blocker ----------
    def check_blocker(self, sct, mod_instance, monitor_region):
        mod_key = mod_instance.get("mod_key")
        if not mod_key:
            return False

        user_blocker_name = f"{mod_key.lower()}Blocker.jpg"
        user_blocker_path = get_alert_user_path(user_blocker_name)

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

        return mv >= BLOCKER_THRESHOLD

    # ---------- Bot Loop ----------
    def bot_loop(self, mod_instance):
        sct = mss.mss()

        X1, Y1, X2, Y2 = mod_instance["region_rect"]
        monitor_region = {
            "top": Y1,
            "left": X1,
            "width": X2 - X1,
            "height": Y2 - Y1
        }

        mod_key = mod_instance.get("mod_key")
        template = MOD_TEMPLATES.get(mod_key, {})

        lower = mod_instance.get(
            "lower_color",
            template.get("lower_color", np.array([0, 0, 0]))
        )
        upper = mod_instance.get(
            "upper_color",
            template.get("upper_color", np.array([179, 255, 255]))
        )
        min_area = mod_instance.get(
            "min_area",
            template.get("min_area", 200)
        )

        LOWER_COLOR = np.array(lower, dtype=np.uint8)
        UPPER_COLOR = np.array(upper, dtype=np.uint8)
        MIN_AREA = int(min_area)

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

                # =======================================================
                # YENİ — OCR Uyumlu Alert kontrolü
                # =======================================================
                # önceki hali:
                # if time.time() >= self.next_alert_check_time:
                #     if self._check_alert_and_action(gray_full):
                #         break
                # =======================================================
                if time.time() >= self.next_alert_check_time:
                    if self._check_alert_and_action(gray_full, mod_instance):
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
                contours, _ = cv2.findContours(
                    mask_merged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )

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

                # Blocker, sadece MOUSE tıklamasını engelliyor
                if mod_instance.get("blocker_path") and not action_due \
                        and now >= next_blocker_check_time:
                    blocker_present = self.check_blocker(sct, mod_instance, monitor_region)
                    if not blocker_present:
                        action_due = True
                    else:
                        next_blocker_check_time = now + BLOCKER_RETRY_SECONDS

                if best and action_due:
                    x, y, w, h, cx_local, cy_local = best
                    cx_global = detect_offset_x + cx_local
                    cy_global = detect_offset_y + cy_local

                    sx = int(X1 + cx_global)
                    sy = int(Y1 + cy_global)

                    pyautogui.moveTo(sx, sy)

                    if self.auto_click_state.get():
                        pyautogui.click()
                        if CLICK_DELAY_MS > 0:
                            time.sleep(CLICK_DELAY_MS / 1000.0)
                        self.master.after(
                            0,
                            lambda m=mod_instance: self.status_text.set(
                                f"Tıklandı: {m['title']}"
                            )
                        )
                    else:
                        self.master.after(
                            0,
                            lambda m=mod_instance: self.status_text.set(
                                f"Taşındı: {m['title']}"
                            )
                        )

                    if mod_instance.get("blocker_path"):
                        action_due = False
                        next_blocker_check_time = now + BLOCKER_RETRY_SECONDS
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
            self.master.after(
                0,
                lambda mid=mod_instance["id"], st=status:
                    self.mode_status_vars[mid].set(st)
            )

        self.master.after(0, self._update_global_status)


    # ---------- Update Check ----------
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
                self.master.after(
                    0,
                    lambda: self._prompt_and_download(latest_version, download_url)
                )
            else:
                self.status_text.set(
                    f"Zaten en son sürüme sahipsiniz. (v{CURRENT_VERSION})"
                )

        except requests.RequestException:
            self.status_text.set(
                "Güncelleme kontrolü başarısız oldu. İnternet veya URL'yi kontrol edin."
            )

    def _prompt_and_download(self, version, url):
        if messagebox.askyesno(
            "Güncelleme Mevcut",
            f"Yeni sürüm v{version} mevcut. İndirip uygulamak ister misiniz? "
            f"(Uygulama yeniden başlatılacaktır)"
        ):
            self.status_text.set("Güncelleme İndiriliyor...")
            Thread(
                target=self._download_and_install_update,
                args=(url, version),
                daemon=True
            ).start()

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

            # ZIP ilk iki byte kontrol (PK)
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

            # Basit batch script (PowerShell Expand-Archive, try/catch yok, {} yok)
            script_content = f"""@echo off
echo Kurulum Baslatiliyor...
cd /d "%~dp0"
echo Calisma klasoru: %CD%

set ZIP_NAME={zip_name}
set NEW_EXE={NEW_EXE_FILENAME}

set TEMP_DIR=update_%RANDOM%_%RANDOM%
mkdir "%TEMP_DIR%"

echo Arsiv cikartiliyor: %ZIP_NAME% -> %TEMP_DIR%
powershell -NoLogo -NoProfile -Command "Expand-Archive -LiteralPath '%ZIP_NAME%' -DestinationPath '%TEMP_DIR%' -Force"

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

            # Kendi kendini kapat
            self.master.quit()

        except Exception as e:
            self.status_text.set("Güncelleme/Kurulum sırasında kritik hata oluştu.")
            messagebox.showerror("Hata", f"Güncelleme başarısız oldu: {e}")
            self.status_text.set(f"Güncelleme Başarısız. (v{CURRENT_VERSION})")


# ================== SETTINGS WINDOW ==================
class SettingsWindow:
    def __init__(self, master, app_instance):
        global ALARM_VOLUME
        self.app = app_instance
        self.settings_root = Toplevel(master)
        self.settings_root.title("Gelişmiş Ayarlar")
        self.settings_root.geometry("540x720")
        self.settings_root.transient(master)
        self.settings_root.grab_set()

        self.master = master
        self.current_config = GLOBAL_CONFIG.copy()
        self.current_config.setdefault("OCR_CONFIG", {"profiles": {}})
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
        self._create_ocr_settings_tab()

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

        # Performans
        perf_frame = tk.LabelFrame(tab, text="Performans Ayarları", padx=10, pady=5)
        perf_frame.pack(pady=10, fill=tk.X, padx=10)

        tk.Label(perf_frame, text="FPS (Tarama Hızı):").pack(anchor='w')
        self.fps_scale = Scale(
            perf_frame,
            from_=1,
            to=30,
            orient=HORIZONTAL,
            length=300
        )
        self.fps_scale.set(self.current_config["PERFORMANCE_SETTINGS"].get("target_fps", TARGET_FPS))
        self.fps_scale.pack()

        # Global tıklama
        click_frame = tk.LabelFrame(tab, text="Global Tıklama Ayarları", padx=10, pady=5)
        click_frame.pack(pady=10, fill=tk.X, padx=10)

        tk.Label(click_frame, text="Tıklama Gecikmesi (ms):").pack(anchor='w')
        self.click_delay_entry = tk.Entry(click_frame, width=8)
        self.click_delay_entry.insert(
            0,
            str(self.current_config["CLICK_SETTINGS"].get("click_delay_ms", CLICK_DELAY_MS))
        )
        self.click_delay_entry.pack(anchor='w')

        # Mod ayarları
        mod_frame = tk.LabelFrame(tab, text="Mod Ayarları", padx=10, pady=5)
        mod_frame.pack(pady=10, fill=tk.X, padx=10)

        tk.Label(mod_frame, text="Blocker Eşik (0.0 – 1.0):").pack(anchor='w')
        self.blocker_thr_entry = tk.Entry(mod_frame, width=8)
        self.blocker_thr_entry.insert(
            0,
            str(self.current_config["MOD_SETTINGS"].get("blocker_threshold", BLOCKER_THRESHOLD))
        )
        self.blocker_thr_entry.pack(anchor='w')

        tk.Label(mod_frame, text="Blocker sonrası bekleme (sn):").pack(anchor='w')
        self.blocker_retry_entry = tk.Entry(mod_frame, width=8)
        self.blocker_retry_entry.insert(
            0,
            str(self.current_config["MOD_SETTINGS"].get("blocker_retry_seconds", BLOCKER_RETRY_SECONDS))
        )
        self.blocker_retry_entry.pack(anchor='w')

        # Mod buton görünürlük
        visibility_frame = tk.LabelFrame(
            tab,
            text="Ana Sayfada Gösterilecek Yeni Mod Butonları",
            padx=10,
            pady=5
        )
        visibility_frame.pack(pady=10, fill=tk.X, padx=10)

        self.visibility_vars = {}
        for mod_key, conf in MOD_TEMPLATES.items():
            is_visible = self.current_config.get("MOD_VISIBILITY", {}).get(mod_key, True)
            var = tk.BooleanVar(value=is_visible)
            self.visibility_vars[mod_key] = var
            tk.Checkbutton(
                visibility_frame,
                text=conf["title"],
                variable=var
            ).pack(anchor='w')

        # Alert ayarları
        alert_frame = tk.LabelFrame(
            tab,
            text="Alert ve Bot Durdurma Ayarları",
            padx=10,
            pady=5
        )
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

        alert_frame = tk.LabelFrame(tab, text="Alert Görselleri", padx=10, pady=5)
        alert_frame.pack(pady=5, fill=tk.X, padx=10)

        alert_texts = GLOBAL_CONFIG.get("ALERT_TEXTS", {})

        self._create_image_setting_button(
            alert_frame,
            "tic.png",
            alert_texts.get("tic", "Tic Görseli")
        )
        self._create_image_setting_button(
            alert_frame,
            "message.png",
            alert_texts.get("message", "Message Görseli")
        )
        self._create_image_setting_button(
            alert_frame,
            "control.png",
            alert_texts.get("control", "Control Görseli")
        )

        blocker_frame = tk.LabelFrame(tab, text="Mod Blocker Görselleri", padx=10, pady=5)
        blocker_frame.pack(pady=10, fill=tk.X, padx=10)

        for mod_key, conf in MOD_TEMPLATES.items():
            self._create_blocker_setting_button(blocker_frame, mod_key, conf["title"])

        # ---------- OCR CONFIG TAB ----------
    def _create_ocr_settings_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="OCR Config")

        info = tk.Label(
            tab,
            text=(
                "Bu sekme, Control görseli geldiğinde kullanılacak OCR alanlarını ayarlamak içindir.\n"
                "1) 'Başlat (7 Kare Seç)'e bas.\n"
                "2) 2 sn içinde oyunun penceresini aktif yap.\n"
                "3) Açılan ekranda sırayla 6 kare + 1 alt metin alanını seç.\n"
                "4) Ayarlar, pencere çözünürlüğüne göre kaydedilir."
            ),
            justify="left",
            wraplength=420
        )
        info.pack(padx=10, pady=10, anchor="w")

        btn = tk.Button(
            tab,
            text="▶ Başlat (7 Kare Seç)",
            command=self._start_ocr_capture
        )
        btn.pack(padx=10, pady=10, anchor="w")

        self.ocr_profiles_list = tk.Listbox(tab, height=5)
        self.ocr_profiles_list.pack(padx=10, pady=(10, 0), fill="x")

        # Var olan profilleri listele
        profiles = self.current_config.get("OCR_CONFIG", {}).get("profiles", {})
        for key in profiles.keys():
            self.ocr_profiles_list.insert(tk.END, key)

    def _start_ocr_capture(self):
        # 2 saniye içinde doğru pencereyi aktif etsin
        messagebox.showinfo(
            "Bilgi",
            "2 saniye içinde OCR ayarı yapılacak pencereyi aktif yap.\n"
            "Sonra o pencerenin ekran görüntüsü üzerinden 7 kare seçeceksin."
        )

        # 2 sn sonra gerçek capture fonksiyonunu çalıştır
        # 🔴 ÖNEMLİ: SettingsWindow içinde root değil, settings_root var
        self.settings_root.after(2000, self._capture_ocr_screenshot)



    def _capture_ocr_screenshot(self):
        try:
            # Aktif pencere boyutlarını al
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                messagebox.showerror("Hata", "Aktif pencere bulunamadı.")
                return

            rect = win32gui.GetWindowRect(hwnd)
            X1, Y1, X2, Y2 = rect
            w = X2 - X1
            h = Y2 - Y1

            if w <= 0 or h <= 0:
                messagebox.showerror("Hata", "Aktif pencere boyutu geçersiz.")
                return

            # Bu rect'i OCR_CONFIG için çözünürlük key'i olarak saklayacağız
            self.ocr_active_window_rect = (X1, Y1, X2, Y2)
            res_key = f"{w}x{h}"

            # Ekran görüntüsü (sadece bu pencere)
            with mss.mss() as sct:
                monitor = {"top": Y1, "left": X1, "width": w, "height": h}
                sct_img = sct.grab(monitor)
                img_np = np.array(sct_img)
                img_rgb = cv2.cvtColor(img_np, cv2.COLOR_BGRA2RGB)

            pil_img = Image.fromarray(img_rgb)

            # 7 kutu seçtir → sonuçlar _on_ocr_coords_selected'e gelecek
            OCRSelectionWindow(
                self.settings_root,
                pil_img,
                self._on_ocr_coords_selected
            )

        except Exception as e:
            messagebox.showerror("Hata", f"OCR ekran görüntüsü alınamadı: {e}")


    def _on_ocr_coords_selected(self, coords_list, original_size):
        """
        OCRSelectionWindow'dan gelen 7 kutuyu:
        - Çözünürlüğe göre OCR_CONFIG'e yazar
        - Koordinatlar **region_rect içinde relatif** olacak (X1,Y1 çıkarılmış)
        """
        if not hasattr(self, "ocr_active_window_rect"):
            messagebox.showerror("Hata", "Aktif pencere bilgisi yok.")
            return

        X1, Y1, X2, Y2 = self.ocr_active_window_rect
        win_w = X2 - X1
        win_h = Y2 - Y1
        res_key = f"{win_w}x{win_h}"

        # coords_list: pencere içi koordinatlar (zaten orijinal boyut)
        rel_coords = []
        for (x1, y1, x2, y2) in coords_list:
            rel_coords.append((
                max(0, x1),
                max(0, y1),
                min(win_w, x2),
                min(win_h, y2)
            ))

        # Config'e yaz
        ocr_conf = GLOBAL_CONFIG.setdefault("OCR_CONFIG", {})
        profiles = ocr_conf.setdefault("profiles", {})
        profiles[res_key] = {
            "coords": rel_coords
        }

        save_config(GLOBAL_CONFIG)
        messagebox.showinfo(
            "Başarılı",
            f"OCR config kaydedildi. Çözünürlük: {res_key}\nToplam 7 kutu: {len(rel_coords)}"
        )


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
        tk.Button(
            parent_frame,
            text=f"📷 {text}",
            command=btn_func
        ).pack(pady=3, fill=tk.X)

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
        messagebox.showinfo(
            "Başarılı",
            f"'{filename}' alert görseli başarıyla güncellendi ve kaydedildi."
        )

    def _blocker_capture_completed(self, filename):
        try:
            self.settings_root.deiconify()
            self.settings_root.grab_set()
        except Exception:
            pass

        messagebox.showinfo(
            "Başarılı",
            f"'{filename}' blocker görseli başarıyla güncellendi ve kaydedildi."
        )

    def _save_and_close(self):
        global ALARM_VOLUME, TARGET_FPS, TARGET_FRAME_TIME
        global CLICK_DELAY_MS, BLOCKER_THRESHOLD, BLOCKER_RETRY_SECONDS

        # Mod visibility
        for mod_key, var in self.visibility_vars.items():
            self.current_config["MOD_VISIBILITY"][mod_key] = var.get()

        # Volume
        new_volume = self.local_volume_value.get()
        self.current_config["SYSTEM_SETTINGS"]["ALARM_VOLUME"] = new_volume
        ALARM_VOLUME = new_volume

        # FPS
        try:
            new_fps = float(self.fps_scale.get())
            if new_fps <= 0:
                new_fps = 1.0
        except Exception:
            new_fps = TARGET_FPS
        self.current_config["PERFORMANCE_SETTINGS"]["target_fps"] = new_fps
        TARGET_FPS = new_fps
        TARGET_FRAME_TIME = 1.0 / TARGET_FPS

        # Click delay
        try:
            new_click_delay = int(self.click_delay_entry.get())
            if new_click_delay < 0:
                new_click_delay = 0
        except Exception:
            new_click_delay = CLICK_DELAY_MS
        self.current_config["CLICK_SETTINGS"]["click_delay_ms"] = new_click_delay
        CLICK_DELAY_MS = new_click_delay

        # Blocker threshold
        try:
            new_blocker_thr = float(self.blocker_thr_entry.get())
        except Exception:
            new_blocker_thr = BLOCKER_THRESHOLD
        self.current_config["MOD_SETTINGS"]["blocker_threshold"] = new_blocker_thr
        BLOCKER_THRESHOLD = new_blocker_thr

        # Blocker retry
        try:
            new_blocker_retry = float(self.blocker_retry_entry.get())
            if new_blocker_retry < 0:
                new_blocker_retry = 0.0
        except Exception:
            new_blocker_retry = BLOCKER_RETRY_SECONDS
        self.current_config["MOD_SETTINGS"]["blocker_retry_seconds"] = new_blocker_retry
        BLOCKER_RETRY_SECONDS = new_blocker_retry

        # Alert system settings
        self.current_config["SYSTEM_SETTINGS"]["stop_on_alert_main"] = \
            self.app.stop_on_alert_main.get()
        self.current_config["SYSTEM_SETTINGS"]["stop_on_tic"] = \
            self.app.stop_on_tic.get()
        self.current_config["SYSTEM_SETTINGS"]["stop_on_message"] = \
            self.app.stop_on_message.get()
        self.current_config["SYSTEM_SETTINGS"]["stop_on_control"] = \
            self.app.stop_on_control.get()

        # Skill settings
        self.current_config["SKILL_SETTINGS"] = {
            "skill_master": self.app.skill_master_var.get(),
            "skill_hava": self.app.skill_hava_var.get(),
            "skill_ofke": self.app.skill_ofke_var.get(),
            "skill_common_minutes": self.app.skill_common_minutes_var.get()
        }

        if save_config(self.current_config):
            messagebox.showinfo(
                "Başarılı",
                "Ayarlar kaydedildi. Arayüz yeniden çiziliyor."
            )
        else:
            messagebox.showerror(
                "Hata",
                "Ayarlar kaydedilemedi! persistent_settings.json yazılabilir mi?"
            )

        self.app.setup_ui()

        self.settings_root.destroy()
        self.app.master.grab_release()


# ================== DEBUG WINDOW ==================
class DebugWindow:
    def __init__(self, master):
        self.master = master
        self.root = Toplevel(master)
        self.root.title("Debug - HSV Canlı Görüntü")
        self.root.geometry("900x900")

        self.root.resizable(False, False)

        self.debug_region_rect = None
        self.debug_running = False
        self.debug_thread = None

        # HSV ve area değerleri
        self.lower_h_var = tk.StringVar(value="0")
        self.lower_s_var = tk.StringVar(value="150")
        self.lower_v_var = tk.StringVar(value="150")

        self.upper_h_var = tk.StringVar(value="10")
        self.upper_s_var = tk.StringVar(value="255")
        self.upper_v_var = tk.StringVar(value="255")

        self.min_area_var = tk.StringVar(value="80")

        # Önizleme için
        self.last_frame = None
        self.preview_photo = None

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Önizleme güncelleme loop'u
        self._schedule_preview_update()

    def _build_ui(self):
        tk.Label(
            self.root,
            text="1) 3 sn içinde pencere seç\n2) HSV aralığı ve min area gir\n3) Debug Başlat",
            justify="left"
        ).pack(pady=5)

        self.region_label = tk.Label(
            self.root,
            text="Bölge: Henüz seçilmedi",
            fg="red"
        )
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
        tk.Entry(lower_row, width=4, textvariable=self.lower_h_var).pack(
            side=tk.LEFT, padx=2
        )
        tk.Entry(lower_row, width=4, textvariable=self.lower_s_var).pack(
            side=tk.LEFT, padx=2
        )
        tk.Entry(lower_row, width=4, textvariable=self.lower_v_var).pack(
            side=tk.LEFT, padx=2
        )

        upper_row = tk.Frame(hsv_frame)
        upper_row.pack(anchor='w', pady=2)
        tk.Label(upper_row, text="Üst (H,S,V): ").pack(side=tk.LEFT)
        tk.Entry(upper_row, width=4, textvariable=self.upper_h_var).pack(
            side=tk.LEFT, padx=2
        )
        tk.Entry(upper_row, width=4, textvariable=self.upper_s_var).pack(
            side=tk.LEFT, padx=2
        )
        tk.Entry(upper_row, width=4, textvariable=self.upper_v_var).pack(
            side=tk.LEFT, padx=2
        )

        area_frame = tk.Frame(self.root)
        area_frame.pack(pady=5)
        tk.Label(area_frame, text="Min Area:").pack(side=tk.LEFT)
        tk.Entry(area_frame, width=6, textvariable=self.min_area_var).pack(
            side=tk.LEFT, padx=3
        )

        # Canlı önizleme label'ı
        self.preview_frame = tk.Frame(self.root)
        self.preview_frame.pack(fill=tk.BOTH, expand=True)

        self.preview_label = tk.Label(self.preview_frame, text="Önizleme yok")
        self.preview_label.pack(fill=tk.BOTH, expand=True)


        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Debug Başlat", command=self.start_debug).pack(
            side=tk.LEFT, padx=5
        )
        tk.Button(btn_frame, text="Debug Durdur", command=self.stop_debug).pack(
            side=tk.LEFT, padx=5
        )

    def trigger_debug_region(self):
        self.region_label.config(
            text="Bölge: 3 sn içinde hedef pencereye geç...",
            fg="orange"
        )
        self.root.update()
        self.root.after(3000, self._set_debug_region)

    def _set_debug_region(self):
        r = get_active_window_rect()
        if r:
            self.debug_region_rect = r
            self.region_label.config(text=f"Bölge: {r}", fg="green")
        else:
            self.region_label.config(
                text="Bölge: Aktif pencere bulunamadı",
                fg="red"
            )

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

                contours, _ = cv2.findContours(
                    mask_merged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )

                vis = frame.copy()
                for cnt in contours:
                    area = cv2.contourArea(cnt)
                    if area >= min_area:
                        x, y, w, h = cv2.boundingRect(cnt)
                        cv2.rectangle(
                            vis, (x, y), (x + w, y + h), (0, 0, 255), 2
                        )

                # Sadece son frame'i tut, gösterme işini Tk tarafı yapacak
                self.last_frame = vis

            except Exception:
                pass

            time.sleep(0.05)

    def _schedule_preview_update(self):
        """Tk tarafında, son frame'i alıp label'da gösterir."""
        if not self.root.winfo_exists():
            return

        if self.last_frame is not None:
            try:
                frame_rgb = cv2.cvtColor(self.last_frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)

                # Küçük bir boyuta ölçekle (örn. 320x180)
                img = img.resize((self.preview_label.winfo_width(),
                  self.preview_label.winfo_height()),
                  Image.Resampling.LANCZOS)


                self.preview_photo = ImageTk.PhotoImage(img)
                self.preview_label.configure(image=self.preview_photo, text="")
            except Exception:
                pass

        # 50ms sonra tekrar
        self.root.after(50, self._schedule_preview_update)

    def on_close(self):
        self.stop_debug()
        self.root.destroy()



# ================== MAIN ==================
if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = AutoClickerApp(root)
        root.mainloop()
    except Exception as e:
        print(f"Uygulama başlatma hatası: {e}")
