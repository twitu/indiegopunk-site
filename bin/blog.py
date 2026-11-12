#!/usr/bin/env python3
"""Build the blog from blog/posts/*.md into static pages.

  bin/blog.py check    Validate every post. Exit 1 on any error.
  bin/blog.py build    Validate, then write blog/index.html, blog/<slug>/index.html, blog/rss.xml, blog/atom.xml.

A post starts with front matter between --- lines:

  ---
  title: Shipping Third Law
  description: One or two sentences for the list and for link previews.
  slug: shipping-third-law            (must match the file name)
  date: 2026-11-20
  author: Your Name
  ---

The body is Markdown. A YouTube link on a line of its own becomes an embedded player.
Images go in blog/posts/images/ and are written as ![alt](images/name.png).
Needs: pip install markdown
"""
import html, json, re, shutil, sys, datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BLOG = ROOT / "blog"
POSTS = BLOG / "posts"
FIELDS = ["title", "description", "slug", "date", "author"]
SITE = "https://indiegopunk.com"
YT = re.compile(r"^\s*<?https?://(?:www\.|m\.)?(?:youtube\.com/(?:watch\?(?:\S*&)?v=|shorts/|live/)|youtu\.be/)([\w-]{11})\S*?>?\s*$")


def read(path):
    """Return (meta, body, errors) for one post file."""
    text, errs = path.read_text(), []
    m = re.match(r"---\n(.*?)\n---\n?(.*)", text, re.S)
    if not m:
        return {}, text, [f"{path.name}: no front matter (--- lines at the top)"]
    meta = {}
    for line in m.group(1).splitlines():
        if line.strip():
            k, sep, v = line.partition(":")
            if not sep:
                errs.append(f"{path.name}: bad front matter line {line!r}")
            meta[k.strip()] = v.strip()
    for k in FIELDS:
        if not meta.get(k):
            errs.append(f"{path.name}: missing {k}")
    for k in meta:
        if k not in FIELDS:
            errs.append(f"{path.name}: unknown field {k}")
    slug = meta.get("slug", "")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug):
        errs.append(f"{path.name}: slug must be a kebab slug")
    if slug and slug != path.stem:
        errs.append(f"{path.name}: slug {slug!r} must match the file name")
    try:
        dt.date.fromisoformat(meta.get("date", ""))
    except ValueError:
        errs.append(f"{path.name}: bad date (use YYYY-MM-DD)")
    body = re.sub(r"<!--.*?-->", "", m.group(2), flags=re.S)  # comments are notes for the writer, never published
    for src in re.findall(r"!\[[^\]]*\]\(\s*<?([^)\s>]+)", body):
        if not re.match(r"https?://|/", src) and not (POSTS / src).is_file():
            errs.append(f"{path.name}: image not found: {src}")
    return meta, body, errs


def load():
    posts, errs = [], []
    for p in sorted(POSTS.glob("*.md")):
        meta, body, e = read(p)
        posts.append((meta, body)); errs += e
    slugs = [m.get("slug") for m, _ in posts]
    errs += [f"duplicate slug {s}" for s in sorted(set(slugs)) if s and slugs.count(s) > 1]
    posts.sort(key=lambda p: (p[0].get("date", ""), p[0].get("slug", "")), reverse=True)
    return posts, errs


def body_html(body):
    import markdown
    # A YouTube link alone on a line becomes the same privacy-friendly embed the home page uses.
    lines = [f'\n<div class="video"><iframe src="https://www.youtube-nocookie.com/embed/{m.group(1)}" title="YouTube video" '
             f'loading="lazy" allow="accelerometer; encrypted-media; picture-in-picture" allowfullscreen></iframe></div>\n'
             if (m := YT.match(l)) else l for l in body.splitlines()]
    out = markdown.markdown("\n".join(lines), extensions=["fenced_code", "tables"])
    # Post pages live at /blog/<slug>/, images at /blog/posts/images/: point relative image paths there.
    return re.sub(r'(<img[^>]*\ssrc=")(?!https?://|/)', r"\1/blog/posts/", out)


def nice(d):
    d = dt.date.fromisoformat(d)
    return f"{d.day} {d.strftime('%B %Y')}"


CSS = """
@font-face { font-family: "Archivo Black"; src: url("/fonts/ArchivoBlack-Regular.ttf"); font-display: swap; }
@font-face { font-family: "Space Mono"; font-weight: 700; src: url("/fonts/SpaceMono-Bold.ttf"); font-display: swap; }
/* Same tokens as the home and calendar pages. */
:root {
  --ink: #0d0a12; --panel: #1b1426; --bone: #f2ece0; --pink: #ff2e88; --yellow: #f4ff3a; --violet: #7a2cff;
  --muted: #cfc6d8; --dim: #8a8099;
  --display: "Archivo Black", Impact, "Arial Black", sans-serif;
  --mono: "Space Mono", ui-monospace, Menlo, monospace;
}
* { box-sizing: border-box; }
html { background: var(--ink); }
body {
  margin: 0; min-height: 100svh; display: grid; grid-template-rows: 1fr auto;
  color: var(--bone); font-family: var(--mono); font-weight: 700; line-height: 1.6;
  padding: 0 max(16px, env(safe-area-inset-right)) 0 max(16px, env(safe-area-inset-left));
}
body::before { content: ""; position: fixed; inset: 0; z-index: -1; pointer-events: none; opacity: .1; background: url("/texture.png") 0 0 / 300px 300px; }
a { color: inherit; }
a:focus-visible { outline: 3px solid var(--yellow); outline-offset: 2px; }
main { width: 100%; max-width: 760px; margin: 0 auto; padding: 28px 0 48px; display: grid; gap: 28px; align-content: start; }
.home { justify-self: start; display: inline-flex; gap: 4px; text-decoration: none; }
.home .t { display: grid; place-items: center; width: 28px; aspect-ratio: 24 / 30; background: var(--bone); color: var(--ink); font: 400 18px / 1 var(--display); border: 2px solid var(--ink); box-shadow: 3px 3px 0 var(--pink); transform: rotate(var(--r, 0deg)); }
.home .t.v { background: var(--violet); color: var(--yellow); }
.home .t.p { background: var(--pink); box-shadow: 3px 3px 0 var(--violet); }
.home .t.y { background: var(--yellow); }
h1 { margin: 0; font: 400 clamp(30px, 7vw, 52px) / 1.05 var(--display); text-transform: uppercase; text-wrap: balance; }
h1 em { font-style: normal; color: var(--pink); text-shadow: 3px 3px 0 var(--yellow); }
.lede { margin: 0; max-width: 56ch; color: var(--muted); }
.by { font-size: 13px; letter-spacing: .06em; text-transform: uppercase; color: var(--dim); }
.by b { color: var(--pink); font-weight: 700; }
.posts { display: grid; gap: 20px; }
.post { background: var(--panel); border: 3px solid var(--ink); box-shadow: 6px 6px 0 var(--violet); padding: 18px 20px; display: grid; gap: 6px; }
.post h2 { margin: 0; font: 400 22px / 1.15 var(--display); text-transform: uppercase; }
.post h2 a { text-decoration: none; }
.post h2 a:hover { color: var(--yellow); }
.post p { margin: 0; color: var(--muted); font-size: 14px; }
.subs { margin: 0; font-size: 13px; color: var(--dim); }
.subs a { color: var(--yellow); }
.empty { background: var(--panel); border: 3px dashed var(--violet); padding: 18px 20px; color: var(--muted); }
article.prose { display: grid; gap: 14px; }
.prose h1 { margin-bottom: 4px; }
.prose h2, .prose h3 { margin: 18px 0 0; font: 400 22px / 1.2 var(--display); text-transform: uppercase; color: var(--yellow); }
.prose h3 { font-size: 18px; color: var(--bone); }
.prose p, .prose ul, .prose ol { margin: 0; color: var(--muted); }
.prose a { color: var(--pink); }
.prose img { max-width: 100%; height: auto; display: block; border: 3px solid var(--ink); box-shadow: 6px 6px 0 var(--violet); }
.prose blockquote { margin: 0; padding: 4px 16px; border-left: 4px solid var(--pink); }
.prose pre { overflow-x: auto; background: var(--panel); padding: 12px 14px; border: 2px solid var(--violet); }
.prose code { font-family: var(--mono); }
.prose table { border-collapse: collapse; display: block; overflow-x: auto; }
.prose th, .prose td { border: 2px solid var(--violet); padding: 6px 10px; text-align: left; }
.video { aspect-ratio: 16 / 9; background: #120d1a; border: 3px solid var(--ink); box-shadow: 6px 6px 0 var(--violet); }
.video iframe { width: 100%; height: 100%; border: 0; display: block; }
.back { font-size: 13px; letter-spacing: .08em; text-transform: uppercase; color: var(--yellow); }
footer { max-width: 760px; width: 100%; margin: 0 auto; text-align: center; padding: 20px 0 28px; font-size: 12px; color: var(--dim); letter-spacing: .06em; text-transform: uppercase; }
footer a { margin: 0 8px; }
"""


def page(title, desc, url, og_type, ld, content):
    e = html.escape
    ld = json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="Indie Go Punk">
<meta property="og:locale" content="en_US">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}/og-home.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">
<meta name="twitter:image" content="{SITE}/og-home.jpg">
<script type="application/ld+json">{ld}</script>
<meta name="theme-color" content="#0d0a12">
<link rel="icon" href="/icon.png">
<link rel="apple-touch-icon" href="/icon.png">
<link rel="alternate" type="application/rss+xml" title="Indie Go Punk Blog (RSS)" href="/blog/rss.xml">
<link rel="alternate" type="application/atom+xml" title="Indie Go Punk Blog (Atom)" href="/blog/atom.xml">
<style>{CSS}</style>
</head>
<body>
<main>
  <a class="home" href="/" aria-label="Indie Go Punk home">
    <span class="t" style="--r:-4deg">I</span><span class="t v" style="--r:3deg">G</span><span class="t p" style="--r:-2deg">P</span><span class="t y" style="--r:4deg">!</span>
  </a>
{content}
</main>
<footer><a href="/">Home</a> &middot; <a href="/blog/">Blog</a> &middot; <a href="/calendars/">Game Jams</a> &middot; &copy; Indie Go Punk</footer>
</body>
</html>
"""


def index_html(posts):
    e = html.escape
    items = "".join(
        f'\n    <article class="post"><span class="by">{nice(m["date"])} &middot; <b>{e(m["author"])}</b></span>'
        f'<h2><a href="/blog/{m["slug"]}/">{e(m["title"])}</a></h2><p>{e(m["description"])}</p></article>'
        for m, _ in posts) or '\n    <div class="empty">First posts are on the way.</div>'
    ld = {"@context": "https://schema.org", "@type": "Blog", "name": "Indie Go Punk Blog", "url": f"{SITE}/blog/",
          "isPartOf": {"@type": "WebSite", "url": f"{SITE}/", "name": "Indie Go Punk"},
          "blogPost": [{"@type": "BlogPosting", "headline": m["title"], "url": f"{SITE}/blog/{m['slug']}/", "datePublished": m["date"]} for m, _ in posts]}
    content = f"""  <header>
    <h1>The <em>blog</em></h1>
    <p class="lede">Notes from Indie Go Punk on making indie games, finding players and shipping.</p>
  </header>
  <section class="posts" aria-label="Posts">{items}
  </section>
  <p class="subs">Follow along in any feed reader: <a href="/blog/rss.xml">RSS</a> &middot; <a href="/blog/atom.xml">Atom</a></p>"""
    return page("Blog | Indie Go Punk", "Notes from Indie Go Punk on making indie games, finding players and shipping.",
                f"{SITE}/blog/", "website", ld, content)


def post_html(m, body):
    e, url = html.escape, f"{SITE}/blog/{m['slug']}/"
    ld = {"@context": "https://schema.org", "@type": "BlogPosting", "headline": m["title"], "description": m["description"],
          "datePublished": m["date"], "author": {"@type": "Person", "name": m["author"]}, "url": url,
          "image": f"{SITE}/og-home.jpg", "publisher": {"@type": "Organization", "name": "Indie Go Punk"}}
    content = f"""  <article class="prose">
    <h1>{e(m["title"])}</h1>
    <span class="by">{nice(m["date"])} &middot; <b>{e(m["author"])}</b></span>
{body_html(body)}
  </article>
  <a class="back" href="/blog/">&larr; All posts</a>"""
    return page(f'{m["title"]} | Indie Go Punk', m["description"], url, "article", ld, content)


def feeds(posts):
    """RSS 2.0 and Atom with full post content. Dated from the newest post, so a rebuild without changes changes nothing."""
    from email.utils import format_datetime
    e = lambda t: html.escape(t, quote=False)
    when = lambda d: dt.datetime.fromisoformat(d).replace(tzinfo=dt.timezone.utc)
    full = lambda body: re.sub(r'((?:src|href)=")/', rf"\1{SITE}/", body_html(body))  # readers need absolute links
    newest = posts[0][0]["date"] if posts else "2026-11-12"
    title, desc = "Indie Go Punk Blog", "Notes from Indie Go Punk on making indie games, finding players and shipping."
    rss = "".join(f"""
<item><title>{e(m["title"])}</title><link>{SITE}/blog/{m["slug"]}/</link><guid>{SITE}/blog/{m["slug"]}/</guid>
<pubDate>{format_datetime(when(m["date"]))}</pubDate><dc:creator>{e(m["author"])}</dc:creator>
<description>{e(full(b))}</description></item>""" for m, b in posts)
    atom = "".join(f"""
<entry><title>{e(m["title"])}</title><link href="{SITE}/blog/{m["slug"]}/"/><id>{SITE}/blog/{m["slug"]}/</id>
<published>{when(m["date"]).isoformat()}</published><updated>{when(m["date"]).isoformat()}</updated>
<author><name>{e(m["author"])}</name></author><summary>{e(m["description"])}</summary>
<content type="html">{e(full(b))}</content></entry>""" for m, b in posts)
    (BLOG / "rss.xml").write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel>
<title>{title}</title><link>{SITE}/blog/</link><description>{desc}</description><language>en</language>
<atom:link href="{SITE}/blog/rss.xml" rel="self" type="application/rss+xml"/>
<lastBuildDate>{format_datetime(when(newest))}</lastBuildDate>{rss}
</channel></rss>
""")
    (BLOG / "atom.xml").write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<title>{title}</title><subtitle>{desc}</subtitle><id>{SITE}/blog/</id>
<link href="{SITE}/blog/"/><link rel="self" href="{SITE}/blog/atom.xml"/>
<updated>{when(newest).isoformat()}</updated><author><name>Indie Go Punk</name></author>{atom}
</feed>
""")


def build(posts):
    # Every folder in blog/ except posts/ is generated: clear them so a renamed or deleted post leaves nothing behind.
    for d in BLOG.iterdir():
        if d.is_dir() and d.name != "posts":
            shutil.rmtree(d)
    (BLOG / "index.html").write_text(index_html(posts))
    feeds(posts)
    for m, body in posts:
        (BLOG / m["slug"]).mkdir()
        (BLOG / m["slug"] / "index.html").write_text(post_html(m, body))
    sys.path.insert(0, str(ROOT / "bin"))
    from jams import sitemap
    sitemap()


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd not in ("check", "build"):
        sys.exit(__doc__)
    posts, errs = load()
    if errs:
        print("\n".join(errs), file=sys.stderr); sys.exit(1)
    if cmd == "build":
        build(posts)
    print(f"ok: {len(posts)} posts")


if __name__ == "__main__":
    main()
