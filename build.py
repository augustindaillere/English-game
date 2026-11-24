#!/usr/bin/env python3
"""GreenFlag companion website - static site generator.

Usage:
    python3 build.py                                  # build the site into dist/
    python3 build.py --base-url https://example.org/greenflag
                                                      # also generate QR codes + printable sheet
    python3 build.py --hide-checks                    # hide the "to verify" tags (final version)

Content lives in content/tiles.json. Styles live in assets/style.css.
Only the Python standard library is needed, except for QR codes (pip install qrcode).
"""
import argparse
import hashlib
import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
SITE_NAME = "GreenFlag"
GAME = json.loads((ROOT / "content" / "game.json").read_text(encoding="utf-8"))
HARD = GAME["hard"]


def asset_version():
    """Short hash of the assets, added to their URLs so phones never keep an old cached copy."""
    h = hashlib.sha1()
    for f in sorted((ROOT / "assets").glob("*")):
        h.update(f.read_bytes())
    return h.hexdigest()[:8]


VERSION = asset_version()

e = html.escape


def page(title, body, depth=0, show_checks=True):
    prefix = "../" * depth
    body_class = "" if show_checks else ' class="hide-checks"'
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#2e9e5b">
<meta name="description" content="GreenFlag: a board game about Green IT and eco-design. Detailed explanations of every tile.">
<title>{e(title)} | {SITE_NAME}</title>
<link rel="stylesheet" href="{prefix}assets/style.css?v={VERSION}">
<script src="{prefix}assets/level.js?v={VERSION}"></script>
<link rel="icon" href="{prefix}assets/flag.svg" type="image/svg+xml">
</head>
<body{body_class}>
<header class="site-header">
  <a class="brand" href="{prefix}index.html"><img src="{prefix}assets/flag.svg" alt="" width="28" height="28"> {SITE_NAME}</a>
  <nav>
    <a href="{prefix}contents.html">Contents</a>
    <a href="{prefix}rules.html">Rules</a>
    <a href="{prefix}about.html">About</a>
  </nav>
</header>
<main>
{body}
</main>
<footer class="site-footer">
  <p>{SITE_NAME}, a serious game about Green IT &amp; eco-design. School project, English Game course.</p>
</footer>
</body>
</html>
"""


LEVEL_SWITCH = """<div class="level-switch" role="group" aria-label="Game level">
  <span class="level-prompt">Which level are you playing?</span>
  <span class="level-label">Level</span>
  <button type="button" data-set-level="easy">Easy</button>
  <button type="button" data-set-level="hard">Hard</button>
</div>"""


TYPE_LABEL = {"good": "Good practice", "bad": "Bad practice", "finish": "Finish"}


def badge(t):
    label = TYPE_LABEL[t["type"]]
    if t.get("effect"):
        label += f" &middot; {e(t['effect'])}"
    return f'<span class="badge badge-{t["type"]}">{label}</span>'


def tile_label(t):
    return f"Tile {t['tile']}" if t.get("tile") else "Go further"


def render_section(s):
    out = [f'<section class="block"><h2>{e(s["heading"])}</h2>']
    if "text" in s:
        out.append(f"<p>{e(s['text'])}</p>")
    if "facts" in s:
        out.append('<ul class="facts">')
        for f in s["facts"]:
            tag = ' <span class="check" title="Figure to double-check before final version">to verify</span>' if f.get("check") else ""
            out.append(f"<li>{e(f['text'])}{tag}</li>")
        out.append("</ul>")
    if "list" in s:
        out.append("<ul>" + "".join(f"<li>{e(i)}</li>" for i in s["list"]) + "</ul>")
    out.append("</section>")
    return "\n".join(out)


def quiz_html(t):
    """Hard level: the definition is shown and the player must type the word."""
    if not t.get("definition"):
        return ""
    answers = [t["title"]] + t.get("answers", [])
    if t["type"] == "finish":
        right = wrong = f'<p class="quiz-effect">{e(HARD["finish"])}</p>'
        order = ""
    else:
        # A tile can override the default bonus/malus of content/game.json with its own "bonus"/"malus"
        right = f'<p class="quiz-effect"><strong>Bonus:</strong> {e(t.get("bonus") or HARD["bonus"])}</p>'
        wrong = f'<p class="quiz-effect"><strong>Malus:</strong> {e(t.get("malus") or HARD["malus"])}</p>'
        order = f'<p class="quiz-order">{e(HARD["order"])}</p>'
    word = f"<strong>{e(t['title'])}</strong>"
    return f"""<section id="quiz" class="quiz block" data-answers="{e(json.dumps(answers, ensure_ascii=False))}" data-tab-title="{e(tile_label(t))} | {SITE_NAME}">
    <h2>Hard level: find the word</h2>
    <p class="quiz-def">{e(t['definition'])}</p>
    <form class="quiz-form" autocomplete="off">
      <label for="answer">Your answer</label>
      <div class="quiz-row">
        <input id="answer" name="answer" type="text" autocapitalize="off" autocorrect="off" spellcheck="false" enterkeyhint="done" required>
        <button type="submit">Check</button>
      </div>
    </form>
    <div class="quiz-result" tabindex="-1" aria-live="polite" hidden></div>
    <template class="quiz-right"><p class="quiz-verdict">Correct! The word was {word}.</p>{right}</template>
    <template class="quiz-wrong"><p class="quiz-verdict">Not quite. The word was {word}.</p>{wrong}</template>
    {order}
  </section>"""


def tile_page(t, by_id, show_checks, prev=None, nxt=None):
    related = [by_id[r] for r in t.get("related", []) if r in by_id]
    rel_html = ""
    if related:
        rel_html = '<section class="block"><h2>Related tiles</h2><ul class="related">' + "".join(
            f'<li><a href="{r["id"]}.html">{e(r["title"])}</a> {badge(r)}</li>' for r in related
        ) + "</ul></section>"
    sources = "".join(
        f'<li><a href="{e(s["url"])}" rel="noopener">{e(s["label"])}</a></li>' for s in t.get("sources", [])
    )
    def nav_link(x, cls, arrow_left):
        if not x:
            return f'<span class="tile-nav-{cls} is-empty"></span>'
        label = f"{x['tile']}" if x.get("tile") else ""
        txt = f"&larr; {label}" if arrow_left else f"{label} &rarr;"
        return f'<a class="tile-nav-{cls}" href="{x["id"]}.html" aria-label="{e(x["title"])}">{txt}</a>'
    prev_html = nav_link(prev, "prev", True)
    next_html = nav_link(nxt, "next", False)
    board_html = f'<blockquote class="board-text"><strong>On the board:</strong> {e(t["board"])}</blockquote>' if t.get("board") else ""
    quiz = quiz_html(t)
    has_quiz = " has-quiz" if quiz else ""
    body = f"""
<article class="tile tile-{t['type']}{has_quiz}">
  {LEVEL_SWITCH if quiz else ""}
  <p class="tile-number">{tile_label(t)}</p>
  <h1 class="tile-reveal">{e(t['title'])}</h1>
  {badge(t)}
  {quiz}
  <div class="tile-reveal">
  {board_html}
  <p class="intro">{e(t['intro'])}</p>
  {''.join(render_section(s) for s in t['sections'])}
  {rel_html}
  <section class="block sources"><h2>Sources</h2><ol>{sources}</ol></section>
  </div>
</article>
<nav class="tile-nav" aria-label="Tile navigation">
  {prev_html}
  <a class="tile-nav-contents" href="../contents.html">Contents</a>
  {next_html}
</nav>
"""
    return page(t["title"], body, depth=1, show_checks=show_checks)


def toc_row(t):
    num = f"{t['tile']:02d}" if t.get("tile") else "+"
    summary = f'<span class="toc-summary">{e(t.get("board") or t["intro"])}</span>'
    if t.get("definition"):
        summary += f'<span class="toc-definition">{e(t["definition"])}</span>'
    effect = f'<span class="toc-effect">{e(t["effect"])}</span>' if t.get("effect") else ""
    return f"""<li class="toc-row toc-{t['type']}">
  <a href="tiles/{t['id']}.html">
    <span class="toc-num">{num}</span>
    <span class="toc-text"><span class="toc-title{" has-def" if t.get("definition") else ""}">{e(t['title'])}</span>{summary}</span>
    <span class="toc-dots" aria-hidden="true"></span>
    {effect}
  </a>
</li>"""


def home_page(show_checks):
    body = """
<section class="home">
  <img class="home-logo" src="assets/flag.svg" alt="" width="96" height="96">
  <h1>GreenFlag</h1>
  <p class="home-tagline">A board game about Green IT &amp; eco-design.</p>
  <p>Roll the dice, move along 30 tiles and discover the environmental impact of digital technology. Good practices help you move forward, bad practices slow you down. First to reach <strong>Net zero</strong> wins!</p>
  <h2 class="home-start">Start a game</h2>
  <div class="levels">
    <a class="level-card" href="contents.html?level=easy" data-set-level="easy">
      <strong>Easy</strong>
      <span>The word and its definition are written on the board. Open a tile here to learn more.</span>
    </a>
    <a class="level-card level-card-hard" href="contents.html?level=hard" data-set-level="hard">
      <strong>Hard</strong>
      <span>Only the definition is on the board. Open the tile here and type the word: right answer = bonus, wrong answer = malus.</span>
    </a>
  </div>
  <p class="home-links"><a href="rules.html">How to play</a> &middot; <a href="about.html">About</a></p>
</section>
"""
    return page("Home", body, show_checks=show_checks)


def index_page(tiles, show_checks):
    board = sorted([t for t in tiles if t.get("tile")], key=lambda t: t["tile"])
    extra = [t for t in tiles if not t.get("tile")]
    body = f"""
<section class="hero">
  <h1>Contents</h1>
  {LEVEL_SWITCH}
  <p>Landed on a coloured tile? Find its number below (or scan its QR code), check its effect and open it to read the detailed explanation.</p>
  <p class="hard-only">Hard level: open the tile, read the definition again and type the matching word.</p>
  <p class="legend"><span class="badge badge-good">Good practice</span> <span class="badge badge-bad">Bad practice</span> <span class="badge badge-finish">Finish</span></p>
</section>
<h2 class="toc-heading">The board, tile by tile</h2>
<ol class="toc">{''.join(toc_row(t) for t in board)}</ol>
<h2 class="toc-heading">Go further</h2>
<ol class="toc">{''.join(toc_row(t) for t in extra)}</ol>
"""
    return page("Contents", body, show_checks=show_checks)


RULES = """
<h1>How to play</h1>
<section class="block">
<h2>Goal</h2>
<p>Be the first player to reach tile 30, <strong>Net zero</strong>, while learning how to use IT in a more sustainable way.</p>
</section>
<section class="block">
<h2>Equipment</h2>
<ul><li>1 board (30 tiles)</li><li>1 dice</li><li>1 pawn per player (2 to 4 players)</li></ul>
</section>
<section class="block">
<h2>Setup (first 5 minutes)</h2>
<ol>
<li>Read the rules together. Remember: this is a serious game, you are here to learn!</li>
<li>Put all pawns on the Start tile.</li>
<li>Each player throws the dice. The highest number starts.</li>
</ol>
</section>
<section class="block">
<h2>Two levels</h2>
<ul>
<li><strong>Easy</strong>: the word and its definition are written on each coloured tile. Use this website to learn more about them.</li>
<li><strong>Hard</strong>: only the definition is written on the tile. Scan the tile (or find its number in the Contents), read the definition and type the matching word.
<ul>
<li>Right answer: <strong>bonus</strong>, {bonus}</li>
<li>Wrong answer: <strong>malus</strong>, {malus}</li>
<li>You only get one try. Capital letters, accents and small typos do not matter.</li>
<li>{order}</li>
</ul></li>
</ul>
</section>
<section class="block">
<h2>A turn</h2>
<ol>
<li>Throw the dice and move your pawn forward by that number of tiles.</li>
<li>If you land on a coloured tile, read it aloud and apply its effect.</li>
<li><span class="badge badge-good">Good practice</span> tiles help you (move again, jump forward).</li>
<li><span class="badge badge-bad">Bad practice</span> tiles slow you down (go back, miss a turn, stay stuck).</li>
<li>Hard level: scan the tile and find the word to win a bonus (see "Two levels").</li>
<li>Want to know more? Scan the QR code of the tile or find it on this website.</li>
</ol>
</section>
<section class="block">
<h2>Special effects</h2>
<ul>
<li><strong>Double your move</strong>: move forward again by the same number you just rolled.</li>
<li><strong>Go to tile X / Back to tile X / Back to start</strong>: move your pawn directly to that tile.</li>
<li><strong>Miss 1 turn</strong>: you do not play next turn.</li>
<li><strong>Stuck until a 6</strong>: you stay on this tile until you roll a 6.</li>
<li><strong>1st turn: 6 = here</strong> (tile 13): if you roll a 6 on your very first turn, go directly to tile 13.</li>
<li><strong>Exact roll only</strong> (tile 30): you must land exactly on tile 30 to win.</li>
</ul>
<p class="check-note"><span class="check">to verify</span> Rule interpretations to confirm with the game designers: does "Double your move" mean moving the rolled number once more? If the roll is too high on the last tiles, does the player stay put or bounce back?</p>
</section>
<section class="block">
<h2>End of the game</h2>
<p>The first player to land exactly on tile 30 wins. Everyone else wins some knowledge about Green IT!</p>
</section>
"""

ABOUT = """
<h1>About GreenFlag</h1>
<section class="block">
<p>GreenFlag is a 30-tile board game inspired by Snakes and Ladders, created for an English course. Every coloured tile is linked to a concept about Green IT and eco-design: carbon footprint, datacenters and PUE, Moore's law, product lifetime, green energy and more.</p>
<p>The board only shows a short sentence for each tile. This website gives more detailed explanations, so the board is not overloaded with text.</p>
</section>
<section class="block">
<h2>Main sources</h2>
<ul>
<li><a href="https://www.ademe.fr/">ADEME</a>, French Agency for Ecological Transition</li>
<li><a href="https://www.arcep.fr/la-regulation/grands-dossiers-thematiques-transverses/lempreinte-environnementale-du-numerique.html">Arcep &amp; ADEME</a>, environmental footprint of digital technology in France</li>
<li><a href="https://theshiftproject.org/">The Shift Project</a>, Lean ICT reports</li>
<li><a href="https://www.iea.org/reports/energy-and-ai">International Energy Agency (IEA)</a>, Energy and AI</li>
<li><a href="https://www.greenit.fr/">GreenIT.fr</a> and the responsible digital design collective</li>
<li><a href="https://ewastemonitor.info/">Global E-waste Monitor</a> (ITU &amp; UNITAR)</li>
</ul>
</section>
<section class="block">
<h2>About this website</h2>
<p>This site practises what it teaches: static pages, no tracker, no external font, very light. The only JavaScript is a tiny script (a few KB) for the Hard level quiz; everything else works without it.</p>
</section>
"""


def build_qr(tiles, base_url, show_checks):
    try:
        import qrcode
        import qrcode.image.svg
    except ImportError:
        print("! qrcode not installed: run `pip install qrcode` to generate QR codes")
        return
    qr_dir = DIST / "qr"
    qr_dir.mkdir(exist_ok=True)
    base = base_url.rstrip("/")
    items = []
    for t in sorted([t for t in tiles if t.get("tile")], key=lambda t: t["tile"]):
        url = f"{base}/tiles/{t['id']}.html"
        n = t["tile"]
        img = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=2)
        img.save(str(qr_dir / f"{n:02d}-{t['id']}.svg"))
        items.append(f"""<li class="print-card card-{t['type']}">
  <img src="qr/{n:02d}-{t['id']}.svg" alt="QR code">
  <div><strong>Tile {n}: {e(t['title'])}</strong> {badge(t)}<br>{e(t['board'])}{'<br><em>Hard level:</em> ' + e(t['definition']) if t.get('definition') else ''}<br><small>{e(url)}</small></div>
</li>""")
    body = '<h1>Printable tiles with QR codes</h1><p class="no-print">Print this page (Ctrl+P) to get the texts and QR codes for the board and cards.</p><ul class="print-list">' + "".join(items) + "</ul>"
    (DIST / "print.html").write_text(page("Print", body, show_checks=show_checks), encoding="utf-8")
    print(f"QR codes generated for {base}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", help="Public URL of the site, used for QR codes")
    ap.add_argument("--hide-checks", action="store_true", help='Hide "to verify" tags')
    args = ap.parse_args()
    show = not args.hide_checks

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
        (DIST / "tiles" / f"{t['id']}.html").write_text(tile_page(t, by_id, show, prev, nxt), encoding="utf-8")
    (DIST / "index.html").write_text(home_page(show), encoding="utf-8")
    (DIST / "contents.html").write_text(index_page(tiles, show), encoding="utf-8")
    rules = RULES.format(bonus=e(HARD["bonus"].rstrip(".").lower()), malus=e(HARD["malus"].rstrip(".").lower()), order=e(HARD["order"]))
    (DIST / "rules.html").write_text(page("How to play", rules, show_checks=show), encoding="utf-8")
    (DIST / "about.html").write_text(page("About", ABOUT, show_checks=show), encoding="utf-8")

    if args.base_url:
        build_qr(tiles, args.base_url, show)
    print(f"Built {len(tiles)} pages ({sum(1 for t in tiles if t.get('tile'))} board tiles) into {DIST}")


if __name__ == "__main__":
    main()
