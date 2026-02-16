#!/usr/bin/env python3
"""
K3s & Docker System Tray Indicator für KDE Plasma
Benötigt: pip install PyQt6
Für SVG: ggf. zusätzlich python3-pyqt6.qtsvg (Debian/Ubuntu)
"""
import os
import sys
import subprocess
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter

try:
    from PyQt6.QtSvg import QSvgRenderer
    HAS_SVG = True
except Exception:
    HAS_SVG = False


class K3sDockerTrayIcon(QSystemTrayIcon):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Logo-Pfad relativ zum Script
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.logo_path = os.path.join(base_dir, "k3s-docker-status-tray.svg")

        # Fallback-Starticon
        self.setIcon(QIcon.fromTheme("kubernetes", QIcon.fromTheme("network-server")))

        # Menu erstellen
        self.menu = QMenu()

        # K3s Status Section
        k3s_header = QAction("─── K3s ───", self.menu)
        k3s_header.setEnabled(False)
        self.menu.addAction(k3s_header)

        self.k3s_status_action = QAction("Status: Checking...", self.menu)
        self.k3s_status_action.setEnabled(False)
        self.menu.addAction(self.k3s_status_action)

        start_k3s_action = QAction("Start K3s", self.menu)
        start_k3s_action.triggered.connect(self.start_k3s)
        self.menu.addAction(start_k3s_action)

        stop_k3s_action = QAction("Stop K3s", self.menu)
        stop_k3s_action.triggered.connect(self.stop_k3s)
        self.menu.addAction(stop_k3s_action)

        restart_k3s_action = QAction("Restart K3s", self.menu)
        restart_k3s_action.triggered.connect(self.restart_k3s)
        self.menu.addAction(restart_k3s_action)

        self.menu.addSeparator()

        # Docker Status Section
        docker_header = QAction("─── Docker ───", self.menu)
        docker_header.setEnabled(False)
        self.menu.addAction(docker_header)

        self.docker_status_action = QAction("Status: Checking...", self.menu)
        self.docker_status_action.setEnabled(False)
        self.menu.addAction(self.docker_status_action)

        start_docker_action = QAction("Start Docker", self.menu)
        start_docker_action.triggered.connect(self.start_docker)
        self.menu.addAction(start_docker_action)

        stop_docker_action = QAction("Stop Docker", self.menu)
        stop_docker_action.triggered.connect(self.stop_docker)
        self.menu.addAction(stop_docker_action)

        restart_docker_action = QAction("Restart Docker", self.menu)
        restart_docker_action.triggered.connect(self.restart_docker)
        self.menu.addAction(restart_docker_action)

        self.menu.addSeparator()

        # Quit Action
        quit_action = QAction("Quit", self.menu)
        quit_action.triggered.connect(QApplication.quit)
        self.menu.addAction(quit_action)

        self.setContextMenu(self.menu)

        # Timer für Status-Updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(5000)
        self.update_status()
        self.show()

    def get_service_status(self, service_name):
        """Generische Funktion für systemctl Status-Abfrage"""
        try:
            result = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True,
                text=True,
                timeout=2,
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"

    def load_logo_pixmap(self, path: str, size: int, tint: str | None = None) -> QPixmap:
        """Lädt SVG/PNG. Bei SVG kann optional per `tint` eingefärbt werden."""
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)

        if not path or not os.path.exists(path):
            return pm

        # SVG
        if path.lower().endswith(".svg"):
            if not HAS_SVG:
                return pm
            try:
                with open(path, "r", encoding="utf-8") as f:
                    svg = f.read()
                if tint:
                    import re
                    svg = re.sub(r'fill="(?!none)[^"]*"', f'fill="{tint}"', svg)
                    svg = re.sub(r"fill='(?!none)[^']*'", f"fill='{tint}'", svg)
                    svg = re.sub(r'stroke="(?!none)[^"]*"', f'stroke="{tint}"', svg)
                    svg = re.sub(r"stroke='(?!none)[^']*'", f"stroke='{tint}'", svg)
                    if 'fill="' not in svg and "fill='" not in svg:
                        svg = svg.replace("<svg", f'<svg fill="{tint}"')

                renderer = QSvgRenderer(svg.encode("utf-8"))
                painter = QPainter(pm)
                renderer.render(painter)
                painter.end()
            except Exception:
                pass
        # PNG
        elif path.lower().endswith(".png"):
            pm = QPixmap(path).scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                                      Qt.TransformationMode.SmoothTransformation)
        return pm

    def create_status_icon(self, cow_color="#000000", size=64) -> QIcon:
        """Tray-Icon: Logo wird eingefärbt basierend auf kombiniertem Status."""
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        logo_size = int(size * 1.35)
        logo = self.load_logo_pixmap(self.logo_path, logo_size, tint=cow_color)
        x = (size - logo.width()) // 2
        y = (size - logo.height()) // 2
        painter.drawPixmap(x, y, logo)

        painter.end()
        return QIcon(pm)

    def update_status(self):
        """Aktualisiert beide Status und das Icon"""
        k3s_status = self.get_service_status("k3s")
        docker_status = self.get_service_status("docker")

        # K3s Status aktualisieren
        if k3s_status == "active":
            self.k3s_status_action.setText("Status: 🟢 Running")
        elif k3s_status == "inactive":
            self.k3s_status_action.setText("Status: 🔴 Stopped")
        else:
            self.k3s_status_action.setText(f"Status: 🟡 {k3s_status}")

        # Docker Status aktualisieren
        if docker_status == "active":
            self.docker_status_action.setText("Status: 🟢 Running")
        elif docker_status == "inactive":
            self.docker_status_action.setText("Status: 🔴 Stopped")
        else:
            self.docker_status_action.setText(f"Status: 🟡 {docker_status}")

        # Tooltip und Icon basierend auf kombiniertem Status
        tooltip_parts = []
        if k3s_status == "active":
            tooltip_parts.append("K3s: ✓")
        else:
            tooltip_parts.append("K3s: ✗")
        
        if docker_status == "active":
            tooltip_parts.append("Docker: ✓")
        else:
            tooltip_parts.append("Docker: ✗")

        self.setToolTip(" | ".join(tooltip_parts))

        # Icon-Farbe: Grün wenn beide laufen, sonst Schwarz
        if k3s_status == "active" and docker_status == "active":
            self.setIcon(self.create_status_icon(cow_color="#255BA3"))
        else:
            self.setIcon(self.create_status_icon(cow_color="#000000"))

    # K3s Kontrollfunktionen
    def start_k3s(self):
        try:
            subprocess.run(["pkexec", "systemctl", "start", "k3s"], check=True)
            self.showMessage("K3s", "K3s was started", QSystemTrayIcon.MessageIcon.Information)
            self.update_status()
        except subprocess.CalledProcessError:
            self.showMessage("K3s", "Error while starting", QSystemTrayIcon.MessageIcon.Critical)

    def stop_k3s(self):
        try:
            subprocess.run(["pkexec", "systemctl", "stop", "k3s"], check=True)
            self.showMessage("K3s", "K3s was stopped", QSystemTrayIcon.MessageIcon.Information)
            self.update_status()
        except subprocess.CalledProcessError:
            self.showMessage("K3s", "Error while stopping", QSystemTrayIcon.MessageIcon.Critical)

    def restart_k3s(self):
        try:
            subprocess.run(["pkexec", "systemctl", "restart", "k3s"], check=True)
            self.showMessage("K3s", "K3s was restarted", QSystemTrayIcon.MessageIcon.Information)
            self.update_status()
        except subprocess.CalledProcessError:
            self.showMessage("K3s", "Error while restarting", QSystemTrayIcon.MessageIcon.Critical)

    # Docker Kontrollfunktionen
    def start_docker(self):
        try:
            subprocess.run(["pkexec", "systemctl", "start", "docker"], check=True)
            self.showMessage("Docker", "Docker was started", QSystemTrayIcon.MessageIcon.Information)
            self.update_status()
        except subprocess.CalledProcessError:
            self.showMessage("Docker", "Error while starting", QSystemTrayIcon.MessageIcon.Critical)

    def stop_docker(self):
        try:
            subprocess.run(["pkexec", "systemctl", "stop", "docker"], check=True)
            self.showMessage("Docker", "Docker was stopped", QSystemTrayIcon.MessageIcon.Information)
            self.update_status()
        except subprocess.CalledProcessError:
            self.showMessage("Docker", "Error while stopping", QSystemTrayIcon.MessageIcon.Critical)

    def restart_docker(self):
        try:
            subprocess.run(["pkexec", "systemctl", "restart", "docker"], check=True)
            self.showMessage("Docker", "Docker was restarted", QSystemTrayIcon.MessageIcon.Information)
            self.update_status()
        except subprocess.CalledProcessError:
            self.showMessage("Docker", "Error while restarting", QSystemTrayIcon.MessageIcon.Critical)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    tray = K3sDockerTrayIcon()
    sys.exit(app.exec())
