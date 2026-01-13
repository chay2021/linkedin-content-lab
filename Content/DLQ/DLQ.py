import os, random, shutil, subprocess
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
FPS = 15  # fast render

def load_font(size=28, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size=size)
    return ImageFont.load_default()

FONT_XL = load_font(52, bold=True)
FONT_L = load_font(30, bold=True)
FONT_M = load_font(22, bold=False)
FONT_M_B = load_font(22, bold=True)
FONT_S = load_font(18, bold=False)
FONT_MONO = load_font(20, bold=False)
BIG_92 = load_font(92, bold=True)
BIG_120 = load_font(120, bold=True)

def lerp(a, b, t): 
    return int(a + (b - a) * t)

def make_fast_gradient_bg():
    # Build a small gradient and upscale (much faster than per-pixel full res)
    w0, h0 = 320, 180
    base = Image.new("RGB", (w0, h0), (15, 23, 42))
    px = base.load()
    c1, c2, c3 = (15, 23, 42), (60, 20, 90), (15, 23, 42)
    for y in range(h0):
        for x in range(w0):
            t = (x + y) / (w0 + h0)
            if t < 0.5:
                u = t / 0.5
                r, g, b = lerp(c1[0], c2[0], u), lerp(c1[1], c2[1], u), lerp(c1[2], c2[2], u)
            else:
                u = (t - 0.5) / 0.5
                r, g, b = lerp(c2[0], c3[0], u), lerp(c2[1], c3[1], u), lerp(c2[2], c3[2], u)
            px[x, y] = (r, g, b)
    return base.resize((W, H), resample=Image.BILINEAR)

BG = make_fast_gradient_bg().convert("RGBA")

def alpha_color(rgb, a): 
    return (rgb[0], rgb[1], rgb[2], a)

def round_rect(draw, xy, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(list(xy), radius=radius, fill=fill, outline=outline, width=width)

def draw_centered(draw, text, y, font, fill):
    bb = draw.textbbox((0, 0), text, font=font)
    w = bb[2] - bb[0]
    draw.text(((W - w) // 2, y), text, font=font, fill=fill)

def make_card(draw, x, y, w, h, title, border, fill, title_fill=(255, 255, 255), radius=16):
    round_rect(draw, (x, y, x + w, y + h), radius, fill=fill, outline=border, width=2)
    draw.text((x + 18, y + 14), title, font=FONT_L, fill=title_fill)

def draw_scenario_pill(draw, text, y, color_rgba):
    tb = draw.textbbox((0, 0), text, font=FONT_M_B)
    pw = (tb[2]-tb[0]) + 34
    ph = (tb[3]-tb[1]) + 18
    px = (W - pw) // 2
    round_rect(draw, (px, y, px+pw, y+ph), 22, fill=alpha_color((0, 0, 0), 120), outline=color_rgba, width=3)
    draw.text((px + 17, y + 9), text, font=FONT_M_B, fill=color_rgba)

# Timeline
INTRO_DUR = 0.9
RUN_DUR = 7.8
TRANS_DUR = 0.6
OUTRO_DUR = 1.6
TOTAL_DUR = INTRO_DUR + RUN_DUR + TRANS_DUR + RUN_DUR + OUTRO_DUR
TOTAL_FRAMES = int(TOTAL_DUR * FPS)

# Deterministic errors
random.seed(7)
is_error = {i: (random.random() < 0.2) for i in range(1, 11)}

def run_phase(t):
    if t < INTRO_DUR: 
        return ("intro", t)
    t -= INTRO_DUR
    if t < RUN_DUR: 
        return ("dlq_run", t)
    t -= RUN_DUR
    if t < TRANS_DUR: 
        return ("transition", t)
    t -= TRANS_DUR
    if t < RUN_DUR: 
        return ("no_dlq_run", t)
    t -= RUN_DUR
    return ("outro", t)

SPACING = 0.75
PROC = 0.95
RESULT = 0.45

def message_state(local_t, msg_id):
    t0 = (msg_id - 1) * SPACING
    if local_t < t0: return None
    if local_t < t0 + PROC: return "processing"
    if local_t < t0 + PROC + RESULT: return "error" if is_error[msg_id] else "success"
    return "done"

def dlq_list(local_t):
    out = []
    for i in range(1, 11):
        t0 = (i - 1) * SPACING
        if is_error[i] and local_t >= t0 + PROC + RESULT:
            out.append(i)
    return out

def lost_count(local_t):
    c = 0
    for i in range(1, 11):
        t0 = (i - 1) * SPACING
        if is_error[i] and local_t >= t0 + PROC + RESULT:
            c += 1
    return c

def draw_frame(frame_idx):
    t = frame_idx / FPS
    phase, lt = run_phase(t)

    img = BG.copy()
    draw = ImageDraw.Draw(img, "RGBA")

    # Header
    title1, title2 = "Dead Letter Queues", "Are Not Optional"
    subtitle = 'They’re the difference between "Recoverable" and "Broken" pipelines'
    a = min(1.0, lt / INTRO_DUR) if phase == "intro" else 1.0
    header_y = 18

    draw_centered(draw, title1, header_y, FONT_XL, (255, 255, 255, int(255 * a)))
    bb2 = draw.textbbox((0, 0), title2, font=FONT_XL)
    w2 = bb2[2] - bb2[0]
    draw.text(((W - w2) // 2, header_y + 58), title2, font=FONT_XL, fill=(245, 158, 11, int(255 * a)))
    draw_centered(draw, subtitle, header_y + 118, FONT_M, (209, 213, 219, int(235 * a)))

    # Credits bottom-right
    credit = "Chaitanya Pothuraju"
    cb = draw.textbbox((0, 0), credit, font=FONT_S)
    draw.text((W - (cb[2]-cb[0]) - 18, H - (cb[3]-cb[1]) - 14), credit, font=FONT_S, fill=(229, 231, 235, 220))

    # Pill + moved-down tiles
    pill_y = 162
    content_top = 220
    pad, col_gap = 24, 24

    if phase == "dlq_run":
        scenario, scenario_color, mode, local_t = "With DLQ (Recoverable)", (34, 197, 94, 255), "dlq", lt
    elif phase == "no_dlq_run":
        scenario, scenario_color, mode, local_t = "Without DLQ (Broken)", (239, 68, 68, 255), "no_dlq", lt
    elif phase == "transition":
        scenario, scenario_color, mode, local_t = "Switching scenario…", (96, 165, 250, 255), "transition", lt
    elif phase == "outro":
        scenario, scenario_color, mode, local_t = "Key takeaway", (245, 158, 11, 255), "outro", lt
    else:
        scenario, scenario_color, mode, local_t = "", (96, 165, 250, 255), "intro", lt

    if scenario:
        draw_scenario_pill(draw, scenario, pill_y, scenario_color)

    # Outro: no tiles
    if mode == "outro":
        panel_x, panel_y, panel_w, panel_h = 120, 250, W - 240, 360
        round_rect(draw, (panel_x, panel_y, panel_x+panel_w, panel_y+panel_h), 26,
                   fill=alpha_color((0, 0, 0), 110), outline=alpha_color((255,255,255), 60), width=2)

        draw_centered(draw, "“One bad event shouldn’t break your whole stream.”", 290, FONT_L, (229, 231, 235, 245))
        draw_centered(draw, "Seasoned data engineers never skip DLQs.", 342, FONT_M, (156, 163, 175, 235))

        bullets = [
            "Isolate failures (don’t block good traffic)",
            "Store bad events for investigation + replay",
            "Control retries (avoid infinite retry storms)",
        ]
        bx, by = panel_x + 90, 410
        for i, b in enumerate(bullets):
            draw.text((bx, by + i*56), f"✔  {b}", font=FONT_M_B, fill=(74, 222, 128, 240))
        return img.convert("RGB")

    # Card layout for other slides
    card_w = (W - pad*2 - col_gap) // 2
    card_h = 430
    x1, x2, y = pad, pad + card_w + col_gap, content_top

    make_card(draw, x1, y, card_w, card_h, "Main Pipeline",
              border=(96, 165, 250, 255), fill=alpha_color((255, 255, 255), 22), title_fill=(255, 255, 255, 240))

    if mode == "dlq":
        make_card(draw, x2, y, card_w, card_h, "Dead Letter Queue",
                  border=(34, 197, 94, 255), fill=alpha_color((34, 197, 94), 20), title_fill=(255, 255, 255, 240))
    elif mode == "no_dlq":
        make_card(draw, x2, y, card_w, card_h, "Lost Forever",
                  border=(239, 68, 68, 255), fill=alpha_color((239, 68, 68), 20), title_fill=(255, 255, 255, 240))
    else:
        make_card(draw, x2, y, card_w, card_h, "Outcome",
                  border=(156, 163, 175, 255), fill=alpha_color((255, 255, 255), 20), title_fill=(255, 255, 255, 230))

    def draw_msg_card(cx, cy, mw, mh, msg_id, status):
        if status == "processing":
            border, fill, icon, icon_fill = (96,165,250,255), alpha_color((59,130,246), 46), "⟳", (96,165,250,255)
        elif status == "error":
            border, fill, icon, icon_fill = (248,113,113,255), alpha_color((239,68,68), 46), "✖", (248,113,113,255)
        else:
            border, fill, icon, icon_fill = (74,222,128,255), alpha_color((34,197,94), 46), "✔", (74,222,128,255)

        round_rect(draw, (cx, cy, cx+mw, cy+mh), 14, fill=fill, outline=border, width=2)
        draw.text((cx+14, cy+10), f"Message #{msg_id}", font=FONT_MONO, fill=(255,255,255,235))
        draw.text((cx+mw-32, cy+8), icon, font=FONT_L, fill=icon_fill)

        if status == "processing":
            ang = (frame_idx * 15) % 360
            r = 10
            ox, oy = cx+mw-68, cy+mh-18
            draw.arc([ox-r, oy-r, ox+r, oy+r], start=ang, end=ang+240, fill=icon_fill, width=3)
            draw.text((cx+14, cy+mh-28), "processing", font=FONT_S, fill=(191,219,254,220))
        elif status == "error":
            draw.text((cx+14, cy+mh-28), "error", font=FONT_S, fill=(254,202,202,220))
        else:
            draw.text((cx+14, cy+mh-28), "success", font=FONT_S, fill=(187,247,208,220))

    # Pipeline list
    list_x, list_y = x1 + 18, y + 74
    list_w, row_h = card_w - 36, 58
    max_rows = 6

    pipeline_msgs = []
    if mode in ("dlq", "no_dlq"):
        for i in range(1, 11):
            st = message_state(local_t, i)
            if st in ("processing", "error", "success"):
                pipeline_msgs.append((i, st))
        pipeline_msgs = pipeline_msgs[-max_rows:]

    if mode in ("dlq", "no_dlq") and not pipeline_msgs and local_t < 0.25:
        draw.text((list_x, list_y+10), "Starting…", font=FONT_M, fill=(156,163,175,220))

    for idx, (mid, st) in enumerate(pipeline_msgs):
        cy = list_y + idx * (row_h + 10)
        draw_msg_card(list_x, cy, list_w, row_h, mid, st)

    # Right side
    if mode == "dlq":
        dlq = dlq_list(local_t)
        rx, ry, rw = x2 + 18, y + 74, card_w - 36
        if not dlq:
            draw.text((rx, ry+10), "Failed messages land here for retry.", font=FONT_M, fill=(209,213,219,220))
        else:
            for idx, mid in enumerate(dlq[-6:]):
                cy = ry + idx * (row_h + 10)
                round_rect(draw, (rx, cy, rx+rw, cy+row_h), 14,
                           fill=alpha_color((245,158,11), 46),
                           outline=(245,158,11,255), width=2)
                draw.text((rx+14, cy+10), f"Message #{mid}", font=FONT_MONO, fill=(255,255,255,235))
                draw.text((rx+14, cy+row_h-28), "recoverable (stored for replay)", font=FONT_S, fill=(253,230,138,230))
                draw.text((rx+rw-36, cy+8), "⟳", font=FONT_L, fill=(253,230,138,255))

    elif mode == "no_dlq":
        c = lost_count(local_t)
        if c == 0:
            draw.text((x2+18, y+110), "Any failed message is lost permanently.", font=FONT_M, fill=(209,213,219,220))
        else:
            s = str(c)
            bb = draw.textbbox((0,0), s, font=BIG_92)
            sw = bb[2]-bb[0]
            draw.text((x2 + (card_w - sw)//2, y+180), s, font=BIG_92, fill=(248,113,113,255))
            draw.text((x2+70, y+290), "messages lost forever", font=FONT_L, fill=(252,165,165,240))
            draw.text((x2+70, y+330), "no replay • no audit • no fix", font=FONT_M, fill=(254,202,202,220))
            draw.text((x2+70, y+375), "…and the dashboard data stays wrong.", font=FONT_M, fill=(254,202,202,220))
            draw.text((x2 + card_w - 120, y+165), "✖", font=BIG_120, fill=(248,113,113,180))

    elif mode == "transition":
        bx, by, bw, bh = pad, y + 90, W - pad*2, 240
        round_rect(draw, (bx, by, bx+bw, by+bh), 26, fill=alpha_color((0,0,0), 110), outline=(96,165,250,255), width=2)
        draw_centered(draw, "Resetting…", by+36, FONT_XL, (255,255,255,240))
        draw_centered(draw, "Same traffic. Different outcome.", by+130, FONT_L, (255,255,255,240))

    return img.convert("RGB")

# Write video via ffmpeg pipe
OUT_DIR = "/mnt/data/dlq_video"
os.makedirs(OUT_DIR, exist_ok=True)
mp4_path = os.path.join(OUT_DIR, "dlq_simulation_v2.mp4")

ffmpeg = shutil.which("ffmpeg")
if not ffmpeg:
    raise RuntimeError("ffmpeg is not available here.")

cmd = [
    ffmpeg, "-y",
    "-f", "rawvideo",
    "-vcodec", "rawvideo",
    "-pix_fmt", "rgb24",
    "-s", f"{W}x{H}",
    "-r", str(FPS),
    "-i", "-",
    "-an",
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "-movflags", "+faststart",
    mp4_path
]

proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

for i in range(TOTAL_FRAMES):
    frame = draw_frame(i)
    proc.stdin.write(frame.tobytes())

proc.stdin.close()
ret = proc.wait()
stderr = proc.stderr.read().decode("utf-8", errors="ignore")
if ret != 0:
    raise RuntimeError(stderr[-2000:])

(mp4_path, os.path.getsize(mp4_path))
