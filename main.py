# main.py - Android App for NPOWER Inverter
import socket
import struct
import threading
import time
from datetime import datetime

from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.card import MDCard
from kivymd.uix.screen import MDScreen
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDFillRoundFlatButton
from kivy.clock import Clock

# KV Language String untuk UI
KV = '''
<ValueCard>:
    orientation: "vertical"
    size_hint: None, None
    size: "300dp", "80dp"
    padding: "10dp"
    spacing: "5dp"
    
    MDLabel:
        id: title_label
        text: root.title
        font_style: "H6"
        theme_text_color: "Primary"
        size_hint_y: None
        height: self.texture_size[1]
    
    MDLabel:
        id: value_label
        text: root.value
        font_style: "H4"
        theme_text_color: "Custom"
        text_color: root.value_color
        bold: True
        size_hint_y: None
        height: self.texture_size[1]

<MainScreen>:
    name: "main"
    
    MDBoxLayout:
        orientation: "vertical"
        padding: "10dp"
        spacing: "10dp"
        
        # Header
        MDBoxLayout:
            size_hint_y: None
            height: "60dp"
            spacing: "10dp"
            
            MDLabel:
                text: "NPOWER INVERTER"
                font_style: "H4"
                bold: True
                halign: "center"
                theme_text_color: "Primary"
            
            MDFillRoundFlatButton:
                id: conn_btn
                text: "DISCONNECTED"
                size_hint: None, None
                size: "150dp", "40dp"
                md_bg_color: 1, 0, 0, 1  # Red
                on_release: root.toggle_connection()
        
        # Configuration Card
        MDCard:
            orientation: "vertical"
            size_hint_y: None
            height: "140dp"
            padding: "10dp"
            spacing: "5dp"
            
            MDLabel:
                text: "Configuration"
                font_style: "H6"
                size_hint_y: None
                height: self.texture_size[1]
            
            MDBoxLayout:
                size_hint_y: None
                height: "40dp"
                spacing: "10dp"
                
                MDTextField:
                    id: ip_input
                    hint_text: "IP Address"
                    text: "11.11.11.254"
                    mode: "rectangle"
                    size_hint_x: 0.6
                
                MDTextField:
                    id: port_input
                    hint_text: "Port"
                    text: "8088"
                    mode: "rectangle"
                    size_hint_x: 0.4
            
            MDBoxLayout:
                size_hint_y: None
                height: "40dp"
                spacing: "10dp"
                
                MDTextField:
                    id: slave_input
                    hint_text: "Slave ID"
                    text: "3"
                    mode: "rectangle"
                    size_hint_x: 0.5
                
                MDFillRoundFlatButton:
                    text: "APPLY"
                    size_hint_x: 0.5
                    on_release: root.apply_config()
        
        # Scrollable values
        ScrollView:
            GridLayout:
                id: values_grid
                cols: 1
                size_hint_y: None
                height: self.minimum_height
                spacing: "10dp"
                padding: "5dp"
        
        # Status Bar
        MDBoxLayout:
            size_hint_y: None
            height: "40dp"
            spacing: "10dp"
            
            MDLabel:
                id: status_label
                text: "Configure and connect"
                font_style: "Body2"
                theme_text_color: "Secondary"
            
            MDLabel:
                id: time_label
                text: "--:--:--"
                font_style: "Body2"
                theme_text_color: "Secondary"
                halign: "right"
'''

class ValueCard(MDCard):
    """Custom card untuk menampilkan nilai"""
    def __init__(self, title="", value="--", color=(0, 0, 0, 1), **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.value = value
        self.value_color = color

class MainScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = None
        self.values = {}
        
        # Warna untuk setiap value
        self.colors = {
            'batt': (1, 0.42, 0.42, 1),      # Red
            'ac_v': (0.3, 0.8, 0.77, 1),     # Teal
            'ac_i': (0.27, 0.72, 0.82, 1),   # Blue
            'power': (1, 0.92, 0.65, 1),     # Yellow
            'load': (0.59, 0.81, 0.71, 1),   # Green
            'int_t': (0.99, 0.47, 0.66, 1),  # Pink
            'rad_t': (0.64, 0.58, 1, 1),     # Purple
        }
        
    def on_pre_enter(self):
        """Setup UI saat screen akan dimasuki"""
        self.create_value_cards()
        
    def create_value_cards(self):
        """Buat card untuk setiap value"""
        grid = self.ids.values_grid
        grid.clear_widgets()
        
        items = [
            ('batt', 'Battery Voltage', '--.- V'),
            ('ac_v', 'AC Voltage', '--.- V'),
            ('ac_i', 'AC Current', '--.- A'),
            ('power', 'AC Power', '---- W'),
            ('load', 'Load Status', 'Unknown'),
            ('int_t', 'Internal Temp', '--°C'),
            ('rad_t', 'Radiator Temp', '--°C'),
        ]
        
        for key, title, default in items:
            card = ValueCard(
                title=title,
                value=default,
                color=self.colors[key]
            )
            self.values[key] = card
            grid.add_widget(card)
    
    def toggle_connection(self):
        """Toggle koneksi"""
        if self.app.modbus.connected:
            self.disconnect()
        else:
            self.connect()
    
    def apply_config(self):
        """Apply konfigurasi baru"""
        try:
            ip = self.ids.ip_input.text.strip()
            port = int(self.ids.port_input.text.strip())
            slave = int(self.ids.slave_input.text.strip())
            
            self.app.modbus.update_config(ip, port, slave)
            self.ids.status_label.text = f"Config updated: {ip}:{port}"
            
        except ValueError:
            self.ids.status_label.text = "Invalid port or slave ID"
    
    def connect(self):
        """Connect ke inverter"""
        if self.app.modbus.connect():
            self.ids.conn_btn.text = "CONNECTED"
            self.ids.conn_btn.md_bg_color = (0, 1, 0, 1)  # Green
            self.ids.status_label.text = "Connected - Monitoring"
            
            # Start monitoring
            Clock.schedule_interval(self.update_values, 1.5)
        else:
            self.ids.status_label.text = "Connection failed"
    
    def disconnect(self):
        """Disconnect dari inverter"""
        self.app.modbus.disconnect()
        self.ids.conn_btn.text = "DISCONNECTED"
        self.ids.conn_btn.md_bg_color = (1, 0, 0, 1)  # Red
        self.ids.status_label.text = "Disconnected"
        
        # Stop monitoring
        Clock.unschedule(self.update_values)
        
        # Reset values
        for key in self.values:
            if key == 'batt':
                self.values[key].value = '--.- V'
            elif key == 'ac_v':
                self.values[key].value = '--.- V'
            elif key == 'ac_i':
                self.values[key].value = '--.- A'
            elif key == 'power':
                self.values[key].value = '---- W'
            elif key == 'load':
                self.values[key].value = 'Unknown'
            else:
                self.values[key].value = '--°C'
    
    def update_values(self, dt):
        """Update nilai-nilai dari inverter"""
        if not self.app.modbus.connected:
            return
        
        try:
            # Baca semua register
            results = self.app.modbus.read_all_registers()
            
            # Update UI
            if results['batt'] is not None:
                self.values['batt'].value = f"{results['batt']:.1f} V"
            
            if results['ac_v'] is not None:
                self.values['ac_v'].value = f"{results['ac_v']:.1f} V"
            
            if results['ac_i'] is not None:
                self.values['ac_i'].value = f"{results['ac_i']:.2f} A"
            
            if results['int_t'] is not None:
                self.values['int_t'].value = f"{results['int_t']:.0f}°C"
            
            if results['rad_t'] is not None:
                self.values['rad_t'].value = f"{results['rad_t']:.0f}°C"
            
            # Calculate power
            if results['ac_v'] and results['ac_i']:
                power = results['ac_v'] * results['ac_i']
                self.values['power'].value = f"{power:.0f} W"
                
                # Load status
                if power < 50:
                    load = "No Load"
                elif power < 300:
                    load = "Light Load"
                elif power < 1000:
                    load = "Medium Load"
                elif power < 2000:
                    load = "Heavy Load"
                else:
                    load = "FULL LOAD!"
                
                self.values['load'].value = load
                self.ids.status_label.text = f"Power: {power:.0f}W"
            else:
                self.values['power'].value = "---- W"
                self.values['load'].value = "AC OFF"
                self.ids.status_label.text = "AC Output Off"
            
            # Update time
            self.ids.time_label.text = datetime.now().strftime("%H:%M:%S")
            
        except Exception as e:
            self.ids.status_label.text = f"Error: {type(e).__name__}"

class ModbusTCPAndroid:
    """Modbus client untuk Android"""
    def __init__(self):
        self.ip = "11.11.11.254"
        self.port = 8088
        self.slave_id = 3
        self.sock = None
        self.connected = False
    
    def update_config(self, ip, port, slave_id):
        """Update configuration"""
        self.ip = ip
        self.port = port
        self.slave_id = slave_id
        self.disconnect()
    
    def connect(self):
        """Connect ke inverter"""
        try:
            if self.sock:
                self.sock.close()
            
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(2.0)
            self.sock.connect((self.ip, self.port))
            self.connected = True
            return True
        except:
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect"""
        if self.sock:
            self.sock.close()
            self.sock = None
        self.connected = False
    
    def read_register(self, addr):
        """Baca satu register"""
        if not self.connected:
            return None
        
        try:
            # Build frame
            frame = struct.pack(">BBHH", self.slave_id, 4, addr, 1)
            
            # Calculate CRC
            crc = 0xFFFF
            for b in frame:
                crc ^= b
                for _ in range(8):
                    if crc & 1:
                        crc = (crc >> 1) ^ 0xA001
                    else:
                        crc >>= 1
            
            frame += struct.pack("<H", crc)
            
            # Send and receive
            self.sock.sendall(frame)
            self.sock.settimeout(1.0)
            resp = self.sock.recv(256)
            
            if resp and len(resp) >= 5 and resp[1] == 4 and resp[2] == 2:
                value = (resp[3] << 8) | resp[4]
                return value / 100.0
            
            return None
        except:
            self.connected = False
            return None
    
    def read_all_registers(self):
        """Baca semua register yang diperlukan"""
        registers = {
            'batt': 0x3108,
            'ac_v': 0x310C,
            'ac_i': 0x310D,
            'int_t': 0x3110,
            'rad_t': 0x3111,
        }
        
        results = {}
        for key, addr in registers.items():
            results[key] = self.read_register(addr)
            time.sleep(0.05)  # Small delay
        
        return results

class NPowerApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"
        
        # Setup modbus client
        self.modbus = ModbusTCPAndroid()
        
        # Load KV string
        screen = Builder.load_string(KV)
        screen.app = self
        return screen
    
    def on_stop(self):
        """Cleanup saat app ditutup"""
        self.modbus.disconnect()

# =============================
# Buildozer spec file (buildozer.spec)
# =============================
'''
[app]
title = NPOWER Inverter
package.name = npowerinverter
package.domain = org.npower
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0
requirements = python3,kivy==2.1.0,kivymd==1.1.1,hostpython3
orientation = portrait
osx.python_version = 3
osx.kivy_version = 2.1.0
fullscreen = 0
android.permissions = INTERNET
android.api = 30
android.minapi = 21
android.sdk = 24
android.ndk = 23b
android.ndk_api = 21
android.gradle_dependencies = 'com.android.support:appcompat-v7:28.0.0'
p4a.branch = master
ios.kivy_ios_url = https://github.com/kivy/kivy-ios
ios.kivy_ios_branch = master
ios.ios_deploy_url = https://github.com/phonegap/ios-deploy
ios.ios_deploy_branch = 1.10.0
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
'''

# Run app
if __name__ == "__main__":
    NPowerApp().run()