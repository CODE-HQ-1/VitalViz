"""
Interactive System Monitoring Dashboard
---------------------------------------
A colorful, real-time system resource monitor for your terminal
featuring CPU, memory, disk usage, and network statistics.
"""

import time
import psutil
import platform
from datetime import datetime
from rich.live import Live
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich import box
from rich.console import Console
from rich.text import Text

console = Console()

def get_cpu_usage_per_core():
    """Get CPU usage percentage for each core."""
    return psutil.cpu_percent(percpu=True, interval=0.1)

def get_memory_info():
    """Get memory usage information."""
    memory = psutil.virtual_memory()
    return {
        "total": memory.total,
        "available": memory.available,
        "percent": memory.percent,
        "used": memory.used,
        "free": memory.free
    }

def get_disk_info():
    """Get disk usage information for all mounted partitions."""
    partitions = []
    for partition in psutil.disk_partitions():
        if partition.fstype:
            usage = psutil.disk_usage(partition.mountpoint)
            partitions.append({
                "device": partition.device,
                "mountpoint": partition.mountpoint,
                "fstype": partition.fstype,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": usage.percent
            })
    return partitions

def get_network_info():
    """Get network I/O statistics."""
    return psutil.net_io_counters()

def size_formatter(bytes_value):
    """Format bytes value to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"

def generate_cpu_table(cpu_usage):
    """Generate a table for CPU usage."""
    cpu_table = Table(title="CPU Usage", box=box.ROUNDED)
    cpu_table.add_column("Core")
    cpu_table.add_column("Usage %")
    cpu_table.add_column("Graph")
    
    for i, percentage in enumerate(cpu_usage):
        bar = "█" * int(percentage / 2)
        color = "green" if percentage < 50 else "yellow" if percentage < 80 else "red"
        cpu_table.add_row(
            f"Core {i}", 
            f"{percentage:.1f}%", 
            Text(bar, style=color)
        )
    return cpu_table

def generate_memory_table(memory_info):
    """Generate a table for memory usage."""
    memory_table = Table(title="Memory Usage", box=box.ROUNDED)
    memory_table.add_column("Metric")
    memory_table.add_column("Value")
    
    memory_table.add_row("Total", size_formatter(memory_info["total"]))
    memory_table.add_row("Available", size_formatter(memory_info["available"]))
    memory_table.add_row("Used", size_formatter(memory_info["used"]))
    memory_table.add_row("Free", size_formatter(memory_info["free"]))
    
    progress = Progress(
        TextColumn("[bold blue]RAM Usage:"),
        BarColumn(bar_width=40),
        TextColumn(f"{memory_info['percent']}%")
    )
    progress.add_task("", total=100, completed=memory_info["percent"])
    
    memory_table.add_row("", "")
    memory_table.add_row("Usage", "")
    
    return Panel(memory_table)

def generate_disk_table(disk_info):
    """Generate a table for disk usage."""
    disk_table = Table(title="Disk Usage", box=box.ROUNDED)
    disk_table.add_column("Device")
    disk_table.add_column("Mount")
    disk_table.add_column("Type")
    disk_table.add_column("Total")
    disk_table.add_column("Used")
    disk_table.add_column("Free")
    disk_table.add_column("Usage %")
    
    for disk in disk_info:
        color = "green" if disk["percent"] < 70 else "yellow" if disk["percent"] < 85 else "red"
        disk_table.add_row(
            disk["device"],
            disk["mountpoint"],
            disk["fstype"],
            size_formatter(disk["total"]),
            size_formatter(disk["used"]),
            size_formatter(disk["free"]),
            Text(f"{disk['percent']}%", style=color)
        )
    return disk_table

def generate_network_table(prev_net_io, current_net_io, time_diff):
    """Generate a table for network statistics."""
    network_table = Table(title="Network Statistics", box=box.ROUNDED)
    network_table.add_column("Metric")
    network_table.add_column("Total")
    network_table.add_column("Per Second")
    
    # Calculate bytes per second
    bytes_sent_per_sec = (current_net_io.bytes_sent - prev_net_io.bytes_sent) / time_diff
    bytes_recv_per_sec = (current_net_io.bytes_recv - prev_net_io.bytes_recv) / time_diff
    
    network_table.add_row(
        "Bytes Sent", 
        size_formatter(current_net_io.bytes_sent),
        size_formatter(bytes_sent_per_sec) + "/s"
    )
    network_table.add_row(
        "Bytes Received", 
        size_formatter(current_net_io.bytes_recv),
        size_formatter(bytes_recv_per_sec) + "/s"
    )
    network_table.add_row(
        "Packets Sent", 
        str(current_net_io.packets_sent),
        f"{(current_net_io.packets_sent - prev_net_io.packets_sent) / time_diff:.2f}/s"
    )
    network_table.add_row(
        "Packets Received", 
        str(current_net_io.packets_recv),
        f"{(current_net_io.packets_recv - prev_net_io.packets_recv) / time_diff:.2f}/s"
    )
    
    return network_table

def generate_system_info():
    """Generate system information panel."""
    uname = platform.uname()
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - boot_time
    
    system_info = Table.grid()
    system_info.add_column()
    system_info.add_column()
    
    system_info.add_row("System:", f"{uname.system} {uname.release}")
    system_info.add_row("Node Name:", uname.node)
    system_info.add_row("Version:", uname.version)
    system_info.add_row("Machine:", uname.machine)
    system_info.add_row("Processor:", uname.processor)
    system_info.add_row("Boot Time:", f"{boot_time.strftime('%Y-%m-%d %H:%M:%S')}")
    system_info.add_row("Uptime:", f"{uptime.days} days, {uptime.seconds//3600} hours, {(uptime.seconds//60)%60} minutes")
    
    return Panel(system_info, title="System Information", border_style="blue")

def main():
    """Main function to run the system monitor dashboard."""
    prev_net_io = psutil.net_io_counters()
    prev_time = time.time()
    
    layout = Layout()
    layout.split_column(
        Layout(name="header"),
        Layout(name="main")
    )
    
    layout["main"].split_row(
        Layout(name="left"),
        Layout(name="right"),
    )
    
    layout["left"].split_column(
        Layout(name="cpu"),
        Layout(name="memory")
    )
    
    layout["right"].split_column(
        Layout(name="disk"),
        Layout(name="network")
    )
    
    try:
        with Live(layout, refresh_per_second=2, screen=True):
            while True:
                # Calculate time difference for network rates
                current_time = time.time()
                time_diff = current_time - prev_time
                
                # Get current system information
                cpu_usage = get_cpu_usage_per_core()
                memory_info = get_memory_info()
                disk_info = get_disk_info()
                # Fix here: use get_network_info() instead of get_net_io_counters()
                current_net_io = get_network_info()
                
                # Update layout
                layout["header"].update(generate_system_info())
                layout["cpu"].update(generate_cpu_table(cpu_usage))
                layout["memory"].update(generate_memory_table(memory_info))
                layout["disk"].update(generate_disk_table(disk_info))
                layout["network"].update(generate_network_table(prev_net_io, current_net_io, time_diff))
                
                # Update previous values
                prev_net_io = current_net_io
                prev_time = current_time
                
                time.sleep(1)
    except KeyboardInterrupt:
        console.print("[bold green]Exiting system monitor...[/bold green]")

if __name__ == "__main__":
    console.print("[bold blue]Starting System Monitor Dashboard...[/bold blue]")
    console.print("[italic](Press CTRL+C to exit)[/italic]")
    time.sleep(1)
    main()