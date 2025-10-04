import os
import subprocess
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QListWidget, QListWidgetItem, QFrame, QSplitter,
    QMessageBox, QProgressBar, QTabWidget, QScrollArea, QGroupBox,
    QCheckBox, QLineEdit, QComboBox, QApplication
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QTextCursor, QColor, QBrush
import git
from git import Repo, InvalidGitRepositoryError
from theme_manager import ThemeManager

class GitLogThread(QThread):
    """Thread for running git log operations"""
    log_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, repo_path, max_commits=50):
        super().__init__()
        self.repo_path = repo_path
        self.max_commits = max_commits
    
    def run(self):
        try:
            repo = Repo(self.repo_path)
            commits = []
            for commit in repo.iter_commits(max_count=self.max_commits):
                commits.append({
                    'hash': commit.hexsha[:8],
                    'message': commit.message.strip(),
                    'author': commit.author.name,
                    'date': commit.committed_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                    'full_hash': commit.hexsha
                })
            self.log_ready.emit(commits)
        except Exception as e:
            self.error_occurred.emit(str(e))

class GitPushThread(QThread):
    """Thread for running git push operations with progress tracking"""
    progress_update = pyqtSignal(str)
    push_completed = pyqtSignal(str)
    push_failed = pyqtSignal(str)
    
    def __init__(self, git_repo, remote, branch):
        super().__init__()
        self.git_repo = git_repo
        self.remote = remote
        self.branch = branch
    
    def run(self):
        try:
            self.progress_update.emit("Initializing push...")
            
            # Check if there are commits to push
            try:
                current_branch = self.git_repo.active_branch.name
                ahead = self.git_repo.iter_commits(f'{self.remote}/{current_branch}..{current_branch}')
                commits_ahead = list(ahead)
                
                if not commits_ahead:
                    self.push_completed.emit("No changes to push to the server")
                    return
                
                self.progress_update.emit(f"Found {len(commits_ahead)} commits to push...")
                
                # Push changes with progress tracking
                self.progress_update.emit("Connecting to remote repository...")
                
                # Use git command with progress output
                result = self.git_repo.git.push(self.remote, self.branch, progress=True)
                
                self.progress_update.emit("Push completed successfully!")
                self.push_completed.emit(f"Successfully pushed {len(commits_ahead)} commits to {self.remote}/{self.branch}")
                
            except Exception as e:
                error_msg = str(e)
                if "no upstream branch" in error_msg.lower():
                    self.push_completed.emit("No remote repository configured for this branch")
                elif "non-fast-forward" in error_msg or "rejected" in error_msg:
                    self.push_failed.emit(f"Push rejected: {error_msg}")
                else:
                    raise e
                    
        except Exception as e:
            self.push_failed.emit(f"Push failed: {str(e)}")

class GitOperationsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_repo = None
        self.repo_path = None
        self.git_repo = None
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the Git operations UI"""
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)
        
        # Header section
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e1e5e9;
                border-radius: 12px;
                padding: 16px;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(16, 16, 16, 16)
        header_layout.setSpacing(8)
        
        # Title
        title_label = QLabel("🔧 Git Operations")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #2ea44f;
                padding: 4px 0;
            }
        """)
        header_layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel("Manage your Git repository: view history, stage changes, push to server, and revert modifications.")
        desc_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #6c757d;
                padding: 4px 0;
                line-height: 1.4;
            }
        """)
        desc_label.setWordWrap(True)
        header_layout.addWidget(desc_label)
        
        main_layout.addWidget(header_frame)
        
        # Create tab widget for different operations
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #e1e5e9;
                border-radius: 8px;
                background-color: #ffffff;
            }
            QTabBar::tab {
                background-color: #f8f9fa;
                color: #495057;
                padding: 12px 20px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #2ea44f;
                color: white;
            }
            QTabBar::tab:hover {
                background-color: #e8f5e8;
            }
        """)
        
        # Create tabs
        self.create_log_tab()
        self.create_stage_tab()
        self.create_push_tab()
        self.create_revert_tab()
        
        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)
    
    def create_log_tab(self):
        """Create the Git log tab"""
        log_widget = QWidget()
        layout = QVBoxLayout(log_widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Log controls
        controls_frame = QFrame()
        controls_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #e1e5e9;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        controls_layout = QHBoxLayout(controls_frame)
        
        self.refresh_log_btn = QPushButton("🔄 Refresh Log")
        self.refresh_log_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #17a2b8, stop:1 #138496);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #138496, stop:1 #117a8b);
            }
        """)
        self.refresh_log_btn.clicked.connect(self.refresh_git_log)
        controls_layout.addWidget(self.refresh_log_btn)
        
        self.max_commits_input = QLineEdit("50")
        self.max_commits_input.setPlaceholderText("Max commits to show")
        self.max_commits_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #e1e5e9;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
                background-color: #ffffff;
            }
            QLineEdit:focus {
                border: 2px solid #2ea44f;
            }
        """)
        controls_layout.addWidget(QLabel("Max commits:"))
        controls_layout.addWidget(self.max_commits_input)
        controls_layout.addStretch()
        
        layout.addWidget(controls_frame)
        
        # Log display
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #e1e5e9;
                border-radius: 8px;
                padding: 12px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 13px;
                line-height: 1.4;
            }
        """)
        layout.addWidget(self.log_display)
        
        self.tab_widget.addTab(log_widget, "📋 Git Log")
    
    def create_stage_tab(self):
        """Create the Git stage/add tab"""
        stage_widget = QWidget()
        layout = QVBoxLayout(stage_widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Status controls
        status_frame = QFrame()
        status_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #e1e5e9;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        status_layout = QHBoxLayout(status_frame)
        
        self.refresh_status_btn = QPushButton("🔄 Check Status")
        self.refresh_status_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #17a2b8, stop:1 #138496);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #138496, stop:1 #117a8b);
            }
        """)
        self.refresh_status_btn.clicked.connect(self.refresh_git_status)
        status_layout.addWidget(self.refresh_status_btn)
        
        self.stage_all_btn = QPushButton("➕ Stage All")
        self.stage_all_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #2ea44f, stop:1 #28a745);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #28a745, stop:1 #1e7e34);
            }
        """)
        self.stage_all_btn.clicked.connect(self.stage_all_changes)
        status_layout.addWidget(self.stage_all_btn)
        
        status_layout.addStretch()
        layout.addWidget(status_frame)
        
        # File status list
        self.status_list = QListWidget()
        self.status_list.setStyleSheet("""
            QListWidget {
                background-color: #ffffff;
                border: 1px solid #e1e5e9;
                border-radius: 8px;
                padding: 8px;
                font-size: 14px;
                selection-background-color: #2ea44f;
                alternate-background-color: #f8f9fa;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
                margin: 2px;
            }
            QListWidget::item:selected {
                background-color: #2ea44f;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #e8f5e8;
            }
        """)
        layout.addWidget(self.status_list)
        
        # Commit section
        commit_frame = QFrame()
        commit_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #e1e5e9;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        commit_layout = QVBoxLayout(commit_frame)
        
        commit_layout.addWidget(QLabel("Commit Message:"))
        self.commit_message = QLineEdit()
        self.commit_message.setPlaceholderText("Enter commit message...")
        self.commit_message.setStyleSheet("""
            QLineEdit {
                border: 1px solid #e1e5e9;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
                background-color: #ffffff;
            }
            QLineEdit:focus {
                border: 2px solid #2ea44f;
            }
        """)
        commit_layout.addWidget(self.commit_message)
        
        commit_btn_layout = QHBoxLayout()
        
        self.stage_commit_btn = QPushButton("⚡ Stage & Commit")
        self.stage_commit_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #17a2b8, stop:1 #138496);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #138496, stop:1 #117a8b);
            }
        """)
        self.stage_commit_btn.clicked.connect(self.stage_and_commit)
        commit_btn_layout.addWidget(self.stage_commit_btn)
        
        self.commit_btn = QPushButton("💾 Commit Only")
        self.commit_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #2ea44f, stop:1 #28a745);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #28a745, stop:1 #1e7e34);
            }
        """)
        self.commit_btn.clicked.connect(self.commit_changes)
        commit_btn_layout.addWidget(self.commit_btn)
        commit_btn_layout.addStretch()
        
        commit_layout.addLayout(commit_btn_layout)
        layout.addWidget(commit_frame)
        
        self.tab_widget.addTab(stage_widget, "➕ Stage & Commit")
    
    def create_push_tab(self):
        """Create the Git push tab"""
        push_widget = QWidget()
        layout = QVBoxLayout(push_widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Push controls
        push_frame = QFrame()
        push_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #e1e5e9;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        push_layout = QVBoxLayout(push_frame)
        
        # Remote selection
        remote_layout = QHBoxLayout()
        remote_layout.addWidget(QLabel("Remote:"))
        self.remote_combo = QComboBox()
        self.remote_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #e1e5e9;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
                background-color: #ffffff;
            }
            QComboBox:focus {
                border: 2px solid #2ea44f;
            }
        """)
        remote_layout.addWidget(self.remote_combo)
        remote_layout.addStretch()
        push_layout.addLayout(remote_layout)
        
        # Branch selection
        branch_layout = QHBoxLayout()
        branch_layout.addWidget(QLabel("Branch:"))
        self.branch_combo = QComboBox()
        self.branch_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #e1e5e9;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
                background-color: #ffffff;
            }
            QComboBox:focus {
                border: 2px solid #2ea44f;
            }
        """)
        branch_layout.addWidget(self.branch_combo)
        branch_layout.addStretch()
        push_layout.addLayout(branch_layout)
        
        # Push buttons
        btn_layout = QHBoxLayout()
        
        self.refresh_remotes_btn = QPushButton("🔄 Refresh")
        self.refresh_remotes_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #17a2b8, stop:1 #138496);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #138496, stop:1 #117a8b);
            }
        """)
        self.refresh_remotes_btn.clicked.connect(self.refresh_remotes)
        btn_layout.addWidget(self.refresh_remotes_btn)
        
        self.push_btn = QPushButton("🚀 Push to Server")
        self.push_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #2ea44f, stop:1 #28a745);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #28a745, stop:1 #1e7e34);
            }
        """)
        self.push_btn.clicked.connect(self.push_changes)
        btn_layout.addWidget(self.push_btn)
        
        btn_layout.addStretch()
        push_layout.addLayout(btn_layout)
        
        layout.addWidget(push_frame)
        
        # Progress bar for push operations
        self.push_progress = QProgressBar()
        self.push_progress.setVisible(False)
        self.push_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #e1e5e9;
                border-radius: 8px;
                text-align: center;
                font-weight: bold;
                background-color: #f8f9fa;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #2ea44f, stop:1 #28a745);
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.push_progress)
        
        # Push output
        self.push_output = QTextEdit()
        self.push_output.setReadOnly(True)
        self.push_output.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #e1e5e9;
                border-radius: 8px;
                padding: 12px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 13px;
                line-height: 1.4;
            }
        """)
        layout.addWidget(self.push_output)
        
        self.tab_widget.addTab(push_widget, "🚀 Push")
    
    def create_revert_tab(self):
        """Create the Git revert tab"""
        revert_widget = QWidget()
        layout = QVBoxLayout(revert_widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Revert controls
        revert_frame = QFrame()
        revert_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #e1e5e9;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        revert_layout = QVBoxLayout(revert_frame)
        
        # File revert
        file_revert_layout = QHBoxLayout()
        self.revert_file_btn = QPushButton("↩️ Revert File")
        self.revert_file_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #ffc107, stop:1 #e0a800);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #e0a800, stop:1 #d39e00);
            }
        """)
        self.revert_file_btn.clicked.connect(self.revert_file)
        file_revert_layout.addWidget(self.revert_file_btn)
        file_revert_layout.addStretch()
        revert_layout.addLayout(file_revert_layout)
        
        # Commit revert
        commit_revert_layout = QHBoxLayout()
        commit_revert_layout.addWidget(QLabel("Revert Commit:"))
        self.commit_hash_input = QLineEdit()
        self.commit_hash_input.setPlaceholderText("Enter commit hash...")
        self.commit_hash_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #e1e5e9;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
                background-color: #ffffff;
            }
            QLineEdit:focus {
                border: 2px solid #2ea44f;
            }
        """)
        commit_revert_layout.addWidget(self.commit_hash_input)
        
        self.revert_commit_btn = QPushButton("↩️ Revert Commit")
        self.revert_commit_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #dc3545, stop:1 #c82333);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #c82333, stop:1 #bd2130);
            }
        """)
        self.revert_commit_btn.clicked.connect(self.revert_commit)
        commit_revert_layout.addWidget(self.revert_commit_btn)
        revert_layout.addLayout(commit_revert_layout)
        
        # Conflict resolution button
        conflict_layout = QHBoxLayout()
        self.continue_revert_btn = QPushButton("✅ Continue Revert")
        self.continue_revert_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #2ea44f, stop:1 #28a745);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #28a745, stop:1 #1e7e34);
            }
        """)
        self.continue_revert_btn.clicked.connect(self.continue_revert)
        self.continue_revert_btn.setVisible(False)  # Hidden by default
        conflict_layout.addWidget(self.continue_revert_btn)
        conflict_layout.addStretch()
        revert_layout.addLayout(conflict_layout)
        
        # Reset options
        reset_layout = QHBoxLayout()
        self.reset_soft_btn = QPushButton("🔄 Soft Reset")
        self.reset_soft_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #6c757d, stop:1 #5a6268);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #5a6268, stop:1 #495057);
            }
        """)
        self.reset_soft_btn.clicked.connect(lambda: self.reset_repo('soft'))
        reset_layout.addWidget(self.reset_soft_btn)
        
        self.reset_hard_btn = QPushButton("⚠️ Hard Reset")
        self.reset_hard_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #dc3545, stop:1 #c82333);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #c82333, stop:1 #bd2130);
            }
        """)
        self.reset_hard_btn.clicked.connect(lambda: self.reset_repo('hard'))
        reset_layout.addWidget(self.reset_hard_btn)
        
        reset_layout.addStretch()
        revert_layout.addLayout(reset_layout)
        
        layout.addWidget(revert_frame)
        
        # Revert output
        self.revert_output = QTextEdit()
        self.revert_output.setReadOnly(True)
        self.revert_output.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #e1e5e9;
                border-radius: 8px;
                padding: 12px;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 13px;
                line-height: 1.4;
            }
        """)
        layout.addWidget(self.revert_output)
        
        self.tab_widget.addTab(revert_widget, "↩️ Revert")
    
    def set_repo(self, repo_path):
        """Set the current repository"""
        self.repo_path = repo_path
        try:
            self.git_repo = Repo(repo_path)
            self.current_repo = repo_path
            self.refresh_all_data()
        except InvalidGitRepositoryError:
            self.show_error("Not a valid Git repository")
        except Exception as e:
            self.show_error(f"Error opening repository: {str(e)}")
    
    def refresh_all_data(self):
        """Refresh all data for the current repository"""
        if not self.git_repo:
            return
        
        self.refresh_git_log()
        self.refresh_git_status()
        self.refresh_remotes()
    
    def refresh_git_log(self):
        """Refresh the git log"""
        if not self.repo_path:
            return
        
        try:
            max_commits = int(self.max_commits_input.text() or "50")
            self.log_thread = GitLogThread(self.repo_path, max_commits)
            self.log_thread.log_ready.connect(self.display_git_log)
            self.log_thread.error_occurred.connect(self.show_error)
            self.log_thread.start()
        except ValueError:
            self.show_error("Invalid number of commits")
    
    def display_git_log(self, commits):
        """Display the git log"""
        self.log_display.clear()
        if not commits:
            self.log_display.setPlainText("No commits found")
            return
        
        log_text = "Git Commit History\n" + "="*50 + "\n\n"
        for commit in commits:
            log_text += f"🔹 {commit['hash']} - {commit['message']}\n"
            log_text += f"   Author: {commit['author']}\n"
            log_text += f"   Date: {commit['date']}\n"
            log_text += f"   Full Hash: {commit['full_hash']}\n\n"
        
        self.log_display.setPlainText(log_text)
    
    def refresh_git_status(self):
        """Refresh git status"""
        if not self.git_repo:
            return
        
        try:
            self.status_list.clear()
            status = self.git_repo.git.status(porcelain=True)
            
            if not status.strip():
                self.status_list.addItem("✅ Working directory clean")
                return
            
            for line in status.strip().split('\n'):
                if line:
                    status_code = line[:2]
                    filename = line[3:]
                    
                    if status_code[0] == 'M':
                        item = QListWidgetItem(f"📝 Modified: {filename}")
                        item.setForeground(QBrush(QColor("#ffc107")))
                    elif status_code[0] == 'A':
                        item = QListWidgetItem(f"➕ Added: {filename}")
                        item.setForeground(QBrush(QColor("#28a745")))
                    elif status_code[0] == 'D':
                        item = QListWidgetItem(f"❌ Deleted: {filename}")
                        item.setForeground(QBrush(QColor("#dc3545")))
                    elif status_code[0] == '?':
                        item = QListWidgetItem(f"❓ Untracked: {filename}")
                        item.setForeground(QBrush(QColor("#6c757d")))
                    else:
                        item = QListWidgetItem(f"{status_code}: {filename}")
                    
                    self.status_list.addItem(item)
        except Exception as e:
            self.show_error(f"Error checking status: {str(e)}")
    
    def stage_all_changes(self):
        """Stage all changes"""
        if not self.git_repo:
            return
        
        try:
            self.git_repo.git.add('.')
            self.refresh_git_status()
            self.show_success("All changes staged successfully")
        except Exception as e:
            self.show_error(f"Error staging changes: {str(e)}")
    
    def stage_and_commit(self):
        """Stage all changes and commit them"""
        if not self.git_repo:
            return
        
        message = self.commit_message.text().strip()
        if not message:
            self.show_error("Please enter a commit message")
            return
        
        try:
            # First, check if there are any changes to commit
            status = self.git_repo.git.status(porcelain=True)
            if not status.strip():
                self.show_error("No changes to commit. Working directory is clean.")
                return
            
            # Stage all changes
            self.git_repo.git.add('.')
            self.show_success("All changes staged")
            
            # Commit the changes
            self.git_repo.git.commit('-m', message)
            self.commit_message.clear()
            self.refresh_git_status()
            self.refresh_git_log()
            self.show_success("Changes staged and committed successfully")
        except Exception as e:
            self.show_error(f"Error staging and committing changes: {str(e)}")
    
    def commit_changes(self):
        """Commit staged changes"""
        if not self.git_repo:
            return
        
        message = self.commit_message.text().strip()
        if not message:
            self.show_error("Please enter a commit message")
            return
        
        try:
            # First, check if there are any changes to commit
            status = self.git_repo.git.status(porcelain=True)
            if not status.strip():
                self.show_error("No changes to commit. Working directory is clean.")
                return
            
            # Check if there are unstaged changes
            unstaged_changes = False
            for line in status.strip().split('\n'):
                if line and line[0] != ' ' and line[0] != '?':
                    unstaged_changes = True
                    break
            
            # If there are unstaged changes, ask user if they want to stage them
            if unstaged_changes:
                reply = QMessageBox.question(
                    self, "Unstaged Changes",
                    "There are unstaged changes. Would you like to stage all changes before committing?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.git_repo.git.add('.')
                    self.show_success("All changes staged automatically")
            
            # Now commit the changes
            self.git_repo.git.commit('-m', message)
            self.commit_message.clear()
            self.refresh_git_status()
            self.refresh_git_log()
            self.show_success("Changes committed successfully")
        except Exception as e:
            self.show_error(f"Error committing changes: {str(e)}")
    
    def refresh_remotes(self):
        """Refresh remote information"""
        if not self.git_repo:
            return
        
        try:
            self.remote_combo.clear()
            self.branch_combo.clear()
            
            # Get remotes
            remotes = self.git_repo.remotes
            for remote in remotes:
                self.remote_combo.addItem(remote.name)
            
            # Get branches
            branches = self.git_repo.branches
            for branch in branches:
                self.branch_combo.addItem(branch.name)
            
            # Set default remote and branch
            if self.remote_combo.count() > 0:
                self.remote_combo.setCurrentText('origin')
            if self.branch_combo.count() > 0:
                self.branch_combo.setCurrentText('main')
        except Exception as e:
            self.show_error(f"Error refreshing remotes: {str(e)}")
    
    def push_changes(self):
        """Push changes to remote"""
        if not self.git_repo:
            return
        
        remote = self.remote_combo.currentText()
        branch = self.branch_combo.currentText()
        
        if not remote or not branch:
            self.show_error("Please select remote and branch")
            return
        
        # Disable push button and show progress
        self.push_btn.setEnabled(False)
        self.push_btn.setText("🔄 Pushing...")
        self.push_progress.setVisible(True)
        self.push_progress.setRange(0, 0)  # Indeterminate progress
        self.push_progress.setFormat("Pushing to server...")
        
        self.push_output.clear()
        self.push_output.append(f"Starting push to {remote}/{branch}...")
        
        # Create and start push thread
        self.push_thread = GitPushThread(self.git_repo, remote, branch)
        self.push_thread.progress_update.connect(self.update_push_progress)
        self.push_thread.push_completed.connect(self.push_completed)
        self.push_thread.push_failed.connect(self.push_failed)
        self.push_thread.start()
    
    def update_push_progress(self, message):
        """Update progress bar with status message"""
        self.push_output.append(f"📡 {message}")
        self.push_progress.setFormat(message)
        QApplication.processEvents()  # Keep UI responsive
    
    def push_completed(self, message):
        """Handle successful push completion"""
        self.push_progress.setVisible(False)
        self.push_btn.setEnabled(True)
        self.push_btn.setText("🚀 Push to Server")
        self.push_output.append(f"✅ {message}")
        self.show_success("Push completed successfully")
        self.push_thread.deleteLater()
    
    def push_failed(self, error_message):
        """Handle push failure"""
        self.push_progress.setVisible(False)
        self.push_btn.setEnabled(True)
        self.push_btn.setText("🚀 Push to Server")
        self.push_output.append(f"❌ {error_message}")
        self.show_error(f"Push failed: {error_message}")
        self.push_thread.deleteLater()
    
    def revert_file(self):
        """Revert selected file"""
        current_item = self.status_list.currentItem()
        if not current_item:
            self.show_error("Please select a file to revert")
            return
        
        filename = current_item.text().split(': ', 1)[1]
        
        reply = QMessageBox.question(
            self, "Revert File",
            f"Are you sure you want to revert changes to '{filename}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.git_repo.git.checkout('--', filename)
                self.refresh_git_status()
                self.show_success(f"File '{filename}' reverted successfully")
            except Exception as e:
                self.show_error(f"Error reverting file: {str(e)}")
    
    def revert_commit(self):
        """Revert a specific commit"""
        commit_hash = self.commit_hash_input.text().strip()
        if not commit_hash:
            self.show_error("Please enter a commit hash")
            return
        
        reply = QMessageBox.question(
            self, "Revert Commit",
            f"Are you sure you want to revert commit '{commit_hash}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Try to revert the commit
                result = self.git_repo.git.revert(commit_hash, '--no-edit')
                self.revert_output.append(f"Commit reverted: {result}")
                self.refresh_git_log()
                self.refresh_git_status()
                self.show_success("Commit reverted successfully")
            except Exception as e:
                error_msg = str(e)
                self.revert_output.append(f"Revert failed: {error_msg}")
                
                # Check if it's a merge conflict
                if "CONFLICT" in error_msg or "conflict" in error_msg.lower():
                    self.handle_revert_conflict(commit_hash)
                else:
                    self.show_error(f"Error reverting commit: {error_msg}")
    
    def handle_revert_conflict(self, commit_hash):
        """Handle revert conflicts"""
        self.revert_output.append("\n" + "="*50)
        self.revert_output.append("MERGE CONFLICT DETECTED")
        self.revert_output.append("="*50)
        self.revert_output.append("The revert operation encountered a merge conflict.")
        self.revert_output.append("This happens when the commit you're trying to revert")
        self.revert_output.append("has been modified by later commits.")
        self.revert_output.append("\nYou have several options:")
        self.revert_output.append("1. Resolve conflicts manually and continue")
        self.revert_output.append("2. Skip this revert operation")
        self.revert_output.append("3. Abort the revert operation")
        self.revert_output.append("\n" + "="*50)
        
        # Show conflict resolution dialog
        msg = QMessageBox(self)
        msg.setWindowTitle("Revert Conflict")
        msg.setText("The revert operation encountered a merge conflict.\n\nWhat would you like to do?")
        msg.setIcon(QMessageBox.Icon.Warning)
        
        # Add custom buttons
        resolve_btn = msg.addButton("🔧 Resolve Conflicts", QMessageBox.ButtonRole.ActionRole)
        skip_btn = msg.addButton("⏭️ Skip Revert", QMessageBox.ButtonRole.ActionRole)
        abort_btn = msg.addButton("❌ Abort Revert", QMessageBox.ButtonRole.ActionRole)
        cancel_btn = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        
        msg.exec()
        
        clicked_button = msg.clickedButton()
        if clicked_button == resolve_btn:
            self.resolve_revert_conflicts()
        elif clicked_button == skip_btn:
            self.skip_revert()
        elif clicked_button == abort_btn:
            self.abort_revert()
    
    def resolve_revert_conflicts(self):
        """Guide user to resolve conflicts manually"""
        self.revert_output.append("\n🔧 MANUAL CONFLICT RESOLUTION REQUIRED")
        self.revert_output.append("="*50)
        self.revert_output.append("1. Open the conflicted files in your editor")
        self.revert_output.append("2. Look for conflict markers (<<<<<<< ======= >>>>>>>)")
        self.revert_output.append("3. Edit the files to resolve conflicts")
        self.revert_output.append("4. Save the files")
        self.revert_output.append("5. Click 'Continue Revert' button below")
        self.revert_output.append("="*50)
        
        # Show the continue revert button
        self.continue_revert_btn.setVisible(True)
        
        QMessageBox.information(
            self, "Resolve Conflicts",
            "Please resolve the conflicts in your files manually, then click the 'Continue Revert' button below."
        )
    
    def continue_revert(self):
        """Continue the revert after conflicts are resolved"""
        try:
            # Add the resolved files
            self.git_repo.git.add('.')
            self.revert_output.append("Resolved files added to staging area")
            
            # Continue the revert
            result = self.git_repo.git.revert('--continue')
            self.revert_output.append(f"Revert completed: {result}")
            self.refresh_git_log()
            self.refresh_git_status()
            self.show_success("Revert completed successfully after resolving conflicts")
            
            # Hide the continue button
            self.continue_revert_btn.setVisible(False)
        except Exception as e:
            self.revert_output.append(f"Error continuing revert: {str(e)}")
            self.show_error(f"Error continuing revert: {str(e)}")
    
    def skip_revert(self):
        """Skip the current revert operation"""
        try:
            self.git_repo.git.revert('--skip')
            self.revert_output.append("Revert operation skipped")
            self.refresh_git_log()
            self.refresh_git_status()
            self.show_success("Revert operation skipped")
            
            # Hide the continue button
            self.continue_revert_btn.setVisible(False)
        except Exception as e:
            self.revert_output.append(f"Error skipping revert: {str(e)}")
            self.show_error(f"Error skipping revert: {str(e)}")
    
    def abort_revert(self):
        """Abort the revert operation"""
        try:
            self.git_repo.git.revert('--abort')
            self.revert_output.append("Revert operation aborted")
            self.refresh_git_log()
            self.refresh_git_status()
            self.show_success("Revert operation aborted")
            
            # Hide the continue button
            self.continue_revert_btn.setVisible(False)
        except Exception as e:
            self.revert_output.append(f"Error aborting revert: {str(e)}")
            self.show_error(f"Error aborting revert: {str(e)}")
    
    def reset_repo(self, reset_type):
        """Reset repository"""
        commit_hash = self.commit_hash_input.text().strip()
        if not commit_hash:
            self.show_error("Please enter a commit hash to reset to")
            return
        
        reset_name = "Soft" if reset_type == 'soft' else "Hard"
        reply = QMessageBox.question(
            self, f"{reset_name} Reset",
            f"Are you sure you want to perform a {reset_name.lower()} reset to '{commit_hash}'?\n\n"
            f"{'This will keep changes in working directory.' if reset_type == 'soft' else 'This will permanently delete all changes.'}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if reset_type == 'soft':
                    self.git_repo.git.reset('--soft', commit_hash)
                else:
                    self.git_repo.git.reset('--hard', commit_hash)
                
                self.revert_output.append(f"{reset_name} reset to {commit_hash} successful")
                self.refresh_git_log()
                self.refresh_git_status()
                self.show_success(f"{reset_name} reset completed successfully")
            except Exception as e:
                self.revert_output.append(f"Reset failed: {str(e)}")
                self.show_error(f"Error performing {reset_name.lower()} reset: {str(e)}")
    
    def show_error(self, message):
        """Show error message"""
        QMessageBox.warning(self, "Error", message)
    
    def show_success(self, message):
        """Show success message"""
        QMessageBox.information(self, "Success", message)
    
    def apply_theme(self, theme_name):
        """Apply theme to the GitOperationsPanel"""
        colors = ThemeManager.get_theme_colors(theme_name)
        
        # Apply comprehensive panel theme
        self.setStyleSheet(ThemeManager.get_panel_style(theme_name) + f"""
            QTabWidget::pane {{
                border: 1px solid {colors['border_color']};
                border-radius: 8px;
                background-color: {colors['panel_bg']};
            }}
            QTabBar::tab {{
                background-color: {colors['input_bg']};
                color: {colors['text_primary']};
                padding: 12px 20px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {colors['accent_color']};
                color: {colors['menu_text']};
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
