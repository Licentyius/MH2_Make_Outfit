"""
MakeHuman 2 Studio Outfit Presets Extension V1.2 by Elvaerwyn_MH2 2026
Saves and loads complete character clothing ensembles and creation information with simple clicks
"""

import os
import json
import getpass
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
                             QListWidgetItem, QPushButton, QLabel, QInputDialog, 
                             QMessageBox, QDialog, QFormLayout, QLineEdit, QTextBrowser, QDockWidget)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap

# --- GLOBAL TRACKING POINTERS ---
_active_outfit_panel_instance = None
_dock_container_instance = None  
_saved_app_context = None
_saved_glob_context = None

def initialize_outfit_studio(app_reference, glob_reference):
    global _active_outfit_panel_instance, _dock_container_instance, _saved_app_context, _saved_glob_context
    from PySide6.QtWidgets import QApplication, QMainWindow
    
    _saved_app_context = QApplication.instance() or app_reference
    _saved_glob_context = glob_reference

    main_window = None
    for widget in _saved_app_context.topLevelWidgets():
        if isinstance(widget, QMainWindow) or widget.objectName() == "mainwindow" or hasattr(widget, "central_widget"):
            main_window = widget
            break
    if not main_window:
        main_window = app_reference

    if _dock_container_instance is not None:
        if _dock_container_instance.isVisible():
            _dock_container_instance.hide()
            return {"status": "outfit_studio_inactive"}
        else:
            _dock_container_instance.show()
            _dock_container_instance.raise_()
            return {"status": "outfit_studio_active"}

    _active_outfit_panel_instance = MakeOutfitPanel(main_window, glob_reference)

    if main_window:
        _dock_container_instance = QDockWidget("Studio Outfit Sets Manager", main_window)
        _dock_container_instance.setObjectName("mh2_outfit_presets_dock_frame")
        _dock_container_instance.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable)
        _dock_container_instance.resize(450, 720)
        _dock_container_instance.setWidget(_active_outfit_panel_instance)
        
        _dock_container_instance.visibilityChanged.connect(handle_extension_toggle_state)
        
        main_window.addDockWidget(Qt.RightDockWidgetArea, _dock_container_instance)
        _dock_container_instance.show()
    else:
        _active_outfit_panel_instance.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        _active_outfit_panel_instance.show()

    glob_reference.mh2_active_outfit_studio_dock = _dock_container_instance
    return {"status": "outfit_studio_active"}

def handle_extension_toggle_state(visible):
    global _saved_glob_context
    if not visible:
        if _saved_glob_context and hasattr(_saved_glob_context, 'extensions_status_map'):
            try:
                _saved_glob_context.extensions_status_map["official_make_outfit"] = "outfit_studio_inactive"
            except Exception: pass

def unload_outfit_extension():
    """ Decooupled cleanup pipeline """
    global _active_outfit_panel_instance, _dock_container_instance, _saved_glob_context
    
    if _saved_glob_context and hasattr(_saved_glob_context, 'mh2_active_outfit_studio_dock'):
        _saved_glob_context.mh2_active_outfit_studio_dock = None

    if _dock_container_instance is not None:
        try:
            _dock_container_instance.setWidget(None)
            _dock_container_instance.close()
            _dock_container_instance.deleteLater()
        except Exception:
            pass
        _dock_container_instance = None

    if _active_outfit_panel_instance is not None:
        try:
            _active_outfit_panel_instance.close()
            _active_outfit_panel_instance.deleteLater()
        except Exception:
            pass
        _active_outfit_panel_instance = None
        
    print("[Outfit Studio] Extension successfully unloaded and memory cleared.")

class MakeOutfitPanel(QWidget):
    def __init__(self, main_window, glob_reference):
        super().__init__()
        self.main_window = main_window
        self.glob = glob_reference
        
        if hasattr(main_window, "env"):
            self.env = main_window.env
            self.outfits_dir = os.path.normpath(os.path.join(self.env.stdUserPath(), "outfit_presets")).replace("\\", "/")
        else:
            import core.globenv as mhenv
            self.env = mhenv  
            self.outfits_dir = os.path.normpath(os.path.join(mhenv.stdUserPath(), "outfit_presets")).replace("\\", "/")
            
        self.scanned_outfits = {}
        self.init_ui()
        self.scan_outfits_folder()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(8, 8, 8, 8)

        theme_button_style = """
            QPushButton {
                font-weight: bold;
                padding: 6px;
                border: 1px solid;
                border-color: qproperty-borderColor, rgba(255, 255, 255, 0.15);
                border-radius: 4px;
            }
            QPushButton:hover {
                border-color: qproperty-highlightColor, rgba(255, 255, 255, 0.45);
            }
        """
        self.setStyleSheet(theme_button_style)

        # --- OFFICIAL METADATA & SNAPSHOT ROW ---
        meta_group = QHBoxLayout()
        current_username = getpass.getuser()
        self.meta_author = QLabel(f"<b>Default Profile:</b> {current_username}")
        meta_group.addWidget(self.meta_author)
        meta_group.addStretch()

        camera_icon_path = os.path.join(self.env.path_sysicon, "camera.png").replace("\\", "/")
        try:
            from gui.widgets import IconButton 
            self.camera_btn = IconButton(1, camera_icon_path, "Take Preset Thumbnail", self.capture_manual_thumbnail)
        except Exception:
            self.camera_btn = QPushButton("📷 Snap")
            if os.path.exists(camera_icon_path):
                self.camera_btn.setIcon(QIcon(camera_icon_path))
            self.camera_btn.clicked.connect(self.capture_manual_thumbnail)
            
        meta_group.addWidget(self.camera_btn)
        layout.addLayout(meta_group)

        # --- VISUAL METADATA PARSE TICKER ---
        layout.addWidget(QLabel("<b>Selected Preset Properties:</b>"))
        self.metadata_display = QTextBrowser()
        self.metadata_display.setMaximumHeight(90)
        self.metadata_display.setHtml("<i style='color:#888888;'>Click a saved outfit preset below to review details...</i>")
        layout.addWidget(self.metadata_display)

        # --- PRESETS LIST ---
        layout.addWidget(QLabel("<b>Saved Outfit Sets:</b>"))
        self.outfit_list = QListWidget()
        self.outfit_list.setViewMode(QListWidget.IconMode)
        self.outfit_list.setResizeMode(QListWidget.Adjust)
        self.outfit_list.setMovement(QListWidget.Static)
        
        self.outfit_list.itemClicked.connect(self.display_selected_metadata)
        self.outfit_list.itemDoubleClicked.connect(self.load_selected_outfit)
        layout.addWidget(self.outfit_list)
        
        # --- EQUIP PRESSED SELECTION BUTTON ---
        self.equip_btn = QPushButton("👗 Equip Selected Outfit Set")
        self.equip_btn.clicked.connect(lambda: self.load_selected_outfit(self.outfit_list.currentItem()))
        layout.addWidget(self.equip_btn)

        # --- REMOVE OUTFIT BUTTON ACTION ROW ---
        action_layout = QHBoxLayout()
        clear_btn = QPushButton("👕 Take Off Whole Outfit")
        clear_btn.clicked.connect(lambda: self.clear_entire_wardrobe(silent=False))
        action_layout.addWidget(clear_btn)
        layout.addLayout(action_layout)
        
        # --- CONTROL BUTTONS ---
        btn_layout = QVBoxLayout()
        row1 = QHBoxLayout()
        row2 = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Refresh List")
        refresh_btn.clicked.connect(self.scan_outfits_folder)
        row1.addWidget(refresh_btn)
        
        save_btn = QPushButton("💾 Save Current Outfit")
        save_btn.clicked.connect(self.capture_current_outfit)
        row1.addWidget(save_btn)

        rename_btn = QPushButton("✏️ Rename Outfit")
        rename_btn.clicked.connect(self.rename_selected_outfit)
        row2.addWidget(rename_btn)

        self.delete_btn = QPushButton("❌ Delete Outfit")
        self.delete_btn.clicked.connect(self.delete_selected_outfit)
        row2.addWidget(self.delete_btn)
        
        btn_layout.addLayout(row1)
        btn_layout.addLayout(row2)
        layout.addLayout(btn_layout)

    def scan_outfits_folder(self):
        self.outfit_list.clear()
        self.scanned_outfits.clear()
        self.metadata_display.setHtml("<i style='color:#888888;'>Click a saved outfit preset below to review details...</i>")
        
        if not os.path.exists(self.outfits_dir):
            try: os.makedirs(self.outfits_dir)
            except Exception: pass

        if os.path.isdir(self.outfits_dir):
            self.outfit_list.setIconSize(QSize(64, 64))

            for filename in os.listdir(self.outfits_dir):
                if filename.lower().endswith('.json'):
                    full_path = os.path.join(self.outfits_dir, filename).replace("\\", "/")
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            name = data.get("outfit_name", filename)
                            self.scanned_outfits[name] = data
                            
                            base_name = os.path.splitext(filename)[0]
                            possible_thumb_path = os.path.join(self.outfits_dir, f"{base_name}.png").replace("\\", "/")
                            
                            item = QListWidgetItem()
                            item.setText(name)
                            item.setData(Qt.UserRole, name)

                            if os.path.exists(possible_thumb_path):
                                item.setIcon(QIcon(possible_thumb_path))
                            else:
                                fallback_icon_path = os.path.join(self.env.path_sysicon, "camera.png").replace("\\", "/")
                                if os.path.exists(fallback_icon_path):
                                    item.setIcon(QIcon(fallback_icon_path))
                                else:
                                    item.setText(f"📷 {name}")

                            self.outfit_list.addItem(item)
                    except Exception as scan_fault: 
                        print(f"⚠️ Failed reading preset item: {scan_fault}")

    def display_selected_metadata(self, item):
        if not item: return
        outfit_name = item.data(Qt.UserRole)
        config = self.scanned_outfits.get(outfit_name)
        if not config: return

        details = config.get("usage_details", {})
        time_day = details.get("time_of_day", "Unassigned")
        season = details.get("time_of_year", "Unassigned")
        event = details.get("event_usage", "Unassigned")
        age = details.get("expected_age", "Variable")
        gender = details.get("expected_gender", "Unisex")
        author = config.get("author", "Unknown")

        html_payload = f"""
        <b>Outfit Set:</b> {outfit_name}<br>
        <b>Creator / Author:</b> {author}<br>
        <b>Contextual Use:</b> {time_day} | {season} | {event}<br>
        <b>Demographics:</b> Age: {age} | Gender: {gender}
        """
        self.metadata_display.setHtml(html_payload)

    def clear_entire_wardrobe(self, silent=False):
        if not hasattr(self.main_window, 'equipment') or not self.main_window.equipment:
            return

        try:
            if not silent: 
                print("[Outfit Studio] Draining attached wardrobe array layers with eye exclusion...")
            
            attached_assets_list = []
            if hasattr(self.main_window, 'glob') and hasattr(self.main_window.glob, 'baseClass'):
                attached_assets_list = getattr(self.main_window.glob.baseClass, 'attachedAssets', [])
            elif hasattr(self.glob, 'baseClass'):
                attached_assets_list = getattr(self.glob.baseClass, 'attachedAssets', [])

            if attached_assets_list:
                safety_threshold = 200  
                while len(attached_assets_list) > 0 and safety_threshold > 0:
                    safety_threshold -= 1
                    elem = attached_assets_list[0]
                    if not elem:
                        attached_assets_list.pop(0)
                        continue
                        
                    asset_type = getattr(elem, 'type', '').lower()
                    
                    # DIRECT EXCLUSION RULE: Bypasses the removal loop if the asset is an eye mesh
                    if asset_type == "eyes":
                        # Move it to the back or pop it safely without triggering the deletion callback
                        attached_assets_list.pop(0)
                        continue

                    try:
                        for node in getattr(self.main_window, 'equipment', []):
                            if node.get('name') == asset_type and node.get('func'):
                                image_selector = node['func']
                                if hasattr(image_selector, 'callback'):
                                    image_selector.callback(elem.filename, asset_type, False)
                        if len(attached_assets_list) > 0 and attached_assets_list[0] == elem:
                            attached_assets_list.pop(0)
                    except Exception:
                        if len(attached_assets_list) > 0:
                            attached_assets_list.pop(0)

            class SafeMockUIElement:
                def __init__(self): self.status = 0
                def getSelected(self): return None
                def refreshAllWidgets(self): pass

            # Deep-clean all remaining interface category states sequentially
            for asset_node in self.main_window.equipment:
                if not asset_node or not isinstance(asset_node, dict): 
                    continue
                
                image_selector = asset_node.get('func')
                slot_name = str(asset_node.get('name', '')).lower()
                
                # Bypasses reset properties for the eyes category tab UI completely
                if slot_name == "eyes":
                    continue

                if image_selector:
                    if hasattr(image_selector, 'picwidget') and image_selector.picwidget is None:
                        image_selector.picwidget = SafeMockUIElement()
                    if hasattr(image_selector, 'parent') and image_selector.parent is None:
                        image_selector.parent = SafeMockUIElement()
                    if hasattr(image_selector, 'selected_asset') and image_selector.selected_asset is None:
                        image_selector.selected_asset = SafeMockUIElement()

                    if slot_name in ["hair", "teeth", "tongue", "mouth", "eyebrows", "eyelashes"]:
                        if hasattr(image_selector, 'asset_category') and image_selector.asset_category:
                            for asset in image_selector.asset_category: 
                                asset.status = 0

                    if hasattr(image_selector, 'noneCallback'):
                        try: 
                            image_selector.noneCallback()
                        except Exception:
                            if hasattr(image_selector, 'picButtonChanged'):
                                try: image_selector.picButtonChanged(None)
                                except Exception: pass
                    elif hasattr(image_selector, 'clearSelection'): 
                        image_selector.clearSelection()
                    elif hasattr(image_selector, 'picButtonChanged'):
                        try: image_selector.picButtonChanged(None)
                        except Exception: pass

                    if slot_name in ["hair", "teeth", "tongue", "mouth", "eyebrows", "eyelashes"]:
                        if hasattr(image_selector, 'selected_asset'): image_selector.selected_asset = None
                        if hasattr(image_selector, 'current_asset'): image_selector.current_asset = None

            if hasattr(self.main_window, 'glob') and hasattr(self.main_window.glob, 'openGLWindow'):
                self.main_window.glob.openGLWindow.Tweak()
        except Exception as strip_fault:
            print(f"⚠️ Error inside native clear wardrobe cycle: {strip_fault}")

    def load_selected_outfit(self, item):
        if not item: 
            QMessageBox.warning(self, "Selection Required", "Please click on a saved outfit set from the menu first.")
            return
        outfit_name = item.data(Qt.UserRole)
        config = self.scanned_outfits.get(outfit_name)
        if not config or "assets" not in config: return

        try:
            self.clear_entire_wardrobe(silent=True)
            self.display_selected_metadata(item)
            saved_wardrobe_slots = config["assets"]

            class SafeMockUIElement:
                def refreshAllWidgets(self): pass
                def getSelected(self): return None

            flat_file_pool = []
            for data_payload in saved_wardrobe_slots.values():
                paths = data_payload if isinstance(data_payload, list) else [data_payload]
                for p in paths:
                    if p and isinstance(p, str) and p not in flat_file_pool: flat_file_pool.append(p)

            for asset_file_path in flat_file_pool:
                if not asset_file_path or not isinstance(asset_file_path, str): continue
                target_full_path = asset_file_path
                
                if not os.path.isabs(target_full_path):
                    cleaned_relative_path = asset_file_path
                    if asset_file_path.startswith("data/"): cleaned_relative_path = asset_file_path[5:]
                    if hasattr(self, 'env') and hasattr(self.env, 'path_sysdata'):
                        target_full_path = os.path.normpath(os.path.join(self.env.path_sysdata, "..", asset_file_path)).replace("\\", "/")
                    if not os.path.exists(target_full_path):
                        target_full_path = os.path.normpath(os.path.join(self.outfits_dir, "..", cleaned_relative_path)).replace("\\", "/")

                if os.path.exists(target_full_path):
                    class DynamicStudioAsset:
                        def __init__(self, filepath):
                            self.filename = filepath
                            self.status = 1
                            self.selected = True
                            self.icon = None
                            self.thumb = None
                            self.material = ""
                            self.obj = self
                            filename_base = os.path.basename(filepath)
                            self.text = filename_base
                            
                            self.name = str(os.path.splitext(filename_base)[0])
                            self.basename = str(filename_base)
                            self.tags = []
                            self.description = "Outfit Studio Managed Asset"
                        def listAllMaterials(self): return []

                    runtime_asset_mock = DynamicStudioAsset(target_full_path)
                    clean_path_for_matching = target_full_path.lower()
                    
                    if "/data/" in clean_path_for_matching: searchable_segment = clean_path_for_matching.split("/data/")[-1]
                    else: searchable_segment = os.path.basename(clean_path_for_matching)

                    for node in getattr(self.main_window, 'equipment', []):
                        if not isinstance(node, dict): continue
                        image_selector = node.get('func')
                        if image_selector and hasattr(image_selector, 'callback') and hasattr(image_selector, 'type'):
                            is_target_tab = False
                            slot_name = str(node.get('name', '')).lower()
                            
                            if slot_name in searchable_segment: is_target_tab = True
                            elif "hair" in slot_name and "hair" in searchable_segment: is_target_tab = True
                            elif "clothes" in slot_name and ("clothes" in searchable_segment or "apparel" in searchable_segment): is_target_tab = True
                            elif slot_name in ["teeth", "tongue", "mouth", "eyes", "eyebrows", "eyelashes"] and slot_name in searchable_segment: is_target_tab = True

                            # PROTECT HUMAN STRUCTURES: Keep eyeball, tooth, and tongue meshes intact when outfits deploy
                            if is_target_tab:
                                if not getattr(image_selector, 'parent', None): image_selector.parent = SafeMockUIElement()
                                if not getattr(image_selector, 'picwidget', None): image_selector.picwidget = SafeMockUIElement()
                                if not getattr(image_selector, 'asset_category', None): image_selector.asset_category = []
                                
                                has_duplicate = False
                                for asset in image_selector.asset_category:
                                    if hasattr(asset, 'filename') and asset.filename == target_full_path:
                                        has_duplicate = True
                                        asset.status = 1
                                        if hasattr(image_selector, 'selected_asset'): image_selector.selected_asset = asset
                                        if hasattr(image_selector, 'current_asset'): image_selector.current_asset = asset
                                        break

                                if not has_duplicate:
                                    image_selector.asset_category.append(runtime_asset_mock)
                                    if hasattr(image_selector, 'selected_asset'): image_selector.selected_asset = runtime_asset_mock
                                    if hasattr(image_selector, 'current_asset'): image_selector.current_asset = runtime_asset_mock

                                multi_mode = getattr(image_selector, 'selmode', 0) == 1
                                try:
                                    image_selector.callback(runtime_asset_mock, image_selector.type, multi_mode)
                                    if hasattr(image_selector, 'changeStatus'): image_selector.changeStatus()
                                    if hasattr(image_selector, 'refreshButtons'): image_selector.refreshButtons()
                                except Exception:
                                    try: image_selector.callback(target_full_path, image_selector.type, multi_mode)
                                    except Exception: pass
                                break

            if hasattr(self.main_window, 'glob') and hasattr(self.main_window.glob, 'openGLWindow'):
                self.main_window.glob.openGLWindow.Tweak()
        except Exception as load_fault:
            print(f"[Outfit Studio Error] Character wardrobe initialization crashed: {load_fault}")

    def capture_current_outfit(self):
        if not hasattr(self.main_window, 'equipment') or not self.main_window.equipment:
            QMessageBox.warning(self, "No Items Equipped", "The character currently has no equipment structure initialized.")
            return

        attached_assets_list = []
        try:
            if hasattr(self.main_window, 'glob') and hasattr(self.main_window.glob, 'baseClass'):
                attached_assets_list = getattr(self.main_window.glob.baseClass, 'attachedAssets', [])
            elif hasattr(self.glob, 'baseClass'):
                attached_assets_list = getattr(self.glob.baseClass, 'attachedAssets', [])
        except Exception: 
            pass

        form_dialog = QDialog(self)
        form_dialog.setWindowTitle("Save Complete Character Outfit Profile")
        form_dialog.resize(360, 260)
        form_dialog.setWindowFlags(form_dialog.windowFlags() | Qt.WindowStaysOnTopHint)
        
        if hasattr(self, 'styleSheet'):
            form_dialog.setStyleSheet(self.styleSheet())
            
        form_layout = QFormLayout(form_dialog)

        txt_name = QLineEdit()
        txt_author = QLineEdit(getpass.getuser())
        txt_time = QLineEdit("Daytime")
        txt_year = QLineEdit("Summer")
        txt_usage = QLineEdit("Casual")
        txt_age = QLineEdit("Adult")
        txt_gender = QLineEdit("Unisex")

        form_layout.addRow("Outfit Preset Name:", txt_name)
        form_layout.addRow("Author / Creator:", txt_author)
        form_layout.addRow("Time of Day Use:", txt_time)
        form_layout.addRow("Time of Year / Season:", txt_year)
        form_layout.addRow("Usage Event / Occasion:", txt_usage)
        form_layout.addRow("Expected Target Age:", txt_age)
        form_layout.addRow("Expected Target Gender:", txt_gender)

        btn_box = QHBoxLayout()
        btn_ok = QPushButton("Save Outfit")
        btn_ok.clicked.connect(form_dialog.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(form_dialog.reject)
        btn_box.addWidget(btn_ok)
        btn_box.addWidget(btn_cancel)
        form_layout.addRow(btn_box)

        if form_dialog.exec() != QDialog.Accepted or not txt_name.text().strip():
            return

        outfit_name = txt_name.text().strip()
        clean_filename = "".join([c for c in outfit_name.lower() if c.isalnum() or c in (" ", "_", "-")]).replace(" ", "")

        target_file_path = os.path.join(self.outfits_dir, f"{clean_filename}.json").replace("\\", "/")

        if os.path.isfile(target_file_path):
            confirm_overwrite = QMessageBox.question(
                self, "Outfit Profile Exists", f"An outfit set named '{outfit_name}' already exists.\n\nOverwrite it?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm_overwrite == QMessageBox.No: 
                return

        unique_file_pool = set()
        captured_assets_dictionary = {}
        
        try:
            for elem in attached_assets_list:
                if elem and hasattr(elem, 'filename') and elem.filename:

                    unique_file_pool.add(os.path.normpath(str(elem.filename)).replace("\\", "/"))

            if not unique_file_pool:
                for asset_node in self.main_window.equipment:
                    if not asset_node or not isinstance(asset_node, dict): 
                        continue
                    image_selector = asset_node.get('func')
                    if image_selector and hasattr(image_selector, 'asset_category'):
                        for asset in image_selector.asset_category:
                            if getattr(asset, 'status', 0) == 1 or getattr(asset, 'selected', False):
                                if hasattr(asset, 'filename') and asset.filename:

                                    unique_file_pool.add(os.path.normpath(str(asset.filename)).replace("\\", "/"))

            for file_index, full_disk_path in enumerate(sorted(list(unique_file_pool))):
                clean_path = full_disk_path
                if "data/" in full_disk_path.lower(): 
                    clean_path = "data/" + full_disk_path.lower().split("data/")[-1]
                elif "makehuman2/" in full_disk_path.lower(): 
                    clean_path = "data/" + full_disk_path.lower().split("makehuman2/")[-1]
                captured_assets_dictionary[f"item_{file_index}"] = [clean_path]

            if not captured_assets_dictionary:
                QMessageBox.warning(self, "Extraction Error", "Could not locate any active assets inside the master attachedAssets list layer.")
                return

            outfit_profile_payload = {
                "outfit_name": outfit_name,
                "author": txt_author.text().strip(),
                "usage_details": {
                    "time_of_day": txt_time.text().strip(),
                    "time_of_year": txt_year.text().strip(),
                    "event_usage": txt_usage.text().strip(),
                    "expected_age": txt_age.text().strip(),
                    "expected_gender": txt_gender.text().strip()
                },
                "assets": captured_assets_dictionary
            }

            with open(target_file_path, 'w', encoding='utf-8') as json_file:
                json.dump(outfit_profile_payload, json_file, indent=4)

            thumbnail_path = os.path.join(self.outfits_dir, f"{clean_filename}.png").replace("\\", "/")
            self.generate_outfit_thumbnail(thumbnail_path)
            self.scan_outfits_folder()
            QMessageBox.information(self, "Outfit Saved!", f"Successfully captured outfit '{outfit_name}'!")
        except Exception as file_fault:
            print(f"[Outfit Studio Error] Failed to capture matrices: {file_fault}")

    def rename_selected_outfit(self):
        current_item = self.outfit_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Selection Required", "Please choose an outfit template from the array list view above to rename.")
            return
            
        old_outfit_name = current_item.data(Qt.UserRole)
        old_clean_filename = "".join([c for c in old_outfit_name.strip().lower() if c.isalnum() or c in (" ", "_", "-")]).replace(" ", "")
        
        new_outfit_name, confirmed = QInputDialog.getText(
            self, "Rename Outfit Profile", f"Provide a replacement title label for '{old_outfit_name}':", text=old_outfit_name
        )
        if not confirmed or not new_outfit_name.strip() or new_outfit_name.strip() == old_outfit_name:
            return
            
        new_clean_filename = "".join([c for c in new_outfit_name.strip().lower() if c.isalnum() or c in (" ", "_", "-")]).replace(" ", "")

        old_json_path = os.path.join(self.outfits_dir, f"{old_clean_filename}.json").replace("\\", "/")
        new_json_path = os.path.join(self.outfits_dir, f"{new_clean_filename}.json").replace("\\", "/")
        old_png_path = os.path.join(self.outfits_dir, f"{old_clean_filename}.png").replace("\\", "/")
        new_png_path = os.path.join(self.outfits_dir, f"{new_clean_filename}.png").replace("\\", "/")

        if os.path.exists(new_json_path):
            QMessageBox.critical(self, "Naming Conflict", "An outfit profile with that computed target file path already exists.")
            return

        try:
            if os.path.isfile(old_json_path):
                with open(old_json_path, 'r', encoding='utf-8') as f: 
                    data = json.load(f)
                data["outfit_name"] = new_outfit_name.strip()
                with open(old_json_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4)
                os.rename(old_json_path, new_json_path)
                if os.path.isfile(old_png_path):
                    os.rename(old_png_path, new_png_path)
                self.scan_outfits_folder()
        except Exception as rename_error:
            print(f"⚠️ Error executing configuration track rename operation loop: {rename_error}")

    def capture_manual_thumbnail(self):
        """ Captures a viewport screenshot and instantly refreshes the preset grid display icons """
        selected_items = self.outfit_list.selectedItems()
        if not selected_items: 
            QMessageBox.warning(self, "Selection Required", "Please click on a saved outfit set from the grid menu first to apply the snapshot thumbnail.")
            return
            
        outfit_name = selected_items[0].data(Qt.UserRole)
        clean_filename = "".join([c for c in outfit_name.strip().lower() if c.isalnum() or c in (" ", "_", "-")]).replace(" ", "")
        thumbnail_path = os.path.join(self.outfits_dir, f"{clean_filename}.png").replace("\\", "/")
        
        # Execute viewport image rendering pass
        self.generate_outfit_thumbnail(thumbnail_path)
        
        # AUTO-REFRESH
        self.scan_outfits_folder()

    def generate_outfit_thumbnail(self, output_png_path):
        from PySide6.QtGui import QPixmap
        try:
            view_handle = None
            if hasattr(self.main_window, 'glob') and hasattr(self.main_window.glob, 'openGLWindow'):
                view_handle = self.main_window.glob.openGLWindow
            elif hasattr(self.glob, 'openGLWindow'): 
                view_handle = self.glob.openGLWindow
                
            if view_handle and hasattr(view_handle, 'createThumbnail'):
                native_image = view_handle.createThumbnail()

                if native_image and not native_image.isNull():
                    pixmap = QPixmap.fromImage(native_image)
                    side_length = min(pixmap.width(), pixmap.height())
                    x_offset = (pixmap.width() - side_length) // 2
                    y_offset = (pixmap.height() - side_length) // 2
                    square_thumbnail = pixmap.copy(x_offset, y_offset, side_length, side_length)
                    final_scaled_thumb = square_thumbnail.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    final_scaled_thumb.save(output_png_path, "PNG")
        except Exception as system_rendering_fault:
            print(f"⚠️ Viewport screenshot failed: {system_rendering_fault}")

    def delete_selected_outfit(self):
        current_item = self.outfit_list.currentItem()
        if not current_item: return
        outfit_name = current_item.data(Qt.UserRole)
        if not outfit_name: return
        confirm_delete = QMessageBox.question(
            self, "Confirm Delete", f"Permanently delete outfit preset '{outfit_name}'?", QMessageBox.Yes | QMessageBox.No
        )
        if confirm_delete == QMessageBox.No: 
            return
            
        clean_filename = "".join([c for c in outfit_name.strip().lower() if c.isalnum() or c in (" ", "_", "-")]).replace(" ", "")
        
        target_file_path = os.path.join(self.outfits_dir, f"{clean_filename}.json").replace("\\", "/")
        
        try:
            if os.path.isfile(target_file_path): 
                os.remove(target_file_path)
 
            thumb_file_path = os.path.join(self.outfits_dir, f"{clean_filename}.png").replace("\\", "/")
            if os.path.isfile(thumb_file_path): 
                os.remove(thumb_file_path)
                
            self.scan_outfits_folder()
        except Exception as delete_fault:
            print(f"[Outfit Studio Error] File removal failed: {delete_fault}")
     
