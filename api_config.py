from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QMessageBox, QApplication, QListWidget, QListWidgetItem, QFrame,
    QScrollArea, QComboBox, QInputDialog
)
from PyQt6.QtCore import Qt
from pathlib import Path
import json
import requests
from theme_manager import ThemeManager

CONFIG_DIR = Path.home() / ".config" / "gitea-interact"
CONFIG_FILE = CONFIG_DIR / "settings.json"

def load_api_settings():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                # Handle migration from old single API format
                if "server_url" in data and "token" in data and "api_configs" not in data:
                    # Migrate old format to new format
                    old_config = {
                        "name": "Default Server",
                        "server_url": data["server_url"],
                        "token": data["token"]
                    }
                    data["api_configs"] = [old_config]
                    save_api_settings(data)  # Save migrated data
                return data
        except Exception:
            return {}
    return {"api_configs": []}

def save_api_settings(settings: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(settings, f, indent=4)

def get_api_configs():
    """Get list of all API configurations"""
    settings = load_api_settings()
    return settings.get("api_configs", [])

def get_api_config_by_name(name):
    """Get specific API configuration by name"""
    configs = get_api_configs()
    for config in configs:
        if config.get("name") == name:
            return config
    return None

class ApiConfigPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_config = None

        # Main layout with scrollable area
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Create content widget
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Title
        title = QLabel("⚙️ Configure Multiple API Settings")
        # Title styling will be applied by theme
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Main content area with split layout
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        # Left side - Configuration list
        left_frame = QFrame()
        # Left frame styling will be applied by theme
        left_frame.setFixedWidth(300)
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(16, 16, 16, 16)

        # Configuration list title
        list_title = QLabel("📋 Saved Configurations")
        # List title styling will be applied by theme
        left_layout.addWidget(list_title)

        # Configuration list
        self.config_list = QListWidget()
        # Config list styling will be applied by theme
        self.config_list.itemClicked.connect(self.on_config_selected)
        left_layout.addWidget(self.config_list)

        # Configuration management buttons
        config_buttons_layout = QHBoxLayout()
        
        self.add_config_btn = QPushButton("➕ Add New")
        # Add config button styling will be applied by theme
        self.add_config_btn.clicked.connect(self.add_new_config)
        config_buttons_layout.addWidget(self.add_config_btn)

        self.remove_config_btn = QPushButton("🗑️ Remove")
        # Remove config button styling will be applied by theme
        self.remove_config_btn.clicked.connect(self.remove_config)
        config_buttons_layout.addWidget(self.remove_config_btn)

        left_layout.addLayout(config_buttons_layout)
        content_layout.addWidget(left_frame)

        # Right side - Configuration details
        right_frame = QFrame()
        # Right frame styling will be applied by theme
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(16, 16, 16, 16)

        # Configuration details title
        details_title = QLabel("🔧 Configuration Details")
        # Details title styling will be applied by theme
        right_layout.addWidget(details_title)

        # Configuration name
        name_label = QLabel("📝 Configuration Name:")
        # Name label styling will be applied by theme
        right_layout.addWidget(name_label)
        
        self.name_input = QLineEdit()
        # Name input styling will be applied by theme
        self.name_input.setPlaceholderText("e.g., My Gitea Server")
        right_layout.addWidget(self.name_input)

        # Server URL
        server_label = QLabel("🌐 Gitea Server URL:")
        # Server label styling will be applied by theme
        right_layout.addWidget(server_label)
        
        self.server_input = QLineEdit()
        # Server input styling will be applied by theme
        self.server_input.setPlaceholderText("https://your-gitea-server.com")
        right_layout.addWidget(self.server_input)

        # API Token
        token_label = QLabel("🔑 API Token:")
        # Token label styling will be applied by theme
        right_layout.addWidget(token_label)
        
        self.token_input = QLineEdit()
        # Token input styling will be applied by theme
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setPlaceholderText("Enter your Gitea API token")
        right_layout.addWidget(self.token_input)

        # Action buttons
        action_buttons_layout = QHBoxLayout()
        
        self.test_button = QPushButton("🔍 Test Connection")
        # Test button styling will be applied by theme
        self.test_button.clicked.connect(self.test_connection)
        action_buttons_layout.addWidget(self.test_button)

        self.save_button = QPushButton("💾 Save Configuration")
        # Save button styling will be applied by theme
        self.save_button.clicked.connect(self.save_configuration)
        action_buttons_layout.addWidget(self.save_button)

        right_layout.addLayout(action_buttons_layout)

        # Status label
        self.status_label = QLabel("")
        # Status label styling will be applied by theme
        self.status_label.setWordWrap(True)
        right_layout.addWidget(self.status_label)

        content_layout.addWidget(right_frame)
        layout.addLayout(content_layout)

        # Set content widget layout
        content_widget.setLayout(layout)
        
        # Set content widget as scroll area widget
        scroll_area.setWidget(content_widget)
        
        # Add scroll area to main layout
        main_layout.addWidget(scroll_area)

        # Load existing configurations
        self.load_configurations()

    def load_configurations(self):
        """Load and display all saved API configurations"""
        self.config_list.clear()
        configs = get_api_configs()
        
        for config in configs:
            item = QListWidgetItem(f"🌐 {config.get('name', 'Unnamed')}")
            item.setData(Qt.ItemDataRole.UserRole, config)
            self.config_list.addItem(item)
    
    def on_config_selected(self, item):
        """Handle configuration selection"""
        config = item.data(Qt.ItemDataRole.UserRole)
        self.current_config = config
        
        # Populate the form fields
        self.name_input.setText(config.get('name', ''))
        self.server_input.setText(config.get('server_url', ''))
        self.token_input.setText(config.get('token', ''))
        
        self.status_label.setText(f"Selected configuration: {config.get('name', 'Unnamed')}")
    
    def add_new_config(self):
        """Add a new API configuration"""
        self.current_config = None
        self.name_input.clear()
        self.server_input.clear()
        self.token_input.clear()
        self.status_label.setText("Creating new configuration...")
    
    def remove_config(self):
        """Remove the selected configuration"""
        if not self.current_config:
            QMessageBox.warning(self, "No Selection", "Please select a configuration to remove.")
            return
        
        reply = QMessageBox.question(
            self, "Confirm Removal",
            f"Are you sure you want to remove the configuration '{self.current_config.get('name', 'Unnamed')}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Remove from settings
            settings = load_api_settings()
            configs = settings.get("api_configs", [])
            configs = [c for c in configs if c.get('name') != self.current_config.get('name')]
            settings["api_configs"] = configs
            save_api_settings(settings)
            
            # Refresh the list
            self.load_configurations()
            self.add_new_config()
            self.status_label.setText("Configuration removed successfully!")

    def test_connection(self):
        """Test the current configuration"""
        server = self.server_input.text().strip()
        token = self.token_input.text().strip()

        if not server or not token:
            self.status_label.setText("Please enter both server URL and API token.")
            return

        # Validate server URL format
        if not server.startswith(('http://', 'https://')):
            server = f"https://{server}"

        # Clean up server URL (remove trailing slash)
        server = server.rstrip('/')

        # Test API connection
        self.status_label.setText("Testing connection...")
        self.test_button.setEnabled(False)
        QApplication.processEvents()

        try:
            # Try to access the user info endpoint
            url = f"{server}/api/v1/user"
            headers = {"Authorization": f"token {token}"}
            
            # Try with SSL verification first
            resp = requests.get(url, headers=headers, timeout=10)
            
            # Check response status and provide detailed error info
            if resp.status_code == 403:
                # Try alternative endpoints that might work
                alt_urls = [
                    f"{server}/api/v1/user",
                    f"{server}/api/v1/user/current", 
                    f"{server}/api/v1/version"
                ]
                
                for alt_url in alt_urls:
                    try:
                        alt_resp = requests.get(alt_url, headers=headers, verify=False, timeout=10)
                        if alt_resp.status_code == 200:
                            if "version" in alt_url:
                                self.status_label.setText(f"✅ Server connection successful! Gitea version: {alt_resp.json().get('version', 'Unknown')}")
                            else:
                                user_data = alt_resp.json()
                                self.status_label.setText(f"✅ Connection successful! Logged in as: {user_data.get('login', 'Unknown user')}")
                            return
                    except:
                        continue
                
                # If all endpoints fail with 403, then provide detailed error info
                self.status_label.setText(f"❌ 403 Forbidden - Check:\n• API token is correct\n• Token has 'read:user' permission\n• Gitea server allows API access")
                return
            
            resp.raise_for_status()
            user_data = resp.json()
            self.status_label.setText(f"✅ Connection successful! Logged in as: {user_data.get('login', 'Unknown user')}")
            
        except requests.exceptions.SSLError:
            # If SSL fails, try without verification (for self-signed certs)
            try:
                resp = requests.get(url, headers=headers, verify=False, timeout=10)
                if resp.status_code == 403:
                    self.status_label.setText(f"❌ 403 Forbidden - Check:\n• API token is correct\n• Token has 'read:user' permission\n• Gitea server allows API access")
                    return
                resp.raise_for_status()
                user_data = resp.json()
                self.status_label.setText(f"✅ Connection successful (SSL bypassed)! Logged in as: {user_data.get('login', 'Unknown user')}")
            except Exception as e:
                self.status_label.setText(f"❌ Connection failed: {str(e)}")
        except requests.exceptions.RequestException as e:
            if "403" in str(e):
                self.status_label.setText(f"❌ 403 Forbidden - Check:\n• API token is correct\n• Token has 'read:user' permission\n• Gitea server allows API access")
            else:
                self.status_label.setText(f"❌ Connection failed: {str(e)}")
        except Exception as e:
            self.status_label.setText(f"❌ Unexpected error: {str(e)}")
        finally:
            self.test_button.setEnabled(True)

    def save_configuration(self):
        """Save the current configuration"""
        name = self.name_input.text().strip()
        server = self.server_input.text().strip()
        token = self.token_input.text().strip()

        if not name or not server or not token:
            QMessageBox.warning(self, "Error", "Please enter configuration name, server URL, and API token.")
            return

        # Validate server URL format
        if not server.startswith(('http://', 'https://')):
            server = f"https://{server}"

        # Clean up server URL (remove trailing slash)
        server = server.rstrip('/')

        # Load existing settings
        settings = load_api_settings()
        configs = settings.get("api_configs", [])
        
        # Check if we're updating an existing config or creating a new one
        if self.current_config:
            # Update existing configuration
            for i, config in enumerate(configs):
                if config.get('name') == self.current_config.get('name'):
                    configs[i] = {
                        "name": name,
                        "server_url": server,
                        "token": token
                    }
                    break
        else:
            # Check if name already exists
            for config in configs:
                if config.get('name') == name:
                    QMessageBox.warning(self, "Error", f"A configuration with the name '{name}' already exists.")
                    return
            
            # Add new configuration
            configs.append({
                "name": name,
                "server_url": server,
                "token": token
            })
        
        # Save settings
        settings["api_configs"] = configs
        save_api_settings(settings)
        
        # Refresh the list
        self.load_configurations()
        
        # Select the saved configuration
        for i in range(self.config_list.count()):
            item = self.config_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole).get('name') == name:
                self.config_list.setCurrentItem(item)
                self.on_config_selected(item)
                break
        
        self.status_label.setText("✅ Configuration saved successfully!")
        QMessageBox.information(self, "Saved", "API configuration saved successfully.")
    
    def apply_theme(self, theme_name):
        """Apply theme to the API config panel"""
        colors = ThemeManager.get_theme_colors(theme_name)
        
        # Apply comprehensive panel theme
        self.setStyleSheet(ThemeManager.get_panel_style(theme_name) + f"""
            QListWidget {{
                background-color: {colors['input_bg']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border_color']};
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
                selection-background-color: {colors['accent_color']};
                alternate-background-color: {colors['main_bg']};
            }}
            QListWidget::item {{
                padding: 8px;
                border-radius: 4px;
                margin: 2px;
            }}
            QListWidget::item:selected {{
                background-color: {colors['accent_color']};
                color: {colors['menu_text']};
            }}
            QListWidget::item:hover {{
                background-color: {colors['accent_hover']};
            }}
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 {colors['button_bg']}, stop:1 {colors['button_hover']});
                color: {colors['menu_text']};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 {colors['button_hover']}, stop:1 {colors['button_bg']});
            }}
            QLabel {{
                padding: 12px;
                border-radius: 8px;
                font-size: 13px;
                background-color: {colors['input_bg']};
                border: 1px solid {colors['border_color']};
                margin-top: 16px;
                color: {colors['text_primary']};
            }}
        """)

