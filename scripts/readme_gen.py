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


# Spacing system. Full-width images span the whole README column (no side padding), so their
# edges line up with the text. Cards sit two per row; each carries half of the 20-unit gutter
# on its inner side, so a pair shown at 49.9% + 49.9% lines up exactly with a full-width image.
# Every image carries the same bottom padding, which becomes the vertical gap between rows.
GAP = 20
VGAP = 16          # plus the few pixels GitHub adds under inline images, this matches GAP


def svg_doc(w, h, label, body, fonts=('Unbounded-700', 'JBMono-400'), extra_css='', pad=(0, 0, 0, VGAP)):
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
 nodes{name description stargazerCount isFork primaryLanguage{name}}}
contributionsCollection{contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}'''


def load_data():
    token = os.environ.get('GH_TOKEN')
    snap_path = os.path.join(ROOT, 'data', 'snapshot.json')
    if token:
        req = urllib.request.Request('https://api.github.com/graphql',
                                     data=json.dumps({'query': GQL, 'variables': {'login': LOGIN}}).encode(),
                                     headers={'Authorization': f'bearer {token}', 'Content-Type': 'application/json'})
        u = json.load(urllib.request.urlopen(req, timeout=60))['data']['user']
        data = {'login': u['login'], 'name': u['name'] or u['login'], 'followers': u['followers']['totalCount'],
                'repos': [{'name': r['name'], 'description': r['description'] or '', 'stars': r['stargazerCount'],
                           'fork': r['isFork'], 'language': (r['primaryLanguage'] or {}).get('name')}
                          for r in u['repositories']['nodes']],
                'calendar': [{'date': d['date'], 'count': d['contributionCount']}
                             for w in u['contributionsCollection']['contributionCalendar']['weeks']
                             for d in w['contributionDays']],
                'source': 'GitHub API ' + dt.date.today().isoformat()}
        os.makedirs(os.path.dirname(snap_path), exist_ok=True)
        json.dump(data, open(snap_path, 'w'), indent=1)
        return data
    print('  GH_TOKEN not set, using data/snapshot.json')
    return json.load(open(snap_path))


# ------------------------------------------------------------ type scale ---
# One scale for every image. Images render at roughly 0.8x on GitHub, so nothing goes below 13.
T_TITLE, T_SUB, T_BODY, T_SMALL = 19, 13.5, 14, 13
INSET = 28  # inner padding of every card


def card_title(title, sub, w, right=None, right_sub=None):
    out = (f'<text x="{INSET}" y="56" class="d" font-size="{T_TITLE}" font-weight="700" fill="{TEXT}">{esc(title)}</text>'
           f'<text x="{INSET}" y="82" class="m pre" font-size="{T_SUB}" fill="{MUTED}">{esc(sub)}</text>')
    if right is not None:
        out += (f'<text x="{w - INSET}" y="56" text-anchor="end" class="d" font-size="{T_TITLE}" font-weight="700" fill="{CYAN}">{esc(right)}</text>'
                f'<text x="{w - INSET}" y="82" text-anchor="end" class="m" font-size="{T_SUB}" fill="{MUTED}">{esc(right_sub)}</text>')
    return out


# --------------------------------------------------------------- headers ---
SECTIONS = [  # (id, glyph, accent, title, subtitle)
    ('about', '{ }', CYAN, 'About me', 'desktop, mobile and web, often from one codebase'),
    ('projects', '</>', PINK, "Things I've built", 'click a card to open the repo'),
    ('toolbox', '#', AMBER, 'Toolbox', 'what I reach for, from C++ to CSS'),
    ('stats', '%', MINT, 'By the numbers', 'redrawn every day from my GitHub data'),
    ('contact', '@', VIOLET, "Let's talk", 'freelance, collaborations, well-written bug reports'),
]


def make_headers():
    W, H = 1000, 64
    for sid, glyph, accent, title, sub in SECTIONS:
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


def make_project_cards(data):
    repos = {r['name']: r for r in data['repos']}
    W, H = CARD_W, 236
    inner = W - 2 * INSET
    for idx, (name, kind, accent, joke) in enumerate(PROJECTS):
        side = (0, GAP // 2, 0, VGAP) if idx % 2 == 0 else (GAP // 2, 0, 0, VGAP)   # left / right column
        r = repos.get(name, {'name': name, 'description': '', 'stars': 0, 'language': None})
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
        b = [card_bg(W, H, accent, 'cg'),
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
        save(f'projects/{name}.svg', svg_doc(W, H, f'{name}: {desc}', ''.join(b), pad=side))


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
    save('stats/overview.svg', svg_doc(W, H, 'Profile overview: ' + ', '.join(f'{t[0]} {t[1]}' for t in tiles), ''.join(b)))


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
    save('stats/activity.svg', svg_doc(W, H, f'{total} contributions in the last 12 months, peak week {vals[pk]}', ''.join(b),
                                       fonts=('Unbounded-700', 'JBMono-400', 'JBMono-700')))


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
    save('stats/breakdown.svg', svg_doc(W, H, f'{la}. {ra}.', body))


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
    save('stats/heatmap.svg', svg_doc(W, H, 'Contribution calendar for the last 12 months', body))


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


def main():
    data = load_data()
    print(f'Generating for {data["login"]} ({data.get("source", "")})')
    make_headers()
    make_project_cards(data)
    make_overview(data)
    make_activity(data)
    make_breakdown(data)
    make_heatmap(data)
    make_footer()


if __name__ == '__main__':
    main()
