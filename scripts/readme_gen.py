#!/usr/bin/env python3
"""
Generates every SVG used by the profile README.

  python scripts/readme_gen.py            # uses GitHub's API when GH_TOKEN is set,
                                          # otherwise falls back to data/snapshot.json

No third-party packages needed. Fonts are pre-subset and stored in scripts/fonts.json.
"""
import base64, collections, datetime as dt, html, json, math, os, random, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, 'assets')
LOGIN = os.environ.get('GH_LOGIN', 'Usama01TN')

# ---------------------------------------------------------------- palette ---
NIGHT1, NIGHT2 = '#0E0B2B', '#2A1A5E'
CARD, CARD2, STROKE = '#16113A', '#1E1850', '#3A2F7A'
TEXT, MUTED, DIM = '#F4F1FF', '#A9A3D6', '#6D66A3'
AMBER, CYAN, PINK, MINT, VIOLET, BLUE = '#FFB547', '#4FD8EB', '#FF6FA3', '#7BE3B5', '#9B8CFF', '#5C7CFA'
DUCK, DUCK_SHADE, BEAK = '#FFD34D', '#F2B92B', '#FF8A3D'
RAMP = ['#231C52', '#2E3A8A', '#3D68C2', '#47A2DD', '#4FD8EB']   # heatmap levels

FONTS = json.load(open(os.path.join(os.path.dirname(__file__), 'fonts.json')))
DISPLAY = "'Unbounded','Segoe UI',Arial,sans-serif"
MONO = "'JBMono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"


def font_css(*keys):
    out = []
    for k in keys:
        fam, w = k.split('-')
        fam = 'Unbounded' if fam == 'Unbounded' else 'JBMono'
        out.append(f"@font-face{{font-family:'{fam}';font-weight:{w};"
                   f"src:url(data:font/woff2;base64,{FONTS[k]['woff2']}) format('woff2')}}")
    return ''.join(out)


def tw(text, key, size):
    """Text width in px using the real font metrics."""
    w = FONTS[key]['widths']
    return sum(w.get(c, 0.6) for c in text) * size


def esc(s):
    return html.escape(str(s), quote=True)


def wrap(text, key, size, maxw, max_lines=3):
    words, lines, cur = text.split(), [], ''
    for word in words:
        trial = (cur + ' ' + word).strip()
        if tw(trial, key, size) <= maxw:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        while tw(lines[-1] + '…', key, size) > maxw:
            lines[-1] = lines[-1].rsplit(' ', 1)[0]
        lines[-1] += '…'
    return lines


def kt(total, *times):
    return ';'.join(f'{min(max(t / total, 0), 1):.4f}' for t in times)


# Spacing system. Each section is ONE image whose grid is laid out inside the SVG, so the gaps
# between cards are exact (GAP units) and can't be changed by how GitHub flows inline images.
GAP = 20


def svg_doc(w, h, label, body, fonts=('Unbounded-700', 'JBMono-400'), extra_css='', pad=(0, 0, 0, 0)):
    pl, pr, pt, pb = pad
    W, H = w + pl + pr, h + pt + pb
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
            f'role="img" aria-label="{esc(label)}"><title>{esc(label)}</title>'
            f'<style>{font_css(*fonts)}.d{{font-family:{DISPLAY}}}.m{{font-family:{MONO}}}'
            f'.pre{{white-space:pre}}{extra_css}</style><g transform="translate({pl} {pt})">{body}</g></svg>')


def save(name, content):
    path = os.path.join(ASSETS, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'  wrote {name:28s} {len(content) // 1024:>4} KB')


def card_bg(w, h, glow=CYAN, gid='g'):
    return (f'<defs><radialGradient id="{gid}" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" '
            f'gradientTransform="translate(0 0) scale({w * .75} {h * 1.1})">'
            f'<stop offset="0" stop-color="{glow}" stop-opacity=".16"/><stop offset="1" stop-color="{glow}" stop-opacity="0"/>'
            f'</radialGradient></defs>'
            f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="20" fill="{CARD}"/>'
            f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="20" fill="url(#{gid})"/>'
            f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="20" fill="none" stroke="{STROKE}" stroke-width="1.5"/>')


def star_path(cx, cy, r, fill):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * .45
        pts.append(f'{cx + rr * math.cos(a):.1f},{cy + rr * math.sin(a):.1f}')
    return f'<polygon points="{" ".join(pts)}" fill="{fill}"/>'


def sky(w, h, n, seed, ymax=None, twinkle=True):
    rnd = random.Random(seed)
    out = []
    for i in range(n):
        x, y = rnd.uniform(10, w - 10), rnd.uniform(10, ymax or h - 10)
        r = rnd.choice([.7, .9, 1.1, 1.4])
        op = rnd.uniform(.35, .9)
        a = ''
        if twinkle and i % 3 == 0:
            a = (f'<animate attributeName="opacity" values="{op:.2f};.1;{op:.2f}" '
                 f'dur="{rnd.uniform(2.5, 5):.1f}s" begin="{rnd.uniform(0, 3):.1f}s" repeatCount="indefinite"/>')
        out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="#FFFFFF" opacity="{op:.2f}">{a}</circle>')
    return ''.join(out)


def shooting_star(x, y, uid, period=7.0, begin=0.0):
    return (f'<defs><linearGradient id="{uid}" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
            f'<stop offset="1" stop-color="#fff" stop-opacity=".9"/></linearGradient></defs>'
            f'<g opacity="0"><animate attributeName="opacity" values="0;1;0;0" keyTimes="0;.04;.12;1" dur="{period}s" begin="{begin}s" repeatCount="indefinite"/>'
            f'<animateTransform attributeName="transform" type="translate" values="0 0;-160 80;-160 80" keyTimes="0;.12;1" dur="{period}s" begin="{begin}s" repeatCount="indefinite"/>'
            f'<line x1="{x + 70}" y1="{y - 35}" x2="{x}" y2="{y}" stroke="url(#{uid})" stroke-width="2" stroke-linecap="round" transform="rotate(180 {x + 35} {y - 17.5})"/>'
            f'<circle cx="{x + 70}" cy="{y - 35}" r="1.8" fill="#fff" transform="rotate(180 {x + 35} {y - 17.5})"/></g>')


def duck(walking=False, scale=1.0):
    """An original rubber duck, drawn facing right, origin at its feet."""
    feet = ''
    if walking:
        feet = (f'<ellipse cx="-6" cy="0" rx="7" ry="2.6" fill="{BEAK}">'
                f'<animate attributeName="cx" values="-9;-2;-9" dur=".5s" repeatCount="indefinite"/></ellipse>'
                f'<ellipse cx="6" cy="0" rx="7" ry="2.6" fill="{BEAK}">'
                f'<animate attributeName="cx" values="2;9;2" dur=".5s" repeatCount="indefinite"/></ellipse>')
    return (f'<g transform="scale({scale})">{feet}'
            f'<path d="M-24,-20 L-34,-33 L-18,-27 Z" fill="{DUCK_SHADE}"/>'
            f'<ellipse cx="0" cy="-17" rx="25" ry="15" fill="{DUCK}"/>'
            f'<ellipse cx="-4" cy="-17" rx="12" ry="7" fill="{DUCK_SHADE}"/>'
            f'<circle cx="12" cy="-37" r="12.5" fill="{DUCK}"/>'
            f'<path d="M22,-40 Q37,-37 23,-31 Q20,-35 22,-40 Z" fill="{BEAK}"/>'
            f'<circle cx="15.5" cy="-40" r="2.3" fill="#1A1033"/><circle cx="16.3" cy="-40.8" r=".8" fill="#fff"/>'
            f'</g>')


# ------------------------------------------------------------------- data ---
GQL = '''query($login:String!){user(login:$login){name login followers{totalCount}
repositories(ownerAffiliations:OWNER,first:100,privacy:PUBLIC,orderBy:{field:STARGAZERS,direction:DESC}){
 nodes{name description stargazerCount isFork pushedAt primaryLanguage{name}
  languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name}}}
  repositoryTopics(first:20){nodes{topic{name}}}}}
contributionsCollection{contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}'''


def load_data():
    token = os.environ.get('GH_TOKEN')
    snap_path = os.path.join(ROOT, 'data', 'snapshot.json')
    if token:
        try:
            return fetch_live(token, snap_path)
        except Exception as e:  # keep yesterday's data rather than break the page
            print(f'  GitHub API failed ({e}); using data/snapshot.json')
    else:
        print('  GH_TOKEN not set, using data/snapshot.json')
    return json.load(open(snap_path))


def fetch_live(token, snap_path):
    if True:
        req = urllib.request.Request('https://api.github.com/graphql',
                                     data=json.dumps({'query': GQL, 'variables': {'login': LOGIN}}).encode(),
                                     headers={'Authorization': f'bearer {token}', 'Content-Type': 'application/json'})
        u = json.load(urllib.request.urlopen(req, timeout=60))['data']['user']
        data = {'login': u['login'], 'name': u['name'] or u['login'], 'followers': u['followers']['totalCount'],
                'repos': [{'name': r['name'], 'description': r['description'] or '', 'stars': r['stargazerCount'],
                           'fork': r['isFork'], 'language': (r['primaryLanguage'] or {}).get('name'),
                           'pushedAt': r.get('pushedAt'),
                           'languages': {e['node']['name']: e['size'] for e in (r.get('languages') or {}).get('edges', [])},
                           'topics': [t['topic']['name'] for t in (r.get('repositoryTopics') or {}).get('nodes', [])]}
                          for r in u['repositories']['nodes']],
                'calendar': [{'date': d['date'], 'count': d['contributionCount']}
                             for w in u['contributionsCollection']['contributionCalendar']['weeks']
                             for d in w['contributionDays']],
                'source': 'GitHub API ' + dt.date.today().isoformat()}
        os.makedirs(os.path.dirname(snap_path), exist_ok=True)
        json.dump(data, open(snap_path, 'w'), indent=1)
        return data


# ------------------------------------------------------------ type scale ---
# One scale for every image. Images render at roughly 0.8x on GitHub, so nothing goes below 13.
T_TITLE, T_SUB, T_BODY, T_SMALL = 19, 13.5, 14, 13
INSET = 28  # inner padding of every card


TODAY = dt.date.today()


def ago(iso):
    if not iso:
        return ''
    d = (TODAY - dt.date.fromisoformat(iso[:10])).days
    if d <= 0:
        return 'today'
    if d == 1:
        return 'yesterday'
    if d < 14:
        return f'{d} days ago'
    if d < 60:
        return f'{d // 7} weeks ago'
    if d < 365:
        return f'{d // 30} months ago'
    return f'{d // 365} year{"s" if d >= 730 else ""} ago'


def own_repos(data):
    return [r for r in data['repos'] if not r['fork'] and r['name'].lower() != data['login'].lower()]


def card_title(title, sub, w, right=None, right_sub=None):
    out = (f'<text x="{INSET}" y="56" class="d" font-size="{T_TITLE}" font-weight="700" fill="{TEXT}">{esc(title)}</text>'
           f'<text x="{INSET}" y="82" class="m pre" font-size="{T_SUB}" fill="{MUTED}">{esc(sub)}</text>')
    if right is not None:
        out += (f'<text x="{w - INSET}" y="56" text-anchor="end" class="d" font-size="{T_TITLE}" font-weight="700" fill="{CYAN}">{esc(right)}</text>'
                f'<text x="{w - INSET}" y="82" text-anchor="end" class="m" font-size="{T_SUB}" fill="{MUTED}">{esc(right_sub)}</text>')
    return out


# --------------------------------------------------------------- headers ---
def sections(data):
    """Section banners. Subtitles are built from live data where it makes sense."""
    return [  # (id, glyph, accent, title, subtitle)
        ('about', '{ }', CYAN, 'About me', 'desktop, mobile and web, often from one codebase'),
        ('projects', '</>', PINK, "Things I've built", 'open source, for desktop, mobile and the web'),
        ('toolbox', '#', AMBER, 'Toolbox', 'languages, frameworks and platforms, picked up from my repos daily'),
        ('stats', '%', MINT, 'By the numbers', f'redrawn every day, last run {TODAY.strftime("%d %b %Y")}'),
        ('support', '<3', PINK, 'Support my work', 'optional, appreciated, mostly converted into coffee'),
        ('contact', '@', VIOLET, "Let's talk", 'freelance, collaborations, well-written bug reports'),
    ]


def make_headers(data):
    W, H = 1000, 64
    for sid, glyph, accent, title, sub in sections(data):
        for mode, tcol, scol in (('dark', TEXT, MUTED), ('light', '#16113A', '#5B5591')):
            tx = 64
            line_x = tx + tw(title, 'Unbounded-700', 24) + 24
            b = (f'<defs><linearGradient id="hl" x1="0" x2="1"><stop offset="0" stop-color="{accent}"/>'
                 f'<stop offset="1" stop-color="{accent}" stop-opacity="0"/></linearGradient></defs>'
                 f'<rect x="0" y="8" width="48" height="48" rx="14" fill="{accent}" fill-opacity=".14" stroke="{accent}" stroke-opacity=".55"/>'
                 f'<text x="24" y="38" text-anchor="middle" class="m" font-size="17" fill="{accent}">{esc(glyph)}</text>'
                 f'<text x="{tx}" y="33" class="d" font-size="24" font-weight="700" fill="{tcol}">{esc(title)}</text>'
                 f'<text x="{tx}" y="57" class="m" font-size="{T_SUB}" fill="{scol}">{esc(sub)}</text>'
                 f'<rect x="{line_x:.0f}" y="24" width="{W - line_x:.0f}" height="2" rx="1" fill="url(#hl)"/>')
            save(f'headers/{sid}-{mode}.svg', svg_doc(W, H, title, b))


# --------------------------------------------------------------- projects ---
PROJECTS = [  # (repo, icon, accent, one-liner) -- edit freely, keep one-liners under ~50 characters
    ('OcrRoute', 'ocr', CYAN, "One engine can't read it? Another will."),
    ('QuizKey', 'key', PINK, 'For studying. Strictly for studying.'),
    ('ManyQt', 'layers', VIOLET, 'Six Qt bindings, zero arguments about which one.'),
    ('QFunnyWidgets', 'toggle', MINT, 'Widgets with a sense of humour.'),
    ('TheWalkingDuckTaskBar', 'duck', AMBER, 'The most important software I have ever shipped.'),
    ('PyQtBuilder', 'box', BLUE, "Turns 'works on my machine' into 'works on yours'."),
    ('QRemoteDisplay', 'remote', CYAN, 'Your other computer, now in a window.'),
    ('MiniRDPBlocker', 'shield', PINK, 'The bouncer your server deserves.'),
]
FALLBACK_DESC = {'QRemoteDisplay': 'A simple RDP connector for Python, built on PyFreeRdpNative and ManyQt.'}
CARD_W = (1000 - GAP) // 2   # 490
CARD_H = 236


def icon(kind, c):
    s = f'stroke="{c}" stroke-width="2.2" fill="none" stroke-linecap="round" stroke-linejoin="round"'
    if kind == 'ocr':
        return (f'<rect x="17" y="12" width="22" height="32" rx="3" {s}/><path d="M22 20h12M22 26h12M22 32h8" {s}/>'
                f'<line x1="11" x2="45" y1="16" y2="16" stroke="{c}" stroke-width="2"><animate attributeName="y1" values="14;42;14" dur="3s" repeatCount="indefinite"/>'
                f'<animate attributeName="y2" values="14;42;14" dur="3s" repeatCount="indefinite"/></line>')
    if kind == 'key':
        return (f'<rect x="11" y="13" width="34" height="30" rx="7" {s}/><rect x="15" y="16" width="26" height="19" rx="4" {s}/>'
                f'<text x="28" y="30" text-anchor="middle" class="m" font-size="12" fill="{c}">Q</text>')
    if kind == 'layers':
        return (f'<rect x="10" y="24" width="26" height="20" rx="3" fill="{CARD}" {s.replace("fill=\"none\" ", "")}/>'
                f'<rect x="16" y="18" width="26" height="20" rx="3" fill="{CARD}" {s.replace("fill=\"none\" ", "")}/>'
                f'<rect x="22" y="12" width="26" height="20" rx="3" fill="{CARD}" {s.replace("fill=\"none\" ", "")}/>')
    if kind == 'toggle':
        return (f'<rect x="10" y="19" width="36" height="18" rx="9" {s}/><circle cx="19" cy="28" r="5.5" fill="{c}">'
                f'<animate attributeName="cx" values="19;19;37;37;19" keyTimes="0;.35;.5;.85;1" dur="3s" repeatCount="indefinite"/></circle>')
    if kind == 'duck':
        return (f'<g transform="translate(26 46)"><g><animateTransform attributeName="transform" type="rotate" '
                f'values="-6;6;-6" dur="1.6s" repeatCount="indefinite"/>{duck(scale=.62)}</g></g>')
    if kind == 'box':
        return f'<path d="M28 10 44 19v18L28 46 12 37V19Z M12 19l16 9 16-9 M28 28v18" {s}/>'
    if kind == 'remote':
        return (f'<rect x="10" y="13" width="36" height="24" rx="3" {s}/><path d="M22 44h12M28 37v7" {s}/>'
                f'<path d="M21 25l5 4 9-9" {s}/>')
    if kind == 'shield':
        return f'<path d="M28 10 44 16v11c0 10-7 16-16 19-9-3-16-9-16-19V16Z" {s}/><path d="M23 23l10 10M33 23 23 33" {s}/>'
    return ''


def project_card(r, name, kind, accent, joke, gid):
    W, H = CARD_W, CARD_H
    inner = W - 2 * INSET
    desc = FALLBACK_DESC.get(name) or r['description'] or ''
    if desc.lower().startswith('about '):
        desc = desc[6:]
    size = T_TITLE
    while tw(name, 'Unbounded-700', size) > W - 104 - INSET and size > 13:
        size -= .5
    lines = wrap(desc, 'JBMono-400', T_BODY, inner, 3)
    joke = wrap(joke, 'JBMono-400', T_SMALL, inner, 1)[0]
    lang = r.get('language') or 'Code'
    star_x = 116 + tw(lang, 'JBMono-400', T_SMALL) + 20
    b = [card_bg(W, H, accent, gid),
         f'<rect x="{INSET}" y="{INSET}" width="56" height="56" rx="16" fill="{accent}" fill-opacity=".12" stroke="{accent}" stroke-opacity=".45"/>',
         f'<g transform="translate({INSET} {INSET})">{icon(kind, accent)}</g>',
         f'<text x="104" y="54" class="d" font-size="{size}" font-weight="700" fill="{TEXT}">{esc(name)}</text>',
         f'<circle cx="109" cy="75" r="5" fill="{accent}"/>',
         f'<text x="120" y="80" class="m" font-size="{T_SMALL}" fill="{MUTED}">{esc(lang)}</text>',
         star_path(star_x + 7, 74.5, 7.5, AMBER),
         f'<text x="{star_x + 20:.0f}" y="80" class="m" font-size="{T_SMALL}" fill="{MUTED}">{r.get("stars", 0)}</text>']
    for i, line in enumerate(lines):
        b.append(f'<text x="{INSET}" y="{124 + i * 22}" class="m" font-size="{T_BODY}" fill="{TEXT}" fill-opacity=".88">{esc(line)}</text>')
    b.append(f'<text x="{INSET}" y="{H - INSET}" class="m" font-size="{T_SMALL}" fill="{accent}">{esc(joke)}</text>')
    if r.get('pushedAt'):
        b.append(f'<text x="{W - INSET}" y="80" text-anchor="end" class="m" font-size="{T_SMALL}" fill="{DIM}">updated {ago(r["pushedAt"])}</text>')
    return ''.join(b), f'{name}: {desc}'


FEATURED = 8
GENERIC_ICONS = ['box', 'layers', 'remote', 'ocr', 'key', 'toggle', 'shield', 'duck']


def featured(data):
    """The PROJECTS list, minus repos that no longer exist, topped up with the most-starred others."""
    repos = {r['name']: r for r in own_repos(data)}
    out = [(n, k, c, j) for n, k, c, j in PROJECTS if n in repos][:FEATURED]
    taken = {n for n, *_ in out}
    extra = sorted((r for r in repos.values() if r['name'] not in taken and (r['description'] or r['stars'])),
                   key=lambda r: (-r['stars'], r.get('pushedAt') or ''))
    cols = [CYAN, PINK, AMBER, MINT, VIOLET, BLUE]
    for i, r in enumerate(extra[:FEATURED - len(out)]):
        out.append((r['name'], GENERIC_ICONS[i % len(GENERIC_ICONS)], cols[i % len(cols)], 'Open source, as always.'))
    return out


def make_projects(data):
    repos = {r['name']: r for r in data['repos']}
    feats = featured(data)
    rows = math.ceil(len(feats) / 2)
    W, H = 1000, rows * CARD_H + (rows - 1) * GAP
    body, labels = [], []
    for i, (name, kind, accent, joke) in enumerate(feats):
        card, label = project_card(repos[name], name, kind, accent, joke, f'cg{i}')
        x, y = (i % 2) * (CARD_W + GAP), (i // 2) * (CARD_H + GAP)
        body.append(f'<g transform="translate({x} {y})">{card}</g>')
        labels.append(label)
    save('projects.svg', svg_doc(W, H, 'Projects. ' + ' '.join(labels), ''.join(body)))
    return [n for n, *_ in feats]


# -------------------------------------------------- badges and toolbox ---
def badge(label, value, color, name, logo=None):
    """A self-hosted badge. No third-party service, so it still renders in 2050."""
    h, fs = 28, 12.5
    lw = tw(label, 'JBMono-700', fs) + 24 + (22 if logo else 0)
    vw = tw(value, 'JBMono-400', fs) + 24
    W = lw + vw
    body = (f'<defs><clipPath id="b"><rect width="{W:.0f}" height="{h}" rx="6"/></clipPath></defs>'
            f'<g clip-path="url(#b)"><rect width="{lw:.0f}" height="{h}" fill="{CARD}"/>'
            f'<rect x="{lw:.0f}" width="{vw:.0f}" height="{h}" fill="{color}"/></g>'
            f'<rect x=".5" y=".5" width="{W - 1:.0f}" height="{h - 1}" rx="6" fill="none" stroke="{STROKE}"/>'
            + (f'<g transform="translate(10 7)">{logo}</g>' if logo else '')
            + f'<text x="{12 + (22 if logo else 0)}" y="18.5" class="m" font-size="{fs}" font-weight="700" fill="{TEXT}" textLength="{tw(label, "JBMono-700", fs):.1f}" lengthAdjust="spacingAndGlyphs">{esc(label)}</text>'
            f'<text x="{lw + 12:.0f}" y="18.5" class="m" font-size="{fs}" fill="{NIGHT1}" textLength="{tw(value, "JBMono-400", fs):.1f}" lengthAdjust="spacingAndGlyphs">{esc(value)}</text>')
    save(f'badges/{name}.svg', svg_doc(math.ceil(W), h, f'{label}: {value}', body, fonts=('JBMono-400', 'JBMono-700')))


LOGO_MAIL = f'<rect x="0" y="2" width="14" height="10" rx="2" fill="none" stroke="{TEXT}" stroke-width="1.4"/><path d="M1 4l6 4 6-4" fill="none" stroke="{TEXT}" stroke-width="1.4"/>'
LOGO_CUP = f'<path d="M1 3h9v5a3.5 3.5 0 0 1-7 0V3z" fill="none" stroke="{TEXT}" stroke-width="1.4"/><path d="M10 4.5h1.5a1.75 1.75 0 0 1 0 3.5H10" fill="none" stroke="{TEXT}" stroke-width="1.4"/><path d="M2 12.5h8" stroke="{TEXT}" stroke-width="1.4"/>'
LOGO_HEART = f'<path d="M7 12.5L2 7.6A2.9 2.9 0 0 1 7 3.9a2.9 2.9 0 0 1 5 3.7z" fill="none" stroke="{TEXT}" stroke-width="1.4"/>'
LOGO_PEOPLE = f'<circle cx="5" cy="4.5" r="2.5" fill="none" stroke="{TEXT}" stroke-width="1.4"/><path d="M1 12.5a4 4 0 0 1 8 0" fill="none" stroke="{TEXT}" stroke-width="1.4"/><circle cx="10.5" cy="5" r="2" fill="none" stroke="{TEXT}" stroke-width="1.3"/><path d="M10 12.5h3.5a3 3 0 0 0-2.5-3.4" fill="none" stroke="{TEXT}" stroke-width="1.3"/>'


def make_badges(data):
    badge('Email', 'ininou.oussematn@gmail.com', PINK, 'email', LOGO_MAIL)
    badge('Followers', f'{data["followers"]:,}', VIOLET, 'followers', LOGO_PEOPLE)
    badge('Ko-fi', 'Buy me a coffee', AMBER, 'kofi', LOGO_CUP)
    badge('Ba9chich', 'Leave a tip', CYAN, 'ba9chich', LOGO_HEART)


# ------------------------------------------------------------- toolbox ---
# The toolbox is an automatic icon grid. Every run it looks at your public repos (languages
# GitHub detects, topics, names and descriptions), merges what it finds with the BASELINE you
# declare below, and draws one icon tile per item. Push a Rust repo tomorrow and a Rust tile
# appears the day after, with no edit to this file.
#
# Icons come from Simple Icons (CC0) and, for brands Simple Icons doesn't carry (Windows, C#,
# Java...), from Devicon (MIT). Both are pinned versions, downloaded only when a NEW item needs
# an icon, and cached in data/icons.json, so a normal daily run makes no extra network calls.
# Anything without an icon still gets a tile, drawn as a monogram.
SIMPLE_ICONS = '16.33.0'
DEVICON = 'v2.17.0'

TOOLBOX_GROUPS = [  # (group, accent)
    ('Languages', CYAN),
    ('Frameworks', PINK),
    ('Platforms', MINT),
]
BASELINE = {  # always shown, even before any public repo proves it
    'Languages': ['C++', 'Python', 'TypeScript', 'JavaScript', 'HTML', 'CSS'],
    'Frameworks': ['Qt', 'PyQt', 'PySide', 'React', 'Node.js'],
    'Platforms': ['Windows', 'macOS', 'Linux', 'Android', 'iOS'],
}
HIDDEN = {'Makefile', 'CMake', 'QMake', 'Batchfile', 'Dockerfile', 'Procfile', 'Roff', 'Jupyter Notebook',
          'Inno Setup', 'NSIS', 'Smarty', 'Mako', 'Jinja', 'SCSS', 'Less'}   # never shown as tiles
LANG_SHARE = .10  # a language counts for a repo when it's the primary one or at least 10% of its code
# Keyword rules for frameworks and platforms: regexes matched as whole words against each repo's
# name (also split on CamelCase), description and topics. Add a line to teach it something new.
DETECT = {
    'Frameworks': [
        ('Qt', r'qt\d?|qml|qss|qtquick|pyqt\d?|pyside\d?'),
        ('PyQt', r'pyqt\d?'),
        ('PySide', r'pyside\d?'),
        ('React', r'react|reactjs|react native|jsx'),
        ('Node.js', r'node|nodejs|node js|npm'),
        ('Express', r'express|expressjs'),
        ('Electron', r'electron'),
        ('Vue.js', r'vue|vuejs'),
        ('Next.js', r'next js|nextjs'),
        ('Flask', r'flask'),
        ('Django', r'django'),
        ('FastAPI', r'fastapi'),
        ('Flutter', r'flutter'),
        ('Tailwind CSS', r'tailwind|tailwindcss'),
        ('Bootstrap', r'bootstrap'),
        ('jQuery', r'jquery'),
        ('OpenCV', r'opencv|cv2'),
        ('.NET', r'dotnet|\.net'),
    ],
    'Platforms': [
        ('Windows', r'windows|win32|win64|winapi|taskbar'),
        ('macOS', r'macos|mac os|osx|os x'),
        ('Linux', r'linux|ubuntu|debian|fedora|arch linux'),
        ('Android', r'android|apk'),
        ('iOS', r'ios|iphone|ipad'),
    ],
}
# How a name maps to an icon: 'slug' = Simple Icons, 'devicon:name' = Devicon,
# a tuple = main icon plus a small badge icon. Unlisted names are looked up by title automatically.
ICON_ALIASES = {
    'C++': 'cplusplus', 'HTML': 'html5', 'Shell': 'gnubash', 'Node.js': 'nodedotjs',
    'PyQt': ('qt', 'python'), 'PySide': ('qt', 'python'),
    'macOS': 'apple', 'iOS': 'apple', 'Windows': 'devicon:windows11', 'C#': 'devicon:csharp', 'Java': 'devicon:java',
    'PowerShell': 'devicon:powershell', 'Visual Basic .NET': 'devicon:visualbasic',
    'Objective-C': 'devicon:objectivec', 'Assembly': 'devicon:embeddedc',
}
SHORT_LABEL = {'Tailwind CSS': 'Tailwind', 'Visual Basic .NET': 'VB.NET', 'Objective-C': 'Obj-C'}


def _words(repo):
    """Lower-case text of a repo for keyword matching, with CamelCase and separators split."""
    import re
    name = repo['name']
    camel = re.sub(r'(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])', ' ', name)
    parts = [name, camel, repo.get('description') or '', ' '.join(repo.get('topics') or [])]
    text = ' '.join(parts).lower()
    return ' ' + re.sub(r'[_\-/,;:()\[\]|!?"]+', ' ', text) + ' '


def detect_toolbox(data):
    """{group: [(name, repo_count), ...]} merged from BASELINE and what the repos show."""
    import re
    own = own_repos(data)
    found = {g: collections.Counter() for g, _ in TOOLBOX_GROUPS}
    for r in own:
        langs = dict(r.get('languages') or {})
        total = sum(langs.values()) or 1
        used = {l for l, size in langs.items() if size / total >= LANG_SHARE}
        if r.get('language'):
            used.add(r['language'])
        for l in used - HIDDEN:
            found['Languages'][l] += 1
        text = _words(r)
        for group, rules in DETECT.items():
            for name, pattern in rules:
                if re.search(rf'(?<![a-z0-9])(?:{pattern})(?![a-z0-9])', text):
                    found[group][name] += 1
    out = {}
    for group, _ in TOOLBOX_GROUPS:
        base = BASELINE.get(group, [])
        names = list(dict.fromkeys(base + [n for n, _ in found[group].most_common()]))
        order = {n: i for i, n in enumerate(names)}
        names.sort(key=lambda n: (-found[group][n], order[n]))
        out[group] = [(n, found[group][n]) for n in names[:16]]
    return out


# ------------------------------------------------------------ icon cache ---
ICON_CACHE = os.path.join(ROOT, 'data', 'icons.json')
_SI = {}


def _simple_icons():
    """Simple Icons metadata and paths, from the pinned npm tarball. Downloaded at most once a run."""
    if not _SI:
        import io, re, tarfile
        url = f'https://registry.npmjs.org/simple-icons/-/simple-icons-{SIMPLE_ICONS}.tgz'
        print(f'  downloading simple-icons {SIMPLE_ICONS}')
        raw = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'readme-gen'}), timeout=60).read()
        with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as tar:
            meta = json.load(tar.extractfile('package/data/simple-icons.json'))
            paths = {}
            for m in tar.getmembers():
                if m.name.startswith('package/icons/') and m.name.endswith('.svg'):
                    svg = tar.extractfile(m).read().decode()
                    p = re.search(r'<path d="([^"]+)"', svg)
                    if p:
                        paths[m.name[14:-4]] = p.group(1)
        _SI['meta'] = {x['slug']: x for x in meta}
        _SI['title'] = {x['title'].lower(): x['slug'] for x in meta}
        _SI['paths'] = paths
    return _SI


def _si_icon(slug_or_title):
    si = _simple_icons()
    slug = slug_or_title if slug_or_title in si['meta'] else si['title'].get(slug_or_title.lower())
    if not slug or slug not in si['paths']:
        return None
    return {'src': f'simple-icons@{SIMPLE_ICONS}', 'viewBox': '0 0 24 24', 'color': '#' + si['meta'][slug]['hex'],
            'body': f'<path d="{si["paths"][slug]}"/>'}


def _devicon(name):
    import re
    for variant in ('original', 'plain'):
        url = f'https://raw.githubusercontent.com/devicons/devicon/{DEVICON}/icons/{name}/{name}-{variant}.svg'
        try:
            svg = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'readme-gen'}), timeout=30).read().decode()
        except Exception:
            continue
        vb = re.search(r'viewBox="([^"]+)"', svg)
        body = re.sub(r'^.*?<svg[^>]*>|</svg>\s*$', '', svg.strip(), flags=re.S)
        body = re.sub(r'<title>.*?</title>|<!--.*?-->', '', body, flags=re.S)
        return {'src': f'devicon@{DEVICON}', 'viewBox': vb.group(1) if vb else '0 0 128 128', 'color': None, 'body': body}
    return None


def _resolve(key):
    """One icon by alias key: Simple Icons slug/title, or 'devicon:name'."""
    if key.startswith('devicon:'):
        return _devicon(key[8:])
    return _si_icon(key) or _devicon(''.join(c for c in key.lower().replace('+', 'plus').replace('#', 'sharp') if c.isalnum()))


def load_icons(names):
    """Icons for every name, from data/icons.json; anything new is fetched once and cached."""
    try:
        cache = json.load(open(ICON_CACHE, encoding='utf-8'))
    except Exception:
        cache = {}
    if cache.get('_versions') != [SIMPLE_ICONS, DEVICON]:
        cache = {'_versions': [SIMPLE_ICONS, DEVICON]}
    keys = set()
    for n in names:
        alias = ICON_ALIASES.get(n, n)
        keys.update(alias if isinstance(alias, tuple) else [alias])
    missing = [k for k in sorted(keys) if k not in cache]
    for k in missing:
        try:
            cache[k] = _resolve(k)            # None is cached too, so a miss isn't retried daily
        except Exception as e:                # offline: draw a monogram today, try again tomorrow
            print(f'  icon for {k!r} unavailable ({e})')
    if missing:
        os.makedirs(os.path.dirname(ICON_CACHE), exist_ok=True)
        json.dump(cache, open(ICON_CACHE, 'w', encoding='utf-8'), indent=1, sort_keys=True)
    return cache


def readable(hexcol):
    """Brand colour, lightened just enough to read on the dark card (black logos turn light grey)."""
    r, g, b = (int(hexcol[i:i + 2], 16) / 255 for i in (1, 3, 5))
    min_lum = .55 if max(r, g, b) - min(r, g, b) < .12 else .16   # greys go light, colours stay colourful

    def lum(c):
        return sum(w * (v / 12.92 if v <= .03928 else ((v + .055) / 1.055) ** 2.4) for w, v in zip((.2126, .7152, .0722), c))
    t = 0
    while lum([v + (1 - v) * t for v in (r, g, b)]) < min_lum and t < .9:
        t += .05
    return '#' + ''.join(f'{round((v + (1 - v) * t) * 255):02X}' for v in (r, g, b))


def draw_icon(icon, x, y, size, uid):
    if icon['color']:   # Simple Icons: one path, filled with the brand colour
        return (f'<svg x="{x:.1f}" y="{y:.1f}" width="{size}" height="{size}" viewBox="{icon["viewBox"]}">'
                f'<g fill="{readable(icon["color"])}">{icon["body"]}</g></svg>')
    import re           # Devicon: full-colour artwork; prefix its ids so tiles can't clash
    body = re.sub(r'id="([^"]+)"', rf'id="{uid}-\1"', icon['body'])
    body = re.sub(r'url\(#([^)]+)\)', rf'url(#{uid}-\1)', body)
    body = re.sub(r'href="#([^"]+)"', rf'href="#{uid}-\1"', body)
    return f'<svg x="{x:.1f}" y="{y:.1f}" width="{size}" height="{size}" viewBox="{icon["viewBox"]}">{body}</svg>'


def make_toolbox(data):
    groups = detect_toolbox(data)
    icons = load_icons([n for items in groups.values() for n, _ in items])
    W = 1000
    tile_w, tile_h, gap, label_w = 84, 88, 10, 150
    per_row = (W - 2 * INSET - label_w + gap) // (tile_w + gap)
    body, y, k = [], INSET, 0
    for gi, (group, accent) in enumerate(TOOLBOX_GROUPS):
        items = groups[group]
        if not items:
            continue
        if gi:
            body.append(f'<line x1="{INSET}" x2="{W - INSET}" y1="{y - gap - 1}" y2="{y - gap - 1}" stroke="{STROKE}" stroke-opacity=".6"/>')
        seen = sum(1 for _, c in items if c)
        body.append(f'<rect x="{INSET}" y="{y + 30}" width="22" height="4" rx="2" fill="{accent}"/>'
                    f'<text x="{INSET}" y="{y + 22}" class="d" font-size="15" font-weight="700" fill="{TEXT}">{esc(group)}</text>'
                    f'<text x="{INSET}" y="{y + 56}" class="m" font-size="{T_SMALL}" fill="{MUTED}">{len(items)} total</text>'
                    f'<text x="{INSET}" y="{y + 74}" class="m" font-size="{T_SMALL}" fill="{DIM}">{seen} in my repos</text>')
        for i, (name, count) in enumerate(items):
            x = INSET + label_w + (i % per_row) * (tile_w + gap)
            ty = y + (i // per_row) * (tile_h + gap)
            label = SHORT_LABEL.get(name, name)
            fs = T_SMALL
            while tw(label, 'JBMono-400', fs) > tile_w - 10 and fs > 10:
                fs -= .5
            alias = ICON_ALIASES.get(name, name)
            main, badge_key = (alias if isinstance(alias, tuple) else (alias, None))
            ico, size = icons.get(main), 34
            ix, iy = x + (tile_w - size) / 2, ty + 14
            if ico:
                art = draw_icon(ico, ix, iy, size, f'i{k}')
                if badge_key and icons.get(badge_key):
                    art += (f'<circle cx="{ix + size + 1:.1f}" cy="{iy + size - 1:.1f}" r="11" fill="{CARD2}" stroke="{STROKE}"/>'
                            + draw_icon(icons[badge_key], ix + size - 8, iy + size - 10, 18, f'i{k}b'))
            else:     # no icon anywhere: a monogram in the group colour
                mono = ''.join(ch for ch in name if ch.isalnum() or ch in '#+')[:3]
                art = (f'<rect x="{ix:.1f}" y="{iy:.1f}" width="{size}" height="{size}" rx="9" fill="{accent}" fill-opacity=".15" stroke="{accent}" stroke-opacity=".6"/>'
                       f'<text x="{ix + size / 2:.1f}" y="{iy + size / 2 + 5:.1f}" text-anchor="middle" class="m" font-size="14" font-weight="700" fill="{accent}">{esc(mono)}</text>')
            tip = f'{name}: in {count} of my public repos' if count else name
            # visible by default (so it still shows where animation is off), faded in where it isn't
            delay = .15 + k * .045
            body.append(f'<g><title>{esc(tip)}</title>'
                        f'<animate attributeName="opacity" values="0;0;1" keyTimes="0;{kt(delay + .4, delay)};1" dur="{delay + .4:.2f}s" fill="freeze"/>'
                        f'<rect x="{x:.1f}" y="{ty:.1f}" width="{tile_w}" height="{tile_h}" rx="16" fill="{CARD2}" stroke="{STROKE}"/>'
                        f'{art}'
                        f'<text x="{x + tile_w / 2:.1f}" y="{ty + tile_h - 16}" text-anchor="middle" class="m" font-size="{fs}" fill="{TEXT}">{esc(label)}</text></g>')
            k += 1
        rows = math.ceil(len(items) / per_row)
        y += rows * tile_h + (rows - 1) * gap + 2 * gap + 1
    H = y - 2 * gap - 1 + INSET
    alt = 'Toolbox. ' + '. '.join(f'{g}: {", ".join(n for n, _ in groups[g])}' for g, _ in TOOLBOX_GROUPS if groups[g])
    save('toolbox.svg', svg_doc(W, H, alt, card_bg(W, H, AMBER, 'tg') + ''.join(body),
                                fonts=('Unbounded-700', 'JBMono-400', 'JBMono-700')))
    return alt


# ------------------------------------------------------------------ stats ---
def weekly(calendar):
    weeks = collections.OrderedDict()
    first = dt.date.fromisoformat(calendar[0]['date'])
    start = first - dt.timedelta(days=(first.weekday() + 1) % 7)       # back to Sunday
    for d in calendar:
        day = dt.date.fromisoformat(d['date'])
        col = (day - start).days // 7
        weeks.setdefault(col, {'start': start + dt.timedelta(weeks=col), 'total': 0, 'days': []})
        weeks[col]['total'] += d['count']
        weeks[col]['days'].append((day, d['count']))
    return list(weeks.values())


def nice_max(v):
    if v <= 4:
        return 4
    mag = 10 ** int(math.log10(v))
    for m in (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if m * mag >= v:
            return int(m * mag)


def smooth(points, floor=1e9):
    d = f'M{points[0][0]:.1f},{points[0][1]:.1f}'
    for i in range(len(points) - 1):
        p0 = points[max(i - 1, 0)]; p1 = points[i]; p2 = points[i + 1]; p3 = points[min(i + 2, len(points) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, min(p1[1] + (p2[1] - p0[1]) / 6, floor))
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, min(p2[1] - (p3[1] - p1[1]) / 6, floor))
        d += f' C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}'
    return d


def make_overview(data):
    total = sum(d['count'] for d in data['calendar'])
    originals = sum(1 for r in data['repos'] if not r['fork'])
    forks = len(data['repos']) - originals
    stars = sum(r['stars'] for r in data['repos'])
    fol = data['followers']
    tiles = [(total, 'contributions', 'in the last 12 months', CYAN),
             (len(data['repos']), 'public repos', f'{originals} originals, {forks} forks', PINK),
             (stars, 'stars earned', 'thank you, stargazers', AMBER),
             (fol, 'followers', f'hi, all {fol} of you' if fol <= 50 else 'hi, all of you', MINT)]
    W, H = 1000, 156
    tile_w = (W - 3 * GAP) / 4
    b = []
    for i, (num, label, sub, c) in enumerate(tiles):
        x = i * (tile_w + GAP)
        b.append(f'''<g transform="translate({x:.1f} 0)">
<rect x=".75" y=".75" width="{tile_w - 1.5:.1f}" height="{H - 1.5}" rx="20" fill="{CARD}" stroke="{STROKE}" stroke-width="1.5"/>
<rect x="24" y="24" width="28" height="4" rx="2" fill="{c}"/>
<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{.15 + i * .18:.2f}s" dur=".5s" fill="freeze"/>
<animateTransform attributeName="transform" type="translate" from="0 10" to="0 0" begin="{.15 + i * .18:.2f}s" dur=".5s" fill="freeze"/>
<text x="24" y="80" class="d" font-size="36" font-weight="700" fill="{c}">{num:,}</text></g>
<text x="24" y="109" class="m" font-size="15" fill="{TEXT}">{esc(label)}</text>
<text x="24" y="131" class="m" font-size="{T_SMALL}" fill="{MUTED}">{esc(sub)}</text></g>''')
    return ''.join(b), H, 'Profile overview: ' + ', '.join(f'{t[0]} {t[1]}' for t in tiles)


def make_activity(data):
    W, H = 1000, 370
    weeks = weekly(data['calendar'])
    vals = [w['total'] for w in weeks]
    total = sum(vals)
    top = nice_max(max(vals) or 1)
    x0, x1, y0, y1 = 76, W - INSET - 4, 124, 306
    pts = [(x0 + i * (x1 - x0) / (len(vals) - 1), y1 - v / top * (y1 - y0)) for i, v in enumerate(vals)]
    line = smooth(pts, floor=y1)
    area = line + f' L{x1},{y1} L{x0},{y1} Z'
    pk = max(range(len(vals)), key=lambda i: vals[i])
    px, py = pts[pk]
    b = [card_bg(W, H, VIOLET, 'ag'), f'''<defs>
<linearGradient id="ln" x1="0" x2="1"><stop offset="0" stop-color="{VIOLET}"/><stop offset=".6" stop-color="{CYAN}"/><stop offset="1" stop-color="{PINK}"/></linearGradient>
<linearGradient id="ar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{CYAN}" stop-opacity=".32"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/></linearGradient></defs>''',
         card_title('Contribution activity', 'commits, PRs, issues and reviews per week, last 12 months', W, f'{total:,}', 'total')]
    div = 4 if top % 4 == 0 else 3 if top % 3 == 0 else 5
    for k in range(div + 1):
        gy = y1 - k * (y1 - y0) / div
        b.append(f'<line x1="{x0}" x2="{x1}" y1="{gy:.1f}" y2="{gy:.1f}" stroke="{STROKE}" stroke-dasharray="3 5" opacity=".7"/>'
                 f'<text x="{x0 - 14}" y="{gy + 4.5:.1f}" text-anchor="end" class="m" font-size="{T_SMALL}" fill="{DIM}">{int(top * k / div)}</text>')
    seen = set()
    for i, w in enumerate(weeks):
        firsts = [d for d, _ in w['days'] if d.day == 1]
        if firsts and 0 < i < len(weeks) - 1 and (firsts[0].year, firsts[0].month) not in seen:
            seen.add((firsts[0].year, firsts[0].month))
            b.append(f'<text x="{pts[i][0]:.0f}" y="{y1 + 30}" text-anchor="middle" class="m" font-size="{T_SMALL}" fill="{MUTED}">{firsts[0].strftime("%b")}</text>')
    b.append(f'''<path d="{area}" fill="url(#ar)" opacity="0"><animate attributeName="opacity" from="0" to="1" begin="1.4s" dur=".8s" fill="freeze"/></path>
<path d="{line}" fill="none" stroke="url(#ln)" stroke-width="3" stroke-linecap="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1">
<animate attributeName="stroke-dashoffset" from="1" to="0" dur="2.2s" begin=".2s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".4 0 .2 1"/></path>''')
    label, sub = f'peak week: {vals[pk]}', '(something was due)'
    lw = max(tw(label, 'JBMono-700', T_SMALL), tw(sub, 'JBMono-400', T_SMALL)) + 28
    lh = 50
    # put the label beside the peak, on whichever side has room
    lx = px - lw - 18 if px + lw + 18 > x1 else px + 18
    ly = min(max(py - lh / 2, y0 - 10), y1 - lh)
    b.append(f'''<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="2.2s" dur=".4s" fill="freeze"/>
<circle cx="{px:.1f}" cy="{py:.1f}" r="6" fill="{AMBER}"/>
<circle cx="{px:.1f}" cy="{py:.1f}" r="6" fill="none" stroke="{AMBER}" stroke-width="2"><animate attributeName="r" values="6;16" dur="1.8s" repeatCount="indefinite"/><animate attributeName="opacity" values=".9;0" dur="1.8s" repeatCount="indefinite"/></circle>
<rect x="{lx:.1f}" y="{ly:.1f}" width="{lw:.0f}" height="{lh}" rx="12" fill="{CARD2}" stroke="{AMBER}" stroke-opacity=".6"/>
<text x="{lx + 14:.1f}" y="{ly + 21:.1f}" class="m" font-size="{T_SMALL}" font-weight="700" fill="{AMBER}">{esc(label)}</text>
<text x="{lx + 14:.1f}" y="{ly + 39:.1f}" class="m" font-size="{T_SMALL}" fill="{MUTED}">{esc(sub)}</text></g>''')
    return ''.join(b), H, f'{total} contributions in the last 12 months, peak week {vals[pk]}'


def languages_card(data, W, H):
    cnt = collections.Counter(r['language'] for r in data['repos'] if r['language'] and not r['fork'])
    n = sum(cnt.values()) or 1
    items = cnt.most_common(5)
    other = n - sum(v for _, v in items)
    if other:
        items.append(('Other', other))
    colors = [CYAN, PINK, AMBER, MINT, VIOLET, DIM]
    cx, cy, r, sw = INSET + 84, 224, 76, 24
    C = 2 * math.pi * r
    lx0, lx1 = 236, W - INSET
    b = [card_bg(W, H, PINK, 'lg'), card_title('Languages', 'main language of my own repos', W),
         f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{CARD2}" stroke-width="{sw}"/>']
    start, t = 0, .2
    rows = len(items)
    row_h = min(36, (H - INSET - 130) / max(rows - 1, 1))
    for i, (name, v) in enumerate(items):
        seg = v / n * C
        dur = .35 + .9 * v / n
        b.append(f'''<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{colors[i]}" stroke-width="{sw}" stroke-dasharray="0 {C:.1f}" stroke-dashoffset="{-start:.1f}" transform="rotate(-90 {cx} {cy})">
<animate attributeName="stroke-dasharray" from="0 {C:.1f}" to="{max(seg - 3, .5):.1f} {C:.1f}" begin="{t:.2f}s" dur="{dur:.2f}s" fill="freeze"/></circle>''')
        start += seg
        t += dur
        y = 136 + i * row_h
        bw = lx1 - lx0
        b.append(f'''<circle cx="{lx0 + 5}" cy="{y - 5}" r="5" fill="{colors[i]}"/>
<text x="{lx0 + 18}" y="{y}" class="m" font-size="{T_BODY}" fill="{TEXT}">{esc(name)}</text>
<text x="{lx1}" y="{y}" text-anchor="end" class="m" font-size="{T_BODY}" fill="{MUTED}">{v / n * 100:.0f}%</text>
<rect x="{lx0}" y="{y + 9}" width="{bw}" height="4" rx="2" fill="{CARD2}"/>
<rect x="{lx0}" y="{y + 9}" width="0" height="4" rx="2" fill="{colors[i]}"><animate attributeName="width" from="0" to="{max(bw * v / n, 4):.1f}" begin="{.3 + i * .15:.2f}s" dur=".8s" fill="freeze"/></rect>''')
    b.append(f'<text x="{cx}" y="{cy + 7}" text-anchor="middle" class="d" font-size="28" font-weight="700" fill="{TEXT}">{n}</text>'
             f'<text x="{cx}" y="{cy + 29}" text-anchor="middle" class="m" font-size="{T_SMALL}" fill="{MUTED}">repos</text>')
    return ''.join(b), 'Languages: ' + ', '.join(f'{k} {v / n:.0%}' for k, v in items)


def weekdays_card(data, W, H):
    names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    tot = [0] * 7
    for d in data['calendar']:
        tot[dt.date.fromisoformat(d['date']).weekday()] += d['count']
    best = max(range(7), key=lambda i: tot[i])
    full = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][best]
    top = max(tot) or 1
    base, hmax, bw = H - 62, H - 196, 38
    step = (W - 2 * INSET - bw) / 6
    b = [card_bg(W, H, AMBER, 'wg'), card_title('When I code', f'{full}s win. Meetings lose.', W),
         f'<line x1="{INSET}" x2="{W - INSET}" y1="{base}" y2="{base}" stroke="{STROKE}"/>']
    for i, v in enumerate(tot):
        h = max(v / top * hmax, 3)
        x = INSET + i * step
        c = AMBER if i == best else VIOLET
        bt = .2 + i * .08
        b.append(f'''<rect x="{x:.1f}" y="{base}" width="{bw}" height="0" rx="8" fill="{c}" fill-opacity="{1 if i == best else .75}">
<animate attributeName="height" from="0" to="{h:.1f}" begin="{bt:.2f}s" dur=".7s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".3 0 .2 1"/>
<animate attributeName="y" from="{base}" to="{base - h:.1f}" begin="{bt:.2f}s" dur=".7s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".3 0 .2 1"/></rect>
<text x="{x + bw / 2:.1f}" y="{base - h - 10:.1f}" text-anchor="middle" class="m" font-size="{T_SMALL}" fill="{TEXT if i == best else MUTED}" opacity="0">{v}<animate attributeName="opacity" from="0" to="1" begin="{bt + .6:.2f}s" dur=".3s" fill="freeze"/></text>
<text x="{x + bw / 2:.1f}" y="{base + 28}" text-anchor="middle" class="m" font-size="{T_SMALL}" fill="{TEXT if i == best else MUTED}">{names[i]}</text>''')
    return ''.join(b), f'Contributions by weekday, busiest on {full}'


def make_breakdown(data):
    W, H = 1000, 370
    left, la = languages_card(data, CARD_W, H)
    right, ra = weekdays_card(data, CARD_W, H)
    body = f'<g>{left}</g><g transform="translate({CARD_W + GAP} 0)">{right}</g>'
    return body, H, f'{la}. {ra}'


def make_heatmap(data):
    W, H = 1000, 300
    weeks = weekly(data['calendar'])
    nz = sorted(d['count'] for d in data['calendar'] if d['count'])
    q = [nz[int(len(nz) * f)] for f in (.25, .5, .75)] if nz else [1, 2, 3]

    def level(v):
        return 0 if v == 0 else 1 + sum(v > t for t in q)

    cell, step = 13, 16
    gx = (W - len(weeks) * step + (step - cell)) / 2 + 18      # centred, nudged right for the day labels
    gy = 134
    lg_x = W - INSET - 5 * 17 - 40
    b = [card_bg(W, H, MINT, 'hg'),
         card_title('A year, square by square', 'not a snake. a duck. it checks on every commit and eats none of them.', W),
         f'<text x="{lg_x - 10}" y="56" text-anchor="end" class="m" font-size="{T_SMALL}" fill="{MUTED}">less</text>',
         f'<text x="{W - INSET}" y="56" text-anchor="end" class="m" font-size="{T_SMALL}" fill="{MUTED}">more</text>']
    for i, c in enumerate(RAMP):
        b.append(f'<rect x="{lg_x + i * 17}" y="45" width="13" height="13" rx="3.5" fill="{c}"/>')
    for r_, name in ((1, 'Mon'), (3, 'Wed'), (5, 'Fri')):
        b.append(f'<text x="{gx - 12:.0f}" y="{gy + r_ * step + 11}" text-anchor="end" class="m" font-size="{T_SMALL}" fill="{DIM}">{name}</text>')
    seen = set()
    for i, w in enumerate(weeks):
        x = gx + i * step
        firsts = [d for d, _ in w['days'] if d.day == 1]
        if firsts and 1 < i < len(weeks) - 2 and (firsts[0].year, firsts[0].month) not in seen:
            seen.add((firsts[0].year, firsts[0].month))
            b.append(f'<text x="{x:.0f}" y="{gy - 12}" class="m" font-size="{T_SMALL}" fill="{DIM}">{firsts[0].strftime("%b")}</text>')
        cells = ''.join(
            f'<rect x="{x:.0f}" y="{gy + ((d.weekday() + 1) % 7) * step}" width="{cell}" height="{cell}" rx="3.5" fill="{RAMP[level(v)]}"><title>{v} on {d.isoformat()}</title></rect>'
            for d, v in w['days'])
        b.append(f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{i * .025:.3f}s" dur=".3s" fill="freeze"/>{cells}</g>')
    ground = H - 22
    b.append(f'''<line x1="{INSET}" x2="{W - INSET}" y1="{ground}" y2="{ground}" stroke="{STROKE}" stroke-dasharray="2 6"/>
<g><animateTransform attributeName="transform" type="translate" values="-40 {ground};{W + 40} {ground}" dur="18s" repeatCount="indefinite"/>
<g><animateTransform attributeName="transform" type="translate" values="0 0;0 -2.5;0 0" dur=".5s" repeatCount="indefinite"/>{duck(walking=True, scale=.62)}</g></g>''')
    body = f'<defs><clipPath id="hm"><rect width="{W}" height="{H}" rx="20"/></clipPath></defs><g clip-path="url(#hm)">{"".join(b)}</g>'
    return body, H, 'Contribution calendar for the last 12 months'


# ----------------------------------------------------------------- footer ---
def make_footer():
    W, H = 1000, 230
    b = f'''<defs><clipPath id="fc"><rect width="{W}" height="{H}" rx="24"/></clipPath>
<linearGradient id="fbg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{NIGHT2}"/><stop offset="1" stop-color="{NIGHT1}"/></linearGradient></defs>
<g clip-path="url(#fc)"><rect width="{W}" height="{H}" fill="url(#fbg)"/>{sky(W, H, 45, 5, ymax=160)}{shooting_star(820, 50, 'fs1', 8, 1)}
<text x="{W / 2}" y="96" text-anchor="middle" class="d" font-size="28" font-weight="700" fill="{TEXT}">Thanks for scrolling</text>
<text x="{W / 2}" y="130" text-anchor="middle" class="m" font-size="15" fill="{MUTED}">the duck will walk you out. close the tab gently.</text>
<rect x="0" y="{H - 30}" width="{W}" height="30" fill="#1A1347"/><rect x="0" y="{H - 34}" width="{W}" height="5" fill="#3B2D80"/>
<g><animateTransform attributeName="transform" type="translate" values="-50 {H - 34};{W + 50} {H - 34}" dur="14s" repeatCount="indefinite"/>
<g><animateTransform attributeName="transform" type="translate" values="0 0;0 -3;0 0" dur=".5s" repeatCount="indefinite"/>{duck(walking=True, scale=.8)}</g></g></g>
<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" rx="24" fill="none" stroke="{STROKE}" stroke-width="1.5"/>'''
    save('footer.svg', svg_doc(W, H, 'Thanks for scrolling', b))


# ---------------------------------------------------------- about & readme ---
THEMES = [  # (label, keywords matched against name + description, lower-case)
    ('Qt and PyQt desktop work', ('qt', 'pyqt', 'pyside')),
    ('remote desktop tooling', ('rdp', 'remote desktop', 'freerdp')),
    ('OCR and AI integrations', ('ocr', ' ai ', 'vision model', 'llm', 'openai', 'claude', 'gemini', 'ollama')),
    ('build and packaging tools', ('builder', 'build', 'packag', 'freeze')),
    ('web and front-end projects', ('html', 'css', 'javascript', 'typescript', 'react', 'node', 'chrome', 'portfolio')),
]


def classify(repo):
    """Themes a repo belongs to, each with a score: keyword in the name beats keyword in the description."""
    name = f' {repo["name"]} '.lower().replace('_', ' ').replace('-', ' ')
    hay = f'{name}{repo.get("description") or ""} {repo.get("language") or ""} '.lower().replace('_', ' ').replace('-', ' ')
    out = []
    for label, keys in THEMES:
        if any(k in name for k in keys):
            out.append((label, 2))
        elif any(k in hay for k in keys):
            out.append((label, 1))
    return out


def oxford(items):
    items = list(items)
    return items[0] if len(items) == 1 else ', '.join(items[:-1]) + ' and ' + items[-1]


def about_text(data):
    duck = any(r['name'] == 'TheWalkingDuckTaskBar' for r in own_repos(data))
    return (
        "**I build software that runs everywhere.** Desktop, mobile and web, often from a single codebase, "
        "with the same attention to how it feels on each screen.\n\n"
        "- 🖥️ **Native:** Qt with C++ and Python (PyQt / PySide), shipped to Windows, macOS, Linux, Android and iOS.\n"
        "- 🌐 **Web:** TypeScript, React and Node.js, from the first component to the deploy.\n"
        "- 🧩 **Favourite problems:** many moving parts behind one clean interface. Fifty OCR engines behind one API, "
        "six Qt bindings behind one import, a vision model behind one hotkey.\n"
        "- 🔌 **Also:** remote-desktop tooling, build and packaging tools, AI integrations"
        + (", and a duck that walks across your taskbar." if duck else ".")
    )


def code_block(data):
    own = own_repos(data)
    langs = [l for l, _ in collections.Counter(r['language'] for r in own if r['language']).most_common(4)]
    return f'''```ts
const usama = {{
  role:      "cross-platform software developer",
  platforms: ["Windows", "macOS", "Linux", "Android", "iOS", "Web"],
  native:    ["Qt C++", "PyQt / PySide"],
  web:       ["TypeScript", "React", "JavaScript", "HTML / CSS"],
  backend:   ["Python", "Node.js"],
  onGitHub:  {{ repos: {len(own)}, stars: {sum(r['stars'] for r in own)}, topLanguages: {json.dumps(langs)} }},
  debugger:  "a rubber duck",            // 100% success rate, 0% salary
  status:    (coffee: boolean) => coffee ? "shipping" : "compiling...",
}} as const;   // onGitHub is refreshed daily by a GitHub Action
```'''


def write_readme(data, names, toolbox_alt):
    tpl = open(os.path.join(ROOT, 'scripts', 'README.template.md'), encoding='utf-8').read()
    links = ' ·\n  '.join(f'<a href="https://github.com/{data["login"]}/{n}">{n}</a>' for n in names)
    out = (tpl.replace('{{about}}', about_text(data)).replace('{{code}}', code_block(data))
              .replace('{{project_links}}', links).replace('{{toolbox_alt}}', esc(toolbox_alt)).replace('{{project_names}}', ', '.join(names))
              .replace('{{login}}', data['login']).replace('{{updated}}', TODAY.strftime('%d %b %Y')))
    with open(os.path.join(ROOT, 'README.md'), 'w', encoding='utf-8') as f:
        f.write(out)
    print('  wrote README.md')


def make_stats(data):
    y, body, labels = 0, [], []
    for build in (make_overview, make_activity, make_breakdown, make_heatmap):
        part, h, label = build(data)
        body.append(f'<g transform="translate(0 {y})">{part}</g>')
        labels.append(label)
        y += h + GAP
    save('stats.svg', svg_doc(1000, y - GAP, '. '.join(labels), ''.join(body),
                              fonts=('Unbounded-700', 'JBMono-400', 'JBMono-700')))


def main():
    data = load_data()
    print(f'Generating for {data["login"]} ({data.get("source", "")})')
    make_headers(data)
    make_badges(data)
    toolbox_alt = make_toolbox(data)
    names = make_projects(data)
    make_stats(data)
    write_readme(data, names, toolbox_alt)
    make_footer()


if __name__ == '__main__':
    main()
