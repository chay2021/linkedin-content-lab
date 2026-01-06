
# v3: Adjust ES→Dashboards curved link to match reference, keep v2 styling
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import math
import imageio

W, H = 1280, 720
BG_TOP = (10, 16, 31)
BG_BOTTOM = (14, 22, 42)
PANEL = (20, 28, 50)
TEXT = (235, 200, 207)      # your variant
MUTED = (168, 180, 205)
TEAL = (0, 207, 173)
BLUE = (47, 146, 255)
PURPLE = (164, 116, 255)
AMBER = (255, 176, 0)
CYAN = (0, 212, 255)
ERR = (255, 90, 95)
WARN = (208, 193, 70)       # your variant
OUTLINE = (50, 80, 140)
SHADOW = (8, 12, 22)
LINK = (112, 189, 255)      # brighter blue for the curved link

# ---- Fonts (single block) ----
try:
    FONT_TITLE = ImageFont.truetype("DejaVuSans.ttf", 38)
    FONT_SUB   = ImageFont.truetype("DejaVuSans.ttf", 22)
    FONT_SMALL = ImageFont.truetype("DejaVuSans.ttf", 18)
    FONT_CREDIT= ImageFont.truetype("DejaVuSans.ttf", 18)
except:
    FONT_TITLE = ImageFont.load_default()
    FONT_SUB   = ImageFont.load_default()
    FONT_SMALL = ImageFont.load_default()
    FONT_CREDIT= ImageFont.load_default()

# ---- Layout ----
layout = {
    "source":   (80,  315, 220,  90),
    "kafka":    (330, 300, 340, 120),
    "consumers":(700, 300, 340, 120),
    "es":       (1080,300, 180, 120),
    "dash":     (1050,470, 210, 100),
}

# ---- Scenes ----
scenes = [
    {"name": "Title",         "dur": 2.0},
    {"name": "Normal",        "dur": 4.0, "lag_target": 0},
    {"name": "Peak",          "dur": 5.0, "lag_target": 120_000},
    {"name": "Hot Partition", "dur": 5.0, "lag_target": 500_000},
    {"name": "Slow Downstream","dur": 5.0, "lag_target": 220_000},
    {"name": "Heavy Logic",   "dur": 5.0, "lag_target": 300_000},
    {"name": "Retry Storm",   "dur": 5.0, "lag_target": 800_000},
    {"name": "Closing",       "dur": 2.0},
]

scene_cum = []
acc = 0.0
for s in scenes:
    scene_cum.append((acc, acc + s["dur"], s))
    acc += s["dur"]
TOTAL_DUR = acc
FPS = 20
TOTAL_FRAMES = int(TOTAL_DUR * FPS)

# ---- Helpers ----
def gradient_bg():
    arr = np.zeros((H, W, 3), dtype=np.uint8)
    for y in range(H):
        t = y/(H-1)
        r = int(BG_TOP[0]*(1-t) + BG_BOTTOM[0]*t)
        g = int(BG_TOP[1]*(1-t) + BG_BOTTOM[1]*t)
        b = int(BG_TOP[2]*(1-t) + BG_BOTTOM[2]*t)
        arr[y,:,0] = r; arr[y,:,1] = g; arr[y,:,2] = b
    return Image.fromarray(arr)

def draw_shadowed_rounded(draw, xy, radius, fill, outline=None, width=2):
    x, y, w, h = xy
    draw.rounded_rectangle([x+3, y+4, x+w+3, y+h+4], radius=radius, fill=SHADOW)
    draw.rounded_rectangle([x,   y,   x+w,   y+h   ], radius=radius, fill=fill, outline=outline, width=width)

def draw_box(draw, xy, title, outline=OUTLINE, fill=PANEL, accent=None):
    x, y, w, h = xy
    draw_shadowed_rounded(draw, (x, y, w, h), radius=16, fill=fill, outline=outline, width=3)
    draw.text((x+12, y+10), title, fill=TEXT, font=FONT_SUB)
    if accent:
        draw.rounded_rectangle([x+12, y+h-12, x+w-12, y+h-8], radius=4, fill=accent)

def draw_arrow(draw, x1, y1, x2, y2, color, pulse=1.0):
    c = tuple(int(color[i]*pulse) for i in range(3))
    draw.line([(x1, y1), (x2, y2)], fill=c, width=5)
    angle = math.atan2(y2-y1, x2-x1)
    L = 14
    p1 = (x2, y2)
    p2 = (x2 - L*math.cos(angle - 0.4), y2 - L*math.sin(angle - 0.4))
    p3 = (x2 - L*math.cos(angle + 0.4), y2 - L*math.sin(angle + 0.4))
    draw.polygon([p1, p2, p3], fill=c)

def draw_curve_arrow(draw, p0, p1, p2, color, width=7):
    """Quadratic Bézier from p0→p2 with control p1."""
    pts = []
    steps = 50
    for i in range(steps+1):
        t = i/steps
        x = (1-t)**2*p0[0] + 2*(1-t)*t*p1[0] + t**2*p2[0]
        y = (1-t)**2*p0[1] + 2*(1-t)*t*p1[1] + t**2*p2[1]
        pts.append((x, y))
    for i in range(len(pts)-1):
        draw.line([pts[i], pts[i+1]], fill=color, width=width)
    # arrow head
    x2, y2 = pts[-1]; x1, y1 = pts[-2]
    angle = math.atan2(y2-y1, x2-x1)
    L = 16
    pA = (x2, y2)
    pB = (x2 - L*math.cos(angle - 0.4), y2 - L*math.sin(angle - 0.4))
    pC = (x2 - L*math.cos(angle + 0.4), y2 - L*math.sin(angle + 0.4))
    draw.polygon([pA, pB, pC], fill=color)

def lerp(a, b, t):
    return a + (b - a) * t

def scenario_state(name, t_rel, dur):
    state = {
        "src_rate": 1000,
        "part_fill": [0.10]*6,
        "part_hot":  [False]*6,
        "cons_state":["steady"]*6,
        "cons_bar":  [0.25]*6,
        "es_meter":  0.20,
        "dash_stale":False,
        "dash_delay":0.0,
        "lag":       0,
        "status":    ("STEADY", "Balanced production & consumption."),
    }
    prog = t_rel/dur if dur > 0 else 1.0
    if name == "Normal":
        pass
    elif name == "Peak":
        state["src_rate"]  = 8000
        state["part_fill"] = [lerp(0.1, 0.6, prog)]*6
        state["dash_stale"]= True
        state["status"]    = ("WARN", "Peak load. Lag rises because downstream throughput is capped.")
        state["lag"]       = int(lerp(0, 120_000, prog))
    elif name == "Hot Partition":
        state["src_rate"]  = 5000
        fills = [0.15]*6; fills[2] = lerp(0.2, 0.95, prog)
        state["part_fill"] = fills
        hot = [False]*6; hot[2] = True
        state["part_hot"]  = hot
        cons = ["steady"]*6; cons[2] = "block"
        state["cons_state"]= cons
        bars = [0.25]*6; bars[2] = 0.05
        state["cons_bar"]  = bars
        state["status"]    = ("ERROR", "Hot partition. One consumer bottlenecks; more consumers do not help.")
        state["lag"]       = int(lerp(0, 500_000, prog))
    elif name == "Slow Downstream":
        state["cons_state"]= ["wait"]*6
        state["cons_bar"]  = [0.10]*6
        state["es_meter"]  = lerp(0.2, 0.95, prog)
        state["dash_stale"]= True
        state["dash_delay"]= lerp(0, 45, prog)
        state["status"]    = ("ERROR", "Downstream slow. Elasticsearch throttles; consumers wait.")
        state["lag"]       = int(lerp(0, 220_000, prog))
    elif name == "Heavy Logic":
        state["cons_state"]= ["block"]*6
        state["cons_bar"]  = [lerp(0.25, 0.08, prog)]*6
        state["status"]    = ("WARN", "Heavy transforms & sync calls reduce throughput.")
        state["lag"]       = int(lerp(0, 300_000, prog))
    elif name == "Retry Storm":
        cons = []; bars = []
        for i in range(6):
            if i % 2 == 0:
                cons.append("block"); bars.append(lerp(0.25, 0.05, prog))
            else:
                cons.append("wait");  bars.append(lerp(0.25, 0.12, prog))
        state["cons_state"]= cons
        state["cons_bar"]  = bars
        state["status"]    = ("ERROR", "Retry storm. Duplicates amplify load; lag is a side effect.")
        state["lag"]       = int(lerp(0, 800_000, prog))
    return state

# ---- Frame builder ----
def make_frame(time_s):
    # Pick scene
    for (t0, t1, s) in scene_cum:
        if t0 <= time_s < t1:
            name = s["name"]; t_rel = time_s - t0; dur = s["dur"]
            break
    else:
        name = "Closing"; t_rel = 0; dur = 1

    img = gradient_bg()
    draw = ImageDraw.Draw(img)

    # Title
    draw.text((40, 40), "Consumer Lag Is a Symptom — Not the Problem", fill=TEXT, font=FONT_TITLE)
    draw.text((40, 88), "Kafka → Consumers → Elasticsearch → Dashboards", fill=MUTED, font=FONT_SUB)

    # Boxes
    draw_box(draw, layout["source"],    "Source",        accent=TEAL)
    draw_box(draw, layout["kafka"],     "Kafka Topic",   accent=BLUE)
    draw_box(draw, layout["consumers"], "Consumers (6)", accent=PURPLE)
    draw_box(draw, layout["es"],        "Elasticsearch", accent=AMBER)
    draw_box(draw, layout["dash"],      "Dashboards",    accent=CYAN)

    # Arrows pulse
    def pulse(t): return 0.8 + 0.2*math.sin(2*math.pi*t)
    p = pulse(time_s)

    xS, yS, wS, hS = layout["source"]
    xK, yK, wK, hK = layout["kafka"]
    xC, yC, wC, hC = layout["consumers"]
    xE, yE, wE, hE = layout["es"]
    xD, yD, wD, hD = layout["dash"]

    # Straight arrows
    draw_arrow(draw, xS+wS, yS+hS//2, xK, yK+hK//2, OUTLINE, p)
    draw_arrow(draw, xK+wK, yK+hK//2, xC, yC+hC//2, OUTLINE, p)
    draw_arrow(draw, xC+wC, yC+hC//2, xE, yE+hE//2, OUTLINE, p)

    # ---- ES → Dashboards curved link (use LINK for highlight, or OUTLINE for uniform) ----
    p0   = (xE + wE//2, yE + hE + 8)                 # bottom-center just below ES
    p2   = (xD + wD//2, yD - 8)                      # top-center just above Dashboards
    ctrl = (max(xE, xD) + abs(xD - xE)//2 + 80, (p0[1] + p2[1])//2)   # smooth arc to the right
    draw_curve_arrow(draw, p0, ctrl, p2, color=OUTLINE, width=7)
    # If you want uniform color across links:
    # draw_curve_arrow(draw, p0, ctrl, p2, color=OUTLINE, width=7)

    # Scene text & metrics
    if name in ("Title", "Closing"):
        msg = ("Lag is your most honest signal. Find the bottleneck; don’t just add consumers."
               if name=="Title" else
               "Junior react to lag. Senior investigate lag.")
        draw.text((40, 130), msg, fill=TEXT, font=FONT_SUB)
    else:
        state = scenario_state(name, t_rel, dur)

        # Source badge
        draw.text((layout["source"][0]+12, layout["source"][1]+58),
                  f"events/sec: {state['src_rate']:,}", fill=MUTED, font=FONT_SMALL)

        # Kafka partitions
        kx, ky, kw, kh = layout["kafka"]
        gap = 6
        pw  = (kw - (gap*5) - 20)//6
        ph  = 20
        py  = ky + 60
        for i in range(6):
            px = kx + 12 + i*(pw+gap)
            outline = OUTLINE if not state["part_hot"][i] else ERR
            draw.rounded_rectangle([px, py, px+pw, py+ph], radius=6, fill=(21,34,68), outline=outline, width=2)
            fillw = int(pw * state["part_fill"][i])
            fill_color = BLUE if not state["part_hot"][i] else ERR
            draw.rounded_rectangle([px, py, px+fillw, py+ph], radius=6, fill=fill_color)

        # Consumers tiles & bars
        cx, cy, cw, ch = layout["consumers"]
        cg  = 6
        bw  = (cw - 20 - cg*5) // 6
        for i in range(6):
            bx = cx + 12 + i*(bw + cg)
            by = cy + 58
            bh = 44
            state_i = state["cons_state"][i]
            outline = OUTLINE
            if state_i == "wait": outline = WARN
            elif state_i == "block": outline = ERR
            draw.rounded_rectangle([bx, by, bx+bw, by+bh], radius=6, fill=(20,32,60), outline=outline, width=2)
            barw = int(bw * state["cons_bar"][i])
            bar_color = PURPLE if state_i == "steady" else (AMBER if state_i == "wait" else ERR)
            draw.rounded_rectangle([bx+4, by+bh-12, bx+4+barw, by+bh-7], radius=4, fill=bar_color)

        # ES meter
        ex, ey, ew, eh = layout["es"]
        meter_w = ew - 20
        mx = ex + 12; my = ey + 70
        draw.rounded_rectangle([mx, my, mx+meter_w, my+14], radius=6, fill=(26,40,73), outline=(57,74,122), width=2)
        meter_fill = int(meter_w * state["es_meter"]) if state["es_meter"] else 0
        draw.rounded_rectangle([mx, my, mx+meter_fill, my+14], radius=6, fill=AMBER)
        if state["es_meter"] and state["es_meter"] > 0.85:
            draw.rounded_rectangle([ex, ey, ex+ew, ey+eh], radius=16, outline=ERR, width=3)
        draw.text((ex+12, ey+94), f"Indexing latency: {int(40 + 80*state['es_meter'])}ms",
                  fill=MUTED, font=FONT_SMALL)

        # Dashboards tiles
        dx, dy, dw, dh = layout["dash"]
        tg = 8
        tw = (dw - 20 - 2*tg)//3
        ty = dy + 52
        for i in range(3):
            tx = dx + 12 + i*(tw + tg)
            outline = OUTLINE if not state["dash_stale"] else WARN
            draw.rounded_rectangle([tx, ty, tx+tw, ty+22], radius=6, fill=(15,26,51), outline=outline, width=2)
        draw.text((dx+12, dy+28), f"Delay: {int(state['dash_delay'])}s", fill=MUTED, font=FONT_SMALL)

        # Lag text (Kafka bottom-right)
        draw.text((kx+kw-210, ky+kh-28), f"Total lag: {state['lag']:,}", fill=MUTED, font=FONT_SMALL)

        # Status ribbon
        sev, msg = state["status"]
        color = TEAL if sev=="STEADY" else (WARN if sev=="WARN" else ERR)
        draw.text((40, 180), f"Scene: {name}", fill=TEXT, font=FONT_SUB)
        draw.text((40, 204), f"Status: {sev} — {msg}", fill=color, font=FONT_SUB)
        draw.text((40, 232), "Lag shows WHERE the pain is, not WHAT to fix.", fill=MUTED, font=FONT_SMALL)

    # Credits
    credit_txt = "Credits: Chaitanya Pothuraju"
    bbox = draw.textbbox((0,0), credit_txt, font=FONT_CREDIT)
    tw = bbox[2] - bbox[0]; th = bbox[3] - bbox[1]
    draw.text((W - tw - 20, H - th - 16), credit_txt, fill=MUTED, font=FONT_CREDIT)

    return np.array(img)

# ---- Render ----
mp4_written = False
try:
    writer = imageio.get_writer('draft_consumer-lag-architecture-v3.mp4', fps=FPS, codec='libx264', quality=8)
    for i in range(TOTAL_FRAMES):
        t = i / FPS
        frame = make_frame(t)
        writer.append_data(frame)
    writer.close()
    mp4_written = True
except Exception as e:
    # Fallback GIF
    imageio.mimsave('draft_consumer-lag-architecture-v3.gif',
                    [make_frame(i/FPS) for i in range(TOTAL_FRAMES)], fps=12)

print('Created:', 'MP4' if mp4_written else 'GIF')
