"""
MakeHuman 2 Official Studio Outfit Presets Plugin V1.0 by Elvaerwyn_MH2 2026
Saves and loads complete character clothing ensembles with simple clicks
"""

import os
import json
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
                             QListWidgetItem, QPushButton, QLabel, QInputDialog, QMessageBox)
from PySide6.QtCore import Qt

def initialize_outfit_studio(app_reference, glob_reference):
    from PySide6.QtWidgets import QApplication, QMainWindow, QDockWidget
    
    main_window = None
    for widget in QApplication.topLevelWidgets():
        if isinstance(widget, QMainWindow) or widget.objectName() == "mainwindow" or hasattr(widget, "central_widget"):
            main_window = widget
            break
    if not main_window:
        main_window = app_reference

    # Clean up old references
    unique_object_name = "mh2_outfit_presets_dock_frame"
    if hasattr(glob_reference, "mh2_active_outfit_studio_dock"):
        try:
            old_dock = getattr(glob_reference, "mh2_active_outfit_studio_dock")
            if old_dock:
                old_dock.close()
                old_dock.deleteLater()
        except Exception:
            pass

    dock_frame = QDockWidget("Studio Outfit Sets Manager", main_window)
    dock_frame.setObjectName(unique_object_name)
    dock_frame.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable)
    dock_frame.resize(450, 600)

    panel_ui = MakeOutfitPanel(main_window, glob_reference)
    dock_frame.setWidget(panel_ui)

    if hasattr(main_window, "addDockWidget"):
        main_window.addDockWidget(Qt.RightDockWidgetArea, dock_frame)
        dock_frame.setFloating(False) 
    else:
        dock_frame.setFloating(True)

    glob_reference.mh2_active_outfit_studio_dock = dock_frame
    dock_frame.show()
    return True

class MakeOutfitPanel(QWidget):
    def __init__(self, main_window, glob_reference):
        super().__init__()
        self.main_window = main_window
        self.glob = glob_reference
        
        # Force lookups
        if hasattr(main_window, "env"):
            self.env = main_window.env
            self.outfits_dir = os.path.normpath(os.path.join(self.env.stdUserPath(), "outfit_presets")).replace("\\", "/")
        else:
            # Fallback directly to the framework's global reference layer if environment is detached
            import core.globenv as mhenv
            self.env = mhenv  
            self.outfits_dir = os.path.normpath(os.path.join(mhenv.stdUserPath(), "outfit_presets")).replace("\\", "/")
            
        self.scanned_outfits = {}
        self.init_ui()
        self.scan_outfits_folder()

    def init_ui(self):
        import getpass  # dynamically get the local OS username safely
        
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(8, 8, 8, 8)

        # --- OFFICIAL METADATA & SNAPSHOT ROW ---
        meta_group = QHBoxLayout()
        
        # Dynamic check: Use current system username instead of hardwired
        current_username = getpass.getuser()
        self.meta_author = QLabel(f"<b>Author:</b> {current_username}")
        meta_group.addWidget(self.meta_author)
        meta_group.addStretch()

        camera_icon_path = os.path.join(self.env.path_sysicon, "camera.png").replace("\\", "/")
        
        try:
            from gui.widgets import IconButton 
            self.camera_btn = IconButton(1, camera_icon_path, "Take Preset Thumbnail", self.capture_manual_thumbnail)
        except Exception:
            self.camera_btn = QPushButton("📷 Snap")
            if os.path.exists(camera_icon_path):
                from PySide6.QtGui import QIcon
                self.camera_btn.setIcon(QIcon(camera_icon_path))
            self.camera_btn.setToolTip("Take Official Preset Thumbnail Shot")
            self.camera_btn.clicked.connect(self.capture_manual_thumbnail)
            
        meta_group.addWidget(self.camera_btn)
        layout.addLayout(meta_group)

        # --- PRESETS LIST ---
        layout.addWidget(QLabel("<b>Saved Outfit Sets:</b>"))
        self.outfit_list = QListWidget()
        
        # Configure IconMode BEFORE adding to layout
        self.outfit_list.setViewMode(QListWidget.IconMode)
        self.outfit_list.setResizeMode(QListWidget.Adjust)
        self.outfit_list.setMovement(QListWidget.Static)
        
        self.outfit_list.itemDoubleClicked.connect(self.load_selected_outfit)
        layout.addWidget(self.outfit_list)
        
        # --- REMOVE OUTFIT BUTTON ACTION ROW ---
        action_layout = QHBoxLayout()
        clear_btn = QPushButton("👕 Take Off Whole Outfit")
        clear_btn.setStyleSheet("font-weight: bold; background-color: #4A5568; color: #FFFFFF; padding: 4px;")
        clear_btn.clicked.connect(lambda: self.clear_entire_wardrobe(silent=False))
        action_layout.addWidget(clear_btn)
        layout.addLayout(action_layout)
        
        # --- CONTROL BUTTONS ---
        btn_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Refresh List")
        refresh_btn.clicked.connect(self.scan_outfits_folder)
        btn_layout.addWidget(refresh_btn)
        
        save_btn = QPushButton("👗 Save Current Outfit")
        save_btn.setStyleSheet("font-weight: bold; background-color: #2D5A27; color: #FFFFFF;")
        save_btn.clicked.connect(self.capture_current_outfit)
        btn_layout.addWidget(save_btn)

        self.delete_btn = QPushButton("❌ Delete Outfit")
        self.delete_btn.setStyleSheet("font-weight: bold; background-color: #A13D3D; color: #FFFFFF;")
        self.delete_btn.clicked.connect(self.delete_selected_outfit)
        btn_layout.addWidget(self.delete_btn)
        
        layout.addLayout(btn_layout)

    def scan_outfits_folder(self):
        self.outfit_list.clear()
        self.scanned_outfits.clear()
        
        if not os.path.exists(self.outfits_dir):
            try: os.makedirs(self.outfits_dir)
            except Exception: pass

        if os.path.isdir(self.outfits_dir):
            from PySide6.QtGui import QIcon
            from PySide6.QtCore import QSize

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

    def clear_entire_wardrobe(self, silent=False):
        """
        clear function with an integrated global memory sweep 
        to ensure hair etc slots drop cleanly off the mesh.
        """
        if not hasattr(self.main_window, 'equipment') or not self.main_window.equipment:
            return

        try:
            if not silent: print("[Outfit Studio] Purging all active garments off avatar mesh via noneCallback...")
            
            # GLOBAL MEMORY SWEEP: 
            attached_assets_list = []
            if hasattr(self.main_window, 'glob') and hasattr(self.main_window.glob, 'baseClass'):
                attached_assets_list = getattr(self.main_window.glob.baseClass, 'attachedAssets', [])
            elif hasattr(self.glob, 'baseClass'):
                attached_assets_list = getattr(self.glob.baseClass, 'attachedAssets', [])

            # Loop backwards through the master engine list to delete hair etc entries safely
            if attached_assets_list:
                for i in range(len(attached_assets_list) - 1, -1, -1):
                    elem = attached_assets_list[i]
                    if elem and getattr(elem, 'type', '').lower() == 'hair':
                        try:
                            # Use the native callback handler to tell the engine to drop the mesh
                            for node in getattr(self.main_window, 'equipment', []):
                                if node.get('name') == 'hair' and node.get('func'):
                                    image_selector = node['func']
                                    if hasattr(image_selector, 'callback'):
                                        image_selector.callback(elem.filename, 'hair', False)
                            attached_assets_list.pop(i)
                        except Exception:
                            pass

            # Safe mock structure to absorb native getSelected exceptions safely
            class SafeMockUIElement:
                def __init__(self):
                    self.status = 0
                def getSelected(self): return None
                def refreshAllWidgets(self): pass

            for asset_node in self.main_window.equipment:
                if not asset_node or not isinstance(asset_node, dict):
                    continue
                
                image_selector = asset_node.get('func')
                slot_name = str(asset_node.get('name', '')).lower()
                
                if image_selector:
                    # THE SAFETY GUARD: If the engine lacks a visual picwidget, give it our safe mock
                    if hasattr(image_selector, 'picwidget') and image_selector.picwidget is None:
                        image_selector.picwidget = SafeMockUIElement()
                    if hasattr(image_selector, 'parent') and image_selector.parent is None:
                        image_selector.parent = SafeMockUIElement()
                    if hasattr(image_selector, 'selected_asset') and image_selector.selected_asset is None:
                        image_selector.selected_asset = SafeMockUIElement()

                    # Reset hair etc specific layout variables to clear slot tracking references
                    if "hair" in slot_name:
                        if hasattr(image_selector, 'asset_category') and image_selector.asset_category:
                            for asset in image_selector.asset_category:
                                asset.status = 0

                    # Trigger your official asset drop procedure safely
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

                    # Clear references AFTER the engine completes its callback processing
                    if "hair" in slot_name:
                        if hasattr(image_selector, 'selected_asset'): image_selector.selected_asset = None
                        if hasattr(image_selector, 'current_asset'): image_selector.current_asset = None

            if hasattr(self.main_window, 'glob') and hasattr(self.main_window.glob, 'openGLWindow'):
                self.main_window.glob.openGLWindow.Tweak()
            
            if not silent:
                print("[Outfit Studio] Character cleared completely via native drop pipeline.")
        except Exception as strip_fault:
            print(f"⚠️ Error occurred inside native clear wardrobe cycle: {strip_fault}")

    def load_selected_outfit(self, item):
        if not item:
            return
        outfit_name = item.data(Qt.UserRole)
        config = self.scanned_outfits.get(outfit_name)
        if not config or "assets" not in config:
            return

        try:
            self.clear_entire_wardrobe(silent=True)
            print(f"[Outfit Studio] Restoring full layered ensemble: {outfit_name}")
            saved_wardrobe_slots = config["assets"]

            class SafeMockUIElement:
                def refreshAllWidgets(self): pass
                def getSelected(self): return None

            # Unpack all paths and guarantee they are processed as clean text strings
            flat_file_pool = []
            for data_payload in saved_wardrobe_slots.values():
                paths = data_payload if isinstance(data_payload, list) else [data_payload]
                for p in paths:
                    if p and isinstance(p, str) and p not in flat_file_pool:
                        flat_file_pool.append(p)

            # Broadcast every file directly
            for asset_file_path in flat_file_pool:
                if not asset_file_path or not isinstance(asset_file_path, str):
                    continue

                target_full_path = asset_file_path
                
                # Reconstruct relative links 
                if not os.path.isabs(target_full_path):
                    cleaned_relative_path = asset_file_path
                    if asset_file_path.startswith("data/"):
                        cleaned_relative_path = asset_file_path[5:]
                    
                    # Target 1: Stitch directly onto MakeHuman 2's application root path string
                    if hasattr(self, 'env') and hasattr(self.env, 'path_sysdata'):
                        target_full_path = os.path.normpath(os.path.join(self.env.path_sysdata, "..", asset_file_path)).replace("\\", "/")
                    
                    # Target 2: Fallback check against your active disk presets path folder
                    if not os.path.exists(target_full_path):
                        target_full_path = os.path.normpath(os.path.join(self.outfits_dir, "..", cleaned_relative_path)).replace("\\", "/")

                if os.path.exists(target_full_path):
                    print(f"  -> Broadcast mounting verified path: {target_full_path}")
                    
                    # Provide every string property the UI button needs
                    class DynamicStudioAsset:
                        def __init__(self, filepath):
                            self.filename = filepath
                            self.status = 1
                            self.selected = True
                            self.icon = None
                            self.thumb = None
                            self.material = ""
                            self.obj = self  # Safe self-referencing dummy fallback structure
                            
                            filename_base = os.path.basename(filepath)
                            self.text = filename_base
                            # Extract the string from the split tuple so it doesn't break engine lookups
                            self.name = os.path.splitext(filename_base)[0]
                            self.basename = filename_base
                            
                            self.tags = []
                            self.description = "Outfit Studio Managed Asset"
                            
                        def listAllMaterials(self): return []

                    runtime_asset_mock = DynamicStudioAsset(target_full_path)

                    # Normalize target file path lowercased representation for safer checking
                    clean_path_for_matching = target_full_path.lower()
                    
                    # Extract only the asset-specific part to avoid matching text inside user disk folder structures
                    if "/data/" in clean_path_for_matching:
                        searchable_segment = clean_path_for_matching.split("/data/")[-1]
                    else:
                        searchable_segment = os.path.basename(clean_path_for_matching)

                    for node in getattr(self.main_window, 'equipment', []):
                        if not isinstance(node, dict):
                            continue
                        
                        image_selector = node.get('func')
                        if image_selector and hasattr(image_selector, 'callback') and hasattr(image_selector, 'type'):
                            
                            is_target_tab = False
                            slot_name = str(node.get('name', '')).lower()
                            
                            # Safely check matching constraints exclusively within the asset data scope
                            if slot_name in searchable_segment:
                                is_target_tab = True
                            elif "hair" in slot_name and "hair" in searchable_segment:
                                is_target_tab = True
                            elif "clothes" in slot_name and ("clothes" in searchable_segment or "apparel" in searchable_segment):
                                is_target_tab = True

                            if is_target_tab:
                                # Crash shields for background initialization
                                if not getattr(image_selector, 'parent', None):
                                    image_selector.parent = SafeMockUIElement()
                                if not getattr(image_selector, 'picwidget', None):
                                    image_selector.picwidget = SafeMockUIElement()

                                if not getattr(image_selector, 'asset_category', None):
                                    image_selector.asset_category = []
                                
                                # Protect the existing clothes panel assets array 
                                has_duplicate = False
                                for asset in image_selector.asset_category:
                                    if hasattr(asset, 'filename') and asset.filename == target_full_path:
                                        has_duplicate = True
                                        asset.status = 1
                                        if hasattr(image_selector, 'selected_asset'): 
                                            image_selector.selected_asset = asset
                                        if hasattr(image_selector, 'current_asset'): 
                                            image_selector.current_asset = asset
                                        break
                                
                                if not has_duplicate:
                                    image_selector.asset_category.append(runtime_asset_mock)
                                    if hasattr(image_selector, 'selected_asset'): 
                                        image_selector.selected_asset = runtime_asset_mock
                                    if hasattr(image_selector, 'current_asset'): 
                                        image_selector.current_asset = runtime_asset_mock

                                # Execute the native asset loading mount callback routine
                                multi_mode = getattr(image_selector, 'selmode', 0) == 1
                                try:
                                    image_selector.callback(runtime_asset_mock, image_selector.type, multi_mode)
                                    if hasattr(image_selector, 'changeStatus'): 
                                        image_selector.changeStatus()
                                    if hasattr(image_selector, 'refreshButtons'): 
                                        image_selector.refreshButtons()
                                except Exception:
                                    try: 
                                        image_selector.callback(target_full_path, image_selector.type, multi_mode)
                                    except Exception: 
                                        pass
                                
                                break # Match complete, exit to next file path

            if hasattr(self.main_window, 'glob') and hasattr(self.main_window.glob, 'openGLWindow'):
                self.main_window.glob.openGLWindow.Tweak()
                
            print(f"[Outfit Studio] Successfully loaded and synchronized all target ensemble assets.")
        except Exception as load_fault:
            print(f"[Outfit Studio Error] Character wardrobe initialization crashed: {load_fault}")

    def capture_current_outfit(self):
        """
        PERMANENT EXTRACTION RESOLUTION: Deep harvests active file paths
        """
        import getpass  # Dynamic system username resolver
        
        if not hasattr(self.main_window, 'equipment') or not self.main_window.equipment:
            QMessageBox.warning(self, "No Items Equipped", "The character currently has no equipment structure initialized.")
            return

        # Access the true master tracking database
        attached_assets_list = []
        try:
            # Gather references from the active layout engine namespaces
            if hasattr(self.main_window, 'glob') and hasattr(self.main_window.glob, 'baseClass'):
                attached_assets_list = getattr(self.main_window.glob.baseClass, 'attachedAssets', [])
            elif hasattr(self.glob, 'baseClass'):
                attached_assets_list = getattr(self.glob.baseClass, 'attachedAssets', [])
        except Exception:
            pass

        outfit_name, confirmed = QInputDialog.getText(
            self, "Save Character Outfit Set", "Enter a unique configuration profile name for this outfit set:"
        )
        if not confirmed or not outfit_name.strip():
            return

        # Allow underscores safely
        clean_filename = "".join([c for c in outfit_name.strip().lower() if c.isalnum() or c in (" ", "_", "-")]).replace(" ", "")
        target_file_path = os.path.join(self.outfits_dir, f"{clean_filename}.json").replace("\\", "/")

        if os.path.isfile(target_file_path):
            confirm_overwrite = QMessageBox.question(
                self, "Outfit Profile Exists",
                f"An outfit set named '{outfit_name.strip()}' already exists.\n\nDo you want to overwrite it?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm_overwrite == QMessageBox.No:
                return

        unique_file_pool = set()
        captured_assets_dictionary = {}
        
        try:
            # STEP 1: Loop through the official memory list
            for elem in attached_assets_list:
                if elem and hasattr(elem, 'filename') and elem.filename:
                    unique_file_pool.add(os.path.normpath(str(elem.filename)).replace("\\", "/"))

            # STEP 2: Safe UI loop harvest fallback if the core master memory reference is locked
            if not unique_file_pool:
                for index, asset_node in enumerate(self.main_window.equipment):
                    if not asset_node or not isinstance(asset_node, dict):
                        continue
                    image_selector = asset_node.get('func')
                    if image_selector and hasattr(image_selector, 'asset_category'):
                        for asset in image_selector.asset_category:
                            if getattr(asset, 'status', 0) == 1 or getattr(asset, 'selected', False):
                                if hasattr(asset, 'filename') and asset.filename:
                                    unique_file_pool.add(os.path.normpath(str(asset.filename)).replace("\\", "/"))

            # STEP 3: Save paths sequentially into independent list keys to prevent file overwrites
            for file_index, full_disk_path in enumerate(sorted(list(unique_file_pool))):
                clean_path = full_disk_path
                
                # Dynamic share portability convert absolute disk mapping to portable paths
                if "data/" in full_disk_path.lower():
                    clean_path = "data/" + full_disk_path.lower().split("data/")[-1]
                elif "makehuman2/" in full_disk_path.lower():
                    clean_path = "data/" + full_disk_path.lower().split("makehuman2/")[-1]

                # Map sequentially by clean indices so duplicate types (dress, boots, beard) NEVER crash!
                flat_key = f"item_{file_index}"
                captured_assets_dictionary[flat_key] = [clean_path]

            if not captured_assets_dictionary:
                QMessageBox.warning(self, "Extraction Error", "Could not locate any active assets inside the master attachedAssets list layer.")
                return

            outfit_profile_payload = {
                "outfit_name": outfit_name.strip(),
                "author": getpass.getuser(),  # Dynamically logs the user's OS name instead of "User"
                "assets": captured_assets_dictionary
            }

            with open(target_file_path, 'w', encoding='utf-8') as json_file:
                json.dump(outfit_profile_payload, json_file, indent=4)

            thumbnail_path = os.path.join(self.outfits_dir, f"{clean_filename}.png").replace("\\", "/")
            self.generate_outfit_thumbnail(thumbnail_path)

            print(f"[Outfit Studio] Successfully serialized wardrobe preset file track to: {target_file_path}")
            self.scan_outfits_folder()
            QMessageBox.information(self, "Outfit Saved!", f"Successfully captured character outfit layout and thumbnail as '{outfit_name}'!")
        except Exception as file_fault:
            print(f"[Outfit Studio Error] Failed to capture live wardrobe matrices: {file_fault}")
            QMessageBox.critical(self, "Error Saving Outfit", f"System serialization file loop crashed: {file_fault}")

    def capture_manual_thumbnail(self):
        selected_items = self.outfit_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Selection Required", "Please click on a saved outfit profile in the list above to assign a new thumbnail to it.")
            return
            
        outfit_name = selected_items[0].data(Qt.UserRole)
        # Include underscores here to match the dynamic save filename structure from above
        clean_filename = "".join([c for c in outfit_name.strip().lower() if c.isalnum() or c in (" ", "_", "-")]).replace(" ", "")
        thumbnail_path = os.path.join(self.outfits_dir, f"{clean_filename}.png").replace("\\", "/")
        
        self.generate_outfit_thumbnail(thumbnail_path)
        QMessageBox.information(self, "Thumbnail Updated", f"Successfully captured fresh engine snapshot for outfit preset '{outfit_name}'!")

    def generate_outfit_thumbnail(self, output_png_path):
        # Import QPixmap early here so data type check does not throw a NameError
        from PySide6.QtGui import QPixmap
        
        try:
            view_handle = None
            if hasattr(self.main_window, 'glob') and hasattr(self.main_window.glob, 'openGLWindow'):
                view_handle = self.main_window.glob.openGLWindow
            elif hasattr(self.glob, 'openGLWindow'):
                view_handle = self.glob.openGLWindow

            if view_handle and hasattr(view_handle, 'createThumbnail'):
                print("[Outfit Studio] Invoking native hardware-accelerated viewport matrix thumbnail rendering channel...")
                native_image = view_handle.createThumbnail()
                if native_image and not native_image.isNull():
                    pixmap = QPixmap.fromImage(native_image) if hasattr(native_image, 'isNull') and not isinstance(native_image, QPixmap) else native_image
                    
                    side_length = min(pixmap.width(), pixmap.height())
                    x_offset = (pixmap.width() - side_length) // 2
                    y_offset = (pixmap.height() - side_length) // 2
                    
                    square_thumbnail = pixmap.copy(x_offset, y_offset, side_length, side_length)
                    final_scaled_thumb = square_thumbnail.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    
                    final_scaled_thumb.save(output_png_path, "PNG")
                    print(f"[Outfit Studio] Native hardware screenshot saved successfully to: {output_png_path}")
                else:
                    print("⚠️ Native Grab Error: Viewport extraction array layer returned invalid or null output pixels.")
            else:
                print("⚠️ Critical Bypassed Channel: 'createThumbnail' engine function was completely unreachable.")
        except Exception as system_rendering_fault:
            print(f"⚠️ Core hardware viewport image acquisition failure loop crashed: {system_rendering_fault}")

    def delete_selected_outfit(self):
        """
        SAFE FILE DELETION: Prompts the user for verification 
        before permanently removing the preset from the hard disk.
        """
        current_item = self.outfit_list.currentItem()
        if not current_item:
            return
            
        outfit_name = current_item.data(Qt.UserRole)
        if not outfit_name:
            return
            
        confirm_delete = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to permanently delete the outfit preset '{outfit_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm_delete == QMessageBox.No:
            return
            
        # Include underscores so file deletion operations match the actual file tracks saved on disk
        clean_filename = "".join([c for c in outfit_name.strip().lower() if c.isalnum() or c in (" ", "_", "-")]).replace(" ", "")
        target_file_path = os.path.join(self.outfits_dir, f"{clean_filename}.json").replace("\\", "/")
        
        try:
            if os.path.isfile(target_file_path):
                os.remove(target_file_path)
                
                thumb_file_path = os.path.join(self.outfits_dir, f"{clean_filename}.png").replace("\\", "/")
                if os.path.isfile(thumb_file_path):
                    os.remove(thumb_file_path)
                    
                self.scan_outfits_folder()
                QMessageBox.information(self, "Deleted", f"Successfully removed outfit '{outfit_name}'.")
        except Exception as delete_fault:
            print(f"[Outfit Studio Error] System file removal failed: {delete_fault}")
