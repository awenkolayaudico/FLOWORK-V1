#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\advanced_web_scraper_module_1a2b\processor.py
# JUMLAH BARIS : 438
#######################################################################

import time
import re
import json
import os
import hashlib
from bs4 import BeautifulSoup
from flowork_kernel.api_contract import BaseModule, IExecutable, IConfigurableUI, IDataPreviewer, IDynamicOutputSchema
from flowork_kernel.ui_shell import shared_properties
from flowork_kernel.utils.payload_helper import get_nested_value
import ttkbootstrap as ttk
from tkinter import scrolledtext, StringVar, BooleanVar, IntVar
from flowork_kernel.ui_shell.custom_widgets.tooltip import ToolTip
from flowork_kernel.ui_shell.components.LabelledCombobox import LabelledCombobox
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
class AdvancedWebScraperModule(BaseModule, IExecutable, IConfigurableUI, IDataPreviewer, IDynamicOutputSchema):
    TIER = "basic" # (MODIFIED) Tier changed to basic as per pricing page
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
        if not SELENIUM_AVAILABLE:
            self.logger("FATAL: Selenium/WebDriver-Manager library is not installed for Advanced Web Scraper.", "CRITICAL")
        self.cache_path = os.path.join(self.kernel.data_path, "web_cache")
        os.makedirs(self.cache_path, exist_ok=True)
    def _resolve_value(self, value_str, payload):
        if not isinstance(value_str, str):
            return value_str
        matches = re.findall(r"\{\{([\w\.]+)\}\}", value_str)
        if not matches:
            return value_str
        resolved_value = get_nested_value(payload, matches[0])
        return resolved_value if resolved_value is not None else value_str
    def execute(self, payload: dict, config: dict, status_updater, ui_callback, mode='EXECUTE'):
        if not SELENIUM_AVAILABLE:
            raise RuntimeError("Required libraries (selenium, webdriver-manager) are not installed.")
        run_mode = config.get('run_mode', 'extract_full_page')
        if run_mode == 'perform_interaction_steps':
            return self._execute_interaction_steps(payload, config, status_updater, ui_callback, mode)
        else: # (COMMENT) Fallback to original behavior
            return self._execute_full_page_extract(payload, config, status_updater, ui_callback, mode)
    def _execute_interaction_steps(self, payload: dict, config: dict, status_updater, ui_callback, mode='EXECUTE'):
        is_headless = bool(config.get('headless_mode', True))
        interaction_steps_str = config.get('interaction_steps', '')
        steps = [line.strip() for line in interaction_steps_str.split('\n') if line.strip() and not line.strip().startswith('#')]
        if not steps:
            raise ValueError("Interaction steps are not defined.")
        driver = None
        try:
            status_updater("Initializing browser driver...", "INFO")
            options = webdriver.ChromeOptions()
            if is_headless: options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1200")
            options.add_argument("--ignore-certificate-errors")
            options.add_argument("--disable-extensions")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            for i, step in enumerate(steps):
                status_updater(f"Executing Step {i+1}/{len(steps)}: {step}", "INFO")
                parts = [p.strip() for p in step.split('|')]
                action = parts[0].upper()
                if action == 'NAVIGATE':
                    url = self._resolve_value(parts[1], payload)
                    driver.get(url)
                elif action == 'WAIT':
                    seconds = int(parts[1])
                    time.sleep(seconds)
                elif action == 'CLICK':
                    selector = parts[1]
                    by, value = self._parse_selector(selector)
                    element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((by, value)))
                    element.click()
                elif action == 'TYPE':
                    selector = parts[1]
                    text_to_type = self._resolve_value(parts[2], payload)
                    by, value = self._parse_selector(selector)
                    element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((by, value)))
                    element.send_keys(text_to_type)
                elif action == 'EXTRACT':
                    rules_str = parts[1]
                    html_content = driver.page_source
                    extracted_data = self._perform_extraction(html_content, rules_str, "") # No excludes in this mode yet
                    if 'data' not in payload or not isinstance(payload['data'], dict):
                        payload['data'] = {}
                    payload['data'].update(extracted_data) # Merge extracted data
                else:
                    self.logger(f"Unknown interaction action: '{action}'", "WARN")
            status_updater("Interaction sequence complete.", "SUCCESS")
            return {"payload": payload, "output_name": "success"}
        finally:
            if driver:
                driver.quit()
    def _parse_selector(self, selector_str):
        if '=' not in selector_str:
            return (By.CSS_SELECTOR, selector_str) # Default to CSS selector
        by_str, value = selector_str.split('=', 1)
        by_map = {
            'id': By.ID,
            'name': By.NAME,
            'xpath': By.XPATH,
            'css_selector': By.CSS_SELECTOR,
            'class_name': By.CLASS_NAME,
            'link_text': By.LINK_TEXT
        }
        return (by_map.get(by_str.lower(), By.CSS_SELECTOR), value)
    def _perform_extraction(self, html_content, rules_str, exclude_str):
        soup = BeautifulSoup(html_content, 'html.parser')
        if exclude_str:
            exclude_selectors = [line.strip() for line in exclude_str.split('\n') if line.strip()]
            for selector in exclude_selectors:
                for unwanted_element in soup.select(selector):
                    unwanted_element.decompose()
        extracted_data = {}
        rules = [line.strip() for line in rules_str.split('\n') if line.strip()]
        for rule in rules:
            try:
                parts = rule.split(':', 1)
                if len(parts) != 2: continue
                data_name = parts[0].strip()
                rule_body = parts[1].strip()
                option_match = re.search(r'\[(\w+)\]', rule_body)
                option = option_match.group(1) if option_match else 'text'
                selector = re.sub(r'\s*\[\w+\]\s*$', '', rule_body).strip() if option_match else rule_body
                elements = soup.select(selector)
                if not elements:
                    extracted_data[data_name] = "" if option != 'list' else []
                    continue
                if option == 'list':
                    extracted_data[data_name] = [el.get_text(strip=True) for el in elements]
                elif option in ['href', 'src', 'content']:
                    extracted_data[data_name] = elements[0].get(option, '')
                else:
                    main_element = elements[0]
                    paragraphs = main_element.find_all('p')
                    if paragraphs:
                        extracted_data[data_name] = "\\n\\n".join([p.get_text(strip=True) for p in paragraphs])
                    else:
                        extracted_data[data_name] = main_element.get_text(strip=True)
            except Exception as e:
                self.logger(f"Failed to process rule '{rule}': {e}", "WARN")
        return extracted_data
    def _execute_full_page_extract(self, payload: dict, config: dict, status_updater, ui_callback, mode='EXECUTE'):
        url_source_mode = config.get('url_source_mode', 'manual')
        target_url = ''
        if url_source_mode == 'dynamic':
            url_variable = config.get('url_source_variable')
            if not url_variable:
                raise ValueError("URL source variable is not set in dynamic mode.")
            target_url = get_nested_value(payload, url_variable)
        else:
            target_url = config.get('target_url', '')
        rules_source_mode = config.get('rules_source_mode', 'manual')
        rules_str = ''
        if rules_source_mode == 'dynamic':
            rules_variable = config.get('rules_source_variable')
            if not rules_variable:
                raise ValueError("Extraction rules source variable is not set in dynamic mode.")
            rules_str = get_nested_value(payload, rules_variable)
            self.logger(f"Dynamically loading extraction rules from payload variable: {rules_variable}", "INFO") # English Log
        else:
            rules_str = config.get('extraction_rules', '')
        fetch_only_html = config.get('fetch_only_html', False)
        exclude_str = config.get('exclude_selectors', '')
        wait_time = int(config.get('wait_time', 5))
        is_headless = bool(config.get('headless_mode', True))
        use_cache = bool(config.get('use_cache', True))
        if not target_url or not str(target_url).startswith('http'):
            error_msg = f"Target URL is invalid or empty. Received: '{target_url}'"
            status_updater(error_msg, "ERROR")
            raise ValueError(error_msg)
        cache_filename = hashlib.md5(str(target_url).encode('utf-8')).hexdigest() + ".html"
        cache_filepath = os.path.join(self.cache_path, cache_filename)
        html_content = None
        if use_cache and os.path.exists(cache_filepath) and mode == 'EXECUTE':
            self.logger(f"Cache HIT for {target_url}. Reading from file.", "SUCCESS")
            status_updater("Reading from cache...", "INFO")
            with open(cache_filepath, 'r', encoding='utf-8') as f:
                html_content = f.read()
        if html_content is None:
            self.logger(f"Cache MISS for {target_url}. Fetching from web.", "WARN")
            driver = None
            try:
                status_updater("Initializing browser driver...", "INFO")
                options = webdriver.ChromeOptions()
                if is_headless: options.add_argument("--headless")
                options.add_argument("--disable-gpu")
                options.add_argument("--window-size=1920,1200")
                options.add_argument("--ignore-certificate-errors")
                options.add_argument("--disable-extensions")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
                try:
                    service = Service(ChromeDriverManager().install())
                    driver = webdriver.Chrome(service=service, options=options)
                except Exception as e:
                    self.logger(f"Failed to initialize ChromeDriverManager: {e}", "ERROR")
                    self.logger("Please ensure you have a stable internet connection or chromedriver is in your PATH.", "ERROR")
                    raise RuntimeError(f"Could not initialize browser driver: {e}")
                status_updater(f"Navigating to {target_url}...", "INFO")
                driver.get(target_url)
                status_updater(f"Waiting for {wait_time}s for page to load...", "INFO")
                time.sleep(wait_time)
                html_content = driver.page_source
                if use_cache and mode == 'EXECUTE':
                    with open(cache_filepath, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    self.logger(f"Saved page content to cache: {cache_filepath}", "INFO")
            finally:
                if driver:
                    status_updater("Closing browser...", "INFO")
                    driver.quit()
        if fetch_only_html:
            self.logger("Fetch Only HTML mode is active. Returning raw HTML content.", "INFO") # English Log
            status_updater("Raw HTML fetched.", "SUCCESS") # English Log
            if 'data' not in payload or not isinstance(payload['data'], dict):
                payload['data'] = {}
            payload['data']['html_content'] = html_content
            return {"payload": payload, "output_name": "success"}
        try:
            status_updater("Cleaning and extracting data...", "INFO")
            extracted_data = self._perform_extraction(html_content, rules_str, exclude_str)
            if 'data' not in payload or not isinstance(payload['data'], dict):
                payload['data'] = {}
            payload['data']['scraped_data'] = extracted_data
            status_updater("Extraction successful!", "SUCCESS")
            return {"payload": payload, "output_name": "success"}
        except Exception as e:
            error_msg = f"An error occurred during data extraction: {e}"
            self.logger(error_msg, "ERROR")
            status_updater("Error during extraction", "ERROR")
            raise e
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        config = get_current_config()
        property_vars = {}
        run_mode_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('prop_run_mode_label'))
        run_mode_frame.pack(fill='x', padx=5, pady=10)
        property_vars['run_mode'] = StringVar(value=config.get('run_mode', 'extract_full_page'))
        full_page_extract_frame = ttk.Frame(parent_frame)
        interaction_steps_frame = ttk.Frame(parent_frame)
        def _toggle_run_mode_ui():
            if property_vars['run_mode'].get() == 'extract_full_page':
                interaction_steps_frame.pack_forget()
                full_page_extract_frame.pack(fill='both', expand=True)
            else:
                full_page_extract_frame.pack_forget()
                interaction_steps_frame.pack(fill='both', expand=True)
        ttk.Radiobutton(run_mode_frame, text=self.loc.get('run_mode_option_extract'), variable=property_vars['run_mode'], value='extract_full_page', command=_toggle_run_mode_ui).pack(anchor='w', padx=5)
        ttk.Radiobutton(run_mode_frame, text=self.loc.get('run_mode_option_interact'), variable=property_vars['run_mode'], value='perform_interaction_steps', command=_toggle_run_mode_ui).pack(anchor='w', padx=5)
        source_frame = ttk.LabelFrame(full_page_extract_frame, text=self.loc.get('prop_url_source_mode_label'))
        source_frame.pack(fill='x', padx=5, pady=10)
        property_vars['url_source_mode'] = StringVar(value=config.get('url_source_mode', 'manual'))
        manual_url_frame = ttk.Frame(source_frame)
        dynamic_url_frame = ttk.Frame(source_frame)
        def _toggle_url_source():
            if property_vars['url_source_mode'].get() == 'manual':
                manual_url_frame.pack(fill='x', padx=5, pady=5)
                dynamic_url_frame.pack_forget()
            else:
                manual_url_frame.pack_forget()
                dynamic_url_frame.pack(fill='x', padx=5, pady=5)
        ttk.Radiobutton(source_frame, text=self.loc.get('prop_mode_manual'), variable=property_vars['url_source_mode'], value='manual', command=_toggle_url_source).pack(anchor='w', padx=5)
        ttk.Radiobutton(source_frame, text=self.loc.get('prop_mode_dynamic'), variable=property_vars['url_source_mode'], value='dynamic', command=_toggle_url_source).pack(anchor='w', padx=5)
        ttk.Label(manual_url_frame, text=self.loc.get('prop_target_url_label')).pack(fill='x')
        property_vars['target_url'] = StringVar(value=config.get('target_url', 'https://'))
        ttk.Entry(manual_url_frame, textvariable=property_vars['target_url']).pack(fill='x')
        property_vars['url_source_variable'] = StringVar(value=config.get('url_source_variable', ''))
        LabelledCombobox(
            parent=dynamic_url_frame,
            label_text=self.loc.get('prop_url_source_variable_label'),
            variable=property_vars['url_source_variable'],
            values=list(available_vars.keys())
        )
        _toggle_url_source()
        rules_source_frame = ttk.LabelFrame(full_page_extract_frame, text=self.loc.get('prop_extraction_rules_source_label', fallback="Extraction Rules Source"))
        rules_source_frame.pack(fill='x', padx=5, pady=5)
        property_vars['rules_source_mode'] = StringVar(value=config.get('rules_source_mode', 'manual'))
        manual_rules_frame = ttk.Frame(rules_source_frame)
        dynamic_rules_frame = ttk.Frame(rules_source_frame)
        def _toggle_rules_source():
            if property_vars['rules_source_mode'].get() == 'manual':
                manual_rules_frame.pack(fill='x', padx=5, pady=5)
                dynamic_rules_frame.pack_forget()
            else:
                manual_rules_frame.pack_forget()
                dynamic_rules_frame.pack(fill='x', padx=5, pady=5)
        ttk.Radiobutton(rules_source_frame, text=self.loc.get('prop_mode_manual'), variable=property_vars['rules_source_mode'], value='manual', command=_toggle_rules_source).pack(anchor='w', padx=5)
        ttk.Radiobutton(rules_source_frame, text=self.loc.get('prop_mode_dynamic'), variable=property_vars['rules_source_mode'], value='dynamic', command=_toggle_rules_source).pack(anchor='w', padx=5)
        ttk.Label(manual_rules_frame, text=self.loc.get('prop_extraction_rules_label')).pack(fill='x', pady=(5, 0))
        rules_editor = scrolledtext.ScrolledText(manual_rules_frame, height=8, font=("Consolas", 10))
        rules_editor.pack(fill="both", expand=True, pady=(0, 5))
        rules_editor.insert('1.0', config.get('extraction_rules', 'judul_artikel: article.detail h1.detail__title [text]\nisi_artikel: article.detail .detail__body-text [text]'))
        property_vars['extraction_rules'] = rules_editor
        property_vars['rules_source_variable'] = StringVar(value=config.get('rules_source_variable', 'data.generated_rules'))
        LabelledCombobox(
            parent=dynamic_rules_frame,
            label_text=self.loc.get('prop_rules_source_variable_label', fallback="Rules from Variable:"),
            variable=property_vars['rules_source_variable'],
            values=list(available_vars.keys())
        )
        _toggle_rules_source()
        ttk.Label(full_page_extract_frame, text=self.loc.get('prop_exclude_selectors_label')).pack(fill='x', padx=5, pady=(5, 0))
        exclude_editor = scrolledtext.ScrolledText(full_page_extract_frame, height=4, font=("Consolas", 10))
        exclude_editor.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        exclude_editor.insert('1.0', config.get('exclude_selectors', '.lihatjg\n.para_caption'))
        property_vars['exclude_selectors'] = exclude_editor
        interaction_rules_frame = ttk.LabelFrame(interaction_steps_frame, text=self.loc.get('prop_interaction_steps_label'))
        interaction_rules_frame.pack(fill='both', expand=True, padx=5, pady=10)
        interaction_help = self.loc.get('prop_interaction_steps_help')
        ttk.Label(interaction_rules_frame, text=interaction_help, wraplength=400, justify='left', bootstyle='secondary').pack(fill='x', padx=5, pady=5)
        interaction_editor = scrolledtext.ScrolledText(interaction_rules_frame, height=15, font=("Consolas", 10))
        interaction_editor.pack(fill="both", expand=True, padx=5, pady=5)
        interaction_editor.insert('1.0', config.get('interaction_steps', ''))
        property_vars['interaction_steps'] = interaction_editor
        common_config_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('prop_scraper_options_label', fallback="Scraper Options"))
        common_config_frame.pack(fill='x', padx=5, pady=10)
        property_vars['fetch_only_html'] = BooleanVar(value=config.get('fetch_only_html', False))
        fetch_html_check = ttk.Checkbutton(common_config_frame, text=self.loc.get('prop_fetch_only_html_label', fallback="Fetch Raw HTML Only (No Extraction)"), variable=property_vars['fetch_only_html'])
        fetch_html_check.pack(anchor='w', padx=10, pady=5)
        ToolTip(fetch_html_check).update_text(self.loc.get('prop_fetch_only_html_tooltip', fallback="If checked, this module will only get the page's HTML content and output it to 'data.html_content', ignoring all extraction rules."))
        wait_time_frame = ttk.Frame(common_config_frame)
        wait_time_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(wait_time_frame, text=self.loc.get('prop_wait_time_label')).pack(side='left', padx=(0,5))
        property_vars['wait_time'] = IntVar(value=config.get('wait_time', 5))
        wait_entry = ttk.Entry(wait_time_frame, textvariable=property_vars['wait_time'], width=5)
        wait_entry.pack(side='left')
        ToolTip(wait_entry).update_text("Time to wait for the page's JavaScript to finish loading before scraping.")
        property_vars['headless_mode'] = BooleanVar(value=config.get('headless_mode', True))
        headless_check = ttk.Checkbutton(common_config_frame, text=self.loc.get('prop_headless_mode_label'), variable=property_vars['headless_mode'])
        headless_check.pack(anchor='w', padx=10, pady=5)
        ToolTip(headless_check).update_text("If checked, the browser will run invisibly in the background.")
        property_vars['use_cache'] = BooleanVar(value=config.get('use_cache', True))
        cache_check = ttk.Checkbutton(common_config_frame, text=self.loc.get('prop_use_cache_label'), variable=property_vars['use_cache'])
        cache_check.pack(anchor='w', padx=10, pady=5)
        ToolTip(cache_check).update_text("If checked, saves a local copy of the page to speed up subsequent runs on the same URL.")
        ttk.Separator(parent_frame).pack(fill='x', pady=15, padx=5)
        debug_vars = shared_properties.create_debug_and_reliability_ui(parent_frame, config, self.loc)
        property_vars.update(debug_vars)
        loop_vars = shared_properties.create_loop_settings_ui(parent_frame, config, self.loc, available_vars)
        property_vars.update(loop_vars)
        _toggle_run_mode_ui() # (ADDED) Initialize the correct view
        return property_vars
    def get_dynamic_output_schema(self, config):
        schema = []
        if config.get('fetch_only_html', False):
            schema.append({
                "name": "data.html_content",
                "type": "string",
                "description": "The raw HTML content of the scraped page."
            })
        else:
            schema.append({
                "name": "data.scraped_data",
                "type": "object",
                "description": "A dictionary containing all scraped data."
            })
            rules_str = config.get('extraction_rules', '')
            rules = [line.strip() for line in rules_str.split('\n') if line.strip()]
            for rule in rules:
                parts = rule.split(':', 1)
                if len(parts) == 2:
                    data_name = parts[0].strip()
                    schema.append({
                        "name": f"data.scraped_data.{data_name}",
                        "type": "string",
                        "description": f"Data for '{data_name}' scraped from the web."
                    })
        return schema
    def get_data_preview(self, config: dict):
        run_mode = config.get('run_mode', 'extract_full_page')
        if run_mode == 'perform_interaction_steps':
            return [{'status': 'preview_not_available', 'reason': 'Interaction steps involve live browser actions and cannot be previewed.'}]
        target_url = config.get('target_url')
        rules_str = config.get('extraction_rules', '')
        if not target_url or not target_url.startswith('http'):
            return [{"error": "Invalid or empty URL for preview."}]
        try:
            response = self.kernel.network.get(target_url, caller_module_id=self.module_id, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            rules = [line.strip() for line in rules_str.split('\n') if line.strip()]
            if not rules:
                return [{"status": "No extraction rules defined."}]
            is_list_scrape = any('[list]' in rule for rule in rules)
            if is_list_scrape:
                first_rule_selector = rules[0].split(':', 1)[1].strip().split('[')[0].strip()
                parent_selector_parts = first_rule_selector.split(' ')
                parent_selector = " ".join(parent_selector_parts[:-1]) if len(parent_selector_parts) > 1 else first_rule_selector
                containers = soup.select(parent_selector)[:5]
                preview_data = []
                for container in containers:
                    item_data = {}
                    for rule in rules:
                        data_name, rule_body = rule.split(':', 1)
                        data_name = data_name.strip()
                        option_match = re.search(r'\\[(\\w+)\\]', rule_body)
                        option = option_match.group(1) if option_match else 'text'
                        selector = re.sub(r'\\s*\\[\\w+\\]\\s*$', '', rule_body).strip()
                        element = container.select_one(selector.replace(parent_selector, '').strip())
                        if element:
                            item_data[data_name] = element.get_text(strip=True) if option == 'text' else element.get(option, '')
                        else:
                            item_data[data_name] = None
                    preview_data.append(item_data)
                return preview_data
            else:
                preview_data = {}
                for rule in rules:
                    data_name, rule_body = rule.split(':', 1)
                    data_name = data_name.strip()
                    option_match = re.search(r'\\[(\\w+)\\]', rule_body)
                    option = option_match.group(1) if option_match else 'text'
                    selector = re.sub(r'\\s*\\[\\w+\\]\\s*$', '', rule_body).strip()
                    element = soup.select_one(selector)
                    if element:
                        preview_data[data_name] = element.get_text(strip=True) if option == 'text' else element.get(option, '')
                    else:
                        preview_data[data_name] = "Not Found"
                return [preview_data]
        except Exception as e:
            return [{"error": f"Preview failed: {str(e)}"}]
