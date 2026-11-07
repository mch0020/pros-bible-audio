"""Find every verse in Louis Tyler's chapter recordings (MMS forced aligner)
and re-encode the chapter files small for the app.
usage: align_book.py <corpus tr|wh|ot> <unzipped root> <out dir> <book>..."""
import json, os, re, subprocess, sys, time, torch, torchaudio
torch.set_num_threads(os.cpu_count() or 2)
corpus, root, out = sys.argv[1:4]; books = [b for b in ' '.join(sys.argv[4:]).split('|') if b]
H = os.path.dirname(os.path.abspath(__file__))
T = json.load(open(f'{H}/../texts/{corpus}.json'))
NT = ['Matthew','Mark','Luke','John','Acts','Romans','1 Corinthians','2 Corinthians','Galatians','Ephesians','Philippians','Colossians',
      '1 Thessalonians','2 Thessalonians','1 Timothy','2 Timothy','Titus','Philemon','Hebrews','James','1 Peter','2 Peter','1 John','2 John','3 John','Jude','Revelation']
ALIAS = {'song of songs': 'Song of Solomon', 'canticles': 'Song of Solomon', 'psalm': 'Psalms', 'qohelet': 'Ecclesiastes'}
def book_of(folder):
    m = re.match(r'(\d+)\s+(.*)', folder)
    if corpus in ('tr', 'wh'): return NT[int(m.group(1)) - 1] if m else None
    name = (m.group(2) if m else folder).strip().lower()
    name = re.sub(r'^(i{1,3})\s', lambda x: str(len(x.group(1))) + ' ', name)
    for b in T['books']:
        if b.lower() == name or ALIAS.get(name) == b: return b
    for b in T['books']:
        if name.startswith(b.lower()) or b.lower().startswith(name): return b
    return None
files = {}
for dp, _, fs in os.walk(root):
    for f in fs:
        if not f.lower().endswith('.mp3'): continue
        b = book_of(os.path.basename(dp))
        n = re.findall(r'(\d+)\s*\.mp3$', f)
        files.setdefault(b, []).append((int(n[0]) if n else 1, os.path.join(dp, f)))
print('books found', {k: len(v) for k, v in files.items()}, flush=True)
bundle = torchaudio.pipelines.MMS_FA
model = bundle.get_model(with_star=True).eval(); lab = bundle.get_dict(star='*'); SR = bundle.sample_rate
FPS = None
def emit(path):
    global FPS
    wav, sr = torchaudio.load(path); wav = torchaudio.functional.resample(wav.mean(0, keepdim=True), sr, SR)
    ems = []; step = SR * 20
    with torch.inference_mode():
        for i in range(0, wav.size(1), step):
            seg = wav[:, i:i + step]
            if seg.size(1) < 400: break
            ems.append(model(seg)[0][0])
    em = torch.cat(ems); FPS = em.size(0) / (wav.size(1) / SR)
    return em, wav.size(1) / SR
def align(em, words, pre_star=True):
    toks = ([lab['*']] if pre_star else []) + [lab[c] for w in words for c in w] + [lab['*']]
    ali, sc = torchaudio.functional.forced_align(em.unsqueeze(0), torch.tensor([toks]), blank=0)
    spans = torchaudio.functional.merge_tokens(ali[0], sc[0].exp())
    spans = spans[1:] if pre_star else spans
    res, i = [], 0
    for w in words:
        s = spans[i:i + len(w)]; i += len(w)
        res.append((s[0].start / FPS, s[-1].end / FPS, float(sum(x.score for x in s) / len(s))))
    return res
os.makedirs(out, exist_ok=True)
for book in books:
    t0 = time.time(); bi = NT.index(book) + 40 if book in NT else T['books'].index(book) + 1
    verses = T['text'][book]; W = []
    for vi, (vid, ch, vs, txt) in enumerate(verses):
        for w in txt.split(): W.append((vi, w))
    fl = sorted(files.get(book, []))
    if not fl: print('NO FILES', book, flush=True); continue
    E = [emit(p) for _, p in fl]
    total = sum(d for _, d in E); rate = len(W) / total
    p = 0; result = {}
    for k, ((num, path), (em, dur)) in enumerate(zip(fl, E)):
        if k < len(fl) - 1:
            em2, dur2 = E[k + 1]
            end = min(len(W), p + int(rate * (dur + 0.5 * dur2)))
            words = [w for _, w in W[p:end]]
            r = align(torch.cat([em, em2]), words)
            n = sum(1 for (a, b, s) in r if a < dur - 0.3)
            # move q to the nearest verse start
            starts = [i for i in range(p + 1, min(len(W), end) + 1) if i == len(W) or W[i][0] != W[i - 1][0]]
            q = min(starts, key=lambda i: abs(i - (p + n))) if starts else p + n
        else:
            q = len(W)
        seg = W[p:q]
        r = align(em, [w for _, w in seg]) if seg else []
        name = f'{bi:02d}-{num:03d}.mp3'
        for (vi, w), (a, b, s) in zip(seg, r):
            e = result.setdefault(verses[vi][0], [name, a, b, [], len(verses[vi][3].split())])
            e[1] = min(e[1], a); e[2] = max(e[2], b); e[3].append(s)
        subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-y', '-i', path, '-ac', '1', '-ar', '24000', '-b:a', '48k', f'{out}/{name}'], check=True)
        p = q
    # verse edges: halfway into the pause on each side
    items = sorted(result.items(), key=lambda x: (x[1][0], x[1][1]))
    final = {}
    for j, (vid, (f, a, b, sc, nw)) in enumerate(items):
        prev = items[j - 1][1] if j and items[j - 1][1][0] == f else None
        nxt = items[j + 1][1] if j + 1 < len(items) and items[j + 1][1][0] == f else None
        s0 = max(a - 0.35, (prev[2] + a) / 2 if prev else 0)
        e0 = min(b + 0.5, (b + nxt[1]) / 2 if nxt else b + 0.6)
        final[vid] = [f, round(s0, 2), round(e0, 2), round(sum(sc) / len(sc), 2)]
    missing = [v[0] for v in verses if v[0] not in final]
    json.dump(final, open(f'{out}/{bi:02d}.json', 'w'))
    low = sorted(final.items(), key=lambda x: x[1][3])[:5]
    print(f'{book}: {len(final)} verses, {len(fl)} files, {total/60:.1f} min audio, {time.time()-t0:.0f}s, missing {len(missing)}, lowest {low}', flush=True)
