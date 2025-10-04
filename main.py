import sys
import json
import os
import warnings
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QSplitter,
    QTreeWidget, QTreeWidgetItem, QTextEdit, QFileIconProvider
)
from PyQt6.QtCore import Qt, QTimer, qInstallMessageHandler
from PyQt6.QtGui import QBrush, QColor, QKeySequence, QShortcut
from menu import create_menu
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from window import RepoWindow, load_repos
from repo_manager import AddRepoPanel
from theme_manager import ThemeManager

# Paths for repos
BASE_DIR = Path.home() / "Gitea Repos"
GITEA_GREEN = QColor("#2ea44f")
GITEA_HIGHLIGHT = QColor("#28a745")

def qt_message_handler(msg_type, context, message):
    """Filter out Qt font warnings while keeping other important messages"""
    # Suppress font-related warnings
    if "OpenType support missing" in message or "font.db" in message:
        return
    
    # Print other messages normally
    print(f"Qt {msg_type.name}: {message}")

# Install the message handler
qInstallMessageHandler(qt_message_handler)

# -------------------------------
# Watchdog Handler
# -------------------------------
class RepoChangeHandler(FileSystemEventHandler):
    def __init__(self, browser):
        self.browser = browser

    def on_any_event(self, event):
        if event.is_directory:
            return
        self.browser.mark_modified(event.src_path)

# -------------------------------
# Main Window
# -------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gitea Interact")
        self.resize(1100, 700)  # Set default windowed size
        
        # Load settings and apply fullscreen if needed
        self.load_settings()
        
        create_menu(self)
        self.browser = RepoWindow(self)
        self.setCentralWidget(self.browser)
        
        # Setup keyboard shortcuts
        self.setup_shortcuts()
        
        # Apply theme after everything is initialized
        self.apply_theme(self.settings.get('theme', 'light'))

    def load_settings(self):
        """Load settings from file and apply them"""
        self.settings_file = os.path.expanduser("~/.gitea_interact_settings.json")
        self.settings = self.load_settings_from_file()
        
        # Apply theme
        self.apply_theme(self.settings.get('theme', 'light'))
        
        # Apply fullscreen setting
        if self.settings.get('start_fullscreen', False):
            # Use a timer to ensure the window is fully initialized before going fullscreen
            QTimer.singleShot(100, self.showFullScreen)
    
    def load_settings_from_file(self):
        """Load settings from JSON file"""
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
    
    def apply_theme(self, theme_name):
        """Apply theme to the application"""
        # Apply main window theme
        self.setStyleSheet(ThemeManager.get_main_window_style(theme_name))
        
        # Apply menu bar theme
        self.menuBar().setStyleSheet(ThemeManager.get_menu_bar_style(theme_name))
        
        # Apply theme to browser (RepoWindow)
        if hasattr(self, 'browser'):
            self.browser.apply_theme(theme_name)
    
    def on_settings_changed(self):
        """Handle settings changes"""
        # Reload settings and apply them
        self.settings = self.load_settings_from_file()
        
        # Apply theme
        self.apply_theme(self.settings.get('theme', 'light'))
        
        # Apply fullscreen setting
        if self.settings.get('start_fullscreen', False):
            if not self.isFullScreen():
                self.showFullScreen()
        else:
            if self.isFullScreen():
                self.showNormal()
                # Set specific window size when switching to windowed mode
                # Use a small delay to ensure showNormal() is complete
                QTimer.singleShot(50, lambda: self.resize(1100, 700))
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # F11 to toggle fullscreen
        self.fullscreen_shortcut = QShortcut(QKeySequence("F11"), self)
        self.fullscreen_shortcut.activated.connect(self.toggle_fullscreen)
    
    def toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        if self.isFullScreen():
            self.showNormal()
            # Set specific window size when switching to windowed mode
            # Use a small delay to ensure showNormal() is complete
            QTimer.singleShot(50, lambda: self.resize(1100, 700))
        else:
            self.showFullScreen()

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Gitea Interact")
    app.setApplicationVersion("1.0")
    
    # Set application icon if available
    # app.setWindowIcon(QIcon("icon.png"))
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()