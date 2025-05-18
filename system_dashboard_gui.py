"""
VitalViz - GUI System Monitoring Dashboard
------------------------------------------
A graphical system resource monitor displaying CPU, memory, 
disk usage, and network statistics with real-time charts.
"""

import tkinter as tk
from tkinter import ttk
import time
import threading
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import platform
from datetime import datetime

# Import monitoring functions from the original dashboard
import psutil
from system_dashboard import (
    get_cpu_usage_per_core, 
    get_memory_info, 
    get_disk_info,
    get_network_info,
    size_formatter
)

class SystemMonitorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("VitalViz - System Monitor")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # Set theme
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
        
        # Configure colors
        style.configure("TNotebook", background="#2e3440")
        style.configure("TFrame", background="#2e3440")
        style.configure("TLabel", background="#2e3440", foreground="#eceff4")
        
        # Data storage for historical plotting
        self.cpu_history = [[] for _ in range(len(get_cpu_usage_per_core()))]
        self.memory_history = []
        self.network_recv_history = []
        self.network_sent_history = []
        self.time_points = []
        
        # Track network stats for calculating rates
        self.prev_net_io = psutil.net_io_counters()
        self.prev_time = time.time()
        
        # Create header with system info
        self.create_header()
        
        # Create tabbed interface
        self.tab_control = ttk.Notebook(self.root)
        
        # CPU Tab
        self.cpu_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.cpu_tab, text="CPU")
        self.create_cpu_tab()
        
        # Memory Tab
        self.memory_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.memory_tab, text="Memory")
        self.create_memory_tab()
        
        # Disk Tab
        self.disk_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.disk_tab, text="Disk")
        self.create_disk_tab()
        
        # Network Tab
        self.network_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.network_tab, text="Network")
        self.create_network_tab()
        
        self.tab_control.pack(expand=1, fill="both")
        
        # Start monitoring
        self.running = True
        self.update_thread = threading.Thread(target=self.update_data)
        self.update_thread.daemon = True
        self.update_thread.start()
    
    def create_header(self):
        """Create header with system information"""
        header_frame = ttk.Frame(self.root, padding=10)
        header_frame.pack(fill="x")
        
        uname = platform.uname()
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        
        # System info
        system_label = ttk.Label(
            header_frame, 
            text=f"System: {uname.system} {uname.release} | "
                 f"Processor: {uname.processor} | "
                 f"Boot Time: {boot_time.strftime('%Y-%m-%d %H:%M:%S')}",
            font=("Arial", 10)
        )
        system_label.pack(anchor="w")
        
        # Create uptime display that will be updated
        self.uptime_label = ttk.Label(
            header_frame,
            text="Uptime: Calculating...",
            font=("Arial", 10)
        )
        self.uptime_label.pack(anchor="w")
    
    def create_cpu_tab(self):
        """Create CPU monitoring tab"""
        # CPU overview frame
        cpu_overview = ttk.Frame(self.cpu_tab, padding=10)
        cpu_overview.pack(fill="x")
        
        cpu_count = psutil.cpu_count(logical=True)
        physical_cores = psutil.cpu_count(logical=False)
        
        ttk.Label(
            cpu_overview,
            text=f"CPU Count: {cpu_count} logical, {physical_cores} physical cores",
            font=("Arial", 12, "bold")
        ).pack(anchor="w")
        
        # Create CPU usage progress bars
        self.cpu_bars_frame = ttk.Frame(self.cpu_tab, padding=10)
        self.cpu_bars_frame.pack(fill="both")
        
        self.cpu_bars = []
        self.cpu_labels = []
        
        for i in range(cpu_count):
            label = ttk.Label(self.cpu_bars_frame, text=f"Core {i}: 0%")
            label.grid(row=i, column=0, sticky="w", padx=5, pady=2)
            
            progressbar = ttk.Progressbar(self.cpu_bars_frame, length=300, maximum=100)
            progressbar.grid(row=i, column=1, padx=5, pady=2)
            
            self.cpu_bars.append(progressbar)
            self.cpu_labels.append(label)
        
        # CPU history graph
        self.cpu_fig = plt.Figure(figsize=(8, 4), dpi=100)
        self.cpu_subplot = self.cpu_fig.add_subplot(111)
        self.cpu_canvas = FigureCanvasTkAgg(self.cpu_fig, self.cpu_tab)
        self.cpu_canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
    
    def create_memory_tab(self):
        """Create memory monitoring tab"""
        # Memory overview frame
        memory_frame = ttk.Frame(self.memory_tab, padding=10)
        memory_frame.pack(fill="x")
        
        # Memory details with labels that will be updated
        mem_info = get_memory_info()
        
        details_frame = ttk.Frame(memory_frame)
        details_frame.pack(fill="x")
        
        # Create labels for memory info
        ttk.Label(details_frame, text="Total Memory:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.total_mem_label = ttk.Label(details_frame, text=size_formatter(mem_info["total"]))
        self.total_mem_label.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        ttk.Label(details_frame, text="Available:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.avail_mem_label = ttk.Label(details_frame, text=size_formatter(mem_info["available"]))
        self.avail_mem_label.grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        ttk.Label(details_frame, text="Used:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.used_mem_label = ttk.Label(details_frame, text=size_formatter(mem_info["used"]))
        self.used_mem_label.grid(row=2, column=1, sticky="w", padx=5, pady=2)
        
        ttk.Label(details_frame, text="Free:", font=("Arial", 10, "bold")).grid(row=3, column=0, sticky="w", padx=5, pady=2)
        self.free_mem_label = ttk.Label(details_frame, text=size_formatter(mem_info["free"]))
        self.free_mem_label.grid(row=3, column=1, sticky="w", padx=5, pady=2)
        
        # Memory usage progress bar
        ttk.Label(memory_frame, text="Memory Usage:", font=("Arial", 10, "bold")).pack(anchor="w", pady=(15, 5))
        self.memory_bar = ttk.Progressbar(memory_frame, length=400, maximum=100)
        self.memory_bar.pack(fill="x", padx=5)
        self.memory_percent_label = ttk.Label(memory_frame, text=f"{mem_info['percent']}%")
        self.memory_percent_label.pack(anchor="e", padx=5)
        
        # Memory history graph
        self.memory_fig = plt.Figure(figsize=(8, 4), dpi=100)
        self.memory_subplot = self.memory_fig.add_subplot(111)
        self.memory_canvas = FigureCanvasTkAgg(self.memory_fig, self.memory_tab)
        self.memory_canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
    
    def create_disk_tab(self):
        """Create disk monitoring tab"""
        disk_frame = ttk.Frame(self.disk_tab, padding=10)
        disk_frame.pack(fill="both", expand=True)
        
        # Create Treeview for disk info
        columns = ("Device", "Mount", "Type", "Total", "Used", "Free", "Usage")
        self.disk_tree = ttk.Treeview(disk_frame, columns=columns, show="headings")
        
        for col in columns:
            self.disk_tree.heading(col, text=col)
            if col in ["Device", "Mount", "Type"]:
                self.disk_tree.column(col, width=100, anchor="w")
            else:
                self.disk_tree.column(col, width=70, anchor="center")
        
        self.disk_tree.pack(fill="both", expand=True)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(disk_frame, orient="vertical", command=self.disk_tree.yview)
        self.disk_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
    
    def create_network_tab(self):
        """Create network monitoring tab"""
        network_frame = ttk.Frame(self.network_tab, padding=10)
        network_frame.pack(fill="x")
        
        # Network stats
        stats_frame = ttk.Frame(network_frame)
        stats_frame.pack(fill="x")
        
        # Create labels for network stats
        ttk.Label(stats_frame, text="Bytes Sent:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.bytes_sent_label = ttk.Label(stats_frame, text="0 B")
        self.bytes_sent_label.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        ttk.Label(stats_frame, text="Bytes Received:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.bytes_recv_label = ttk.Label(stats_frame, text="0 B")
        self.bytes_recv_label.grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        ttk.Label(stats_frame, text="Send Rate:", font=("Arial", 10, "bold")).grid(row=0, column=2, sticky="w", padx=5, pady=2)
        self.bytes_sent_rate_label = ttk.Label(stats_frame, text="0 B/s")
        self.bytes_sent_rate_label.grid(row=0, column=3, sticky="w", padx=5, pady=2)
        
        ttk.Label(stats_frame, text="Receive Rate:", font=("Arial", 10, "bold")).grid(row=1, column=2, sticky="w", padx=5, pady=2)
        self.bytes_recv_rate_label = ttk.Label(stats_frame, text="0 B/s")
        self.bytes_recv_rate_label.grid(row=1, column=3, sticky="w", padx=5, pady=2)
        
        # Network history graph
        self.network_fig = plt.Figure(figsize=(8, 4), dpi=100)
        self.network_subplot = self.network_fig.add_subplot(111)
        self.network_canvas = FigureCanvasTkAgg(self.network_fig, self.network_tab)
        self.network_canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
    
    def update_data(self):
        """Update all monitoring data in a separate thread"""
        MAX_HISTORY = 60  # Keep 60 data points (1 minute at 1 second intervals)
        
        while self.running:
            # Calculate time difference for network rates
            current_time = time.time()
            time_diff = current_time - self.prev_time
            
            # Get current system info
            cpu_usage = get_cpu_usage_per_core()
            memory_info = get_memory_info()
            disk_info = get_disk_info()
            current_net_io = get_network_info()
            
            # Update time points for graphs
            if len(self.time_points) >= MAX_HISTORY:
                self.time_points.pop(0)
            self.time_points.append(datetime.now().strftime("%H:%M:%S"))
            
            # Update CPU history
            for i, usage in enumerate(cpu_usage):
                if len(self.cpu_history[i]) >= MAX_HISTORY:
                    self.cpu_history[i].pop(0)
                self.cpu_history[i].append(usage)
            
            # Update memory history
            if len(self.memory_history) >= MAX_HISTORY:
                self.memory_history.pop(0)
            self.memory_history.append(memory_info["percent"])
            
            # Calculate network rates
            bytes_sent_per_sec = (current_net_io.bytes_sent - self.prev_net_io.bytes_sent) / time_diff
            bytes_recv_per_sec = (current_net_io.bytes_recv - self.prev_net_io.bytes_recv) / time_diff
            
            # Update network history
            if len(self.network_sent_history) >= MAX_HISTORY:
                self.network_sent_history.pop(0)
                self.network_recv_history.pop(0)
            
            self.network_sent_history.append(bytes_sent_per_sec)
            self.network_recv_history.append(bytes_recv_per_sec)
            
            # Schedule GUI updates
            self.root.after(0, self.update_ui_cpu, cpu_usage)
            self.root.after(0, self.update_ui_memory, memory_info)
            self.root.after(0, self.update_ui_disk, disk_info)
            self.root.after(0, self.update_ui_network, current_net_io, bytes_sent_per_sec, bytes_recv_per_sec)
            self.root.after(0, self.update_ui_system_info)
            
            # Update previous values
            self.prev_net_io = current_net_io
            self.prev_time = current_time
            
            time.sleep(1)
    
    def update_ui_cpu(self, cpu_usage):
        """Update CPU UI elements"""
        # Update progress bars
        for i, usage in enumerate(cpu_usage):
            if i < len(self.cpu_bars):
                self.cpu_bars[i]["value"] = usage
                self.cpu_labels[i].config(text=f"Core {i}: {usage:.1f}%")
        
        # Update graph
        self.cpu_subplot.clear()
        
        # Plot each CPU core
        for i, history in enumerate(self.cpu_history):
            if history:  # Only plot if we have data
                self.cpu_subplot.plot(range(len(history)), history, label=f"Core {i}")
        
        self.cpu_subplot.set_ylim(0, 100)
        self.cpu_subplot.set_title("CPU Usage History")
        self.cpu_subplot.set_ylabel("Usage %")
        self.cpu_subplot.set_xlabel("Time (seconds ago)")
        self.cpu_subplot.grid(True)
        
        # Only show legend if we have many cores
        if len(self.cpu_history) <= 8:
            self.cpu_subplot.legend(loc="upper left")
            
        self.cpu_fig.tight_layout()
        self.cpu_canvas.draw()
    
    def update_ui_memory(self, memory_info):
        """Update Memory UI elements"""
        # Update memory info labels
        self.total_mem_label.config(text=size_formatter(memory_info["total"]))
        self.avail_mem_label.config(text=size_formatter(memory_info["available"]))
        self.used_mem_label.config(text=size_formatter(memory_info["used"]))
        self.free_mem_label.config(text=size_formatter(memory_info["free"]))
        
        # Update progress bar
        self.memory_bar["value"] = memory_info["percent"]
        self.memory_percent_label.config(text=f"{memory_info['percent']:.1f}%")
        
        # Update graph
        self.memory_subplot.clear()
        if self.memory_history:
            x = range(len(self.memory_history))
            self.memory_subplot.plot(x, self.memory_history, 'b-')
            self.memory_subplot.fill_between(x, self.memory_history, alpha=0.3)
            
        self.memory_subplot.set_ylim(0, 100)
        self.memory_subplot.set_title("Memory Usage History")
        self.memory_subplot.set_ylabel("Usage %")
        self.memory_subplot.set_xlabel("Time (seconds ago)")
        self.memory_subplot.grid(True)
        
        self.memory_fig.tight_layout()
        self.memory_canvas.draw()
    
    def update_ui_disk(self, disk_info):
        """Update Disk UI elements"""
        # Clear existing data
        for item in self.disk_tree.get_children():
            self.disk_tree.delete(item)
        
        # Add disk info rows
        for disk in disk_info:
            values = (
                disk["device"],
                disk["mountpoint"],
                disk["fstype"],
                size_formatter(disk["total"]),
                size_formatter(disk["used"]),
                size_formatter(disk["free"]),
                f"{disk['percent']:.1f}%"
            )
            self.disk_tree.insert("", "end", values=values)
    
    def update_ui_network(self, net_io, bytes_sent_per_sec, bytes_recv_per_sec):
        """Update Network UI elements"""
        # Update network labels
        self.bytes_sent_label.config(text=size_formatter(net_io.bytes_sent))
        self.bytes_recv_label.config(text=size_formatter(net_io.bytes_recv))
        self.bytes_sent_rate_label.config(text=f"{size_formatter(bytes_sent_per_sec)}/s")
        self.bytes_recv_rate_label.config(text=f"{size_formatter(bytes_recv_per_sec)}/s")
        
        # Update graph
        self.network_subplot.clear()
        if self.network_sent_history and self.network_recv_history:
            x = range(len(self.network_sent_history))
            
            # Plot sent and received data
            self.network_subplot.plot(x, self.network_sent_history, 'r-', label='Sent')
            self.network_subplot.plot(x, self.network_recv_history, 'g-', label='Received')
            
        self.network_subplot.set_title("Network Traffic History")
        self.network_subplot.set_ylabel("Bytes/second")
        self.network_subplot.set_xlabel("Time (seconds ago)")
        self.network_subplot.grid(True)
        self.network_subplot.legend(loc="upper left")
        
        self.network_fig.tight_layout()
        self.network_canvas.draw()
    
    def update_ui_system_info(self):
        """Update system information in header"""
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        
        uptime_str = f"Uptime: {uptime.days} days, {uptime.seconds//3600} hours, {(uptime.seconds//60)%60} minutes"
        self.uptime_label.config(text=uptime_str)
    
    def on_closing(self):
        """Clean up when window is closed"""
        self.running = False
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = SystemMonitorGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()