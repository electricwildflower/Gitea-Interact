from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox, QProgressBar, QApplication, QComboBox, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
import requests
import subprocess
from pathlib import Path
from api_config import load_api_settings, get_api_configs, get_api_config_by_name
from theme_manager import ThemeManager

BASE_DOWNLOAD_DIR = Path.home() / "Gitea Repos"


class UserManagerDialogue(QWidget):
    repo_changed = pyqtSignal()  # Signal to notify when repos are added
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.parent_window = parent  # used to refresh tree after cloning
        self.settings = load_api_settings()
        self.selected_config = None
        self.downloaded_count = 0

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
        title = QLabel("📦 Bulk Download User Repositories")
        # Title styling will be applied by theme
        title.setProperty("title", "true")  # For special title styling
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # API Configuration selection
        config_label = QLabel("🌐 Select Gitea Server:")
        # Config label styling will be applied by theme
        layout.addWidget(config_label)
        
        self.config_combo = QComboBox()
        # Config combo styling will be applied by theme
        self.config_combo.currentTextChanged.connect(self.on_config_changed)
        layout.addWidget(self.config_combo)
        
        # Username section
        username_label = QLabel("👤 Username:")
        # Username label styling will be applied by theme
        layout.addWidget(username_label)
        
        self.username_input = QLineEdit()
        # Username input styling will be applied by theme
        self.username_input.setPlaceholderText("Enter the username whose repositories you want to download")
        layout.addWidget(self.username_input)

        # API Token Status (now handled by configuration dropdown)
        # Removed token_status_label as we now use the configuration dropdown

        # Fetch Repos Button
        self.fetch_button = QPushButton("🔍 Fetch Repositories")
        # Fetch button styling will be applied by theme
        layout.addWidget(self.fetch_button)

        # Repo List
        list_label = QLabel("📋 Available Repositories:")
        # List label styling will be applied by theme
        layout.addWidget(list_label)
        
        self.repo_list = QListWidget()
        # Repo list styling will be applied by theme
        layout.addWidget(self.repo_list)

        # Progress Bar
        self.progress_bar = QProgressBar()
        # Progress bar styling will be applied by theme
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Status Label
        self.status_label = QLabel("")
        # Status label styling will be applied by theme
        layout.addWidget(self.status_label)

        # Download Selected Button
        self.download_button = QPushButton("⬇️ Download Selected Repositories")
        # Download button styling will be applied by theme
        self.download_button.setEnabled(False)
        layout.addWidget(self.download_button)

        # Connect Signals
        self.fetch_button.clicked.connect(self.fetch_repos)
        self.download_button.clicked.connect(self.download_selected)
        
        # Set content widget layout
        content_widget.setLayout(layout)
        
        # Set content widget as scroll area widget
        scroll_area.setWidget(content_widget)
        
        # Add scroll area to main layout
        main_layout.addWidget(scroll_area)
        
        # Load API configurations after all UI elements are created
        self.load_api_configurations()
        
        # Apply initial theme
        self.apply_theme('light')  # Default theme, will be updated by parent if needed

    def load_api_configurations(self):
        """Load API configurations into the dropdown"""
        self.config_combo.clear()
        configs = get_api_configs()
        
        if not configs:
            self.config_combo.addItem("No API configurations found")
            self.config_combo.setEnabled(False)
            self.status_label.setText("❌ No API configurations found. Please configure API settings first (SSH/API → Configure API).")
        else:
            for config in configs:
                display_name = f"🌐 {config.get('name', 'Unnamed')} ({config.get('server_url', 'No URL')})"
                self.config_combo.addItem(display_name, config)
            self.config_combo.setEnabled(True)
            # Select the first configuration by default
            if configs:
                self.on_config_changed(self.config_combo.currentText())
    
    def on_config_changed(self, text):
        """Handle API configuration selection change"""
        if not text or "No API configurations found" in text:
            self.selected_config = None
            return
        
        # Get the selected configuration
        current_data = self.config_combo.currentData()
        if current_data:
            self.selected_config = current_data
            self.status_label.setText(f"Selected: {self.selected_config.get('name', 'Unnamed')} - {self.selected_config.get('server_url', 'No URL')}")
        else:
            self.selected_config = None

    # -------------------------------
    # Fetch user repos from Gitea API
    # -------------------------------
    def fetch_repos(self):
        username = self.username_input.text().strip()

        if not username:
            QMessageBox.warning(self, "Error", "Please provide username.")
            return
            
        if not self.selected_config:
            QMessageBox.warning(self, "Error", "Please select a Gitea server configuration.")
            return

        server = self.selected_config.get('server_url', '').strip()
        token = self.selected_config.get('token', '').strip()

        if not server or not token:
            QMessageBox.warning(self, "Error", "Selected configuration is missing server URL or token.")
            return

        # Validate server URL format
        if not server.startswith(('http://', 'https://')):
            server = f"https://{server}"

        # Clean up server URL (remove trailing slash)
        server = server.rstrip('/')

        url = f"{server}/api/v1/users/{username}/repos"
        headers = {"Authorization": f"token {token}"}

        self.status_label.setText("Fetching repositories...")
        self.fetch_button.setEnabled(False)
        QApplication.processEvents()

        try:
            # Try with SSL verification first
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            repos = resp.json()
        except requests.exceptions.SSLError:
            # If SSL fails, try without verification (for self-signed certs)
            try:
                resp = requests.get(url, headers=headers, verify=False, timeout=30)
                resp.raise_for_status()
                repos = resp.json()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to fetch repos (SSL and non-SSL failed):\n{e}")
                self.status_label.setText("")
                self.fetch_button.setEnabled(True)
                return
        except requests.exceptions.RequestException as e:
            QMessageBox.warning(self, "Error", f"Failed to fetch repos:\n{e}")
            self.status_label.setText("")
            self.fetch_button.setEnabled(True)
            return

        # Populate list widget
        self.repo_list.clear()
        if not repos:
            self.status_label.setText("No repositories found for this user.")
            self.download_button.setEnabled(False)
        else:
            # Get existing repos to show status
            from repo_utils import get_existing_repo_names
            existing_repos = get_existing_repo_names()
            
            for repo in repos:
                # Create a more informative display
                repo_name = repo["name"]
                repo_desc = repo.get("description", "No description")
                
                # Check if repo already exists
                if repo_name in existing_repos:
                    display_text = f"✅ {repo_name} - {repo_desc[:40]}{'...' if len(repo_desc) > 40 else ''} (Already exists)"
                else:
                    display_text = f"{repo_name} - {repo_desc[:50]}{'...' if len(repo_desc) > 50 else ''}"
                
                item = QListWidgetItem(display_text)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                
                # Pre-check repos that don't exist yet
                if repo_name not in existing_repos:
                    item.setCheckState(Qt.CheckState.Unchecked)
                else:
                    # Don't check existing repos by default
                    item.setCheckState(Qt.CheckState.Unchecked)
                
                item.setData(Qt.ItemDataRole.UserRole, repo)  # store full repo dict
                self.repo_list.addItem(item)
            
            existing_count = len([r for r in repos if r["name"] in existing_repos])
            new_count = len(repos) - existing_count
            
            if existing_count > 0:
                self.status_label.setText(f"Found {len(repos)} repositories ({new_count} new, {existing_count} already exist). Select the ones you want to download.")
            else:
                self.status_label.setText(f"Found {len(repos)} repositories. Select the ones you want to download.")
            self.download_button.setEnabled(True)

        self.fetch_button.setEnabled(True)

    # -------------------------------
    # Download selected repos via git clone
    # -------------------------------
    def download_selected(self):
        selected_repos = []
        for i in range(self.repo_list.count()):
            item = self.repo_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected_repos.append(item.data(Qt.ItemDataRole.UserRole))

        if not selected_repos:
            QMessageBox.information(self, "No Selection", "Please select at least one repository to download.")
            return

        # Get authentication details
        username = self.username_input.text().strip()
        
        if not username:
            QMessageBox.warning(self, "Error", "Please provide username.")
            return
            
        if not self.selected_config:
            QMessageBox.warning(self, "Error", "Please select a Gitea server configuration.")
            return

        BASE_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

        # Check for existing repos and filter them out
        from repo_utils import get_existing_repo_names
        existing_repos = get_existing_repo_names()
        
        # Separate new repos from existing ones
        new_repos = []
        already_existing = []
        
        for repo in selected_repos:
            repo_name = repo["name"]
            if repo_name in existing_repos:
                already_existing.append(repo_name)
            else:
                new_repos.append(repo)
        
        # Show info about existing repos
        if already_existing:
            existing_list = ", ".join(already_existing)
            QMessageBox.information(
                self, 
                "Some Repos Already Exist", 
                f"The following repositories already exist and will be skipped:\n{existing_list}\n\nOnly new repositories will be downloaded."
            )
        
        if not new_repos:
            QMessageBox.information(self, "No New Repos", "All selected repositories already exist. Nothing to download.")
            return

        # Setup progress tracking for new repos only
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(new_repos))
        self.progress_bar.setValue(0)
        self.download_button.setEnabled(False)
        self.downloaded_count = 0
        failed_repos = []

        for i, repo in enumerate(new_repos):
            repo_name = repo["name"]
            
            # Construct the correct clone URL with embedded credentials
            server = self.selected_config.get('server_url', '').strip()
            if not server.startswith(('http://', 'https://')):
                server = f"https://{server}"
            server = server.rstrip('/')
            
            # Get the owner from the repo data
            owner = repo.get("owner", {}).get("login", username)  # fallback to username
            
            # Create URL with embedded credentials to avoid prompts
            repo_url = f"{server}/{owner}/{repo_name}.git"
            # Embed credentials in URL: https://username:token@server/path
            token = self.selected_config.get('token', '')
            auth_url = f"{server.replace('https://', f'https://{username}:{token}@')}/{owner}/{repo_name}.git"
            
            dest = BASE_DOWNLOAD_DIR / repo_name

            self.status_label.setText(f"Cloning {repo_name}...")
            QApplication.processEvents()
            
            # Debug: print the URL being used (without password for security)

            # No need to check if dest.exists() since we already filtered out existing repos

            try:
                # Use git clone with SSL certificate bypass and embedded credentials
                git_cmd = [
                    "git", "clone", 
                    "--config", "http.sslVerify=false",  # Disable SSL verification
                    auth_url,  # Use URL with embedded credentials
                    str(dest)
                ]
                
                result = subprocess.run(
                    git_cmd, 
                    check=True, 
                    capture_output=True, 
                    text=True,
                    timeout=300  # 5 minute timeout per repo
                )
                self.downloaded_count += 1
            except subprocess.CalledProcessError as e:
                failed_repos.append(f"{repo_name}: {e.stderr.strip() if e.stderr else str(e)}")
            except subprocess.TimeoutExpired:
                failed_repos.append(f"{repo_name}: Clone timed out after 5 minutes")
            except Exception as e:
                failed_repos.append(f"{repo_name}: {str(e)}")

            self.progress_bar.setValue(i + 1)
            QApplication.processEvents()

        # Show completion message
        self.progress_bar.setVisible(False)
        self.download_button.setEnabled(True)
        
        if failed_repos:
            error_msg = f"Downloaded {self.downloaded_count} repositories successfully.\n\nFailed repositories:\n" + "\n".join(failed_repos)
            QMessageBox.warning(self, "Download Complete with Errors", error_msg)
        else:
            QMessageBox.information(self, "Download Complete", f"Successfully downloaded {self.downloaded_count} repositories!")

        self.status_label.setText(f"Downloaded {self.downloaded_count} repositories.")
        
        # Update JSON file and emit signal to refresh the tree if any repos were downloaded
        if self.downloaded_count > 0:
            # Import here to avoid circular imports
            from repo_utils import update_repo_json
            update_repo_json()
            self.repo_changed.emit()

    def showEvent(self, event):
        """Called when the panel is shown - refresh API configurations in case settings were updated."""
        super().showEvent(event)
        # Reload API configurations in case they were updated
        self.load_api_configurations()
    
    def apply_theme(self, theme_name):
        """Apply theme to the UserManagerDialogue"""
        colors = ThemeManager.get_theme_colors(theme_name)
        
        # Apply comprehensive panel theme
        self.setStyleSheet(ThemeManager.get_panel_style(theme_name) + f"""
            QComboBox {{
                background-color: {colors['input_bg']};
                color: {colors['text_primary']};
                border: 2px solid {colors['border_color']};
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                min-height: 20px;
            }}
            QComboBox:focus {{
                border: 2px solid {colors['accent_color']};
                background-color: {colors['input_bg']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {colors['text_secondary']};
                margin-right: 10px;
            }}
            QComboBox QAbstractItemView {{
                border: 1px solid {colors['border_color']};
                border-radius: 8px;
                background-color: {colors['input_bg']};
                color: {colors['text_primary']};
                selection-background-color: {colors['accent_color']};
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
                padding: 8px;
                border-radius: 4px;
                margin: 2px;
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
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 {colors['button_hover']}, stop:1 {colors['button_bg']});
            }}
            QProgressBar {{
                border: 2px solid {colors['border_color']};
                border-radius: 8px;
                text-align: center;
                background-color: {colors['input_bg']};
                color: {colors['text_primary']};
            }}
            QProgressBar::chunk {{
                background-color: {colors['accent_color']};
                border-radius: 6px;
            }}
            QLabel {{
                color: {colors['text_primary']};
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 4px;
            }}
            QLabel[title="true"] {{
                font-size: 20px;
                font-weight: bold;
                color: {colors['accent_color']};
                padding: 16px;
                background-color: {colors['panel_bg']};
                border-radius: 8px;
                border-left: 4px solid {colors['accent_color']};
            }}
        """)

