"""Generate the animated "Software Interests" typing GIFs (dark + light).

Usage: python scripts/interests_gif.py   (requires Pillow, macOS SF Mono)
"""

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ITEMS = [
    "Full stack web development",
    "Distributed systems",
    "DevOps",
    "Software quality",
    "Agentic workflows",
    "Developer tooling",
]

PROMPT = ""
SCALE = 2  # render at 2x for crisp retina display
FONT_SIZE = 16 * SCALE
FONT_PATH = "/System/Library/Fonts/SFNSMono.ttf"  # GitHub's ui-monospace on macOS

# GitHub Primer colors
THEMES = {
    "dark": {"bg": "#0d1117", "fg": "#f0f6fc", "prompt": "#3fb950"},
    "light": {"bg": "#ffffff", "fg": "#1f2328", "prompt": "#1a7f37"},
}

# Timing (ms) — GIF delays are in 10ms units
TYPE_MS = (50, 110)
DELETE_MS = 30
HOLD_MS = 2000
BLINK_MS = 500
EMPTY_MS = 400

OUT_DIR = Path(__file__).resolve().parent.parent / "media"


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def build_palette(theme, levels=32):
    bg = hex_rgb(theme["bg"])
    colors = [bg]
    for key in ("fg", "prompt"):
        c = hex_rgb(theme[key])
        for i in range(1, levels + 1):
            t = i / levels
            colors.append(tuple(round(bg[j] + (c[j] - bg[j]) * t) for j in range(3)))
    flat = [v for col in colors for v in col]
    flat += [0] * (768 - len(flat))
    pal = Image.new("P", (1, 1))
    pal.putpalette(flat)
    return pal


def timeline():
    """Yield (text, cursor_visible, duration_ms) states."""
    rng = random.Random(7)
    for item in ITEMS:
        for i in range(1, len(item) + 1):
            yield item[:i], True, rng.randint(*TYPE_MS)
        for k in range(HOLD_MS // BLINK_MS):
            yield item, k % 2 == 1, BLINK_MS
        for i in range(len(item) - 1, -1, -1):
            yield item[:i], True, DELETE_MS
        yield "", True, EMPTY_MS


def render(theme_name):
    theme = THEMES[theme_name]
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    font.set_variation_by_name("Regular")
    char_w = font.getlength("M")
    ascent, descent = font.getmetrics()
    line_h = ascent + descent

    longest = max(len(s) for s in ITEMS)
    pad_y = 6 * SCALE
    width = round(char_w * (len(PROMPT) + longest + 1)) + 2 * SCALE
    height = line_h + 2 * pad_y
    palette = build_palette(theme)

    frames, durations, prev = [], [], None
    for text, cursor, ms in timeline():
        key = (text, cursor)
        if key == prev:  # merge identical consecutive frames
            durations[-1] += ms
            continue
        prev = key

        img = Image.new("RGB", (width, height), theme["bg"])
        d = ImageDraw.Draw(img)
        d.text((0, pad_y), PROMPT, font=font, fill=theme["prompt"])
        x = char_w * len(PROMPT)
        d.text((x, pad_y), text, font=font, fill=theme["fg"])
        if cursor:
            cx = x + char_w * len(text)
            d.rectangle(
                [round(cx), pad_y + 2 * SCALE, round(cx + char_w) - 1, pad_y + line_h - 2 * SCALE],
                fill=theme["fg"],
            )
        frames.append(img.quantize(palette=palette, dither=Image.Dither.NONE))
        durations.append(ms)

    out = OUT_DIR / f"interests-{theme_name}.gif"
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=[round(ms / 10) * 10 for ms in durations],
        loop=0,
        transparency=0,
        disposal=2,
        optimize=False,
    )
    print(f"wrote {out} ({width}x{height}, {len(frames)} frames, {out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    for name in THEMES:
        render(name)
