#!/usr/bin/env python3
"""GreenFlag companion website (V2, Figma mockup) - static site generator.

Usage:
    python3 build.py                                  # build the site into dist/

Content lives in content/tiles.json. Styles live in assets/style.css,
images in assets/img/, icons in assets/icons/, fonts in assets/fonts/.
Only the Python standard library is needed.
"""
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
SITE_NAME = "GreenFlag"

e = html.escape


# ---------------------------------------------------------------- helpers

def icon(name, cls="icon"):
    """Inline an SVG icon from assets/icons (they use currentColor)."""
    svg = (ROOT / "assets" / "icons" / f"{name}.svg").read_text(encoding="utf-8").strip()
    svg = re.sub(r'\s(width|height)="\d+"', "", svg, count=2)
    return svg.replace("<svg ", f'<svg class="{cls}" aria-hidden="true" focusable="false" ', 1)


def img(prefix, path, w, h, alt="", cls="", eager=False):
    """<img> with its @2x version for Retina screens."""
    base = f"{prefix}assets/img/{path}"
    retina = base.replace(".png", "@2x.png")
    loading = "" if eager else ' loading="lazy"'
    c = f' class="{cls}"' if cls else ""
    return (f'<img{c} src="{base}" srcset="{base} 1x, {retina} 2x" width="{w}" height="{h}" '
            f'alt="{e(alt)}" decoding="async"{loading}>')


def label(text, tag="h2", cls=""):
    """Yellow, slightly tilted title bubble used all over the mockup."""
    return f'<{tag} class="label {cls}">{text}</{tag}>'


TABS = [
    ("home", "Home", "index.html", "tab-home"),
    ("contents", "Contents", "contents.html", "tab-contents"),
    ("rules", "Rules", "rules.html", "tab-rules"),
    ("about", "About", "about.html", "tab-about"),
]


def page(title, hero, body, depth=0, tab=None):
    prefix = "../" * depth
    links = []
    for key, name, href, ic in TABS:
        current = ' aria-current="page"' if key == tab else ""
        links.append(f'<a href="{prefix}{href}"{current}>{icon(ic)}<span>{name}</span></a>')
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#2D4A1C">
<meta name="description" content="GreenFlag: a board game about Green IT and eco-design. Detailed explanations of every tile.">
<title>{e(title)} | {SITE_NAME}</title>
<link rel="preload" href="{prefix}assets/fonts/fredoka.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="{prefix}assets/fonts/nunito.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{prefix}assets/style.css">
<link rel="icon" href="{prefix}assets/img/logo/favicon.png" type="image/png">
<link rel="apple-touch-icon" href="{prefix}assets/img/logo/favicon@2x.png">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
{hero}
<main id="main">
{body}
</main>
<nav class="tabbar" aria-label="Main menu">{''.join(links)}</nav>
</body>
</html>
"""


def illustrated_hero(prefix, illustration, size, alt):
    w, h = size
    return (f'<header class="hero hero-illustrated">'
            f'{img(prefix, "heroes/" + illustration, w, h, alt=alt, cls="hero-illustration", eager=True)}</header>')


# ---------------------------------------------------------------- tiles

TYPE_LABEL = {"good": "Good practice", "bad": "Bad practice", "finish": "Finish"}


def pill(t, with_type=False, cls=""):
    """Effect badge, written like on the board (Kalam)."""
    parts = []
    if with_type or not t.get("effect"):
        parts.append(TYPE_LABEL[t["type"]])
    if t.get("effect"):
        parts.append(t["effect"])
    return f'<span class="pill pill-{t["type"]} {cls}">{" &middot; ".join(e(p) for p in parts)}</span>'


def tile_label(t):
    return f"Tile {t['tile']}" if t.get("tile") else "Go further"


def render_section(s):
    out = [label(e(s["heading"])), '<div class="card">']
    if "text" in s:
        out.append(f"<p>{e(s['text'])}</p>")
    if "facts" in s:
        out.append('<ul class="dots">' + "".join(f"<li>{e(f['text'])}</li>" for f in s["facts"]) + "</ul>")
    if "list" in s:
        out.append('<ul class="dots">' + "".join(f"<li>{e(i)}</li>" for i in s["list"]) + "</ul>")
    out.append("</div>")
    return "\n".join(out)


def tile_page(t, by_id, prev=None, nxt=None):
    related = [by_id[r] for r in t.get("related", []) if r in by_id]
    rel_html = ""
    if related:
        rel_html = label("Related tiles") + '<ul class="related">' + "".join(
            f'<li><a class="related-card related-{r["type"]}" href="{r["id"]}.html">'
            f'<span class="related-text"><span class="related-title">{e(r["title"])}</span>{pill(r, with_type=True)}</span>'
            f'<span class="round round-{r["type"]}">{icon("arrow-next")}</span></a></li>' for r in related
        ) + "</ul>"
    sources = "".join(
        f'<li><a href="{e(s["url"])}" rel="noopener">{e(s["label"])}</a></li>' for s in t.get("sources", [])
    )
    prev_html = ""
    if prev:
        prev_txt = f"&larr; {prev['tile']}" if prev.get("tile") else "&larr;"
        prev_html = (f'<a class="btn btn-outline btn-small" href="{prev["id"]}.html" '
                     f'aria-label="Previous: {e(prev["title"])}">{prev_txt}</a>')
    next_html = ""
    if nxt:
        next_txt = f"{nxt['tile']} &rarr;" if nxt.get("tile") else "Next &rarr;"
        next_html = (f'<a class="btn btn-dark" href="{nxt["id"]}.html" '
                     f'aria-label="Next: {e(nxt["title"])}">{next_txt}</a>')

    board = ""
    if t.get("board"):
        board = f'<p class="on-board">On the board:</p><p class="board-text">{e(t["board"])}</p>'
    hero = f"""<header class="hero hero-tile"><div class="hero-inner">
  <div class="hero-tile-top">
    <a class="back" href="../contents.html" aria-label="Back to contents">{icon("arrow-back")}</a>
    <span class="tile-chip">{tile_label(t)}</span>
  </div>
  {pill(t)}
  <h1>{e(t['title'])}</h1>
  {board}
</div></header>"""
    body = f"""
<article class="tile">
  <p class="intro">{e(t['intro'])}</p>
  {''.join(render_section(s) for s in t['sections'])}
  {rel_html}
  {label("Sources")}
  <ul class="card list-lines sources">{sources}</ul>
</article>
<nav class="tile-nav" aria-label="Tile navigation">
  {prev_html}
  <a class="btn btn-outline" href="../contents.html">Contents</a>
  {next_html}
</nav>
"""
    return page(t["title"], hero, body, depth=1, tab="contents")


def tile_card(t):
    return f"""<li>
  <a class="tile-card tile-card-{t['type']}" href="tiles/{t['id']}.html">
    <span class="tile-card-top">
      <span class="num"><span class="sr">Tile </span>{t['tile']}</span>
      <span class="round round-{t['type']}">{icon("arrow-next")}</span>
    </span>
    <span class="tile-card-board">{e(t.get("board") or "")}</span>
    <span class="tile-card-title">{e(t['title'])}</span>
  </a>
</li>"""


def further_row(t):
    return f"""<li>
  <a class="further-row" href="tiles/{t['id']}.html">
    <span class="further-text"><span class="further-title">{e(t['title'])}</span>{e(t['intro'])}</span>
    <span class="round round-white">{icon("arrow-next")}</span>
  </a>
</li>"""


# ---------------------------------------------------------------- pages

def home_page():
    p = ""
    hero = illustrated_hero(p, "hero-home-illustration.png", (390, 367), "")
    body = f"""
<section class="home-intro">
  <h1><span class="home-kicker">A board game about</span> <span class="label label-big">Green IT &amp; eco-design.</span></h1>
  <p>Roll the dice, move along 30 tiles and discover the environmental impact of digital technology.</p>
</section>
<section class="bento" aria-label="Discover the game">
  <a class="bento-block bento-good" href="contents.html#board">
    <span class="bento-title">Good practices help you move forward,</span>
    {img(p, "home-bento/home-bento-good-practices.png", 165, 180)}
  </a>
  <a class="bento-block bento-bad" href="contents.html#board">
    <span class="bento-title">bad practices slow you down.</span>
    {img(p, "home-bento/home-bento-bad-practices.png", 165, 180)}
  </a>
  <a class="bento-block bento-finish" href="tiles/net-zero.html">
    <span class="bento-title">First to reach Net zero wins!</span>
    {img(p, "home-bento/home-bento-net-zero.png", 165, 160)}
  </a>
  <a class="bento-block bento-rules" href="rules.html">
    <span class="bento-title">How to play {icon("arrow-next")}</span>
    {img(p, "home-bento/home-bento-how-to-play.png", 165, 160)}
  </a>
</section>
<p class="center"><a class="btn btn-dark btn-wide" href="contents.html">Start a game</a></p>
"""
    return page("Home", hero, body, tab="home")


def index_page(tiles):
    board = sorted([t for t in tiles if t.get("tile")], key=lambda t: t["tile"])
    extra = [t for t in tiles if not t.get("tile")]
    # Two independent columns, like the mockup: 1st, 3rd, 5th... tiles on the left.
    left = "".join(tile_card(t) for t in board[0::2])
    right = "".join(tile_card(t) for t in board[1::2])
    hero = illustrated_hero("", "hero-contents-illustration.png", (390, 250), "")
    body = f"""
<div class="page-head">
  {label("Contents", "h1", "label-big")}
  <p>Landed on a coloured tile? Find its number below, check its effect and open it to read the detailed explanation.</p>
</div>
<h2 class="split-title" id="board">The board, <span class="label">tile by tile</span></h2>
<div class="tile-grid">
  <ol class="tile-col">{left}</ol>
  <ol class="tile-col">{right}</ol>
</div>
<div class="center" id="go-further">{label("Go further")}</div>
<ul class="further card-pale">{''.join(further_row(t) for t in extra)}</ul>
"""
    return page("Contents", hero, body, tab="contents")


def rules_page():
    p = ""
    hero = illustrated_hero(p, "hero-how-to-play-illustration.png", (388, 250), "")

    def equip(cls, image, w, h, text):
        return f'<li class="equip equip-{cls}"><span>{text}</span>{img(p, "how-to-play/" + image, w, h)}</li>'

    steps = [
        "The game is played with a minimum of 2 players and a maximum of 4 players.",
        "Players choose their pawns. Each player must have a pawn of a different shape or color.",
        "Each player rolls the dice. The first player to roll a 6 starts, followed by the player on their left, and so on.",
        "Players take turns rolling the dice and moving their pawns forward by the number of tiles shown on the dice.",
    ]
    steps_html = "".join(f'<li><span class="step-num step-{i}">{i}</span><p>{s}</p></li>'
                         for i, s in enumerate(steps, 1))
    effects = [
        ([("good", "Double your move")], "Move forward again by the same number you just rolled."),
        ([("good", "Go to tile X"), ("bad", "Back to tile X"), ("bad", "Back to start")], "Move your pawn directly to that tile."),
        ([("bad", "Miss 1 turn")], "You do not play next turn."),
        ([("bad", "Stuck until a 6")], "You stay on this tile until you roll a 6."),
        ([("good", "1st turn: 6 = here (tile 13)")], "If you roll a 6 on your very first turn, go directly to tile 13."),
        ([("finish", "Exact roll only (tile 30)")], "You must land exactly on tile 30. Extra points make you move backward."),
    ]
    eff_html = "".join(
        '<li class="card"><p class="pills">' + "".join(f'<span class="pill pill-{k}">{n}</span>' for k, n in pills)
        + f"</p><p>{text}</p></li>" for pills, text in effects)
    body = f"""
<div class="page-head">
  {label("How to play", "h1", "label-big")}
  <p>These rules can be modified and adapted.</p>
</div>

<section class="card card-dark">
  <h2 class="card-title"><span class="round round-light">{icon("flag")}</span>Goal</h2>
  <p>Be the first player to land exactly on the final tile, Net zero (tile 30), while learning how to use IT in a more sustainable way.</p>
</section>

<div class="center">{label("Equipment")}</div>
<ul class="equipment">
  {equip("board", "equipment-board.png", 94, 71, "1 double-sided board: Level 1, then Level 2")}
  {equip("cards", "equipment-cards.png", 71, 82, "Definition cards, with the answer under each one")}
  {equip("dice", "equipment-dice.png", 79, 78, "1 dice")}
  {equip("pawn", "equipment-pawn.png", 54, 78, "1 different pawn per player")}
</ul>

<div class="center">{label("Getting started")}</div>
<ol class="timeline">{steps_html}</ol>

<section class="card card-blue">
  {img(p, "how-to-play/rules-winning.png", 304, 99, cls="winning-img")}
  <h2 class="card-title">Winning</h2>
  <p>The winner is the first player to land exactly on the final tile. If a player rolls a number higher than the number of spaces needed to finish, they must move backward by the number of extra spaces.</p>
</section>

<section class="card card-dark">
  <h2 class="card-title"><span class="round round-light">1</span>First phase: discovery and memorization</h2>
  <p>During the first phase, when a player lands on a bonus or penalty tile, they must perform the action indicated on that tile. They must also try to memorize the words associated with these tiles, as they will be useful during the second phase.</p>
</section>

<section class="card card-yellow">
  <h2 class="card-title"><span class="round round-brown">2</span>Second phase: memory and strategy</h2>
  <p>During the second phase, when a player lands on a bonus or penalty tile, an opponent draws a card and reads the definition aloud. The player must give the corresponding word memorized during the first phase. The answer is written under the definition on the card.</p>
  <div class="inner">
    <span class="chip chip-bad">{icon("chevrons-back")}Penalty tile</span>
    <p>If the player remembers the correct word, they avoid the penalty indicated on the tile. Otherwise, they must perform the required action.</p>
  </div>
  <div class="inner">
    <span class="chip chip-good">{icon("chevrons-forward")}Bonus tile</span>
    <p>If the player remembers the correct word, they receive the advantage indicated on the tile. Otherwise, they cannot benefit from it.</p>
  </div>
  <p class="strong">The objective is to use memory skills to avoid penalties and gain advantages in order to progress faster through the game.</p>
</section>

<section class="card card-pale">
  <h2 class="card-title">Transition to the second phase</h2>
  <p>The first player to reach the end of the first phase earns a Joker for the second phase. This Joker can be used on either a bonus or penalty tile, giving the player a strategic advantage.</p>
  <p>Once the first phase is completed, flip the game board over to begin the second phase.</p>
  <p>The Joker allows the player to cancel a penalty or activate a bonus, even if they cannot remember the correct word.</p>
</section>

<div class="center">{label("What the tiles mean")}</div>
<ul class="effects">{eff_html}</ul>

<p class="center more">Want to know more about a tile? Find it in the Contents of this website.<br>
<a class="underline" href="contents.html">Contents</a></p>
"""
    return page("How to play", hero, body, tab="rules")


def about_page():
    hero = illustrated_hero("", "hero-about-illustration.png", (388, 250), "")
    sources = [
        ("https://www.ademe.fr/", "ADEME, French Agency for Ecological Transition"),
        ("https://www.arcep.fr/la-regulation/grands-dossiers-thematiques-transverses/lempreinte-environnementale-du-numerique.html",
         "Arcep &amp; ADEME, environmental footprint of digital technology in France"),
        ("https://theshiftproject.org/", "The Shift Project, Lean ICT reports"),
        ("https://www.iea.org/reports/energy-and-ai", "International Energy Agency (IEA), Energy and AI"),
        ("https://www.greenit.fr/", "GreenIT.fr and the responsible digital design collective"),
        ("https://ewastemonitor.info/", "Global E-waste Monitor (ITU &amp; UNITAR)"),
    ]
    src = "".join(f'<li><a href="{u}" rel="noopener">{t}</a></li>' for u, t in sources)
    body = f"""
<div class="page-head">
  {label("About GreenFlag", "h1", "label-big")}
</div>
<section class="card">
  <p>GreenFlag is a 30-tile board game inspired by Snakes and Ladders, created for an English course. Every coloured tile is linked to a concept about Green IT and eco-design: carbon footprint, datacenters and PUE, Moore's law, product lifetime, green energy and more.</p>
</section>
<section class="card card-yellow">
  <p>The board only shows a short sentence for each tile. This website gives more detailed explanations, so the board is not overloaded with text.</p>
</section>
{label("Main sources")}
<ul class="card list-lines">{src}</ul>
<section class="card card-dark">
  <h2 class="card-title title-yellow">About this website</h2>
  <p>This site practises what it teaches: static pages, no tracker, no external font, no JavaScript, very light.</p>
</section>
"""
    return page("About", hero, body, tab="about")


# ---------------------------------------------------------------- main

def main():
    tiles = json.loads((ROOT / "content" / "tiles.json").read_text(encoding="utf-8"))
    by_id = {t["id"]: t for t in tiles}

    # Empty dist/ (files only, folders are kept: friendlier with network drives)
    if DIST.exists():
        for f in DIST.rglob("*"):
            if f.is_file():
                f.unlink()
    (DIST / "tiles").mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "assets", DIST / "assets", dirs_exist_ok=True)

    ordered = sorted([t for t in tiles if t.get("tile")], key=lambda t: t["tile"]) + [t for t in tiles if not t.get("tile")]
    for i, t in enumerate(ordered):
        prev = ordered[i - 1] if i > 0 else None
        nxt = ordered[i + 1] if i + 1 < len(ordered) else None
        (DIST / "tiles" / f"{t['id']}.html").write_text(tile_page(t, by_id, prev, nxt), encoding="utf-8")
    (DIST / "index.html").write_text(home_page(), encoding="utf-8")
    (DIST / "contents.html").write_text(index_page(tiles), encoding="utf-8")
    (DIST / "rules.html").write_text(rules_page(), encoding="utf-8")
    (DIST / "about.html").write_text(about_page(), encoding="utf-8")

    print(f"Built {len(tiles)} pages ({sum(1 for t in tiles if t.get('tile'))} board tiles) into {DIST}")


if __name__ == "__main__":
    main()
