"""Rebuild ~/Desktop/1/wahl-strassenbau text files from Claude Code session transcripts.

Replays, in timestamp order: Write results, Edit/MultiEdit results (originalFile + change),
full Read results, Bash heredocs (cat > / cat >>) and bashEditDiff hunks.
Usage: python3 -I recover.py <transcripts_dir> <out_dir>
"""
import glob, json, os, re, sys

ROOT = '/Users/macbook/Desktop/1/wahl-strassenbau/'
SKIP_PREFIX = ('.agents/', '.git/', 'node_modules/')
src_dir, out_dir = sys.argv[1], sys.argv[2]

files = {}   # rel -> content
meta = {}    # rel -> dict(source, ts, stale)
log = []


def rel_of(p):
    p = os.path.normpath(p)
    if not p.startswith(ROOT):
        return None
    r = p[len(ROOT):]
    return None if (not r or r.startswith(SKIP_PREFIX)) else r


def setf(rel, content, source, ts):
    files[rel] = content
    meta[rel] = {'source': source, 'ts': ts, 'stale': False}


def apply_hunks(text, hunks):
    lines = text.split('\n')
    offset = 0
    for h in hunks:
        old = [l[1:] for l in h['lines'] if l[:1] in (' ', '-')]
        new = [l[1:] for l in h['lines'] if l[:1] in (' ', '+')]
        start = max(h['oldStart'] - 1 + offset, 0)
        pos = None
        if not old:
            pos = min(start, len(lines))
        else:
            for delta in range(0, len(lines) + 1):
                for cand in (start + delta, start - delta):
                    if 0 <= cand <= len(lines) - len(old) and lines[cand:cand + len(old)] == old:
                        pos = cand
                        break
                if pos is not None:
                    break
        if pos is None:
            return None
        lines[pos:pos + len(old)] = new
        offset += len(new) - len(old)
    return '\n'.join(lines)


HEREDOC = re.compile(
    r"cat\s*(?:(>>?)\s*(['\"]?)([^\s'\"<>|;&]+)\2\s*<<-?\s*(['\"]?)(\w+)\4"
    r"|<<-?\s*(['\"]?)(\w+)\6\s*(>>?)\s*(['\"]?)([^\s'\"<>|;&]+)\9)[^\n]*\n(.*?)\n(?:\5|\7)[ \t]*(?=\n|$)",
    re.S)
CD = re.compile(r"(?:^|&&|;|\n)\s*cd\s+(['\"]?)([^\s'\";&|]+)\1")


def heredocs(cmd, cwd):
    out = []
    for m in HEREDOC.finditer(cmd):
        mode = m.group(1) or m.group(8)
        path = m.group(3) or m.group(10)
        body = m.group(11)
        cur = cwd
        for c in CD.finditer(cmd[:m.start()]):
            cur = os.path.normpath(os.path.join(cur, os.path.expanduser(c.group(2))))
        out.append((mode, os.path.normpath(os.path.join(cur, os.path.expanduser(path))), body + '\n'))
    return out


# 1. collect tool_use inputs and results from all transcripts
uses, events = {}, []
for f in glob.glob(os.path.join(src_dir, '**', '*.jsonl'), recursive=True):
    for line in open(f, encoding='utf-8', errors='ignore'):
        if 'wahl-strassenbau' not in line:
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        c = (d.get('message') or {}).get('content')
        if not isinstance(c, list):
            continue
        for b in c:
            if not isinstance(b, dict):
                continue
            if b.get('type') == 'tool_use':
                uses[b['id']] = (b['name'], b.get('input', {}), d.get('cwd') or '')
            elif b.get('type') == 'tool_result':
                events.append((d.get('timestamp', ''), b['tool_use_id'], bool(b.get('is_error')),
                               d.get('toolUseResult'), os.path.basename(f)))

events.sort(key=lambda e: e[0])

# 2. replay
for ts, uid, is_err, res, fname in events:
    if uid not in uses or is_err:
        continue
    name, inp, cwd = uses[uid]
    res = res if isinstance(res, dict) else {}
    if name == 'Write':
        rel = rel_of(inp.get('file_path', ''))
        if rel:
            setf(rel, inp.get('content', ''), 'Write', ts)
    elif name in ('Edit', 'MultiEdit'):
        rel = rel_of(inp.get('file_path', ''))
        if not rel:
            continue
        base = res.get('originalFile')
        if base is None:
            base = files.get(rel)
        if base is None:
            log.append(f'{ts} {rel}: Edit without base, skipped')
            if rel in meta:
                meta[rel]['stale'] = True
            continue
        edits = inp.get('edits') if name == 'MultiEdit' else [inp]
        text, ok = base, True
        for e in edits:
            o, n = e.get('old_string', ''), e.get('new_string', '')
            if o not in text:
                ok = False
                break
            text = text.replace(o, n) if e.get('replace_all') else text.replace(o, n, 1)
        if ok:
            setf(rel, text, 'Edit', ts)
        else:
            log.append(f'{ts} {rel}: Edit old_string not found')
            setf(rel, base, 'Edit-base', ts)
            meta[rel]['stale'] = True
    elif name == 'Read':
        fi = res.get('file') if isinstance(res.get('file'), dict) else None
        rel = rel_of(inp.get('file_path', ''))
        if rel and fi and res.get('type') == 'text' and 'content' in fi:
            if fi.get('startLine', 1) == 1 and fi.get('numLines') == fi.get('totalLines'):
                setf(rel, fi['content'] + ('\n' if not fi['content'].endswith('\n') else ''), 'Read', ts)
    elif name == 'Bash':
        cmd = inp.get('command', '')
        touched = set()
        for mode, path, body in heredocs(cmd, cwd):
            rel = rel_of(path)
            if not rel:
                continue
            touched.add(rel)
            if mode == '>>':
                if rel in files:
                    files[rel] += body
                    meta[rel].update(source='Bash>>', ts=ts)
                else:
                    log.append(f'{ts} {rel}: append without base')
            else:
                setf(rel, body, 'Bash>', ts)
        for fd in (res.get('bashEditDiff') or {}).get('files', []):
            rel = rel_of(fd.get('filePath', ''))
            if not rel or rel in touched:
                continue
            hunks = fd.get('hunks', [])
            if rel not in files:
                if hunks and hunks[0].get('oldLines') == 0 and len(hunks) == 1:
                    setf(rel, '', 'Bash-new', ts)
                else:
                    log.append(f'{ts} {rel}: bash diff without base')
                    continue
            new = apply_hunks(files[rel], hunks)
            if new is None:
                log.append(f'{ts} {rel}: bash diff did not apply')
                meta[rel]['stale'] = True
            else:
                files[rel] = new
                meta[rel].update(source=meta[rel]['source'] + '+bashdiff', ts=ts)

# 3. write out
for rel, content in files.items():
    p = os.path.join(out_dir, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as fh:
        fh.write(content)
json.dump({'files': meta, 'log': log}, open(os.path.join(out_dir, '_recovery-meta.json'), 'w'),
          ensure_ascii=False, indent=1, sort_keys=True)
print('files', len(files), 'stale', sum(m['stale'] for m in meta.values()), 'log', len(log))
