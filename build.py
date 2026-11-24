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
PHASE2 = GAME["phase2"]


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
<script src="{prefix}assets/phase.js?v={VERSION}"></script>
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


PHASE_SWITCH = """<div class="phase-switch" role="group" aria-label="Game phase">
  <span class="phase-prompt">Which phase are you playing?</span>
  <span class="phase-label">Phase</span>
  <button type="button" data-set-phase="1">Phase 1</button>
  <button type="button" data-set-phase="2">Phase 2</button>
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
    """Phase 2: the definition is shown and the player must type the word."""
    if not t.get("definition"):
        return ""
    answers = [t["title"]] + t.get("answers", [])
    word = f"<strong>{e(t['title'])}</strong>"
    effect = t.get("effect", "")
    effect = effect[:1].lower() + effect[1:]

    def msg(key):
        return e(PHASE2[key]).replace("{effect}", e(effect))

    if t["type"] == "finish":
        right = wrong = joker = f'<p class="quiz-effect">{msg("finish")}</p>'
        joker_btn = ""
    else:
        kind = "good" if t["type"] == "good" else "bad"
        right = f'<p class="quiz-effect">{msg(kind + "_right")}</p>'
        wrong = f'<p class="quiz-effect">{msg(kind + "_wrong")}</p>'
        joker = f'<p class="quiz-effect">{msg("joker_" + kind)}</p>'
        joker_btn = """<div class="joker">
      <button type="button" class="joker-button">Use the Joker</button>
      <p class="joker-help">Only for the player who won the Joker in phase 1. It works once per game, even without the word.</p>
    </div>
    <p class="joker-gone">The Joker has already been used in this game.</p>"""
    stake = {"good": "Find the word to get the bonus.", "bad": "Find the word to avoid the penalty."}.get(t["type"], "Find the word.")
    return f"""<section id="quiz" class="quiz block" data-answers="{e(json.dumps(answers, ensure_ascii=False))}" data-tab-title="{e(tile_label(t))} | {SITE_NAME}">
    <h2>Phase 2: {stake}</h2>
    <p class="quiz-def">{e(t['definition'])}</p>
    <form class="quiz-form" autocomplete="off">
      <label for="answer">The word</label>
      <div class="quiz-row">
        <input id="answer" name="answer" type="text" autocapitalize="off" autocorrect="off" spellcheck="false" enterkeyhint="done" required>
        <button type="submit">Check</button>
      </div>
    </form>
    <div class="quiz-result" tabindex="-1" aria-live="polite" hidden></div>
    <template class="quiz-right"><p class="quiz-verdict">Correct! The word was {word}.</p>{right}</template>
    <template class="quiz-wrong"><p class="quiz-verdict">Not quite. The word was {word}.</p>{wrong}</template>
    <template class="quiz-joker"><p class="quiz-verdict">Joker used! The word was {word}.</p>{joker}</template>
    {joker_btn}
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
  {PHASE_SWITCH if quiz else ""}
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
    <a class="level-card" href="contents.html?phase=1&amp;new=1" data-set-phase="1">
      <strong>Phase 1: Discovery</strong>
      <span>Words and definitions are on the board. Do what each tile says and memorize its word.</span>
    </a>
    <a class="level-card level-card-hard" href="contents.html?phase=2" data-set-phase="2">
      <strong>Phase 2: Memory</strong>
      <span>Board flipped: only definitions. Type the word here to get the bonus or avoid the penalty.</span>
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
  {PHASE_SWITCH}
  <p>Landed on a coloured tile? Find its number below (or scan its QR code), check its effect and open it to read the detailed explanation.</p>
  <p class="phase2-only">Phase 2: open the tile, read the definition and type the word you memorized. Right word: you get the bonus or avoid the penalty.</p>
  <p class="phase2-only joker-status"><span class="joker-free">Joker: not used yet in this game.</span><span class="joker-spent">Joker: already used in this game. <button type="button" class="link-button" data-reset-joker>New game? Give it back</button></span></p>
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
<ul><li>1 double-sided board (30 tiles): words and definitions on one side for phase 1, only definitions on the other side for phase 2</li><li>1 dice</li><li>1 pawn per player (2 to 4 players)</li></ul>
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
<h2>First phase: discovery and memorization</h2>
<p>When a player lands on a bonus or penalty tile, they must do the action written on that tile. They must also try to memorize the words of these tiles: they will be useful during the second phase.</p>
</section>
<section class="block">
<h2>Transition to the second phase</h2>
<p>The first player to reach the end of the first phase earns a <strong>Joker</strong> for the second phase. Once the first phase is over, flip the board over to begin the second phase: only the definitions are written on it.</p>
</section>
<section class="block">
<h2>Second phase: memory and strategy</h2>
<p>When a player lands on a bonus or penalty tile, they scan the tile (or find its number in the Contents) and type the word memorized during the first phase.</p>
<ul>
<li><span class="badge badge-bad">Penalty tile</span> Right word: you avoid the penalty. Wrong word: you do the action written on the tile.</li>
<li><span class="badge badge-good">Bonus tile</span> Right word: you get the advantage written on the tile. Wrong word: you cannot use it.</li>
<li>One try only. Capital letters, accents and small typos do not matter.</li>
</ul>
<p>The goal is to use your memory to avoid penalties and get advantages, so you move faster through the game.</p>
</section>
<section class="block">
<h2>The Joker</h2>
<p>The Joker can be used once, on a bonus or a penalty tile: it cancels a penalty or activates a bonus, even if you cannot remember the word. On the website, press <strong>Use the Joker</strong> on the tile page (before answering, or just after a wrong answer).</p>
</section>
<section class="block">
<h2>A turn</h2>
<ol>
<li>Throw the dice and move your pawn forward by that number of tiles.</li>
<li>If you land on a coloured tile, read it aloud and apply its effect.</li>
<li><span class="badge badge-good">Good practice</span> tiles help you (move again, jump forward).</li>
<li><span class="badge badge-bad">Bad practice</span> tiles slow you down (go back, miss a turn, stay stuck).</li>
<li>Second phase: scan the tile and type its word before applying the effect (see below).</li>
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
<p>The first player to land exactly on tile 30 during the second phase wins. Everyone else wins some knowledge about Green IT!</p>
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
<p>This site practises what it teaches: static pages, no tracker, no external font, very light. The only JavaScript is a tiny script (a few KB) for the phase 2 quiz and the Joker; everything else works without it.</p>
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
  <div><strong>Tile {n}: {e(t['title'])}</strong> {badge(t)}<br>{e(t['board'])}{'<br><em>Phase 2 side:</em> ' + e(t['definition']) if t.get('definition') else ''}<br><small>{e(url)}</small></div>
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
    (DIST / "rules.html").write_text(page("How to play", RULES, show_checks=show), encoding="utf-8")
    (DIST / "about.html").write_text(page("About", ABOUT, show_checks=show), encoding="utf-8")

    if args.base_url:
        build_qr(tiles, args.base_url, show)
    print(f"Built {len(tiles)} pages ({sum(1 for t in tiles if t.get('tile'))} board tiles) into {DIST}")


if __name__ == "__main__":
    main()
