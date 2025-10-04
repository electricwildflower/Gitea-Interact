from PyQt6.QtWidgets import QMenuBar, QMenu, QMessageBox, QApplication, QDialog
from PyQt6.QtGui import QAction, QKeySequence
import webbrowser
from pathlib import Path
from ssh import SSHWindow
from user_manager import UserManagerDialogue

def create_menu(window):
    """
    Creates a sleek menu bar and attaches it to the given window.
    Assumes window.browser is your RepoWindow instance.
    """
    menu_bar = QMenuBar(window)
    menu_bar.setStyleSheet("""
        QMenuBar {
            background-color: #2ea44f;  /* Gitea green */
            color: white;
            font-size: 14px;
            padding: 4px;
       }
         QMenuBar::item {
            background: transparent;
            padding: 6px 12px;
            color: white;
        }
        QMenuBar::item:selected {
            background: #28a745;
            border-radius: 4px;
        }
        QMenu {
            background-color: #ffffff;
            border: 1px solid #dcdcdc;
        }
        QMenu::item:selected {
            background-color: #28a745;
            color: white;
        }
    """)

    # --- File Menu ---
    file_menu = QMenu("File", window)
    exit_action = QAction("Exit", window)
    exit_action.setShortcut(QKeySequence.StandardKey.Quit)  # Ctrl+Q
    exit_action.triggered.connect(window.close)
    file_menu.addAction(exit_action)
    menu_bar.addMenu(file_menu)

    # --- Home Button ---
    home_action = QAction("🏠 Home", window)
    def go_home():
        if hasattr(window, 'browser') and window.browser:
            window.browser.show_welcome_message()
    home_action.triggered.connect(go_home)
    menu_bar.addAction(home_action)

    # --- Gitea Menu ---
    gitea_menu = QMenu("Gitea", window)
    
    # Single repo manager
    add_repo_action = QAction("Add/Remove Single Repos", window)
    def add_repo():
        from repo_manager import AddRepoPanel
        if hasattr(window, "browser") and window.browser:
            panel = AddRepoPanel(window.browser)   # make a QWidget panel
            # Apply current theme
            panel.apply_theme(window.settings.get('theme', 'light'))
            # Connect the repo_changed signal to the tree refresh mechanism
            panel.repo_changed.connect(window.browser.on_repo_added)
            window.browser.set_right_panel(panel)
    add_repo_action.triggered.connect(add_repo)
    gitea_menu.addAction(add_repo_action)

    # Bulk user repo manager
    bulk_repo_action = QAction("Bulk Download User Repos", window)
    def open_user_manager():
        from user_manager import UserManagerDialogue
        if hasattr(window, "browser") and window.browser:
            panel = UserManagerDialogue(window.browser)
            # Connect the repo_changed signal to the tree refresh mechanism
            panel.repo_changed.connect(window.browser.on_repo_added)
            # Apply current theme
            panel.apply_theme(window.settings.get('theme', 'light'))
            window.browser.set_right_panel(panel)
    bulk_repo_action.triggered.connect(open_user_manager)
    gitea_menu.addAction(bulk_repo_action)

    menu_bar.addMenu(gitea_menu)

        # --- SSH/API Menu ---
    ssh_menu = QMenu("SSH/API", window)

    # Configure SSH Keys
    configure_ssh_action = QAction("Configure SSH Keys", window)
    def open_ssh():
        from ssh import SSHWindow
        if hasattr(window, "browser") and window.browser:
            panel = SSHWindow()  # Remove parent parameter for panel integration
            # Apply current theme
            panel.apply_theme(window.settings.get('theme', 'light'))
            window.browser.set_right_panel(panel)
    configure_ssh_action.triggered.connect(open_ssh)
    ssh_menu.addAction(configure_ssh_action)

    # Configure API
    configure_api_action = QAction("Configure API", window)
    def open_api_config():
        from api_config import ApiConfigPanel
        if hasattr(window, "browser") and window.browser:
            panel = ApiConfigPanel(window.browser)
            # Apply current theme
            panel.apply_theme(window.settings.get('theme', 'light'))
            window.browser.set_right_panel(panel)
    configure_api_action.triggered.connect(open_api_config)
    ssh_menu.addAction(configure_api_action)

    menu_bar.addMenu(ssh_menu)

    # --- Settings Menu ---
    settings_menu = QMenu("Settings", window)

    # Application Settings
    settings_action = QAction("⚙️ Application Settings", window)
    def open_settings():
        from settings import SettingsPanel
        if hasattr(window, "browser") and window.browser:
            panel = SettingsPanel()
            # Apply current theme to the settings panel
            panel.apply_theme(window.settings.get('theme', 'light'))
            panel.settings_changed.connect(window.browser.on_settings_changed)
            panel.settings_changed.connect(window.on_settings_changed)
            window.browser.set_right_panel(panel)
    settings_action.triggered.connect(open_settings)
    settings_menu.addAction(settings_action)

    menu_bar.addMenu(settings_menu)

    # Git operations are now available via right-click context menus on repos and files

    # --- Help Menu ---
    help_menu = QMenu("Help", window)

    docs_action = QAction("Documentation", window)
    docs_action.triggered.connect(open_docs)
    help_menu.addAction(docs_action)

    about_action = QAction("About", window)
    about_action.triggered.connect(lambda: show_about(window))
    help_menu.addAction(about_action)

    menu_bar.addMenu(help_menu)

    # Attach menu bar to the window
    window.setMenuBar(menu_bar)


def open_docs():
    """Opens local documentation or fallback URL."""
    docs_path = Path(__file__).parent / "docs" / "index.html"
    if docs_path.exists():
        webbrowser.open(docs_path.as_uri())
    else:
        webbrowser.open("https://gitea.yourserver.com/youruser/Gitea-Interact/wiki")


def show_about(parent):
    """Displays an About dialog."""
    about_box = QMessageBox(parent)
    about_box.setWindowTitle("About Gitea Interact")
    about_box.setText(
        "<h3>Gitea Interact</h3>"
        "<p>A simple Linux desktop app for interacting with Gitea repositories.</p>"
        "<p>Version 0.1.0</p>"
    )
    about_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    about_box.exec()

