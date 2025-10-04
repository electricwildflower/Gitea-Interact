import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QListWidget, QListWidgetItem, QFrame, QMessageBox,
    QScrollArea, QApplication
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor, QColor, QBrush
import git
from git import Repo, InvalidGitRepositoryError
from theme_manager import ThemeManager

class GitLogsThread(QThread):
    """Thread for running git log operations"""
    logs_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, repo_path, file_path=None, max_commits=100):
        super().__init__()
        self.repo_path = repo_path
        self.file_path = file_path
        self.max_commits = max_commits
    
    def run(self):
        try:
            repo = Repo(self.repo_path)
            commits = []
            
            # Determine the main branch to get full history from
            # Try to get the main branch (main, master, or current branch)
            main_branch = None
            try:
                # Try to get the main branch
                if 'main' in repo.branches:
                    main_branch = repo.branches['main']
                elif 'master' in repo.branches:
                    main_branch = repo.branches['master']
                else:
                    # Fall back to the current branch
                    main_branch = repo.active_branch
            except:
                # If we're in detached HEAD, try to find the main branch
                try:
                    if 'main' in repo.branches:
                        main_branch = repo.branches['main']
                    elif 'master' in repo.branches:
                        main_branch = repo.branches['master']
                    else:
                        # Get the first available branch
                        main_branch = list(repo.branches)[0]
                except:
                    # Last resort: use HEAD
                    main_branch = repo.head
            
            # Get commits for specific file or entire repos
            if self.file_path:
                # Get commits that affected this specific file from the main branch
                for commit in repo.iter_commits(main_branch, paths=str(self.file_path), max_count=self.max_commits):
                    commits.append({
                        'hash': commit.hexsha[:8],
                        'message': commit.message.strip(),
                        'author': commit.author.name,
                        'date': commit.committed_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                        'full_hash': commit.hexsha,
                        'is_file_specific': True
                    })
            else:
                # Get all commits for the repo from the main branch
                for commit in repo.iter_commits(main_branch, max_count=self.max_commits):
                    commits.append({
                        'hash': commit.hexsha[:8],
                        'message': commit.message.strip(),
                        'author': commit.author.name,
                        'date': commit.committed_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                        'full_hash': commit.hexsha,
                        'is_file_specific': False
                    })
            
            self.logs_ready.emit(commits)
        except Exception as e:
            self.error_occurred.emit(str(e))

class GitLogsViewer(QWidget):
    def __init__(self, repo_path, file_path=None, parent=None):
        super().__init__(parent)
        self.repo_path = repo_path
        self.file_path = file_path
        self.git_repo = None
        self.current_commits = []
        
        try:
            self.git_repo = Repo(repo_path)
        except InvalidGitRepositoryError:
            self.show_error("Not a valid Git repository")
            return
        except Exception as e:
            self.show_error(f"Error opening repository: {str(e)}")
            return
        
        self.setup_ui()
        self.load_git_logs()
    
    def setup_ui(self):
        """Setup the Git logs viewer UI"""
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)
        
        # Header section
        header_frame = QFrame()
        # Header frame styling will be applied by theme
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(16, 16, 16, 16)
        header_layout.setSpacing(8)
        
        # Title
        if self.file_path:
            title_text = f"📋 Git Logs - {Path(self.file_path).name}"
        else:
            title_text = f"📋 Git Logs - {Path(self.repo_path).name}"
        
        title_label = QLabel(title_text)
        # Title styling will be applied by theme
        header_layout.addWidget(title_label)
        
        # Description
        if self.file_path:
            desc_text = f"Viewing commit history for file: {self.file_path}"
        else:
            desc_text = f"Viewing commit history for repository: {self.repo_path}"
        
        desc_label = QLabel(desc_text)
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
        
        # Controls section
        controls_frame = QFrame()
        # Controls frame styling will be applied by theme
        controls_layout = QHBoxLayout(controls_frame)
        
        self.refresh_btn = QPushButton("🔄 Refresh Logs")
        # Refresh button styling will be applied by theme
        self.refresh_btn.clicked.connect(self.load_git_logs)
        controls_layout.addWidget(self.refresh_btn)
        
        controls_layout.addStretch()
        main_layout.addWidget(controls_frame)
        
        # Logs display with selection
        logs_frame = QFrame()
        # Logs frame styling will be applied by theme
        logs_layout = QVBoxLayout(logs_frame)
        logs_layout.setContentsMargins(12, 12, 12, 12)
        
        # Commits list
        commits_label = QLabel("📋 Select a commit to reverse to:")
        # Commits label styling will be applied by theme
        logs_layout.addWidget(commits_label)
        
        self.commits_list = QListWidget()
        # Commits list styling will be applied by theme
        self.commits_list.itemClicked.connect(self.on_commit_selected)
        logs_layout.addWidget(self.commits_list)
        
        # Selected commit info
        self.selected_commit_info = QLabel("No commit selected")
        # Selected commit info styling will be applied by theme
        self.selected_commit_info.setWordWrap(True)
        logs_layout.addWidget(self.selected_commit_info)
        
        main_layout.addWidget(logs_frame)
        
        # Action buttons for selected commit
        action_frame = QFrame()
        # Action frame styling will be applied by theme
        action_layout = QHBoxLayout(action_frame)
        
        self.safe_revert_btn = QPushButton("✅ Safe Revert (Keep History)")
        # Safe revert button styling will be applied by theme
        self.safe_revert_btn.clicked.connect(self.safe_revert)
        action_layout.addWidget(self.safe_revert_btn)
        
        self.destructive_revert_btn = QPushButton("⚠️ Destructive Revert (Delete History)")
        # Destructive revert button styling will be applied by theme
        self.destructive_revert_btn.clicked.connect(self.destructive_revert)
        action_layout.addWidget(self.destructive_revert_btn)
        
        action_layout.addStretch()
        main_layout.addWidget(action_frame)
        
        self.setLayout(main_layout)
    
    def load_git_logs(self):
        """Load git logs in a separate thread"""
        if not self.git_repo:
            return
        
        # Clear the commits list and show loading state
        self.commits_list.clear()
        self.selected_commit_info.setText("Loading git logs...")
        
        self.logs_thread = GitLogsThread(self.repo_path, self.file_path)
        self.logs_thread.logs_ready.connect(self.display_git_logs)
        self.logs_thread.error_occurred.connect(self.show_error)
        self.logs_thread.start()
    
    def display_git_logs(self, commits):
        """Display the git logs in the commits list"""
        self.current_commits = commits
        self.commits_list.clear()
        self.selected_commit = None
        self.selected_commit_info.setText("No commit selected")
        
        if not commits:
            self.selected_commit_info.setText("No commits found")
            return
        
        # Populate commits list
        for i, commit in enumerate(commits):
            # Create a more readable display text
            display_text = f"#{i+1} {commit['hash']} - {commit['message'][:50]}{'...' if len(commit['message']) > 50 else ''}"
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, commit)
            self.commits_list.addItem(item)
        
        # Select the first commit by default
        if commits:
            self.commits_list.setCurrentRow(0)
            self.on_commit_selected(self.commits_list.item(0))
    
    def on_commit_selected(self, item):
        """Handle commit selection"""
        if not item:
            return
        
        commit = item.data(Qt.ItemDataRole.UserRole)
        self.selected_commit = commit
        
        # Update the selected commit info
        info_text = f"Selected: {commit['hash']}\n"
        info_text += f"Message: {commit['message']}\n"
        info_text += f"Author: {commit['author']}\n"
        info_text += f"Date: {commit['date']}\n"
        info_text += f"Full Hash: {commit['full_hash']}"
        
        self.selected_commit_info.setText(info_text)
    
    def safe_revert(self):
        """Safe revert - keeps history visible, allows forward/backward navigation"""
        if not self.selected_commit:
            self.show_error("Please select a commit from the list above")
            return
        
        # Check for unmerged files first
        if not self.check_and_handle_unmerged_files():
            return
        
        commit = self.selected_commit
        reply = QMessageBox.question(
            self, "Safe Revert (Keep History)",
            f"Are you sure you want to safely revert to commit '{commit['hash']}'?\n\n"
            f"Message: {commit['message']}\n"
            f"Author: {commit['author']}\n"
            f"Date: {commit['date']}\n\n"
            f"✅ SAFE REVERT:\n"
            f"• Switches to this commit without moving branch pointer\n"
            f"• All commits remain VISIBLE in logs\n"
            f"• You can navigate forward/backward between commits\n"
            f"• Current changes are preserved in working directory\n"
            f"• You can easily switch back to any commit later",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if self.file_path:
                    # Checkout specific file to the selected commit
                    self.git_repo.git.checkout(commit['full_hash'], '--', str(self.file_path))
                    self.load_git_logs()
                    self.show_success(f"File safely reverted to commit {commit['hash']} - history preserved")
                else:
                    # Checkout the selected commit (detached HEAD state)
                    self.git_repo.git.checkout(commit['full_hash'])
                    self.load_git_logs()
                    self.show_success(f"Repository safely reverted to commit {commit['hash']} - all commits remain visible in logs")
            except Exception as e:
                self.show_error(f"Error during safe revert: {str(e)}")
    
    def check_and_handle_unmerged_files(self):
        """Check for unmerged files and handle them before operations"""
        try:
            # Check git status for unmerged files
            status = self.git_repo.git.status('--porcelain')
            unmerged_files = []
            
            for line in status.split('\n'):
                if line and (line.startswith('UU ') or line.startswith('AA ') or line.startswith('DD ')):
                    unmerged_files.append(line[3:])  # Remove status prefix
            
            if unmerged_files:
                self.handle_unmerged_files_error(unmerged_files)
                return False
            
            return True
        except Exception as e:
            # If we can't check status, proceed anyway
            return True
    
    def handle_unmerged_files_error(self, unmerged_files=None):
        """Handle the case where there are unmerged files"""
        if unmerged_files is None:
            unmerged_files = ["Unknown files"]
        
        files_list = '\n'.join(f"  • {f}" for f in unmerged_files)
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Unmerged Files Detected")
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText("The repository has unmerged files from a previous operation.")
        msg.setDetailedText(f"Unmerged files:\n{files_list}\n\nYou need to resolve these conflicts before performing new operations.")
        
        # Add custom buttons
        resolve_btn = msg.addButton("🔧 Resolve Conflicts", QMessageBox.ButtonRole.ActionRole)
        abort_btn = msg.addButton("❌ Abort Previous Operation", QMessageBox.ButtonRole.ActionRole)
        reset_btn = msg.addButton("🔄 Reset Repository", QMessageBox.ButtonRole.ActionRole)
        msg.addButton(QMessageBox.StandardButton.Cancel)
        
        msg.exec()
        
        if msg.clickedButton() == resolve_btn:
            self.guide_conflict_resolution(unmerged_files)
        elif msg.clickedButton() == abort_btn:
            self.abort_previous_operation()
        elif msg.clickedButton() == reset_btn:
            self.reset_repository_state()
    
    def guide_conflict_resolution(self, unmerged_files):
        """Guide user to resolve conflicts manually"""
        files_list = '\n'.join(f"  • {f}" for f in unmerged_files)
        
        QMessageBox.information(
            self, "Resolve Conflicts",
            f"Please resolve the conflicts in these files:\n\n{files_list}\n\n"
            "Steps to resolve:\n"
            "1. Open each file in your editor\n"
            "2. Look for conflict markers (<<<<<<< ======= >>>>>>>)\n"
            "3. Edit the files to resolve conflicts\n"
            "4. Save the files\n"
            "5. Use Git commands:\n"
            "   - git add <resolved-files>\n"
            "   - git commit (if needed)\n\n"
            "After resolving, you can try the revert operation again."
        )
    
    def abort_previous_operation(self):
        """Abort any ongoing Git operation"""
        try:
            # Try to abort revert first
            try:
                self.git_repo.git.revert('--abort')
                self.show_success("Previous revert operation aborted successfully")
                return
            except:
                pass
            
            # Try to abort merge
            try:
                self.git_repo.git.merge('--abort')
                self.show_success("Previous merge operation aborted successfully")
                return
            except:
                pass
            
            # Try to abort cherry-pick
            try:
                self.git_repo.git.cherry_pick('--abort')
                self.show_success("Previous cherry-pick operation aborted successfully")
                return
            except:
                pass
            
            self.show_error("No ongoing operation found to abort")
            
        except Exception as e:
            self.show_error(f"Error aborting previous operation: {str(e)}")
    
    def reset_repository_state(self):
        """Reset repository to a clean state"""
        reply = QMessageBox.question(
            self, "Reset Repository",
            "⚠️ WARNING: This will reset the repository to the last commit!\n\n"
            "This will discard all uncommitted changes and resolve conflicts by resetting to HEAD.\n\n"
            "Are you sure you want to do this?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Reset to HEAD, discarding all changes
                self.git_repo.git.reset('--hard', 'HEAD')
                self.load_git_logs()
                self.show_success("Repository reset to clean state - all conflicts resolved")
            except Exception as e:
                self.show_error(f"Error resetting repository: {str(e)}")
    
    def handle_revert_conflict(self, commit, error_msg):
        """Handle merge conflicts during revert operations"""
        # Show conflict resolution dialog
        msg = QMessageBox(self)
        msg.setWindowTitle("Merge Conflict Detected")
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText(f"Merge conflict occurred while reverting commit '{commit['hash']}'")
        msg.setDetailedText(f"Error: {error_msg}\n\nYou have several options:")
        
        # Add custom buttons
        resolve_btn = msg.addButton("🔧 Resolve Conflicts", QMessageBox.ButtonRole.ActionRole)
        skip_btn = msg.addButton("⏭️ Skip Revert", QMessageBox.ButtonRole.ActionRole)
        abort_btn = msg.addButton("❌ Abort Revert", QMessageBox.ButtonRole.ActionRole)
        msg.addButton(QMessageBox.StandardButton.Cancel)
        
        msg.exec()
        
        if msg.clickedButton() == resolve_btn:
            self.resolve_revert_conflicts()
        elif msg.clickedButton() == skip_btn:
            self.skip_revert()
        elif msg.clickedButton() == abort_btn:
            self.abort_revert()
    
    def resolve_revert_conflicts(self):
        """Guide user to resolve conflicts manually"""
        QMessageBox.information(
            self, "Resolve Conflicts",
            "Please resolve the merge conflicts manually:\n\n"
            "1. Open the conflicted files in your editor\n"
            "2. Look for conflict markers (<<<<<<< ======= >>>>>>>)\n"
            "3. Edit the files to resolve conflicts\n"
            "4. Save the files\n"
            "5. Click 'Continue Revert' when done\n\n"
            "The 'Continue Revert' button will appear below."
        )
        
        # Show continue button
        self.show_continue_revert_button()
    
    def skip_revert(self):
        """Skip the current revert"""
        try:
            self.git_repo.git.revert('--skip')
            self.load_git_logs()
            self.show_success("Revert skipped successfully")
        except Exception as e:
            self.show_error(f"Error skipping revert: {str(e)}")
    
    def abort_revert(self):
        """Abort the revert operation"""
        try:
            self.git_repo.git.revert('--abort')
            self.load_git_logs()
            self.show_success("Revert aborted - repository restored to previous state")
        except Exception as e:
            self.show_error(f"Error aborting revert: {str(e)}")
    
    def show_continue_revert_button(self):
        """Show continue revert button"""
        # Add continue button to the action frame
        if not hasattr(self, 'continue_revert_btn'):
            self.continue_revert_btn = QPushButton("✅ Continue Revert")
            self.continue_revert_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                        stop:0 #28a745, stop:1 #20c997);
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                        stop:0 #20c997, stop:1 #17a2b8);
                }
            """)
            self.continue_revert_btn.clicked.connect(self.continue_revert)
            
            # Add to action frame
            action_frame = self.findChild(QFrame)
            if action_frame:
                action_layout = action_frame.layout()
                if action_layout:
                    action_layout.addWidget(self.continue_revert_btn)
        
        self.continue_revert_btn.setVisible(True)
    
    def continue_revert(self):
        """Continue the revert after resolving conflicts"""
        try:
            # Check if there are still conflicts
            status = self.git_repo.git.status('--porcelain')
            if 'UU' in status or 'AA' in status or 'DD' in status:
                QMessageBox.warning(
                    self, "Conflicts Not Resolved",
                    "There are still unresolved conflicts. Please resolve all conflicts before continuing."
                )
                return
            
            # Continue the revert
            self.git_repo.git.revert('--continue')
            self.load_git_logs()
            self.show_success("Revert completed successfully after resolving conflicts")
            
            # Hide continue button
            if hasattr(self, 'continue_revert_btn'):
                self.continue_revert_btn.setVisible(False)
                
        except Exception as e:
            self.show_error(f"Error continuing revert: {str(e)}")
    
    def destructive_revert(self):
        """Destructive revert - deletes history permanently"""
        if not self.selected_commit:
            self.show_error("Please select a commit from the list above")
            return
        
        # Check for unmerged files first
        if not self.check_and_handle_unmerged_files():
            return
        
        commit = self.selected_commit
        reply = QMessageBox.question(
            self, "Destructive Revert (Delete History)",
            f"⚠️ DANGER: This will PERMANENTLY DELETE all commits after '{commit['hash']}'!\n\n"
            f"Message: {commit['message']}\n"
            f"Author: {commit['author']}\n"
            f"Date: {commit['date']}\n\n"
            f"🚨 DESTRUCTIVE REVERT:\n"
            f"• All commits after this one will be LOST FOREVER\n"
            f"• This action CANNOT be undone\n"
            f"• Repository will be reset to this exact state\n"
            f"• Use 'Safe Revert' if you want to preserve commits\n\n"
            f"Are you absolutely sure you want to do this?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if self.file_path:
                    # Reset specific file to the selected commit
                    self.git_repo.git.checkout(commit['full_hash'], '--', str(self.file_path))
                    self.load_git_logs()
                    self.show_success(f"File destructively reverted to commit {commit['hash']} - history deleted")
                else:
                    # Reset entire repo to the selected commit (hard reset)
                    self.git_repo.git.reset('--hard', commit['full_hash'])
                    self.load_git_logs()
                    self.show_success(f"Repository destructively reverted to commit {commit['hash']} - all commits after this have been permanently deleted")
            except Exception as e:
                self.show_error(f"Error during destructive revert: {str(e)}")
    
    def show_error(self, message):
        """Show error message"""
        QMessageBox.warning(self, "Error", message)
    
    def show_success(self, message):
        """Show success message"""
        QMessageBox.information(self, "Success", message)
    
    def apply_theme(self, theme_name):
        """Apply theme to the GitLogsViewer"""
        # Apply git logs viewer theme
        self.setStyleSheet(ThemeManager.get_git_logs_style(theme_name))
