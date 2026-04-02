import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.gui import DriverMonitorApp
import customtkinter as ctk

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    app = DriverMonitorApp(root)
    root.mainloop()