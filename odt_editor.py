import os
import zipfile
import tempfile
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QToolBar, 
    QPushButton, QComboBox, QFontComboBox, QSpinBox, QLabel,
    QColorDialog, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import (
    QTextCharFormat, QTextBlockFormat, QTextListFormat, 
    QFont, QColor, QTextCursor, QAction, QIcon, QPixmap
)
from odf.opendocument import load, OpenDocumentText
from odf.text import P, H, Span
from odf.style import Style, TextProperties, ParagraphProperties
from odf import text, style
from lxml import etree
import xml.etree.ElementTree as ET

class ODTEditor(QWidget):
    """Rich text editor for ODT files with full WYSIWYG capabilities"""
    
    content_changed = pyqtSignal()
    
    def __init__(self, file_path=None, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.odt_document = None
        self.is_loading = False
        
        self.setup_ui()
        self.setup_toolbar()
        
        if file_path and os.path.exists(file_path):
            self.load_odt_file(file_path)
    
    def setup_ui(self):
        """Setup the main UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create toolbar
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        layout.addWidget(self.toolbar)
        
        # Create rich text editor
        self.text_editor = QTextEdit()
        self.text_editor.setAcceptRichText(True)
        self.text_editor.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.text_editor)
        
        # Create save button
        self.save_button = QPushButton("💾 Save ODT File")
        # Style will be applied via theme_manager in apply_theme method
        self.save_button.clicked.connect(self.save_file)
        layout.addWidget(self.save_button)
        
        self.setLayout(layout)
    
    def apply_theme(self, theme_name):
        """Apply theme to the ODT editor"""
        from theme_manager import ThemeManager
        
        # Apply ODT editor theme
        self.setStyleSheet(ThemeManager.get_odt_editor_style(theme_name))
    
    def setup_toolbar(self):
        """Setup the formatting toolbar"""
        # Font family
        self.font_combo = QFontComboBox()
        self.font_combo.currentFontChanged.connect(self.change_font)
        self.toolbar.addWidget(QLabel("Font:"))
        self.toolbar.addWidget(self.font_combo)
        
        # Font size
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 72)
        self.font_size.setValue(12)
        self.font_size.valueChanged.connect(self.change_font_size)
        self.toolbar.addWidget(QLabel("Size:"))
        self.toolbar.addWidget(self.font_size)
        
        self.toolbar.addSeparator()
        
        # Bold
        self.bold_action = QAction("B", self)
        self.bold_action.setCheckable(True)
        self.bold_action.setShortcut("Ctrl+B")
        self.bold_action.triggered.connect(self.toggle_bold)
        self.toolbar.addAction(self.bold_action)
        
        # Italic
        self.italic_action = QAction("I", self)
        self.italic_action.setCheckable(True)
        self.italic_action.setShortcut("Ctrl+I")
        self.italic_action.triggered.connect(self.toggle_italic)
        self.toolbar.addAction(self.italic_action)
        
        # Underline
        self.underline_action = QAction("U", self)
        self.underline_action.setCheckable(True)
        self.underline_action.setShortcut("Ctrl+U")
        self.underline_action.triggered.connect(self.toggle_underline)
        self.toolbar.addAction(self.underline_action)
        
        self.toolbar.addSeparator()
        
        # Text color
        self.color_action = QAction("A", self)
        self.color_action.triggered.connect(self.change_text_color)
        self.toolbar.addAction(self.color_action)
        
        # Background color
        self.bg_color_action = QAction("BG", self)
        self.bg_color_action.triggered.connect(self.change_background_color)
        self.toolbar.addAction(self.bg_color_action)
        
        self.toolbar.addSeparator()
        
        # Alignment
        self.align_left_action = QAction("◀", self)
        self.align_left_action.setCheckable(True)
        self.align_left_action.triggered.connect(lambda: self.change_alignment(Qt.AlignmentFlag.AlignLeft))
        self.toolbar.addAction(self.align_left_action)
        
        self.align_center_action = QAction("◐", self)
        self.align_center_action.setCheckable(True)
        self.align_center_action.triggered.connect(lambda: self.change_alignment(Qt.AlignmentFlag.AlignCenter))
        self.toolbar.addAction(self.align_center_action)
        
        self.align_right_action = QAction("▶", self)
        self.align_right_action.setCheckable(True)
        self.align_right_action.triggered.connect(lambda: self.change_alignment(Qt.AlignmentFlag.AlignRight))
        self.toolbar.addAction(self.align_right_action)
        
        self.toolbar.addSeparator()
        
        # Lists
        self.bullet_list_action = QAction("•", self)
        self.bullet_list_action.triggered.connect(self.insert_bullet_list)
        self.toolbar.addAction(self.bullet_list_action)
        
        self.numbered_list_action = QAction("1.", self)
        self.numbered_list_action.triggered.connect(self.insert_numbered_list)
        self.toolbar.addAction(self.numbered_list_action)
        
        # Connect cursor position changes to update toolbar
        self.text_editor.cursorPositionChanged.connect(self.update_toolbar)
    
    def load_odt_file(self, file_path):
        """Load an ODT file into the editor"""
        try:
            self.is_loading = True
            self.file_path = file_path
            
            # Load the ODT document
            self.odt_document = load(file_path)
            
            # Extract text content and convert to HTML for rich text display
            html_content = self.odt_to_html()
            self.text_editor.setHtml(html_content)
            
            self.is_loading = False
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load ODT file: {str(e)}")
            self.is_loading = False
    
    def odt_to_html(self):
        """Convert ODT content to HTML for display in rich text editor"""
        try:
            html_parts = []
            
            # Get all paragraphs and headings
            for element in self.odt_document.text.childNodes:
                if element.qname[1] in ['p', 'h']:  # paragraph or heading
                    html_parts.append(self.element_to_html(element))
            
            return ''.join(html_parts)
            
        except Exception as e:
            return f"<p>Error converting ODT to HTML: {str(e)}</p>"
    
    def element_to_html(self, element):
        """Convert an ODT element to HTML"""
        tag_name = element.qname[1]
        
        if tag_name == 'p':
            return f"<p>{self.get_element_text(element)}</p>"
        elif tag_name == 'h':
            level = element.getAttribute('outlinelevel') or '1'
            return f"<h{level}>{self.get_element_text(element)}</h{level}>"
        else:
            return f"<p>{self.get_element_text(element)}</p>"
    
    def get_element_text(self, element):
        """Extract text content from an element, preserving basic formatting"""
        text_parts = []
        
        for child in element.childNodes:
            if hasattr(child, 'qname'):
                if child.qname[1] == 'span':
                    # Handle spans with formatting
                    style_name = child.getAttribute('stylename')
                    text_content = self.get_element_text(child)
                    
                    if style_name:
                        # Apply basic formatting based on style
                        if 'bold' in style_name.lower():
                            text_content = f"<b>{text_content}</b>"
                        if 'italic' in style_name.lower():
                            text_content = f"<i>{text_content}</i>"
                    
                    text_parts.append(text_content)
                else:
                    text_parts.append(self.get_element_text(child))
            elif hasattr(child, 'data'):
                text_parts.append(child.data)
        
        return ''.join(text_parts)
    
    def save_odt_file(self, file_path=None):
        """Save the current content as an ODT file"""
        try:
            if file_path:
                self.file_path = file_path
            
            if not self.file_path:
                QMessageBox.warning(self, "Error", "No file path specified for saving")
                return False
            
            # Create a new ODT document
            doc = OpenDocumentText()
            
            # Convert HTML content back to ODT format
            self.html_to_odt(doc)
            
            # Save the document
            doc.save(self.file_path)
            
            return True
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save ODT file: {str(e)}")
            return False
    
    def html_to_odt(self, doc):
        """Convert HTML content to ODT format"""
        try:
            html_content = self.text_editor.toHtml()
            
            # Parse HTML and convert to ODT elements
            # This is a simplified conversion - in a full implementation,
            # you'd want to use a proper HTML parser
            
            # For now, create a simple paragraph with the text content
            plain_text = self.text_editor.toPlainText()
            paragraphs = plain_text.split('\n\n')
            
            for para_text in paragraphs:
                if para_text.strip():
                    p = P(text=para_text.strip())
                    doc.text.addElement(p)
            
        except Exception as e:
            # Fallback: create a simple paragraph
            plain_text = self.text_editor.toPlainText()
            p = P(text=plain_text)
            doc.text.addElement(p)
    
    def on_text_changed(self):
        """Handle text changes"""
        if not self.is_loading:
            self.content_changed.emit()
    
    def update_toolbar(self):
        """Update toolbar based on current cursor position"""
        cursor = self.text_editor.textCursor()
        char_format = cursor.charFormat()
        
        # Update font
        font = char_format.font()
        self.font_combo.setCurrentFont(font)
        self.font_size.setValue(font.pointSize())
        
        # Update formatting buttons
        self.bold_action.setChecked(font.bold())
        self.italic_action.setChecked(font.italic())
        self.underline_action.setChecked(font.underline())
        
        # Update alignment
        block_format = cursor.blockFormat()
        alignment = block_format.alignment()
        self.align_left_action.setChecked(alignment == Qt.AlignmentFlag.AlignLeft)
        self.align_center_action.setChecked(alignment == Qt.AlignmentFlag.AlignCenter)
        self.align_right_action.setChecked(alignment == Qt.AlignmentFlag.AlignRight)
    
    def change_font(self, font):
        """Change font family"""
        cursor = self.text_editor.textCursor()
        char_format = cursor.charFormat()
        char_format.setFontFamily(font.family())
        cursor.mergeCharFormat(char_format)
        self.text_editor.setTextCursor(cursor)
    
    def change_font_size(self, size):
        """Change font size"""
        cursor = self.text_editor.textCursor()
        char_format = cursor.charFormat()
        char_format.setFontPointSize(size)
        cursor.mergeCharFormat(char_format)
        self.text_editor.setTextCursor(cursor)
    
    def toggle_bold(self):
        """Toggle bold formatting"""
        cursor = self.text_editor.textCursor()
        char_format = cursor.charFormat()
        char_format.setFontWeight(QFont.Weight.Bold if not char_format.font().bold() else QFont.Weight.Normal)
        cursor.mergeCharFormat(char_format)
        self.text_editor.setTextCursor(cursor)
    
    def toggle_italic(self):
        """Toggle italic formatting"""
        cursor = self.text_editor.textCursor()
        char_format = cursor.charFormat()
        char_format.setFontItalic(not char_format.font().italic())
        cursor.mergeCharFormat(char_format)
        self.text_editor.setTextCursor(cursor)
    
    def toggle_underline(self):
        """Toggle underline formatting"""
        cursor = self.text_editor.textCursor()
        char_format = cursor.charFormat()
        char_format.setFontUnderline(not char_format.font().underline())
        cursor.mergeCharFormat(char_format)
        self.text_editor.setTextCursor(cursor)
    
    def change_text_color(self):
        """Change text color"""
        color = QColorDialog.getColor(self.text_editor.textColor(), self)
        if color.isValid():
            cursor = self.text_editor.textCursor()
            char_format = cursor.charFormat()
            char_format.setForeground(color)
            cursor.mergeCharFormat(char_format)
            self.text_editor.setTextCursor(cursor)
    
    def change_background_color(self):
        """Change background color"""
        color = QColorDialog.getColor(QColor(255, 255, 255), self)
        if color.isValid():
            cursor = self.text_editor.textCursor()
            char_format = cursor.charFormat()
            char_format.setBackground(color)
            cursor.mergeCharFormat(char_format)
            self.text_editor.setTextCursor(cursor)
    
    def change_alignment(self, alignment):
        """Change text alignment"""
        cursor = self.text_editor.textCursor()
        block_format = cursor.blockFormat()
        block_format.setAlignment(alignment)
        cursor.mergeBlockFormat(block_format)
        self.text_editor.setTextCursor(cursor)
    
    def insert_bullet_list(self):
        """Insert bullet list"""
        cursor = self.text_editor.textCursor()
        list_format = QTextListFormat()
        list_format.setStyle(QTextListFormat.Style.ListDisc)
        cursor.createList(list_format)
        self.text_editor.setTextCursor(cursor)
    
    def insert_numbered_list(self):
        """Insert numbered list"""
        cursor = self.text_editor.textCursor()
        list_format = QTextListFormat()
        list_format.setStyle(QTextListFormat.Style.ListDecimal)
        cursor.createList(list_format)
        self.text_editor.setTextCursor(cursor)
    
    def get_content(self):
        """Get the current content as plain text"""
        return self.text_editor.toPlainText()
    
    def set_content(self, content):
        """Set the content"""
        self.text_editor.setPlainText(content)
    
    def save_file(self):
        """Save the ODT file"""
        if self.file_path:
            if self.save_odt_file(self.file_path):
                QMessageBox.information(self, "Success", "ODT file saved successfully!")
            else:
                QMessageBox.warning(self, "Error", "Failed to save ODT file.")
        else:
            QMessageBox.warning(self, "Error", "No file path specified for saving.")
