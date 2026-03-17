import customtkinter as ctk

from ui.widgets import make_splash_image


class SplashScreen(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.overrideredirect(True)
        self.attributes("-topmost", True)

        width, height = 420, 240
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

        frame = ctk.CTkFrame(self, corner_radius=24)
        frame.pack(fill="both", expand=True)

        splash_img = make_splash_image()
        self._ctk_img = ctk.CTkImage(light_image=splash_img, dark_image=splash_img, size=(360, 180))

        ctk.CTkLabel(frame, text="", image=self._ctk_img).pack(pady=(22, 8))
        ctk.CTkLabel(frame, text="Cargando interfaz...", text_color="gray75").pack(pady=(0, 14))
