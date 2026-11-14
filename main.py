import os
import sys
from urllib.parse import quote_plus

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QToolButton, QLineEdit, QMessageBox, QMenu, QToolBar
)
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView

APP_NAME = "Tarnakium"
START_PAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "startpage.html")
HOME_URL = QUrl.fromLocalFile(START_PAGE)
SEARCH_URL = "https://duckduckgo.com/?q={}"


def address_to_url(text: str) -> QUrl:
    text = text.strip()
    if not text:
        return QUrl(HOME_URL)
    if " " not in text and ("." in text or text.startswith(("http://", "https://", "file://"))):
        if "://" not in text and not text.startswith("localhost"):
            text = "https://" + text
        return QUrl.fromUserInput(text)
    return QUrl(SEARCH_URL.format(quote_plus(text)))


class TarnakiumBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tarnakium")
        self.resize(1280, 820)
        self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)

        self.profile = QWebEngineProfile.defaultProfile()
        # Keep Qt WebEngine's normal user agent. Spoofing it can make search
        # engines distrust the browser; it cannot remove server-side CAPTCHA.

        self.browser = QWebEngineView(self)
        settings = self.browser.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, False)
        self.browser.urlChanged.connect(self.sync_address)
        self.browser.titleChanged.connect(self.sync_title)
        self.browser.loadFinished.connect(lambda _ok: self.sync_address(self.browser.url()))

        self._build_toolbar()
        self._build_menus()
        self._apply_style()
        self.setCentralWidget(self.browser)
        self.browser.setUrl(HOME_URL)

    def _tool_button(self, label, tooltip, callback):
        button = QToolButton(self)
        button.setText(label)
        button.setToolTip(tooltip)
        button.clicked.connect(callback)
        return button

    def _build_toolbar(self):
        bar = QWidget(self)
        row = QHBoxLayout(bar)
        row.setContentsMargins(8, 7, 8, 7)
        row.setSpacing(6)
        row.addWidget(self._tool_button("←", "Back", self.browser_back))
        row.addWidget(self._tool_button("→", "Forward", self.browser_forward))
        row.addWidget(self._tool_button("⟳", "Reload", self.browser_reload))
        row.addWidget(self._tool_button("⌂", "Home", self.go_home))
        self.address = QLineEdit(self)
        self.address.setPlaceholderText("Search Google or enter a website address")
        self.address.setClearButtonEnabled(True)
        self.address.returnPressed.connect(self.navigate_from_bar)
        row.addWidget(self.address, 1)

        toolbar = QToolBar("Navigation", self)
        toolbar.setMovable(False)
        toolbar.addWidget(bar)
        self.addToolBar(toolbar)

    def _build_menus(self):
        file_menu = self.menuBar().addMenu("&File")
        home_action = QAction("Go to start page", self)
        home_action.setShortcut("Alt+Home")
        home_action.triggered.connect(self.go_home)
        file_menu.addAction(home_action)
        reload_action = QAction("Reload page", self)
        reload_action.setShortcut("F5")
        reload_action.triggered.connect(self.browser_reload)
        file_menu.addAction(reload_action)

        privacy_menu = self.menuBar().addMenu("&Privacy")
        clear_action = QAction("Clear cookies and cache…", self)
        clear_action.triggered.connect(self.clear_site_data)
        privacy_menu.addAction(clear_action)
        note_action = QAction("Privacy limitations", self)
        note_action.triggered.connect(self.show_privacy_note)
        privacy_menu.addAction(note_action)

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #111318; color: #e8eaf0; }
            QMenuBar { background: #171a21; color: #e8eaf0; padding: 5px; }
            QMenuBar::item:selected, QMenu::item:selected { background: #303747; }
            QMenu { background: #1b1f29; color: #e8eaf0; border: 1px solid #353b49; }
            QToolBar { background: #171a21; border: none; spacing: 6px; }
            QToolButton { background: #252a36; color: #e8eaf0; border: 1px solid #353b49;
                border-radius: 8px; padding: 7px 11px; font-size: 15px; }
            QToolButton:hover { background: #343b4c; }
            QLineEdit { background: #202430; color: #f4f5f8; border: 1px solid #3b4252;
                border-radius: 10px; padding: 9px 12px; selection-background-color: #5268a8; }
            QStatusBar { background: #171a21; color: #9ca6b8; }
        """)

    def browser_back(self):
        self.browser.back()

    def browser_forward(self):
        self.browser.forward()

    def browser_reload(self):
        self.browser.reload()

    def go_home(self):
        self.browser.setUrl(HOME_URL)

    def navigate_from_bar(self):
        self.browser.setUrl(address_to_url(self.address.text()))

    def sync_address(self, url):
        self.address.setText(url.toString())

    def sync_title(self, title):
        self.setWindowTitle(f"{title or APP_NAME} — {APP_NAME}")

    def clear_site_data(self):
        answer = QMessageBox.question(
            self, "Clear browsing data",
            "Delete cookies and cached files for this browser profile? This may sign you out of websites.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.profile.cookieStore().deleteAllCookies()
            self.profile.clearHttpCache()
            self.profile.clearAllVisitedLinks()
            QMessageBox.information(self, "Privacy", "A request to clear cookies, cache and visited-link data was sent.")

    def show_privacy_note(self):
        QMessageBox.information(
            self, "Privacy limitations",
            "Tarnakium is a starter browser, not an anonymity tool. Websites can still see your IP address and browser characteristics. "
            "Google controls its own CAPTCHA checks; the browser cannot remove or disable them. Keep Python, PySide6 and Qt WebEngine updated."
        )


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    window = TarnakiumBrowser()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
