"""Generate the animated "Software Interests" typing GIFs (dark + light).

Styled to match GitHub's inline `code` rendering:
  font-size 85% of 16px, padding .2em .4em, border-radius 6px,
  background var(--bgColor-neutral-muted), color var(--fgColor-default).

Usage: python scripts/interests_gif.py   (requires Pillow, macOS SF Mono)
       gifsicle -O3 --batch media/interests-*.gif   (optional, shrinks output)
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

SCALE = 2  # render at 2x for crisp retina display
FONT_PX = 16 * 0.85  # GitHub: code { font-size: 85% }
PAD_X_EM, PAD_Y_EM = 0.4, 0.2  # GitHub: code { padding: .2em .4em }
RADIUS_PX = 6  # GitHub: code { border-radius: 6px }
CARET_W = 3  # device px at 2x (= 1.5 CSS px)
FONT_PATH = "/System/Library/Fonts/SFNSMono.ttf"  # GitHub's ui-monospace on macOS

# GitHub Primer colors. `code` = bgColor-neutral-muted (translucent) over page bg.
THEMES = {
    "dark": {"page": "#0d1117", "code": ((101, 108, 118), 0.20), "fg": "#f0f6fc"},
    "light": {"page": "#ffffff", "code": ((129, 139, 152), 0.12), "fg": "#1f2328"},
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


def mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def build_palette(page, code, fg):
    colors = [page]  # index 0 -> transparent
    colors += [mix(page, code, i / 16) for i in range(1, 17)]  # rounded-corner AA
    colors += [mix(code, fg, i / 48) for i in range(1, 49)]  # text AA
    flat = [v for c in colors for v in c] + [0] * (768 - 3 * len(colors))
    pal = Image.new("P", (1, 1))
    pal.putpalette(flat)
    return pal


def timeline():
    """Yield (text, caret_visible, duration_ms) states."""
    rng = random.Random(7)
    for item in ITEMS:
        for i in range(1, len(item) + 1):
            yield item[:i], True, rng.randint(*TYPE_MS)
        for k in range(HOLD_MS // BLINK_MS):
            yield item, k % 2 == 1, BLINK_MS
        for i in range(len(item) - 1, -1, -1):
            yield item[:i], True, DELETE_MS
        for k in range(EMPTY_MS // 200):
            yield "", k % 2 == 1, 200


def pill_mask(w, h, canvas_w, r):
    """Anti-aliased rounded-rect mask via 4x supersampling."""
    ss = 4
    m = Image.new("L", (canvas_w * ss, h * ss), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w * ss - 1, h * ss - 1], radius=r * ss, fill=255)
    return m.resize((canvas_w, h), Image.Resampling.BOX)


def render(theme_name):
    theme = THEMES[theme_name]
    page, fg = hex_rgb(theme["page"]), hex_rgb(theme["fg"])
    code = mix(page, *theme["code"])

    size = FONT_PX * SCALE
    font = ImageFont.truetype(FONT_PATH, round(size))
    font.set_variation_by_name("Regular")
    char_w = font.getlength("M")
    ascent, descent = font.getmetrics()
    pad_x, pad_y = PAD_X_EM * size, PAD_Y_EM * size
    radius = RADIUS_PX * SCALE

    def pill_w(n):
        return round(2 * pad_x + char_w * n)

    width = pill_w(max(len(s) for s in ITEMS))
    height = round(ascent + descent + 2 * pad_y)
    palette = build_palette(page, code, fg)
    masks = {}

    frames, durations, prev = [], [], None
    for text, caret, ms in timeline():
        if (text, caret) == prev:  # merge identical consecutive frames
            durations[-1] += ms
            continue
        prev = (text, caret)

        w = pill_w(len(text))
        if w not in masks:
            masks[w] = pill_mask(w, height, width, radius)
        img = Image.composite(Image.new("RGB", (width, height), code),
                              Image.new("RGB", (width, height), page), masks[w])
        d = ImageDraw.Draw(img)
        d.text((pad_x, pad_y), text, font=font, fill=fg)
        if caret:
            cx = round(pad_x + char_w * len(text))
            d.rectangle([cx, round(pad_y), cx + CARET_W - 1, round(pad_y + ascent + descent) - 1], fill=fg)
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
    print(f"wrote {out} ({width}x{height} -> display width {width / SCALE:g}px, "
          f"{len(frames)} frames, {out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    for name in THEMES:
        render(name)
