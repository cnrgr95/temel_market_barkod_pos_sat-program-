from tkinter import ttk


def apply_theme(root) -> None:
    style = ttk.Style(root)
    style.theme_use("clam")

    # Global palette inspired by modern POS dashboards.
    style.configure(".", font=("Segoe UI", 10))
    style.configure("TFrame", background="#F4F6FB")
    style.configure("TLabel", background="#F4F6FB", foreground="#1A1F36")
    style.configure("TLabelframe", background="#F4F6FB", foreground="#1A1F36")
    style.configure("TLabelframe.Label", background="#F4F6FB", foreground="#1A1F36", font=("Segoe UI", 10, "bold"))
    style.configure("TButton", padding=6, background="#FFFFFF")
    style.map("TButton", background=[("active", "#EEF2FF")])
    style.configure("Accent.TButton", background="#365CF5", foreground="#FFFFFF")
    style.map("Accent.TButton", background=[("active", "#2D4ED6")], foreground=[("active", "#FFFFFF")])

    style.configure("Treeview", rowheight=26, fieldbackground="#FFFFFF", background="#FFFFFF")
    style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background="#E8ECF7", foreground="#1A1F36")
    style.map("Treeview", background=[("selected", "#DDE7FF")], foreground=[("selected", "#1A1F36")])

    style.configure("Card.TFrame", background="#FFFFFF")
    style.configure("Header.TFrame", background="#1A1F36")
    style.configure("Header.TLabel", background="#1A1F36", foreground="#FFFFFF", font=("Segoe UI", 11, "bold"))
    style.configure("Sidebar.TFrame", background="#11162B")
    style.configure("Sidebar.TButton", background="#11162B", foreground="#DDE3F7", padding=10, anchor="w")
    style.map("Sidebar.TButton", background=[("active", "#1C2444"), ("pressed", "#1C2444")], foreground=[("active", "#FFFFFF")])
