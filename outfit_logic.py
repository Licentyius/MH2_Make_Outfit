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

from gui.common import IconButton, ErrorBox

class OutfitPlugin(QWidget):
    def __init__(self, app_reference, glob_reference, pluginname):
        super().__init__()
        self.glob = glob_reference
        self.mh_app = app_reference
        self.pluginname = pluginname
        self.mainwindow = self.glob.MainWindow
        self.repo = self.glob.pluginRepo
        self.env = self.glob.env
        self.baseclass = self.glob.baseClass

        # TODO checked when base is changed
        self.outfits_dir = os.path.normpath(os.path.join(self.env.stdUserPath(), "outfit_presets", self.env.basename)).replace("\\", "/")
        self.scanned_outfits = {}
        self.dock = None
        self.panel = None

    class Panel(QWidget):
        def __init__(self, parent, glob):
            super().__init__()

            self.glob = glob
            self.env = glob.env
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

            camera_icon_path = os.path.join(self.env.path_sysicon, "camera.png")
            self.camera_btn = IconButton(1, camera_icon_path, "Take Preset Thumbnail", parent.capture_manual_thumbnail)
            
            meta_group.addWidget(self.camera_btn)
            layout.addLayout(meta_group)

            # --- VISUAL METADATA PARSE TICKER ---
            layout.addWidget(QLabel("<b>Selected Preset Properties:</b>"))
            parent.metadata_display = QTextBrowser()
            parent.metadata_display.setMaximumHeight(90)
            parent.metadata_display.setHtml("<i style='color:#888888;'>Click a saved outfit preset below to review details...</i>")
            layout.addWidget(parent.metadata_display)

            # --- PRESETS LIST ---
            layout.addWidget(QLabel("<b>Saved Outfit Sets:</b>"))
            parent.outfit_list = QListWidget()
            parent.outfit_list.setViewMode(QListWidget.IconMode)
            parent.outfit_list.setResizeMode(QListWidget.Adjust)
            parent.outfit_list.setMovement(QListWidget.Static)
        
            parent.outfit_list.itemClicked.connect(parent.display_selected_metadata)
            parent.outfit_list.itemDoubleClicked.connect(parent.load_selected_outfit)
            layout.addWidget(parent.outfit_list)
        
            # --- EQUIP PRESSED SELECTION BUTTON ---
            self.equip_btn = QPushButton("👗 Equip Selected Outfit Set")
            self.equip_btn.clicked.connect(lambda: parent.load_selected_outfit(parent.outfit_list.currentItem()))
            layout.addWidget(self.equip_btn)

            # --- REMOVE OUTFIT BUTTON ACTION ROW ---
            action_layout = QHBoxLayout()
            clear_btn = QPushButton("👕 Take Off Whole Outfit")
            clear_btn.clicked.connect(lambda: parent.clear_entire_wardrobe())
            action_layout.addWidget(clear_btn)
            layout.addLayout(action_layout)
        
            # --- CONTROL BUTTONS ---
            btn_layout = QVBoxLayout()
            row1 = QHBoxLayout()
            row2 = QHBoxLayout()
        
            refresh_btn = QPushButton("🔄 Refresh List")
            refresh_btn.clicked.connect(parent.scan_outfits_folder)
            row1.addWidget(refresh_btn)

            save_btn = QPushButton("💾 Save Current Outfit")
            save_btn.clicked.connect(parent.capture_current_outfit)
            row1.addWidget(save_btn)

            rename_btn = QPushButton("✏️ Rename Outfit")
            rename_btn.clicked.connect(parent.rename_selected_outfit)
            row2.addWidget(rename_btn)

            self.delete_btn = QPushButton("❌ Delete Outfit")
            self.delete_btn.clicked.connect(parent.delete_selected_outfit)
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

                    # continue when JSON file contains errors 
                    # important: also shows name which one is corrupt

                    data = self.env.readJSON(full_path)
                    if data is None:
                        ErrorBox(self.glob.centralWidget, self.env.last_error)
                        continue

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

    def clear_entire_wardrobe(self):
        """
        collect assets to delete, a copy is needed, since attachedAssets changes
        when detachAssetByName is called. The delete them in a loop
        """
        filenames = []
        for elem in self.baseclass.attachedAssets:
            if elem.type != "eyes":
                filenames.append(elem.filename)

        for filename in filenames:
            self.baseclass.detachAssetByName(filename)
                

    def load_selected_outfit(self, item):
        """
        loads assets from a json list
        """
        if not item: 
            QMessageBox.warning(self, "Selection Required", "Please click on a saved outfit set from the menu first.")
            return
        outfit_name = item.data(Qt.UserRole)
        config = self.scanned_outfits.get(outfit_name)
        if not config or "assets" not in config: return

        self.clear_entire_wardrobe()

        # now all assets except eyes are gone attach new assets
        #
        saved_wardrobe_slots = config["assets"]

        # all assets are in glob.cachedInfo as a class loadEquipment
        # the asset can be determined by getAssetByFilename
        #
        for slot in saved_wardrobe_slots.values():
            if "filename" not in slot:
                continue
            path = slot["filename"]
            material = slot["material"] if "material" in slot else None

            # prepend user and system datapath and check if the asset is known
            #
            sysasset = os.path.join(self.env.path_sysdata, path)
            userasset = os.path.join(self.env.path_userdata, path)
            elem = self.glob.getAssetByFilename(sysasset)
            if elem is None:
                elem = self.glob.getAssetByFilename(userasset)

            if elem is not None:
                if elem.folder != "eyes":
                    # materialpath is the asset path + materialname if given
                    #
                    if material is not None:
                        matpath = os.path.join(os.path.dirname(elem.path), material)
                    else:
                        matpath = None
                    multi = (elem.folder == "clothes")
                    self.baseclass.addAndDisplayAsset(elem.path, elem.folder, multi, materialpath=matpath, materialsource=material)


    def capture_current_outfit(self):
        attached_assets_list = self.baseclass.attachedAssets

        if not hasattr(self.mainwindow, 'equipment') or not self.mainwindow.equipment:
            QMessageBox.warning(self, "No Items Equipped", "The character currently has no equipment structure initialized.")
            return

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
        clean_filename = self.env.normalizeName(outfit_name)

        target_file_path = os.path.join(self.outfits_dir, f"{clean_filename}.json").replace("\\", "/")

        if os.path.isfile(target_file_path):
            confirm_overwrite = QMessageBox.question(
                self, "Outfit Profile Exists", f"An outfit set named '{outfit_name}' already exists.\n\nOverwrite it?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm_overwrite == QMessageBox.No: 
                return

        captured_assets_dictionary = {}
        
        lensys = len(self.env.path_sysdata) + 1 # delete trailing "/"
        lenuser = len(self.env.path_userdata) + 1

        for slotindex, elem in enumerate(attached_assets_list):

            # different way then in MHM file, save relative path
            # absolute file name is given in elem.filename
            # try so subtract either system or user path if the file starts with that path
            #
            if elem.filename.startswith(self.env.path_sysdata):
                fname = elem.filename[lensys:]
            elif elem.filename.startswith(self.env.path_userdata):
                fname = elem.filename[lenuser:]
            else:
                fname = elem.filename # this should not happen

            fname = os.path.normpath(fname).replace("\\", "/")

            # save material if material is not None
            # 
            entry = {"filename": fname}
            if  elem.materialsource is not None:
                entry["material"] = self.env.formatPath(elem.materialsource)
            captured_assets_dictionary[f"item_{slotindex}"] = entry

        if len(captured_assets_dictionary) < 1:
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

        if self.env.writeJSON(target_file_path, outfit_profile_payload) is False:
            ErrorBox(self.glob.centralWidget, self.env.last_error)
            return

        thumbnail_path = os.path.join(self.outfits_dir, f"{clean_filename}.png").replace("\\", "/")
        self.generate_outfit_thumbnail(thumbnail_path)
        self.scan_outfits_folder()
        QMessageBox.information(self, "Outfit Saved!", f"Successfully captured outfit '{outfit_name}'!")

    def rename_selected_outfit(self):
        current_item = self.outfit_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Selection Required", "Please choose an outfit template from the array list view above to rename.")
            return
            
        old_outfit_name = current_item.data(Qt.UserRole)
        old_clean_filename = self.env.normalizeName(old_outfit_name)
        
        new_outfit_name, confirmed = QInputDialog.getText(
            self, "Rename Outfit Profile", f"Provide a replacement title label for '{old_outfit_name}':", text=old_outfit_name
        )
        if not confirmed or not new_outfit_name.strip() or new_outfit_name.strip() == old_outfit_name:
            return
            
        new_clean_filename = self.env.normalizeName(new_outfit_name)

        old_json_path = os.path.join(self.outfits_dir, f"{old_clean_filename}.json").replace("\\", "/")
        new_json_path = os.path.join(self.outfits_dir, f"{new_clean_filename}.json").replace("\\", "/")
        old_png_path = os.path.join(self.outfits_dir, f"{old_clean_filename}.png").replace("\\", "/")
        new_png_path = os.path.join(self.outfits_dir, f"{new_clean_filename}.png").replace("\\", "/")

        if os.path.exists(new_json_path):
            QMessageBox.critical(self, "Naming Conflict", "An outfit profile with that computed target file path already exists.")
            return

        # no file return
        if not os.path.isfile(old_json_path):
            return

        # read json, read error or bad syntax return
        data = self.env.readJSON(old_json_path)
        if data is None:
            ErrorBox(self.glob.centralWidget, self.env.last_error)
            return

        data["outfit_name"] = new_outfit_name.strip()

        # write error for new JSON, return
        if self.env.writeJSON(old_json_path, data) is False:
            ErrorBox(self.glob.centralWidget, self.env.last_error)
            return

        # rename files
        try:
            os.rename(old_json_path, new_json_path)
            if os.path.isfile(old_png_path):
                os.rename(old_png_path, new_png_path)
            self.scan_outfits_folder()
        except Exception as rename_error:
            ErrorBox(self.glob.centralWidget, f"⚠️ Error executing rename operation: {rename_error}")

    def capture_manual_thumbnail(self):
        """ Captures a viewport screenshot and instantly refreshes the preset grid display icons """
        selected_items = self.outfit_list.selectedItems()
        if not selected_items: 
            QMessageBox.warning(self, "Selection Required", "Please click on a saved outfit set from the grid menu first to apply the snapshot thumbnail.")
            return
            
        outfit_name = selected_items[0].data(Qt.UserRole)
        clean_filename = self.env.normalizeName(outfit_name)
        thumbnail_path = os.path.join(self.outfits_dir, f"{clean_filename}.png").replace("\\", "/")
        
        # Execute viewport image rendering pass
        self.generate_outfit_thumbnail(thumbnail_path)
        
        # AUTO-REFRESH
        self.scan_outfits_folder()

    def generate_outfit_thumbnail(self, output_png_path):
        view_handle = self.glob.openGLWindow

        try:
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
            ErrorBox(self.glob.centralWidget, f"⚠️ Viewport screenshot failed: {system_rendering_fault}")

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
            
        clean_filename = self.env.normalizeName(outfit_name)
        
        target_file_path = os.path.join(self.outfits_dir, f"{clean_filename}.json").replace("\\", "/")

        try:
            if os.path.isfile(target_file_path): 
                os.remove(target_file_path)
 
            thumb_file_path = os.path.join(self.outfits_dir, f"{clean_filename}.png").replace("\\", "/")
            if os.path.isfile(thumb_file_path): 
                os.remove(thumb_file_path)

            self.scan_outfits_folder()
        except Exception as delete_fault:
            ErrorBox(self.glob.centralWidget, f"[Outfit Studio Error] File removal failed: {delete_fault}")


    def shutdown(self):
        self.panel.close()
        self.panel.deleteLater()
        self.mainwindow.removeDockWidget(self.dock)
        self.dock.close()
        self.dock.deleteLater()
        self.dock = None

    def initialize(self):
        """
        the initialize function for this dock panel
        """
        if self.pluginname in self.repo:
            # if loaded second time
            # Clean up old references just in case
            self.shutdown()

        self.dock = QDockWidget("Studio Outfit Sets Manage", self.mainwindow)
        self.dock.setObjectName("mh2_outfit_presets_dock_frame")
        self.dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        # create UI
        self.panel = self.Panel(self, self.glob)
        self.dock.setWidget(self.panel)
        self.scan_outfits_folder()

        if hasattr(self.mainwindow, "addDockWidget"):
            self.mainwindow.addDockWidget(Qt.RightDockWidgetArea, self.dock)
        else:
            self.dock.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)

        self.dock.show()

        # now add plugin to repository
        #
        self.repo[self.pluginname] = self
        return True

def load_extension(app_reference, glob_reference):
    glob_reference.env.logLine(1, "[Outfit Studio Core] Executing native decoupled official tool initialization sequence...")

    pluginname = os.path.abspath(__file__)
    plugin = OutfitPlugin(app_reference, glob_reference, pluginname)
    return plugin.initialize()


def unload_extension(glob):
    pluginname = os.path.abspath(__file__)
    if pluginname in glob.pluginRepo:
        glob.pluginRepo[pluginname].shutdown()
        glob.pluginRepo.pop(pluginname)     # and delete from repo

