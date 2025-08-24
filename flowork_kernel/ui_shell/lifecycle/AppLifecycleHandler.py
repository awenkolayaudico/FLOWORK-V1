#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\flowork_kernel\ui_shell\lifecycle\AppLifecycleHandler.py
# JUMLAH BARIS : 68
#######################################################################

from tkinter import messagebox
import logging
import threading
from PIL import Image
import pystray
import sys
class AppLifecycleHandler:
    def __init__(self, main_window, kernel):
        self.main_window = main_window
        self.kernel = kernel
        self.loc = self.kernel.get_service("localization_manager")
        self.tray_icon = None
        self.tray_thread = None
    def on_closing_app(self):
        self.main_window.withdraw() # Hide the main window
        self._create_or_show_tray_icon()
    def _create_or_show_tray_icon(self):
        """Creates and runs the system tray icon in a separate thread if it's not already running."""
        if self.tray_thread and self.tray_thread.is_alive():
            return
        try:
            image = Image.open("icon.png")
        except FileNotFoundError:
            self.kernel.write_to_log("System tray icon.png not found, using placeholder.", "ERROR")
            image = Image.new('RGB', (64, 64), color = 'blue')
        menu = (
            pystray.MenuItem(
                self.loc.get('tray_menu_show', fallback='Show Flowork'),
                self._show_window,
                default=True
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                self.loc.get('tray_menu_exit', fallback='Exit Flowork'),
                self._exit_app
            )
        )
        self.tray_icon = pystray.Icon("flowork", image, "Flowork", menu)
        self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        self.tray_thread.start()
        self.kernel.write_to_log("Application minimized to system tray.", "INFO")
    def _show_window(self):
        """Shows the main window when the tray icon option is clicked."""
        self.main_window.after(0, self.main_window.deiconify)
    def _exit_app(self):
        """The real exit logic for the application."""
        if self.tray_icon:
            self.tray_icon.stop()
        should_save = messagebox.askyesnocancel(
            self.loc.get('confirm_exit_title', fallback="Exit Application"),
            self.loc.get('confirm_exit_save_workflow_message', fallback="Do you want to save your work before exiting?")
        )
        if should_save is None:
            self.kernel.write_to_log("Exit process cancelled by user.", "INFO")
            return
        if should_save:
            self.main_window.save_layout_and_session()
        self.kernel.write_to_log("Application exit initiated.", "INFO")
        self.kernel.stop_all_services()
        self.main_window.destroy()
        sys.exit(0)
