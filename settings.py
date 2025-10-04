import json
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QCheckBox, QFrame, QMessageBox, QApplication, QComboBox, QSizePolicy, QScrollArea
)
from theme_manager import ThemeManager
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont

class SettingsPanel(QWidget):
    settings_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings_file = os.path.expanduser("~/.gitea_interact_settings.json")
        self.settings = self.load_settings()
        
        # Setup UI with scrollable area
        self.setup_ui()
        
        # Apply theme after UI is set up
        self.apply_theme(self.settings.get('theme', 'light'))
    
    def setup_ui(self):
        """Setup the settings UI with scrollable area"""
        # Main layout for the widget
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
        
        # Header section
        header_frame = QFrame()
        # Header frame styling will be applied by theme
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(16, 16, 16, 16)
        header_layout.setSpacing(8)
        
        # Title
        title_label = QLabel("⚙️ Application Settings")
        # Title label styling will be applied by theme
        title_label.setProperty("title", "true")  # For special title styling
        header_layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel("Configure your application preferences. Changes are saved automatically.")
        # Description label styling will be applied by theme
        desc_label.setProperty("info", "true")  # For special info styling
        desc_label.setWordWrap(True)
        header_layout.addWidget(desc_label)
        
        content_layout.addWidget(header_frame)
        
        # Display settings section
        display_frame = QFrame()
        # Display frame styling will be applied by theme
        display_layout = QVBoxLayout(display_frame)
        display_layout.setContentsMargins(16, 16, 16, 16)
        display_layout.setSpacing(12)
        
        # Display title
        display_title = QLabel("🖥️ Display Settings")
        # Display title styling will be applied by theme
        display_title.setProperty("subtitle", "true")  # For special subtitle styling
        display_layout.addWidget(display_title)
        
        # Theme selection
        theme_label = QLabel("🎨 Theme:")
        # Theme label styling will be applied by theme
        display_layout.addWidget(theme_label)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light (Default)", "Dark Mode"])
        # Theme combo styling will be applied by theme
        
        # Set current theme
        current_theme = self.settings.get('theme', 'light')
        if current_theme == 'dark':
            self.theme_combo.setCurrentIndex(1)
        else:
            self.theme_combo.setCurrentIndex(0)
        
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        display_layout.addWidget(self.theme_combo)
        
        # Theme description
        theme_desc = QLabel("Choose between the light green theme (default) or dark mode for a different visual experience.")
        # Theme description styling will be applied by theme
        theme_desc.setProperty("info", "true")  # For special info styling
        theme_desc.setWordWrap(True)
        display_layout.addWidget(theme_desc)
        
        # Fullscreen checkbox
        self.fullscreen_checkbox = QCheckBox("Start in Fullscreen Mode")
        # Fullscreen checkbox styling will be applied by theme
        self.fullscreen_checkbox.setChecked(self.settings.get('start_fullscreen', False))
        self.fullscreen_checkbox.toggled.connect(self.on_fullscreen_toggled)
        display_layout.addWidget(self.fullscreen_checkbox)
        
        # Fullscreen description
        fullscreen_desc = QLabel("When enabled, the application will start in fullscreen mode. You can still toggle fullscreen using F11 or the window controls.")
        # Fullscreen description styling will be applied by theme
        fullscreen_desc.setProperty("info", "true")  # For special info styling
        fullscreen_desc.setWordWrap(True)
        display_layout.addWidget(fullscreen_desc)
        
        content_layout.addWidget(display_frame)
        
        # Action buttons section
        buttons_frame = QFrame()
        # Buttons frame styling will be applied by theme
        buttons_layout = QHBoxLayout(buttons_frame)
        buttons_layout.setContentsMargins(16, 16, 16, 16)
        buttons_layout.setSpacing(12)
        
        # Apply button
        self.apply_btn = QPushButton("💾 Apply Settings")
        # Apply button styling will be applied by theme
        self.apply_btn.clicked.connect(self.apply_settings)
        buttons_layout.addWidget(self.apply_btn)
        
        # Reset button
        self.reset_btn = QPushButton("🔄 Reset to Defaults")
        # Reset button styling will be applied by theme
        self.reset_btn.clicked.connect(self.reset_settings)
        buttons_layout.addWidget(self.reset_btn)
        
        # Add stretch to push buttons to the right
        buttons_layout.addStretch()
        
        content_layout.addWidget(buttons_frame)
        
        # Add stretch to push everything to the top
        content_layout.addStretch()
        
        # Set content widget layout
        content_widget.setLayout(content_layout)
        
        # Set content widget as scroll area widget
        scroll_area.setWidget(content_widget)
        
        # Add scroll area to main layout
        main_layout.addWidget(scroll_area)
        
        self.setLayout(main_layout)
        
        # Apply initial theme
        self.apply_theme(self.settings.get('theme', 'light'))
    
    def load_settings(self):
        """Load settings from file"""
        default_settings = {
            'start_fullscreen': False,
            'theme': 'light'
        }
        
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    for key, value in default_settings.items():
                        if key not in settings:
                            settings[key] = value
                    return settings
            except (json.JSONDecodeError, IOError):
                pass
        
        return default_settings
    
    def save_settings(self):
        """Save settings to file"""
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            return True
        except IOError:
            return False
    
    def on_theme_changed(self, theme_text):
        """Handle theme selection change"""
        if "Dark Mode" in theme_text:
            self.settings['theme'] = 'dark'
        else:
            self.settings['theme'] = 'light'
        self.save_settings()
        self.apply_theme(self.settings['theme'])
        self.settings_changed.emit()
    
    def on_fullscreen_toggled(self, checked):
        """Handle fullscreen checkbox toggle"""
        self.settings['start_fullscreen'] = checked
        self.save_settings()
        self.settings_changed.emit()
    
    def apply_settings(self):
        """Apply current settings"""
        self.settings['start_fullscreen'] = self.fullscreen_checkbox.isChecked()
        
        # Update theme setting
        if self.theme_combo.currentText() == "Dark Mode":
            self.settings['theme'] = 'dark'
        else:
            self.settings['theme'] = 'light'
        
        if self.save_settings():
            # Show success message
            msg = QMessageBox(self)
            msg.setWindowTitle("✅ Settings Saved")
            msg.setText("Settings have been saved successfully!")
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
            
            # Emit signal to notify parent
            self.settings_changed.emit()
        else:
            QMessageBox.warning(self, "Error", "Failed to save settings. Please check file permissions.")
    
    def reset_settings(self):
        """Reset settings to defaults"""
        reply = QMessageBox.question(
            self, "Reset Settings",
            "Are you sure you want to reset all settings to their default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.settings = {
                'start_fullscreen': False,
                'theme': 'light'
            }
            self.fullscreen_checkbox.setChecked(False)
            self.theme_combo.setCurrentIndex(0)  # Set to Light (Default)
            self.save_settings()
            self.settings_changed.emit()
            
            QMessageBox.information(self, "Settings Reset", "Settings have been reset to defaults.")
    
    def get_start_fullscreen(self):
        """Get the start fullscreen setting"""
        return self.settings.get('start_fullscreen', False)
    
    def apply_theme(self, theme_name):
        """Apply theme to the settings panel"""
        # Apply settings panel theme from theme manager
        self.setStyleSheet(ThemeManager.get_settings_panel_style(theme_name))
        
        # Update theme combo selection to reflect current theme
        if hasattr(self, 'theme_combo'):
            if theme_name == 'dark':
                self.theme_combo.setCurrentIndex(1)
            else:
                self.theme_combo.setCurrentIndex(0)
    
    def get_theme(self):
        """Get the current theme setting"""
        return self.settings.get('theme', 'light')
    
