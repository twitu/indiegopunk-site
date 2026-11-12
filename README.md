# Indie Go Punk site

The website for [indiegopunk.com](https://indiegopunk.com), the punkest indie games podcast.

- `/` home page: episodes, the "want your studio on the show?" form, links out.
- `/calendars/` game jam calendar: list and month views, filters, `.ics` feed.
- `/blog/` blog: posts written in Markdown.

Everything is plain HTML, CSS and JavaScript. There is no framework and no bundler. Small Python scripts generate the parts that come from data (jams and blog posts).

## How it is hosted

GitHub Pages serves the `main` branch as it is committed ("deploy from a branch", with `.nojekyll` so GitHub does not run Jekyll). `CNAME` points it at indiegopunk.com.

This means **whatever is on `main` is live**, usually within a minute or two of a merge. Generated files (blog pages, `jams.ics`, `sitemap.xml`) must be built and committed; GitHub Pages does not build anything.

## Run it locally

```bash
pip install markdown             # only needed for the blog build
python3 -m http.server 8765      # then open http://127.0.0.1:8765/
```

Use port 8765: the interest form backend only accepts requests from the live domains and `http://127.0.0.1:8765`.

## Layout

```
index.html                 home page (episodes list is the EPISODES array near the bottom)
calendars/
  index.html               calendar page; loads jams.json in the browser
  jams.json                the jam data, the one source of truth
  jams.ics                 generated feed
blog/
  posts/*.md               blog posts (you write these)
  posts/images/            images used by posts
  index.html, <slug>/      generated pages, do not edit by hand
bin/
  jams.py                  validate and build the jam calendar
  jams_sync.py             pull upcoming jams from itch.io
  jams-refresh.sh          fortnightly sync run on the owner's Mac
  blog.py                  validate and build the blog
  new-post                 start a new blog post from a template
  test_blog.py             self-check for blog.py
infra/                     AWS CDK: interest form backend and public asset bucket
.github/workflows/         CI for jams and blog
sitemap.xml, robots.txt    SEO; sitemap.xml is generated
```

## Blog

### Write a post

1. Start the post:

   ```bash
   bin/new-post "Shipping Third Law"                 # author defaults to your git user.name
   bin/new-post "Shipping Third Law" "Your Name"
   ```

   This writes `blog/posts/<slug>.md` with today's date and an example body. The YouTube and image examples sit inside an `<!-- ... -->` comment; copy what you need out of it. HTML comments are never published. The finished file looks like this:

   ```markdown
   ---
   title: Shipping Third Law
   description: One or two sentences, shown in the post list and in link previews.
   slug: shipping-third-law
   date: 2026-11-20
   author: Your Name
   ---
   The post body, in Markdown.

   https://www.youtube.com/watch?v=SNbzYsUCjBk

   ![A screenshot of the game](images/third-law.png)
   ```

   - All five fields are required. `slug` must be lowercase-with-hyphens and match the file name. `date` is `YYYY-MM-DD`.
   - A YouTube link **on a line of its own** becomes an embedded player. A YouTube link inside a sentence stays a normal link.
   - Put images in `blog/posts/images/` and refer to them as `images/<name>`. Compress them first; they live in the repo.
   - Tables and fenced code blocks work. Raw HTML is passed through.

2. Build and preview:

   ```bash
   python3 bin/blog.py build      # or: python3 bin/blog.py check  (validate only)
   python3 -m http.server 8765    # http://127.0.0.1:8765/blog/
   ```

   The build rewrites `blog/index.html` (newest first), every `blog/<slug>/index.html`, and `sitemap.xml`. You never edit the post list by hand. A deleted or renamed post's old page is removed.

3. Commit the `.md`, its images and the generated files together:

   ```bash
   git add blog sitemap.xml
   ```

4. Open a pull request (see [Contributing](#contributing)). The post goes live when the PR is merged into `main`.

### What CI does

`.github/workflows/blog.yml` runs on pull requests and pushes to `main` that touch the blog. It runs `bin/test_blog.py`, rebuilds the blog, and fails if the generated pages differ from what was committed. If it fails with "Run python3 bin/blog.py build and commit the result", do exactly that. CI never commits anything for the blog.

### Known friction and how to remove it later

The current setup is simple but asks writers to run the build and commit generated HTML. Two posts in flight at the same time will both change `blog/index.html` and `sitemap.xml`, so the second one to merge needs a rebuild after rebasing.

Two ways to improve it, if posting becomes frequent:

- **Deploy with GitHub Actions (preferred).** Switch Settings > Pages > Source to "GitHub Actions" and add a workflow that runs `python3 bin/blog.py build` on every push to `main` and publishes the result. Generated blog HTML would no longer be committed: a post becomes one `.md` file plus images. Changing the Pages source needs admin access on the repo.
- **Build on the pull request.** Change `blog.yml` to build and commit the generated pages back to the PR branch. No settings change needed, but a bot pushes to your branch, so pull before committing again.

## Game jam calendar

`calendars/jams.json` is the data. Edit it, then run:

```bash
python3 bin/jams.py check          # validate
python3 bin/jams.py build          # validate, sort, write jams.json, jams.ics, structured data and sitemap
python3 bin/jams.py add --name "..." --url https://... --start 2027-01-29 --end 2027-01-31 --host "..."
python3 bin/jams.py stale 30       # jams not verified in 30 days
python3 bin/jams_sync.py           # dry run of the itch.io sync; --write to apply
```

- Required fields: `id, name, url, start, end, host, format, team, verified`. Unknown fields fail validation; add new ones to `KEYS` in `bin/jams.py`.
- `end` is inclusive. Dates are `YYYY-MM-DD` strings.
- `build` replaces the regions between `<!--jams-ld-->…<!--/jams-ld-->` and `<!--jams-ns-->…<!--/jams-ns-->` in `calendars/index.html`. Do not edit inside them, and do not remove the markers.
- Jams added by `jams_sync.py` carry `"source": "itch-sync"` and default to online, solo or team, no prize. Check them against the jam page before merging.
- People submit jams through the "Submit a game jam" issue form.

`.github/workflows/jams.yml` validates on pull requests. On pushes to `main` that change `jams.json`, and every Monday, it rebuilds and **commits straight to `main` as jams-bot**. Pull before you push after touching jam data.

## Shared pieces to keep in step

- **Sitemap.** Both `jams.py build` and `blog.py build` regenerate `sitemap.xml` through `sitemap()` in `bin/jams.py`, which lists the fixed pages plus every generated blog page. Add new top-level pages there.
- **Styles.** Each page carries its own CSS with the same tokens (`--ink`, `--pink`, `--yellow`, `--violet`, fonts). The blog's CSS is in `bin/blog.py`. A brand change means updating the home page, the calendar page and `blog.py`.
- **Calendar `.ics` output** is produced in two places: `feed()` in `bin/jams.py` (full feed) and `ics()` in `calendars/index.html` (single event download). Change both.
- **Form validation** exists in the browser (`index.html`) and in the Lambda (`infra/bin/app.js`).
- **Untrusted text.** Jam names come from itch.io. The calendar page builds the page with `textContent` and checks URLs with `safeUrl()`; keep it that way.

## Infrastructure (`infra/`)

AWS CDK in plain JavaScript, region `ap-south-1`.

- `IndieGoPunkInterestStack`: the interest form backend, one Lambda behind a public function URL that writes to the DynamoDB table `IndieGoPunkInterest`. The function URL is hardcoded as `JOIN_URL` in `index.html`.
- `IndieGoPunkAssetsStack`: an S3 bucket where only `public/*` is world readable, used for social media assets.

```bash
cd infra && npm install
npx cdk diff
npx cdk deploy IndieGoPunkInterestStack     # or IndieGoPunkAssetsStack
```

Both stacks retain their data if destroyed.

## Contributing

- Never push to `main`; it is the live site.
- Branch from an up-to-date `main` (`git switch -c post/my-post origin/main`), commit, push the branch, and open a pull request into `main`.
- Commit messages follow `area: short lowercase summary`, for example `blog: post on shipping Third Law` or `calendars: add Global Game Jam 2027`.
- Wait for CI to pass and for a review before merging. Delete the branch after merging.
