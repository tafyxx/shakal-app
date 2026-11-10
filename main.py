import os
import random
import io
import time
from datetime import datetime
from PIL import Image, ImageDraw, ImageOps, ImageChops, ImageEnhance

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.slider import Slider
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.core.window import Window
from kivy.core.audio import SoundLoader

# Папка Download видна в проводнике любого телефона и при подключении к ПК
STORAGE_BASE = "/sdcard/Download/ShakalStudio"
DIRS = {
    "ads": os.path.join(STORAGE_BASE, "ads"),
    "screamers": os.path.join(STORAGE_BASE, "screamers"),
    "cam_audio": os.path.join(STORAGE_BASE, "sounds_camera"),
    "scr_audio": os.path.join(STORAGE_BASE, "sounds_screamer"),
    "screenshots": os.path.join(STORAGE_BASE, "screenshots")
}

# Создание структуры папок при старте
for d in DIRS.values():
    os.makedirs(d, exist_ok=True)

class ShakalMobileApp(App):
    def build(self):
        self.request_android_permissions()

        self.native_w = int(Window.width)
        self.native_h = int(Window.height)

        root = BoxLayout(orientation='vertical', padding=12, spacing=8)

        # Шапка с автоопределением разрешения
        self.lbl_head = Label(
            text=f"SHAKAL ENGINE MOBILE\nЭкран: {self.native_w}x{self.native_h}",
            size_hint_y=None, height=60, bold=True, color=(0, 0.96, 0.83, 1)
        )
        root.add_widget(self.lbl_head)

        scroll = ScrollView(size_hint=(1, 1))
        content = BoxLayout(orientation='vertical', spacing=10, size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))

        # Разрешение
        content.add_widget(Label(text="Разрешение экрана", size_hint_y=None, height=25))
        self.slider_res = Slider(min=2, max=100, value=100, size_hint_y=None, height=35)
        content.add_widget(self.slider_res)

        # JPEG сжатие
        content.add_widget(Label(text="JPEG сжатие", size_hint_y=None, height=25))
        self.slider_q = Slider(min=1, max=100, value=65, size_hint_y=None, height=35)
        content.add_widget(self.slider_q)

        # Количество реклам
        content.add_widget(Label(text="Количество реклам", size_hint_y=None, height=25))
        self.slider_ads = Slider(min=0, max=100, value=15, size_hint_y=None, height=35)
        content.add_widget(self.slider_ads)

        # Пережарка
        content.add_widget(Label(text="Пережарка цвета", size_hint_y=None, height=25))
        self.slider_fry = Slider(min=1.0, max=5.0, value=1.2, size_hint_y=None, height=35)
        content.add_widget(self.slider_fry)

        # Индикатор папок
        self.lbl_status = Label(
            text="Папки созданы в: Download/ShakalStudio",
            size_hint_y=None, height=30, color=(1, 0.9, 0, 1), font_size=12
        )
        content.add_widget(self.lbl_status)

        scroll.add_widget(content)
        root.add_widget(scroll)

        # Главная кнопка
        btn_capture = Button(
            text="СДЕЛАТЬ ТЕСТОВЫЙ СКРИНШОТ",
            size_hint_y=None, height=55,
            background_color=(1, 0, 0.33, 1), bold=True
        )
        btn_capture.bind(on_release=self.take_and_process)
        root.add_widget(btn_capture)

        return root

    def request_android_permissions(self):
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.SYSTEM_ALERT_WINDOW
            ])
        except ImportError:
            pass

    def take_and_process(self, instance):
        # Захват экрана Kivy
        win_img = Window.screenshot(name=os.path.join(DIRS["screenshots"], "temp_raw.png"))
        time.sleep(0.1)

        raw_path = os.path.join(DIRS["screenshots"], "temp_raw.png")
        if not os.path.exists(raw_path):
            return

        with Image.open(raw_path) as img:
            img = img.convert("RGB")
            w, h = img.size

            # Наложение рекламы из папки ads
            ad_files = [os.path.join(DIRS['ads'], f) for f in os.listdir(DIRS['ads']) if f.lower().endswith(('.png', '.jpg', '.webp'))]
            ad_count = int(self.slider_ads.value)

            if ad_files and ad_count > 0:
                for _ in range(ad_count):
                    try:
                        with Image.open(random.choice(ad_files)) as ad:
                            ad = ad.convert("RGBA")
                            scale = random.uniform(0.2, 0.5)
                            tw, th = max(40, int(w * scale)), max(40, int(h * scale))
                            ad = ad.resize((tw, th), Image.Resampling.BILINEAR)
                            rx = random.randint(0, max(1, w - tw))
                            ry = random.randint(0, max(1, h - th))
                            img.paste(ad.convert("RGB"), (rx, ry), ad)
                    except Exception:
                        pass

            # Пережарка цвета
            fry = self.slider_fry.value
            if fry > 1.0:
                img = ImageEnhance.Color(img).enhance(fry * 1.3)
                img = ImageEnhance.Contrast(img).enhance(fry)

            # Масштаб разрешения (вплоть до 1800-х годов)
            pct = self.slider_res.value / 100.0
            if pct < 1.0:
                tw, th = max(24, int(w * pct)), max(18, int(h * pct))
                img = img.resize((tw, th), Image.Resampling.BILINEAR)

            # Сохранение готового файла
            fname = f"shakal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            save_path = os.path.join(DIRS["screenshots"], fname)
            img.save(save_path, format="JPEG", quality=int(self.slider_q.value))

        # Удаление временного файла
        if os.path.exists(raw_path):
            os.remove(raw_path)

        # Воспроизведение звука из папки sounds_camera
        self.play_sound(DIRS["cam_audio"])
        self.lbl_status.text = f"Сохранено: {fname}"

    def play_sound(self, folder):
        audio_files = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(('.mp3', '.wav', '.ogg'))]
        if audio_files:
            snd = SoundLoader.load(random.choice(audio_files))
            if snd:
                snd.play()

if __name__ == '__main__':
    ShakalMobileApp().run()