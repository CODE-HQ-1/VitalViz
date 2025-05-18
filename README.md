# 🖥️ VitalViz

A powerful, interactive terminal-based system monitoring tool that provides real-time insights into your computer's vital signs with a colorful, easy-to-read interface..

---

## 📊 Features

- **Real-time CPU Monitoring:** Per-core usage with color-coded visual indicators  
- **Memory Analysis:** RAM utilization with percentages and meters  
- **Disk Usage Visualization:** Mounted partition stats with space breakdown  
- **Network Traffic Tracking:** Bandwidth usage with real-time upload/download rates  
- **System Overview:** OS details, uptime, hardware specs  
- **Color-Coded Alerts:** Warnings for high resource usage  
- **Responsive Terminal UI:** Auto-adjusts to terminal size  
- **Low Resource Footprint:** Lightweight and efficient  

---

## 🛠️ Requirements

- Python **3.6+**
- Dependencies:
  - `psutil`
  - `rich`

---

## 📥 Installation

```bash
git clone https://github.com/CODE-HQ-1/vitalviz.git
cd vitalviz
pip install psutil rich
```

---

## 🚀 Usage

Run VitalViz with:

```bash
python system_dashboard.py
```

**Controls:**  
- `CTRL+C` to exit  
- Auto-refreshes every second  

---

## 🐛 Troubleshooting

**Known Issue:**  
```
NameError: name 'get_net_io_counters' is not defined
```

**Fix:**  
In `system_dashboard.py`, change line 223:  
```python
# From:
current_net_io = get_net_io_counters()

# To:
current_net_io = get_network_info()
```

---

## 📖 How It Works

VitalViz uses:
- **psutil** to collect system metrics  
- **rich** to render an attractive terminal UI

It regularly updates panels showing:
- System info (OS, hostname, uptime)
- CPU usage (per core)
- Memory stats (total, used, available)
- Disk space (all partitions)
- Network I/O (live transfer rates)

---

## 🤝 Contributing

1. Fork this repository  
2. Create a branch: `git checkout -b new-feature`  
3. Commit your changes: `git commit -am 'Add feature'`  
4. Push the branch: `git push origin new-feature`  
5. Open a pull request  

---

## 📜 License

Licensed under the **MIT License**. See the [LICENSE](LICENSE) file.

---

## 🙏 Acknowledgments

- [psutil](https://github.com/giampaolo/psutil) — System monitoring
- [rich](https://github.com/Textualize/rich) — Terminal formatting  
- Made with by code.cli
