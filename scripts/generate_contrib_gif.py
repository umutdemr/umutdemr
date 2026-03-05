import os
import math
import datetime as dt
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

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

def get_bucket(from_date: dt.date, to_date: dt.date) -> dict:
    q = """
    query($login:String!, $from:DateTime!, $to:DateTime!){
      user(login:$login){
        contributionsCollection(from:$from, to:$to){
          contributionCalendar{ totalContributions }
          totalCommitContributions
          totalIssueContributions
          totalPullRequestContributions
          totalPullRequestReviewContributions
        }
      }
    }
    """
    data = gql(q, {"login": USER, "from": iso(from_date), "to": iso(to_date)})
    cc = data["user"]["contributionsCollection"]
    return {
        "total": int(cc["contributionCalendar"]["totalContributions"]),
        "commits": int(cc["totalCommitContributions"]),
        "issues": int(cc["totalIssueContributions"]),
        "prs": int(cc["totalPullRequestContributions"]),
        "reviews": int(cc["totalPullRequestReviewContributions"]),
    }

def sum_all_time(created: dt.date, today: dt.date) -> dict:
    total = {"total": 0, "commits": 0, "issues": 0, "prs": 0, "reviews": 0}
    y = created.year
    while y <= today.year:
        start = dt.date(y, 1, 1)
        end = dt.date(y + 1, 1, 1)
        if y == created.year:
            start = created
        if y == today.year:
            end = today + dt.timedelta(days=1)
        b = get_bucket(start, end)
        for k in total:
            total[k] += b[k]
        y += 1
    return total

def load_font(size: int, bold: bool = False):
    # GitHub ubuntu runner'da genelde var
    regular = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    boldp = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    try:
        return ImageFont.truetype(boldp if bold else regular, size=size)
    except Exception:
        return ImageFont.load_default()

def ease_in_out(t: float) -> float:
    # smoothstep-ish
    return t * t * (3 - 2 * t)

def lerp(a, b, t):
    return int(a + (b - a) * t)

def lerp_rgb(c1, c2, t):
    return (lerp(c1[0], c2[0], t), lerp(c1[1], c2[1], t), lerp(c1[2], c2[2], t))

def make_vertical_gradient(w, h, top, bottom):
    img = Image.new("RGB", (w, h), top)
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        c = lerp_rgb(top, bottom, t)
        for x in range(w):
            px[x, y] = c
    return img

def rounded(draw, xy, r, fill):
    draw.rounded_rectangle(xy, radius=r, fill=fill)

def format_k(n: int) -> str:
    # 1250 -> 1.2k
    if n >= 1000:
        v = n / 1000.0
        if v < 10:
            return f"{v:.1f}k"
        return f"{v:.0f}k"
    return str(n)

def make_frame(w, h, name, role, tagline, totals: dict, val_total: int, p: float, shimmer_x: float) -> Image.Image:
    # gradient bg
    bg = make_vertical_gradient(w, h, top=(8, 12, 24), bottom=(22, 10, 38))

    # add soft diagonal glow
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([-200, -120, 520, 520], fill=(255, 77, 141, 80))
    gd.ellipse([w-520, h-420, w+200, h+200], fill=(96, 165, 250, 70))
    glow = glow.filter(ImageFilter.GaussianBlur(18))
    bg = Image.alpha_composite(bg.convert("RGBA"), glow).convert("RGB")

    d = ImageDraw.Draw(bg)

    pad = 18
    card = (pad, pad, w - pad, h - pad)
    rounded(d, card, r=18, fill=(14, 20, 36))

    # top gradient strip
    strip_h = 5
    strip = Image.new("RGB", (w - 2 * pad, strip_h), (0, 0, 0))
    spx = strip.load()
    for x in range(strip.width):
        t = x / max(1, strip.width - 1)
        c = lerp_rgb((255, 77, 141), (96, 165, 250), t)
        for y in range(strip_h):
            spx[x, y] = c
    bg.paste(strip, (pad, pad))

    # shimmer highlight
    shimmer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shimmer)
    # thin angled rectangle
    x0 = int(shimmer_x) - 120
    sd.polygon([(x0, pad+8), (x0+70, pad+8), (x0+190, h-pad-8), (x0+120, h-pad-8)],
               fill=(255, 255, 255, 24))
    shimmer = shimmer.filter(ImageFilter.GaussianBlur(10))
    bg = Image.alpha_composite(bg.convert("RGBA"), shimmer).convert("RGB")
    d = ImageDraw.Draw(bg)

    # fonts
    f_name = load_font(26, bold=True)
    f_role = load_font(16, bold=False)
    f_tag = load_font(14, bold=False)
    f_big = load_font(46, bold=True)
    f_lbl = load_font(14, bold=False)
    f_metric = load_font(14, bold=True)

    x = pad + 18
    y = pad + 16

    # left texts
    d.text((x, y), name, font=f_name, fill=(230, 237, 243))
    d.text((x, y + 36), role, font=f_role, fill=(255, 77, 141))
    d.text((x, y + 60), tagline, font=f_tag, fill=(201, 209, 217))

    # right big total (animated)
    total_text = f"{val_total:,}"
    tw = d.textbbox((0, 0), total_text, font=f_big)[2]
    tx = w - pad - 18 - tw
    ty = y + 2

    # gradient-ish big number (fake by drawing twice)
    d.text((tx, ty), total_text, font=f_big, fill=(255, 77, 141))
    d.text((tx+1, ty+1), total_text, font=f_big, fill=(96, 165, 250))

    label = "All-time Contributions"
    lbw = d.textbbox((0, 0), label, font=f_lbl)[2]
    d.text((w - pad - 18 - lbw, ty + 56), label, font=f_lbl, fill=(201, 209, 217))

    # metrics row (commits/prs/issues/reviews)
    metrics = [
        ("Commits", totals["commits"]),
        ("PRs", totals["prs"]),
        ("Issues", totals["issues"]),
        ("Reviews", totals["reviews"]),
    ]

    row_y = h - pad - 44
    # separator line
    d.line([(x, row_y - 10), (w - pad - 18, row_y - 10)], fill=(34, 46, 68), width=1)

    # draw chips
    cx = x
    for (k, v) in metrics:
        text = f"{k}: {format_k(v)}"
        bb = d.textbbox((0, 0), text, font=f_metric)
        chip_w = (bb[2] - bb[0]) + 18
        chip_h = 26
        rounded(d, (cx, row_y, cx + chip_w, row_y + chip_h), r=10, fill=(9, 12, 20))
        # tiny gradient dot
        d.ellipse([cx + 8, row_y + 10, cx + 14, row_y + 16], fill=(255, 77, 141))
        d.text((cx + 18, row_y + 5), text, font=f_metric, fill=(201, 209, 217))
        cx += chip_w + 10

    # subtle bottom progress (purely aesthetic)
    bar_x0, bar_y0 = x, h - pad - 16
    bar_x1, bar_y1 = w - pad - 18, h - pad - 10
    d.rounded_rectangle([bar_x0, bar_y0, bar_x1, bar_y1], radius=6, fill=(9, 12, 20))
    fill_w = int((bar_x1 - bar_x0) * p)
    # bar gradient
    for i in range(max(1, fill_w)):
        t = i / max(1, fill_w - 1)
        c = lerp_rgb((255, 77, 141), (96, 165, 250), t)
        d.line([(bar_x0 + i, bar_y0), (bar_x0 + i, bar_y1)], fill=c, width=1)

    return bg

def main():
    os.makedirs("dist", exist_ok=True)

    created = get_created_at()
    today = dt.date.today()
    totals = sum_all_time(created, today)

    # animation settings (slower + smoother)
    n_frames = 110            # daha fazla frame
    duration_ms = 42          # frame başına süre (toplam ~4.6s)
    frames = []

    for i in range(n_frames):
        t = i / (n_frames - 1)
        p = ease_in_out(t)
        # extra slow-start feel
        p2 = p ** 1.15
        val_total = int(round(totals["total"] * p2))
        shimmer_x = (t * 1.25 - 0.15) * 900  # shimmer sweep
        frames.append(
            make_frame(
                w=900,
                h=220,
                name=DISPLAY_NAME,
                role=ROLE_LINE,
                tagline=TAGLINE,
                totals=totals,
                val_total=val_total,
                p=p,
                shimmer_x=shimmer_x,
            )
        )

    out_gif = "dist/umutdemr-contrib-card.gif"
    frames[0].save(
        out_gif,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
        optimize=True,
        disposal=2,
    )

    # static png final frame
    frames[-1].save("dist/umutdemr-contrib-card.png", optimize=True)

    print(f"Generated: {out_gif} totals={totals}")

if __name__ == "__main__":
    main()
