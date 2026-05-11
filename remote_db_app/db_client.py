import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import subprocess
import queue
import sys
import os
import io
import paramiko
from datetime import datetime
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

class ToolTip:
    """Simple tooltip class for better UX"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind('<Enter>', self.show_tip)
        widget.bind('<Leave>', self.hide_tip)

    def show_tip(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, background="#ffffe0", relief="solid", borderwidth=1, font=("Segoe UI", 9))
        label.pack()

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

class DbClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Remote DB Client - Oracle Automation")
        self.root.geometry("1150x950")
        self.root.configure(bg="#f0f2f5")

        # Apply modern style (no coloured buttons)
        self._setup_styles()

        # ---------- Top frame: two DB connections + SSH ----------
        frm_conn = ttk.Frame(root)
        frm_conn.pack(fill=tk.X, padx=15, pady=10)

        # ===== Database 1 =====
        self.frm_db1 = ttk.LabelFrame(frm_conn, text="Oracle Database 1 (Source)", padding=10)
        self.frm_db1.grid(row=0, column=0, sticky="nsew", padx=(0,8))

        ttk.Label(self.frm_db1, text="Host:").grid(row=0, column=0, sticky=tk.W)
        self.host = ttk.Entry(self.frm_db1, width=16)
        self.host.grid(row=0, column=1, padx=5, pady=2)
        self.host.insert(0, "localhost")
        ToolTip(self.host, "Database server hostname or IP")

        ttk.Label(self.frm_db1, text="Port:").grid(row=0, column=2, sticky=tk.W, padx=(5,0))
        self.port = ttk.Entry(self.frm_db1, width=6)
        self.port.grid(row=0, column=3, padx=5, pady=2)
        self.port.insert(0, "1521")

        ttk.Label(self.frm_db1, text="Service Name:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.db_name = ttk.Entry(self.frm_db1, width=16)
        self.db_name.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(self.frm_db1, text="User:").grid(row=1, column=2, sticky=tk.W, pady=2)
        self.user = ttk.Entry(self.frm_db1, width=16)
        self.user.grid(row=1, column=3, padx=5, pady=2)

        ttk.Label(self.frm_db1, text="Password:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.password = ttk.Entry(self.frm_db1, width=16, show="*")
        self.password.grid(row=2, column=1, padx=5, pady=2)

        btn_frame_db1 = ttk.Frame(self.frm_db1)
        btn_frame_db1.grid(row=3, column=0, columnspan=4, pady=8)
        self.btn_db_connect = ttk.Button(btn_frame_db1, text="Connect", command=self.connect_db)
        self.btn_db_connect.pack(side=tk.LEFT, padx=3)
        self.btn_db_disconnect = ttk.Button(btn_frame_db1, text="Disconnect", command=self.disconnect_db, state=tk.DISABLED)
        self.btn_db_disconnect.pack(side=tk.LEFT, padx=3)
        self.db_status_var = tk.StringVar(value="Not connected")
        self.db_status_label = ttk.Label(btn_frame_db1, textvariable=self.db_status_var, foreground="red")
        self.db_status_label.pack(side=tk.LEFT, padx=5)

        # ===== Database 2 =====
        self.frm_db2 = ttk.LabelFrame(frm_conn, text="Oracle Database 2 (Target)", padding=10)
        self.frm_db2.grid(row=0, column=1, sticky="nsew", padx=(8,0))

        ttk.Label(self.frm_db2, text="Host:").grid(row=0, column=0, sticky=tk.W)
        self.host2 = ttk.Entry(self.frm_db2, width=16)
        self.host2.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(self.frm_db2, text="Port:").grid(row=0, column=2, sticky=tk.W, padx=(5,0))
        self.port2 = ttk.Entry(self.frm_db2, width=6)
        self.port2.grid(row=0, column=3, padx=5, pady=2)
        self.port2.insert(0, "1521")

        ttk.Label(self.frm_db2, text="Service Name:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.db_name2 = ttk.Entry(self.frm_db2, width=16)
        self.db_name2.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(self.frm_db2, text="User:").grid(row=1, column=2, sticky=tk.W, pady=2)
        self.user2 = ttk.Entry(self.frm_db2, width=16)
        self.user2.grid(row=1, column=3, padx=5, pady=2)

        ttk.Label(self.frm_db2, text="Password:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.password2 = ttk.Entry(self.frm_db2, width=16, show="*")
        self.password2.grid(row=2, column=1, padx=5, pady=2)

        btn_frame_db2 = ttk.Frame(self.frm_db2)
        btn_frame_db2.grid(row=3, column=0, columnspan=4, pady=8)
        self.btn_db2_connect = ttk.Button(btn_frame_db2, text="Connect", command=self.connect_db2)
        self.btn_db2_connect.pack(side=tk.LEFT, padx=3)
        self.btn_db2_disconnect = ttk.Button(btn_frame_db2, text="Disconnect", command=self.disconnect_db2, state=tk.DISABLED)
        self.btn_db2_disconnect.pack(side=tk.LEFT, padx=3)
        self.db2_status_var = tk.StringVar(value="Not connected")
        self.db2_status_label = ttk.Label(btn_frame_db2, textvariable=self.db2_status_var, foreground="red")
        self.db2_status_label.pack(side=tk.LEFT, padx=5)

        # ===== SSH connection =====
        self.frm_ssh = ttk.LabelFrame(frm_conn, text="Linux Server SSH Connection", padding=10)
        self.frm_ssh.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(12,0))

        ttk.Label(self.frm_ssh, text="Host:").grid(row=0, column=0, sticky=tk.W)
        self.ssh_host = ttk.Entry(self.frm_ssh, width=18)
        self.ssh_host.grid(row=0, column=1, padx=5, pady=2)
        self.ssh_host.insert(0, "192.168.1.100")

        ttk.Label(self.frm_ssh, text="Port:").grid(row=0, column=2, sticky=tk.W, padx=(10,0))
        self.ssh_port = ttk.Entry(self.frm_ssh, width=7)
        self.ssh_port.grid(row=0, column=3, padx=5, pady=2)
        self.ssh_port.insert(0, "22")

        ttk.Label(self.frm_ssh, text="User:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.ssh_user = ttk.Entry(self.frm_ssh, width=18)
        self.ssh_user.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(self.frm_ssh, text="Password:").grid(row=1, column=2, sticky=tk.W, pady=5)
        self.ssh_pass = ttk.Entry(self.frm_ssh, width=18, show="*")
        self.ssh_pass.grid(row=1, column=3, padx=5, pady=2)

        btn_frame_ssh = ttk.Frame(self.frm_ssh)
        btn_frame_ssh.grid(row=2, column=0, columnspan=4, pady=8)
        self.btn_ssh_connect = ttk.Button(btn_frame_ssh, text="Connect", command=self.ssh_connect)
        self.btn_ssh_connect.pack(side=tk.LEFT, padx=5)
        self.btn_ssh_disconnect = ttk.Button(btn_frame_ssh, text="Disconnect", command=self.ssh_disconnect, state=tk.DISABLED)
        self.btn_ssh_disconnect.pack(side=tk.LEFT, padx=5)
        self.btn_oraenv = ttk.Button(btn_frame_ssh, text="Run . oraenv", command=self.run_oraenv, state=tk.DISABLED)
        self.btn_oraenv.pack(side=tk.LEFT, padx=10)
        self.ssh_status_var = tk.StringVar(value="Not connected")
        self.ssh_status_label = ttk.Label(btn_frame_ssh, textvariable=self.ssh_status_var, foreground="red")
        self.ssh_status_label.pack(side=tk.LEFT, padx=10)

        frm_conn.columnconfigure(0, weight=1)
        frm_conn.columnconfigure(1, weight=1)

        # Engines
        self.engine = None
        self.engine2 = None
        self.ssh_client = None

        # ---------- Notebook for tabs (DataPump, File Transfer, Compare Objects) ----------
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=(5,15))
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # ----- DataPump tab (scrollable) -----
        self.tab_datapump = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_datapump, text=" DataPump ")
        self._build_datapump_tab()

        # ----- File Transfer tab -----
        self.tab_transfer = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_transfer, text=" File Transfer ")
        self._build_file_transfer_tab()

        # ----- DB Objects Comparison tab -----
        self.tab_compare = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_compare, text=" Compare Objects ")
        self._build_compare_tab()

        # Status bar
        self.status = tk.StringVar()
        self.status.set("Ready")
        status_bar = ttk.Label(root, textvariable=self.status, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, padx=15, pady=(0,10))

        # Initial visibility: both visible by default
        self.show_db1_frame(True)
        self.show_db2_frame(True)

        # Process management attributes
        self.dp_process = None
        self.dp_channel = None
        self.dp_queue = queue.Queue()
        self.dp_thread = None
        self.after_id = None

    def _setup_styles(self):
        style = ttk.Style()
        available_themes = style.theme_names()
        if 'clam' in available_themes:
            style.theme_use('clam')
        # No custom button backgrounds – buttons are colourless by default

    # ====================== Visibility Control ======================
    def show_db1_frame(self, visible=True):
        if visible:
            self.frm_db1.grid()
        else:
            self.frm_db1.grid_remove()

    def show_db2_frame(self, visible=True):
        if visible:
            self.frm_db2.grid()
        else:
            self.frm_db2.grid_remove()

    def on_tab_changed(self, event):
        current_tab = self.notebook.index(self.notebook.select())
        tab_text = self.notebook.tab(current_tab, "text").strip()
        
        if tab_text == "DataPump":
            self.update_datapump_visibility()
        elif tab_text == "Compare Objects":
            self.show_db1_frame(False)
            self.show_db2_frame(True)
            self.frm_db2.config(text="Oracle Database 2 (Target)")
        elif tab_text == "File Transfer":
            self.show_db1_frame(True)
            self.show_db2_frame(True)
            self.frm_db1.config(text="Oracle Database 1 (Source for File Transfer)")
            self.frm_db2.config(text="Oracle Database 2 (Destination for File Transfer)")
        else:
            self.show_db1_frame(True)
            self.show_db2_frame(True)
            self.frm_db1.config(text="Oracle Database 1")
            self.frm_db2.config(text="Oracle Database 2")

    def update_datapump_visibility(self):
        if self.dp_mode.get() == "export":
            self.show_db1_frame(True)
            self.show_db2_frame(False)
            self.frm_db1.config(text="Oracle Database (Source for Export)")
        else:
            self.show_db1_frame(False)
            self.show_db2_frame(True)
            self.frm_db2.config(text="Oracle Database (Target for Import)")

    # ====================== DataPump Tab (scrollable, two columns) ======================
    def _build_datapump_tab(self):
        # Create canvas and scrollbar
        canvas = tk.Canvas(self.tab_datapump, bg="#f0f2f5", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.tab_datapump, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Main container inside scrollable frame
        main_pane = ttk.Frame(scrollable_frame)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        main_pane.columnconfigure(0, weight=1)
        main_pane.columnconfigure(1, weight=1)
        main_pane.rowconfigure(0, weight=1)

        # ----- LEFT COLUMN: Controls -----
        left_frame = ttk.LabelFrame(main_pane, text="DataPump Controls", padding=10)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0,5))

        # Mode selection
        mode_frame = ttk.Frame(left_frame)
        mode_frame.pack(fill=tk.X, pady=5)
        self.dp_mode = tk.StringVar(value="export")
        ttk.Radiobutton(mode_frame, text="Export", variable=self.dp_mode, value="export", command=self.update_datapump_visibility).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="Import", variable=self.dp_mode, value="import", command=self.update_datapump_visibility).pack(side=tk.LEFT, padx=5)

        # Required parameters
        ttk.Label(left_frame, text="Directory:").pack(anchor=tk.W, pady=(10,0))
        self.dir_entry = ttk.Entry(left_frame, width=40)
        self.dir_entry.pack(fill=tk.X, pady=2)
        self.dir_entry.insert(0, "DATA_PUMP")

        ttk.Label(left_frame, text="Dump file:").pack(anchor=tk.W, pady=(5,0))
        self.dumpfile_entry = ttk.Entry(left_frame, width=40)
        self.dumpfile_entry.pack(fill=tk.X, pady=2)
        self.dumpfile_entry.insert(0, "export.dmp")

        ttk.Label(left_frame, text="Log file:").pack(anchor=tk.W, pady=(5,0))
        self.logfile_entry = ttk.Entry(left_frame, width=40)
        self.logfile_entry.pack(fill=tk.X, pady=2)
        self.logfile_entry.insert(0, "export.log")

        # Optional parameters section
        opt_frame = ttk.LabelFrame(left_frame, text="Optional Parameters", padding=5)
        opt_frame.pack(fill=tk.X, pady=(10,0))

        ttk.Label(opt_frame, text="Schemas:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.schemas_entry = ttk.Entry(opt_frame, width=30)
        self.schemas_entry.grid(row=0, column=1, padx=5, pady=2, sticky=tk.W)
        ttk.Label(opt_frame, text="(comma separated)").grid(row=0, column=2, padx=5, sticky=tk.W)

        ttk.Label(opt_frame, text="Tables:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.tables_entry = ttk.Entry(opt_frame, width=30)
        self.tables_entry.grid(row=1, column=1, padx=5, pady=2, sticky=tk.W)
        ttk.Label(opt_frame, text="(schema.table, ...)").grid(row=1, column=2, padx=5, sticky=tk.W)

        ttk.Label(opt_frame, text="Remap Schema:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        remap_frame = ttk.Frame(opt_frame)
        remap_frame.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        self.remap_from = ttk.Entry(remap_frame, width=15)
        self.remap_from.pack(side=tk.LEFT, padx=2)
        ttk.Label(remap_frame, text="→").pack(side=tk.LEFT, padx=5)
        self.remap_to = ttk.Entry(remap_frame, width=15)
        self.remap_to.pack(side=tk.LEFT, padx=2)

        ttk.Label(opt_frame, text="Content:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.content_combo = ttk.Combobox(opt_frame, values=["ALL", "DATA_ONLY", "METADATA_ONLY"], state="readonly", width=18)
        self.content_combo.grid(row=3, column=1, padx=5, pady=2, sticky=tk.W)
        self.content_combo.set("ALL")

        ttk.Label(opt_frame, text="Parallel:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=2)
        self.parallel_spin = ttk.Spinbox(opt_frame, from_=1, to=32, width=10)
        self.parallel_spin.grid(row=4, column=1, padx=5, pady=2, sticky=tk.W)
        self.parallel_spin.set(1)

        ttk.Label(opt_frame, text="Compression:").grid(row=5, column=0, sticky=tk.W, padx=5, pady=2)
        self.compression_combo = ttk.Combobox(opt_frame, values=["NONE", "METADATA_ONLY", "DATA_ONLY", "ALL"], state="readonly", width=18)
        self.compression_combo.grid(row=5, column=1, padx=5, pady=2, sticky=tk.W)
        self.compression_combo.set("NONE")

        ttk.Label(opt_frame, text="Extra params:").grid(row=6, column=0, sticky=tk.W, padx=5, pady=2)
        self.extra_entry = ttk.Entry(opt_frame, width=50)
        self.extra_entry.grid(row=6, column=1, columnspan=2, padx=5, pady=2, sticky="ew")
        ToolTip(self.extra_entry, "Additional expdp/impdp parameters")

        # Buttons
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, pady=15)
        ttk.Button(btn_frame, text="Generate Command", command=self.generate_datapump_cmd).pack(side=tk.LEFT, padx=2)
        self.btn_run = ttk.Button(btn_frame, text="Run", command=self.run_datapump)
        self.btn_run.pack(side=tk.LEFT, padx=2)
        self.btn_stop = ttk.Button(btn_frame, text="Stop", command=self.stop_datapump, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=2)

        # ----- RIGHT COLUMN: Generated Command and Output -----
        right_frame = ttk.Frame(main_pane)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5,0))
        right_frame.rowconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=2)
        right_frame.rowconfigure(2, weight=0)  # for clear button
        right_frame.columnconfigure(0, weight=1)

        # Generated command area
        cmd_frame = ttk.LabelFrame(right_frame, text="Generated Command", padding=5)
        cmd_frame.grid(row=0, column=0, sticky="nsew", pady=(0,5))
        cmd_frame.rowconfigure(0, weight=1)
        cmd_frame.columnconfigure(0, weight=1)
        self.cmd_text = scrolledtext.ScrolledText(cmd_frame, height=6, font=("Consolas", 9), wrap=tk.WORD)
        self.cmd_text.grid(row=0, column=0, sticky="nsew")

        # Output area
        output_frame = ttk.LabelFrame(right_frame, text="Output", padding=5)
        output_frame.grid(row=1, column=0, sticky="nsew")
        output_frame.rowconfigure(0, weight=1)
        output_frame.columnconfigure(0, weight=1)
        self.output_text = scrolledtext.ScrolledText(output_frame, height=15, font=("Consolas", 9), bg="#1e1e2f", fg="#d4d4d4", insertbackground="white")
        self.output_text.grid(row=0, column=0, sticky="nsew")

        # Clear output button – use grid, not pack
        clear_btn = ttk.Button(right_frame, text="Clear Output", command=self.clear_output)
        clear_btn.grid(row=2, column=0, sticky=tk.W, pady=5)

    # ====================== File Transfer Tab (scrollable, no manual file fields) ======================
    def _build_file_transfer_tab(self):
        # Create canvas and scrollbar for this tab
        canvas = tk.Canvas(self.tab_transfer, bg="#f0f2f5", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.tab_transfer, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Make inner frame width follow canvas width
        def _configure_canvas(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind("<Configure>", _configure_canvas)

        # Enable mouse wheel scrolling when mouse is over the canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # --- The actual transfer UI (inside scrollable frame) ---
        frm_transfer = ttk.LabelFrame(scrollable_frame, text="Server-to-Server File Transfer", padding=15)
        frm_transfer.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        frm_transfer.columnconfigure(1, weight=1)

        # --- Source Server (uses main SSH connection) ---
        ttk.Label(frm_transfer, text="Source Server (uses main SSH connection):", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, columnspan=4, sticky=tk.W, pady=(0,8))

        ttk.Label(frm_transfer, text="Host:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.ssh_source_host = ttk.Entry(frm_transfer, width=20)
        self.ssh_source_host.grid(row=1, column=1, padx=5, pady=2, sticky=tk.W)
        self.ssh_source_host.insert(0, self.ssh_host.get())

        ttk.Label(frm_transfer, text="Port:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        self.ssh_source_port = ttk.Entry(frm_transfer, width=6)
        self.ssh_source_port.grid(row=1, column=3, padx=5, pady=2, sticky=tk.W)
        self.ssh_source_port.insert(0, self.ssh_port.get())

        ttk.Label(frm_transfer, text="User:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.ssh_source_user = ttk.Entry(frm_transfer, width=20)
        self.ssh_source_user.grid(row=2, column=1, padx=5, pady=2, sticky=tk.W)
        self.ssh_source_user.insert(0, self.ssh_user.get())

        ttk.Label(frm_transfer, text="Password:").grid(row=2, column=2, sticky=tk.W, padx=5, pady=2)
        self.ssh_source_pass = ttk.Entry(frm_transfer, width=20, show="*")
        self.ssh_source_pass.grid(row=2, column=3, padx=5, pady=2, sticky=tk.W)
        self.ssh_source_pass.insert(0, self.ssh_pass.get())

        ttk.Label(frm_transfer, text="Source Directory Path:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.source_path = ttk.Entry(frm_transfer, width=60)
        self.source_path.grid(row=3, column=1, columnspan=2, padx=5, pady=2, sticky="ew")
        btn_auto_source = ttk.Button(frm_transfer, text="Auto-fill from DB1", command=self.autofill_source_path)
        btn_auto_source.grid(row=3, column=3, padx=5, pady=2, sticky=tk.W)

        # --- Destination Server (uses Database 2) ---
        ttk.Label(frm_transfer, text="Destination Server (uses Database 2 credentials):", font=("Segoe UI", 10, "bold")).grid(row=4, column=0, columnspan=4, sticky=tk.W, pady=(15,8))

        ttk.Label(frm_transfer, text="Host:").grid(row=5, column=0, sticky=tk.W, padx=5, pady=2)
        self.ssh_dest_host = ttk.Entry(frm_transfer, width=20)
        self.ssh_dest_host.grid(row=5, column=1, padx=5, pady=2, sticky=tk.W)
        self.ssh_dest_host.insert(0, self.host2.get())

        ttk.Label(frm_transfer, text="Port:").grid(row=5, column=2, sticky=tk.W, padx=5, pady=2)
        self.ssh_dest_port = ttk.Entry(frm_transfer, width=6)
        self.ssh_dest_port.grid(row=5, column=3, padx=5, pady=2, sticky=tk.W)
        self.ssh_dest_port.insert(0, self.port2.get())

        ttk.Label(frm_transfer, text="User:").grid(row=6, column=0, sticky=tk.W, padx=5, pady=2)
        self.ssh_dest_user = ttk.Entry(frm_transfer, width=20)
        self.ssh_dest_user.grid(row=6, column=1, padx=5, pady=2, sticky=tk.W)
        self.ssh_dest_user.insert(0, self.user2.get())

        ttk.Label(frm_transfer, text="Password:").grid(row=6, column=2, sticky=tk.W, padx=5, pady=2)
        self.ssh_dest_pass = ttk.Entry(frm_transfer, width=20, show="*")
        self.ssh_dest_pass.grid(row=6, column=3, padx=5, pady=2, sticky=tk.W)
        self.ssh_dest_pass.insert(0, self.password2.get())

        ttk.Label(frm_transfer, text="Destination Directory Path:").grid(row=7, column=0, sticky=tk.W, padx=5, pady=2)
        self.dest_path = ttk.Entry(frm_transfer, width=60)
        self.dest_path.grid(row=7, column=1, columnspan=2, padx=5, pady=2, sticky="ew")
        btn_auto_dest = ttk.Button(frm_transfer, text="Auto-fill from DB2", command=self.autofill_dest_path)
        btn_auto_dest.grid(row=7, column=3, padx=5, pady=2, sticky=tk.W)

        # ✅ Transfer button – always visible
        self.transfer_btn = ttk.Button(frm_transfer, text="🚀 Transfer Files", command=self.transfer_files)
        self.transfer_btn.grid(row=8, column=0, columnspan=4, pady=20)

        # Transfer output console
        ttk.Label(frm_transfer, text="Transfer Output:", font=("Segoe UI", 9, "bold")).grid(row=9, column=0, columnspan=4, sticky=tk.W, pady=(10,2))
        self.transfer_output = scrolledtext.ScrolledText(frm_transfer, height=15, font=("Consolas", 9), bg="#1e1e2f", fg="#d4d4d4")
        self.transfer_output.grid(row=10, column=0, columnspan=4, sticky="nsew", pady=5)
        ttk.Button(frm_transfer, text="Clear Transfer Log", command=self.clear_transfer_output).grid(row=11, column=0, sticky=tk.W, pady=5)

        # Make the transfer output expandable
        frm_transfer.rowconfigure(10, weight=1)
        frm_transfer.columnconfigure(1, weight=1)

    # ====================== Compare Objects Tab ======================
    def _build_compare_tab(self):
        frm_compare = ttk.LabelFrame(self.tab_compare, text="Object Comparison", padding=10)
        frm_compare.pack(fill=tk.BOTH, expand=True, pady=8)
        
        btn_run_compare = ttk.Button(frm_compare, text="Compare Objects", command=self.compare_objects)
        btn_run_compare.pack(pady=8, anchor=tk.W)
        
        self.compare_tree = ttk.Treeview(frm_compare, columns=("Type", "DB1 Count", "DB2 Count", "Missing in DB2"), show="headings")
        self.compare_tree.heading("Type", text="Object Type")
        self.compare_tree.heading("DB1 Count", text="DB1 Count")
        self.compare_tree.heading("DB2 Count", text="DB2 Count")
        self.compare_tree.heading("Missing in DB2", text="Missing in DB2 (names)")
        self.compare_tree.column("Type", width=140)
        self.compare_tree.column("DB1 Count", width=100)
        self.compare_tree.column("DB2 Count", width=100)
        self.compare_tree.column("Missing in DB2", width=500)
        self.compare_tree.pack(fill=tk.BOTH, expand=True)

    # ====================== Database Connections ======================
    def get_connection_string(self, host, port, service, user, password):
        return f"oracle+oracledb://{user}:{quote_plus(password)}@{host}:{port}/?service_name={service}"
    
    def connect_db(self):
        try:
            conn_str = self.get_connection_string(self.host.get().strip(), self.port.get().strip(), self.db_name.get().strip(), self.user.get().strip(), self.password.get())
            self.engine = create_engine(conn_str)
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1 FROM DUAL"))
            self.db_status_var.set("Connected")
            self.db_status_label.config(foreground="green")
            self.btn_db_connect.config(state=tk.DISABLED)
            self.btn_db_disconnect.config(state=tk.NORMAL)
            self.status.set(f"DB1 connected to {self.db_name.get()}")
        except Exception as e:
            self.engine = None
            self.db_status_var.set("Failed")
            self.db_status_label.config(foreground="red")
            messagebox.showerror("Connection Error", str(e))
    
    def disconnect_db(self):
        if self.engine:
            self.engine.dispose()
        self.engine = None
        self.db_status_var.set("Not connected")
        self.db_status_label.config(foreground="red")
        self.btn_db_connect.config(state=tk.NORMAL)
        self.btn_db_disconnect.config(state=tk.DISABLED)
        self.status.set("DB1 disconnected")
    
    def connect_db2(self):
        try:
            conn_str = self.get_connection_string(self.host2.get().strip(), self.port2.get().strip(), self.db_name2.get().strip(), self.user2.get().strip(), self.password2.get())
            self.engine2 = create_engine(conn_str)
            with self.engine2.connect() as conn:
                conn.execute(text("SELECT 1 FROM DUAL"))
            self.db2_status_var.set("Connected")
            self.db2_status_label.config(foreground="green")
            self.btn_db2_connect.config(state=tk.DISABLED)
            self.btn_db2_disconnect.config(state=tk.NORMAL)
            self.status.set(f"DB2 connected to {self.db_name2.get()}")
        except Exception as e:
            self.engine2 = None
            self.db2_status_var.set("Failed")
            self.db2_status_label.config(foreground="red")
            messagebox.showerror("DB2 Connection Error", str(e))
    
    def disconnect_db2(self):
        if self.engine2:
            self.engine2.dispose()
        self.engine2 = None
        self.db2_status_var.set("Not connected")
        self.db2_status_label.config(foreground="red")
        self.btn_db2_connect.config(state=tk.NORMAL)
        self.btn_db2_disconnect.config(state=tk.DISABLED)
        self.status.set("DB2 disconnected")
    
    # ====================== SSH and Remote Execution ======================
    def ssh_connect(self):
        host = self.ssh_host.get().strip()
        port = int(self.ssh_port.get().strip())
        user = self.ssh_user.get().strip()
        pw = self.ssh_pass.get()
        if not all([host, user, pw]):
            messagebox.showwarning("Missing SSH credentials", "Fill all SSH fields.")
            return
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(host, port=port, username=user, password=pw)
            self.ssh_status_var.set("Connected")
            self.ssh_status_label.config(foreground="green")
            self.btn_ssh_connect.config(state=tk.DISABLED)
            self.btn_ssh_disconnect.config(state=tk.NORMAL)
            self.btn_oraenv.config(state=tk.NORMAL)
            self.status.set(f"SSH connected to {host}")
        except Exception as e:
            self.ssh_client = None
            self.ssh_status_var.set("Failed")
            self.ssh_status_label.config(foreground="red")
            messagebox.showerror("SSH Error", str(e))
    
    def ssh_disconnect(self):
        if self.ssh_client:
            self.ssh_client.close()
        self.ssh_client = None
        self.ssh_status_var.set("Not connected")
        self.ssh_status_label.config(foreground="red")
        self.btn_ssh_connect.config(state=tk.NORMAL)
        self.btn_ssh_disconnect.config(state=tk.DISABLED)
        self.btn_oraenv.config(state=tk.DISABLED)
        self.status.set("SSH disconnected")
    
    def run_oraenv(self):
        if not self.ssh_client:
            messagebox.showwarning("SSH not connected", "Connect to the Linux server first.")
            return
        service_name = self.db_name.get().strip()
        if not service_name:
            messagebox.showwarning("Missing service name", "Enter the service name (used as ORACLE_SID).")
            return
        cmd = f"export ORACLE_SID={service_name}; export ORAENV_ASK=NO; . /usr/local/bin/oraenv; echo '--- Environment after . oraenv ---'; echo ORACLE_HOME=$ORACLE_HOME; echo ORACLE_SID=$ORACLE_SID; echo PATH=$PATH"
        self._run_remote_cmd(cmd, on_finish=lambda: None, tag=". oraenv")
    
    def _run_remote_cmd(self, cmd, on_finish=None, tag="Remote command"):
        if not self.ssh_client:
            self._log_now(f"SSH not connected – cannot run: {tag}")
            return
        self._clear_output()
        self.btn_run.config(state=tk.DISABLED)
        self.btn_oraenv.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.DISABLED)
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
            self.dp_channel = stdout.channel
            self.dp_process = None
            self.dp_queue = queue.Queue()
            self.dp_thread_stdout = threading.Thread(target=self._read_stream, args=(stdout,), daemon=True)
            self.dp_thread_stderr = threading.Thread(target=self._read_stream, args=(stderr,), daemon=True)
            self.dp_thread_stdout.start()
            self.dp_thread_stderr.start()
            self.after_id = self.root.after(100, self._check_ssh_status, on_finish)
        except Exception as e:
            self._log_now(f"Failed to execute remote command: {e}")
            self._on_remote_finished(on_finish)
    
    def _read_stream(self, stream):
        try:
            for line in iter(stream.readline, ''):
                if line:
                    self.dp_queue.put(line)
        except Exception:
            pass
        finally:
            stream.close()
    
    def _check_ssh_status(self, on_finish):
        try:
            while True:
                line = self.dp_queue.get_nowait()
                if line is not None:
                    self._log_now(line.rstrip())
        except queue.Empty:
            pass
        if self.dp_channel and not self.dp_channel.closed:
            self.after_id = self.root.after(100, self._check_ssh_status, on_finish)
        else:
            try:
                while True:
                    line = self.dp_queue.get_nowait()
                    if line:
                        self._log_now(line.rstrip())
            except queue.Empty:
                pass
            self._on_remote_finished(on_finish)
    
    def _on_remote_finished(self, on_finish):
        self.btn_run.config(state=tk.NORMAL)
        self.btn_oraenv.config(state=tk.NORMAL if self.ssh_client else tk.DISABLED)
        self.btn_stop.config(state=tk.DISABLED)
        self.dp_channel = None
        if on_finish:
            on_finish()
        self.status.set("Remote command completed")
    
    def stop_datapump(self):
        if self.dp_process and self.dp_process.poll() is None:
            self.dp_process.terminate()
            try:
                self.dp_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.dp_process.kill()
            self._log_now("\n*** Process terminated by user ***\n")
            self._on_process_finished()
        elif self.dp_channel and not self.dp_channel.closed:
            self.dp_channel.close()
            self._log_now("\n*** Remote process terminated by user ***\n")
            self._on_remote_finished(on_finish=None)
        else:
            messagebox.showinfo("Nothing to stop", "No active process.")
    
    # ====================== DataPump Logic (with all optional parameters) ======================
    def _get_target_db_fields(self):
        if self.dp_mode.get() == "export":
            return (self.user.get().strip(), self.password.get(), self.host.get().strip(), self.port.get().strip(), self.db_name.get().strip())
        else:
            return (self.user2.get().strip(), self.password2.get(), self.host2.get().strip(), self.port2.get().strip(), self.db_name2.get().strip())
    
    def generate_datapump_cmd(self):
        try:
            conn_user, conn_pw, conn_host, conn_port, conn_service = self._get_target_db_fields()
            if not all([conn_user, conn_pw, conn_host, conn_port, conn_service]):
                messagebox.showwarning("Missing connection", "Fill in all fields for the required database.")
                return
            date_str = datetime.now().strftime("%d%m%y")
            # Auto‑generate dump/log names if export and schemas provided
            if self.dp_mode.get() == "export":
                schemas_text = self.schemas_entry.get().strip()
                if schemas_text:
                    first_schema = schemas_text.split(",")[0].strip()
                    if first_schema:
                        if self.dumpfile_entry.get().strip() in ("export.dmp", ""):
                            self.dumpfile_entry.delete(0, tk.END)
                            self.dumpfile_entry.insert(0, f"{first_schema}_{date_str}.dmp")
                        if self.logfile_entry.get().strip() in ("export.log", ""):
                            self.logfile_entry.delete(0, tk.END)
                            self.logfile_entry.insert(0, f"{first_schema}_{date_str}.log")
            else:
                # For import, default logfile based on user
                if self.logfile_entry.get().strip() in ("export.log", ""):
                    self.logfile_entry.delete(0, tk.END)
                    self.logfile_entry.insert(0, f"{conn_user}_{date_str}.log")
            
            connect_str = f"{conn_user}/{conn_pw}"
            cmd_parts = ["expdp" if self.dp_mode.get() == "export" else "impdp", connect_str]
            
            # Required
            dp_dir = self.dir_entry.get().strip()
            if dp_dir:
                cmd_parts.append(f"directory={dp_dir}")
            dumpfile = self.dumpfile_entry.get().strip()
            if dumpfile:
                cmd_parts.append(f"dumpfile={dumpfile}")
            logfile = self.logfile_entry.get().strip()
            if logfile:
                cmd_parts.append(f"logfile={logfile}")
            
            # Optional
            schemas = self.schemas_entry.get().strip()
            if schemas:
                cmd_parts.append(f"schemas={schemas.replace(' ', '')}")
            tables = self.tables_entry.get().strip()
            if tables:
                cmd_parts.append(f"tables={tables.replace(' ', '')}")
            
            if self.dp_mode.get() == "import":
                remap_from = self.remap_from.get().strip()
                remap_to = self.remap_to.get().strip()
                if remap_from and remap_to:
                    cmd_parts.append(f"remap_schema={remap_from}:{remap_to}")
            
            content = self.content_combo.get()
            if content != "ALL":
                cmd_parts.append(f"content={content}")
            
            parallel = self.parallel_spin.get()
            if parallel != "1":
                cmd_parts.append(f"parallel={parallel}")
            
            compression = self.compression_combo.get()
            if compression != "NONE":
                cmd_parts.append(f"compression={compression}")
            
            extra = self.extra_entry.get().strip()
            if extra:
                cmd_parts.extend(extra.split())
            
            cmd_str = subprocess.list2cmdline(cmd_parts)
            self.cmd_text.config(state=tk.NORMAL)
            self.cmd_text.delete("1.0", tk.END)
            self.cmd_text.insert(tk.END, cmd_str)
            self.cmd_text.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate command: {e}")
    
    def run_datapump(self):
        cmd_str = self.cmd_text.get("1.0", tk.END).strip()
        if not cmd_str:
            messagebox.showwarning("No command", "Generate a command first.")
            return
        self.btn_run.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        if self.ssh_client:
            _, _, _, _, conn_service = self._get_target_db_fields()
            env_prefix = f"export ORACLE_SID={conn_service}; export ORAENV_ASK=NO; . /usr/local/bin/oraenv; "
            full_remote_cmd = env_prefix + cmd_str
            self._run_remote_cmd(full_remote_cmd, on_finish=self._on_datapump_finish, tag="DataPump")
        else:
            self._clear_output()
            self.dp_process = subprocess.Popen(cmd_str, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, universal_newlines=True)
            self.dp_queue = queue.Queue()
            self.dp_thread = threading.Thread(target=self._read_local_output, args=(self.dp_process.stdout,), daemon=True)
            self.dp_thread.start()
            self.after_id = self.root.after(100, self._process_local_output)
    
    def _read_local_output(self, stream):
        try:
            for line in iter(stream.readline, ''):
                self.dp_queue.put(line)
            stream.close()
        except Exception:
            pass
        finally:
            self.dp_queue.put(None)
    
    def _process_local_output(self):
        try:
            while True:
                line = self.dp_queue.get_nowait()
                if line is None:
                    self._on_process_finished()
                    return
                self._log_now(line.rstrip())
        except queue.Empty:
            pass
        self.after_id = self.root.after(100, self._process_local_output)
    
    def _on_process_finished(self):
        self.btn_run.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.dp_process = None
        self.status.set("DataPump job completed")
    
    def _on_datapump_finish(self):
        self.btn_run.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.status.set("DataPump job completed")
    
    # ====================== Output Utilities ======================
    def _clear_output(self):
        if hasattr(self, 'output_text'):
            self.output_text.config(state=tk.NORMAL)
            self.output_text.delete("1.0", tk.END)
            self.output_text.config(state=tk.DISABLED)
    
    def clear_output(self):
        self._clear_output()
    
    def _log_now(self, message):
        if hasattr(self, 'output_text'):
            self.output_text.config(state=tk.NORMAL)
            self.output_text.insert(tk.END, message + "\n")
            self.output_text.see(tk.END)
            self.output_text.config(state=tk.DISABLED)
    
    def clear_transfer_output(self):
        self.transfer_output.config(state=tk.NORMAL)
        self.transfer_output.delete("1.0", tk.END)
        self.transfer_output.config(state=tk.DISABLED)
    
    def _log_transfer(self, message):
        self.transfer_output.config(state=tk.NORMAL)
        self.transfer_output.insert(tk.END, message + "\n")
        self.transfer_output.see(tk.END)
        self.transfer_output.config(state=tk.DISABLED)
    
    # ====================== File Transfer Methods ======================
    def autofill_source_path(self):
        if self.engine is None:
            messagebox.showwarning("Not connected", "Connect to DB1 first.")
            return
        dp_directory = self.dir_entry.get().strip() if hasattr(self, 'dir_entry') else "DATA_PUMP"
        if not dp_directory:
            messagebox.showwarning("Missing directory", "Enter a DataPump directory name in the DataPump tab first.")
            return
        query = "SELECT directory_path FROM dba_directories WHERE directory_name = :dir"
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query), {"dir": dp_directory.upper()})
                row = result.fetchone()
                if row is None:
                    messagebox.showwarning("Not found", f"Directory '{dp_directory}' not found in DB1.")
                    return
                self.source_path.delete(0, tk.END)
                self.source_path.insert(0, row[0])
                self._log_transfer(f"Found source path: {row[0]}")
        except Exception as e:
            messagebox.showerror("Query error", str(e))
    
    def autofill_dest_path(self):
        if self.engine2 is None:
            messagebox.showwarning("Not connected", "Connect to DB2 first.")
            return
        dp_directory = self.dir_entry.get().strip() if hasattr(self, 'dir_entry') else "DATA_PUMP"
        if not dp_directory:
            messagebox.showwarning("Missing directory", "Enter a DataPump directory name in the DataPump tab first.")
            return
        query = "SELECT directory_path FROM dba_directories WHERE directory_name = :dir"
        try:
            with self.engine2.connect() as conn:
                result = conn.execute(text(query), {"dir": dp_directory.upper()})
                row = result.fetchone()
                if row is None:
                    messagebox.showwarning("Not found", f"Directory '{dp_directory}' not found in DB2.")
                    return
                self.dest_path.delete(0, tk.END)
                self.dest_path.insert(0, row[0])
                self._log_transfer(f"Found destination path: {row[0]}")
        except Exception as e:
            messagebox.showerror("Query error", str(e))
    
    def transfer_files(self):
        # Automatically use the dump/log file names from the DataPump tab
        dumpfile = self.dumpfile_entry.get().strip()
        logfile = self.logfile_entry.get().strip()
        source_dir = self.source_path.get().strip()
        dest_dir = self.dest_path.get().strip()
        if not dumpfile and not logfile:
            messagebox.showwarning("Missing files", "No dump/log file names set in DataPump tab.")
            return
        if not source_dir or not dest_dir:
            messagebox.showwarning("Missing paths", "Enter both source and destination paths.")
            return
        src_host = self.ssh_source_host.get().strip()
        src_port = int(self.ssh_source_port.get().strip())
        src_user = self.ssh_source_user.get().strip()
        src_pass = self.ssh_source_pass.get()
        dst_host = self.ssh_dest_host.get().strip()
        dst_port = int(self.ssh_dest_port.get().strip())
        dst_user = self.ssh_dest_user.get().strip()
        dst_pass = self.ssh_dest_pass.get()
        if not all([src_host, src_user, src_pass, dst_host, dst_user, dst_pass]):
            messagebox.showwarning("Missing SSH credentials", "Fill all SSH fields for source and destination.")
            return
        self.transfer_btn.config(state=tk.DISABLED)
        self._log_transfer("=== Starting direct server‑to‑server file transfer ===")
        def worker():
            src_ssh = None
            dst_ssh = None
            try:
                files = [f for f in (dumpfile, logfile) if f]
                self._log_transfer("Connecting to source server...")
                src_ssh = paramiko.SSHClient()
                src_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                src_ssh.connect(src_host, port=src_port, username=src_user, password=src_pass)
                src_sftp = src_ssh.open_sftp()
                self._log_transfer("Connecting to destination server...")
                dst_ssh = paramiko.SSHClient()
                dst_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                dst_ssh.connect(dst_host, port=dst_port, username=dst_user, password=dst_pass)
                dst_sftp = dst_ssh.open_sftp()
                for f in files:
                    remote_src = os.path.join(source_dir, f).replace("\\", "/")
                    remote_dst = os.path.join(dest_dir, f).replace("\\", "/")
                    self._log_transfer(f"Transferring {remote_src} -> {remote_dst}")
                    with io.BytesIO() as buffer:
                        src_sftp.getfo(remote_src, buffer)
                        buffer.seek(0)
                        dst_sftp.putfo(buffer, remote_dst)
                src_sftp.close()
                dst_sftp.close()
                self._log_transfer("✅ Direct transfer completed successfully.")
            except Exception as e:
                self._log_transfer(f"❌ Transfer failed: {e}")
            finally:
                if src_ssh: src_ssh.close()
                if dst_ssh: dst_ssh.close()
                self.root.after(0, lambda: self.transfer_btn.config(state=tk.NORMAL))
        threading.Thread(target=worker, daemon=True).start()
    
    # ====================== Database Objects Comparison ======================
    def compare_objects(self):
        if self.engine is None or self.engine2 is None:
            messagebox.showwarning("Not connected", "Both DB1 and DB2 must be connected.")
            return
        for row in self.compare_tree.get_children():
            self.compare_tree.delete(row)
        object_types = ["FUNCTION", "INDEX", "LOB", "PACKAGE", "PACKAGE BODY", "PROCEDURE", "SEQUENCE", "SYNONYM", "TABLE", "TRIGGER"]
        def get_objects(engine, obj_type):
            try:
                with engine.connect() as conn:
                    result = conn.execute(text("SELECT object_name FROM user_objects WHERE object_type = :t"), {"t": obj_type})
                    return {row[0] for row in result}, result.rowcount
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Query Error", f"Error in {obj_type}: {e}"))
                return None, 0
        self.status.set("Comparing objects...")
        def compare_thread():
            for obj_type in object_types:
                names1, count1 = get_objects(self.engine, obj_type)
                if names1 is None: continue
                names2, count2 = get_objects(self.engine2, obj_type)
                if names2 is None: continue
                missing = sorted(names1 - names2)
                missing_str = ", ".join(missing) if missing else "None"
                self.root.after(0, lambda t=obj_type, c1=count1, c2=count2, m=missing_str: self.compare_tree.insert("", tk.END, values=(t, c1, c2, m)))
            self.root.after(0, lambda: self.status.set("Comparison completed."))
        threading.Thread(target=compare_thread, daemon=True).start()
    
    def on_closing(self):
        if self.dp_process and self.dp_process.poll() is None:
            self.dp_process.terminate()
        if self.dp_channel and not self.dp_channel.closed:
            self.dp_channel.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = DbClientApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()