import shutil
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QMessageBox, QListWidget, QListWidgetItem, QApplication, QScrollArea
)
from PyQt6.QtCore import pyqtSignal, Qt
from git import Repo
from repo_utils import load_repos, update_repo_json, BASE_DIR
from theme_manager import ThemeManager

class AddRepoPanel(QWidget):
    repo_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Repositories")
        BASE_DIR.mkdir(exist_ok=True)
        
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
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Title
        title = QLabel("🔧 Add/Remove Single Repositories")
        # Title styling will be applied by theme
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # URL input section
        url_label = QLabel("📡 Repository URL (SSH or HTTPS):")
        # URL label styling will be applied by theme
        layout.addWidget(url_label)
        
        self.url_input = QLineEdit()
        # URL input styling will be applied by theme
        self.url_input.setPlaceholderText("ssh://git@192.168.0.1:222/user/repo.git or https://192.168.0.1:8000/user/repo.git")
        layout.addWidget(self.url_input)

        self.add_btn = QPushButton("➕ Add Repository")
        # Add button styling will be applied by theme
        self.add_btn.clicked.connect(self.add_repo)
        layout.addWidget(self.add_btn)

        self.status_label = QLabel("")
        # Status label styling will be applied by theme
        layout.addWidget(self.status_label)

        # Repositories list section
        list_label = QLabel("📁 Repositories in ~/Gitea Repos:")
        # List label styling will be applied by theme
        layout.addWidget(list_label)
        
        self.repo_list = QListWidget()
        # Repo list styling will be applied by theme
        layout.addWidget(self.repo_list)

        self.remove_btn = QPushButton("🗑️ Remove Selected Repository")
        # Remove button styling will be applied by theme
        self.remove_btn.clicked.connect(self.remove_selected_repo)
        layout.addWidget(self.remove_btn)

        # Set content widget layout
        content_widget.setLayout(layout)
        
        # Set content widget as scroll area widget
        scroll_area.setWidget(content_widget)
        
        # Add scroll area to main layout
        main_layout.addWidget(scroll_area)
        
        self.setLayout(main_layout)
        self.load_repos()

    def load_repos(self):
        self.repo_list.clear()
        for repo in load_repos():
            item = QListWidgetItem(repo["name"])
            self.repo_list.addItem(item)

    def add_repo(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a repository URL.")
            return

        repo_name = url.split("/")[-1].replace(".git", "")
        repo_path = BASE_DIR / repo_name

        if repo_path.exists():
            QMessageBox.warning(self, "Error", f"Repository '{repo_name}' already exists.")
            return

        try:
            self.status_label.setText("Cloning repository...")
            self.add_btn.setEnabled(False)
            QApplication.processEvents()

            # Clone the repository
            Repo.clone_from(url, repo_path)

            # Update the JSON file
            update_repo_json()

            # Reload list on the right panel
            self.load_repos()

            # Reset UI
            self.url_input.clear()
            self.status_label.setText("")

            # Emit signal so left tree refreshes
            self.repo_changed.emit()

            QMessageBox.information(self, "Success", f"Repository '{repo_name}' cloned successfully!")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to clone repo:\n{e}")
            self.status_label.setText("")
        finally:
            self.add_btn.setEnabled(True)

    def remove_selected_repo(self):
        selected = self.repo_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Please select a repository to remove.")
            return

        repo_name = selected.text()
        repo_path = BASE_DIR / repo_name
        reply = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Are you sure you want to remove '{repo_name}'?\nThis will delete the folder but not the base 'Gitea Repos' directory.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                shutil.rmtree(repo_path)
                update_repo_json()
                self.load_repos()

                # Emit signal so left tree refreshes immediately
                self.repo_changed.emit()

                QMessageBox.information(self, "Removed", f"Repository '{repo_name}' removed successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to remove repo:\n{e}")
    
    def apply_theme(self, theme_name):
        """Apply theme to the AddRepoPanel"""
        colors = ThemeManager.get_theme_colors(theme_name)
        
        # Apply comprehensive panel theme
        self.setStyleSheet(ThemeManager.get_panel_style(theme_name) + f"""
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
                padding: 8px;
                border-radius: 4px;
                margin: 2px;
            }}
            QListWidget::item:selected {{
                background-color: {colors['accent_color']};
                color: {colors['menu_text']};
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
                min-width: 80px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 {colors['button_hover']}, stop:1 {colors['button_bg']});
            }}
        """)

