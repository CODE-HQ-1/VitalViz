"""
VitalViz - GUI System Monitoring Dashboard
------------------------------------------
A graphical system resource monitor displaying CPU, memory, 
disk usage, and network statistics with real-time charts.
"""

import customtkinter as ctk  # Modern alternative to ttk
import tkinter as tk
from tkinter import ttk, messagebox
import time
import threading
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk
)
import numpy as np
import platform
from datetime import datetime
import psutil

# Import monitoring functions from the original dashboard
from vitalviz_cli import (
    get_cpu_usage_per_core, 
    get_memory_info, 
    get_disk_info,
    get_network_info,
    size_formatter
)

# Handle optional dependencies
try:
    from tktooltip import ToolTip
    TOOLTIPS_AVAILABLE = True
except ImportError:
    TOOLTIPS_AVAILABLE = False
    print("Warning: tktooltip module not found. Tooltips will be disabled.")

try:
    import pystray
    from PIL import Image, ImageDraw
    SYSTRAY_AVAILABLE = True
except ImportError:
    SYSTRAY_AVAILABLE = False
    print("Warning: pystray or PIL modules not found. System tray icon will be disabled.")

try:
    from plyer import notification
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False
    print("Warning: plyer module not found. System notifications will be disabled.")

# Helper functions
def add_tooltip(widget, text):
    """Add tooltip to widget if tooltips are available"""
    if TOOLTIPS_AVAILABLE:
        ToolTip(widget, msg=text, delay=0.5, follow=True, bg="#333333", fg="white")

def notify(title, message):
    """Show notification if available"""
    if NOTIFICATIONS_AVAILABLE:
        notification.notify(
            title=title,
            message=message,
            app_name='VitalViz',
            timeout=10
        )

class SplashScreen(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("")
        self.geometry("400x250")
        self.overrideredirect(True)  # Remove window decorations
        
        # Center on screen
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        
        # Configure appearance
        self.configure(fg_color="#1e1e2e")
        
        # Add content
        ctk.CTkLabel(
            self, 
            text="VitalViz",
            font=("Arial", 28, "bold"),
            text_color="#89b4fa"
        ).pack(pady=(40, 10))
        
        ctk.CTkLabel(
            self,
            text="System Monitoring Dashboard",
            font=("Arial", 14),
            text_color="#cdd6f4"
        ).pack(pady=5)
        
        # Progress bar
        self.progress = ctk.CTkProgressBar(self, width=300)
        self.progress.pack(pady=20)
        self.progress.set(0)
        
        ctk.CTkLabel(
            self,
            text="Loading system information...",
            font=("Arial", 10),
            text_color="#a6adc8"
        ).pack(pady=5)
        
        # Start progress animation
        self.progress_value = 0
        self.animate_progress()
    
    def animate_progress(self):
        """Animate progress bar"""
        if self.progress_value < 1:
            self.progress_value += 0.02
            self.progress.set(self.progress_value)
            self.after(10, self.animate_progress)
        else:
            self.after(500, self.destroy)

class SystemMonitorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("VitalViz - System Monitor")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # Initialize settings
        self.update_interval = 1
        self.max_history = 60
        self.enable_notifications = True
        
        # Set theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Add color theme support
        self.themes = {
            "dark": {
                "bg": "#1e1e2e",
                "fg": "#cdd6f4",
                "accent": "#89b4fa",
                "warning": "#f9e2af",
                "critical": "#f38ba8"
            },
            "light": {
                "bg": "#eff1f5",
                "fg": "#4c4f69",
                "accent": "#1e66f5",
                "warning": "#df8e1d",
                "critical": "#d20f39"
            }
        }
        self.current_theme = "dark"  # Default theme
        
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
        self.tab_control = ctk.CTkTabview(self.root)
        self.tab_control.pack(expand=1, fill="both")
        
        # Dashboard Tab
        self.dashboard_tab = self.tab_control.add("Dashboard")
        self.create_dashboard_tab()
        
        # CPU Tab
        self.cpu_tab = self.tab_control.add("CPU")
        self.create_cpu_tab()
        
        # Memory Tab
        self.memory_tab = self.tab_control.add("Memory")
        self.create_memory_tab()
        
        # Disk Tab
        self.disk_tab = self.tab_control.add("Disk")
        self.create_disk_tab()
        
        # Network Tab
        self.network_tab = self.tab_control.add("Network")
        self.create_network_tab()
        
        # Add process monitoring tab
        self.processes_tab = self.tab_control.add("Processes")
        self.create_processes_tab()
        
        # Start monitoring
        self.running = True
        self.update_thread = threading.Thread(target=self.update_data)
        self.update_thread.daemon = True
        self.update_thread.start()
        
        # Create system tray icon
        self.create_system_tray()
        
        # Create menubar
        self.create_menubar()
    
    def create_header(self):
        """Create header with system information"""
        header_frame = ctk.CTkFrame(self.root, corner_radius=0)
        header_frame.pack(fill="x")
        
        # Top bar with theme toggle
        top_bar = ctk.CTkFrame(header_frame)
        top_bar.pack(fill="x", pady=(0, 5))
        
        # Add theme toggle
        self.theme_switch_var = ctk.StringVar(value="dark")
        theme_switch = ctk.CTkSwitch(
            top_bar, 
            text="Dark Mode",
            command=self.toggle_theme,
            variable=self.theme_switch_var,
            onvalue="dark",
            offvalue="light"
        )
        theme_switch.pack(side="right", padx=10)
        
        # System info
        uname = platform.uname()
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        
        system_label = ctk.CTkLabel(
            header_frame, 
            text=f"System: {uname.system} {uname.release} | "
                 f"Processor: {uname.processor} | "
                 f"Boot Time: {boot_time.strftime('%Y-%m-%d %H:%M:%S')}",
            font=("Arial", 10)
        )
        system_label.pack(anchor="w", padx=10)
        
        # Create uptime display that will be updated
        self.uptime_label = ctk.CTkLabel(
            header_frame,
            text="Uptime: Calculating...",
            font=("Arial", 10)
        )
        self.uptime_label.pack(anchor="w", padx=10)
    
    def create_cpu_tab(self):
        """Create CPU monitoring tab"""
        # CPU overview frame
        cpu_overview = ctk.CTkFrame(self.cpu_tab)
        cpu_overview.pack(fill="x", padx=10, pady=10)
        
        cpu_count = psutil.cpu_count(logical=True)
        physical_cores = psutil.cpu_count(logical=False)
        
        ctk.CTkLabel(
            cpu_overview,
            text=f"CPU Count: {cpu_count} logical, {physical_cores} physical cores",
            font=("Arial", 12, "bold")
        ).pack(anchor="w", padx=10, pady=5)
        
        # Create CPU usage progress bars
        self.cpu_bars_frame = ctk.CTkFrame(self.cpu_tab)
        self.cpu_bars_frame.pack(fill="both", padx=10, pady=5)
        
        self.cpu_bars = []
        self.cpu_labels = []
        
        for i in range(cpu_count):
            label = ctk.CTkLabel(self.cpu_bars_frame, text=f"Core {i}: 0%")
            label.grid(row=i, column=0, sticky="w", padx=5, pady=2)
            
            # Fixed: Removed max_value parameter which is not supported
            progressbar = ctk.CTkProgressBar(self.cpu_bars_frame, width=300)
            progressbar.grid(row=i, column=1, padx=5, pady=2)
            progressbar.set(0)  # Set initial value to 0 (values range from 0 to 1)
            
            self.cpu_bars.append(progressbar)
            self.cpu_labels.append(label)
        
        # CPU history graph
        self.cpu_fig = plt.Figure(figsize=(8, 4), dpi=100)
        self.cpu_subplot = self.cpu_fig.add_subplot(111)
        self.cpu_canvas = FigureCanvasTkAgg(self.cpu_fig, self.cpu_tab)
        self.cpu_canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        
        # CPU toolbar for graph navigation
        self.cpu_toolbar_frame = ttk.Frame(self.cpu_tab)
        self.cpu_toolbar_frame.pack(fill="x")
        self.cpu_toolbar = NavigationToolbar2Tk(self.cpu_canvas, self.cpu_toolbar_frame)
        self.cpu_toolbar.update()
    
    def create_memory_tab(self):
        """Create memory monitoring tab"""
        # Memory overview frame
        memory_frame = ctk.CTkFrame(self.memory_tab)
        memory_frame.pack(fill="x", padx=10, pady=10)
        
        # Memory details with labels that will be updated
        mem_info = get_memory_info()
        
        details_frame = ctk.CTkFrame(memory_frame)
        details_frame.pack(fill="x", padx=10, pady=10)
        
        # Create labels for memory info
        ctk.CTkLabel(details_frame, text="Total Memory:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.total_mem_label = ctk.CTkLabel(details_frame, text=size_formatter(mem_info["total"]))
        self.total_mem_label.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        ctk.CTkLabel(details_frame, text="Available:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.avail_mem_label = ctk.CTkLabel(details_frame, text=size_formatter(mem_info["available"]))
        self.avail_mem_label.grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        ctk.CTkLabel(details_frame, text="Used:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.used_mem_label = ctk.CTkLabel(details_frame, text=size_formatter(mem_info["used"]))
        self.used_mem_label.grid(row=2, column=1, sticky="w", padx=5, pady=2)
        
        ctk.CTkLabel(details_frame, text="Free:", font=("Arial", 10, "bold")).grid(row=3, column=0, sticky="w", padx=5, pady=2)
        self.free_mem_label = ctk.CTkLabel(details_frame, text=size_formatter(mem_info["free"]))
        self.free_mem_label.grid(row=3, column=1, sticky="w", padx=5, pady=2)
        
        # Memory usage progress bar
        ctk.CTkLabel(memory_frame, text="Memory Usage:", font=("Arial", 10, "bold")).pack(anchor="w", pady=(15, 5), padx=10)
        # Fixed: Removed max_value parameter
        self.memory_bar = ctk.CTkProgressBar(memory_frame, width=400)
        self.memory_bar.pack(fill="x", padx=15)
        self.memory_bar.set(mem_info["percent"] / 100)  # Set value as fraction of 1
        self.memory_percent_label = ctk.CTkLabel(memory_frame, text=f"{mem_info['percent']}%")
        self.memory_percent_label.pack(anchor="e", padx=15)
        
        # Add tooltip to memory usage bar
        add_tooltip(self.memory_bar, "Current RAM usage percentage")
        
        # Memory history graph
        self.memory_fig = plt.Figure(figsize=(8, 4), dpi=100)
        self.memory_subplot = self.memory_fig.add_subplot(111)
        self.memory_canvas = FigureCanvasTkAgg(self.memory_fig, self.memory_tab)
        self.memory_canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
    
    def create_disk_tab(self):
        """Create disk monitoring tab"""
        disk_frame = ctk.CTkFrame(self.disk_tab)
        disk_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create regular ttk Treeview for disk info
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
        network_frame = ctk.CTkFrame(self.network_tab)
        network_frame.pack(fill="x", padx=10, pady=10)
        
        # Network stats
        stats_frame = ctk.CTkFrame(network_frame)
        stats_frame.pack(fill="x", padx=10, pady=10)
        
        # Create labels for network stats
        ctk.CTkLabel(stats_frame, text="Bytes Sent:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.bytes_sent_label = ctk.CTkLabel(stats_frame, text="0 B")
        self.bytes_sent_label.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        
        ctk.CTkLabel(stats_frame, text="Bytes Received:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.bytes_recv_label = ctk.CTkLabel(stats_frame, text="0 B")
        self.bytes_recv_label.grid(row=1, column=1, sticky="w", padx=5, pady=2)
        
        ctk.CTkLabel(stats_frame, text="Send Rate:", font=("Arial", 10, "bold")).grid(row=0, column=2, sticky="w", padx=5, pady=2)
        self.bytes_sent_rate_label = ctk.CTkLabel(stats_frame, text="0 B/s")
        self.bytes_sent_rate_label.grid(row=0, column=3, sticky="w", padx=5, pady=2)
        
        ctk.CTkLabel(stats_frame, text="Receive Rate:", font=("Arial", 10, "bold")).grid(row=1, column=2, sticky="w", padx=5, pady=2)
        self.bytes_recv_rate_label = ctk.CTkLabel(stats_frame, text="0 B/s")
        self.bytes_recv_rate_label.grid(row=1, column=3, sticky="w", padx=5, pady=2)
        
        # Network history graph
        self.network_fig = plt.Figure(figsize=(8, 4), dpi=100)
        self.network_subplot = self.network_fig.add_subplot(111)
        self.network_canvas = FigureCanvasTkAgg(self.network_fig, self.network_tab)
        self.network_canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
    
    def create_processes_tab(self):
        """Create process monitoring tab"""
        process_frame = ttk.Frame(self.processes_tab, padding=10)
        process_frame.pack(fill="both", expand=True)
        
        # Controls frame
        controls_frame = ttk.Frame(process_frame)
        controls_frame.pack(fill="x", pady=5)
        
        ttk.Label(controls_frame, text="Sort by:").pack(side="left", padx=5)
        self.sort_var = tk.StringVar(value="CPU")
        sort_options = ttk.Combobox(controls_frame, textvariable=self.sort_var, 
                                  values=["CPU", "Memory", "Name", "PID"], width=10)
        sort_options.pack(side="left", padx=5)
        
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_processes)
        ttk.Label(controls_frame, text="Search:").pack(side="left", padx=(20, 5))
        ttk.Entry(controls_frame, textvariable=self.search_var, width=20).pack(side="left", padx=5)
        
        # Process list with treeview
        columns = ("PID", "Name", "CPU %", "Memory %", "Status")
        self.process_tree = ttk.Treeview(process_frame, columns=columns, show="headings")
        
        for col in columns:
            self.process_tree.heading(col, text=col)
            width = 70 if col in ["PID", "CPU %", "Memory %"] else 200
            self.process_tree.column(col, width=width)
        
        self.process_tree.pack(fill="both", expand=True)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(process_frame, orient="vertical", command=self.process_tree.yview)
        self.process_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        
        # Context menu
        self.process_menu = tk.Menu(self.root, tearoff=0)
        self.process_menu.add_command(label="End Process", command=self.end_selected_process)
        self.process_menu.add_command(label="Show Details", command=self.show_process_details)
        
        self.process_tree.bind("<Button-3>", self.show_process_menu)
    
    def create_dashboard_tab(self):
        """Create dashboard overview tab"""
        dashboard_frame = ctk.CTkFrame(self.dashboard_tab)
        dashboard_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create grid layout
        dashboard_frame.columnconfigure(0, weight=1)
        dashboard_frame.columnconfigure(1, weight=1)
        dashboard_frame.rowconfigure(0, weight=1)
        dashboard_frame.rowconfigure(1, weight=1)
        
        # CPU summary panel
        cpu_panel = ctk.CTkFrame(dashboard_frame)
        cpu_panel.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        ctk.CTkLabel(cpu_panel, text="CPU Usage", font=("Arial", 14, "bold")).pack(pady=5)
        
        # CPU gauge (circular progress bar)
        self.cpu_gauge_frame = ctk.CTkFrame(cpu_panel)
        self.cpu_gauge_frame.pack(fill="both", expand=True)
        
        self.cpu_fig_gauge = plt.Figure(figsize=(3, 3), dpi=100)
        self.cpu_subplot_gauge = self.cpu_fig_gauge.add_subplot(111, polar=True)
        self.cpu_canvas_gauge = FigureCanvasTkAgg(self.cpu_fig_gauge, self.cpu_gauge_frame)
        self.cpu_canvas_gauge.get_tk_widget().pack(fill="both", expand=True)
        
        self.cpu_value_label = ctk.CTkLabel(cpu_panel, text="0%", font=("Arial", 20))
        self.cpu_value_label.pack(pady=5)
        
        # Memory summary panel
        memory_panel = ctk.CTkFrame(dashboard_frame)
        memory_panel.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        
        ctk.CTkLabel(memory_panel, text="Memory Usage", font=("Arial", 14, "bold")).pack(pady=5)
        
        # Memory gauge
        self.memory_gauge_frame = ctk.CTkFrame(memory_panel)
        self.memory_gauge_frame.pack(fill="both", expand=True)
        
        self.memory_fig_gauge = plt.Figure(figsize=(3, 3), dpi=100)
        self.memory_subplot_gauge = self.memory_fig_gauge.add_subplot(111, polar=True)
        self.memory_canvas_gauge = FigureCanvasTkAgg(self.memory_fig_gauge, self.memory_gauge_frame)
        self.memory_canvas_gauge.get_tk_widget().pack(fill="both", expand=True)
        
        self.memory_value_label = ctk.CTkLabel(memory_panel, text="0%", font=("Arial", 20))
        self.memory_value_label.pack(pady=5)
        
        # Network summary panel
        network_panel = ctk.CTkFrame(dashboard_frame)
        network_panel.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        
        ctk.CTkLabel(network_panel, text="Network Traffic", font=("Arial", 14, "bold")).pack(pady=5)
        
        # Network rates
        self.network_down_label = ctk.CTkLabel(network_panel, text="↓ 0 B/s", font=("Arial", 16))
        self.network_down_label.pack(pady=5)
        
        self.network_up_label = ctk.CTkLabel(network_panel, text="↑ 0 B/s", font=("Arial", 16))
        self.network_up_label.pack(pady=5)
        
        # Disk summary panel
        disk_panel = ctk.CTkFrame(dashboard_frame)
        disk_panel.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")
        
        ctk.CTkLabel(disk_panel, text="Disk Usage", font=("Arial", 14, "bold")).pack(pady=5)
        
        # Will contain disk usage summary
        self.disk_summary_frame = ctk.CTkFrame(disk_panel)
        self.disk_summary_frame.pack(fill="both", expand=True)
    
    def create_system_tray(self):
        """Create system tray icon if available"""
        if not SYSTRAY_AVAILABLE:
            return
        
        # Create icon image
        icon_size = 64
        image = Image.new('RGB', (icon_size, icon_size), color=(0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Draw a simple CPU icon
        draw.rectangle([10, 10, 54, 54], fill="#4c78db", outline="white", width=2)
        
        # Create icon menu
        menu = (
            pystray.MenuItem('Show', self.show_window),
            pystray.MenuItem('Exit', self.exit_app)
        )
        
        self.tray_icon = pystray.Icon("vitalviz", image, "VitalViz", menu)
    
    def create_menubar(self):
        """Create application menubar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Settings", command=self.create_settings_dialog)
        file_menu.add_command(label="Export Data", command=self.export_data)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        
        self.always_on_top = tk.BooleanVar(value=False)
        view_menu.add_checkbutton(label="Always On Top", variable=self.always_on_top,
                                  command=self.toggle_always_on_top)
        view_menu.add_separator()
        view_menu.add_command(label="Reset Graphs", command=self.reset_graphs)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
    
    def update_data(self):
        """Update all monitoring data in a separate thread"""
        MAX_HISTORY = 60  # Keep 60 data points (1 minute at 1 second intervals)
        
        while self.running:
            try:
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
                self.root.after(0, self.update_dashboard, cpu_usage, memory_info, current_net_io, bytes_sent_per_sec, bytes_recv_per_sec)
                
                # Check thresholds for notifications
                if NOTIFICATIONS_AVAILABLE and self.enable_notifications:
                    self.check_thresholds(cpu_usage, memory_info)
                
                # Update previous values
                self.prev_net_io = current_net_io
                self.prev_time = current_time
            
            except Exception as e:
                print(f"Error in update thread: {e}")
            
            time.sleep(self.update_interval)
    
    def update_ui_cpu(self, cpu_usage):
        """Update CPU UI elements"""
        # Update progress bars
        for i, usage in enumerate(cpu_usage):
            if i < len(self.cpu_bars):
                self.cpu_bars[i].set(usage / 100)  # Convert percentage to 0-1 range
                self.cpu_labels[i].configure(text=f"Core {i}: {usage:.1f}%")
        
        # Update graph
        if hasattr(self, 'cpu_subplot') and hasattr(self, 'cpu_canvas'):
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
            
            # Only show legend if we have few cores
            if len(self.cpu_history) <= 8:
                self.cpu_subplot.legend(loc="upper left")
                
            self.cpu_fig.tight_layout()
            self.cpu_canvas.draw()
    
    def update_ui_memory(self, memory_info):
        """Update Memory UI elements"""
        # Update memory info labels
        if hasattr(self, 'total_mem_label'):
            self.total_mem_label.configure(text=size_formatter(memory_info["total"]))
        if hasattr(self, 'avail_mem_label'):
            self.avail_mem_label.configure(text=size_formatter(memory_info["available"]))
        if hasattr(self, 'used_mem_label'):
            self.used_mem_label.configure(text=size_formatter(memory_info["used"]))
        if hasattr(self, 'free_mem_label'):
            self.free_mem_label.configure(text=size_formatter(memory_info["free"]))
        
        # Update progress bar - use 0-1 range for CTkProgressBar
        if hasattr(self, 'memory_bar'):
            self.memory_bar.set(memory_info["percent"] / 100)
        if hasattr(self, 'memory_percent_label'):
            self.memory_percent_label.configure(text=f"{memory_info['percent']:.1f}%")
        
        # Update graph
        if hasattr(self, 'memory_subplot') and hasattr(self, 'memory_canvas'):
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
        if hasattr(self, 'bytes_sent_label'):
            self.bytes_sent_label.configure(text=size_formatter(net_io.bytes_sent))
        if hasattr(self, 'bytes_recv_label'):
            self.bytes_recv_label.configure(text=size_formatter(net_io.bytes_recv))
        if hasattr(self, 'bytes_sent_rate_label'):
            self.bytes_sent_rate_label.configure(text=f"{size_formatter(bytes_sent_per_sec)}/s")
        if hasattr(self, 'bytes_recv_rate_label'):
            self.bytes_recv_rate_label.configure(text=f"{size_formatter(bytes_recv_per_sec)}/s")
        
        # Update graph
        if hasattr(self, 'network_subplot') and hasattr(self, 'network_canvas'):
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
        self.uptime_label.configure(text=uptime_str)
    
    def update_dashboard(self, cpu_usage, memory_info, net_io, bytes_sent_per_sec, bytes_recv_per_sec):
        """Update dashboard overview panel"""
        # Update CPU gauge
        avg_cpu = sum(cpu_usage) / len(cpu_usage)
        self.update_gauge(self.cpu_subplot_gauge, avg_cpu)
        self.cpu_value_label.configure(text=f"{avg_cpu:.1f}%")
        
        # Update Memory gauge
        self.update_gauge(self.memory_subplot_gauge, memory_info["percent"])
        self.memory_value_label.configure(text=f"{memory_info['percent']:.1f}%")
        
        # Update Network labels
        self.network_down_label.configure(text=f"↓ {size_formatter(bytes_recv_per_sec)}/s")
        self.network_up_label.configure(text=f"↑ {size_formatter(bytes_sent_per_sec)}/s")
        
        # Redraw canvases
        self.cpu_canvas_gauge.draw()
        self.memory_canvas_gauge.draw()
    
    def update_gauge(self, subplot, value):
        """Update a gauge (polar plot) with a value"""
        subplot.clear()
        
        # Background ring (gray)
        subplot.barh(0, 100, height=0.6, color='gray', alpha=0.3)
        
        # Foreground ring (colored by value)
        if value < 60:
            color = 'green'
        elif value < 80:
            color = 'orange'
        else:
            color = 'red'
        
        subplot.barh(0, value, height=0.6, color=color)
        
        # Remove axis ticks and labels
        subplot.set_xticks([])
        subplot.set_yticks([])
        
        # Only show necessary spines
        for spine in subplot.spines.values():
            spine.set_visible(False)
    
    def show_window(self):
        """Show window from system tray"""
        if SYSTRAY_AVAILABLE:
            self.tray_icon.stop()
            self.root.after(0, self.root.deiconify)
    
    def minimize_to_tray(self):
        """Minimize to system tray"""
        if SYSTRAY_AVAILABLE:
            self.root.withdraw()
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
    
    def exit_app(self):
        """Exit application from tray"""
        if SYSTRAY_AVAILABLE:
            self.tray_icon.stop()
        self.on_closing()
    
    def check_thresholds(self, cpu_usage, memory_info):
        """Check if any resources exceed thresholds and notify"""
        # CPU threshold
        avg_cpu = sum(cpu_usage) / len(cpu_usage)
        if avg_cpu > 90 and not hasattr(self, 'cpu_notified'):
            notify('VitalViz Alert', 'CPU usage is extremely high (>90%)')
            self.cpu_notified = True
        elif avg_cpu < 70 and hasattr(self, 'cpu_notified'):
            delattr(self, 'cpu_notified')
            
        # Memory threshold
        if memory_info["percent"] > 85 and not hasattr(self, 'memory_notified'):
            notify('VitalViz Alert', 'Memory usage is high (>85%)')
            self.memory_notified = True
        elif memory_info["percent"] < 75 and hasattr(self, 'memory_notified'):
            delattr(self, 'memory_notified')
    
    def toggle_theme(self):
        """Toggle between light and dark theme"""
        new_theme = self.theme_switch_var.get()
        self.current_theme = new_theme
        ctk.set_appearance_mode(new_theme)
        
        # Update matplotlib style
        if new_theme == "dark":
            plt.style.use('dark_background')
        else:
            plt.style.use('default')
        
        # Redraw all charts
        try:
            self.update_ui_cpu(get_cpu_usage_per_core())
            self.update_ui_memory(get_memory_info())
            self.update_ui_network(get_network_info(), 0, 0)
            self.update_dashboard(get_cpu_usage_per_core(), get_memory_info(), 
                              get_network_info(), 0, 0)
        except Exception as e:
            print(f"Error updating UI after theme change: {e}")
    
    def apply_theme(self):
        """Apply the selected theme"""
        ctk.set_appearance_mode(self.current_theme)
        
        # Update matplotlib style
        if self.current_theme == "dark":
            plt.style.use('dark_background')
        else:
            plt.style.use('default')
    
    def toggle_always_on_top(self):
        """Toggle always on top setting"""
        self.root.attributes('-topmost', self.always_on_top.get())
    
    def reset_graphs(self):
        """Reset all graph history data"""
        self.cpu_history = [[] for _ in range(len(get_cpu_usage_per_core()))]
        self.memory_history = []
        self.network_recv_history = []
        self.network_sent_history = []
        self.time_points = []
        messagebox.showinfo("Graphs Reset", "All graph history has been cleared.")
    
    def show_about(self):
        """Show about dialog"""
        about_dialog = ctk.CTkToplevel(self.root)
        about_dialog.title("About VitalViz")
        about_dialog.geometry("400x300")
        about_dialog.resizable(False, False)
        about_dialog.transient(self.root)
        about_dialog.grab_set()
        
        ctk.CTkLabel(
            about_dialog, 
            text="VitalViz",
            font=("Arial", 24, "bold")
        ).pack(pady=(20, 5))
        
        ctk.CTkLabel(
            about_dialog,
            text="System Monitoring Dashboard",
            font=("Arial", 14)
        ).pack(pady=5)
        
        ctk.CTkLabel(
            about_dialog,
            text=f"Version 1.0\n\nCopyright © 2025",
            font=("Arial", 12)
        ).pack(pady=20)
        
        ctk.CTkButton(
            about_dialog, 
            text="Close", 
            command=about_dialog.destroy
        ).pack(pady=20)
    
    def filter_processes(self, *args):
        """Filter process list by search term"""
        search_term = self.search_var.get().lower()
        # Implementation to be added
    
    def show_process_menu(self, event):
        """Show context menu for process"""
        if SYSTRAY_AVAILABLE:
            self.process_menu.post(event.x_root, event.y_root)
    
    def end_selected_process(self):
        """End the selected process"""
        selected = self.process_tree.selection()
        if not selected:
            return
        
        pid = self.process_tree.item(selected[0])['values'][0]
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            messagebox.showinfo("Process Terminated", f"Process {pid} has been terminated.")
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            messagebox.showerror("Error", f"Could not terminate process: {str(e)}")
    
    def show_process_details(self):
        """Show details for the selected process"""
        selected = self.process_tree.selection()
        if not selected:
            return
        
        # Implementation to be added
    
    def create_settings_dialog(self):
        """Create settings dialog window"""
        settings_win = ctk.CTkToplevel(self.root)
        settings_win.title("VitalViz Settings")
        settings_win.geometry("400x300")
        settings_win.resizable(False, False)
        settings_win.transient(self.root)
        settings_win.grab_set()
        
        # Theme selection
        ctk.CTkLabel(settings_win, text="Theme:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        theme_var = ctk.StringVar(value=self.current_theme.capitalize())
        theme_combo = ctk.CTkComboBox(settings_win, values=["Dark", "Light"], variable=theme_var)
        theme_combo.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        
        # Update frequency
        ctk.CTkLabel(settings_win, text="Update interval (seconds):").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        interval_var = ctk.IntVar(value=self.update_interval)
        interval_spin = ctk.CTkEntry(settings_win, textvariable=interval_var, width=50)
        interval_spin.grid(row=1, column=1, padx=10, pady=10, sticky="w")
        
        # History length
        ctk.CTkLabel(settings_win, text="History length (seconds):").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        history_var = ctk.IntVar(value=self.max_history)
        history_spin = ctk.CTkEntry(settings_win, textvariable=history_var, width=50)
        history_spin.grid(row=2, column=1, padx=10, pady=10, sticky="w")
        
        # Enable notifications checkbox
        notifications_var = ctk.BooleanVar(value=self.enable_notifications)
        notifications_check = ctk.CTkCheckBox(settings_win, text="Enable notifications", variable=notifications_var)
        notifications_check.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="w")
        
        # Buttons
        def save_settings():
            self.current_theme = theme_var.get().lower()
            self.update_interval = int(interval_var.get())
            self.max_history = int(history_var.get())
            self.enable_notifications = notifications_var.get()
            self.apply_theme()
            settings_win.destroy()
        
        ctk.CTkButton(settings_win, text="Save", command=save_settings).grid(row=4, column=0, padx=10, pady=20)
        ctk.CTkButton(settings_win, text="Cancel", command=settings_win.destroy).grid(row=4, column=1, padx=10, pady=20)
    
    def export_data(self):
        """Export monitoring data"""
        # Create export options dialog
        export_dialog = ctk.CTkToplevel(self.root)
        export_dialog.title("Export Options")
        export_dialog.geometry("300x200")
        export_dialog.transient(self.root)
        export_dialog.grab_set()
        
        # Export format options
        ctk.CTkLabel(export_dialog, text="Export Format:").pack(pady=(10, 5))
        format_var = tk.StringVar(value="csv")
        
        csv_option = ctk.CTkRadioButton(
            export_dialog, text="CSV (Spreadsheet)", variable=format_var, value="csv")
        csv_option.pack(anchor="w", padx=20)
        
        json_option = ctk.CTkRadioButton(
            export_dialog, text="JSON (Data)", variable=format_var, value="json")
        json_option.pack(anchor="w", padx=20)
        
        image_option = ctk.CTkRadioButton(
            export_dialog, text="PNG (Screenshots)", variable=format_var, value="png")
        image_option.pack(anchor="w", padx=20)
        
        def do_export():
            export_format = format_var.get()
            
            if export_format == "csv":
                self.export_to_csv()
            elif export_format == "json":
                self.export_to_json()
            elif export_format == "png":
                self.export_screenshots()
            
            export_dialog.destroy()
        
        # Buttons
        ctk.CTkButton(export_dialog, text="Export", command=do_export).pack(pady=(20, 5))
        ctk.CTkButton(export_dialog, text="Cancel", command=export_dialog.destroy).pack(pady=5)
    
    def export_to_csv(self):
        """Export data to CSV format"""
        from tkinter import filedialog
        import csv
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Monitoring Data as CSV"
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header
                writer.writerow(["Timestamp", "CPU Avg %", "Memory %", 
                                "Network Send (B/s)", "Network Receive (B/s)"])
                
                # Write data
                cpu_data = self.cpu_history
                for i in range(len(self.memory_history)):
                    if i < len(self.time_points):
                        timestamp = self.time_points[i]
                    else:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        
                    avg_cpu = sum(history[i] for history in cpu_data if i < len(history)) / len(cpu_data)
                    memory = self.memory_history[i] if i < len(self.memory_history) else 0
                    net_send = self.network_sent_history[i] if i < len(self.network_sent_history) else 0
                    net_recv = self.network_recv_history[i] if i < len(self.network_recv_history) else 0
                    
                    writer.writerow([timestamp, f"{avg_cpu:.2f}", f"{memory:.2f}", 
                                    f"{net_send:.2f}", f"{net_recv:.2f}"])
            
            # Show success message
            messagebox.showinfo("Export Successful", f"Data exported to {filename}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Failed to export data: {str(e)}")
    
    def export_to_json(self):
        """Export data to JSON format"""
        from tkinter import filedialog
        import json
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Export Monitoring Data as JSON"
        )
        
        if not filename:
            return
        
        try:
            data = {
                "system_info": {
                    "system": platform.system(),
                    "node": platform.node(),
                    "release": platform.release(),
                    "version": platform.version(),
                    "machine": platform.machine(),
                    "processor": platform.processor(),
                },
                "timestamps": self.time_points,
                "cpu_data": [hist for hist in self.cpu_history],
                "memory_data": self.memory_history,
                "network_data": {
                    "sent": self.network_sent_history,
                    "received": self.network_recv_history
                }
            }
            
            with open(filename, 'w') as jsonfile:
                json.dump(data, jsonfile, indent=2)
                
            # Show success message
            messagebox.showinfo("Export Successful", f"Data exported to {filename}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Failed to export data: {str(e)}")
    
    def export_screenshots(self):
        """Export screenshots of all graphs"""
        from tkinter import filedialog
        import os
        
        directory = filedialog.askdirectory(
            title="Select Directory for Screenshots"
        )
        
        if not directory:
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save CPU chart
            cpu_filename = os.path.join(directory, f"vitalviz_cpu_{timestamp}.png")
            self.cpu_fig.savefig(cpu_filename, dpi=150)
            
            # Save memory chart
            memory_filename = os.path.join(directory, f"vitalviz_memory_{timestamp}.png")
            self.memory_fig.savefig(memory_filename, dpi=150)
            
            # Save network chart
            network_filename = os.path.join(directory, f"vitalviz_network_{timestamp}.png")
            self.network_fig.savefig(network_filename, dpi=150)
            
            # Show success message
            messagebox.showinfo("Export Successful", 
                               f"Screenshots saved to {directory}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Failed to save screenshots: {str(e)}")
    
    def on_closing(self):
        """Clean up when window is closed"""
        self.running = False
        self.root.destroy()

if __name__ == "__main__":
    # Simple initialization for debugging
    try:
        root = ctk.CTk()
        app = SystemMonitorGUI(root)
        root.protocol("WM_DELETE_WINDOW", app.on_closing)
        root.mainloop()
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()