# Portable Markdown Reader / Editor (Windows)

This is a simple **desktop Markdown reader/editor** written in Python + Tkinter.
It is designed to be usable in environments where software installation is restricted.

## Features

- Multi-tab document UI (Notepad++-style tabbed workflow)
- Open / Save / Save As
- Recent files menu
- Split editor + rich text preview
- Basic Markdown rendering (`#`, `##`, `###`, lists, blockquotes, bold/italic/inline code)
- Standard text editing actions (cut/copy/paste/undo/redo)
- Resizable window

## Run directly (if Python is available)

```bash
python markdown_reader_app.py
```

## Build a no-install portable EXE

On a machine where you are allowed to prepare binaries:

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```
2. Build a single executable:
   ```bash
   pyinstaller --noconfirm --onefile --windowed --name MKDReader markdown_reader_app.py
   ```
3. Copy `dist/MKDReader.exe` to your restricted Windows 11 machine and run it.

No installer is required for the EXE produced above.

## Notes

- This app stores Markdown source text and renders a live preview in the right panel.
- Rendering is intentionally lightweight and dependency-free.
