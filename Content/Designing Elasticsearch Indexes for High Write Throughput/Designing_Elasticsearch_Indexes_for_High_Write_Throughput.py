"""
Index Design Animation (PIL + imageio) — based on your sample style

Scenes:
1) Setup: App → Kafka → Consumer → Elasticsearch → Dashboards (green, smooth, "confidence high")
2) Traffic growth: thicker arrows, red pulse, heap pressure meter rises, "Write Rejections" popups
3) Misconception: thought bubble “We need bigger machines!” crossed out → reveal “Index design is the real culprit.”
4) 4 factors: Shards, Refresh Interval, Replicas, ILM (animated icons + short callouts)
5) Optimized architecture: fewer shards, refresh 30–60s, replicas=0 during ingestion, ILM Hot→Warm→Cold

Run:
  pip install pillow numpy imageio imageio-ffmpeg
  python index_design_animation.py

Output:
  index-design-animation.mp4  (falls back to GIF if mp4 fails)
"""

from PIL import Image, ImageDraw, ImageFont
import numpy as np
import imageio
import math
from pathlib import Path

# ----------------------------
# Canvas / timing
# ----------------------------
W, H = 1280, 720
FPS = 30

SCENES = [
    ("scene1", 4.0),
    ("scene2", 5.0),
    ("scene3", 4.0),
    ("scene4", 10.0),
    ("scene5", 5.0),
]
SCENE_START = {}
_acc = 0.0
for name, dur in SCENES:
    SCENE_START[name] = _acc
    _acc += dur
TOTAL_DUR = _acc
TOTAL_FRAMES = int(TOTAL_DUR * FPS)

# ----------------------------
# Colors
# ----------------------------
BG_TOP = (255, 255, 255)
BG_BOTTOM = (255, 255, 255)

PANEL = (245, 245, 245)
PANEL_2 = (235, 235, 235)
OUTLINE = (180, 180, 180)

TEXT = (12, 12, 12)
MUTED = (80, 80, 80)

GREEN = (0, 207, 173)
RED = (255, 88, 102)
AMBER = (255, 187, 72)
BLUE = (120, 180, 255)

# ----------------------------
# Fonts (auto-detect)
# ----------------------------
def load_font(size, bold=False):
    # Prefer common fonts; fall back to PIL default.
    candidates = []
    if bold:
        candidates += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
        ]
    candidates += [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()

# Larger fonts as requested
FONT_TITLE = load_font(44, bold=True)
FONT_H2 = load_font(32, bold=True)
FONT_BODY = load_font(24, bold=False)
FONT_SMALL = load_font(20, bold=False)
FONT_TINY = load_font(18, bold=False)
FONT_BADGE = load_font(22, bold=True)

# ----------------------------
# Helpers
# ----------------------------
def lerp(a, b, t):
    return a + (b - a) * t

def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))

def ease_in_out(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)

def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) * (1 - t)

def ease_in(t):
    t = clamp(t)
    return t * t

def gradient_bg():
    img = Image.new("RGB", (W, H), BG_TOP)
    px = img.load()
    for y in range(H):
        t = y / (H - 1)
        r = int(lerp(BG_TOP[0], BG_BOTTOM[0], t))
        g = int(lerp(BG_TOP[1], BG_BOTTOM[1], t))
        b = int(lerp(BG_TOP[2], BG_BOTTOM[2], t))
        for x in range(W):
            px[x, y] = (r, g, b)
    return img

def rounded(draw, box, radius=18, fill=None, outline=None, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)

def measure_text(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return (bbox[2] - bbox[0], bbox[3] - bbox[1])

def wrap_text(draw, text, font, max_w):
    words = text.split()
    if not words:
        return [""]
    lines, cur = [], words[0]
    for w in words[1:]:
        trial = cur + " " + w
        if measure_text(draw, trial, font)[0] <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines

def draw_text_box(draw, box, title, body, accent=BLUE):
    x1, y1, x2, y2 = box
    rounded(draw, box, radius=18, fill=PANEL, outline=OUTLINE, width=2)
    # accent bar
    rounded(draw, (x1, y1, x1 + 10, y2), radius=18, fill=accent, outline=None, width=0)

    pad = 18
    cx1, cy1 = x1 + pad + 12, y1 + pad
    max_w = (x2 - x1) - (pad * 2) - 12

    draw.text((cx1, cy1), title, fill=TEXT, font=FONT_H2)
    title_h = measure_text(draw, title, FONT_H2)[1]
    cy = cy1 + title_h + 10

    lines = wrap_text(draw, body, FONT_BODY, max_w)
    for ln in lines:
        draw.text((cx1, cy), ln, fill=MUTED, font=FONT_BODY)
        cy += measure_text(draw, ln, FONT_BODY)[1] + 6

def center_text(draw, xy, text, font, fill):
    tw, th = measure_text(draw, text, font)
    draw.text((xy[0] - tw / 2, xy[1] - th / 2), text, font=font, fill=fill)

def draw_node(draw, cx, cy, w, h, label, color=GREEN, glow=0.0, pulse=0.0):
    # keep label safely inside
    x1, y1, x2, y2 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    # outer glow
    if glow > 0:
        gw = int(10 + 18 * glow)
        rounded(draw, (x1 - gw, y1 - gw, x2 + gw, y2 + gw), radius=28, fill=None, outline=(color[0], color[1], color[2]), width=2)
    # main
    rounded(draw, (x1, y1, x2, y2), radius=22, fill=PANEL_2, outline=color, width=3)
    # subtle pulse ring
    if pulse > 0:
        pw = int(2 + 8 * pulse)
        rounded(draw, (x1 - 6, y1 - 6, x2 + 6, y2 + 6), radius=24, fill=None, outline=color, width=pw)

    # text: keep normal weight, fall back to smaller fonts if needed
    font = FONT_BODY
    if measure_text(draw, label, font)[0] > (w - 24):
        font = FONT_SMALL
    center_text(draw, (cx, cy), label, font, TEXT)

def quad_curve_points(p0, p1, p2, steps=60):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
        pts.append((x, y))
    return pts

def draw_arrow(draw, p0, p2, color=GREEN, width=6, curve=0.0, arrow_size=16, alpha=1.0):
    # curve uses p1 shifted upward
    if curve != 0.0:
        mx, my = (p0[0] + p2[0]) / 2, (p0[1] + p2[1]) / 2
        p1 = (mx, my - 140 * curve)
        pts = quad_curve_points(p0, p1, p2, steps=70)
        for i in range(len(pts) - 1):
            draw.line([pts[i], pts[i + 1]], fill=color, width=width)
        x2, y2 = pts[-1]
        x1, y1 = pts[-2]
    else:
        draw.line([p0, p2], fill=color, width=width)
        x2, y2 = p2
        x1, y1 = p0

    ang = math.atan2(y2 - y1, x2 - x1)
    L = arrow_size
    pA = (x2, y2)
    pB = (x2 - L * math.cos(ang - 0.4), y2 - L * math.sin(ang - 0.4))
    pC = (x2 - L * math.cos(ang + 0.4), y2 - L * math.sin(ang + 0.4))
    draw.polygon([pA, pB, pC], fill=color)

def badge(draw, x, y, text, color=GREEN):
    pad_x, pad_y = 14, 8
    tw, th = measure_text(draw, text, FONT_BADGE)
    box = (x, y, x + tw + 2 * pad_x, y + th + 2 * pad_y)
    rounded(draw, box, radius=16, fill=(248, 248, 248), outline=color, width=2)
    draw.text((x + pad_x, y + pad_y), text, fill=TEXT, font=FONT_BADGE)

def meter(draw, x, y, w, h, label, value01, color=AMBER):
    rounded(draw, (x, y, x + w, y + h), radius=14, fill=(248, 248, 248), outline=OUTLINE, width=2)
    draw.text((x + 14, y + 10), label, fill=MUTED, font=FONT_SMALL)
    bar_y = y + 46
    bar_h = h - 62
    rounded(draw, (x + 14, bar_y, x + w - 14, bar_y + bar_h), radius=12, fill=(230, 230, 230), outline=OUTLINE, width=2)
    fill_w = int((w - 28) * clamp(value01))
    rounded(draw, (x + 14, bar_y, x + 14 + fill_w, bar_y + bar_h), radius=12, fill=color, outline=None, width=0)

def popup(draw, x, y, text, color=RED):
    tw, th = measure_text(draw, text, FONT_BODY)
    box = (x, y, x + tw + 28, y + th + 18)
    rounded(draw, box, radius=16, fill=(248, 248, 248), outline=color, width=2)
    draw.text((x + 14, y + 8), text, fill=TEXT, font=FONT_BODY)

def safe_clip(v, lo, hi):
    return max(lo, min(hi, v))

# ----------------------------
# Layout (no overlaps)
# ----------------------------
def layout_nodes():
    # top margin reserved for title; bottom reserved for captions
    y = 320
    return {
        "app":  (140, y),
        "kafka": (340, y),
        "consumer": (560, y),
        "es": (820, y),
        "dash": (1120, y),
    }

NODE_W, NODE_H = 160, 86

# ----------------------------
# Scene drawing
# ----------------------------
def draw_pipeline(draw, nodes, arrow_color=GREEN, arrow_w=6, line=0.0, pulse_map=None, glow_map=None):
    pulse_map = pulse_map or {}
    glow_map = glow_map or {}

    # arrows
    p = nodes
    draw_arrow(draw, (p["app"][0] + NODE_W/2, p["app"][1]), (p["kafka"][0] - NODE_W/2, p["kafka"][1]), color=arrow_color, width=arrow_w)
    draw_arrow(draw, (p["kafka"][0] + NODE_W/2, p["kafka"][1]), (p["consumer"][0] - NODE_W/2, p["consumer"][1]), color=arrow_color, width=arrow_w)
    draw_arrow(draw, (p["consumer"][0] + NODE_W/2, p["consumer"][1]), (p["es"][0] - NODE_W/2, p["es"][1]), color=arrow_color, width=arrow_w)
    # curved ES → Dashboards
    draw_arrow(
        draw,
        (p["es"][0] + NODE_W/2, p["es"][1]),
        (p["dash"][0] - NODE_W/2, p["dash"][1]),
        color=arrow_color,
        width=arrow_w,
        curve=line
    )

    # nodes
    draw_node(draw, *p["app"], NODE_W, NODE_H, "App", color=GREEN, glow=glow_map.get("app", 0), pulse=pulse_map.get("app", 0))
    draw_node(draw, *p["kafka"], NODE_W, NODE_H, "Kafka", color=GREEN, glow=glow_map.get("kafka", 0), pulse=pulse_map.get("kafka", 0))
    draw_node(draw, *p["consumer"], NODE_W, NODE_H, "Consumer", color=GREEN, glow=glow_map.get("consumer", 0), pulse=pulse_map.get("consumer", 0))
    draw_node(draw, *p["es"], NODE_W, NODE_H, "Elasticsearch", color=GREEN, glow=glow_map.get("es", 0), pulse=pulse_map.get("es", 0))
    draw_node(draw, *p["dash"], NODE_W, NODE_H, "Dashboards", color=GREEN, glow=glow_map.get("dash", 0), pulse=pulse_map.get("dash", 0))

def draw_scene1(draw, local_t):
    # Title
    center_text(draw, (W/2, 90), "Kafka Indexing: What Looks Fast… Until Production", FONT_TITLE, TEXT)
    center_text(draw, (W/2, 140), "App → Kafka → Consumer → Elasticsearch → Dashboards", FONT_BODY, MUTED)

    nodes = layout_nodes()
    # steady tiles without extra glow
    draw_pipeline(draw, nodes, arrow_color=GREEN, arrow_w=6, pulse_map={}, glow_map={})
    badge(draw, 70, 580, "confidence: high", color=GREEN)

def draw_scene2(draw, local_t):
    center_text(draw, (W/2, 90), "Traffic Grows. The Cluster Starts Screaming.", FONT_TITLE, TEXT)

    nodes = layout_nodes()
    # arrows thicken with traffic
    traffic = ease_in_out(local_t / 5.0)
    arrow_w = int(6 + 10 * traffic)
    # red pulse on ES and Kafka
    pulse = 0.5 + 0.5 * math.sin(local_t * 6.0)
    pulse_map = {}
    # shift arrow color toward amber/red as pressure rises
    arrow_color = (int(lerp(GREEN[0], AMBER[0], traffic)),
                   int(lerp(GREEN[1], AMBER[1], traffic)),
                   int(lerp(GREEN[2], AMBER[2], traffic)))
    draw_pipeline(draw, nodes, arrow_color=arrow_color, arrow_w=arrow_w, pulse_map=pulse_map)

    # Heap pressure meter rises
    heap = clamp(0.15 + 0.85 * traffic)
    meter(draw, 40, 420, 260, 170, "Heap pressure", heap, color=AMBER if heap < 0.8 else RED)

    # Write rejections popups appear later
    if local_t > 2.0:
        pop_alpha = ease_in_out((local_t - 2.0) / 3.0)
        # place popups near ES but ensure on-screen and non-overlapping
        popup(draw, 760, 520, "Write Rejections", color=RED)
        popup(draw, 760, 570, "Indexing Slowdown", color=RED)
        popup(draw, 760, 620, "Dashboards Lagging", color=AMBER)

def draw_scene3(draw, local_t):
    center_text(draw, (W/2, 90), "The Most Common (Wrong) Reaction", FONT_TITLE, TEXT)

    nodes = layout_nodes()
    # keep pipeline but muted
    draw_pipeline(draw, nodes, arrow_color=(90, 110, 150), arrow_w=6, pulse_map={})

    # Thought bubble
    bx, by, bw, bh = 260, 400, 760, 170
    rounded(draw, (bx, by, bx + bw, by + bh), radius=28, fill=PANEL, outline=OUTLINE, width=2)
    # little bubble tail
    draw.polygon([(bx + 120, by + bh), (bx + 160, by + bh), (bx + 145, by + bh + 28)], fill=PANEL, outline=OUTLINE)
    thought = "“We need bigger machines!”"
    center_text(draw, (bx + bw/2, by + 60), thought, FONT_H2, TEXT)

    # Cross-out animation then reveal
    t = local_t / 4.0
    if t < 0.55:
        k = ease_in(t / 0.55)
        tw, th = measure_text(draw, thought, FONT_H2)
        x1 = bx + (bw - tw) / 2
        y1 = by + 60
        x2 = x1 + tw * k
        y2 = y1 - 22 * k
        draw.line([(x1, y1), (x2, y2)], fill=RED, width=10)
    else:
        # show full cross-out
        tw, th = measure_text(draw, thought, FONT_H2)
        x1 = bx + (bw - tw) / 2
        y1 = by + 60
        x2 = x1 + tw
        y2 = y1 - 22
        draw.line([(x1, y1), (x2, y2)], fill=RED, width=10)

        # reveal correct message under it
        reveal = ease_out((t - 0.55) / 0.45)
        msg = "Index design is the real culprit."
        # Slide-in from below, no overlap with bubble border
        y = by + 118 + (1 - reveal) * 25
        center_text(draw, (bx + bw/2, y), msg, FONT_H2, GREEN)

    # Supporting caption (kept inside safe margins)
    center_text(draw, (W/2, 660), "Hardware helps sometimes — but bad index settings can bottleneck writes permanently.", FONT_BODY, MUTED)

def icon_shards(draw, x, y, t):
    # multiple shards splitting, memory bars rising
    base_w, base_h = 150, 90
    rounded(draw, (x, y, x + base_w, y + base_h), radius=16, fill=(10, 16, 32), outline=OUTLINE, width=2)
    # splitting blocks
    s = 1 + int(3 * ease_in_out(t))
    gap = 6
    sw = (base_w - (s + 1) * gap) / s
    for i in range(s):
        x1 = x + gap + i * (sw + gap)
        rounded(draw, (x1, y + 16, x1 + sw, y + 54), radius=10, fill=PANEL_2, outline=BLUE, width=2)
    # memory bars
    bar_x = x + 16
    bar_y = y + 66
    bar_w = base_w - 32
    rounded(draw, (bar_x, bar_y, bar_x + bar_w, bar_y + 14), radius=10, fill=(8, 14, 28), outline=(40, 54, 86), width=2)
    fill_w = int(bar_w * (0.15 + 0.8 * ease_in(t)))
    rounded(draw, (bar_x, bar_y, bar_x + fill_w, bar_y + 14), radius=10, fill=AMBER if t < 0.7 else RED, outline=None, width=0)

def icon_refresh(draw, x, y, t):
    # clock ticking fast -> indexing slows
    r = 42
    cx, cy = x + 75, y + 48
    rounded(draw, (x, y, x + 150, y + 90), radius=16, fill=(10, 16, 32), outline=OUTLINE, width=2)
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=BLUE, width=4)
    # hands speed up
    ang = -math.pi/2 + 6.0 * t * 2 * math.pi
    hx, hy = cx + 0.75 * r * math.cos(ang), cy + 0.75 * r * math.sin(ang)
    draw.line([(cx, cy), (hx, hy)], fill=TEXT, width=5)
    # small "slowdown" bar below
    bar = ease_in(t)
    rounded(draw, (x + 16, y + 72, x + 134, y + 84), radius=10, fill=(8, 14, 28), outline=(40, 54, 86), width=2)
    rounded(draw, (x + 16, y + 72, x + 16 + int(118 * (1 - 0.6 * bar)), y + 84), radius=10, fill=AMBER, outline=None, width=0)

def icon_replicas(draw, x, y, t):
    # duplicate arrows multiplying writes
    rounded(draw, (x, y, x + 150, y + 90), radius=16, fill=(10, 16, 32), outline=OUTLINE, width=2)
    count = 1 + int(2 * ease_in_out(t))
    for i in range(count):
        y0 = y + 25 + i * 18
        draw_arrow(draw, (x + 22, y0), (x + 128, y0), color=RED if i > 0 else GREEN, width=5, arrow_size=14)

def icon_ilm(draw, x, y, t):
    # old indices piling up -> metadata overload
    rounded(draw, (x, y, x + 150, y + 90), radius=16, fill=(10, 16, 32), outline=OUTLINE, width=2)
    stacks = 2 + int(4 * ease_in(t))
    for i in range(stacks):
        yy = y + 64 - i * 10
        rounded(draw, (x + 26, yy, x + 124, yy + 12), radius=8, fill=PANEL_2, outline=BLUE, width=2)
    # warning dot
    if t > 0.65:
        draw.ellipse((x + 118, y + 12, x + 138, y + 32), fill=RED)

def draw_scene4(draw, local_t):
    center_text(draw, (W/2, 90), "The 4 Index Settings That Usually Break Writes", FONT_TITLE, TEXT)

    # four factor cards, spaced to avoid overlaps
    cards = [
        ("Shards", "Too many shards → more overhead, more heap pressure.", icon_shards, BLUE),
        ("Refresh Interval", "Refreshing too often steals cycles from ingestion.", icon_refresh, AMBER),
        ("Replicas", "Replicas multiply write work during heavy ingestion.", icon_replicas, RED),
        ("ILM", "No lifecycle strategy → old indices pile up and metadata grows.", icon_ilm, BLUE),
    ]

    # animate one card at a time (2.5s each)
    per = 2.5
    idx = int(local_t // per)
    frac = (local_t - idx * per) / per
    idx = safe_clip(idx, 0, 3)

    # positions
    x0, y0 = 80, 160
    gap_x, gap_y = 30, 26
    cw, ch = 560, 130

    for i, (title, body, icon_fn, accent) in enumerate(cards):
        row = i // 2
        col = i % 2
        bx = x0 + col * (cw + gap_x)
        by = y0 + row * (ch + gap_y)

        # highlight active
        active = 1.0 if i == idx else 0.0
        glow = 0.12 + 0.25 * active * (0.5 + 0.5 * math.sin(local_t * 6.0))

        rounded(draw, (bx, by, bx + cw, by + ch), radius=22, fill=PANEL, outline=OUTLINE, width=2)
        # accent strip
        rounded(draw, (bx, by, bx + 10, by + ch), radius=22, fill=accent, outline=None, width=0)

        # icon
        ix, iy = bx + 20, by + 20
        tt = ease_in_out(frac) if i == idx else 0.0
        icon_fn(draw, ix, iy, tt)

        # text (wrapped, stays inside)
        tx = bx + 190
        ty = by + 22
        draw.text((tx, ty), title, fill=TEXT, font=FONT_H2)

        max_w = (bx + cw) - tx - 20
        lines = wrap_text(draw, body, FONT_BODY, max_w)
        yy = ty + measure_text(draw, title, FONT_H2)[1] + 8
        for ln in lines[:2]:
            draw.text((tx, yy), ln, fill=MUTED, font=FONT_BODY)
            yy += measure_text(draw, ln, FONT_BODY)[1] + 6

        # subtle active outline pulse
        if active:
            pw = int(2 + 6 * (0.5 + 0.5 * math.sin(local_t * 8.0)))
            rounded(draw, (bx - 2, by - 2, bx + cw + 2, by + ch + 2), radius=24, fill=None, outline=(accent[0], accent[1], accent[2]), width=pw)

    center_text(draw, (W/2, 660), "Fix these, and your write throughput usually jumps without any hardware changes.", FONT_BODY, MUTED)

def draw_scene5(draw, local_t):
    center_text(draw, (W/2, 90), "Optimized Setup (Write-Friendly)", FONT_TITLE, TEXT)
    nodes = layout_nodes()

    # cleaner green, steady arrows
    draw_pipeline(draw, nodes, arrow_color=GREEN, arrow_w=7, pulse_map={}, glow_map={})

    # right-side best-practices panel (no overlap with nodes)
    panel = (720, 430, 1240, 670)
    draw_text_box(
        draw,
        panel,
        "Ingestion Tuning",
        "• Fewer shards (right-sized)\n• Refresh interval: 30–60s\n• Replicas = 0 during ingestion\n• ILM: Hot → Warm → Cold",
        accent=GREEN
    )

    # ILM phase track (animated)
    tx1, ty1, tx2, ty2 = 80, 520, 640, 610
    rounded(draw, (tx1, ty1, tx2, ty2), radius=22, fill=PANEL, outline=OUTLINE, width=2)
    draw.text((tx1 + 18, ty1 + 16), "ILM Phases", fill=TEXT, font=FONT_H2)

    # phases as pills
    phases = [("Hot", RED), ("Warm", AMBER), ("Cold", BLUE)]
    px = tx1 + 18
    py = ty1 + 68
    prog = ease_in_out(local_t / 5.0)
    active_idx = min(2, int(prog * 3.0))
    for i, (nm, c) in enumerate(phases):
        pill_w = 150
        box = (px + i * (pill_w + 18), py, px + i * (pill_w + 18) + pill_w, py + 44)
        rounded(draw, box, radius=18, fill=(255, 255, 255), outline=c, width=3)
        center_text(draw, ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2), nm, FONT_BODY, TEXT)
        if i == active_idx:
            # moving dot indicating progression
            dotx = box[0] + 18 + (pill_w - 36) * (prog * 3.0 - i)
            dotx = safe_clip(dotx, box[0] + 18, box[2] - 18)
            draw.ellipse((dotx - 7, py + 20 - 7, dotx + 7, py + 20 + 7), fill=GREEN)

    badge(draw, 80, 170, "Outcome: stable writes, fresher dashboards", color=GREEN)

# ----------------------------
# Frame composer
# ----------------------------
def make_frame(t):
    img = gradient_bg()
    draw = ImageDraw.Draw(img)

    # Scene routing
    if SCENE_START["scene1"] <= t < SCENE_START["scene2"]:
        local = t - SCENE_START["scene1"]
        draw_scene1(draw, local)
    elif SCENE_START["scene2"] <= t < SCENE_START["scene3"]:
        local = t - SCENE_START["scene2"]
        draw_scene2(draw, local)
    elif SCENE_START["scene3"] <= t < SCENE_START["scene4"]:
        local = t - SCENE_START["scene3"]
        draw_scene3(draw, local)
    elif SCENE_START["scene4"] <= t < SCENE_START["scene5"]:
        local = t - SCENE_START["scene4"]
        draw_scene4(draw, local)
    else:
        local = t - SCENE_START["scene5"]
        draw_scene5(draw, local)

    # credits
    credits = "video credits: Chaitanya Pothuraju"
    tw, th = measure_text(draw, credits, FONT_BODY)
    draw.text((W - tw - 24, H - th - 18), credits, fill=MUTED, font=FONT_BODY)

    return np.array(img)

# ----------------------------
# Render
# ----------------------------
out_mp4 = "index-design-animation.mp4"
out_gif = "index-design-animation.gif"

mp4_written = False
try:
    writer = imageio.get_writer(out_mp4, fps=FPS, codec="libx264", quality=8)
    for i in range(TOTAL_FRAMES):
        tt = i / FPS
        writer.append_data(make_frame(tt))
    writer.close()
    mp4_written = True
except Exception as e:
    frames = [make_frame(i / FPS) for i in range(TOTAL_FRAMES)]
    imageio.mimsave(out_gif, frames, fps=12)

print("Created:", out_mp4 if mp4_written else out_gif)
