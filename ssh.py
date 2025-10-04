import os
import subprocess
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QPushButton, QLabel, QMessageBox,
    QTextEdit, QHBoxLayout, QListWidget, QListWidgetItem, QApplication,
    QWidget, QFrame, QScrollArea
)
from PyQt6.QtGui import QClipboard, QFont, QPixmap, QIcon
from PyQt6.QtCore import Qt
from theme_manager import ThemeManager

class SSHWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Apply initial theme
        self.apply_theme('light')  # Default theme, will be updated by parent if needed

        # Main layout with scrollable area
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Create content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)

        # Header section - more compact for panel use
        header_frame = QFrame()
        # Header frame styling will be applied by theme
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(16, 16, 16, 16)
        header_layout.setSpacing(8)

        # Title
        title_label = QLabel("🔑 SSH Key Management")
        # Title label styling will be applied by theme
        title_label.setProperty("title", "true")  # For special title styling
        header_layout.addWidget(title_label)

        # Info text
        info_label = QLabel("Manage your SSH keys in ~/.ssh directory. Create new keys or view existing ones for Git authentication.")
        # Info label styling will be applied by theme
        info_label.setProperty("info", "true")  # For special info styling
        info_label.setWordWrap(True)
        header_layout.addWidget(info_label)

        content_layout.addWidget(header_frame)

        # Create key section
        create_frame = QFrame()
        # Create frame styling will be applied by theme
        create_layout = QVBoxLayout(create_frame)
        create_layout.setContentsMargins(16, 16, 16, 16)
        create_layout.setSpacing(8)

        create_title = QLabel("Create New SSH Key")
        # Create title styling will be applied by theme
        create_title.setProperty("subtitle", "true")  # For special subtitle styling
        create_layout.addWidget(create_title)

        create_info = QLabel("Generate a new RSA SSH key pair for secure Git authentication.")
        # Create info styling will be applied by theme
        create_info.setProperty("info", "true")  # For special info styling
        create_layout.addWidget(create_info)

        self.create_btn = QPushButton("🔧 Create New SSH Key")
        # Create button styling will be applied by theme
        self.create_btn.clicked.connect(self.create_new_key)
        create_layout.addWidget(self.create_btn)

        content_layout.addWidget(create_frame)

        # Existing keys section
        keys_frame = QFrame()
        # Keys frame styling will be applied by theme
        keys_layout = QVBoxLayout(keys_frame)
        keys_layout.setContentsMargins(16, 16, 16, 16)
        keys_layout.setSpacing(8)

        keys_title = QLabel("📋 Existing SSH Keys")
        # Keys title styling will be applied by theme
        keys_title.setProperty("subtitle", "true")  # For special subtitle styling
        keys_layout.addWidget(keys_title)

        keys_info = QLabel("Select a key to view its contents or copy to clipboard.")
        # Keys info styling will be applied by theme
        keys_info.setProperty("info", "true")  # For special info styling
        keys_layout.addWidget(keys_info)

        # Key list with custom styling
        self.key_list = QListWidget()
        # Key list styling will be applied by theme
        self.key_list.itemDoubleClicked.connect(self.view_key)
        keys_layout.addWidget(self.key_list)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.view_btn = QPushButton("👁️ View Selected Key")
        # View button styling will be applied by theme
        self.view_btn.clicked.connect(self.view_selected_key)
        self.view_btn.setEnabled(False)
        btn_layout.addWidget(self.view_btn)

        self.refresh_btn = QPushButton("🔄 Refresh")
        # Refresh button styling will be applied by theme
        self.refresh_btn.clicked.connect(self.load_keys)
        btn_layout.addWidget(self.refresh_btn)

        keys_layout.addLayout(btn_layout)
        content_layout.addWidget(keys_frame)

        # Connect selection change to enable/disable view button
        self.key_list.itemSelectionChanged.connect(self.on_selection_changed)

        # Set content widget layout
        content_widget.setLayout(content_layout)
        
        # Set content widget as scroll area widget
        scroll_area.setWidget(content_widget)
        
        # Add scroll area to main layout
        main_layout.addWidget(scroll_area)
        
        self.setLayout(main_layout)

        # Load keys initially
        self.load_keys()

        # --- Prompt to create a key if none exist ---
        if self.key_list.count() == 0:
            reply = QMessageBox.question(
                self, "No SSH Keys Found",
                "No SSH keys found in ~/.ssh. Would you like to create one now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.create_new_key()


    def ssh_dir(self):
        path = os.path.expanduser("~/.ssh")
        os.makedirs(path, exist_ok=True)
        return path

    def on_selection_changed(self):
        """Enable/disable view button based on selection"""
        self.view_btn.setEnabled(self.key_list.currentItem() is not None)

    def load_keys(self):
        """Load all *.pub keys in ~/.ssh"""
        self.key_list.clear()
        ssh_dir = self.ssh_dir()
        if os.path.exists(ssh_dir):
            for fname in sorted(os.listdir(ssh_dir)):
                if fname.endswith(".pub"):
                    item = QListWidgetItem(f"🔑 {fname}")
                    item.setData(Qt.ItemDataRole.UserRole, fname)  # Store original filename
                    self.key_list.addItem(item)
        
        # Update button state
        self.on_selection_changed()

    def create_new_key(self):
        ssh_path = self.ssh_dir()
        # Suggest a unique name
        count = 1
        while True:
            key_name = f"id_rsa_custom_{count}"
            priv_path = os.path.join(ssh_path, key_name)
            pub_path = priv_path + ".pub"
            if not os.path.exists(priv_path) and not os.path.exists(pub_path):
                break
            count += 1

        try:
            subprocess.run(
                ["ssh-keygen", "-t", "rsa", "-b", "4096", "-f", priv_path, "-N", ""],
                check=True
            )
            QMessageBox.information(self, "Success", f"New SSH key created:\n{priv_path}")
            self.load_keys()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create key:\n{e}")

    def view_selected_key(self):
        item = self.key_list.currentItem()
        if not item:
            QMessageBox.warning(self, "No Selection", "Please select a key to view.")
            return
        self.view_key(item)

    def view_key(self, item):
        # Get the original filename from the item data
        filename = item.data(Qt.ItemDataRole.UserRole)
        pub_path = os.path.join(self.ssh_dir(), filename)
        
        if not os.path.exists(pub_path):
            QMessageBox.warning(self, "Not Found", f"Public key not found:\n{pub_path}")
            return

        with open(pub_path, "r") as f:
            key_text = f.read()

        dialog = QDialog(self)
        dialog.setWindowTitle(f"🔑 SSH Key: {filename}")
        dialog.resize(700, 400)
        # Dialog styling will be applied by theme
        # Apply current theme to dialog
        current_theme = getattr(self.parent(), 'settings', {}).get('theme', 'light') if hasattr(self, 'parent') and self.parent() else 'light'
        colors = ThemeManager.get_theme_colors(current_theme)
        dialog.setStyleSheet(ThemeManager.get_panel_style(current_theme) + f"""
            QLabel {{
                color: {colors['text_primary']};
                font-size: 14px;
                padding: 4px 0;
            }}
            QLabel[header="true"] {{
                font-size: 18px;
                font-weight: bold;
                color: {colors['accent_color']};
                padding: 8px 0;
            }}
            QTextEdit {{
                background-color: {colors['input_bg']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border_color']};
                border-radius: 8px;
                padding: 12px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 13px;
                line-height: 1.4;
                selection-background-color: {colors['accent_color']};
            }}
            QTextEdit:focus {{
                border: 2px solid {colors['accent_color']};
            }}
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 {colors['button_bg']}, stop:1 {colors['button_hover']});
                color: {colors['menu_text']};
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
                min-height: 20px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 {colors['button_hover']}, stop:1 {colors['button_bg']});
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header_label = QLabel(f"SSH Public Key: {filename}")
        # Header label styling will be applied by theme
        header_label.setProperty("header", "true")  # For special header styling
        layout.addWidget(header_label)

        # Instructions
        info_label = QLabel("Copy this key to your Git server (GitHub, GitLab, Gitea, etc.) for authentication.")
        # Info label styling will be applied by theme
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Text area with custom styling
        text_box = QTextEdit()
        text_box.setPlainText(key_text)
        text_box.setReadOnly(True)
        # Text box styling will be applied by theme
        layout.addWidget(text_box)

        # Button layout
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        copy_btn = QPushButton("📋 Copy to Clipboard")
        # Copy button styling will be applied by theme
        copy_btn.clicked.connect(lambda: self.copy_to_clipboard(key_text, dialog))
        btn_layout.addWidget(copy_btn)

        close_btn = QPushButton("❌ Close")
        # Close button styling will be applied by theme
        close_btn.clicked.connect(dialog.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)
        dialog.setLayout(layout)
        dialog.exec()

    def copy_to_clipboard(self, text, parent):
        clipboard = QApplication.clipboard()
        clipboard.setText(text, QClipboard.Mode.Clipboard)
        
        # Create a styled message box
        msg = QMessageBox(parent)
        msg.setWindowTitle("✅ Success")
        msg.setText("SSH key copied to clipboard!")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #f8f9fa;
            }
            QMessageBox QLabel {
                color: #2ea44f;
                font-size: 14px;
                font-weight: bold;
            }
            QMessageBox QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #2ea44f, stop:1 #28a745);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #28a745, stop:1 #1e7e34);
            }
        """)
        msg.exec()
    
    def apply_theme(self, theme_name):
        """Apply theme to the SSH panel"""
        colors = ThemeManager.get_theme_colors(theme_name)
        
        # Apply comprehensive panel theme
        self.setStyleSheet(ThemeManager.get_panel_style(theme_name) + f"""
            QFrame {{
                background-color: {colors['panel_bg']};
                border: 1px solid {colors['border_color']};
                border-radius: 12px;
                padding: 16px;
            }}
            QLabel {{
                color: {colors['text_primary']};
                font-size: 14px;
                padding: 4px 0;
            }}
            QLabel[title="true"] {{
                font-size: 20px;
                font-weight: bold;
                color: {colors['accent_color']};
                padding: 4px 0;
            }}
            QLabel[subtitle="true"] {{
                font-size: 18px;
                font-weight: bold;
                color: {colors['accent_color']};
                padding: 4px 0;
            }}
            QLabel[info="true"] {{
                font-size: 14px;
                color: {colors['text_secondary']};
                padding: 4px 0;
                line-height: 1.4;
            }}
            QListWidget {{
                background-color: {colors['input_bg']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border_color']};
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
                selection-background-color: {colors['accent_color']};
                alternate-background-color: {colors['main_bg']};
            }}
            QListWidget::item {{
                padding: 12px;
                border-radius: 6px;
                margin: 2px;
                min-height: 24px;
                color: {colors['text_primary']};
            }}
            QListWidget::item:selected {{
                background-color: {colors['accent_color']};
                color: {colors['menu_text']};
            }}
            QListWidget::item:hover {{
                background-color: {colors['accent_hover']};
                color: {colors['menu_text']};
            }}
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 {colors['button_bg']}, stop:1 {colors['button_hover']});
                color: {colors['menu_text']};
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
                min-height: 20px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 {colors['button_hover']}, stop:1 {colors['button_bg']});
            }}
            QPushButton:disabled {{
                background: {colors['text_secondary']};
                color: {colors['menu_text']};
            }}
        """)

