#!/usr/bin/env python3
"""Self-check for bin/blog.py parsing. Run: python3 bin/test_blog.py"""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import blog

out = blog.body_html("Hi\nhttps://www.youtube.com/watch?v=SNbzYsUCjBk&t=10s\nSee https://youtu.be/SNbzYsUCjBk inline.\n\n![a](images/x.png)\n![b](https://e.com/y.png)")
assert out.count("youtube-nocookie.com/embed/SNbzYsUCjBk") == 1, out  # own line embeds, inline link does not
assert 'src="/blog/posts/images/x.png"' in out and 'src="https://e.com/y.png"' in out, out
assert blog.YT.match("https://youtu.be/SNbzYsUCjBk") and blog.YT.match("https://youtube.com/shorts/SNbzYsUCjBk")
assert not blog.YT.match("watch https://youtu.be/SNbzYsUCjBk")

with tempfile.TemporaryDirectory() as d:
    blog.POSTS = Path(d)
    (Path(d) / "good-post.md").write_text("---\ntitle: T\ndescription: D\nslug: good-post\ndate: 2026-11-20\nauthor: A\n---\nBody\n")
    (Path(d) / "bad.md").write_text("---\ntitle: T\nslug: other\ndate: 20-11-2026\nauthor: A\ncolour: red\n---\n![x](images/missing.png)\n")
    (Path(d) / "commented.md").write_text("---\ntitle: T\ndescription: D\nslug: commented\ndate: 2026-11-20\nauthor: A\n---\nHi\n<!--\n![x](images/nope.png)\n-->\n")
    posts, errs = blog.load()
    assert "nope.png" not in str(errs) and "<!--" not in [b for m, b in posts if m["slug"] == "commented"][0]
    assert all(e.startswith("bad.md") for e in errs), errs
    for want in ["missing description", "must match the file name", "bad date", "unknown field colour", "image not found"]:
        assert any(want in e for e in errs), (want, errs)
print("ok")
