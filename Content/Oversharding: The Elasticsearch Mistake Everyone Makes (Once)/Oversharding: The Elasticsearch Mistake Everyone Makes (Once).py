import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from moviepy import (
    TextClip, CompositeVideoClip, ColorClip, ImageClip, concatenate_videoclips
)

W, H = 1280, 720
BG_COLOR = (255, 255, 255)

def pick_font(bold=False):
    candidates = []
    if bold:
        candidates += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
            "/System/Library/Fonts/Supplemental/Helvetica Bold.ttf",
            "/Library/Fonts/Helvetica Bold.ttf",
        ]
    candidates += [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttf",
        "/Library/Fonts/Helvetica.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    return None

FONT_BOLD = pick_font(bold=True)
FONT_REGULAR = pick_font(bold=False)

def pick_emoji_font():
    candidates = [
        "/System/Library/Fonts/Apple Color Emoji.ttc",
        "/System/Library/Fonts/Apple Color Emoji.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    return None

FONT_EMOJI = pick_emoji_font()

def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) * (1 - t)

def animated_y(base_y, t, start=0.0, travel=28, dur=0.6):
    if t <= start:
        return base_y + travel
    if t >= start + dur:
        return base_y
    k = ease_out((t - start) / dur)
    return base_y + travel * (1 - k)

def bob_y(base_y, t, amp=6, speed=3.5):
    return base_y + amp * math.sin(t * speed)

def load_font(font_path, font_size):
    if not font_path:
        return ImageFont.load_default()
    try:
        return ImageFont.truetype(font_path, font_size)
    except OSError:
        if font_path.endswith(".ttc"):
            try:
                return ImageFont.truetype(font_path, font_size, index=0)
            except OSError:
                pass
        for alt_size in (64, 56, 48):
            try:
                return ImageFont.truetype(font_path, alt_size)
            except OSError:
                continue
    return ImageFont.load_default()

def render_text_image(text, font_path, font_size, color, pad=8):
    font = load_font(font_path, font_size)

    dummy = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    draw = ImageDraw.Draw(dummy)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    img = Image.new("RGBA", (text_w + pad * 2, text_h + pad * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.text((pad, pad), text, font=font, fill=color)
    return np.array(img)

def slide(
    text,
    subtext=None,
    duration=4,
    color="#111111",
    sub_color="#555555",
    emoji=None,
    emoji_color="#111111",
    effect=None,
):
    clips = []

    bg = ColorClip(size=(W, H), color=BG_COLOR, duration=duration)
    clips.append(bg)

    main = TextClip(
        text=text,
        font=FONT_BOLD,
        font_size=74,
        color=color,
        method="caption",
        size=(W - 220, None),
        margin=(12, 12),
        text_align="center",
    ).with_position(
        lambda t: ("center", animated_y(H * 0.40, t, start=0.0, travel=36, dur=0.7))
    ).with_duration(duration)

    clips.append(main)

    if subtext:
        sub = TextClip(
            text=subtext,
            font=FONT_REGULAR,
            font_size=34,
            color=sub_color,
            method="caption",
            size=(W - 260, None),
            margin=(10, 10),
            text_align="center",
        ).with_position(
            lambda t: ("center", animated_y(H * 0.62, t, start=0.2, travel=26, dur=0.7))
        ).with_start(0.2).with_duration(duration - 0.2)
        clips.append(sub)

    if emoji:
        emoji_img = render_text_image(
            emoji,
            FONT_EMOJI or FONT_BOLD or FONT_REGULAR,
            72,
            emoji_color,
            pad=10,
        )
        emoji_clip = ImageClip(emoji_img)
        if effect == "bounce":
            emoji_clip = emoji_clip.with_position(
                lambda t: (W * 0.15, animated_y(H * 0.20, t, start=0.1, travel=18, dur=0.5))
            )
        elif effect == "pulse":
            emoji_clip = emoji_clip.with_position(
                lambda t: (W * 0.12, bob_y(H * 0.18, t, amp=10, speed=5.0))
            )
        else:
            emoji_clip = emoji_clip.with_position((W * 0.12, H * 0.18))
        emoji_clip = emoji_clip.with_duration(duration)
        clips.append(emoji_clip)

    if effect == "flash":
        flash = ColorClip(size=(W, H), color=(255, 255, 255), duration=0.2)
        flash = flash.with_opacity(0.22)
        flash = flash.with_start(0.05)
        clips.append(flash)

    if effect == "glow":
        glow = ColorClip(size=(W, H), color=(255, 255, 255), duration=duration)
        glow = glow.with_opacity(0.08)
        clips.append(glow)

    copyright_img = render_text_image(
        "Copyright © Chaitanya Pothuraju",
        FONT_REGULAR,
        20,
        "#777777",
        pad=6,
    )
    copyright_clip = ImageClip(copyright_img).with_duration(duration)
    copyright_clip = copyright_clip.with_position(
        (W - copyright_clip.w - 20, H - copyright_clip.h - 16)
    )
    clips.append(copyright_clip)

    return CompositeVideoClip(clips)

slides = [
    slide(
        "OVERSHARDING",
        "The Elasticsearch mistake everyone makes (once)",
        4,
        color="#0A3D62",
        emoji="⚠️",
        emoji_color="#F4B400",
        effect="glow",
    ),
    slide(
        "“We need more shards to scale”",
        "More shards = more parallelism",
        4,
        color="#1E6091",
        emoji="🚀",
        emoji_color="#2E86C1",
        effect="bounce",
    ),
    slide(
        "1 index × 20 shards × 30 days",
        "= 600 Lucene indexes",
        5,
        color="#B45309",
        emoji="🧱",
        emoji_color="#8D5524",
        effect="pulse",
    ),
    slide(
        "More shards ≠ more throughput",
        "More shards = more overhead",
        5,
        color="#C1121F",
        emoji="🔥",
        emoji_color="#E63946",
        effect="flash",
    ),
    slide(
        "Elasticsearch spends more time\nmanaging shards\nthan indexing data",
        duration=5,
        color="#6C5CE7",
        emoji="⏱️",
        emoji_color="#6C5CE7",
        effect="pulse",
    ),
    slide(
        "TARGET 20–50 GB PER SHARD",
        "Fewer shards win",
        4,
        color="#2A9D8F",
        emoji="✅",
        emoji_color="#2E7D32",
        effect="glow",
    ),
]

final = concatenate_videoclips(slides, method="compose")
final.write_videofile(
    "elasticsearch_oversharding_explainer.mp4",
    fps=24,
    codec="libx264",
    audio=False
)
