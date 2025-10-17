# Teams Icon Maker (Microsoft Teams 400×400 PNG)

A small Windows GUI tool to generate **400×400 PNG** icons for Microsoft Teams.

- **White background**, **5 px black border**, **5 px inner margin**
- **1–4 lines**, max **8 chars/line**, **UPPERCASE enforced**, **accents removed** (ASCII only)
- **One color per line** (palette + color picker)
- **Adaptive per-line font size** (**no overlap**), **precise H/V centering**
- Single-file Python app: `teams_icon_app.py` (Tkinter + Pillow)

---

## 🔎 Story Behind the Project

**The Problem**  
We needed a quick way to produce consistent Microsoft Teams icons with strict layout rules:
- 400×400 PNG
- Black border (5 px), text at least 5 px away from the inner edge
- 1–4 lines, max 8 characters each, uppercase, no accents/emojis
- One color per line
- Text perfectly centered horizontally and vertically, no overlap

**Challenges**  
- Default text rendering in Pillow made centering look off.
- Border drawn with `outline` wasn’t precise.
- Multi-line layout required adaptive font sizing and spacing.
- Early attempts failed due to copy/paste corruption (HTML entities like `-&gt;`) and OneDrive sync issues.

**The Solution**  
- Exact border: draw a full black rectangle, then an inner white rectangle → guaranteed 5 px border.
- True centering: measure text with `textbbox`, compute per-line vertical centers, render with `anchor="mm"`.
- Adaptive sizing: fit each line to width, then scale down uniformly if total height exceeds available space.
- Sanitization: remove diacritics, enforce uppercase, clamp to 8 chars.
- Single-file app for simplicity, packaged as EXE with PyInstaller.

---

## ✅ Features

- GUI with live preview (Tkinter)
- Up to 4 lines, max 8 chars each
- Automatic uppercase, accents removed
- Color picker per line + preset palette
- Export as PNG (400×400, strict margins)
- Build as standalone EXE for Windows

---

## ▶️ Run (Development)

```bash
py -3 -m pip install Pillow
py -3 teams_icon_app.py
