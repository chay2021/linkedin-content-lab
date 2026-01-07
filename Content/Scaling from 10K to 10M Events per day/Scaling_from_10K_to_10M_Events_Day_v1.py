
# v4: "What We Thought Would Change vs What Actually Did" — quick architecture video
# Based on your base script; adds BEFORE (App→Logstash→ES→Dashboards) vs AFTER (App→Kafka→Consumers→ES→Dashboards)
# and ties scenes to the article’s core lessons: buffering, backpressure, retries, observability, simple designs.

from PIL import Image, ImageDraw, ImageFont
from matplotlib.pyplot import draw
import numpy as np
import math
import imageio

W, H = 1280, 720
BG_TOP = (10, 16, 31)
BG_BOTTOM = (14, 22, 42)
PANEL = (20, 28, 50)
TEXT = (235, 200, 207)
MUTED = (168, 180, 205)
TEAL = (0, 207, 173)
BLUE = (47, 146, 255)
PURPLE = (164, 116, 255)
AMBER = (255, 176, 0)
CYAN = (0, 212, 255)
ERR = (255, 90, 95)
WARN = (208, 193, 70)
OUTLINE = (50, 80, 140)
SHADOW = (8, 12, 22)
LINK = (112, 189, 255)

# Fonts
try:
    FONT_TITLE = ImageFont.truetype("DejaVuSans.ttf", 48)  # Increased from 38 to 48
    FONT_SUB = ImageFont.truetype("DejaVuSans.ttf", 32)    # Increased from 22 to 32
    FONT_SMALL = ImageFont.truetype("DejaVuSans.ttf", 28)  # Increased from 18 to 28
    FONT_CREDIT = ImageFont.truetype("DejaVuSans.ttf", 28) # Increased from 18 to 28
except:
    FONT_TITLE = ImageFont.load_default()
    FONT_SUB = ImageFont.load_default()
    FONT_SMALL = ImageFont.load_default()
    FONT_CREDIT = ImageFont.load_default()
# try:
#     FONT_TITLE = ImageFont.truetype("DejaVuSans.ttf", 38)
#     FONT_SUB = ImageFont.truetype("DejaVuSans.ttf", 22)
#     FONT_SMALL = ImageFont.truetype("DejaVuSans.ttf", 18)
#     FONT_CREDIT = ImageFont.truetype("DejaVuSans.ttf", 18)
# except:
#     FONT_TITLE = ImageFont.load_default()
#     FONT_SUB = ImageFont.load_default()
#     FONT_SMALL = ImageFont.load_default()
#     FONT_CREDIT = ImageFont.load_default()

# Layouts
layout_after = {
    "source": (80, 315, 220, 90),      # App
    "kafka": (330, 300, 340, 120),
    "consumers": (700, 300, 340, 120),
    "es": (1080, 300, 180, 120),
    "dash": (1050, 470, 210, 100),
}
layout_before = {
    "app": (80, 315, 220, 90),
    "logstash": (420, 300, 260, 120),
    "es": (780, 300, 220, 120),
    "dash": (760, 470, 240, 100),
}

# Scenes — ordered
scenes = [
    {"name": "Title", "dur": 2.0, "mode": "title"},
    {"name": "Before — 10K/day", "dur": 4.0, "mode": "before", "events": 10000},
    {"name": "Before — Spike hits", "dur": 5.0, "mode": "before", "events": 200000},
    {"name": "Shift — Insert Kafka buffer", "dur": 3.0, "mode": "transition"},
    {"name": "After — Baseline", "dur": 4.0, "mode": "after", "lag_target": 0},
    {"name": "After — Peak load", "dur": 5.0, "mode": "after", "lag_target": 120_000},
    {"name": "After — Hot Partition", "dur": 5.0, "mode": "after", "lag_target": 500_000},
    {"name": "After — Downstream Slow", "dur": 5.0, "mode": "after", "lag_target": 220_000},
    {"name": "After — Retry Storm", "dur": 5.0, "mode": "after", "lag_target": 800_000},
    {"name": "Observability — What we debug", "dur": 4.0, "mode": "obs"},
    {"name": "Closing", "dur": 2.0, "mode": "closing"},
]

scene_cum = []
acc = 0.0
for s in scenes:
    scene_cum.append((acc, acc + s["dur"], s))
    acc += s["dur"]
TOTAL_DUR = acc
FPS = 20
TOTAL_FRAMES = int(TOTAL_DUR * FPS)

# Helpers
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
    draw.rounded_rectangle([x, y, x+w, y+h], radius=radius, fill=fill, outline=outline, width=width)

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
    pts = []
    steps = 50
    for i in range(steps+1):
        t = i/steps
        x = (1-t)**2*p0[0] + 2*(1-t)*t*p1[0] + t**2*p2[0]
        y = (1-t)**2*p0[1] + 2*(1-t)*t*p1[1] + t**2*p2[1]
        pts.append((x, y))
    for i in range(len(pts)-1):
        draw.line([pts[i], pts[i+1]], fill=color, width=width)
    x2, y2 = pts[-1]; x1, y1 = pts[-2]
    angle = math.atan2(y2-y1, x2-x1)
    L = 16
    pA = (x2, y2)
    pB = (x2 - L*math.cos(angle - 0.4), y2 - L*math.sin(angle - 0.4))
    pC = (x2 - L*math.cos(angle + 0.4), y2 - L*math.sin(angle + 0.4))
    draw.polygon([pA, pB, pC], fill=color)

def lerp(a, b, t):
    return a + (b - a) * t

# State builders

def before_state(name, t_rel, dur, events):
    prog = t_rel/dur if dur > 0 else 1.0
    state = {
        "events": events,
        "es_meter": 0.20,
        "dash_stale": False,
        "dash_delay": 0,
        "gc_pause": 0.0,
        "retry_rate": 0.0,
        "status": ("STEADY", "10K/day — Fast dashboards, low CPU, no alerts."),
    }
    if "Spike" in name:
        # No buffer; indexing fights search, GC pauses climb, retries amplify load
        state["es_meter"] = lerp(0.3, 0.95, prog)
        state["gc_pause"] = lerp(5, 180, prog)  # ms
        state["retry_rate"] = lerp(0.0, 0.18, prog)  # fraction
        state["dash_stale"] = True
        state["dash_delay"] = int(lerp(0, 45, prog))
        state["status"] = ("ERROR", "Spike without buffer — ES throttles; retries cascade.")
    return state


def after_state(name, t_rel, dur):
    # use your original rich after-state logic
    state = {
        "src_rate": 1000,
        "part_fill": [0.10]*6,
        "part_hot": [False]*6,
        "cons_state": ["steady"]*6,
        "cons_bar": [0.25]*6,
        "es_meter": 0.20,
        "dash_stale": False,
        "dash_delay": 0.0,
        "lag": 0,
        "status": ("STEADY", "Buffered ingestion. Balanced production & consumption."),
    }
    prog = t_rel/dur if dur > 0 else 1.0
    if "Peak" in name:
        state["src_rate"] = 8000
        state["part_fill"] = [lerp(0.1, 0.6, prog)]*6
        state["dash_stale"] = True
        state["status"] = ("WARN", "Peak load. Lag rises; downstream throughput is capped.")
        state["lag"] = int(lerp(0, 120_000, prog))
    elif "Hot Partition" in name:
        state["src_rate"] = 5000
        fills = [0.15]*6; fills[2] = lerp(0.2, 0.95, prog)
        state["part_fill"] = fills
        hot = [False]*6; hot[2] = True
        state["part_hot"] = hot
        cons = ["steady"]*6; cons[2] = "block"
        state["cons_state"] = cons
        bars = [0.25]*6; bars[2] = 0.05
        state["cons_bar"] = bars
        state["status"] = ("ERROR", "Hot partition — one consumer bottlenecks; more consumers don’t help.")
        state["lag"] = int(lerp(0, 500_000, prog))
    elif "Downstream Slow" in name:
        state["cons_state"] = ["wait"]*6
        state["cons_bar"] = [0.10]*6
        state["es_meter"] = lerp(0.2, 0.95, prog)
        state["dash_stale"] = True
        state["dash_delay"] = lerp(0, 45, prog)
        state["status"] = ("ERROR", "Downstream slow — ES throttles; consumers apply backpressure.")
        state["lag"] = int(lerp(0, 220_000, prog))
    elif "Retry Storm" in name:
        cons = []
        bars = []
        for i in range(6):
            if i % 2 == 0:
                cons.append("block"); bars.append(lerp(0.25, 0.05, prog))
            else:
                cons.append("wait"); bars.append(lerp(0.25, 0.12, prog))
        state["cons_state"] = cons
        state["cons_bar"] = bars
        state["status"] = ("ERROR", "Retry storm — duplicates amplify load; lag is a side effect.")
        state["lag"] = int(lerp(0, 800_000, prog))
    return state

# Frame builder

def make_frame(time_s):
    # Pick scene
    for (t0, t1, s) in scene_cum:
        if t0 <= time_s < t1:
            name = s["name"]; t_rel = time_s - t0; dur = s["dur"]; mode = s["mode"]
            events = s.get("events", 0)
            break
    else:
        name = "Closing"; t_rel = 0; dur = 1; mode = "closing"; events = 0

    img = gradient_bg()
    draw = ImageDraw.Draw(img)

    # Title strip
    draw.text((40, 40), "What We Thought Would Change vs What Actually Did", fill=TEXT, font=FONT_TITLE)
    draw.text((40, 88), "Scaling observability pipelines", fill=MUTED, font=FONT_SUB)

    # Pulse for arrows
    p = 0.8 + 0.2*math.sin(2*math.pi*time_s)

    if mode == "title":
        draw.text((40, 130), "Before: App → Logstash → Elasticsearch → Dashboards", fill=TEXT, font=FONT_SUB)
        draw.text((40, 160), "After:   App → Kafka → Consumers → Elasticsearch → Dashboards", fill=TEXT, font=FONT_SUB)
        draw.text((40, 200), "Scaling exposes assumptions. Search engines are not buffers.", fill=MUTED, font=FONT_SMALL)

    elif mode == "before":
        # Boxes
        draw_box(draw, layout_before["app"], "App", accent=TEAL)
        draw_box(draw, layout_before["logstash"], "Logstash", accent=BLUE)
        draw_box(draw, layout_before["es"], "Elasticsearch", accent=AMBER)
        draw_box(draw, layout_before["dash"], "Dashboards", accent=CYAN)
        # Arrows
        ax, ay, aw, ah = layout_before["app"]
        lx, ly, lw, lh = layout_before["logstash"]
        ex, ey, ew, eh = layout_before["es"]
        dx, dy, dw, dh = layout_before["dash"]
        draw_arrow(draw, ax+aw, ay+ah//2, lx, ly+lh//2, OUTLINE, p)
        draw_arrow(draw, lx+lw, ly+lh//2, ex, ey+eh//2, OUTLINE, p)
        # curved ES→Dashboards
        p0 = (ex + ew//2, ey + eh + 8)
        p2 = (dx + dw//2, dy - 8)
        ctrl = (max(ex, dx) + abs(dx - ex)//2 + 60, (p0[1] + p2[1])//2)
        draw_curve_arrow(draw, p0, ctrl, p2, color=OUTLINE, width=7)
        # Metrics for before
        state = before_state(name, t_rel, dur, events)
        draw.text((ax+12, ay+58), f"events/day: {state['events']:,}", fill=MUTED, font=FONT_SMALL)
        # ES meter
        meter_w = ew - 20
        mx = ex + 12; my = ey + 70
        draw.rounded_rectangle([mx, my, mx+meter_w, my+14], radius=6, fill=(26,40,73), outline=(57,74,122), width=2)
        meter_fill = int(meter_w * state["es_meter"]) if state["es_meter"] else 0
        draw.rounded_rectangle([mx, my, mx+meter_fill, my+14], radius=6, fill=AMBER)
        if state["es_meter"] and state["es_meter"] > 0.85:
            draw.rounded_rectangle([ex, ey, ex+ew, ey+eh], radius=16, outline=ERR, width=3)
        draw.text((ex+12, ey+94), f"Indexing latency: {int(40 + 80*state['es_meter'])}ms", fill=MUTED, font=FONT_SMALL)
        # Dashboards
        tx = layout_before["dash"][0] + 12
        ty = layout_before["dash"][1] + 52
        tw = (layout_before["dash"][2] - 20 - 2*8)//3
        for i in range(3):
            draw.rounded_rectangle([tx + i*(tw+8), ty, tx + i*(tw+8) + tw, ty+22], radius=6,
                                   fill=(15,26,51), outline=(OUTLINE if not state["dash_stale"] else WARN), width=2)
        draw.text((layout_before["dash"][0]+12, layout_before["dash"][1]+28), f"Delay: {int(state['dash_delay'])}s", fill=MUTED, font=FONT_SMALL)
        # Before-only signals
        draw.text((lx+12, ly+80), f"GC pause: {int(state['gc_pause'])}ms", fill=MUTED, font=FONT_SMALL)  # Moved up
        draw.text((lx+120, ly+94), f"Retry rate: {int(state['retry_rate']*100)}%", fill=MUTED, font=FONT_SMALL)  # Moved left
        sev, msg = state["status"]
        color = TEAL if sev == "STEADY" else (WARN if sev == "WARN" else ERR)
        draw.text((40, 180), f"Scene: {name}", fill=TEXT, font=FONT_SUB)
        draw.text((40, 204), f"Status: {sev} — {msg}", fill=color, font=FONT_SUB)
        draw.text((40, 232), "Search engines are not buffers.", fill=MUTED, font=FONT_SMALL)

    elif mode == "transition":
        # Show both pipelines faded, with Kafka highlighted
        # Before faded
        a, b, e, d = layout_before["app"], layout_before["logstash"], layout_before["es"], layout_before["dash"]
        draw_box(draw, a, "App", outline=(60,60,60), fill=(24,24,24))
        draw_box(draw, b, "Logstash", outline=(60,60,60), fill=(24,24,24))
        draw_box(draw, e, "Elasticsearch", outline=(60,60,60), fill=(24,24,24))
        draw_box(draw, d, "Dashboards", outline=(60,60,60), fill=(24,24,24))
        # After bright
        draw_box(draw, layout_after["source"], "App", accent=TEAL)
        draw_box(draw, layout_after["kafka"], "Kafka Topic", accent=BLUE)
        draw_box(draw, layout_after["consumers"], "Consumers (6)", accent=PURPLE)
        draw_box(draw, layout_after["es"], "Elasticsearch", accent=AMBER)
        draw_box(draw, layout_after["dash"], "Dashboards", accent=CYAN)
        # Arrows for after
        xS,yS,wS,hS = layout_after["source"]
        xK,yK,wK,hK = layout_after["kafka"]
        xC,yC,wC,hC = layout_after["consumers"]
        xE,yE,wE,hE = layout_after["es"]
        xD,yD,wD,hD = layout_after["dash"]
        draw_arrow(draw, xS+wS, yS+hS//2, xK, yK+hK//2, OUTLINE, p)
        draw_arrow(draw, xK+wK, yK+hK//2, xC, yC+hC//2, OUTLINE, p)
        draw_arrow(draw, xC+wC, yC+hC//2, xE, yE+hE//2, OUTLINE, p)
        p0 = (xE + wE//2, yE + hE + 8)
        p2 = (xD + wD//2, yD - 8)
        ctrl = (max(xE, xD) + abs(xD - xE)//2 + 80, (p0[1] + p2[1])//2)
        draw_curve_arrow(draw, p0, ctrl, p2, color=OUTLINE, width=7)
        draw.text((40, 180), "The shift that saves systems:", fill=TEXT, font=FONT_SUB)
        draw.text((40, 204), "Insert a durable queue (Kafka) to absorb spikes.", fill=MUTED, font=FONT_SMALL)
        draw.text((40, 228), "Let Elasticsearch focus on search. Failures stop cascading.", fill=MUTED, font=FONT_SMALL)

    elif mode == "after":
        # Render After pipeline (your original style)
        draw_box(draw, layout_after["source"], "App", accent=TEAL)
        draw_box(draw, layout_after["kafka"], "Kafka Topic", accent=BLUE)
        draw_box(draw, layout_after["consumers"], "Consumers (6)", accent=PURPLE)
        draw_box(draw, layout_after["es"], "Elasticsearch", accent=AMBER)
        draw_box(draw, layout_after["dash"], "Dashboards", accent=CYAN)
        # Arrows
        xS,yS,wS,hS = layout_after["source"]
        xK,yK,wK,hK = layout_after["kafka"]
        xC,yC,wC,hC = layout_after["consumers"]
        xE,yE,wE,hE = layout_after["es"]
        xD,yD,wD,hD = layout_after["dash"]
        draw_arrow(draw, xS+wS, yS+hS//2, xK, yK+hK//2, OUTLINE, p)
        draw_arrow(draw, xK+wK, yK+hK//2, xC, yC+hC//2, OUTLINE, p)
        draw_arrow(draw, xC+wC, yC+hC//2, xE, yE+hE//2, OUTLINE, p)
        p0 = (xE + wE//2, yE + hE + 8)
        p2 = (xD + wD//2, yD - 8)
        ctrl = (max(xE, xD) + abs(xD - xE)//2 + 80, (p0[1] + p2[1])//2)
        draw_curve_arrow(draw, p0, ctrl, p2, color=OUTLINE, width=7)
        # Scene state
        state = after_state(name, t_rel, dur)
        # Source badge
        draw.text((layout_after["source"][0]+12, layout_after["source"][1]+58),
                  f"events/sec: {state['src_rate']:,}", fill=MUTED, font=FONT_SMALL)
        # Kafka partitions
        kx, ky, kw, kh = layout_after["kafka"]
        gap = 6
        pw = (kw - (gap*5) - 20)//6
        ph = 20
        py = ky + 60
        for i in range(6):
            px = kx + 12 + i*(pw+gap)
            outline = OUTLINE if not state["part_hot"][i] else ERR
            draw.rounded_rectangle([px, py, px+pw, py+ph], radius=6, fill=(21,34,68), outline=outline, width=2)
            fillw = int(pw * state["part_fill"][i])
            fill_color = BLUE if not state["part_hot"][i] else ERR
            draw.rounded_rectangle([px, py, px+fillw, py+ph], radius=6, fill=fill_color)
        # Consumers tiles & bars
        cx, cy, cw, ch = layout_after["consumers"]
        cg = 6
        bw = (cw - 20 - cg*5) // 6
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
        ex, ey, ew, eh = layout_after["es"]
        meter_w = ew - 20
        mx = ex + 12; my = ey + 70
        draw.rounded_rectangle([mx, my, mx+meter_w, my+14], radius=6, fill=(26,40,73), outline=(57,74,122), width=2)
        meter_fill = int(meter_w * state["es_meter"]) if state["es_meter"] else 0
        draw.rounded_rectangle([mx, my, mx+meter_fill, my+14], radius=6, fill=AMBER)
        if state["es_meter"] and state["es_meter"] > 0.85:
            draw.rounded_rectangle([ex, ey, ex+ew, ey+eh], radius=16, outline=ERR, width=3)
        draw.text((ex+12, ey+94), f"Indexing latency: {int(40 + 80*state['es_meter'])}ms", fill=MUTED, font=FONT_SMALL)
        # Dashboards tiles
        dx, dy, dw, dh = layout_after["dash"]
        tg = 8
        tw = (dw - 20 - 2*tg)//3
        ty = dy + 52
        for i in range(3):
            tx = dx + 12 + i*(tw + tg)
            outline = OUTLINE if not state["dash_stale"] else WARN
            draw.rounded_rectangle([tx, ty, tx+tw, ty+22], radius=6, fill=(15,26,51), outline=outline, width=2)
        draw.text((dx+12, dy+28), f"Delay: {int(state['dash_delay'])}s", fill=MUTED, font=FONT_SMALL)
        # Lag text
        draw.text((kx+kw-210, ky+kh-28), f"Total lag: {state['lag']:,}", fill=MUTED, font=FONT_SMALL)
        # Status ribbon
        sev, msg = state["status"]
        color = TEAL if sev=="STEADY" else (WARN if sev=="WARN" else ERR)
        draw.text((40, 180), f"Scene: {name}", fill=TEXT, font=FONT_SUB)
        draw.text((40, 204), f"Status: {sev} — {msg}", fill=color, font=FONT_SUB)
        draw.text((40, 232), "Backpressure keeps systems predictable.", fill=MUTED, font=FONT_SMALL)

    elif mode == "obs":
        # After layout with emphasis on metrics we actually debug
        draw_box(draw, layout_after["kafka"], "Kafka Topic", accent=BLUE)
        draw_box(draw, layout_after["consumers"], "Consumers (6)", accent=PURPLE)
        draw_box(draw, layout_after["es"], "Elasticsearch", accent=AMBER)
        # Consumer lag chart (textual badges)
        kx, ky, kw, kh = layout_after["kafka"]
        cx, cy, cw, ch = layout_after["consumers"]
        ex, ey, ew, eh = layout_after["es"]
        # Badges
        draw.text((kx+12, ky+90), "Consumer lag: 120,000 → 0", fill=MUTED, font=FONT_SMALL)
        draw.text((cx+12, cy+90), "Ingestion vs indexing rate", fill=MUTED, font=FONT_SMALL)
        draw.text((ex+12, ey+90), "P99 processing latency", fill=MUTED, font=FONT_SMALL)
        # Legend list
        draw.text((40, 180), "Observability beats raw throughput:", fill=TEXT, font=FONT_SUB)
        draw.text((40, 204), "Consumer lag  • Ingestion vs indexing  • Queue depth  • P95/P99 latencies", fill=MUTED, font=FONT_SMALL)
        draw.text((40, 232), "Dashboards become survival tools.", fill=MUTED, font=FONT_SMALL)

    else:  # closing
        msg_top = "Scaling isn’t about bigger machines or more threads."
        msg_mid = "Design for failure: buffer ingestion, apply backpressure, handle retries idempotently."
        msg_bot = "At 10K/day the happy path dominates; at 10M/day, the failure path is the system."
        draw.text((40, 130), msg_top, fill=TEXT, font=FONT_SUB)
        draw.text((40, 160), msg_mid, fill=MUTED, font=FONT_SMALL)
        draw.text((40, 188), msg_bot, fill=MUTED, font=FONT_SMALL)

    # Credits
    credit_txt = "Credits: Chaitanya Pothuraju"
    bbox = draw.textbbox((0,0), credit_txt, font=FONT_CREDIT)
    tw = bbox[2] - bbox[0]; th = bbox[3] - bbox[1]
    draw.text((W - tw - 20, H - th - 16), credit_txt, fill=MUTED, font=FONT_CREDIT)

    return np.array(img)

# Render
mp4_written = False
try:
    writer = imageio.get_writer('what-we-thought-vs-what-changed-architecture.mp4', fps=FPS, codec='libx264', quality=8)
    for i in range(TOTAL_FRAMES):
        t = i / FPS
        frame = make_frame(t)
        writer.append_data(frame)
    writer.close()
    mp4_written = True
except Exception as e:
    # Fallback GIF
    imageio.mimsave('what-we-thought-vs-what-changed-architecture.gif',
                    [make_frame(i/FPS) for i in range(TOTAL_FRAMES)], fps=12)
print('Created:', 'MP4' if mp4_written else 'GIF')
