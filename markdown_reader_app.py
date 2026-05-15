import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from pathlib import Path

MAX_RECENT_FILES = 12


class DocumentTab:
    def __init__(self, app, title="Untitled"):
        self.app = app
        self.file_path = None
        self.dirty = False

        self.frame = ttk.PanedWindow(app.notebook, orient=tk.HORIZONTAL)

        self.editor = tk.Text(self.frame, wrap="word", undo=True)
        self.preview = tk.Text(self.frame, wrap="word", state="disabled", bg="#fbfbfb")

        self._setup_preview_tags()

        self.editor.bind("<<Modified>>", self._on_modified)

        self.frame.add(self.editor, weight=3)
        self.frame.add(self.preview, weight=2)

        app.notebook.add(self.frame, text=title)
        app.notebook.select(self.frame)

    def _setup_preview_tags(self):
        self.preview.tag_configure("h1", font=("Segoe UI", 20, "bold"), spacing3=8)
        self.preview.tag_configure("h2", font=("Segoe UI", 16, "bold"), spacing3=6)
        self.preview.tag_configure("h3", font=("Segoe UI", 14, "bold"), spacing3=4)
        self.preview.tag_configure("bold", font=("Segoe UI", 10, "bold"))
        self.preview.tag_configure("italic", font=("Segoe UI", 10, "italic"))
        self.preview.tag_configure("code", font=("Consolas", 10), background="#f0f0f0")
        self.preview.tag_configure("blockquote", lmargin1=20, lmargin2=20, foreground="#555")
        self.preview.tag_configure("list", lmargin1=15, lmargin2=30)
        self.preview.tag_configure("normal", font=("Segoe UI", 10))

    def _on_modified(self, _event=None):
        if self.editor.edit_modified():
            self.editor.edit_modified(False)
            self.dirty = True
            self.refresh_preview()
            self.app.update_tab_title(self)

    def set_content(self, text):
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", text)
        self.editor.edit_modified(False)
        self.dirty = False
        self.refresh_preview()
        self.app.update_tab_title(self)

    def get_content(self):
        return self.editor.get("1.0", "end-1c")

    def refresh_preview(self):
        md = self.get_content()
        self.preview.configure(state="normal")
        self.preview.delete("1.0", tk.END)

        for line in md.splitlines() or [""]:
            stripped = line.strip()
            if stripped.startswith("### "):
                self._insert_inline(stripped[4:], base_tag="h3")
                self.preview.insert(tk.END, "\n")
            elif stripped.startswith("## "):
                self._insert_inline(stripped[3:], base_tag="h2")
                self.preview.insert(tk.END, "\n")
            elif stripped.startswith("# "):
                self._insert_inline(stripped[2:], base_tag="h1")
                self.preview.insert(tk.END, "\n")
            elif stripped.startswith("> "):
                self._insert_inline(stripped[2:], base_tag="blockquote")
                self.preview.insert(tk.END, "\n")
            elif re.match(r"^[-*+]\s+", stripped):
                bullet_text = re.sub(r"^[-*+]\s+", "• ", stripped)
                self._insert_inline(bullet_text, base_tag="list")
                self.preview.insert(tk.END, "\n")
            elif re.match(r"^\d+\.\s+", stripped):
                self._insert_inline(stripped, base_tag="list")
                self.preview.insert(tk.END, "\n")
            else:
                self._insert_inline(line, base_tag="normal")
                self.preview.insert(tk.END, "\n")

        self.preview.configure(state="disabled")

    def _insert_inline(self, text, base_tag="normal"):
        pos = 0
        for m in re.finditer(r"(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)", text):
            if m.start() > pos:
                self.preview.insert(tk.END, text[pos:m.start()], base_tag)
            token = m.group(0)
            if token.startswith("`"):
                self.preview.insert(tk.END, token[1:-1], (base_tag, "code"))
            elif token.startswith("**"):
                self.preview.insert(tk.END, token[2:-2], (base_tag, "bold"))
            else:
                self.preview.insert(tk.END, token[1:-1], (base_tag, "italic"))
            pos = m.end()

        if pos < len(text):
            self.preview.insert(tk.END, text[pos:], base_tag)


class MarkdownReaderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Portable Markdown Reader / Editor")
        self.geometry("1200x750")
        self.minsize(800, 500)

        self.recent_files = []
        self.tab_map = {}

        self._build_ui()
        self.new_tab()

    def _build_ui(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        self._build_menu()

    def _build_menu(self):
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New Tab", command=self.new_tab, accelerator="Ctrl+N")
        file_menu.add_command(label="Open...", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Save", command=self.save_current, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As...", command=self.save_current_as, accelerator="Ctrl+Shift+S")

        self.recent_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Recent Files", menu=self.recent_menu)
        self._refresh_recent_menu()

        file_menu.add_separator()
        file_menu.add_command(label="Close Tab", command=self.close_current_tab, accelerator="Ctrl+W")
        file_menu.add_command(label="Exit", command=self.quit)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Cut", command=lambda: self._editor_event("<<Cut>>"), accelerator="Ctrl+X")
        edit_menu.add_command(label="Copy", command=lambda: self._editor_event("<<Copy>>"), accelerator="Ctrl+C")
        edit_menu.add_command(label="Paste", command=lambda: self._editor_event("<<Paste>>"), accelerator="Ctrl+V")
        edit_menu.add_separator()
        edit_menu.add_command(label="Undo", command=lambda: self._editor_event("<<Undo>>"), accelerator="Ctrl+Z")
        edit_menu.add_command(label="Redo", command=lambda: self._editor_event("<<Redo>>"), accelerator="Ctrl+Y")

        menubar.add_cascade(label="File", menu=file_menu)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        self.config(menu=menubar)

        self.bind_all("<Control-n>", lambda _e: self.new_tab())
        self.bind_all("<Control-o>", lambda _e: self.open_file())
        self.bind_all("<Control-s>", lambda _e: self.save_current())
        self.bind_all("<Control-Shift-S>", lambda _e: self.save_current_as())
        self.bind_all("<Control-w>", lambda _e: self.close_current_tab())

    def _editor_event(self, event):
        tab = self.current_tab()
        if tab:
            tab.editor.event_generate(event)

    def current_tab(self):
        current = self.notebook.select()
        return self.tab_map.get(current)

    def new_tab(self, content="", file_path=None):
        tab = DocumentTab(self)
        tab.set_content(content)
        tab.file_path = file_path
        self.tab_map[str(tab.frame)] = tab
        self.update_tab_title(tab)

    def update_tab_title(self, tab):
        name = Path(tab.file_path).name if tab.file_path else "Untitled"
        if tab.dirty:
            name += " *"
        self.notebook.tab(tab.frame, text=name)

    def open_file(self, file_path=None):
        if file_path is None:
            file_path = filedialog.askopenfilename(filetypes=[("Markdown", "*.md *.markdown *.txt"), ("All files", "*.*")])
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.new_tab(content=content, file_path=file_path)
            self._push_recent(file_path)
        except Exception as e:
            messagebox.showerror("Open failed", str(e))

    def save_current(self):
        tab = self.current_tab()
        if not tab:
            return
        if not tab.file_path:
            return self.save_current_as()
        self._save_to_path(tab, tab.file_path)

    def save_current_as(self):
        tab = self.current_tab()
        if not tab:
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("Text", "*.txt"), ("All files", "*.*")],
        )
        if not file_path:
            return
        self._save_to_path(tab, file_path)

    def _save_to_path(self, tab, file_path):
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(tab.get_content())
            tab.file_path = file_path
            tab.dirty = False
            self.update_tab_title(tab)
            self._push_recent(file_path)
        except Exception as e:
            messagebox.showerror("Save failed", str(e))

    def close_current_tab(self):
        tab = self.current_tab()
        if not tab:
            return
        if tab.dirty:
            if not messagebox.askyesno("Unsaved", "This tab has unsaved changes. Close anyway?"):
                return
        key = self.notebook.select()
        self.notebook.forget(key)
        self.tab_map.pop(key, None)
        if not self.tab_map:
            self.new_tab()

    def _push_recent(self, file_path):
        file_path = os.path.abspath(file_path)
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        self.recent_files.insert(0, file_path)
        self.recent_files = self.recent_files[:MAX_RECENT_FILES]
        self._refresh_recent_menu()

    def _refresh_recent_menu(self):
        self.recent_menu.delete(0, tk.END)
        if not self.recent_files:
            self.recent_menu.add_command(label="(No recent files)", state="disabled")
            return
        for p in self.recent_files:
            self.recent_menu.add_command(label=p, command=lambda path=p: self.open_file(path))


if __name__ == "__main__":
    app = MarkdownReaderApp()
    app.mainloop()
