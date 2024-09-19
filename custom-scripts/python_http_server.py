#!/usr/bin/env python3

import time
import os
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

HOST_NAME = '127.0.0.1'
PORT_NUMBER = 8000
BUILDROOT_HOST = 'buildroot_ip'
BUILDROOT_USER = 'root'

def get_system_time():
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

def get_uptime():
    with open('/proc/uptime', 'r') as f:
        uptime_seconds = float(f.readline().split()[0])
    return int(uptime_seconds)

def get_cpu_info():
    cpu_info = {}
    with open('/proc/cpuinfo', 'r') as f:
        for line in f:
            if 'model name' in line:
                cpu_info['model'] = line.split(':')[1].strip()
            if 'cpu MHz' in line:
                cpu_info['speed'] = float(line.split(':')[1].strip())
                break
    return cpu_info

def get_cpu_usage():
    with open('/proc/stat', 'r') as f:
        fields = f.readline().split()
        idle_time = float(fields[4])
        total_time = sum(float(i) for i in fields[1:])
    return 100 * (1 - idle_time / total_time)

def get_memory_info():
    mem_info = {}
    with open('/proc/meminfo', 'r') as f:
        for line in f:
            if 'MemTotal' in line:
                mem_info['total'] = int(line.split()[1]) // 1024
            if 'MemAvailable' in line:
                mem_info['used'] = mem_info['total'] - (int(line.split()[1]) // 1024)
                break
    return mem_info

def get_os_version():
    with open('/proc/version', 'r') as f:
        return f.readline().strip()

def get_processes():
    processes = []
    for pid in os.listdir('/proc'):
        if pid.isdigit():
            try:
                with open(f'/proc/{pid}/comm', 'r') as f:
                    process_name = f.readline().strip()
                processes.append((pid, process_name))
            except IOError:
                continue
    return processes

def get_disk_info():
    with open('/proc/partitions', 'r') as f:
        disks = []
        for line in f.readlines()[2:]:
            parts = line.split()
            if len(parts) == 4:
                size_mb = int(parts[2]) // 1024
                name = parts[3]
                disks.append((name, size_mb))
    return disks

def get_usb_devices():
    usb_devices = []
    with open('/proc/bus/input/devices', 'r') as f:
        device = {}
        for line in f:
            if line.startswith('T:'):
                device = {}
            elif line.startswith('P:'):
                usb_devices.append(device)
            elif line.startswith('S:') and 'Product=' in line:
                device['product'] = line.split('=')[1].strip()
            elif line.startswith('S:') and 'Manufacturer=' in line:
                device['manufacturer'] = line.split('=')[1].strip()
            elif line.startswith('D:') and 'Port=' in line:
                device['port'] = line.split('=')[1].strip()
    return usb_devices

def get_network_adapters():
    adapters = []
    with open('/proc/net/dev', 'r') as f:
        for line in f.readlines()[2:]:
            iface = line.split()[0].replace(':', '')
            try:
                with open(f'/proc/net/if_inet6', 'r') as f:
                    for l in f:
                        if iface in l:
                            ip = l.split()[0]
                            adapters.append((iface, ip))
            except FileNotFoundError:
                pass
    return adapters

def get_buildroot_info(command):
    ssh_command = f"ssh {BUILDROOT_USER}@{BUILDROOT_HOST} '{command}'"
    result = subprocess.run(ssh_command, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

class MyHandler(BaseHTTPRequestHandler):
    def do_HEAD(s):
        s.send_response(200)
        s.send_header("Content-type", "text/html")
        s.end_headers()
    def do_GET(s):
        """Respond to a GET request."""
        s.send_response(200)
        s.send_header("Content-type", "text/html")
        s.end_headers()

        system_time = get_system_time()
        uptime = get_uptime()
        cpu_info = get_cpu_info()
        cpu_usage = get_cpu_usage()
        memory_info = get_memory_info()
        os_version = get_os_version()
        processes = get_processes()
        disks = get_disk_info()
        usb_devices = get_usb_devices()
        network_adapters = get_network_adapters()

        buildroot_uptime = get_buildroot_info('cat /proc/uptime')
        buildroot_cpu_info = get_buildroot_info('cat /proc/cpuinfo')
        buildroot_memory_info = get_buildroot_info('cat /proc/meminfo')

        response = f"""
        <html>
        <head><title>System Information</title></head>
        <body>
        <h1>System Information</h1>
        <p><strong>Date and Time:</strong> {system_time}</p>
        <p><strong>Uptime (seconds):</strong> {uptime}</p>
        <p><strong>CPU Model:</strong> {cpu_info['model']}</p>
        <p><strong>CPU Speed (MHz):</strong> {cpu_info['speed']}</p>
        <p><strong>CPU Usage (%):</strong> {cpu_usage:.2f}%</p>
        <p><strong>Memory Total (MB):</strong> {memory_info['total']} MB</p>
        <p><strong>Memory Used (MB):</strong> {memory_info['used']} MB</p>
        <p><strong>OS Version:</strong> {os_version}</p>
        <h2>Processes</h2>
        <ul>
        {''.join([f"<li>{pid}: {name}</li>" for pid, name in processes])}
        </ul>
        <h2>Disks</h2>
        <ul>
        {''.join([f"<li>{name}: {size_mb} MB</li>" for name, size_mb in disks])}
        </ul>
        <h2>USB Devices</h2>
        <ul>
        {''.join([f"<li>Product: {dev.get('product', 'N/A')}, Manufacturer: {dev.get('manufacturer', 'N/A')}, Port: {dev.get('port', 'N/A')}</li>" for dev in usb_devices])}
        </ul>
        <h2>Network Adapters</h2>
        <ul>
        {''.join([f"<li>{iface}: {ip}</li>" for iface, ip in network_adapters])}
        </ul>
        <h2>Buildroot Information</h2>
        <p><strong>Buildroot Uptime:</strong> {buildroot_uptime}</p>
        <p><strong>Buildroot CPU Info:</strong> {buildroot_cpu_info}</p>
        <p><strong>Buildroot Memory Info:</strong> {buildroot_memory_info}</p>
        </body>
        </html>
        """

        # Write the response to the client
        s.wfile.write(response.encode())

if __name__ == '__main__':
    httpd = HTTPServer((HOST_NAME, PORT_NUMBER), MyHandler)
    print("Server Starts - %s:%s" % (HOST_NAME, PORT_NUMBER))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print("Server Stops - %s:%s" % (HOST_NAME, PORT_NUMBER))