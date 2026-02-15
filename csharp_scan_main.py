"""
C# Code Mapper Pro

A Tkinter desktop application for exploring source-code structure through:
- a tree-based entity explorer
- an interactive node-link diagram
- a synchronized source-code viewer

Key capabilities:
- Multi-language structural parsing with language detection
- Theme management with persistent configuration
- Diagram interaction (zoom, click-to-navigate)
- Tree/code/diagram synchronization
- History tracking and screenshot export
"""

from fileinput import filename
from logging import config
import tkinter as tk
from tkinter import Scrollbar, ttk, filedialog, messagebox, simpledialog, scrolledtext
import tkinter.font as tkfont
import re, os, json, difflib
import sys
import importlib.util
from datetime import datetime


def collect_missing_prerequisites(version_info=None, module_checker=None):
    """Return a list of missing prerequisites needed to run the application."""
    version_info = version_info or sys.version_info
    module_checker = module_checker or importlib.util.find_spec
    missing = []

    if (version_info.major, version_info.minor) < (3, 9):
        missing.append(f"Python 3.9+ required (detected {version_info.major}.{version_info.minor}).")

    required_modules = [
        ("tkinter", "Tkinter is required. On Linux install python3-tk."),
        ("PIL", "Pillow is required for PNG screenshots. Install: pip install pillow"),
    ]
    for module_name, install_hint in required_modules:
        if module_checker(module_name) is None:
            missing.append(install_hint)

    return missing


def verify_runtime_prerequisites():
    """
    Validate runtime requirements.
    If requirements are missing, show a popup with install guidance and return False.
    """
    missing = collect_missing_prerequisites()
    if not missing:
        return True

    detail = "\n".join(f"- {item}" for item in missing)
    message = (
        "C# Code Mapper Pro cannot start because prerequisites are missing:\n\n"
        f"{detail}\n\n"
        "Install the missing items and restart."
    )
    try:
        boot = tk.Tk()
        boot.withdraw()
        messagebox.showerror("Missing Prerequisites", message)
        boot.destroy()
    except Exception:
        print(message)
    return False

class ConfigHandler:    
    """Small helper for mapping loaded JSON dictionaries to object attributes."""
    def __init__(self, d):
        self.__dict__ = d

    @classmethod
    def from_json(cls, fh):
        return cls(json.load(fh))

class LineNumberCanvas(tk.Canvas):
    """Canvas used to render line numbers for the code text widget."""
    def __init__(self, master, text_widget, **kwargs):
        super().__init__(master, **kwargs)
        self.text_widget = text_widget
        self.line_color = "#606060"
    def redraw(self, *args):
        self.delete("all")
        i = self.text_widget.index("@0,0")
        while True:
            dline = self.text_widget.dlineinfo(i)
            if dline is None: break
            linenum = str(i).split(".")[0]
            self.create_text(35, dline[1], anchor="ne", text=linenum, fill=self.line_color, font=("Consolas", 10))
            i = self.text_widget.index("%s + 1line" % i)
    def set_theme(self, bg, fg):
        self.configure(bg=bg)
        self.line_color = fg

class CSharpProMapper:
    """Main application controller for UI, parsing, visualization, and persistence."""
    def __init__(self, root):
        self.root = root
        self.root.title("C# Code Mapper Pro")
        self.config_file = "config.json"
        #self.config = {"theme": "light", "history": [], "auto_parse": False, "show_diff": True, "window_size": "1400x900"}
       # self.load_config()
        self.config = self.load_config(self.config_file) or {"theme": "dark", "history": [], "auto_parse": False, "show_diff": True, "window_size": "1400x900"}
        self.config.setdefault("theme", "dark")
        self.config.setdefault("history", [])
        self.config.setdefault("window_size", "1400x900")
        self.max_history_items = 12
        try:
            self.root.geometry(self.config["window_size"])
        except tk.TclError:
            pass
        
        self.tabs_data = {}
        self.setup_ui()
        self.apply_theme(self.config["theme"])
        self.root.protocol("WM_DELETE_WINDOW", self.safe_exit)
        self.log("Application Initialized.")

    def get_available_themes(self):
        return {
            "dark": {
                "label": "Dark",
                "bg": "#2d2d2d",
                "fg": "#f0f0f0",
                "accent_class_fill": "#4a77b4",
                "accent_method_fill": "#3a9e6f",
                "line_main": "#b0b0b0",
                "line_sub": "#808080",
                "node_root": "#8f8f8f",
                "line_number": "#a0a0a0",
                "tree_class_fg": "#76b7ff",
                "tree_method_fg": "#73dca2",
                "tree_variable_fg": "#f2c879",
                "accent_variable_fill": "#d9b16f",
                "scroll_bg": "#3a3a3a",
                "scroll_trough": "#232323",
                "scroll_active": "#4d4d4d",
                "tree_selected_bg": "#4a77b4",
                "tree_selected_fg": "#ffffff",
                "nav_line_bg": "#525252",
            },
            "light": {
                "label": "Light",
                "bg": "#f0f0f0",
                "fg": "#2d2d2d",
                "accent_class_fill": "#b7d8ff",
                "accent_method_fill": "#bcefd2",
                "line_main": "#404040",
                "line_sub": "#6a6a6a",
                "node_root": "#a0a0a0",
                "line_number": "#606060",
                "tree_class_fg": "#1b5fa8",
                "tree_method_fg": "#1b7c4e",
                "tree_variable_fg": "#9d6f12",
                "accent_variable_fill": "#f2d59d",
                "scroll_bg": "#d9d9d9",
                "scroll_trough": "#efefef",
                "scroll_active": "#c8c8c8",
                "tree_selected_bg": "#b7d8ff",
                "tree_selected_fg": "#202020",
                "nav_line_bg": "#d6e7ff",
            },
            "monochrome": {
                "label": "Monochrome (Lime)",
                "bg": "#000000",
                "fg": "#7CFC00",
                "accent_class_fill": "#113300",
                "accent_method_fill": "#001a00",
                "line_main": "#66ff66",
                "line_sub": "#33cc33",
                "node_root": "#194d19",
                "line_number": "#66ff66",
                "tree_class_fg": "#99ff66",
                "tree_method_fg": "#7CFC00",
                "tree_variable_fg": "#b6ff8a",
                "accent_variable_fill": "#0d2a00",
                "scroll_bg": "#0c0c0c",
                "scroll_trough": "#000000",
                "scroll_active": "#1a1a1a",
                "tree_selected_bg": "#194d19",
                "tree_selected_fg": "#b6ff8a",
                "nav_line_bg": "#0f2d0f",
            },
        }

    def get_theme_colors(self, theme):
        themes = self.get_available_themes()
        return themes.get(theme, themes["dark"])
        
    def load_config(self, filename='config.json'):
        #"""Loads configuration data from a JSON file."""
        # Build the full file path relative to the script location
        config_path = os.path.join(os.path.dirname(__file__), filename)
        try:
            with open(config_path, 'r') as config_file:
                config_data = json.load(config_file)
            return config_data
        except FileNotFoundError:
            print(f"Error: The configuration file '{filename}' was not found at {config_path}")
            return None
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from the file '{filename}'")
            return None

    def save_config(self):
        config_path = os.path.join(os.path.dirname(__file__), self.config_file)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2)

    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.terminal.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.terminal.see(tk.END)
        
    def setup_ui(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open File", command=self.open_file)
        file_menu.add_command(label="Save Diagram Screenshot...", command=self.save_diagram_screenshot)
        self.hist_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Recent Files", menu=self.hist_menu)
        menubar.add_cascade(label="File", menu=file_menu)

        sections_menu = tk.Menu(menubar, tearoff=0)
        self.v_tree = tk.BooleanVar(value=True); self.v_graph = tk.BooleanVar(value=True); self.v_code = tk.BooleanVar(value=True)
        sections_menu.add_checkbutton(label="Tree Explorer", variable=self.v_tree, command=self.toggle_layout)
        sections_menu.add_checkbutton(label="Visual Graph", variable=self.v_graph, command=self.toggle_layout)
        sections_menu.add_checkbutton(label="Code Preview", variable=self.v_code, command=self.toggle_layout)
        menubar.add_cascade(label="Sections", menu=sections_menu)

        settings_menu = tk.Menu(menubar, tearoff=0)
        self.theme_menu = tk.Menu(settings_menu, tearoff=0)
        settings_menu.add_cascade(label="Themes", menu=self.theme_menu)
        settings_menu.add_separator()
        settings_menu.add_command(label="Zoom In Diagram", command=lambda: self.zoom_current_diagram(1.1))
        settings_menu.add_command(label="Zoom Out Diagram", command=lambda: self.zoom_current_diagram(0.9))
        settings_menu.add_command(label="Reset Diagram Zoom", command=self.reset_current_diagram_zoom)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        self.root.config(menu=menubar)
        self.refresh_history_menu()
        self.refresh_theme_menu()
        self.root.bind("<Control-equal>", lambda _e: self.zoom_current_diagram(1.1))
        self.root.bind("<Control-plus>", lambda _e: self.zoom_current_diagram(1.1))
        self.root.bind("<Control-minus>", lambda _e: self.zoom_current_diagram(0.9))
        self.root.bind("<Control-0>", lambda _e: self.reset_current_diagram_zoom())
      

        self.main_pane = tk.PanedWindow(self.root, orient=tk.VERTICAL, sashrelief=tk.RAISED,width=900, height=400)
        self.main_pane.pack(fill=tk.BOTH, expand=True)
        self.notebook = ttk.Notebook(self.main_pane)
        self.main_pane.add(self.notebook, stretch="always")
        self.terminal = tk.Text(self.main_pane, bg="#1e1e1e", fg="white", font=("Consolas", 10))
        sbY = Scrollbar(self.terminal,orient=tk.VERTICAL, bg=self.ret_Theme(self.config["theme"])["bg"])
        sbW = Scrollbar(self.terminal,orient=tk.HORIZONTAL)
        sbY.pack(side=tk.RIGHT,fill=tk.Y)
        sbW.pack(side=tk.BOTTOM,fill=tk.X)
        sbY.configure(command=self.terminal.yview)
        sbW.configure(command=self.terminal.xview)
        self.terminal.configure(yscrollcommand=sbY.set, xscrollcommand=sbW.set)
        self.main_pane.add(self.terminal, minsize=80)
        self.apply_scrollbar_theme()
        self.console_auto_layout = True
        self.main_pane.bind("<Configure>", lambda _e: self.schedule_main_pane_layout())
        self.main_pane.bind("<ButtonRelease-1>", self.on_main_pane_mouse_release, add="+")
        self.schedule_main_pane_layout()
       
        #vsb = tk.Scrollbar(self.terminal, orient="vertical", command=self.terminal.yview)
        #hsb = tk.Scrollbar(self.terminal, orient="horizontal", command=self.terminal.xview)
       # self.terminal.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        #vsb.pack(side=tk.RIGHT, fill=tk.Y)
       # hsb.pack(side=tk.BOTTOM, fill=tk.X)
       # self.terminal.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        
        
    def refresh_theme_menu(self):
        self.theme_menu.delete(0, tk.END)
        selected_theme = self.config.get("theme", "dark")
        for theme_key, theme_data in self.get_available_themes().items():
            label = theme_data.get("label", theme_key)
            if theme_key == selected_theme:
                label = f"{label} (Current)"
            self.theme_menu.add_command(label=label, command=lambda k=theme_key: self.select_theme(k))

    def select_theme(self, theme):
        self.apply_theme(theme)
        self.save_config()
   
    def apply_theme(self, theme):
        if theme not in self.get_available_themes():
            theme = "dark"
        self.config["theme"] = theme
        colors = self.get_theme_colors(theme)
        self.theme_colors = colors

        self.root.configure(bg=colors["bg"])
        style = ttk.Style()
        style.theme_use('clam') # Use a theme that supports coloring
        style.configure("Treeview", background=colors["bg"], foreground=colors["fg"], fieldbackground=colors["bg"])
        style.map(
            "Treeview",
            background=[("selected", colors["tree_selected_bg"])],
            foreground=[("selected", colors["tree_selected_fg"])],
        )
        style.configure("TNotebook", background=colors["bg"])
        style.configure("TFrame", background=colors["bg"])
        style.configure("TPanedwindow", background=colors["bg"])
        style.configure("TNotebook.Tab", background=colors["scroll_bg"], foreground=colors["fg"])
        style.map("TNotebook.Tab", background=[("selected", colors["bg"])], foreground=[("selected", colors["fg"])])

        if hasattr(self, "main_pane"):
            self.main_pane.configure(bg=colors["bg"])
        if hasattr(self, "terminal"):
            self.terminal.configure(bg=colors["bg"], fg=colors["fg"], insertbackground=colors["fg"])

        self.apply_scrollbar_theme()
        self.refresh_all_tabs()
        if hasattr(self, "theme_menu"):
            self.refresh_theme_menu()
        self.log(f"Theme set to {theme}")

    def ret_Theme(self, theme):
        colors = self.get_theme_colors(theme)
        return {"bg": colors["bg"], "fg": colors["fg"]}

    def apply_scrollbar_theme(self):
        if not hasattr(self, "theme_colors"):
            return
        colors = self.theme_colors
        widgets = [self.root]
        while widgets:
            w = widgets.pop()
            try:
                widgets.extend(w.winfo_children())
            except tk.TclError:
                continue
            if isinstance(w, tk.Scrollbar):
                try:
                    w.configure(
                        bg=colors["scroll_bg"],
                        troughcolor=colors["scroll_trough"],
                        activebackground=colors["scroll_active"],
                        highlightthickness=0,
                        bd=0,
                    )
                except tk.TclError:
                    pass

    def refresh_all_tabs(self):
        for tid in list(self.tabs_data.keys()):
            if tid in self.tabs_data:
                self.refresh_tab(tid)
        
    def open_file(self):
        p = filedialog.askopenfilename(
            filetypes=[
                ("Supported Source Files", "*.cs *.java *.js *.jsx *.ts *.tsx *.py *.go *.rs *.cpp *.cc *.cxx *.c *.h *.hpp *.php *.swift *.kt *.kts *.scala *.dart *.rb *.lua *.pl *.r *.m *.mm *.sol *.fs *.fsi *.fsx *.vb *.pas *.nim *.zig *.hs *.ex *.exs *.erl *.clj *.groovy *.mal *.mbg *.malbolge"),
                ("All Files", "*.*"),
            ]
        )
        if p:
            self.create_tab(p)
            self.add_recent_file(p)

    def open_recent_file(self, path):
        if os.path.exists(path):
            self.create_tab(path)
            self.add_recent_file(path)
        else:
            self.config["history"] = [p for p in self.config.get("history", []) if p != path]
            self.refresh_history_menu()
            self.save_config()
            messagebox.showwarning("Missing File", f"Recent file not found:\n{path}")

    def add_recent_file(self, path):
        norm = os.path.abspath(path)
        history = [p for p in self.config.get("history", []) if os.path.exists(p)]
        if norm in history:
            history.remove(norm)
        history.insert(0, norm)
        self.config["history"] = history[:self.max_history_items]
        self.refresh_history_menu()
        self.save_config()

    def refresh_history_menu(self):
        self.hist_menu.delete(0, tk.END)
        history = [p for p in self.config.get("history", []) if os.path.exists(p)]
        self.config["history"] = history[:self.max_history_items]
        if not self.config["history"]:
            self.hist_menu.add_command(label="(empty)", state=tk.DISABLED)
            return
        for path in self.config["history"]:
            self.hist_menu.add_command(label=path, command=lambda p=path: self.open_recent_file(p))

    def create_tab(self, path):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=os.path.basename(path))
        self.notebook.select(tab)
        currenttheme = self.config["theme"]
        pw = tk.PanedWindow(tab, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, bg=self.ret_Theme(currenttheme)["bg"])
        pw.pack(fill=tk.BOTH, expand=True)

        t_f = tk.Frame(pw); tree = ttk.Treeview(t_f, columns=("kind",), show="tree headings")
        tree.heading("#0", text="Scoped Structure")
        tree.heading("kind", text="Type")
        tree.column("#0", width=260, stretch=True)
        tree.column("kind", width=110, anchor="center", stretch=False)
        tree.pack(fill=tk.BOTH, expand=True)
        pw.add(t_f, width=75)
        
        g_f = tk.Frame(pw); canvas = tk.Canvas(g_f, bg=self.ret_Theme(currenttheme)["bg"])
        canvas.pack(fill=tk.BOTH, expand=True)
        pw.add(g_f, width=350)


        c_f = tk.Frame(pw); txt = tk.Text(c_f, font=("Consolas", 10), wrap=tk.NONE, bg=self.ret_Theme(currenttheme)["bg"], fg=self.ret_Theme(currenttheme)["fg"])
        ln = LineNumberCanvas(c_f, txt, width=5, highlightthickness=0); ln.pack(side=tk.LEFT, fill=tk.Y)
        txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        pw.add(c_f, width=500)

        tid = str(tab)
        self.tabs_data[tid] = {
            "path": path,
            "pw": pw,
            "t_f": t_f,
            "g_f": g_f,
            "c_f": c_f,
            "tree": tree,
            "canvas": canvas,
            "code": txt,
            "line_numbers": ln,
            "canvas_item_to_tree": {},
            "zoom": 1.0,
            "tree_columns_manual": False,
            "tree_resize_started": False,
        }
        tree.bind("<<TreeviewSelect>>", lambda _e, tab_id=tid: self.on_tree_select(tab_id))
        tree.bind("<ButtonPress-1>", lambda e, tab_id=tid: self.on_tree_press(tab_id, e))
        tree.bind("<ButtonRelease-1>", lambda e, tab_id=tid: self.on_tree_release(tab_id, e))
        canvas.bind("<Button-1>", lambda e, tab_id=tid: self.on_canvas_click(tab_id, e))
        canvas.bind("<Control-MouseWheel>", lambda e, tab_id=tid: self.on_canvas_zoom(tab_id, e))
        canvas.bind("<Control-Button-4>", lambda e, tab_id=tid: self.on_canvas_zoom(tab_id, e, 1.1))
        canvas.bind("<Control-Button-5>", lambda e, tab_id=tid: self.on_canvas_zoom(tab_id, e, 0.9))
        pw.bind("<Configure>", lambda _e, tab_id=tid: self.schedule_tab_proportions(tab_id))

        sbT = Scrollbar(self.tabs_data[tid]["tree"],orient=tk.VERTICAL)
        sbT.pack(side=tk.RIGHT,fill=tk.Y)
        sbT.configure(command=self.tabs_data[tid]["tree"].yview)
        self.tabs_data[tid]["tree"].configure(yscrollcommand=sbT.set)
        sbT_W = Scrollbar(tree, orient=tk.HORIZONTAL)
        sbT_W.pack(side=tk.BOTTOM,fill=tk.X)
        sbT_W.configure(command=self.tabs_data[tid]["tree"].xview)
        self.tabs_data[tid]["tree"].configure(xscrollcommand=sbT_W.set)
        
        sbC = Scrollbar(self.tabs_data[tid]["canvas"],orient=tk.VERTICAL)
        sbC.pack(side=tk.RIGHT,fill=tk.Y)
        sbC.configure(command=self.tabs_data[tid]["canvas"].yview)
        self.tabs_data[tid]["canvas"].configure(yscrollcommand=sbC.set)
        sbC_W = Scrollbar(canvas, orient=tk.HORIZONTAL)
        sbC_W.pack(side=tk.BOTTOM,fill=tk.X)
        sbC_W.configure(command=self.tabs_data[tid]["canvas"].xview)
        self.tabs_data[tid]["canvas"].configure(xscrollcommand=sbC_W.set)
               
        sbCd = Scrollbar(self.tabs_data[tid]["code"],orient=tk.VERTICAL)
        sbCd.pack(side=tk.RIGHT,fill=tk.Y)
        sbCd.configure(command=self.tabs_data[tid]["code"].yview)
        self.tabs_data[tid]["code"].configure(yscrollcommand=sbCd.set)
        sbCd_W = Scrollbar(self.tabs_data[tid]["code"], orient=tk.HORIZONTAL)
        sbCd_W.pack(side=tk.BOTTOM,fill=tk.X)
        sbCd_W.configure(command=self.tabs_data[tid]["code"].xview)
        self.tabs_data[tid]["code"].configure(xscrollcommand=sbCd_W.set)

        self.refresh_tab(tid)
        self.schedule_tab_proportions(tid)
        self.apply_scrollbar_theme()

    def schedule_tab_proportions(self, tid):
        self.root.after_idle(lambda tab_id=tid: self.apply_tab_proportions(tab_id))

    def apply_tab_proportions(self, tid):
        if tid not in self.tabs_data:
            return
        t = self.tabs_data[tid]
        pw = t["pw"]
        panes = pw.panes()
        total_w = pw.winfo_width()
        if total_w <= 1 or len(panes) < 2:
            return

        tree_visible = str(t["t_f"]) in panes
        graph_visible = str(t["g_f"]) in panes
        code_visible = str(t["c_f"]) in panes
        if tree_visible and graph_visible and code_visible and len(panes) >= 3:
            tree_w = max(140, int(total_w * 0.15))
            graph_w = max(220, int((total_w - tree_w) * 0.5))
            pw.sash_place(0, tree_w, 0)
            pw.sash_place(1, tree_w + graph_w, 0)
            return

        if tree_visible and graph_visible and not code_visible and len(panes) >= 2:
            tree_w = max(140, int(total_w * 0.15))
            pw.sash_place(0, tree_w, 0)
            return

        if tree_visible and code_visible and not graph_visible and len(panes) >= 2:
            tree_w = max(140, int(total_w * 0.15))
            pw.sash_place(0, tree_w, 0)
            return

        if not tree_visible and graph_visible and code_visible and len(panes) >= 2:
            pw.sash_place(0, int(total_w * 0.5), 0)

    def schedule_main_pane_layout(self):
        self.root.after_idle(self.apply_main_pane_layout)

    def apply_main_pane_layout(self):
        if not getattr(self, "console_auto_layout", False):
            return
        if len(self.main_pane.panes()) < 2:
            return
        total_h = self.main_pane.winfo_height()
        if total_h <= 1:
            return
        notebook_h = int(total_h * 0.85)
        self.main_pane.sash_place(0, 0, notebook_h)

    def on_main_pane_mouse_release(self, event):
        if len(self.main_pane.panes()) < 2:
            return
        try:
            _x, sash_y = self.main_pane.sash_coord(0)
        except tk.TclError:
            return
        if abs(event.y - sash_y) <= 10 and self.console_auto_layout:
            self.console_auto_layout = False
            self.log("Console height unlocked by user.")

    def save_diagram_screenshot(self):
        tid = self.notebook.select()
        if tid not in self.tabs_data:
            messagebox.showinfo("No Diagram", "Open a file tab first to save a diagram screenshot.")
            return
        canvas = self.tabs_data[tid]["canvas"]
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("PostScript", "*.ps")],
            title="Save Diagram Screenshot",
        )
        if not file_path:
            return

        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".ps":
            canvas.postscript(file=file_path, colormode="color")
            self.log(f"Diagram saved: {file_path}")
            return

        try:
            from PIL import ImageGrab
            self.root.update_idletasks()
            x = canvas.winfo_rootx()
            y = canvas.winfo_rooty()
            w = canvas.winfo_width()
            h = canvas.winfo_height()
            img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
            img.save(file_path)
            self.log(f"Diagram saved: {file_path}")
        except Exception as ex:
            fallback = os.path.splitext(file_path)[0] + ".ps"
            canvas.postscript(file=fallback, colormode="color")
            messagebox.showwarning("PNG Save Failed", f"Could not save PNG ({ex}). Saved PostScript instead:\n{fallback}")
            self.log(f"PNG save failed, fallback saved: {fallback}")

    def on_canvas_zoom(self, tid, event, fixed_factor=None):
        if tid not in self.tabs_data:
            return "break"
        if fixed_factor is not None:
            factor = fixed_factor
        else:
            delta = getattr(event, "delta", 0)
            factor = 1.1 if delta > 0 else 0.9
        self.zoom_diagram(tid, factor, event.x, event.y)
        return "break"

    def zoom_current_diagram(self, factor):
        tid = self.notebook.select()
        if tid in self.tabs_data:
            self.zoom_diagram(tid, factor)

    def reset_current_diagram_zoom(self):
        tid = self.notebook.select()
        if tid not in self.tabs_data:
            return
        current_zoom = self.tabs_data[tid].get("zoom", 1.0)
        if abs(current_zoom - 1.0) < 0.001:
            return
        self.zoom_diagram(tid, 1.0 / current_zoom)
        self.tabs_data[tid]["zoom"] = 1.0

    def zoom_diagram(self, tid, factor, event_x=None, event_y=None):
        info = self.tabs_data.get(tid)
        if not info:
            return
        canvas = info["canvas"]
        old_zoom = info.get("zoom", 1.0)
        new_zoom = max(0.4, min(3.0, old_zoom * factor))
        applied_factor = new_zoom / old_zoom
        if abs(applied_factor - 1.0) < 0.0001:
            return

        if event_x is None or event_y is None:
            cx = canvas.canvasx(canvas.winfo_width() / 2)
            cy = canvas.canvasy(canvas.winfo_height() / 2)
        else:
            cx = canvas.canvasx(event_x)
            cy = canvas.canvasy(event_y)

        canvas.scale("all", cx, cy, applied_factor, applied_factor)
        bbox = canvas.bbox("all")
        if bbox:
            pad = 80
            canvas.configure(scrollregion=(bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad))
        info["zoom"] = new_zoom
        self.log(f"Diagram zoom: {int(new_zoom * 100)}%")
        
    def refresh_tab(self, tid):
        info = self.tabs_data[tid]
        colors = self.get_theme_colors(self.config["theme"])
        info["pw"].configure(bg=colors["bg"])
        info["t_f"].configure(bg=colors["bg"])
        info["g_f"].configure(bg=colors["bg"])
        info["c_f"].configure(bg=colors["bg"])
        info["canvas"].configure(bg=colors["bg"])
        info["code"].configure(bg=colors["bg"], fg=colors["fg"], insertbackground=colors["fg"])
        info["line_numbers"].set_theme(colors["bg"], colors["line_number"])
        info["tree"].tag_configure("class", foreground=colors["tree_class_fg"])
        info["tree"].tag_configure("method", foreground=colors["tree_method_fg"])
        info["tree"].tag_configure("variable", foreground=colors["tree_variable_fg"])
        info["tree"].tag_configure("root", foreground=colors["fg"])
        with open(info["path"], 'r', encoding='utf-8') as f: lines = f.readlines()
        info["code"].delete("1.0", tk.END); info["code"].insert("1.0", "".join(lines))
        info["line_numbers"].redraw()
        self.parse_scoped(tid, lines)

    def detect_language(self, path, lines):
        """Infer source language from extension and lightweight content heuristics."""
        ext = os.path.splitext(path)[1].lower()
        extension_map = {
            ".cs": "csharp", ".java": "java", ".js": "javascript", ".jsx": "javascript",
            ".ts": "typescript", ".tsx": "typescript", ".py": "python", ".go": "go",
            ".rs": "rust", ".c": "c", ".h": "c", ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp",
            ".hpp": "cpp", ".php": "php", ".swift": "swift", ".kt": "kotlin", ".kts": "kotlin",
            ".scala": "scala", ".dart": "dart", ".rb": "ruby", ".lua": "lua", ".pl": "perl",
            ".r": "r", ".m": "objective-c", ".mm": "objective-c", ".sol": "solidity",
            ".fs": "fsharp", ".fsi": "fsharp", ".fsx": "fsharp", ".vb": "vb", ".pas": "pascal",
            ".nim": "nim", ".zig": "zig", ".hs": "haskell", ".ex": "elixir", ".exs": "elixir",
            ".mal": "malbolge", ".mbg": "malbolge", ".malbolge": "malbolge",
            ".erl": "erlang", ".clj": "clojure", ".groovy": "groovy",
        }
        if ext in extension_map:
            return extension_map[ext]

        head = "\n".join(lines[:3]).lower()
        if head.startswith("#!/") and "python" in head:
            return "python"
        if "using system;" in head or "namespace " in head:
            return "csharp"
        if "public static void main" in head or "import java." in head:
            return "java"
        if "def " in head and ":" in head:
            return "python"
        if "function " in head or "=>" in head:
            return "javascript"
        if any(ch in head for ch in "ji*p</vo"):
            return "malbolge"
        return "unknown"

    def get_language_spec(self, language):
        """Return generic brace-language regex patterns for class/method/variable detection."""
        class_keywords = r"class|interface|struct|record|enum|module"
        if language in {"java"}:
            class_keywords = r"class|interface|enum|record"
        if language in {"javascript", "typescript", "dart"}:
            class_keywords = r"class|interface|enum"
        if language in {"go"}:
            class_keywords = r"struct|interface|type"

        return {
            "comment_prefixes": ("//", "#", "--"),
            "class_re": re.compile(rf"\b(?:{class_keywords})\s+([A-Za-z_]\w*)"),
            "method_patterns": [
                re.compile(r"^(?:(?:public|private|protected|internal|static|virtual|override|async|sealed|new|extern|unsafe|partial|abstract|final|open)\s+)*[\w<>\[\],\.\?:]+\s+([A-Za-z_]\w*)\s*\([^;]*\)"),
                re.compile(r"^\s*func\s+([A-Za-z_]\w*)\s*\("),  # Go
                re.compile(r"^\s*(?:fn|def)\s+([A-Za-z_]\w*)\s*\("),  # Rust/others
                re.compile(r"^\s*function\s+([A-Za-z_]\w*)\s*\("),  # JS/PHP
            ],
            "variable_patterns": [
                re.compile(r"^(?:(?:public|private|protected|internal|static|readonly|const|volatile|final|var|let|mut)\s+)*[\w<>\[\],\.\?:]+\s+([A-Za-z_]\w*)\s*(?:=[^;]*)?;"),
                re.compile(r"^\s*(?:var|let|const)\s+([A-Za-z_]\w*)\s*(?:=|;|$)"),
            ],
        }

    def is_probably_programming_language(self, lines):
        """Heuristic gate used when extension-based language detection is unknown."""
        sample = "\n".join(lines[:120])
        indicators = [
            "class ", "def ", "function ", "func ", "fn ", "public ", "private ",
            "import ", "using ", "namespace ", "return ", "{", "}", ";", "=>",
        ]
        score = sum(1 for marker in indicators if marker in sample)
        return score >= 2

    def _begin_parse(self, tid):
        """Reset parse visuals/state and create a root tree+diagram node."""
        info = self.tabs_data[tid]
        colors = self.get_theme_colors(self.config["theme"])
        info["tree"].delete(*info["tree"].get_children())
        info["canvas"].delete("all")
        info["node_map"] = {}
        info["active_canvas_items"] = []
        info["canvas_item_to_tree"] = {}
        root_node = info["tree"].insert("", "end", text="Project Root", values=("Root",), tags=("root",))
        root_pos = (50, 50)
        root_shape = info["canvas"].create_oval(40, 40, 60, 60, fill=colors["node_root"], outline=colors["line_main"])
        info["canvas_item_to_tree"][root_shape] = root_node
        info["node_map"][root_node] = {"line": 1, "canvas_x": root_pos[0], "canvas_y": root_pos[1], "canvas_items": [root_shape]}
        return info, colors, root_node, root_pos

    def _add_entity(self, info, colors, parent_node, parent_pos, name, kind, line_num, x, y):
        """Add one parsed entity to tree and diagram, and register cross-view mappings."""
        tree_tag = "class" if kind == "Class" else ("method" if kind == "Method" else "variable")
        node = info["tree"].insert(parent_node, "end", text=name, values=(kind,), tags=(tree_tag,), open=True if kind == "Class" else False)
        link_id = info["canvas"].create_line((parent_pos[0] + 10, parent_pos[1]), (x - 35, y), fill=colors["line_main"] if kind == "Class" else colors["line_sub"])
        if kind == "Class":
            shape_id = info["canvas"].create_rectangle(x - 40, y - 15, x + 40, y + 15, fill=colors["accent_class_fill"], outline=colors["line_main"])
            text_id = info["canvas"].create_text(x, y, text=name, font=("Arial", 9, "bold"), fill=colors["fg"])
        elif kind == "Method":
            shape_id = info["canvas"].create_oval(x - 30, y - 12, x + 30, y + 12, fill=colors["accent_method_fill"], outline=colors["line_sub"])
            text_id = info["canvas"].create_text(x, y, text=name, font=("Arial", 8), fill=colors["fg"])
        else:
            shape_id = info["canvas"].create_rectangle(x - 32, y - 12, x + 32, y + 12, fill=colors["accent_variable_fill"], outline=colors["line_sub"])
            text_id = info["canvas"].create_text(x, y, text=name, font=("Arial", 8), fill=colors["fg"])

        for cid in (link_id, shape_id, text_id):
            info["canvas_item_to_tree"][cid] = node
        info["node_map"][node] = {
            "line": line_num,
            "canvas_x": x,
            "canvas_y": y,
            "canvas_items": [link_id, shape_id, text_id],
        }
        return node

    def parse_scoped(self, tid, lines):
        """Language-dispatched parsing entry point for the active tab."""
        info = self.tabs_data[tid]
        language = self.detect_language(info["path"], lines)
        if language == "unknown" and not self.is_probably_programming_language(lines):
            info, _colors, _root_node, _root_pos = self._begin_parse(tid)
            info["canvas"].config(scrollregion=(0, 0, 1200, 300))
            self.autosize_tree_columns(tid)
            self.log(f"Skipped structural parse (not detected as programming language): {os.path.basename(info['path'])}")
            return
        info["language"] = language
        if language == "python":
            self.parse_python_scoped(tid, lines)
        elif language == "malbolge":
            self.parse_malbolge_scoped(tid, lines)
        else:
            self.parse_brace_scoped(tid, lines, language)
        self.autosize_tree_columns(tid)
        self.log(f"Scoped parse complete for {os.path.basename(info['path'])} ({language})")

    def parse_python_scoped(self, tid, lines):
        """Indentation-aware parser for Python class/method/attribute-like structures."""
        info, colors, root_node, root_pos = self._begin_parse(tid)
        class_re = re.compile(r"^\s*class\s+([A-Za-z_]\w*)")
        method_re = re.compile(r"^\s*def\s+([A-Za-z_]\w*)\s*\(")
        var_re = re.compile(r"^\s*(self\.)?([A-Za-z_]\w*)\s*=")

        class_stack = []
        y = 50
        max_x = 430

        for line_num, line in enumerate(lines, 1):
            clean = line.rstrip("\n")
            stripped = clean.strip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(clean) - len(clean.lstrip(" "))
            while class_stack and indent <= class_stack[-1]["indent"]:
                class_stack.pop()

            if m := class_re.match(clean):
                name = m.group(1)
                parent = class_stack[-1] if class_stack else {"tree_id": root_node, "pos": root_pos}
                x = 200 + (len(class_stack) * 180)
                class_node = self._add_entity(info, colors, parent["tree_id"], parent["pos"], name, "Class", line_num, x, y)
                class_stack.append({"name": name, "tree_id": class_node, "pos": (x, y), "indent": indent})
                max_x = max(max_x, x + 220)
                y += 60
                continue

            owner = class_stack[-1] if class_stack else {"tree_id": root_node, "pos": root_pos}
            owner_depth = len(class_stack)
            if m := method_re.match(clean):
                name = m.group(1)
                x = (owner["pos"][0] + 200) if class_stack else 250
                self._add_entity(info, colors, owner["tree_id"], owner["pos"], name, "Method", line_num, x, y)
                max_x = max(max_x, x + 180)
                y += 40
                continue

            if class_stack and indent > class_stack[-1]["indent"] and "(" not in stripped:
                if m := var_re.match(clean):
                    name = m.group(2)
                    x = owner["pos"][0] + 200
                    self._add_entity(info, colors, owner["tree_id"], owner["pos"], name, "Variable", line_num, x, y)
                    max_x = max(max_x, x + 180)
                    y += 35

        info["canvas"].config(scrollregion=(0, 0, max(1200, int(max_x)), y + 100))

    def parse_brace_scoped(self, tid, lines, language):
        """Generic parser for brace-delimited languages (C-like families and similar)."""
        info, colors, root_node, root_pos = self._begin_parse(tid)
        spec = self.get_language_spec(language)
        class_re = spec["class_re"]
        method_patterns = spec["method_patterns"]
        variable_patterns = spec["variable_patterns"]
        comment_prefixes = spec["comment_prefixes"]

        brace_depth = 0
        class_stack = []
        pending_classes = []
        y = 50
        max_x = 430

        for line_num, line in enumerate(lines, 1):
            clean_line = line.strip()
            if not clean_line or clean_line.startswith(comment_prefixes):
                continue

            pre_depth = brace_depth
            open_count = clean_line.count("{")
            close_count = clean_line.count("}")

            while class_stack and pre_depth < class_stack[-1]["depth"]:
                class_stack.pop()
            if pending_classes and open_count > 0:
                pending_classes[0]["depth"] = pre_depth + 1
                class_stack.append(pending_classes.pop(0))

            class_match = class_re.search(clean_line)
            if class_match:
                name = class_match.group(1)
                parent = class_stack[-1] if class_stack else {"tree_id": root_node, "pos": root_pos}
                x = 200 + (len(class_stack) * 180)
                class_node = self._add_entity(info, colors, parent["tree_id"], parent["pos"], name, "Class", line_num, x, y)
                class_entry = {"name": name, "tree_id": class_node, "pos": (x, y), "depth": None}
                if open_count > 0:
                    class_entry["depth"] = pre_depth + 1
                    class_stack.append(class_entry)
                else:
                    pending_classes.append(class_entry)
                max_x = max(max_x, x + 220)
                y += 60
            else:
                in_class_scope = class_stack and pre_depth == class_stack[-1]["depth"]
                owner = class_stack[-1] if in_class_scope else {"tree_id": root_node, "pos": root_pos}
                owner_is_root = not in_class_scope

                member_name = None
                member_kind = None
                for mp in method_patterns:
                    m = mp.search(clean_line)
                    if m:
                        member_name = m.group(1)
                        member_kind = "Method"
                        break
                if not member_name:
                    for vp in variable_patterns:
                        m = vp.search(clean_line)
                        if m:
                            member_name = m.group(1)
                            member_kind = "Variable"
                            break

                blocked = {"if", "while", "for", "switch", "catch", "lock", "using", "return"}
                if member_name and member_name not in blocked:
                    x = (owner["pos"][0] + 200) if not owner_is_root else 250
                    self._add_entity(info, colors, owner["tree_id"], owner["pos"], member_name, member_kind, line_num, x, y)
                    max_x = max(max_x, x + 180)
                    y += 40 if member_kind == "Method" else 35

            brace_depth += open_count - close_count
            if brace_depth < 0:
                brace_depth = 0
            while class_stack and class_stack[-1]["depth"] is not None and brace_depth < class_stack[-1]["depth"]:
                class_stack.pop()

        info["canvas"].config(scrollregion=(0, 0, max(1200, int(max_x)), y + 100))

    def parse_malbolge_scoped(self, tid, lines):
        """Specialized parser view for Malbolge: line/op summaries and operation stats."""
        info, colors, root_node, root_pos = self._begin_parse(tid)
        y = 70
        max_x = 430
        max_line_nodes = 120
        op_chars = "ji*p</vo"

        program_node = self._add_entity(info, colors, root_node, root_pos, "Malbolge Program", "Class", 1, 220, y)
        program_pos = (220, y)
        y += 70

        total_ops = 0
        counted_lines = 0
        op_counts = {ch: 0 for ch in op_chars}

        for line_num, line in enumerate(lines, 1):
            # Malbolge typically treats non-space printable chars as program content.
            code_chars = [ch for ch in line if ch not in " \t\r\n"]
            if not code_chars:
                continue
            counted_lines += 1
            total_ops += len(code_chars)
            for ch in code_chars:
                if ch in op_counts:
                    op_counts[ch] += 1

            if counted_lines <= max_line_nodes:
                label = f"Line {line_num} ({len(code_chars)} ops)"
                self._add_entity(info, colors, program_node, program_pos, label, "Method", line_num, 420, y)
                y += 36

        summary_x = 650
        self._add_entity(info, colors, program_node, program_pos, f"Total Ops: {total_ops}", "Variable", 1, summary_x, 120)
        self._add_entity(info, colors, program_node, program_pos, f"Code Lines: {counted_lines}", "Variable", 1, summary_x, 160)
        stats_y = 210
        for op, cnt in op_counts.items():
            if cnt > 0:
                self._add_entity(info, colors, program_node, program_pos, f"'{op}' x {cnt}", "Variable", 1, summary_x, stats_y)
                stats_y += 30

        max_x = max(max_x, summary_x + 220)
        info["canvas"].config(scrollregion=(0, 0, max(1200, int(max_x)), max(y, stats_y) + 120))

    def on_tree_press(self, tid, event):
        if tid not in self.tabs_data:
            return
        tree = self.tabs_data[tid]["tree"]
        self.tabs_data[tid]["tree_resize_started"] = (tree.identify_region(event.x, event.y) == "separator")

    def on_tree_release(self, tid, event):
        if tid not in self.tabs_data:
            return
        if not self.tabs_data[tid].get("tree_resize_started", False):
            return
        self.tabs_data[tid]["tree_resize_started"] = False
        tree = self.tabs_data[tid]["tree"]
        if tree.identify_region(event.x, event.y) == "separator":
            self.tabs_data[tid]["tree_columns_manual"] = True
            self.log("Tree column auto-fit disabled for this tab (manual resize detected).")

    def autosize_tree_columns(self, tid):
        if tid not in self.tabs_data:
            return
        info = self.tabs_data[tid]
        if info.get("tree_columns_manual", False):
            return
        tree = info["tree"]
        if tree.winfo_width() <= 1:
            self.root.after_idle(lambda tab_id=tid: self.autosize_tree_columns(tab_id))
            return

        normal_font = tkfont.nametofont(tree.cget("font"))
        heading_font = tkfont.nametofont("TkHeadingFont")
        pad = 20
        indent_px = 18

        col0_width = heading_font.measure(tree.heading("#0", option="text")) + pad
        kind_width = heading_font.measure(tree.heading("kind", option="text")) + pad

        def measure_item(item_id, depth):
            nonlocal col0_width, kind_width
            item_text = tree.item(item_id, "text") or ""
            # Include indentation so width matches an expanded tree layout.
            col0_width = max(col0_width, normal_font.measure(item_text) + pad + (depth * indent_px))
            vals = tree.item(item_id, "values") or []
            if vals:
                kind_text = str(vals[0])
                kind_width = max(kind_width, normal_font.measure(kind_text) + pad)
            for child in tree.get_children(item_id):
                measure_item(child, depth + 1)

        for top in tree.get_children(""):
            measure_item(top, 0)

        col0_width = max(140, min(900, col0_width))
        kind_width = max(70, min(260, kind_width))
        available = max(220, tree.winfo_width() - 8)
        min_kind = 70
        min_col0 = 120
        # Keep both columns visible inside current widget width.
        if col0_width + kind_width > available:
            kind_width = min(kind_width, max(min_kind, int(available * 0.35)))
            col0_width = max(min_col0, available - kind_width)

        tree.column("kind", minwidth=min_kind, stretch=False)
        tree.column("#0", minwidth=min_col0, stretch=True)
        tree.column("#0", width=col0_width)
        tree.column("kind", width=kind_width)

    def on_tree_select(self, tid, _event=None):
        """Tree selection handler: sync and focus matching code line and diagram entity."""
        if tid not in self.tabs_data:
            return
        info = self.tabs_data[tid]
        tree = info["tree"]
        selected = tree.selection()
        if not selected:
            return
        node_id = selected[0]
        node_data = info.get("node_map", {}).get(node_id)
        if not node_data:
            return

        line_num = max(1, int(node_data.get("line", 1)))
        code = info["code"]
        code.see(f"{line_num}.0")
        code.mark_set("insert", f"{line_num}.0")
        code.tag_configure("nav_line", background=self.theme_colors["nav_line_bg"])
        code.tag_remove("nav_line", "1.0", tk.END)
        code.tag_add("nav_line", f"{line_num}.0", f"{line_num}.0 lineend+1c")

        canvas = info["canvas"]
        target_x = node_data.get("canvas_x")
        target_y = node_data.get("canvas_y")
        items = node_data.get("canvas_items", [])
        if items:
            bbox = canvas.bbox(*items)
            if bbox:
                target_x = (bbox[0] + bbox[2]) / 2
                target_y = (bbox[1] + bbox[3]) / 2
        if target_x is not None and target_y is not None:
            self.scroll_canvas_to(canvas, target_x, target_y)

        for item_id in info.get("active_canvas_items", []):
            try:
                if canvas.type(item_id) != "text":
                    canvas.itemconfigure(item_id, width=1)
            except tk.TclError:
                pass
        active_items = node_data.get("canvas_items", [])
        for item_id in active_items:
            try:
                if canvas.type(item_id) != "text":
                    canvas.itemconfigure(item_id, width=2)
            except tk.TclError:
                pass
        info["active_canvas_items"] = active_items

    def on_canvas_click(self, tid, event):
        """Canvas click handler: resolve entity and route selection back to tree/code."""
        if tid not in self.tabs_data:
            return
        info = self.tabs_data[tid]
        canvas = info["canvas"]
        current = canvas.find_withtag("current")
        item_id = current[0] if current else None
        if item_id is None:
            nearest = canvas.find_closest(canvas.canvasx(event.x), canvas.canvasy(event.y))
            if not nearest:
                return
            item_id = nearest[0]

        tree_id = info.get("canvas_item_to_tree", {}).get(item_id)
        if not tree_id:
            return
        tree = info["tree"]
        tree.selection_set(tree_id)
        tree.focus(tree_id)
        tree.see(tree_id)
        self.on_tree_select(tid)

    def scroll_canvas_to(self, canvas, x, y):
        region = canvas.cget("scrollregion")
        if not region:
            return
        x1, y1, x2, y2 = [float(v) for v in region.split()]
        width = max(1.0, x2 - x1)
        height = max(1.0, y2 - y1)
        view_w = max(1, canvas.winfo_width())
        view_h = max(1, canvas.winfo_height())

        fx = (x - x1 - (view_w / 2)) / width
        fy = (y - y1 - (view_h / 2)) / height
        fx = min(1.0, max(0.0, fx))
        fy = min(1.0, max(0.0, fy))
        canvas.xview_moveto(fx)
        canvas.yview_moveto(fy)

    def toggle_layout(self):
        tid = self.notebook.select()
        if tid in self.tabs_data:
            t = self.tabs_data[tid]
            for f in [t["t_f"], t["g_f"], t["c_f"]]: t["pw"].forget(f)
            if self.v_tree.get(): t["pw"].add(t["t_f"], width=200)
            if self.v_graph.get(): t["pw"].add(t["g_f"], stretch="always")
            if self.v_code.get(): t["pw"].add(t["c_f"], width=500)
            self.schedule_tab_proportions(tid)
            
    def safe_exit(self):
        self.config["window_size"] = self.root.geometry()
        self.save_config()
        self.root.destroy()
if __name__ == "__main__":
    if verify_runtime_prerequisites():
        root = tk.Tk()
        app = CSharpProMapper(root)
        root.mainloop()
