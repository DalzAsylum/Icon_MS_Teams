# Teams Icon Maker (Microsoft Teams 400×400 PNG)

A small Windows GUI tool to generate **400×400 PNG** icons for Microsoft Teams.

- **White background**, **5 px black border**, **5 px inner margin**
- **1–4 lines**, max **8 chars/line**, **UPPERCASE enforced**, **accents removed** (ASCII only)
- **One color per line** (palette + color picker)
- **Adaptive per-line font size** (**no overlap**), **precise H/V centering**
- Single-file Python app: `teams_icon_app.py` (Tkinter + Pillow)

---

## 🔎 Problem & Solution

**Problem.** We needed a quick way to produce consistent Teams icons (400×400), 
with strict border/margin rules and centered multi-line labels.

**Solution.**
- Exact border: draw a black frame, then an inner white rectangle → **true 5 px** border.
- True centering: measure text with `textbbox`, compute per-line **vertical centers**,
  render with `anchor="mm"` at the content center X → **precise horizontal & vertical centering**.
- Adaptive sizing (Mode B): each line fits width; if the stack exceeds height,
  apply a **uniform scale-down** (sizes + gap ≈ 18% of median line height).
- Sanitization: diacritics/emojis removed, **UPPERCASE**, **≤ 8 chars** per line.
- Packaging: **PyInstaller** `--onefile --windowed` → `TeamsIconMaker.exe`.

---

## ▶️ Run (dev)

```bash
py -3 -m pip install Pillow
py -3 teams_icon_app.py
