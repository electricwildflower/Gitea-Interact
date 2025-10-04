"""
Theme Manager for Gitea Interact
Centralized styling and theming system with clear light/dark theme organization
"""

import os

class ThemeManager:
    """Manages application themes and styling"""
    
    # =============================================================================
    # LIGHT THEME COLORS
    # =============================================================================
    
    @staticmethod
    def get_light_theme():
        """Get the light theme color palette"""
        return {
            # Main backgrounds
            'main_bg': '#f8f9fa',           # Main application background
            'panel_bg': '#ffffff',          # Panel and widget backgrounds
            'input_bg': '#ffffff',          # Input field backgrounds
            
            # Text colors
            'text_primary': '#333333',      # Primary text color
            'text_secondary': '#6c757d',    # Secondary text color
            
            # Accent colors
            'accent_color': '#2ea44f',      # Primary accent color (green)
            'accent_hover': '#28a745',      # Accent hover state
            
            # UI elements
            'border_color': '#e1e5e9',      # Border and divider color
            'button_bg': '#2ea44f',         # Button background
            'button_hover': '#28a745',      # Button hover state
            
            # Menu colors
            'menu_bg': '#2ea44f',           # Menu background
            'menu_text': '#ffffff',         # Menu text color
            
            # Tree widget colors
            'tree_bg': '#ffffff',           # Tree widget background
            'tree_text': '#333333',         # Tree widget text
            
            # Editor colors
            'editor_bg': '#ffffff',         # Text editor background
            'editor_text': '#333333',       # Text editor text
            
            # Welcome screen colors
            'welcome_bg': '#f8f9fa',        # Welcome screen background
            'welcome_text': '#333333',      # Welcome screen text
            
            # Status colors
            'success_bg': '#d4edda',        # Success message background
            'success_text': '#155724',      # Success message text
            'warning_bg': '#fff3cd',        # Warning message background
            'warning_text': '#856404',      # Warning message text
            'error_bg': '#f8d7da',          # Error message background
            'error_text': '#721c24',        # Error message text
            
            # Icon colors
            'arrow_color': '#000000',       # Arrow icon color (black)
            
            # Settings colors
            'settings_bg': '#ffffff',       # Settings panel background
            'settings_text': '#333333',     # Settings panel text
            
            # Image viewer colors
            'image_bg': '#f8f9fa',          # Image viewer background
            'image_border': '#e1e5e9',      # Image viewer border
        }
    
    # =============================================================================
    # DARK THEME COLORS
    # =============================================================================
    
    @staticmethod
    def get_dark_theme():
        """Get the dark theme color palette"""
        return {
            # Main backgrounds
            'main_bg': '#1a1a1a',           # Main application background
            'panel_bg': '#2d2d2d',          # Panel and widget backgrounds
            'input_bg': '#3d3d3d',          # Input field backgrounds
            
            # Text colors
            'text_primary': '#ffffff',      # Primary text color
            'text_secondary': '#b0b0b0',    # Secondary text color
            
            # Accent colors
            'accent_color': '#4CAF50',      # Primary accent color (green)
            'accent_hover': '#45a049',      # Accent hover state
            
            # UI elements
            'border_color': '#404040',      # Border and divider color
            'button_bg': '#4CAF50',         # Button background
            'button_hover': '#45a049',      # Button hover state
            
            # Menu colors
            'menu_bg': '#2d2d2d',           # Menu background
            'menu_text': '#ffffff',         # Menu text color
            
            # Tree widget colors
            'tree_bg': '#2d2d2d',           # Tree widget background
            'tree_text': '#ffffff',         # Tree widget text
            
            # Editor colors
            'editor_bg': '#1e1e1e',         # Text editor background
            'editor_text': '#ffffff',       # Text editor text
            
            # Welcome screen colors
            'welcome_bg': '#2d2d2d',        # Welcome screen background
            'welcome_text': '#ffffff',      # Welcome screen text
            
            # Status colors
            'success_bg': '#1b5e20',        # Success message background
            'success_text': '#a5d6a7',      # Success message text
            'warning_bg': '#e65100',        # Warning message background
            'warning_text': '#ffcc02',      # Warning message text
            'error_bg': '#b71c1c',          # Error message background
            'error_text': '#ffcdd2',        # Error message text
            
            # Icon colors
            'arrow_color': '#ffffff',       # Arrow icon color (white)
            
            # Settings colors
            'settings_bg': '#2d2d2d',       # Settings panel background
            'settings_text': '#ffffff',     # Settings panel text
            
            # Image viewer colors
            'image_bg': '#1a1a1a',          # Image viewer background
            'image_border': '#404040',      # Image viewer border
        }
    
    # =============================================================================
    # THEME UTILITIES
    # =============================================================================
    
    @staticmethod
    def get_theme_colors(theme_name):
        """Get theme colors by name"""
        if theme_name == 'dark':
            return ThemeManager.get_dark_theme()
        else:
            return ThemeManager.get_light_theme()
    
    @staticmethod
    def get_triangle_icons(theme_name):
        """Get triangle icon paths based on theme"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        icons_dir = os.path.join(script_dir, 'icons')
        
        if theme_name == 'dark':
            return {
                'right': os.path.join(icons_dir, 'triangle_right_white.png').replace('\\', '/'),
                'down': os.path.join(icons_dir, 'triangle_down_white.png').replace('\\', '/')
            }
        else:
            return {
                'right': os.path.join(icons_dir, 'triangle_right_black.png').replace('\\', '/'),
                'down': os.path.join(icons_dir, 'triangle_down_black.png').replace('\\', '/')
            }
    
    # =============================================================================
    # MAIN WINDOW STYLES
    # =============================================================================
    
    @staticmethod
    def get_main_window_style(theme_name):
        """Get main window stylesheet"""
        colors = ThemeManager.get_theme_colors(theme_name)
        
        return f"""
        QMainWindow {{
            background-color: {colors['main_bg']};
            color: {colors['text_primary']};
        }}
        QWidget {{
            background-color: {colors['main_bg']};
            color: {colors['text_primary']};
        }}
        QSplitter {{
            background-color: {colors['main_bg']};
        }}
        QSplitter::handle {{
            background-color: {colors['border_color']};
        }}
        QSplitter::handle:horizontal {{
            width: 3px;
        }}
        QSplitter::handle:vertical {{
            height: 3px;
        }}
        """
    
    @staticmethod
    def get_splitter_style(theme_name):
        """Get splitter stylesheet"""
        colors = ThemeManager.get_theme_colors(theme_name)
        
        return f"""
        QSplitter::handle {{
            background-color: {colors['border_color']};
            width: 2px;
            border-radius: 1px;
        }}
        QSplitter::handle:hover {{
            background-color: {colors['accent_color']};
        }}
        """
    
    # =============================================================================
    # MENU STYLES
    # =============================================================================
    
    @staticmethod
    def get_menu_bar_style(theme_name):
        """Get menu bar stylesheet"""
        colors = ThemeManager.get_theme_colors(theme_name)
        
        return f"""
        QMenuBar {{
            background-color: {colors['menu_bg']};
            color: {colors['menu_text']};
            font-size: 14px;
            padding: 4px;
            border-bottom: 1px solid {colors['border_color']};
        }}
        QMenuBar::item {{
            background: transparent;
            padding: 6px 12px;
            color: {colors['menu_text']};
        }}
        QMenuBar::item:selected {{
            background: {colors['accent_hover']};
            border-radius: 4px;
        }}
        QMenu {{
            background-color: {colors['panel_bg']};
            border: 1px solid {colors['border_color']};
            color: {colors['text_primary']};
        }}
        QMenu::item:selected {{
            background-color: {colors['accent_color']};
            color: {colors['menu_text']};
        }}
        """
    
    @staticmethod
    def get_context_menu_style(theme_name):
        """Get context menu stylesheet"""
        colors = ThemeManager.get_theme_colors(theme_name)
        
        return f"""
        QMenu {{
            background-color: {colors['panel_bg']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border_color']};
            border-radius: 8px;
            padding: 8px;
        }}
        QMenu::item {{
            padding: 8px 16px;
            border-radius: 4px;
            margin: 2px;
        }}
        QMenu::item:selected {{
            background-color: {colors['accent_color']};
            color: {colors['menu_text']};
        }}
        """
    
    # =============================================================================
    # TREE WIDGET STYLES
    # =============================================================================
    
    @staticmethod
    def get_tree_widget_style(theme_name):
        """Get tree widget stylesheet"""
        colors = ThemeManager.get_theme_colors(theme_name)
        icons = ThemeManager.get_triangle_icons(theme_name)
        
        return f"""
        QTreeWidget {{
            background-color: {colors['tree_bg']};
            color: {colors['tree_text']};
            border: 1px solid {colors['border_color']};
            border-radius: 8px;
            font-size: 13px;
            selection-background-color: {colors['accent_color']};
        }}
        QTreeWidget::item {{
            padding: 4px;
            border: none;
            background-color: transparent;
            color: {colors['tree_text']};
        }}
        QTreeWidget::item:selected {{
            background-color: {colors['accent_color']};
            color: {colors['menu_text']};
        }}
        QTreeWidget::item:hover {{
            background-color: {colors['accent_hover']};
            color: {colors['menu_text']};
        }}
        QTreeWidget::branch {{
            background: transparent;
            border: none;
        }}
        QTreeWidget::branch:has-children:!has-siblings:closed,
        QTreeWidget::branch:closed:has-children:has-siblings {{
            background: transparent;
            border: none;
            image: url({icons['right']});
            width: 8px;
            height: 8px;
            margin-right: 6px;
            margin-top: 3px;
            margin-left: 3px;
        }}
        QTreeWidget::branch:open:has-children:!has-siblings,
        QTreeWidget::branch:open:has-children:has-siblings {{
            background: transparent;
            border: none;
            image: url({icons['down']});
            width: 8px;
            height: 8px;
            margin-right: 6px;
            margin-top: 3px;
            margin-left: 3px;
        }}
        """
    
    @staticmethod
    def get_tree_header_style(theme_name):
        """Get tree header stylesheet"""
        colors = ThemeManager.get_theme_colors(theme_name)
        
        return f"""
        QWidget {{
            background-color: {colors['panel_bg']};
            border: 1px solid {colors['border_color']};
            border-bottom: none;
            border-radius: 12px 12px 0 0;
            padding: 8px 12px;
        }}
        QLabel {{
            font-size: 16px;
            font-weight: bold;
            color: {colors['text_primary']};
            background: transparent;
            border: none;
        }}
        """
    
    # =============================================================================
    # BUTTON STYLES
    # =============================================================================
    
    @staticmethod
    def get_button_style(theme_name):
        """Get button stylesheet"""
        colors = ThemeManager.get_theme_colors(theme_name)
        
        return f"""
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
        QPushButton:pressed {{
            background: {colors['button_hover']};
        }}
        QPushButton:disabled {{
            background: {colors['border_color']};
            color: {colors['text_secondary']};
        }}
        """
    
    @staticmethod
    def get_small_button_style(theme_name):
        """Get small button stylesheet (for refresh button, etc.)"""
        colors = ThemeManager.get_theme_colors(theme_name)
        
        return f"""
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                stop:0 {colors['button_bg']}, stop:1 {colors['button_hover']});
            color: {colors['menu_text']};
            border: none;
            border-radius: 6px;
            padding: 6px 12px;
            font-size: 14px;
            font-weight: bold;
            min-width: 32px;
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                stop:0 {colors['button_hover']}, stop:1 {colors['button_bg']});
        }}
        QPushButton:pressed {{
            background: {colors['button_hover']};
        }}
        QPushButton:disabled {{
            background: {colors['border_color']};
            color: {colors['text_secondary']};
        }}
        """
    
    # =============================================================================
    # TEXT EDITOR STYLES
    # =============================================================================
    
    @staticmethod
    def get_text_edit_style(theme_name):
        """Get text editor stylesheet"""
        colors = ThemeManager.get_theme_colors(theme_name)
        
        return f"""
        QTextEdit {{
            background-color: {colors['editor_bg']};
            color: {colors['editor_text']};
            border: 1px solid {colors['border_color']};
            border-radius: 8px;
            padding: 12px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.4;
        }}
        QTextEdit:focus {{
            border: 2px solid {colors['accent_color']};
        }}
        """
    
    # =============================================================================
    # PANEL STYLES
    # =============================================================================
    
    @staticmethod
    def get_panel_style(theme_name):
        """Get comprehensive panel stylesheet for all panels"""
        colors = ThemeManager.get_theme_colors(theme_name)
        
        return f"""
        QWidget {{
            background-color: {colors['main_bg']};
            color: {colors['text_primary']};
        }}
        QFrame {{
            background-color: {colors['panel_bg']};
            border: 1px solid {colors['border_color']};
            border-radius: 12px;
            padding: 16px;
        }}
        QLabel {{
            color: {colors['text_primary']};
            background-color: transparent;
        }}
        QLineEdit {{
            background-color: {colors['input_bg']};
            color: {colors['text_primary']};
            border: 2px solid {colors['border_color']};
            border-radius: 8px;
            padding: 12px;
            font-size: 14px;
        }}
        QLineEdit:focus {{
            border: 2px solid {colors['accent_color']};
        }}
        QTextEdit {{
            background-color: {colors['editor_bg']};
            color: {colors['editor_text']};
            border: 1px solid {colors['border_color']};
            border-radius: 8px;
            padding: 12px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 13px;
        }}
        QTextEdit:focus {{
            border-color: {colors['accent_color']};
        }}
        QScrollArea {{
            background-color: {colors['panel_bg']};
            border: 1px solid {colors['border_color']};
            border-radius: 8px;
        }}
        QScrollArea > QWidget > QWidget {{
            background-color: {colors['panel_bg']};
        }}
        QComboBox {{
            background-color: {colors['input_bg']};
            color: {colors['text_primary']};
            border: 2px solid {colors['border_color']};
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 14px;
        }}
        QComboBox:focus {{
            border: 2px solid {colors['accent_color']};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid {colors['text_primary']};
            margin-right: 5px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {colors['main_bg']};
            color: {colors['text_primary']};
            border: 1px solid {colors['main_bg']};
            border-radius: 6px;
            selection-background-color: {colors['accent_color']};
            selection-color: {colors['menu_text']};
            outline: none;
        }}
        QComboBox QAbstractItemView::item {{
            background-color: {colors['panel_bg']};
            color: {colors['text_primary']};
            padding: 12px 16px;
            border-radius: 4px;
            margin: 1px;
            min-height: 20px;
        }}
        QComboBox QAbstractItemView::item:selected {{
            background-color: {colors['accent_color']};
            color: {colors['menu_text']};
            font-weight: bold;
        }}
        QComboBox QAbstractItemView::item:hover {{
            background-color: {colors['accent_hover']};
            color: {colors['menu_text']};
        }}
        QListWidget {{
            background-color: {colors['input_bg']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border_color']};
            border-radius: 8px;
            padding: 8px;
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
            color: {colors['menu_text']};
        }}
        """
    
    @staticmethod
    def get_content_area_style(theme_name):
        """Get content area stylesheet"""
        colors = ThemeManager.get_theme_colors(theme_name)
        
        return f"""
        QWidget {{
            background-color: {colors['panel_bg']};
            border: 1px solid {colors['border_color']};
            border-radius: 12px;
            margin: 8px;
        }}
        """
    
    @staticmethod
    def get_editor_panel_style(theme_name):
        """Get editor panel stylesheet"""
        colors = ThemeManager.get_theme_colors(theme_name)
        
        return f"""
        QWidget {{
            background-color: {colors['panel_bg']};
            border-radius: 12px;
        }}
        """
    
    # =============================================================================
    # IMAGE VIEWER STYLES
    # =============================================================================
    
    @staticmethod
    def get_image_viewer_style(theme_name):
        """Get image viewer stylesheet"""
        colors = ThemeManager.get_theme_colors(theme_name)
        
        return f"""
        QLabel {{
            background-color: {colors['image_bg']};
            border: 2px dashed {colors['image_border']};
            border-radius: 8px;
            padding: 20px;
        }}
        """
    
    @staticmethod
    def get_image_scroll_style(theme_name):
        """Get image scroll area stylesheet"""
        colors = ThemeManager.get_theme_colors(theme_name)
        
        return f"""
        QScrollArea {{
            background-color: {colors['image_bg']};
            border: 1px solid {colors['image_border']};
            border-radius: 8px;
        }}
        """
    
    # =============================================================================
    # WELCOME SCREEN STYLES
    # =============================================================================
    
    @staticmethod
    def get_welcome_style(theme_name):
        """Get welcome message stylesheet"""
        colors = ThemeManager.get_theme_colors(theme_name)
        
        return f"""
        QLabel {{
            font-size: 14px;
            color: {colors['welcome_text']};
            padding: 16px;
            background-color: transparent;
            line-height: 1.6;
        }}
        """
    
    @staticmethod
    def get_welcome_html(theme_name):
        """Get welcome screen HTML content with theme colors"""
        colors = ThemeManager.get_theme_colors(theme_name)
        
        return f"""
        <div style="text-align: center; margin-bottom: 20px;">
            <h1 style="color: {colors['accent_color']}; font-size: 24px; margin: 0;">👋 Welcome to Gitea Interact</h1>
            <p style="color: {colors['text_secondary']}; font-size: 16px; margin: 8px 0;">Complete Git Management Solution</p>
        </div>
        
        <div style="background-color: {colors['welcome_bg']}; padding: 20px; border-radius: 8px; border-left: 4px solid {colors['accent_color']};">
            <h3 style="color: {colors['accent_color']}; margin-top: 0;">🚀 Getting Started</h3>
            
            <p><b>📁 Repository Tree (Left Panel):</b></p>
            <ul style="margin: 8px 0;">
            <li><b>Right-click repositories</b> for Git operations (Add, Commit, Push, Pull, Logs)</li>
            <li><b>Right-click files/folders</b> to create, remove, or view Git history</li>
            <li><b>Click files</b> to open and edit them in the right panel</li>
            <li><b>Refresh button</b> (🔄) to sync with external changes</li>
            </ul>
            
            <p><b>⚙️ Configuration:</b></p>
            <ul style="margin: 8px 0;">
            <li><b>SSH Menu:</b> Create and manage SSH keys for Git authentication</li>
            <li><b>Gitea Menu:</b> Configure API connections and download repositories</li>
            <li><b>Settings Menu:</b> Toggle fullscreen mode and manage preferences</li>
            </ul>
            
            <p style="background-color: {colors['success_bg']}; color: {colors['success_text']}; padding: 12px; border-radius: 6px; margin: 16px 0 0 0;">
            <b>💡 Pro Tip:</b> Most Git operations are available via right-click context menus!
            </p>
        </div>
        """
    
    # =============================================================================
    # MESSAGE BOX STYLES
    # =============================================================================
    
    @staticmethod
    def get_message_box_style(theme_name):
        """Get message box stylesheet"""
        colors = ThemeManager.get_theme_colors(theme_name)
        
        return f"""
        QMessageBox {{
            background-color: {colors['panel_bg']};
            color: {colors['text_primary']};
        }}
        QMessageBox QLabel {{
            background-color: transparent;
            color: {colors['text_primary']};
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 12px;
            line-height: 1.4;
        }}
        QMessageBox QPushButton {{
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
        QMessageBox QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                stop:0 {colors['button_hover']}, stop:1 {colors['button_bg']});
        }}
        """
    
    # =============================================================================
    # GIT LOGS VIEWER STYLES
    # =============================================================================
    
    @staticmethod
    def get_git_logs_style(theme_name):
        """Get git logs viewer stylesheet"""
        colors = ThemeManager.get_theme_colors(theme_name)
        
        return f"""
        QWidget {{
            background-color: {colors['panel_bg']};
            color: {colors['text_primary']};
        }}
        QFrame {{
            background-color: {colors['panel_bg']};
            border: 1px solid {colors['border_color']};
            border-radius: 12px;
            padding: 16px;
        }}
        QLabel {{
            color: {colors['text_primary']};
            background-color: transparent;
        }}
        QListWidget {{
            background-color: {colors['input_bg']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border_color']};
            border-radius: 8px;
            padding: 8px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 12px;
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
            color: {colors['menu_text']};
        }}
        QTextEdit {{
            background-color: {colors['editor_bg']};
            color: {colors['editor_text']};
            border: 1px solid {colors['border_color']};
            border-radius: 8px;
            padding: 12px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 12px;
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
        """
    
    # =============================================================================
    # SETTINGS PANEL STYLES
    # =============================================================================
    
    @staticmethod
    def get_settings_panel_style(theme_name):
        """Get settings panel stylesheet"""
        colors = ThemeManager.get_theme_colors(theme_name)
        
        return f"""
        QWidget {{
            background-color: {colors['main_bg']};
            color: {colors['text_primary']};
        }}
        QFrame {{
            background-color: {colors['panel_bg']};
            border: 1px solid {colors['border_color']};
            border-radius: 12px;
            padding: 16px;
        }}
        QLabel {{
            color: {colors['text_primary']};
            background-color: transparent;
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
            font-size: 12px;
            color: {colors['text_secondary']};
            padding: 4px 0 8px 0;
            line-height: 1.4;
        }}
        QCheckBox {{
            color: {colors['text_primary']};
            background-color: transparent;
            font-size: 14px;
            padding: 8px 0;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 4px;
            background-color: {colors['input_bg']};
            border: 2px solid {colors['border_color']};
        }}
        QCheckBox::indicator:checked {{
            background-color: {colors['accent_color']};
            border-color: {colors['accent_color']};
        }}
        QCheckBox::indicator:hover {{
            border-color: {colors['accent_color']};
        }}
        QComboBox {{
            background-color: {colors['input_bg']};
            color: {colors['text_primary']};
            border: 2px solid {colors['border_color']};
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 14px;
            min-width: 200px;
        }}
        QComboBox:hover {{
            border-color: {colors['accent_color']};
        }}
        QComboBox:focus {{
            border-color: {colors['accent_color']};
            outline: none;
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid {colors['text_secondary']};
        }}
        QComboBox QAbstractItemView {{
            background-color: {colors['main_bg']};
            color: {colors['text_primary']};
            border: 1px solid {colors['main_bg']};
            border-radius: 6px;
            selection-background-color: {colors['accent_color']};
            selection-color: {colors['menu_text']};
            outline: none;
        }}
        QComboBox QAbstractItemView::item {{
            background-color: {colors['panel_bg']};
            color: {colors['text_primary']};
            padding: 12px 16px;
            border-radius: 4px;
            margin: 1px;
            min-height: 20px;
        }}
        QComboBox QAbstractItemView::item:selected {{
            background-color: {colors['accent_color']};
            color: {colors['menu_text']};
            font-weight: bold;
        }}
        QComboBox QAbstractItemView::item:hover {{
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
        QPushButton:pressed {{
            background: {colors['button_hover']};
        }}
        """
    
    # =============================================================================
    # ODT EDITOR STYLES
    # =============================================================================
    
    @staticmethod
    def get_odt_editor_style(theme_name):
        """Get ODT editor stylesheet"""
        colors = ThemeManager.get_theme_colors(theme_name)
        
        return f"""
        QWidget {{
            background-color: {colors['panel_bg']};
            color: {colors['text_primary']};
        }}
        QTextEdit {{
            background-color: {colors['editor_bg']};
            color: {colors['editor_text']};
            border: 1px solid {colors['border_color']};
            border-radius: 8px;
            padding: 12px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.4;
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
        QPushButton:pressed {{
            background: {colors['button_hover']};
        }}
        """
