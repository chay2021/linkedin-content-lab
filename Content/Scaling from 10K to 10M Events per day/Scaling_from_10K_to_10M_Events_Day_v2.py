
# v4.1 Fixes requested by Chaitanya
# 1) Remove duplicate faded boxes in the first AFTER appearance (transition scene) — only show the good AFTER pipeline.
# 2) Tighten animations & text alignment to match the earlier source version, while preserving your font choices & offsets.

from PIL import Image, ImageDraw, ImageFont
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

# Fonts (preserve your choices)
try:
    FONT_TITLE = ImageFont.truetype("DejaVuSans-Bold.ttf", 31)
    FONT_SUB = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
    FONT_SMALL = ImageFont.truetype("DejaVuSans.ttf", 18)
    FONT_CREDIT = ImageFont.truetype("DejaVuSans.ttf", 18)
except:
    try:
        FONT_TITLE = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 31)
        FONT_SUB = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
        FONT_SMALL = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
        FONT_CREDIT = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
    except:
        FONT_TITLE = ImageFont.load_default()
        FONT_SUB = ImageFont.load_default()
        FONT_SMALL = ImageFont.load_default()
        FONT_CREDIT = ImageFont.load_default()

# Scene text vertical offsets (preserve)
SCENE_Y = 160
STATUS_Y = 200
TAGLINE_Y = 240

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
    c = tuple(max(0, min(255, int(color[i]*pulse))) for i in range(3))
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
        state["es_meter"] = lerp(0.3, 0.95, prog)
        state["gc_pause"] = lerp(5, 180, prog)  # ms
        state["retry_rate"] = lerp(0.0, 0.18, prog)  # fraction
        state["dash_stale"] = True
        state["dash_delay"] = int(lerp(0, 45, prog))
        state["status"] = ("ERROR", "Spike without buffer — ES throttles; retries cascade.")
    return state

def after_state(name, t_rel, dur):
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

# Per-component detailed drawing — simplified & aligned like source version
def draw_kafka_partitions(draw, xy, part_fill, part_hot):
    x, y, w, h = xy
    n = max(1, len(part_fill))
    pad = 12
    pw_total = w - 2*pad
    gap = 6
    slot = (pw_total - (n-1)*gap) / n
    py = y + 60
    ph = 20
    for i, fill in enumerate(part_fill):
        px = x + pad + i*(slot + gap)
        fw = int(slot * max(0.02, min(1.0, fill)))
        draw.rounded_rectangle([px, py, px+slot, py+ph], radius=6, fill=(21,34,68), outline=(57,74,122), width=2)
        if fw > 0:
            fill_color = BLUE if not (part_hot and i < len(part_hot) and part_hot[i]) else ERR
            draw.rounded_rectangle([px, py, px+fw, py+ph], radius=6, fill=fill_color)
        if part_hot and i < len(part_hot) and part_hot[i]:
            draw.rounded_rectangle([px-2, py-2, px+slot+2, py+ph+2], radius=8, outline=ERR, width=2)

def draw_consumers(draw, xy, cons_state, cons_bar):
    x, y, w, h = xy
    cols = len(cons_state)
    pad = 12
    gap = 6
    slot_w = (w - 2*pad - (cols-1)*gap) / cols
    slot_h = 44
    by = y + 58
    for i in range(cols):
        sx = int(x + pad + i*(slot_w + gap))
        sy = int(by)
        sw = int(slot_w)
        sh = slot_h
        # consumer tile
        outline = OUTLINE
        if cons_state[i] == "wait": outline = WARN
        elif cons_state[i] == "block": outline = ERR
        draw.rounded_rectangle([sx, sy, sx+sw, sy+sh], radius=6, fill=(20,32,60), outline=outline, width=2)
        # progress bar
        barw = int(sw * max(0.0, min(1.0, cons_bar[i])))
        bar_y = sy + sh - 12
        draw.rounded_rectangle([sx+4, bar_y, sx+4+barw, bar_y+5], radius=3,
                               fill=(PURPLE if cons_state[i]=="steady" else (AMBER if cons_state[i]=="wait" else ERR)))

# Frame builder
def make_frame(time_s):
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
    draw.text((40, 105), "Scaling observability pipelines", fill=MUTED, font=FONT_SUB)

    # Pulse for arrows
    p = 0.8 + 0.2*math.sin(2*math.pi*time_s)

    if mode == "title":
        draw.text((40, 160), "Before: App → Logstash → Elasticsearch → Dashboards", fill=TEXT, font=FONT_SUB)
        draw.text((40, 210), "After:   App → Kafka → Consumers → Elasticsearch → Dashboards", fill=TEXT, font=FONT_SUB)
        draw.text((40, SCENE_Y), "Scaling exposes assumptions. Search engines are not buffers.", fill=MUTED, font=FONT_SMALL)

    elif mode == "before":
        draw_box(draw, layout_before["app"], "App", accent=TEAL)
        draw_box(draw, layout_before["logstash"], "Logstash", accent=BLUE)
        draw_box(draw, layout_before["es"], "Elasticsearch", accent=AMBER)
        draw_box(draw, layout_before["dash"], "Dashboards", accent=CYAN)
        ax, ay, aw, ah = layout_before["app"]
        lx, ly, lw, lh = layout_before["logstash"]
        ex, ey, ew, eh = layout_before["es"]
        dx, dy, dw, dh = layout_before["dash"]
        draw_arrow(draw, ax+aw, ay+ah//2, lx, ly+lh//2, OUTLINE, p)
        draw_arrow(draw, lx+lw, ly+lh//2, ex, ey+eh//2, OUTLINE, p)
        # ES → Dashboards (curved)
        p0 = (ex + ew//2, ey + eh + 8)
        p2 = (dx + dw//2, dy - 8)
        ctrl = (max(ex, dx) + abs(dx - ex)//2 + 60, (p0[1] + p2[1])//2)
        draw_curve_arrow(draw, p0, ctrl, p2, color=OUTLINE, width=7)
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
        # Dashboards tiles
        tx = layout_before["dash"][0] + 12
        ty = layout_before["dash"][1] + 52
        tw = (layout_before["dash"][2] - 20 - 2*8)//3
        for i in range(3):
            draw.rounded_rectangle([tx + i*(tw+8), ty, tx + i*(tw+8) + tw, ty+22], radius=6,
                                   fill=(15,26,51), outline=(OUTLINE if not state["dash_stale"] else WARN), width=2)
        draw.text((layout_before["dash"][0]+12, layout_before["dash"][1]+28), f"Delay: {int(state['dash_delay'])}s", fill=MUTED, font=FONT_SMALL)
        # Extra signals
        draw.text((lx+12, ly+50), f"GC pause: {int(state['gc_pause'])}ms", fill=MUTED, font=FONT_SMALL)
        draw.text((lx+120, ly+90), f"Retry rate: {int(state['retry_rate']*100)}%", fill=MUTED, font=FONT_SMALL)
        sev, msg = state["status"]
        color = TEAL if sev == "STEADY" else (WARN if sev == "WARN" else ERR)
        draw.text((40, SCENE_Y), f"Scene: {name}", fill=TEXT, font=FONT_SUB)
        draw.text((40, STATUS_Y), f"Status: {sev} — {msg}", fill=color, font=FONT_SUB)
        draw.text((40, TAGLINE_Y), "Search engines are not buffers.", fill=MUTED, font=FONT_SMALL)

    elif mode == "transition":
        # FIX: show ONLY the AFTER pipeline (no faded BEFORE boxes)
        # Boxes
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
        # ES → Dashboards curved
        p0 = (xE + wE//2, yE + hE + 8)
        p2 = (xD + wD//2, yD - 8)
        ctrl = (max(xE, xD) + abs(xD - xE)//2 + 80, (p0[1] + p2[1])//2)
        draw_curve_arrow(draw, p0, ctrl, p2, color=OUTLINE, width=7)
        # Copy
        draw.text((40, SCENE_Y), "The shift that saves systems:", fill=TEXT, font=FONT_SUB)
        draw.text((40, STATUS_Y), "Insert a durable queue (Kafka) to absorb spikes.", fill=MUTED, font=FONT_SMALL)
        draw.text((40, TAGLINE_Y), "Let Elasticsearch focus on search. Failures stop cascading.", fill=MUTED, font=FONT_SMALL)

    elif mode == "after":
        state = after_state(name, t_rel, dur)
        draw_box(draw, layout_after["source"], "App", accent=TEAL)
        draw_box(draw, layout_after["kafka"], "Kafka Topic", accent=BLUE)
        draw_kafka_partitions(draw, layout_after["kafka"], state.get("part_fill", [0.1]*6), state.get("part_hot", [False]*6))
        draw_box(draw, layout_after["consumers"], "Consumers (6)", accent=PURPLE)
        draw_consumers(draw, layout_after["consumers"], state.get("cons_state", ["steady"]*6), state.get("cons_bar", [0.25]*6))
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
        # Badges aligned to boxes
        draw.text((xS+12, yS+58), f"events/sec: {state['src_rate']:,}", fill=MUTED, font=FONT_SMALL)
        # ES meter
        meter_w = layout_after["es"][2] - 20
        mx = xE + 12; my = yE + 70
        draw.rounded_rectangle([mx, my, mx+meter_w, my+14], radius=6, fill=(26,40,73), outline=(57,74,122), width=2)
        meter_fill = int(meter_w * state["es_meter"]) if state["es_meter"] else 0
        draw.rounded_rectangle([mx, my, mx+meter_fill, my+14], radius=6, fill=AMBER)
        if state["es_meter"] and state["es_meter"] > 0.85:
            draw.rounded_rectangle([xE, yE, xE+wE, yE+hE], radius=16, outline=ERR, width=3)
        draw.text((xE+12, yE+94), f"Indexing latency: {int(40 + 80*state['es_meter'])}ms", fill=MUTED, font=FONT_SMALL)
        # Dashboards small tiles
        tg = 8
        tw = (wD - 20 - 2*tg)//3
        ty = yD + 52
        for i in range(3):
            tx = xD + 12 + i*(tw + tg)
            outline = OUTLINE if not state["dash_stale"] else WARN
            draw.rounded_rectangle([tx, ty, tx+tw, ty+22], radius=6, fill=(15,26,51), outline=outline, width=2)
        draw.text((xD+12, yD+28), f"Delay: {int(state['dash_delay'])}s", fill=MUTED, font=FONT_SMALL)
        # Lag text (Kafka bottom-right)
        draw.text((xK+wK-210, yK+hK-28), f"Total lag: {state['lag']:,}", fill=MUTED, font=FONT_SMALL)
        # Status ribbons
        sev, msg = state["status"]
        color = TEAL if sev == "STEADY" else (WARN if sev == "WARN" else ERR)
        draw.text((40, SCENE_Y), f"Scene: {name}", fill=TEXT, font=FONT_SUB)
        draw.text((40, STATUS_Y), f"Status: {sev} — {msg}", fill=color, font=FONT_SUB)
        draw.text((40, TAGLINE_Y), "Backpressure keeps systems predictable.", fill=MUTED, font=FONT_SMALL)

    elif mode == "obs":
        state = after_state(name, t_rel, dur)
        draw_box(draw, layout_after["kafka"], "Kafka Topic", accent=BLUE)
        draw_kafka_partitions(draw, layout_after["kafka"], state.get("part_fill", [0.1]*6), state.get("part_hot", [False]*6))
        draw_box(draw, layout_after["consumers"], "Consumers (6)", accent=PURPLE)
        draw_consumers(draw, layout_after["consumers"], state.get("cons_state", ["steady"]*6), state.get("cons_bar", [0.25]*6))
        draw_box(draw, layout_after["es"], "Elasticsearch", accent=AMBER)
        draw.text((40, SCENE_Y), "Observability beats raw throughput:", fill=TEXT, font=FONT_SUB)
        draw.text((40, STATUS_Y), "Consumer lag • Ingestion vs indexing • Queue depth • P95/P99 latencies", fill=MUTED, font=FONT_SMALL)
        draw.text((40, TAGLINE_Y), "Dashboards become survival tools.", fill=MUTED, font=FONT_SMALL)

    else:  # closing
        msg_top = "Scaling isn't about bigger machines or more threads."
        msg_mid = "Design for failure: buffer ingestion, apply backpressure, handle retries idempotently."
        msg_bot = "At 10K/day the happy path dominates; at 10M/day, the failure path is the system."
        draw.text((40, SCENE_Y), msg_top, fill=TEXT, font=FONT_SUB)
        draw.text((40, STATUS_Y), msg_mid, fill=MUTED, font=FONT_SMALL)
        draw.text((40, TAGLINE_Y), msg_bot, fill=MUTED, font=FONT_SMALL)

    # Credits
    credit_txt = "Credits: Chaitanya Pothuraju"
    bbox = draw.textbbox((0,0), credit_txt, font=FONT_CREDIT)
    tw = bbox[2] - bbox[0]; th = bbox[3] - bbox[1]
    draw.text((W - tw - 20, H - th - 16), credit_txt, fill=MUTED, font=FONT_CREDIT)

    return np.array(img)

# Render
mp4_written = False
try:
    writer = imageio.get_writer('what-we-thought-vs-what-changed-architecture-fixed.mp4', fps=FPS, codec='libx264', quality=8)
    for i in range(TOTAL_FRAMES):
        t = i / FPS
        frame = make_frame(t)
        writer.append_data(frame)
    writer.close()
    mp4_written = True
except Exception:
    imageio.mimsave('what-we-thought-vs-what-changed-architecture-fixed.gif',
                    [make_frame(i/FPS) for i in range(TOTAL_FRAMES)], fps=12)
print('Created:', 'MP4' if mp4_written else 'GIF')
