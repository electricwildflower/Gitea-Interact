from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTreeWidget, QTreeWidgetItem, QTextEdit, QFileIconProvider, QLabel, QScrollArea, QPushButton, QMessageBox, QApplication, QMenu
from PyQt6.QtGui import QShortcut, QKeySequence, QBrush, QColor, QPixmap
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
from repo_manager import AddRepoPanel
from repo_utils import load_repos, BASE_DIR
from theme_manager import ThemeManager

# --- Colors ---
GITEA_GREEN = QColor("#2ea44f")
GITEA_UNSAVED = QColor("#ff9900")

class RepoChangeHandler(FileSystemEventHandler):
    def __init__(self, browser):
        self.browser = browser

    def on_any_event(self, event):
        if event.is_directory:
            return
        self.browser.mark_modified(event.src_path)

class RepoWindow(QWidget):
    repo_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.current_file = None
        self.loading_file = False
        self.modified_items = {}
        self.unsaved_items = {}
        self.icon_provider = QFileIconProvider()
        self.observer = Observer()
        self.repos = load_repos()
        self.add_panel = None  # Keep reference to panel

        # --- Layout ---
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        # Splitter styling will be applied by theme

        # --- Left: repo tree with header ---
        # Create a container widget for the tree and header
        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)
        tree_layout.setSpacing(0)
        
        # Create header with title and refresh button
        self.header_widget = QWidget()
        # Header widget styling will be applied by theme
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(8, 8, 8, 8)
        header_layout.setSpacing(8)
        
        # Title label
        title_label = QLabel("📁 Repositories")
        # Title label styling will be applied by theme
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Refresh button
        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setToolTip("Refresh repository tree")
        # Style will be applied via theme_manager in apply_theme method
        self.refresh_btn.clicked.connect(self.refresh_repository_tree)
        header_layout.addWidget(self.refresh_btn)
        
        # Tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)  # Hide default header since we have custom one
        # Tree widget styling will be applied by theme
        self.tree.itemClicked.connect(self.on_item_clicked)
        self.tree.itemExpanded.connect(self.on_item_expanded)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        
        # Add header and tree to container
        tree_layout.addWidget(self.header_widget)
        tree_layout.addWidget(self.tree)
        
        self.splitter.addWidget(tree_container)

        # --- Right: content area (swappable) ---
        self.content_area = QWidget()
        # Content area styling will be applied by theme
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(16, 16, 16, 16)
        self.content_layout.setSpacing(12)
        self.splitter.addWidget(self.content_area)

        # Start with editor panel as default
        self.editor_panel = self.create_editor_panel()
        self.set_right_panel(self.editor_panel)

        self.splitter.setSizes([250, 600])
        layout = QVBoxLayout()
        layout.addWidget(self.splitter)
        self.setLayout(layout)

        # Build repo tree + start watching
        self.build_initial_tree()
        self.start_watching()

    def show_add_panel(self):
        # Create panel only if it doesn't exist
        if self.add_panel is None:
            self.add_panel = AddRepoPanel(self)
            # Connect the signal to a handler that ensures refresh happens
            self.add_panel.repo_changed.connect(self.on_repo_added)
        
        # Always reload the repo list when showing the panel
        self.add_panel.load_repos()
        self.set_right_panel(self.add_panel)

    def on_repo_added(self):
        """Handler for when a repo is added or removed"""
        # Add a small delay to ensure the clone operation and JSON update are complete
        QTimer.singleShot(1000, self.force_refresh_tree)

    def force_refresh_tree(self):
        """Force a complete tree refresh"""
        
        # Save the currently expanded items
        expanded_items = []
        def save_expanded(item):
            if item.isExpanded():
                expanded_items.append(item.text(0))
            for i in range(item.childCount()):
                save_expanded(item.child(i))
        
        for i in range(self.tree.topLevelItemCount()):
            save_expanded(self.tree.topLevelItem(i))
        
        
        # Clear the tree completely
        self.tree.clear()
        
        # Force Qt to process the clear
        QApplication.processEvents()
        
        # Reload the repos from disk
        self.repos = load_repos()
        
        # Rebuild the tree
        for repo in self.repos:
            repo_name = repo["name"]
            repo_path = BASE_DIR / repo_name

            if not repo_path.exists():
                continue

            repo_item = QTreeWidgetItem([repo_name])
            repo_item.setData(0, Qt.ItemDataRole.UserRole, str(repo_path))
            repo_item.setIcon(0, self.icon_provider.icon(QFileIconProvider.IconType.Folder))
            repo_item.setForeground(0, QBrush(GITEA_GREEN))
            self.tree.addTopLevelItem(repo_item)
            
            # Add dummy child for expandable folders
            self.add_dummy(repo_item, repo_path)
            
            # Re-expand if it was expanded before
            if repo_name in expanded_items:
                repo_item.setExpanded(True)
        
        # Force the tree widget to update its display
        self.tree.viewport().update()
        self.tree.repaint()
        QApplication.processEvents()
        
        
        # Update file watchers
        self.update_watchers()

    def refresh_repos(self):
        """Compatibility method - calls force_refresh_tree"""
        self.force_refresh_tree()

    def set_right_panel(self, widget: QWidget):
        # Preserve current window size to prevent auto-resizing
        current_size = self.window().size()
        
        # Remove old widget from layout
        for i in reversed(range(self.content_layout.count())):
            old_widget = self.content_layout.itemAt(i).widget()
            if old_widget:
                self.content_layout.removeWidget(old_widget)
                old_widget.setParent(None)
        
        # Add new widget
        self.content_layout.addWidget(widget)
        self.right_panel = widget
        
        # Restore window size to prevent auto-resizing from content changes
        self.window().resize(current_size)
        widget.show()

    def create_editor_panel(self):
        panel = QWidget()
        # Style will be applied via theme_manager in apply_theme method
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Welcome message with getting started guide (only shown when no file is selected)
        self.welcome_label = QLabel()
        # Welcome content will be updated when theme is applied
        # Welcome label styling will be applied by theme
        self.welcome_label.setWordWrap(True)
        self.welcome_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.welcome_label)

        self.text_viewer = QTextEdit()
        # Style will be applied via theme_manager in apply_theme method
        self.text_viewer.textChanged.connect(self.mark_unsaved)
        self.text_viewer.hide()
        layout.addWidget(self.text_viewer)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setScaledContents(True)
        # Style will be applied via theme_manager in apply_theme method

        self.image_scroll = QScrollArea()
        self.image_scroll.setWidgetResizable(True)
        self.image_scroll.setWidget(self.image_label)
        # Style will be applied via theme_manager in apply_theme method
        self.image_scroll.hide()
        layout.addWidget(self.image_scroll)

        self.save_button = QPushButton("💾 Save File")
        # Style will be applied via theme_manager in apply_theme method
        self.save_button.clicked.connect(self.save_current_file)
        self.save_button.hide()
        layout.addWidget(self.save_button)

        self.save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self.save_shortcut.activated.connect(self.save_current_file)
        self.save_shortcut.setEnabled(False)

        return panel

    def create_file_viewer_panel(self):
        """Create a clean editor panel without welcome message for file viewing"""
        panel = QWidget()
        # Panel styling will be applied by theme
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Text viewer (no welcome message)
        text_viewer = QTextEdit()
        # Text viewer styling will be applied by theme
        text_viewer.textChanged.connect(self.mark_unsaved)
        layout.addWidget(text_viewer)

        # Image viewer
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setScaledContents(True)
        # Style will be applied via theme_manager in apply_theme method

        image_scroll = QScrollArea()
        image_scroll.setWidgetResizable(True)
        image_scroll.setWidget(image_label)
        # Style will be applied via theme_manager in apply_theme method
        image_scroll.hide()
        layout.addWidget(image_scroll)

        # Save button
        save_button = QPushButton("💾 Save File")
        # Style will be applied via theme_manager in apply_theme method
        save_button.clicked.connect(self.save_current_file)
        save_button.hide()
        layout.addWidget(save_button)

        # Store references for later use
        panel.text_viewer = text_viewer
        panel.image_label = image_label
        panel.image_scroll = image_scroll
        panel.save_button = save_button

        return panel

    def show_welcome_message(self):
        """Show the welcome message and hide file content"""
        # Always switch to editor panel to show welcome message
        if hasattr(self, 'editor_panel'):
            self.set_right_panel(self.editor_panel)
            
            # Hide file content - only if the widgets still exist and are valid
            if hasattr(self, 'text_viewer') and self.text_viewer is not None:
                try:
                    self.text_viewer.hide()
                except RuntimeError:
                    # Widget has been deleted, ignore
                    pass
            
            if hasattr(self, 'image_scroll') and self.image_scroll is not None:
                try:
                    self.image_scroll.hide()
                except RuntimeError:
                    # Widget has been deleted, ignore
                    pass
            
            if hasattr(self, 'save_button') and self.save_button is not None:
                try:
                    self.save_button.hide()
                except RuntimeError:
                    # Widget has been deleted, ignore
                    pass
            
            if hasattr(self, 'save_shortcut') and self.save_shortcut is not None:
                try:
                    self.save_shortcut.setEnabled(False)
                except RuntimeError:
                    # Widget has been deleted, ignore
                    pass
            
            # Show welcome message (only if attributes exist)
            if hasattr(self.right_panel, 'welcome_label'):
                self.right_panel.welcome_label.show()
            
            # Clear current file
            self.current_file = None

    def build_initial_tree(self):
        self.tree.clear()
        self.repos = load_repos()

        for repo in self.repos:
            repo_name = repo["name"]
            repo_path = BASE_DIR / repo_name

            if not repo_path.exists():
                continue

            repo_item = QTreeWidgetItem([repo_name])
            repo_item.setData(0, Qt.ItemDataRole.UserRole, str(repo_path))
            repo_item.setIcon(0, self.icon_provider.icon(QFileIconProvider.IconType.Folder))
            repo_item.setForeground(0, QBrush(GITEA_GREEN))
            self.tree.addTopLevelItem(repo_item)
            self.add_dummy(repo_item, repo_path)

    def refresh_repository_tree(self):
        """Refresh the repository tree to sync with external changes"""
        try:
            # Disable the refresh button temporarily to prevent multiple clicks
            self.refresh_btn.setEnabled(False)
            self.refresh_btn.setText("⏳")
            
            # Save current expanded state
            expanded_items = []
            def save_expanded(item):
                if item.isExpanded():
                    expanded_items.append(item.data(0, Qt.ItemDataRole.UserRole))
                for i in range(item.childCount()):
                    save_expanded(item.child(i))
            
            for i in range(self.tree.topLevelItemCount()):
                save_expanded(self.tree.topLevelItem(i))
            
            
            # Clear the tree completely
            self.tree.clear()
            
            # Force Qt to process the clear
            QApplication.processEvents()
            
            # Reload repositories
            self.repos = load_repos()
            
            # Rebuild the tree
            for repo in self.repos:
                repo_name = repo["name"]
                repo_path = BASE_DIR / repo_name

                if not repo_path.exists():
                    continue

                repo_item = QTreeWidgetItem([repo_name])
                repo_item.setData(0, Qt.ItemDataRole.UserRole, str(repo_path))
                repo_item.setIcon(0, self.icon_provider.icon(QFileIconProvider.IconType.Folder))
                repo_item.setForeground(0, QBrush(GITEA_GREEN))
                self.tree.addTopLevelItem(repo_item)
                self.add_dummy(repo_item, repo_path)
            
            # Restore expanded state
            def restore_expanded(item):
                if item.data(0, Qt.ItemDataRole.UserRole) in expanded_items:
                    item.setExpanded(True)
                for i in range(item.childCount()):
                    restore_expanded(item.child(i))
            
            for i in range(self.tree.topLevelItemCount()):
                restore_expanded(self.tree.topLevelItem(i))
            
            # Update file watchers
            self.update_watchers()
            
            # Force the tree widget to update its display
            self.tree.viewport().update()
            self.tree.repaint()
            QApplication.processEvents()
            
            
        except Exception as e:
            QMessageBox.warning(self, "Refresh Error", f"Failed to refresh repository tree: {str(e)}")
        finally:
            # Re-enable the refresh button
            self.refresh_btn.setEnabled(True)
            self.refresh_btn.setText("🔄")

    def add_dummy(self, item, path: Path):
        if path.is_dir() and any(path.iterdir()):
            dummy = QTreeWidgetItem(["Loading..."])
            dummy.setIcon(0, self.icon_provider.icon(QFileIconProvider.IconType.Folder))
            dummy.setForeground(0, QBrush(GITEA_GREEN))
            item.addChild(dummy)

    def on_item_expanded(self, item):
        if item.childCount() == 1 and item.child(0).text(0) == "Loading...":
            item.removeChild(item.child(0))
            path = Path(item.data(0, Qt.ItemDataRole.UserRole))
            if path.exists() and path.is_dir():
                for child_path in sorted(path.iterdir()):
                    if child_path.name == ".git":
                        continue
                    child_item = QTreeWidgetItem([child_path.name])
                    child_item.setData(0, Qt.ItemDataRole.UserRole, str(child_path))
                    if child_path.is_dir():
                        child_item.setIcon(0, self.icon_provider.icon(QFileIconProvider.IconType.Folder))
                        self.add_dummy(child_item, child_path)
                    else:
                        child_item.setIcon(0, self.icon_provider.icon(QFileIconProvider.IconType.File))
                        child_item.setForeground(0, QBrush(GITEA_GREEN))
                    if str(child_path) in self.modified_items:
                        self.apply_highlight(child_item)
                    if str(child_path) in self.unsaved_items:
                        self.apply_unsaved(child_item)
                    item.addChild(child_item)

    # --- File interaction ---
    def on_item_clicked(self, item, column):
        path = item.data(0, Qt.ItemDataRole.UserRole)
        
        # If no path or it's a directory, show welcome message
        if not path or not Path(path).is_file():
            if self.right_panel is not self.editor_panel:
                self.set_right_panel(self.editor_panel)
            self.show_welcome_message()
            return

        # Create a clean file viewer panel (no welcome message)
        file_viewer = self.create_file_viewer_panel()
        self.set_right_panel(file_viewer)
        
        # Update references to use the new panel's widgets
        self.text_viewer = file_viewer.text_viewer
        self.image_label = file_viewer.image_label
        self.image_scroll = file_viewer.image_scroll
        self.save_button = file_viewer.save_button
        
        # Apply current theme to the new file viewer panel
        current_theme = getattr(self.parent(), 'settings', {}).get('theme', 'light') if hasattr(self, 'parent') and self.parent() else 'light'
        self.apply_theme_to_file_viewer(file_viewer, current_theme)

        if self.current_file and self.current_file in self.unsaved_items:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                f"The file '{Path(self.current_file).name}' has unsaved changes. Save now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.save_current_file()

        self.current_file = str(path)
        path_obj = Path(path)
        suffix = path_obj.suffix.lower()
        image_exts = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".svg"}
        odt_exts = {".odt"}

        if suffix in image_exts:
            if hasattr(self, 'text_viewer') and self.text_viewer is not None:
                try:
                    self.text_viewer.hide()
                except RuntimeError:
                    pass
            if hasattr(self, 'save_button') and self.save_button is not None:
                try:
                    self.save_button.hide()
                except RuntimeError:
                    pass
            if hasattr(self, 'image_scroll') and self.image_scroll is not None:
                try:
                    self.image_scroll.show()
                except RuntimeError:
                    pass
            try:
                pixmap = QPixmap(str(path_obj))
                if pixmap.isNull():
                    if hasattr(self, 'image_label') and self.image_label is not None:
                        self.image_label.setText("Failed to load image.")
                else:
                    if hasattr(self, 'image_label') and self.image_label is not None:
                        self.image_label.setPixmap(pixmap)
            except Exception as e:
                if hasattr(self, 'image_label') and self.image_label is not None:
                    self.image_label.setText(f"Error loading image:\n{e}")
        elif suffix in odt_exts:
            # Handle ODT files with rich text editor
            if hasattr(self, 'image_scroll') and self.image_scroll is not None:
                try:
                    self.image_scroll.hide()
                except RuntimeError:
                    pass
            if hasattr(self, 'text_viewer') and self.text_viewer is not None:
                try:
                    self.text_viewer.hide()
                except RuntimeError:
                    pass
            if hasattr(self, 'save_button') and self.save_button is not None:
                try:
                    self.save_button.show()  # Show save button for ODT files
                except RuntimeError:
                    pass
            
            try:
                self.loading_file = True
                # Create ODT editor
                from odt_editor import ODTEditor
                odt_editor = ODTEditor(str(path_obj))
                
                # Replace the right panel with ODT editor
                self.set_right_panel(odt_editor)
                
                # Connect content change tracking
                odt_editor.content_changed.connect(self.mark_unsaved)
                
                # Enable save shortcut
                if hasattr(self, 'save_shortcut') and self.save_shortcut is not None:
                    try:
                        self.save_shortcut.setEnabled(True)
                    except RuntimeError:
                        pass
                
                self.loading_file = False
                
            except Exception as e:
                # Fallback to simple text extraction if rich editor fails
                if hasattr(self, 'text_viewer') and self.text_viewer is not None:
                    try:
                        self.text_viewer.show()
                    except RuntimeError:
                        pass
                try:
                    odt_content = self.extract_odt_text(path_obj)
                    if hasattr(self, 'text_viewer') and self.text_viewer is not None:
                        self.text_viewer.setPlainText(f"Rich editor failed, showing text content:\n\n{odt_content}")
                except Exception as e2:
                    if hasattr(self, 'text_viewer') and self.text_viewer is not None:
                        self.text_viewer.setPlainText(f"Failed to read ODT file:\n{e}\n\nFallback error: {e2}")
                self.loading_file = False
        else:
            if hasattr(self, 'image_scroll') and self.image_scroll is not None:
                try:
                    self.image_scroll.hide()
                except RuntimeError:
                    pass
            if hasattr(self, 'text_viewer') and self.text_viewer is not None:
                try:
                    self.text_viewer.show()
                except RuntimeError:
                    pass
            if hasattr(self, 'save_button') and self.save_button is not None:
                try:
                    self.save_button.show()
                except RuntimeError:
                    pass
            try:
                self.loading_file = True
                with open(path_obj, "r", encoding="utf-8", errors="ignore") as f:
                    if hasattr(self, 'text_viewer') and self.text_viewer is not None:
                        self.text_viewer.setPlainText(f.read())
                self.loading_file = False
            except Exception as e:
                if hasattr(self, 'text_viewer') and self.text_viewer is not None:
                    self.text_viewer.setPlainText(f"Failed to read file:\n{e}")
                self.loading_file = False

        if hasattr(self, 'save_shortcut') and self.save_shortcut is not None:
            try:
                self.save_shortcut.setEnabled(True)
            except RuntimeError:
                pass

    def extract_odt_text(self, path_obj):
        """Extract text content from ODT file"""
        try:
            from odf.opendocument import load
            from odf.text import P
            
            # Load the ODT document
            doc = load(str(path_obj))
            
            # Extract text from all paragraphs
            text_content = []
            for paragraph in doc.getElementsByType(P):
                # Get text content from the paragraph
                para_text = ""
                for node in paragraph.childNodes:
                    if hasattr(node, 'data'):
                        para_text += node.data
                    elif hasattr(node, 'childNodes'):
                        for child in node.childNodes:
                            if hasattr(child, 'data'):
                                para_text += child.data
                if para_text.strip():
                    text_content.append(para_text.strip())
            
            # Join all paragraphs with newlines
            full_text = "\n\n".join(text_content)
            
            if not full_text.strip():
                return "No text content found in this ODT file."
            
            return full_text
            
        except ImportError:
            return "Error: ODT support library not available. Please install odfpy."
        except Exception as e:
            return f"Error reading ODT file: {str(e)}"
    

    def mark_unsaved(self):
        if self.loading_file or not self.current_file:
            return
        # Check if text_viewer still exists and is valid
        if not hasattr(self, 'text_viewer') or self.text_viewer is None:
            return
        if self.current_file not in self.unsaved_items:
            self.unsaved_items[self.current_file] = True
            self.update_tree_item_color(self.current_file, GITEA_UNSAVED)

    def save_current_file(self):
        if not self.current_file:
            return
        suffix = Path(self.current_file).suffix.lower()
        image_exts = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".svg"}
        odt_exts = {".odt"}
        
        if suffix in image_exts:
            return
        
        # Handle ODT files
        if suffix in odt_exts:
            # Check if we have an ODT editor in the right panel
            if hasattr(self, 'right_panel') and self.right_panel is not None:
                try:
                    # Check if the right panel is an ODT editor
                    if hasattr(self.right_panel, 'save_odt_file'):
                        if self.right_panel.save_odt_file(self.current_file):
                            # Mark as saved
                            if self.current_file in self.unsaved_items:
                                del self.unsaved_items[self.current_file]
                            self.update_tree_item_color(self.current_file, GITEA_GREEN)
                            QMessageBox.information(self, "Success", "ODT file saved successfully!")
                        else:
                            QMessageBox.warning(self, "Error", "Failed to save ODT file.")
                    else:
                        QMessageBox.warning(self, "Save Error", "ODT editor is not available.")
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Error saving ODT file: {str(e)}")
            else:
                QMessageBox.warning(self, "Save Error", "No editor is currently open.")
            return

        # Handle regular text files
        # Check if text_viewer still exists and is valid
        if not hasattr(self, 'text_viewer') or self.text_viewer is None:
            QMessageBox.warning(self, "Save Error", "Text viewer is not available.")
            return

        try:
            with open(self.current_file, "w", encoding="utf-8") as f:
                f.write(self.text_viewer.toPlainText())
            if self.current_file in self.unsaved_items:
                del self.unsaved_items[self.current_file]
            self.update_tree_item_color(self.current_file, GITEA_GREEN)
            QMessageBox.information(self, "Success", "File saved successfully!")
        except RuntimeError:
            QMessageBox.warning(self, "Save Error", "Text viewer has been deleted. Please reopen the file.")
        except Exception as e:
            QMessageBox.warning(self, "Save Error", f"Failed to save file:\n{e}")

    # --- Helpers ---
    def update_tree_item_color(self, path_str, color):
        def recurse_items(parent):
            for i in range(parent.childCount()):
                child = parent.child(i)
                if child.data(0, Qt.ItemDataRole.UserRole) == path_str:
                    child.setForeground(0, QBrush(color))
                    return True
                if recurse_items(child):
                    return True
            return False

        for i in range(self.tree.topLevelItemCount()):
            top_item = self.tree.topLevelItem(i)
            if top_item.data(0, Qt.ItemDataRole.UserRole) == path_str:
                top_item.setForeground(0, QBrush(color))
                return
            recurse_items(top_item)

    def apply_highlight(self, item):
        item.setForeground(0, QBrush(GITEA_GREEN))
        font = item.font(0)
        font.setBold(True)
        item.setFont(0, font)

    def apply_unsaved(self, item):
        item.setForeground(0, QBrush(GITEA_UNSAVED))
        font = item.font(0)
        font.setBold(True)
        item.setFont(0, font)

    # --- Filesystem watcher ---
    def start_watching(self):
        self.update_watchers()

    def update_watchers(self):
        # Stop old observer if running
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()

        self.observer = Observer()
        self.repos = load_repos()  # Reload repos
        for repo in self.repos:
            repo_path = BASE_DIR / repo["name"]
            if repo_path.exists():
                handler = RepoChangeHandler(self)
                self.observer.schedule(handler, str(repo_path), recursive=True)
        self.observer.start()

    def mark_modified(self, path):
        self.modified_items[str(path)] = True

    def show_context_menu(self, position):
        """Show context menu for tree items"""
        item = self.tree.itemAt(position)
        if not item:
            return
        
        menu = QMenu(self)
        # Style will be applied via theme_manager
        from theme_manager import ThemeManager
        current_theme = getattr(self.parent(), 'settings', {}).get('theme', 'light') if hasattr(self, 'parent') and self.parent() else 'light'
        menu.setStyleSheet(ThemeManager.get_context_menu_style(current_theme))
        
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if not path:
            return
        
        path_obj = Path(path)
        
        if path_obj.is_file():
            # File context menu
            self.create_file_context_menu(menu, path_obj, item)
        elif path_obj.is_dir() and path_obj.parent.name == "Gitea Repos":
            # Repository context menu (top-level directories)
            self.create_repo_context_menu(menu, path_obj, item)
        else:
            # Folder context menu (subdirectories)
            self.create_folder_context_menu(menu, path_obj, item)
        
        menu.exec(self.tree.mapToGlobal(position))
    
    def create_repo_context_menu(self, menu, repo_path, item):
        """Create context menu for repository"""
        # Show Commit Info
        commit_info_action = menu.addAction("ℹ️ Show Commit Info")
        commit_info_action.triggered.connect(lambda: self.show_commit_info(repo_path))
        
        menu.addSeparator()
        
        # Git Logs
        logs_action = menu.addAction("📋 View Git Logs")
        logs_action.triggered.connect(lambda: self.show_git_logs(repo_path, is_repo=True))
        
        menu.addSeparator()
        
        # Reverse operations
        safe_revert_action = menu.addAction("✅ Safe Revert (Keep History)")
        safe_revert_action.triggered.connect(lambda: self.safe_revert_repo(repo_path))
        
        destructive_revert_action = menu.addAction("⚠️ Destructive Revert (Delete History)")
        destructive_revert_action.triggered.connect(lambda: self.destructive_revert_repo(repo_path))
        
        menu.addSeparator()
        
        # Git operations
        add_action = menu.addAction("➕ Add Changes")
        add_action.triggered.connect(lambda: self.add_repo_changes(repo_path))
        
        commit_action = menu.addAction("💾 Commit Changes")
        commit_action.triggered.connect(lambda: self.commit_repo_changes(repo_path))
        
        push_action = menu.addAction("🚀 Push to Server")
        push_action.triggered.connect(lambda: self.push_repo_changes(repo_path))
        
        pull_action = menu.addAction("⬇️ Pull from Server")
        pull_action.triggered.connect(lambda: self.pull_repo_changes(repo_path))
        
        # Add submenu for creating files/folders
        add_menu = menu.addMenu("➕ Add")
        add_folder_action = add_menu.addAction("📁 New Folder")
        add_folder_action.triggered.connect(lambda: self.add_new_folder(repo_path))
        add_file_action = add_menu.addAction("📄 New File")
        add_file_action.triggered.connect(lambda: self.add_new_file(repo_path))
    
    def create_file_context_menu(self, menu, file_path, item):
        """Create context menu for file"""
        # Git Logs
        logs_action = menu.addAction("📋 View File Logs")
        logs_action.triggered.connect(lambda: self.show_git_logs(file_path, is_repo=False))
        
        menu.addSeparator()
        
        # Reverse operations
        safe_revert_action = menu.addAction("✅ Safe Revert File (Keep History)")
        safe_revert_action.triggered.connect(lambda: self.safe_revert_file(file_path))
        
        destructive_revert_action = menu.addAction("⚠️ Destructive Revert File (Delete History)")
        destructive_revert_action.triggered.connect(lambda: self.destructive_revert_file(file_path))
        
        menu.addSeparator()
        
        # Remove file option
        remove_file_action = menu.addAction("🗑️ Remove File")
        remove_file_action.triggered.connect(lambda: self.remove_file(file_path))
    
    def create_folder_context_menu(self, menu, folder_path, item):
        """Create context menu for folder"""
        # Add submenu for creating files/folders
        add_menu = menu.addMenu("➕ Add")
        add_folder_action = add_menu.addAction("📁 New Folder")
        add_folder_action.triggered.connect(lambda: self.add_new_folder(folder_path))
        add_file_action = add_menu.addAction("📄 New File")
        add_file_action.triggered.connect(lambda: self.add_new_file(folder_path))
        
        menu.addSeparator()
        
        # Remove folder option
        remove_folder_action = menu.addAction("🗑️ Remove Folder")
        remove_folder_action.triggered.connect(lambda: self.remove_folder(folder_path))
    
    def show_git_logs(self, path, is_repo=True):
        """Show Git logs for repository or file"""
        try:
            from git_logs_viewer import GitLogsViewer
            import git
            
            if is_repo:
                # For repository, use the path directly
                repo_path = str(path)
                file_path = None
            else:
                # For file, find the repository root using GitPython
                try:
                    # Use GitPython to find the repository root
                    repo = git.Repo(str(path), search_parent_directories=True)
                    repo_path = repo.working_tree_dir
                    file_path = str(path)
                except git.InvalidGitRepositoryError:
                    QMessageBox.warning(self, "Error", "File is not in a valid Git repository")
                    return
            
            logs_panel = GitLogsViewer(repo_path, file_path)
            # Apply current theme - get theme from parent application
            current_theme = getattr(self.parent(), 'settings', {}).get('theme', 'light') if hasattr(self, 'parent') and self.parent() else 'light'
            logs_panel.apply_theme(current_theme)
            self.set_right_panel(logs_panel)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load Git logs: {str(e)}")
    
    def safe_revert_repo(self, repo_path):
        """Safe revert repository to previous commit (keep history visible)"""
        try:
            import git
            repo = git.Repo(repo_path)
            
            # Check for unmerged files first
            if not self.check_context_unmerged_files(repo):
                return
            
            # Get the previous commit
            try:
                prev_commit = repo.head.commit.parents[0]
                prev_hash = prev_commit.hexsha[:8]
                prev_message = prev_commit.message.strip()
                prev_author = prev_commit.author.name
                prev_date = prev_commit.committed_datetime.strftime('%Y-%m-%d %H:%M:%S')
            except IndexError:
                QMessageBox.warning(self, "Error", "No previous commit to revert to")
                return
            
            reply = QMessageBox.question(
                self, "Safe Revert (Keep History)",
                f"Are you sure you want to safely revert '{Path(repo_path).name}' to the previous commit?\n\n"
                f"Previous commit: {prev_hash}\n"
                f"Message: {prev_message}\n"
                f"Author: {prev_author}\n"
                f"Date: {prev_date}\n\n"
                f"✅ SAFE REVERT:\n"
                f"• Switches to previous commit without moving branch pointer\n"
                f"• All commits remain VISIBLE in logs\n"
                f"• You can navigate forward/backward between commits\n"
                f"• Current changes are preserved in working directory\n"
                f"• You can easily switch back to any commit later",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    # Checkout the previous commit (detached HEAD state)
                    repo.git.checkout(prev_commit.hexsha)
                    QMessageBox.information(self, "Success", f"Repository safely reverted to commit {prev_hash} - all commits remain visible in logs")
                except Exception as revert_error:
                    QMessageBox.warning(self, "Error", f"Failed to safely revert repository: {str(revert_error)}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to safely revert repository: {str(e)}")
    
    def destructive_revert_repo(self, repo_path):
        """Destructive revert repository to previous commit (delete history)"""
        try:
            import git
            repo = git.Repo(repo_path)
            
            # Check for unmerged files first
            if not self.check_context_unmerged_files(repo):
                return
            
            # Get the last commit
            last_commit = repo.head.commit
            
            reply = QMessageBox.question(
                self, "Destructive Revert (Delete History)",
                f"⚠️ DANGER: This will PERMANENTLY DELETE the current commit in '{Path(repo_path).name}'!\n\n"
                f"Current commit: {last_commit.hexsha[:8]}\n"
                f"Message: {last_commit.message.strip()}\n"
                f"Author: {last_commit.author.name}\n"
                f"Date: {last_commit.committed_datetime.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"🚨 DESTRUCTIVE REVERT:\n"
                f"• Current commit will be LOST FOREVER\n"
                f"• This action CANNOT be undone\n"
                f"• Use 'Safe Revert' if you want to preserve it\n\n"
                f"Are you absolutely sure you want to do this?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    # Reset to previous commit (hard reset)
                    repo.git.reset('--hard', 'HEAD~1')
                    QMessageBox.information(self, "Success", f"Repository destructively reverted to previous commit - current commit permanently deleted")
                except Exception as reset_error:
                    QMessageBox.warning(self, "Error", f"Failed to destructively revert repository: {str(reset_error)}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to destructively revert repository: {str(e)}")
    
    def check_context_unmerged_files(self, repo):
        """Check for unmerged files in context menu operations"""
        try:
            # Check git status for unmerged files
            status = repo.git.status('--porcelain')
            unmerged_files = []
            
            for line in status.split('\n'):
                if line and (line.startswith('UU ') or line.startswith('AA ') or line.startswith('DD ')):
                    unmerged_files.append(line[3:])  # Remove status prefix
            
            if unmerged_files:
                self.handle_context_unmerged_files_error(repo, unmerged_files)
                return False
            
            return True
        except Exception as e:
            # If we can't check status, proceed anyway
            return True
    
    def handle_context_unmerged_files_error(self, repo, unmerged_files=None):
        """Handle unmerged files error for context menu"""
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
            self.guide_context_conflict_resolution(unmerged_files)
        elif msg.clickedButton() == abort_btn:
            self.abort_context_previous_operation(repo)
        elif msg.clickedButton() == reset_btn:
            self.reset_context_repository_state(repo)
    
    def guide_context_conflict_resolution(self, unmerged_files):
        """Guide user to resolve conflicts manually for context menu"""
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
    
    def abort_context_previous_operation(self, repo):
        """Abort any ongoing Git operation for context menu"""
        try:
            # Try to abort revert first
            try:
                repo.git.revert('--abort')
                QMessageBox.information(self, "Success", "Previous revert operation aborted successfully")
                return
            except:
                pass
            
            # Try to abort merge
            try:
                repo.git.merge('--abort')
                QMessageBox.information(self, "Success", "Previous merge operation aborted successfully")
                return
            except:
                pass
            
            # Try to abort cherry-pick
            try:
                repo.git.cherry_pick('--abort')
                QMessageBox.information(self, "Success", "Previous cherry-pick operation aborted successfully")
                return
            except:
                pass
            
            QMessageBox.warning(self, "No Operation", "No ongoing operation found to abort")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error aborting previous operation: {str(e)}")
    
    def reset_context_repository_state(self, repo):
        """Reset repository to a clean state for context menu"""
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
                repo.git.reset('--hard', 'HEAD')
                QMessageBox.information(self, "Success", "Repository reset to clean state - all conflicts resolved")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Error resetting repository: {str(e)}")
    
    def handle_context_revert_conflict(self, repo, commit, error_msg):
        """Handle merge conflicts during context menu revert operations"""
        # Show conflict resolution dialog
        msg = QMessageBox(self)
        msg.setWindowTitle("Merge Conflict Detected")
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText(f"Merge conflict occurred while reverting commit '{commit.hexsha[:8]}'")
        msg.setDetailedText(f"Error: {error_msg}\n\nYou have several options:")
        
        # Add custom buttons
        resolve_btn = msg.addButton("🔧 Resolve Conflicts", QMessageBox.ButtonRole.ActionRole)
        skip_btn = msg.addButton("⏭️ Skip Revert", QMessageBox.ButtonRole.ActionRole)
        abort_btn = msg.addButton("❌ Abort Revert", QMessageBox.ButtonRole.ActionRole)
        msg.addButton(QMessageBox.StandardButton.Cancel)
        
        msg.exec()
        
        if msg.clickedButton() == resolve_btn:
            self.resolve_context_revert_conflicts(repo)
        elif msg.clickedButton() == skip_btn:
            self.skip_context_revert(repo)
        elif msg.clickedButton() == abort_btn:
            self.abort_context_revert(repo)
    
    def resolve_context_revert_conflicts(self, repo):
        """Guide user to resolve conflicts manually for context menu"""
        QMessageBox.information(
            self, "Resolve Conflicts",
            "Please resolve the merge conflicts manually:\n\n"
            "1. Open the conflicted files in your editor\n"
            "2. Look for conflict markers (<<<<<<< ======= >>>>>>>)\n"
            "3. Edit the files to resolve conflicts\n"
            "4. Save the files\n"
            "5. Use Git commands to continue:\n"
            "   - git add <resolved-files>\n"
            "   - git revert --continue\n\n"
            "Or use the Git logs viewer for easier conflict resolution."
        )
    
    def skip_context_revert(self, repo):
        """Skip the current revert for context menu"""
        try:
            repo.git.revert('--skip')
            QMessageBox.information(self, "Success", "Revert skipped successfully")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error skipping revert: {str(e)}")
    
    def abort_context_revert(self, repo):
        """Abort the revert operation for context menu"""
        try:
            repo.git.revert('--abort')
            QMessageBox.information(self, "Success", "Revert aborted - repository restored to previous state")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error aborting revert: {str(e)}")
    
    def reverse_repo_destructive(self, repo_path):
        """Reverse repository destructively (wiping history) - resets to previous commit"""
        try:
            import git
            repo = git.Repo(repo_path)
            # Get the last commit
            last_commit = repo.head.commit
            
            reply = QMessageBox.question(
                self, "Reverse Repository Destructive",
                f"⚠️ WARNING: This will permanently delete the last commit in '{Path(repo_path).name}'!\n\n"
                f"Last commit: {last_commit.hexsha[:8]}\n"
                f"Message: {last_commit.message.strip()}\n"
                f"Author: {last_commit.author.name}\n"
                f"Date: {last_commit.committed_datetime.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"Are you absolutely sure you want to do this? This action cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Reset to previous commit
                repo.git.reset('--hard', 'HEAD~1')
                QMessageBox.information(self, "Success", f"Repository reset destructively - removed commit {last_commit.hexsha[:8]}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to reverse repository: {str(e)}")
    
    def safe_revert_file(self, file_path):
        """Safe revert file to previous commit (keep history)"""
        try:
            import git
            repo = git.Repo(file_path.parent)
            # Get the last commit
            last_commit = repo.head.commit
            
            reply = QMessageBox.question(
                self, "Safe Revert File (Keep History)",
                f"Are you sure you want to safely revert the file '{Path(file_path).name}' to the previous commit?\n\n"
                f"Last commit: {last_commit.hexsha[:8]}\n"
                f"Message: {last_commit.message.strip()}\n"
                f"Author: {last_commit.author.name}\n"
                f"Date: {last_commit.committed_datetime.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"✅ SAFE REVERT:\n"
                f"• File will be reverted to previous commit\n"
                f"• All history will be preserved\n"
                f"• You can continue working from this point",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Checkout the file from the previous commit
                repo.git.checkout('HEAD~1', '--', str(file_path))
                QMessageBox.information(self, "Success", f"File '{Path(file_path).name}' safely reverted to previous commit - history preserved")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to safely revert file: {str(e)}")
    
    def destructive_revert_file(self, file_path):
        """Destructive revert file to previous commit (delete history)"""
        try:
            import git
            repo = git.Repo(file_path.parent)
            # Get the last commit
            last_commit = repo.head.commit
            
            reply = QMessageBox.question(
                self, "Destructive Revert File (Delete History)",
                f"⚠️ DANGER: This will permanently revert '{Path(file_path).name}' to the previous commit!\n\n"
                f"Last commit: {last_commit.hexsha[:8]}\n"
                f"Message: {last_commit.message.strip()}\n"
                f"Author: {last_commit.author.name}\n"
                f"Date: {last_commit.committed_datetime.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"🚨 DESTRUCTIVE REVERT:\n"
                f"• This action CANNOT be undone!\n"
                f"• Use 'Safe Revert File' if you want to preserve history\n\n"
                f"Are you absolutely sure you want to do this?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Reset the file to previous commit
                repo.git.checkout('HEAD~1', '--', str(file_path))
                QMessageBox.information(self, "Success", f"File '{Path(file_path).name}' destructively reverted to previous commit - history deleted")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to destructively revert file: {str(e)}")
    
    def refresh_git_status(self, repo):
        """Force refresh of Git status to detect external changes"""
        try:
            # Update the index to reflect any external changes
            repo.git.update_index('--refresh')
            # Also run git status to ensure the working directory is up to date
            repo.git.status()
        except:
            pass  # Ignore errors if refresh fails
    
    def add_repo_changes(self, repo_path):
        """Add all changes to staging area"""
        try:
            import git
            repo = git.Repo(repo_path)
            
            # Force refresh of Git status to detect external changes
            self.refresh_git_status(repo)
            
            # Check if there are any changes to add
            status = repo.git.status('--porcelain')
            if not status.strip():
                QMessageBox.information(self, "No Changes", "No changes found to add to staging area.")
                return
            
            # Show what will be added
            untracked_files = []
            modified_files = []
            deleted_files = []
            
            for line in status.split('\n'):
                if line.strip():
                    status_code = line[:2]
                    filename = line[3:]
                    
                    if status_code.startswith('??'):
                        untracked_files.append(filename)
                    elif status_code.startswith(' M') or status_code.startswith('M '):
                        modified_files.append(filename)
                    elif status_code.startswith(' D') or status_code.startswith('D '):
                        deleted_files.append(filename)
            
            # Create summary message
            summary_parts = []
            if untracked_files:
                summary_parts.append(f"New files: {len(untracked_files)}")
            if modified_files:
                summary_parts.append(f"Modified files: {len(modified_files)}")
            if deleted_files:
                summary_parts.append(f"Deleted files: {len(deleted_files)}")
            
            summary = ", ".join(summary_parts)
            
            reply = QMessageBox.question(
                self, "Add Changes to Staging",
                f"Are you sure you want to add all changes to the staging area?\n\n"
                f"Changes to be added:\n{summary}\n\n"
                f"This will stage all changes for the next commit.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Add all changes
                repo.git.add('.')
                QMessageBox.information(self, "Success", f"All changes have been added to staging area.\n\n{summary}")
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to add changes: {str(e)}")
    
    def commit_repo_changes(self, repo_path):
        """Commit all staged changes in repository"""
        try:
            import git
            repo = git.Repo(repo_path)
            
            # Force refresh of Git status to detect external changes
            self.refresh_git_status(repo)
            
            # Check if there are any staged changes
            staged_files = repo.git.diff('--cached', '--name-only')
            if not staged_files.strip():
                # Check if there are any unstaged changes
                unstaged_files = repo.git.diff('--name-only')
                if unstaged_files.strip():
                    reply = QMessageBox.question(
                        self, "No Staged Changes",
                        "No changes are staged for commit.\n\n"
                        "Would you like to:\n"
                        "• Stage all changes and commit (Yes)\n"
                        "• Cancel and stage changes manually first (No)",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        repo.git.add('.')
                        staged_files = repo.git.diff('--cached', '--name-only')
                    else:
                        QMessageBox.information(self, "Cancelled", "Please stage changes first using 'Add Changes' option.")
                        return
                else:
                    QMessageBox.information(self, "No Changes", "No changes found to commit.\n\nUse 'Add Changes' to stage changes first.")
                    return
            
            # Show what will be committed
            staged_list = staged_files.strip().split('\n') if staged_files.strip() else []
            files_summary = f"{len(staged_list)} file(s) staged for commit"
            if len(staged_list) <= 5:
                files_summary += f":\n• " + "\n• ".join(staged_list)
            else:
                files_summary += f":\n• " + "\n• ".join(staged_list[:5]) + f"\n• ... and {len(staged_list) - 5} more files"
            
            # Get commit message from user
            from PyQt6.QtWidgets import QInputDialog
            message, ok = QInputDialog.getText(
                self, "Commit Message", 
                f"Enter commit message:\n\n{files_summary}"
            )
            
            if ok and message.strip():
                # Commit changes
                repo.git.commit('-m', message.strip())
                QMessageBox.information(self, "Success", f"Changes committed successfully!\n\nMessage: '{message.strip()}'\n\n{files_summary}")
            else:
                QMessageBox.warning(self, "No Message", "Commit message is required.")
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to commit changes: {str(e)}")
    
    def push_repo_changes(self, repo_path):
        """Push changes to remote repository"""
        try:
            import git
            repo = git.Repo(repo_path)
            
            # Check if there are any commits to push
            try:
                # Check if we're in detached HEAD state
                try:
                    current_branch = repo.active_branch.name
                    is_detached = False
                except TypeError:
                    # We're in detached HEAD state
                    is_detached = True
                    current_branch = None
                
                if is_detached:
                    # Handle detached HEAD state
                    self.handle_detached_head_push(repo, repo_path)
                    return
                
                # Check if there are commits ahead of origin
                ahead = repo.iter_commits(f'origin/{current_branch}..{current_branch}')
                commits_ahead = list(ahead)
                
                if not commits_ahead:
                    QMessageBox.information(self, "No Changes", "No changes to push to the server")
                    return
                
                # Push changes
                repo.git.push('origin', current_branch)
                QMessageBox.information(self, "Success", f"Pushed {len(commits_ahead)} commits to server")
                
            except Exception as e:
                error_msg = str(e)
                if "no upstream branch" in error_msg.lower():
                    QMessageBox.information(self, "No Remote", "No remote repository configured for this branch")
                elif "non-fast-forward" in error_msg or "rejected" in error_msg:
                    # Handle the case where local history has been rewritten
                    self.handle_non_fast_forward_push(repo, repo_path, current_branch, error_msg)
                else:
                    raise e
                    
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to push changes: {str(e)}")
    
    def handle_non_fast_forward_push(self, repo, repo_path, current_branch, error_msg):
        """Handle non-fast-forward push errors when local history has been rewritten"""
        try:
            # Get information about the divergent branches
            local_commits = list(repo.iter_commits(f'origin/{current_branch}..{current_branch}'))
            remote_commits = list(repo.iter_commits(f'{current_branch}..origin/{current_branch}'))
            
            local_count = len(local_commits)
            remote_count = len(remote_commits)
            
            # Create detailed message
            message = f"Push rejected - Local history has been rewritten!\n\n"
            message += f"Your local branch has {local_count} commit(s) that aren't on the server\n"
            message += f"The server has {remote_count} commit(s) that aren't in your local branch\n\n"
            message += f"This usually happens when you:\n"
            message += f"• Reverted to a previous commit\n"
            message += f"• Reset your branch to an earlier state\n"
            message += f"• Rewrote commit history\n\n"
            message += f"Choose how to handle this:"
            
            # Create custom dialog with multiple options
            msg = QMessageBox(self)
            msg.setWindowTitle("Non-Fast-Forward Push - Choose Resolution")
            msg.setIcon(QMessageBox.Icon.Question)
            msg.setText(message)
            
            # Add custom buttons for different strategies
            force_push_btn = msg.addButton("⚠️ Force Push (Overwrite Server)", QMessageBox.ButtonRole.ActionRole)
            pull_merge_btn = msg.addButton("🔄 Pull & Merge (Keep Both)", QMessageBox.ButtonRole.ActionRole)
            pull_rebase_btn = msg.addButton("📝 Pull & Rebase (Clean History)", QMessageBox.ButtonRole.ActionRole)
            cancel_btn = msg.addButton("❌ Cancel", QMessageBox.ButtonRole.RejectRole)
            
            msg.exec()
            
            if msg.clickedButton() == force_push_btn:
                self.force_push_changes(repo, repo_path, current_branch)
            elif msg.clickedButton() == pull_merge_btn:
                self.pull_and_merge_push(repo, repo_path, current_branch)
            elif msg.clickedButton() == pull_rebase_btn:
                self.pull_and_rebase_push(repo, repo_path, current_branch)
            # Cancel does nothing
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to handle non-fast-forward push: {str(e)}")
    
    def force_push_changes(self, repo, repo_path, current_branch):
        """Force push changes, overwriting server history"""
        try:
            # Show strong warning
            reply = QMessageBox.question(
                self, "Force Push Warning",
                f"⚠️ DANGER: Force Push will OVERWRITE the server history!\n\n"
                f"This will:\n"
                f"• Delete {len(list(repo.iter_commits(f'{current_branch}..origin/{current_branch}')))} commit(s) from the server\n"
                f"• Replace server history with your local history\n"
                f"• This action CANNOT be undone\n\n"
                f"Only use this if you're sure the server commits should be discarded!\n\n"
                f"Are you absolutely sure you want to force push?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Force push with lease for safety
                repo.git.push('origin', current_branch, '--force-with-lease')
                QMessageBox.information(self, "Success", "Force push completed - server history has been overwritten")
            else:
                QMessageBox.information(self, "Cancelled", "Force push cancelled")
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to force push: {str(e)}")
    
    def pull_and_merge_push(self, repo, repo_path, current_branch):
        """Pull changes and merge, then push"""
        try:
            # First pull with merge strategy
            repo.git.pull('origin', current_branch, '--no-rebase')
            
            # Then push
            repo.git.push('origin', current_branch)
            QMessageBox.information(self, "Success", "Pulled, merged, and pushed successfully")
            
        except Exception as e:
            error_msg = str(e)
            if "merge conflict" in error_msg.lower():
                QMessageBox.warning(self, "Merge Conflict", 
                    f"Merge conflict occurred during pull:\n{error_msg}\n\n"
                    f"Please resolve conflicts manually and try again.")
            else:
                QMessageBox.warning(self, "Error", f"Failed to pull and merge: {str(e)}")
    
    def pull_and_rebase_push(self, repo, repo_path, current_branch):
        """Pull changes and rebase, then push"""
        try:
            # First pull with rebase strategy
            repo.git.pull('origin', current_branch, '--rebase')
            
            # Then push
            repo.git.push('origin', current_branch)
            QMessageBox.information(self, "Success", "Pulled, rebased, and pushed successfully")
            
        except Exception as e:
            error_msg = str(e)
            if "rebase conflict" in error_msg.lower() or "conflict" in error_msg.lower():
                QMessageBox.warning(self, "Rebase Conflict", 
                    f"Rebase conflict occurred during pull:\n{error_msg}\n\n"
                    f"Please resolve conflicts manually and try again.")
            else:
                QMessageBox.warning(self, "Error", f"Failed to pull and rebase: {str(e)}")
    
    def handle_detached_head_push(self, repo, repo_path):
        """Handle push when in detached HEAD state"""
        try:
            # Get current commit hash
            current_commit = repo.head.commit.hexsha[:8]
            
            # Get the default branch (usually main or master)
            try:
                # Try to get the default branch from remote
                remote_refs = repo.remote('origin').refs
                default_branch = None
                for ref in remote_refs:
                    if ref.name == 'origin/main':
                        default_branch = 'main'
                        break
                    elif ref.name == 'origin/master':
                        default_branch = 'master'
                        break
                
                if not default_branch:
                    # Fallback to checking local branches
                    local_branches = [branch.name for branch in repo.branches]
                    if 'main' in local_branches:
                        default_branch = 'main'
                    elif 'master' in local_branches:
                        default_branch = 'master'
                    else:
                        default_branch = local_branches[0] if local_branches else 'main'
                        
            except:
                default_branch = 'main'
            
            # Create detailed message
            message = f"⚠️ Detached HEAD State Detected!\n\n"
            message += f"You're currently on commit {current_commit} (detached HEAD)\n"
            message += f"This usually happens after:\n"
            message += f"• Checking out a specific commit\n"
            message += f"• Reverting to a previous commit\n"
            message += f"• Other Git operations that move HEAD\n\n"
            message += f"To push your changes, you need to be on a branch.\n\n"
            message += f"Options:\n\n"
            message += f"1. 🔄 Create new branch from current commit\n"
            message += f"2. 📍 Switch back to {default_branch} branch\n"
            message += f"3. 🏷️ Create and switch to new branch\n"
            message += f"4. ❌ Cancel and handle manually"
            
            # Create custom dialog with options
            dialog = QMessageBox(self)
            dialog.setWindowTitle("Detached HEAD State")
            dialog.setText(message)
            dialog.setIcon(QMessageBox.Icon.Warning)
            
            # Add custom buttons
            new_branch_btn = dialog.addButton("Create New Branch", QMessageBox.ButtonRole.ActionRole)
            switch_btn = dialog.addButton(f"Switch to {default_branch}", QMessageBox.ButtonRole.ActionRole)
            create_switch_btn = dialog.addButton("Create & Switch Branch", QMessageBox.ButtonRole.ActionRole)
            cancel_btn = dialog.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
            
            dialog.exec()
            clicked_button = dialog.clickedButton()
            
            if clicked_button == new_branch_btn:
                self.create_branch_from_detached_head(repo, repo_path, current_commit)
            elif clicked_button == switch_btn:
                self.switch_to_default_branch(repo, repo_path, default_branch)
            elif clicked_button == create_switch_btn:
                self.create_and_switch_branch(repo, repo_path, current_commit)
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to handle detached HEAD state: {str(e)}")
    
    def create_branch_from_detached_head(self, repo, repo_path, current_commit):
        """Create a new branch from the current detached HEAD commit"""
        try:
            # Get branch name from user
            branch_name, ok = QInputDialog.getText(
                self, "Create New Branch", 
                f"Enter name for new branch (from commit {current_commit}):",
                text="feature-branch"
            )
            
            if ok and branch_name.strip():
                branch_name = branch_name.strip()
                
                # Create new branch from current commit
                new_branch = repo.create_head(branch_name)
                new_branch.checkout()
                
                # Set upstream and push
                repo.git.push('origin', branch_name, '--set-upstream')
                
                QMessageBox.information(self, "Success", 
                    f"Created branch '{branch_name}' and pushed to server!")
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to create branch: {str(e)}")
    
    def switch_to_default_branch(self, repo, repo_path, default_branch):
        """Switch back to the default branch"""
        try:
            # Check if there are uncommitted changes
            if repo.is_dirty(untracked_files=True):
                reply = QMessageBox.question(
                    self, "Uncommitted Changes",
                    f"You have uncommitted changes. What would you like to do?\n\n"
                    f"1. Stash changes and switch to {default_branch}\n"
                    f"2. Commit changes to current commit\n"
                    f"3. Discard changes and switch",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # Stash changes
                    repo.git.stash('push', '-m', f'Stashed before switching to {default_branch}')
                    repo.git.checkout(default_branch)
                    QMessageBox.information(self, "Success", 
                        f"Stashed changes and switched to {default_branch}")
                elif reply == QMessageBox.StandardButton.No:
                    # Commit changes to current commit
                    repo.git.add('.')
                    repo.git.commit('-m', 'Commit from detached HEAD')
                    # Create temporary branch and push
                    temp_branch = f"temp-{repo.head.commit.hexsha[:8]}"
                    repo.create_head(temp_branch)
                    repo.git.push('origin', temp_branch)
                    QMessageBox.information(self, "Success", 
                        f"Committed changes to temporary branch '{temp_branch}'")
                else:
                    return
            else:
                # No uncommitted changes, just switch
                repo.git.checkout(default_branch)
                QMessageBox.information(self, "Success", f"Switched to {default_branch}")
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to switch to {default_branch}: {str(e)}")
    
    def create_and_switch_branch(self, repo, repo_path, current_commit):
        """Create a new branch and switch to it"""
        try:
            # Get branch name from user
            branch_name, ok = QInputDialog.getText(
                self, "Create and Switch Branch", 
                f"Enter name for new branch (from commit {current_commit}):",
                text="feature-branch"
            )
            
            if ok and branch_name.strip():
                branch_name = branch_name.strip()
                
                # Create new branch from current commit and switch to it
                new_branch = repo.create_head(branch_name)
                new_branch.checkout()
                
                QMessageBox.information(self, "Success", 
                    f"Created and switched to branch '{branch_name}'\n\n"
                    f"You can now commit and push your changes!")
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to create and switch branch: {str(e)}")
    
    def pull_repo_changes(self, repo_path):
        """Pull changes from remote repository with conflict resolution"""
        try:
            import git
            repo = git.Repo(repo_path)
            
            # Force refresh of Git status to detect external changes
            self.refresh_git_status(repo)
            
            # Check if there are any uncommitted changes
            uncommitted_changes = repo.is_dirty(untracked_files=True)
            if uncommitted_changes:
                reply = QMessageBox.question(
                    self, "Uncommitted Changes",
                    "You have uncommitted changes. Would you like to stash them before pulling?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    repo.git.stash()
                    stashed = True
                else:
                    return
            else:
                stashed = False
            
            try:
                # Get the current branch
                current_branch = repo.active_branch.name
                # Fetch latest changes
                repo.git.fetch('origin')
                
                # Check if there are commits behind origin
                behind = repo.iter_commits(f'{current_branch}..origin/{current_branch}')
                commits_behind = list(behind)
                
                if not commits_behind:
                    QMessageBox.information(self, "No Changes", "No changes to pull from the server")
                    return
                
                # Try to pull changes
                repo.git.pull('origin', current_branch)
                
                # Restore stashed changes if any
                if stashed:
                    try:
                        repo.git.stash('pop')
                        QMessageBox.information(self, "Success", f"Pulled {len(commits_behind)} commits from server and stashed changes restored")
                    except:
                        QMessageBox.information(self, "Success", f"Pulled {len(commits_behind)} commits from server. Stashed changes had conflicts and remain in stash")
                else:
                    QMessageBox.information(self, "Success", f"Pulled {len(commits_behind)} commits from server")
                    
            except Exception as pull_error:
                error_msg = str(pull_error)
                
                # Check if it's a divergent branches error
                if "divergent branches" in error_msg or "Need to specify how to reconcile" in error_msg:
                    self.handle_divergent_branches(repo, repo_path, stashed)
                elif "no upstream branch" in error_msg.lower():
                    QMessageBox.information(self, "No Remote", "No remote repository configured for this branch")
                else:
                    # Other pull errors
                    QMessageBox.warning(self, "Pull Error", f"Failed to pull changes: {error_msg}")
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to pull changes: {str(e)}")
    
    def handle_divergent_branches(self, repo, repo_path, stashed=False):
        """Handle divergent branches with multiple resolution options"""
        try:
            # Get information about the divergent branches
            current_branch = repo.active_branch.name
            local_commits = list(repo.iter_commits(f'origin/{current_branch}..{current_branch}'))
            remote_commits = list(repo.iter_commits(f'{current_branch}..origin/{current_branch}'))
            
            local_count = len(local_commits)
            remote_count = len(remote_commits)
            
            # Create detailed message
            message = f"Divergent branches detected!\n\n"
            message += f"Your local branch has {local_count} commit(s) that aren't on the server\n"
            message += f"The server has {remote_count} commit(s) that aren't in your local branch\n\n"
            message += f"Choose how to reconcile the differences:"
            
            # Create custom dialog with multiple options
            msg = QMessageBox(self)
            msg.setWindowTitle("Divergent Branches - Choose Resolution Strategy")
            msg.setIcon(QMessageBox.Icon.Question)
            msg.setText(message)
            
            # Add custom buttons for different strategies
            merge_btn = msg.addButton("🔄 Merge (Create Merge Commit)", QMessageBox.ButtonRole.ActionRole)
            rebase_btn = msg.addButton("📝 Rebase (Replay Your Commits)", QMessageBox.ButtonRole.ActionRole)
            fast_forward_btn = msg.addButton("⚡ Fast-Forward Only (Safe)", QMessageBox.ButtonRole.ActionRole)
            overwrite_local_btn = msg.addButton("⚠️ Overwrite Local (Dangerous)", QMessageBox.ButtonRole.ActionRole)
            cancel_btn = msg.addButton("❌ Cancel", QMessageBox.ButtonRole.RejectRole)
            
            msg.exec()
            
            if msg.clickedButton() == merge_btn:
                self.pull_with_merge(repo, repo_path, stashed)
            elif msg.clickedButton() == rebase_btn:
                self.pull_with_rebase(repo, repo_path, stashed)
            elif msg.clickedButton() == fast_forward_btn:
                self.pull_fast_forward_only(repo, repo_path, stashed)
            elif msg.clickedButton() == overwrite_local_btn:
                self.pull_overwrite_local(repo, repo_path, stashed)
            # Cancel does nothing
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to handle divergent branches: {str(e)}")
    
    def pull_with_merge(self, repo, repo_path, stashed=False):
        """Pull with merge strategy (creates merge commit)"""
        try:
            current_branch = repo.active_branch.name
            # Configure and pull with merge
            repo.git.config('pull.rebase', 'false')
            repo.git.pull('origin', current_branch)
            
            # Restore stashed changes if any
            if stashed:
                try:
                    repo.git.stash('pop')
                    QMessageBox.information(self, "Success", "Changes pulled with merge strategy and stashed changes restored")
                except:
                    QMessageBox.information(self, "Success", "Changes pulled with merge strategy. Stashed changes had conflicts and remain in stash")
            else:
                QMessageBox.information(self, "Success", "Changes pulled with merge strategy - a merge commit was created")
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to pull with merge: {str(e)}")
    
    def pull_with_rebase(self, repo, repo_path, stashed=False):
        """Pull with rebase strategy (replays local commits on top)"""
        try:
            current_branch = repo.active_branch.name
            # Configure and pull with rebase
            repo.git.config('pull.rebase', 'true')
            repo.git.pull('origin', current_branch)
            
            # Restore stashed changes if any
            if stashed:
                try:
                    repo.git.stash('pop')
                    QMessageBox.information(self, "Success", "Changes pulled with rebase strategy and stashed changes restored")
                except:
                    QMessageBox.information(self, "Success", "Changes pulled with rebase strategy. Stashed changes had conflicts and remain in stash")
            else:
                QMessageBox.information(self, "Success", "Changes pulled with rebase strategy - your commits were replayed on top")
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to pull with rebase: {str(e)}")
    
    def pull_fast_forward_only(self, repo, repo_path, stashed=False):
        """Pull with fast-forward only (safest, fails if not possible)"""
        try:
            current_branch = repo.active_branch.name
            # Configure and pull with fast-forward only
            repo.git.config('pull.ff', 'only')
            repo.git.pull('origin', current_branch)
            
            # Restore stashed changes if any
            if stashed:
                try:
                    repo.git.stash('pop')
                    QMessageBox.information(self, "Success", "Changes pulled with fast-forward strategy and stashed changes restored")
                except:
                    QMessageBox.information(self, "Success", "Changes pulled with fast-forward strategy. Stashed changes had conflicts and remain in stash")
            else:
                QMessageBox.information(self, "Success", "Changes pulled with fast-forward strategy - clean linear history maintained")
                
        except Exception as e:
            error_msg = str(e)
            if "Not possible to fast-forward" in error_msg or "fast-forward" in error_msg:
                QMessageBox.warning(self, "Fast-Forward Not Possible", 
                    "Fast-forward is not possible because there are divergent changes.\n\n"
                    "Please choose 'Merge' or 'Rebase' strategy instead.")
            else:
                QMessageBox.warning(self, "Error", f"Failed to pull with fast-forward: {error_msg}")
    
    def pull_overwrite_local(self, repo, repo_path, stashed=False):
        """Pull and overwrite local changes (DANGEROUS)"""
        try:
            # Get current branch
            current_branch = repo.active_branch.name
            
            # Show strong warning
            reply = QMessageBox.question(
                self, "⚠️ DANGER: Overwrite Local Changes",
                f"⚠️ WARNING: This will PERMANENTLY DELETE your local commits!\n\n"
                f"Your local changes will be lost forever:\n"
                f"• All local commits will be discarded\n"
                f"• Your local branch will be reset to match the server\n"
                f"• This action CANNOT be undone\n\n"
                f"Are you absolutely sure you want to do this?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Reset local branch to match remote
                repo.git.fetch('origin')
                repo.git.reset('--hard', f'origin/{current_branch}')
                
                # Restore stashed changes if any
                if stashed:
                    try:
                        repo.git.stash('pop')
                        QMessageBox.information(self, "Success", "Local changes overwritten and stashed changes restored")
                    except:
                        QMessageBox.information(self, "Success", "Local changes overwritten. Stashed changes had conflicts and remain in stash")
                else:
                    QMessageBox.information(self, "Success", "Local changes overwritten - your branch now matches the server")
            else:
                QMessageBox.information(self, "Cancelled", "Overwrite operation cancelled")
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to overwrite local changes: {str(e)}")
    
    def add_new_folder(self, parent_path):
        """Add a new folder to the specified path"""
        try:
            from PyQt6.QtWidgets import QInputDialog
            
            folder_name, ok = QInputDialog.getText(
                self, "New Folder", 
                f"Enter folder name:\n\nParent: {Path(parent_path).name}",
                text="NewFolder"
            )
            
            if ok and folder_name.strip():
                folder_name = folder_name.strip()
                new_folder_path = Path(parent_path) / folder_name
                
                if new_folder_path.exists():
                    QMessageBox.warning(self, "Error", f"Folder '{folder_name}' already exists!")
                    return
                
                # Create the folder
                new_folder_path.mkdir(parents=True, exist_ok=True)
                
                # Refresh the tree to show the new folder
                self.refresh_repository_tree()
                
                QMessageBox.information(self, "Success", f"Folder '{folder_name}' created successfully!")
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to create folder: {str(e)}")
    
    def add_new_file(self, parent_path):
        """Add a new file to the specified path"""
        try:
            from PyQt6.QtWidgets import QInputDialog
            
            file_name, ok = QInputDialog.getText(
                self, "New File", 
                f"Enter file name (include extension):\n\nParent: {Path(parent_path).name}\n\nExamples: script.py, readme.txt, index.html",
                text="newfile.txt"
            )
            
            if ok and file_name.strip():
                file_name = file_name.strip()
                new_file_path = Path(parent_path) / file_name
                
                if new_file_path.exists():
                    QMessageBox.warning(self, "Error", f"File '{file_name}' already exists!")
                    return
                
                # Create the file with some basic content based on extension
                content = self.get_default_file_content(file_name)
                
                with open(new_file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # Refresh the tree to show the new file
                self.refresh_repository_tree()
                
                QMessageBox.information(self, "Success", f"File '{file_name}' created successfully!")
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to create file: {str(e)}")
    
    def get_default_file_content(self, filename):
        """Get default content for new files based on extension"""
        ext = Path(filename).suffix.lower()
        
        if ext == '.py':
            return f'# {filename}\n# Created with Gitea Interact\n\nprint("Hello, World!")\n'
        elif ext == '.html':
            return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{Path(filename).stem}</title>
</head>
<body>
    <h1>Hello, World!</h1>
    <p>This file was created with Gitea Interact.</p>
</body>
</html>'''
        elif ext == '.txt':
            return f'{filename}\n\nThis file was created with Gitea Interact.\n'
        elif ext == '.md':
            return f'# {Path(filename).stem}\n\nThis file was created with Gitea Interact.\n'
        elif ext == '.json':
            return '{\n    "name": "example",\n    "description": "Created with Gitea Interact"\n}\n'
        elif ext == '.css':
            return f'/* {filename} */\n/* Created with Gitea Interact */\n\nbody {{\n    font-family: Arial, sans-serif;\n    margin: 0;\n    padding: 20px;\n}}\n'
        elif ext == '.js':
            return f'// {filename}\n// Created with Gitea Interact\n\nconsole.log("Hello, World!");\n'
        else:
            return f'# {filename}\n\nThis file was created with Gitea Interact.\n'
    
    def remove_file(self, file_path):
        """Remove a file with confirmation"""
        try:
            file_name = Path(file_path).name
            
            reply = QMessageBox.question(
                self, "Remove File",
                f"Are you sure you want to remove the file '{file_name}'?\n\n"
                f"Path: {file_path}\n\n"
                f"⚠️ This action cannot be undone!",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Remove the file
                Path(file_path).unlink()
                
                # Refresh the tree to remove the file from view
                self.refresh_repository_tree()
                
                QMessageBox.information(self, "Success", f"File '{file_name}' removed successfully!")
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to remove file: {str(e)}")
    
    def remove_folder(self, folder_path):
        """Remove a folder with confirmation"""
        try:
            folder_name = Path(folder_path).name
            
            # Check if folder is empty
            folder_obj = Path(folder_path)
            if any(folder_obj.iterdir()):
                reply = QMessageBox.question(
                    self, "Remove Folder",
                    f"⚠️ WARNING: The folder '{folder_name}' is not empty!\n\n"
                    f"Path: {folder_path}\n\n"
                    f"Removing this folder will delete ALL files and subfolders inside it!\n"
                    f"This action cannot be undone!\n\n"
                    f"Are you absolutely sure you want to continue?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
            else:
                reply = QMessageBox.question(
                    self, "Remove Folder",
                    f"Are you sure you want to remove the empty folder '{folder_name}'?\n\n"
                    f"Path: {folder_path}\n\n"
                    f"⚠️ This action cannot be undone!",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Remove the folder and all its contents
                import shutil
                shutil.rmtree(folder_path)
                
                # Refresh the tree to remove the folder from view
                self.refresh_repository_tree()
                
                QMessageBox.information(self, "Success", f"Folder '{folder_name}' removed successfully!")
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to remove folder: {str(e)}")
    
    def get_current_commit_info(self, repo_path):
        """Get current commit information for a repository"""
        try:
            import git
            repo = git.Repo(repo_path)
            
            # Get current commit
            current_commit = repo.head.commit
            
            # Check if we're in detached HEAD state
            try:
                branch_name = repo.active_branch.name
                is_detached = False
            except:
                # We're in detached HEAD state
                branch_name = "detached HEAD"
                is_detached = True
            
            # Get commit hash (short)
            commit_hash = current_commit.hexsha[:8]
            
            # Get commit message (first line, truncated if too long)
            commit_message = current_commit.message.strip().split('\n')[0]
            if len(commit_message) > 30:
                commit_message = commit_message[:27] + "..."
            
            # Format the display string
            if is_detached:
                return f"HEAD@{commit_hash}: {commit_message}"
            else:
                return f"{branch_name}@{commit_hash}: {commit_message}"
                
        except Exception as e:
            # Not a git repository or other error
            return None
    
    def show_commit_info(self, repo_path):
        """Show detailed commit information in a dialog"""
        try:
            import git
            repo = git.Repo(repo_path)
            
            # Get current commit
            current_commit = repo.head.commit
            
            # Check if we're in detached HEAD state
            try:
                branch_name = repo.active_branch.name
                is_detached = False
            except:
                # We're in detached HEAD state
                branch_name = "detached HEAD"
                is_detached = True
            
            # Get detailed commit information
            commit_hash = current_commit.hexsha
            commit_hash_short = commit_hash[:8]
            commit_message = current_commit.message.strip()
            commit_author = current_commit.author.name
            commit_email = current_commit.author.email
            commit_date = current_commit.committed_datetime.strftime('%Y-%m-%d %H:%M:%S')
            
            # Get parent commits
            parent_hashes = [parent.hexsha[:8] for parent in current_commit.parents]
            parent_info = ", ".join(parent_hashes) if parent_hashes else "None (initial commit)"
            
            # Create detailed message
            message = f"📋 Current Commit Information\n\n"
            message += f"Repository: {Path(repo_path).name}\n"
            message += f"Branch: {branch_name}\n"
            message += f"Status: {'Detached HEAD' if is_detached else 'On Branch'}\n\n"
            message += f"Commit Hash: {commit_hash}\n"
            message += f"Short Hash: {commit_hash_short}\n"
            message += f"Author: {commit_author} <{commit_email}>\n"
            message += f"Date: {commit_date}\n"
            message += f"Parent(s): {parent_info}\n\n"
            message += f"Commit Message:\n{commit_message}"
            
            # Show information dialog
            msg = QMessageBox(self)
            msg.setWindowTitle("Commit Information")
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setText(message)
            # Style will be applied via theme_manager
            from theme_manager import ThemeManager
            current_theme = getattr(self.parent(), 'settings', {}).get('theme', 'light') if hasattr(self, 'parent') and self.parent() else 'light'
            msg.setStyleSheet(ThemeManager.get_message_box_style(current_theme))
            msg.exec()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to get commit information: {str(e)}")
    
    def update_welcome_content(self, theme_name):
        """Update welcome content with theme-appropriate colors"""
        from theme_manager import ThemeManager
        
        # Use theme manager for welcome content
        welcome_html = ThemeManager.get_welcome_html(theme_name)
        
        self.welcome_label.setText(welcome_html)

    def apply_theme(self, theme_name):
        """Apply theme to the RepoWindow"""
        colors = ThemeManager.get_theme_colors(theme_name)
        
        # Apply splitter theme
        self.splitter.setStyleSheet(ThemeManager.get_splitter_style(theme_name))
        
        # Apply comprehensive panel theme to the entire right panel
        self.right_panel.setStyleSheet(ThemeManager.get_panel_style(theme_name))
        
        # Apply editor panel theme specifically (for welcome message background)
        if hasattr(self, 'editor_panel') and self.editor_panel is not None:
            try:
                self.editor_panel.setStyleSheet(ThemeManager.get_editor_panel_style(theme_name))
            except RuntimeError:
                # Editor panel has been deleted, skip styling
                pass
        
        # Apply tree header theme
        if hasattr(self, 'header_widget'):
            self.header_widget.setStyleSheet(ThemeManager.get_tree_header_style(theme_name))
        
        # Apply content area theme
        self.content_area.setStyleSheet(ThemeManager.get_content_area_style(theme_name))
        
        # Apply tree widget theme
        self.tree.setStyleSheet(ThemeManager.get_tree_widget_style(theme_name))
        
        # Apply text editor theme
        if hasattr(self, 'text_viewer') and self.text_viewer is not None:
            try:
                self.text_viewer.setStyleSheet(ThemeManager.get_text_edit_style(theme_name))
            except RuntimeError:
                # Text viewer has been deleted, skip styling
                pass
        
        # Apply welcome message theme
        if hasattr(self, 'welcome_label') and self.welcome_label is not None:
            try:
                self.welcome_label.setStyleSheet(ThemeManager.get_welcome_style(theme_name))
            except RuntimeError:
                # Welcome label has been deleted, skip styling
                pass
        
        # Update welcome content with theme colors
        self.update_welcome_content(theme_name)
        
        # Apply image viewer themes to main editor panel
        if hasattr(self, 'image_label') and self.image_label is not None:
            try:
                self.image_label.setStyleSheet(ThemeManager.get_image_viewer_style(theme_name))
            except RuntimeError:
                pass
                
        if hasattr(self, 'image_scroll') and self.image_scroll is not None:
            try:
                self.image_scroll.setStyleSheet(ThemeManager.get_image_scroll_style(theme_name))
            except RuntimeError:
                pass
        
        # Apply button themes
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setStyleSheet(ThemeManager.get_small_button_style(theme_name))
        
        # Update the current file reference colors
        self.current_file = None  # Reset to force re-application of styles

    def apply_theme_to_file_viewer(self, file_viewer, theme_name):
        """Apply theme to a file viewer panel"""
        colors = ThemeManager.get_theme_colors(theme_name)
        
        # Apply panel theme
        file_viewer.setStyleSheet(ThemeManager.get_editor_panel_style(theme_name))
        
        # Apply text editor theme
        if hasattr(file_viewer, 'text_viewer') and file_viewer.text_viewer is not None:
            try:
                file_viewer.text_viewer.setStyleSheet(ThemeManager.get_text_edit_style(theme_name))
            except RuntimeError:
                pass
        
        # Apply image viewer themes
        if hasattr(file_viewer, 'image_label') and file_viewer.image_label is not None:
            try:
                file_viewer.image_label.setStyleSheet(ThemeManager.get_image_viewer_style(theme_name))
            except RuntimeError:
                pass
                
        if hasattr(file_viewer, 'image_scroll') and file_viewer.image_scroll is not None:
            try:
                file_viewer.image_scroll.setStyleSheet(ThemeManager.get_image_scroll_style(theme_name))
            except RuntimeError:
                pass
        
        # Apply button theme
        if hasattr(file_viewer, 'save_button') and file_viewer.save_button is not None:
            try:
                file_viewer.save_button.setStyleSheet(ThemeManager.get_button_style(theme_name))
            except RuntimeError:
                pass

    def on_settings_changed(self):
        """Handle settings changes from the settings panel"""
        # This method will be called when settings are changed
        # For now, we'll just print a message, but this could be extended
        # to handle other settings changes in the future

    def closeEvent(self, event):
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
        super().closeEvent(event)
