#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
teams_icon_app.py — Single-file GUI + core for Teams icon generation.

Specs:
- Output: 400x400 PNG, white background, 5 px black border, 5 px inner margin
- Text: 1..4 lines, max 8 chars per line, UPPERCASE enforced, accents removed (ASCII only), no emojis
- Per-line color (palette + color picker)
- Centered horizontally and vertically (no overlap), adaptive per-line font size (Mode B)
- GUI: Tkinter (English), live preview, Export PNG to current folder

Requirements:
- Python 3.x (Windows recommended)
- Pillow (pip install Pillow)
"""

import os
import re
import sys
import time
import unicodedata
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
from dataclasses import dataclass
from typing import List, Tuple

# ---- Pillow imports with graceful error message ----
try:
    from PIL import Image, ImageDraw, ImageFont, ImageTk
except Exception:
    # Show a friendly dialog if Pillow is missing
    try:
        tk.Tk().withdraw()
    except Exception:
        pass
    messagebox.showerror(
        "Missing dependency",
        "Pillow is required.\nInstall it with:\n\npy -3 -m pip install Pillow"
    )
    sys.exit(1)

# ---------------- Core (rendering) ---------------- #

IMG_SIZE = 400
BORDER_PX = 5
INNER_MARGIN_PX = 5
BACKGROUND_COLOR = "#FFFFFF"
BORDER_COLOR = "#000000"

# Inner content square (strictly inside border + margin)
CONTENT_LEFT = BORDER_PX + INNER_MARGIN_PX
CONTENT_TOP = BORDER_PX + INNER_MARGIN_PX
CONTENT_SIZE = IMG_SIZE - 2 * (BORDER_PX + INNER_MARGIN_PX)  # 380 px
CONTENT_CENTER_X = CONTENT_LEFT + CONTENT_SIZE // 2

MAX_LINES = 4
MAX_CHARS = 8
MIN_FONT = 8
MAX_FONT = 400

# Color presets (Microsoft-like)
COLOR_PRESETS: List[Tuple[str, str]] = [
    ("MS Blue", "#0078D4"),
    ("Black", "#000000"),
    ("Green", "#107C10"),
    ("Purple", "#5C2D91"),
    ("Red", "#E81123"),
    ("Orange", "#D83B01"),
    ("Yellow", "#FFB900"),
    ("Magenta", "#B4009E"),
    ("Cyan", "#0099BC"),
    ("Gray", "#605E5C"),
]

# Candidate bold fonts to try on Windows, then optional local fonts
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\segoeuib.ttf",  # Segoe UI Bold
    r"C:\Windows\Fonts\arialbd.ttf",   # Arial Bold
    r"C:\Windows\Fonts\calibrib.ttf",  # Calibri Bold
    "fonts/DejaVuSans-Bold.ttf",
    "fonts/Arial-Bold.ttf",
]


@dataclass
class LineSpec:
    text: str       # sanitized (≤8 chars, uppercase, ASCII)
    color_hex: str  # "#RRGGBB"


_HEX_RE = re.compile(r"^#([0-9A-Fa-f]{6})$")


def is_valid_hex_color(value: str) -> bool:
    return bool(_HEX_RE.match(value or ""))


def strip_accents_upper_ascii(text: str) -> str:
    """
    Remove diacritics, drop non-ASCII (incl. emojis), keep printable ASCII (space..~), uppercase.
    """
    if not text:
        return ""
    norm = unicodedata.normalize("NFKD", text)
    no_marks = "".join(ch for ch in norm if not unicodedata.combining(ch))
    ascii_only = no_marks.encode("ascii", "ignore").decode("ascii")
    ascii_printable = "".join(ch for ch in ascii_only if 32 <= ord(ch) <= 126)
    return ascii_printable.upper()


def sanitize_line(text: str) -> str:
    """
    Enforce UPPERCASE, remove accents/emojis, ASCII only, and clamp to MAX_CHARS.
    """
    return strip_accents_upper_ascii(text)[:MAX_CHARS].strip()


def try_load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """
    Try to load a bold TrueType font by priority; fallback to PIL default if none found.
    """
    for path in FONT_CANDIDATES:
        try:
            fpath = path if os.path.isabs(path) else os.path.join(os.path.abspath("."), path)
            if os.path.exists(fpath):
                return ImageFont.truetype(fpath, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def _text_bbox(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> Tuple[int, int]:
    """
    Return (width, height) for given text and font using textbbox (accurate).
    """
    if not text:
        return 0, 0
    l, t, r, b = draw.textbbox((0, 0), text, font=font)
    return (r - l), (b - t)


def _compute_adaptive_layout(lines: List[LineSpec]) -> Tuple[List[int], int, List[float]]:
    """
    Compute per-line font sizes (adaptive Mode B), interline gap, and vertical centers for each line.
    Returns:
        sizes: [int] font size per line
        line_gap: int, interline spacing in px
        centers_y: [float] vertical center (absolute Y) for each line
    """
    n = len(lines)
    if n == 0:
        return [], 0, []

    tmp_img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(tmp_img)

    # 1) Fit each line to content width independently
    REF = 100
    ref_widths: List[int] = []
    for ln in lines:
        f = try_load_font(REF)
        w, _ = _text_bbox(draw, ln.text, f)
        ref_widths.append(max(w, 1))

    sizes: List[int] = []
    for w_ref in ref_widths:
        s = int((CONTENT_SIZE / w_ref) * REF)
        s = max(min(s, MAX_FONT), MIN_FONT)
        sizes.append(s)

    # 2) Measure heights at those sizes
    heights: List[int] = []
    for i, s in enumerate(sizes):
        f = try_load_font(s)
        _, h = _text_bbox(draw, lines[i].text, f)
        heights.append(h)

    # 3) Interline gap ≈ 18% of median height (works well for bold caps)
    median_h = sorted(heights)[len(heights) // 2]
    line_gap = 0 if n == 1 else max(int(0.18 * median_h), 1)
    total_h = sum(heights) + (n - 1) * line_gap

    # 4) If total height overflows, scale down sizes (and gap) uniformly
    if total_h > CONTENT_SIZE:
        ratio = CONTENT_SIZE / total_h
        sizes = [max(int(s * ratio), MIN_FONT) for s in sizes]
        heights = []
        for i, s in enumerate(sizes):
            f = try_load_font(s)
            _, h = _text_bbox(draw, lines[i].text, f)
            heights.append(h)
        line_gap = 0 if n == 1 else max(int(line_gap * ratio), 1)
        total_h = sum(heights) + (n - 1) * line_gap

    # 5) Compute vertical centers for each line (for anchor="mm")
    block_top = CONTENT_TOP + (CONTENT_SIZE - total_h) // 2
    centers_y: List[float] = []
    y = block_top
    for i in range(n):
        h = heights[i]
        centers_y.append(y + h / 2.0)
        y += h + (line_gap if i < n - 1 else 0)

    return sizes, line_gap, centers_y


def render_icon(line_specs: List[LineSpec]) -> Image.Image:
    """
    Render the icon and return a PIL Image (400x400).
    """
    # Sanitize and filter lines
    sanitized: List[LineSpec] = []
    for spec in line_specs[:MAX_LINES]:
        txt = sanitize_line(spec.text)
        if txt == "":
            continue
        col = spec.color_hex.strip().upper()
        if not is_valid_hex_color(col):
            col = "#000000"
        sanitized.append(LineSpec(text=txt, color_hex=col))

    # Base image
    img = Image.new("RGB", (IMG_SIZE, IMG_SIZE), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(img)

    # Draw exact 5 px border: fill black frame then inner white rect
    draw.rectangle([0, 0, IMG_SIZE - 1, IMG_SIZE - 1], fill=BORDER_COLOR)
    inner = BORDER_PX
    draw.rectangle([inner, inner, IMG_SIZE - 1 - inner, IMG_SIZE - 1 - inner], fill=BACKGROUND_COLOR)

    if not sanitized:
        return img

    sizes, _gap, centers_y = _compute_adaptive_layout(sanitized)

    # Draw each line centered with anchor="mm"
    for i, spec in enumerate(sanitized):
        font = try_load_font(sizes[i])
        draw.text((CONTENT_CENTER_X, centers_y[i]), spec.text, font=font, fill=spec.color_hex, anchor="mm")

    return img


# ---------------- GUI (Tkinter) ---------------- #

class TeamsIconMakerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Teams Icon Maker")
        self.resizable(False, False)

        # State
        self.line_vars: List[tk.StringVar] = [tk.StringVar(value="") for _ in range(MAX_LINES)]
        default_hex = [COLOR_PRESETS[i % len(COLOR_PRESETS)][1] for i in range(MAX_LINES)]
        self.color_vars: List[tk.StringVar] = [tk.StringVar(value=default_hex[i]) for i in range(MAX_LINES)]
        self.combos: List[ttk.Combobox] = []

        self._build_ui()
        self._bind_events()
        self._update_preview()

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=10)
        root.grid(row=0, column=0)

        info = ttk.Label(
            root,
            text=(
                "Up to 4 lines • max 8 chars per line • UPPERCASE enforced • accents removed • "
                "one color per line • white background • 5 px black border • 5 px inner margin"
            ),
            justify="left",
            wraplength=420,
        )
        info.grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))

        preset_values = [f"{name} ({hexv})" for name, hexv in COLOR_PRESETS]

        for i in range(MAX_LINES):
            row_i = 1 + i

            lbl = ttk.Label(root, text=f"Line {i+1}:")
            lbl.grid(row=row_i, column=0, sticky="e", padx=(0, 6))

            entry = ttk.Entry(root, textvariable=self.line_vars[i], width=14)
            entry.grid(row=row_i, column=1, sticky="w")
            entry.configure(validate="key", validatecommand=(self.register(self._validate_len), "%P"))

            combo = ttk.Combobox(root, values=preset_values, state="readonly", width=24)
            combo.grid(row=row_i, column=2, padx=(6, 0))
            combo.set(self._display_from_hex(self.color_vars[i].get()))
            self.combos.append(combo)

            btn = ttk.Button(root, text="Pick…", width=6, command=lambda idx=i: self._pick_color(idx))
            btn.grid(row=row_i, column=3, padx=(6, 0))

        # Buttons
        btns = ttk.Frame(root)
        btns.grid(row=1 + MAX_LINES, column=0, columnspan=4, pady=(10, 8), sticky="w")

        self.export_btn = ttk.Button(btns, text="Export PNG", command=self._export_png)
        self.export_btn.grid(row=0, column=0, padx=(0, 8))

        clear_btn = ttk.Button(btns, text="Clear", command=self._clear)
        clear_btn.grid(row=0, column=1, padx=(0, 8))

        quit_btn = ttk.Button(btns, text="Quit", command=self.destroy)
        quit_btn.grid(row=0, column=2)

        # Preview
        ttk.Label(root, text="Preview").grid(row=2 + MAX_LINES, column=0, columnspan=4, sticky="w")
        self.canvas = tk.Canvas(root, width=IMG_SIZE, height=IMG_SIZE, bg="#DDDDDD", highlightthickness=0)
        self.canvas.grid(row=3 + MAX_LINES, column=0, columnspan=4, pady=(4, 0))

    def _bind_events(self) -> None:
        for i in range(MAX_LINES):
            # Sanitize on any text change + refresh preview
            self.line_vars[i].trace_add("write", lambda *_: self._on_text_changed())
            # Update color on selection + refresh preview
            self.combos[i].bind("<<ComboboxSelected>>", lambda _e, idx=i: self._on_combo(idx))

    # ---------- Helpers & Events ---------- #

    def _validate_len(self, proposed: str) -> bool:
        return len(proposed) <= MAX_CHARS

    def _display_from_hex(self, hexv: str) -> str:
        for name, hx in COLOR_PRESETS:
            if hx.lower() == hexv.lower():
                return f"{name} ({hx})"
        return hexv.upper()

    def _hex_from_display(self, display: str) -> str:
        if "(" in display and ")" in display:
            return display[display.find("(") + 1:display.find(")")]
        return display.strip()

    def _pick_color(self, idx: int) -> None:
        initial = self.color_vars[idx].get()
        rgb, hexv = colorchooser.askcolor(color=initial, title=f"Pick color for line {idx+1}")
        if hexv and is_valid_hex_color(hexv):
            self.color_vars[idx].set(hexv.upper())
            self.combos[idx].set(hexv.upper())
            self._update_preview()

    def _on_combo(self, idx: int) -> None:
        hexv = self._hex_from_display(self.combos[idx].get())
        if is_valid_hex_color(hexv):
            self.color_vars[idx].set(hexv.upper())
        else:
            messagebox.showwarning("Invalid color", f"Not a valid hex color: {self.combos[idx].get()}")
        self._update_preview()

    def _on_text_changed(self) -> None:
        # Sanitize all entries (uppercase, accents removed, truncate)
        changed = False
        for i in range(MAX_LINES):
            val = self.line_vars[i].get()
            sanitized = sanitize_line(val)
            if sanitized != val:
                self.line_vars[i].set(sanitized)
                changed = True
        if not changed:
            self._update_preview()

    def _collect_lines(self) -> List[LineSpec]:
        specs: List[LineSpec] = []
        for i in range(MAX_LINES):
            txt = sanitize_line(self.line_vars[i].get())
            if txt == "":
                continue
            color = self.color_vars[i].get().strip().upper()
            if not is_valid_hex_color(color):
                color = "#000000"
            specs.append(LineSpec(text=txt, color_hex=color))
        return specs

    def _update_preview(self) -> None:
        lines = self._collect_lines()
        self.export_btn.configure(state=(tk.NORMAL if lines else tk.DISABLED))
        try:
            img = render_icon(lines)
            self._tk_img = ImageTk.PhotoImage(img)  # keep reference to avoid GC
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor="nw", image=self._tk_img)
        except Exception as e:
            self.canvas.delete("all")
            self.canvas.create_rectangle(0, 0, IMG_SIZE, IMG_SIZE, fill="#FFEEEE", outline="")
            self.canvas.create_text(IMG_SIZE // 2, IMG_SIZE // 2, text=f"Preview error:\n{e}", fill="#AA0000")

    def _export_png(self) -> None:
        lines = self._collect_lines()
        if not lines:
            messagebox.showinfo("Nothing to export", "Please enter at least one line.")
            return
        try:
            img = render_icon(lines)
            filename = f"teams_icon_{time.strftime('%Y%m%d-%H%M%S')}.png"
            out_path = os.path.join(os.getcwd(), filename)
            img.save(out_path, "PNG", optimize=True)
            messagebox.showinfo("Exported", f"Icon saved:\n{out_path}")
        except PermissionError:
            messagebox.showerror("Permission error", "Cannot write the file. Check folder permissions.")
        except Exception as e:
            messagebox.showerror("Export error", str(e))

    def _clear(self) -> None:
        """Clear all input lines and refresh preview."""
        for v in self.line_vars:
            v.set("")
        self._update_preview()


def main() -> None:
    app = TeamsIconMakerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
