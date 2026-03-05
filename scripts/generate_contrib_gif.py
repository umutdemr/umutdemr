import os
import math
import datetime as dt
import requests
from PIL import Image, ImageDraw, ImageFont

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
USER = os.environ.get("GITHUB_USERNAME", "umutdemr")
DISPLAY_NAME = os.environ.get("DISPLAY_NAME", "Umut Can Demir")
ROLE_LINE = os.environ.get("ROLE_LINE", "Frontend Developer")
TAGLINE = os.environ.get("TAGLINE", "React • TypeScript • Next.js • Testing")

API = "https://api.github.com/graphql"
HEADERS = {"Authorization": f"bearer {GITHUB_TOKEN}"}

def gql(query: str, variables: dict):
    r = requests.post(API, json={"query": query, "variables": variables}, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]

def iso(d: dt.date) -> str:
    return dt.datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=dt.timezone.utc).isoformat()

def get_created_at() -> dt.date:
    q = """
    query($login:String!){
      user(login:$login){ createdAt }
    }
    """
    data = gql(q, {"login": USER})
    created_at = data["user"]["createdAt"]
    return dt.datetime.fromisoformat(created_at.replace("Z", "+00:00")).date()

def get_total_contrib(from_date: dt.date, to_date: dt.date) -> int:
    q = """
    query($login:String!, $from:DateTime!, $to:DateTime!){
      user(login:$login){
        contributionsCollection(from:$from, to:$to){
          contributionCalendar{ totalContributions }
        }
      }
    }
    """
    data = gql(q, {"login": USER, "from": iso(from_date), "to": iso(to_date)})
    return int(data["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"])

def sum_all_time_contrib(created: dt.date, today: dt.date) -> int:
    total = 0
    y = created.year
    while y <= today.year:
        start = dt.date(y, 1, 1)
        end = dt.date(y + 1, 1, 1)
        if y == created.year:
            start = created
        if y == today.year:
            end = today + dt.timedelta(days=1)
        total += get_total_contrib(start, end)
        y += 1
    return total

def load_font(size: int, bold: bool = False):
    # Ubuntu runner'da genelde mevcut
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    path = candidates[1] if bold else candidates[0]
    try:
        return ImageFont.truetype(path, size=size)
    except Exception:
        return ImageFont.load_default()

def ease_out_cubic(t: float) -> float:
    return 1 - (1 - t) ** 3

def rounded_rect(draw: ImageDraw.ImageDraw, xy, r, fill):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=fill)

def make_frame(w: int, h: int, value: int, total: int, date_range: str, progress: float) -> Image.Image:
    img = Image.new("RGB", (w, h), (10, 14, 24))  # dark bg
    d = ImageDraw.Draw(img)

    # card
    pad = 18
    card = (pad, pad, w - pad, h - pad)
    rounded_rect(d, card, r=18, fill=(15, 23, 42))

    # subtle glow bar
    glow_w = int((w - 2 * pad) * (0.35 + 0.65 * progress))
    d.rectangle([pad, pad, pad + glow_w, pad + 3], fill=(255, 77, 141))

    # text
    f_name = load_font(26, bold=True)
    f_role = load_font(16, bold=False)
    f_tag = load_font(14, bold=False)
    f_label = load_font(14, bold=False)
    f_num = load_font(44, bold=True)
    f_small = load_font(13, bold=False)

    x = pad + 18
    y = pad + 18

    d.text((x, y), DISPLAY_NAME, font=f_name, fill=(230, 237, 243))
    d.text((x, y + 36), ROLE_LINE, font=f_role, fill=(255, 77, 141))
    d.text((x, y + 60), TAGLINE, font=f_tag, fill=(201, 209, 217))

    # right side number
    num_text = f"{value:,}"
    label = "Total Contributions"
    tw, th = d.textbbox((0, 0), num_text, font=f_num)[2:]
    lx, ly = w - pad - 18 - tw, y + 8
    d.text((lx, ly), num_text, font=f_num, fill=(255, 77, 141))
    lbw, lbh = d.textbbox((0, 0), label, font=f_label)[2:]
    d.text((w - pad - 18 - lbw, ly + 54), label, font=f_label, fill=(201, 209, 217))
    d.text((w - pad - 18 - d.textbbox((0, 0), date_range, font=f_small)[2],
            ly + 76),
           date_range,
           font=f_small,
           fill=(201, 209, 217))

    # progress bar
    bar_x0, bar_y0 = x, h - pad - 26
    bar_x1, bar_y1 = w - pad - 18, h - pad - 16
    d.rounded_rectangle([bar_x0, bar_y0, bar_x1, bar_y1], radius=6, fill=(9, 12, 20))
    fill_w = int((bar_x1 - bar_x0) * progress)
    d.rounded_rectangle([bar_x0, bar_y0, bar_x0 + fill_w, bar_y1], radius=6, fill=(255, 77, 141))

    return img

def main():
    os.makedirs("dist", exist_ok=True)

    created = get_created_at()
    today = dt.date.today()
    total = sum_all_time_contrib(created, today)

    date_range = f"{created.isoformat()} → {today.isoformat()}"

    # GIF frames: count up
    frames = []
    n_frames = 56
    for i in range(n_frames):
        t = i / (n_frames - 1)
        p = ease_out_cubic(t)
        val = int(round(total * p))
        frames.append(make_frame(900, 180, val, total, date_range, p))

    out = "dist/umutdemr-contrib-card.gif"
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=28,
        loop=0,
        optimize=True,
    )

    # Also export a static PNG
    frames[-1].save("dist/umutdemr-contrib-card.png", optimize=True)

    print(f"Generated: {out} (total={total})")

if __name__ == "__main__":
    main()
