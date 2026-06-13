from io import BytesIO

from PIL import Image, ImageDraw, ImageFilter, ImageFont

WIDTH, HEIGHT = 900, 260
BG = (18, 16, 20)
PANEL = (26, 23, 29)
ACCENT = (255, 107, 53)
TRACK = (45, 41, 50)
TEXT = (240, 236, 230)
MUTED = (143, 138, 148)

FONT_CANDIDATES = ("seguibl.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf")


def _font(size):
    for name in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def build_rank_card(username, avatar_bytes, level, xp, xp_needed, rank):
    card = Image.new("RGB", (WIDTH, HEIGHT), BG)

    glow = Image.new("RGB", (WIDTH, HEIGHT), BG)
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((WIDTH - 320, -120, WIDTH + 120, 220), fill=(64, 34, 22))
    glow = glow.filter(ImageFilter.GaussianBlur(70))
    card = Image.blend(card, glow, 0.5)

    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle((20, 20, WIDTH - 20, HEIGHT - 20), radius=26, outline=(58, 52, 64), width=2)

    avatar = Image.open(BytesIO(avatar_bytes)).convert("RGB").resize((150, 150))
    mask = Image.new("L", (150, 150), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 150, 150), fill=255)
    card.paste(avatar, (52, 55), mask)
    draw.ellipse((48, 51, 206, 209), outline=ACCENT, width=4)

    name_font = _font(42)
    label_font = _font(22)
    big_font = _font(34)

    shown = username if len(username) <= 18 else username[:17] + "…"
    draw.text((240, 62), shown, font=name_font, fill=TEXT)
    draw.text((240, 122), f"Rank #{rank}", font=label_font, fill=MUTED)

    level_text = f"LVL {level}"
    lw = draw.textlength(level_text, font=big_font)
    draw.text((WIDTH - 60 - lw, 56), level_text, font=big_font, fill=ACCENT)

    bar_x, bar_y, bar_w, bar_h = 240, 170, WIDTH - 300, 30
    draw.rounded_rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), radius=15, fill=TRACK)
    progress = max(0.04, min(1.0, xp / xp_needed if xp_needed else 1.0))
    draw.rounded_rectangle(
        (bar_x, bar_y, bar_x + int(bar_w * progress), bar_y + bar_h), radius=15, fill=ACCENT
    )
    draw.text((bar_x, bar_y + 40), f"{xp:,} / {xp_needed:,} XP", font=label_font, fill=MUTED)

    buffer = BytesIO()
    card.save(buffer, "PNG")
    buffer.seek(0)
    return buffer
