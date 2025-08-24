#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\flowork_kernel\ui_shell\ui_components\menubar_manager.py
# JUMLAH BARIS : 83
#######################################################################

from tkinter import Menu
from flowork_kernel.api_contract import BaseUIProvider
from flowork_kernel.utils.performance_logger import log_performance
class MenubarManager:
    def __init__(self, main_window, kernel):
        self.main_window = main_window
        self.kernel = kernel
        self.loc = self.kernel.get_service("localization_manager")
        self.menubar = Menu(self.main_window)
        self.main_window.config(menu=self.menubar)
    @log_performance("Building main menubar")
    def build_menu(self):
        self.menubar.delete(0, 'end' )
        self.main_window.main_menus.clear()
        file_menu = Menu(self.menubar, tearoff=0)
        file_menu_label = self.loc.get('menu_file', fallback="File")
        self.menubar.add_cascade(label=file_menu_label, menu=file_menu)
        self.main_window.main_menus[file_menu_label] = file_menu
        file_menu.add_command(label=self.loc.get('menu_save_workflow', fallback="Save Workflow"), command=lambda: self.main_window._trigger_workflow_action('save_workflow' ))
        file_menu.add_command(label=self.loc.get('menu_load_workflow', fallback="Load Workflow"), command=lambda: self.main_window._trigger_workflow_action('load_workflow'))
        file_menu.add_separator()
        file_menu.add_command(label=self.loc.get('menu_activate_license', fallback="Activate New License..."), command=self.main_window.handle_license_activation_request)
        file_menu.add_command(label=self.loc.get('menu_deactivate_license', fallback="Deactivate This Computer"), command=self.main_window.handle_license_deactivation_request)
        file_menu.add_separator()
        file_menu.add_command(label=self.loc.get('menu_exit', fallback="Exit"), command=self.main_window.lifecycle_handler.on_closing_app)
        ai_tools_menu = Menu(self.menubar, tearoff=0)
        ai_tools_menu_label = self.loc.get('menu_ai_tools', fallback="AI Tools")
        self.menubar.add_cascade(label=ai_tools_menu_label, menu=ai_tools_menu)
        self.main_window.main_menus[ai_tools_menu_label] = ai_tools_menu
        triggers_menu = Menu(self.menubar, tearoff=0)
        triggers_menu_label = self.loc.get('menu_triggers' , fallback="Triggers")
        self.menubar.add_cascade(label=triggers_menu_label, menu=triggers_menu)
        self.main_window.main_menus[triggers_menu_label] = triggers_menu
        triggers_menu.add_command(label=self.loc.get('menu_manage_triggers', fallback="Manage Triggers..."), command=lambda: self.main_window.tab_manager.open_managed_tab("trigger_manager"))
        themes_menu = Menu(self.menubar, tearoff=0)
        themes_menu_label = self.loc.get('menu_themes', fallback="Themes")
        self.menubar.add_cascade(label=themes_menu_label, menu=themes_menu)
        self.main_window.main_menus[themes_menu_label] = themes_menu
        themes_menu.add_command(label=self.loc.get("menu_manage_themes", fallback="Manage Themes..."), command=lambda: self.main_window.tab_manager.open_managed_tab("template_manager"))
        marketplace_menu = Menu(self.menubar, tearoff=0)
        marketplace_menu_label = self.loc.get('menu_marketplace', fallback="Marketplace")
        self.menubar.add_cascade(label=marketplace_menu_label, menu=marketplace_menu)
        self.main_window.main_menus[marketplace_menu_label] = marketplace_menu
        marketplace_menu.add_command(label=self.loc.get("menu_open_marketplace", fallback="Manage Components"), command=lambda: self.main_window._open_managed_tab("marketplace"))
        settings_menu= Menu(self.menubar, tearoff=0)
        settings_menu_label = self.loc.get('menu_settings', fallback="Settings")
        self.menubar.add_cascade(label=settings_menu_label, menu=settings_menu)
        self.main_window.main_menus[settings_menu_label] = settings_menu
        settings_menu.add_command(label=self.loc.get('menu_open_settings_tab', fallback="Open Settings"), command =lambda: self.main_window.tab_manager.open_managed_tab("settings"))
        help_menu= Menu(self.menubar, tearoff=0)
        help_menu_label = self.loc.get('menu_help', fallback="Help")
        self.menubar.add_cascade(label=help_menu_label, menu=help_menu)
        self.main_window.main_menus[help_menu_label] = help_menu
        help_menu.add_command(label=self.loc.get('menu_about', fallback="About Flowork"), command=lambda: self.main_window._show_about_dialog())
        self.kernel.write_to_log("MenubarManager: Discovering dynamic menu items from plugins...", "DEBUG")
        module_manager = self.kernel.get_service("module_manager_service")
        if module_manager:
            for module_id, module_data in module_manager.loaded_modules.items():
                instance = module_data.get("instance")
                if instance and isinstance(instance, BaseUIProvider) and not module_data.get("is_paused"):
                    menu_items = instance.get_menu_items()
                    if menu_items:
                        self.kernel.write_to_log(f" -> Found {len(menu_items)} menu item(s) from plugin '{module_id}'", "SUCCESS")
                        for item in menu_items:
                            parent_label = item.get('parent')
                            label = item.get('label')
                            command = item.get('command')
                            if parent_label not in self.main_window.main_menus:
                                new_menu = Menu(self.menubar, tearoff=0)
                                self.menubar.add_cascade(label=parent_label, menu=new_menu)
                                self.main_window.main_menus[parent_label] = new_menu
                            target_menu = self.main_window.main_menus.get(parent_label)
                            if target_menu and label and command:
                                if item.get('add_separator'):
                                    target_menu.add_separator()
                                target_menu.add_command(label=label, command=command)
