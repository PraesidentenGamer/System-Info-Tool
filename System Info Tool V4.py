import sys
import psutil
import platform
import json
import csv
import time
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QProgressBar, QGroupBox,
    QGridLayout, QComboBox, QHBoxLayout, QPushButton, QFileDialog
)
from PyQt6.QtCore import QTimer, Qt
from datetime import timedelta
import pyqtgraph as pg


class SystemInfoApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("System Info Tool V4")
        self.setGeometry(100, 100, 800, 800)
        self.net_interfaces = psutil.net_if_stats().keys()
        self.selected_interface = list(self.net_interfaces)[0]
        self.cpu_history = [[] for _ in range(psutil.cpu_count(logical=True))]
        self.ram_history = []
        self.max_history = 60
        self.dark_mode = False
        self.init_ui()
        self.update_stats()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1000)

    def init_ui(self):
        layout = QVBoxLayout()

        # Uptime
        self.uptime_label = QLabel("Uptime: ...")
        layout.addWidget(self.uptime_label)

        # CPU Auslastung
        cpu_group = QGroupBox("CPU Auslastung")
        cpu_layout = QGridLayout()
        self.cpu_bars = []
        for i in range(psutil.cpu_count(logical=True)):
            label = QLabel(f"Kern {i}:")
            bar = QProgressBar()
            bar.setRange(0, 100)
            cpu_layout.addWidget(label, i, 0)
            cpu_layout.addWidget(bar, i, 1)
            self.cpu_bars.append(bar)
        cpu_group.setLayout(cpu_layout)
        layout.addWidget(cpu_group)

        # Live CPU Graph
        self.cpu_plot = pg.PlotWidget(title="CPU Verlauf")
        self.cpu_plot.addLegend()
        self.cpu_curves = [self.cpu_plot.plot(pen=pg.mkPen(i, width=2), name=f"Core {i}") for i in range(psutil.cpu_count(logical=True))]
        layout.addWidget(self.cpu_plot)

        # RAM
        ram_group = QGroupBox("Arbeitsspeicher")
        ram_layout = QGridLayout()
        self.ram_bar = QProgressBar()
        self.ram_label = QLabel()
        self.ram_details = QLabel()
        ram_layout.addWidget(self.ram_label, 0, 0, 1, 2)
        ram_layout.addWidget(self.ram_bar, 1, 0, 1, 2)
        ram_layout.addWidget(self.ram_details, 2, 0, 1, 2)
        ram_group.setLayout(ram_layout)
        layout.addWidget(ram_group)

        # RAM Graph
        self.ram_plot = pg.PlotWidget(title="RAM Verlauf")
        self.ram_curve = self.ram_plot.plot(pen=pg.mkPen("r", width=2), name="RAM")
        layout.addWidget(self.ram_plot)

        # Festplatten
        disk_group = QGroupBox("Festplatten")
        disk_layout = QVBoxLayout()
        self.disk_labels = []
        self.disk_bars = []
        for p in psutil.disk_partitions():
            label = QLabel()
            bar = QProgressBar()
            bar.setRange(0, 100)
            disk_layout.addWidget(label)
            disk_layout.addWidget(bar)
            self.disk_labels.append((p.device, label))
            self.disk_bars.append(bar)
        disk_group.setLayout(disk_layout)
        layout.addWidget(disk_group)

        # Netzwerk
        net_group = QGroupBox("Netzwerk")
        net_layout = QGridLayout()

        self.interface_selector = QComboBox()
        self.interface_selector.addItems(self.net_interfaces)
        self.interface_selector.currentTextChanged.connect(self.change_interface)

        self.net_sent_label = QLabel("Gesendet: ...")
        self.net_recv_label = QLabel("Empfangen: ...")

        net_layout.addWidget(QLabel("Interface:"), 0, 0)
        net_layout.addWidget(self.interface_selector, 0, 1)
        net_layout.addWidget(self.net_sent_label, 1, 0)
        net_layout.addWidget(self.net_recv_label, 2, 0)

        net_group.setLayout(net_layout)
        layout.addWidget(net_group)

        # Temperatur
        self.temp_label = QLabel("Temperatur: ...")
        layout.addWidget(self.temp_label)

        # Buttons
        btn_layout = QHBoxLayout()

        self.toggle_theme_btn = QPushButton("Dark Mode umschalten")
        self.toggle_theme_btn.clicked.connect(self.toggle_theme)
        btn_layout.addWidget(self.toggle_theme_btn)

        self.export_btn = QPushButton("Systemdaten exportieren")
        self.export_btn.clicked.connect(self.export_data)
        btn_layout.addWidget(self.export_btn)

        self.ping_btn = QPushButton("Diagnose: Ping google.com")
        self.ping_btn.clicked.connect(self.run_ping_test)
        btn_layout.addWidget(self.ping_btn)

        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.old_net = psutil.net_io_counters(pernic=True)

    def change_interface(self, iface):
        self.selected_interface = iface

    def toggle_theme(self):
        if self.dark_mode:
            self.setStyleSheet("")
        else:
            self.setStyleSheet("""
                QWidget {
                    background-color: #2d2d2d;
                    color: #ffffff;
                }
                QProgressBar {
                    border: 1px solid grey;
                    border-radius: 5px;
                    background: #444;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: #00CC66;
                }
            """)
        self.dark_mode = not self.dark_mode

    def export_data(self):
        info = {
            "cpu_percent": psutil.cpu_percent(percpu=True),
            "virtual_memory": psutil.virtual_memory()._asdict(),
            "disks": {p.device: psutil.disk_usage(p.device)._asdict() for p in psutil.disk_partitions() if p.fstype},
            "network": psutil.net_io_counters(pernic=True)[self.selected_interface]._asdict()
        }
        file_path, _ = QFileDialog.getSaveFileName(self, "Exportieren als JSON", "", "JSON-Dateien (*.json)")
        if file_path:
            with open(file_path, "w") as f:
                json.dump(info, f, indent=4)

    def run_ping_test(self):
        try:
            output = subprocess.check_output(["ping", "-n" if platform.system() == "Windows" else "-c", "4", "google.com"], text=True)
            self.temp_label.setText("Ping Ergebnis:\n" + output)
        except Exception as e:
            self.temp_label.setText(f"Ping Fehler: {e}")

    def update_stats(self):
        self.uptime_label.setText(f"Uptime: {timedelta(seconds=int(time.time() - psutil.boot_time()))}")

        cpu_percents = psutil.cpu_percent(percpu=True)
        for i, usage in enumerate(cpu_percents):
            self.cpu_bars[i].setValue(int(usage))
            self.cpu_history[i].append(usage)
            if len(self.cpu_history[i]) > self.max_history:
                self.cpu_history[i].pop(0)
            self.cpu_curves[i].setData(self.cpu_history[i])

        ram = psutil.virtual_memory()
        self.ram_bar.setValue(int(ram.percent))
        self.ram_label.setText(f"{ram.used // (1024**2)} MB / {ram.total // (1024**2)} MB ({ram.percent}%)")
        self.ram_details.setText(f"Frei: {ram.available // (1024**2)} MB, Cache: {getattr(ram, 'cached', 0) // (1024**2)} MB")
        self.ram_history.append(ram.percent)
        if len(self.ram_history) > self.max_history:
            self.ram_history.pop(0)
        self.ram_curve.setData(self.ram_history)

        for (device, label), bar in zip(self.disk_labels, self.disk_bars):
            try:
                usage = psutil.disk_usage(device)
                bar.setValue(int(usage.percent))
                label.setText(f"{device}: {usage.used // (1024**3)} GB / {usage.total // (1024**3)} GB ({usage.percent}%)")
            except:
                label.setText(f"{device}: Nicht verfügbar")
                bar.setValue(0)

        try:
            new = psutil.net_io_counters(pernic=True)[self.selected_interface]
            old = self.old_net[self.selected_interface]
            sent = (new.bytes_sent - old.bytes_sent) / (1024 ** 2)
            recv = (new.bytes_recv - old.bytes_recv) / (1024 ** 2)
            self.net_sent_label.setText(f"Gesendet: {sent:.2f} MB/s")
            self.net_recv_label.setText(f"Empfangen: {recv:.2f} MB/s")
            self.old_net[self.selected_interface] = new
        except:
            self.net_sent_label.setText("Gesendet: N/A")
            self.net_recv_label.setText("Empfangen: N/A")

        try:
            temps = psutil.sensors_temperatures()
            cpu_temp = temps.get('coretemp', temps.get('cpu-thermal', []))
            if cpu_temp:
                self.temp_label.setText("Temperatur: " + ", ".join([f"{s.label or 'CPU'}: {s.current} °C" for s in cpu_temp]))
            else:
                self.temp_label.setText("Temperatur: Keine Daten")
        except:
            self.temp_label.setText("Temperatur: Nicht unterstützt")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SystemInfoApp()
    window.show()
    sys.exit(app.exec())
