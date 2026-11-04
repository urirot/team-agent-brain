#!/usr/bin/env python3
"""The one tool behind the brain's hooks and skills. Python 3.9+, standard library only.

    python3 tools/brain.py find <words>         ranked notes for a task, best first
    python3 tools/brain.py show <folder|note>   a note's status, abstract, links and backlinks
    python3 tools/brain.py for-path <file>      the notes that cite a code file
    python3 tools/brain.py catalog              what the session-start hook prints
    python3 tools/brain.py check                notes missing a status or an abstract, broken links
    python3 tools/brain.py build                rebuild .index/ (the other commands do it when stale)
    python3 tools/brain.py setup                print the hook and env config for Claude Code and Cursor
    python3 tools/brain.py hook <event>         session-start | prompt | file | stop | end (reads stdin)

The index under .index/ is built on each laptop from the notes and never committed, so two people's
pushes never conflict over a generated file.
"""
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(os.environ.get('BRAIN_DIR') or Path(__file__).resolve().parents[1])
INDEX_DIR = ROOT / '.index'
INDEX = INDEX_DIR / 'index.json'

# Claude Code replaces hook context over 10,000 characters with a short preview, so every hook
# stays under this.
HOOK_CAP = 9500
TOP_K = 5
MIN_SCORE = 3.0          # below this the prompt hook stays silent; raise it as the brain grows
MIN_COVERAGE = 0.25      # share of the prompt's word weight a hit must match
ID_BONUS = 12.0          # a note whose subject is an issue number the prompt names
PUSH_EVERY_S = 30 * 60   # the turn-end push runs at most this often

SKIP_DIRS = {'.git', '.index', 'tools', 'skills', 'examples', 'node_modules'}
ROOT_FILES = {'README.md', 'AGENTS.md', 'LESSONS.md', 'LICENSE.md', 'CHANGELOG.md'}
FIELDS = {'title': 3.0, 'abstract': 2.0, 'path': 2.0, 'tags': 2.0, 'body': 1.0}
STOP = set('''a an and are as at be but by can could did do does for from had has have how i if in into
is it its just let lets me my no not of on or our please so than that the their them then there these
this to up us was we were what when where which while who why will with would you your yes ok okay
check look see make get go need want also some any all one two new now here about after before'''.split())
COMMON_NAMES = {'README.md', 'index.ts', 'index.js', '__init__.py', 'config.py', 'utils.py', 'main.py',
                'package.json', 'Makefile', 'Dockerfile', 'settings.json', 'CLAUDE.md', 'AGENTS.md'}
DONE = ('shipped', 'done', 'answered', 'superseded', 'abandoned', 'reference')


# ---------- notes ----------

def note_files():
    for p in sorted(ROOT.rglob('*.md')):
        rel = p.relative_to(ROOT)
        if rel.parts[0] in SKIP_DIRS or (len(rel.parts) == 1 and rel.name in ROOT_FILES):
            continue
        yield p


def parse_note(path):
    text = path.read_text(encoding='utf-8', errors='replace')
    fm, body = {}, text
    if text.startswith('---\n'):
        end = text.find('\n---', 4)
        if end != -1:
            for line in text[4:end].splitlines():
                if ':' in line and not line.startswith((' ', '-')):
                    k, v = line.split(':', 1)
                    fm[k.strip()] = v.strip().strip('"\'')
            body = text[end + 4:].lstrip('\n')
    title = fm.get('title') or next((l[2:].strip() for l in body.splitlines() if l.startswith('# ')), path.stem)
    abstract, inside = [], False
    for line in body.splitlines():
        if line.lower().startswith('> [!abstract]'):
            inside = True
            continue
        if inside:
            if not line.startswith('>'):
                break
            abstract.append(line[1:].strip())
    rel = path.relative_to(ROOT).as_posix()
    return {
        'path': rel,
        'folder': str(Path(rel).parent.as_posix()),
        'title': title,
        'status': fm.get('status', ''),
        'updated': fm.get('last_updated') or fm.get('updated') or '',
        'author': fm.get('author', ''),
        'issue': fm.get('issue', ''),
        'tags': fm.get('tags', '').strip('[]'),
        'abstract': ' '.join(abstract),
        'body': body,
        'cites': sorted(set(cited_paths(body))),
        'links': sorted(set(wiki_links(body, rel))),
    }


def cited_paths(body):
    """Code spans that look like a file path: `api/dashboard_stream.py`, `Makefile` is too common."""
    for span in re.findall(r'`([^`\s]+)`', body):
        span = span.split(':')[0].rstrip('.,')
        span = span[2:] if span.startswith('./') else span
        if '/' in span or re.search(r'\.[A-Za-z0-9]{1,5}$', span):
            if Path(span).name not in COMMON_NAMES and not span.startswith(('http', 'people/')):
                yield span


def wiki_links(body, rel):
    """[[people/sam/topic/analysis]] and [text](../other/note.md), as vault-relative paths."""
    for t in re.findall(r'\[\[([^\]|#]+)', body):
        yield t.strip().removesuffix('.md') + '.md'
    for t in re.findall(r'\]\(([^)#\s]+\.md)\)', body):
        if not t.startswith('http'):
            yield os.path.normpath(os.path.join(os.path.dirname(rel), t))


def is_done(status):
    return status.lower().startswith(DONE)


# ---------- index ----------

def tokens(text):
    out = []
    for w in re.findall(r'[a-z0-9]+', text.lower()):
        if len(w) < 2 or w in STOP:
            continue
        for suf in ('ing', 'ed', 'es', 's'):
            if len(w) > 4 and w.endswith(suf) and not w.isdigit():
                w = w[:-len(suf)]
                break
        out.append(w)
    return out


def build():
    notes = [parse_note(p) for p in note_files()]
    docs, df = [], {}
    for n in notes:
        tf = {}
        for field, weight in FIELDS.items():
            src = n['folder'] if field == 'path' else n[field]
            for t in tokens(src):
                tf[t] = tf.get(t, 0) + weight
        length = sum(tf.values())
        docs.append({**{k: v for k, v in n.items() if k != 'body'}, 'tf': tf, 'len': length})
        for t in tf:
            df[t] = df.get(t, 0) + 1
    N = max(len(docs), 1)
    index = {'built': time.time(), 'N': N, 'avg': sum(d['len'] for d in docs) / N if docs else 0,
             'df': df, 'docs': docs}
    INDEX_DIR.mkdir(exist_ok=True)
    INDEX.write_text(json.dumps(index), encoding='utf-8')
    return index


def load():
    """The index, rebuilt first when any note or LESSONS.md is newer than it."""
    try:
        built = INDEX.stat().st_mtime
        newest = max([p.stat().st_mtime for p in note_files()] + [lessons_mtime()], default=0)
        if newest <= built:
            return json.loads(INDEX.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        pass
    return build()


def lessons_mtime():
    try:
        return (ROOT / 'LESSONS.md').stat().st_mtime
    except OSError:
        return 0


# ---------- ranking ----------

def ids_in(text):
    return set(re.findall(r'(?:#|issues?/|pull/)(\d{2,6})\b', text)) | set(re.findall(r'\b([A-Z]+-\d+)\b', text))


def rank(index, query, limit=10):
    q = tokens(query)
    ids = ids_in(query)
    N, avg, df = index['N'], index['avg'] or 1, index['df']
    idf = {t: math.log(1 + (N - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5)) for t in set(q)}
    total = sum(idf.values()) or 1
    rows = []
    for d in index['docs']:
        score, matched = 0.0, 0.0
        for t in set(q):
            f = d['tf'].get(t)
            if f:
                score += idf[t] * f * 2.2 / (f + 1.2 * (0.25 + 0.75 * d['len'] / avg))
                matched += idf[t]
        coverage = matched / total
        subject = ' '.join([d['issue'], d['folder']])
        if ids and any(i in subject for i in ids):
            score += ID_BONUS
            coverage = 1.0                                  # the note is about what the prompt names
        if d['status'].lower().startswith('superseded'):
            score /= 2                                      # so its replacement ranks first
        if score > 0:
            rows.append((score, coverage, d))
    rows.sort(key=lambda r: -r[0])
    return rows[:limit]


def best_per_folder(rows, k):
    out, seen = [], set()
    for r in rows:
        if r[2]['folder'] not in seen:
            seen.add(r[2]['folder'])
            out.append(r)
        if len(out) == k:
            break
    return out


def line_for(d, width=200):
    status = d['status'] or 'no status'
    s = '- %s [%s] %s' % (d['folder'], status, d['title'])
    return s if len(s) <= width else s[:width - 1] + '…'


# ---------- lessons ----------

def lessons():
    """LESSONS.md bullets: (headline, linked note paths)."""
    try:
        text = (ROOT / 'LESSONS.md').read_text(encoding='utf-8')
    except OSError:
        return []
    out = []
    for block in re.split(r'\n(?=- \*\*)', text):
        m = re.match(r'- \*\*(.+?)\*\*', block)
        if m:
            out.append((m.group(1), [l.removesuffix('.md') for l in re.findall(r'\[\[([^\]|#]+)', block)]))
    return out


# ---------- commands ----------

def cmd_find(words):
    index = load()
    rows = best_per_folder(rank(index, ' '.join(words), limit=40), 10)
    if not rows:
        print('no note matches')
    for score, cov, d in rows:
        print('%5.1f  %s' % (score, line_for(d)))


def resolve(arg):
    index = load()
    arg = arg.rstrip('/').removesuffix('.md')
    for d in index['docs']:
        if d['path'].removesuffix('.md') == arg:
            return index, d
    in_folder = [d for d in index['docs'] if d['folder'] == arg]
    if in_folder:
        return index, next((d for d in in_folder if d['abstract']), in_folder[0])
    sys.exit('no such note or folder: %s' % arg)


def cmd_show(arg):
    index, d = resolve(arg)
    print(d['path'])
    print('status: %s · updated %s · author %s' % (d['status'] or '-', d['updated'] or '-', d['author'] or '-'))
    print()
    print(d['abstract'] or '(no abstract)')
    if d['links']:
        print('\nlinks to: ' + ', '.join(d['links']))
    back = sorted({o['path'] for o in index['docs'] if d['path'] in o['links']})
    if back:
        print('linked from: ' + ', '.join(back))
    if d['cites']:
        print('cites: ' + ', '.join(d['cites'][:12]))


def citing(index, file_path):
    """Notes that cite this file: a cited path that ends the file's path, or a distinctive file name."""
    f = file_path.replace('\\', '/')
    hits = []
    for d in index['docs']:
        for c in d['cites']:
            if f == c or f.endswith('/' + c):
                hits.append(d)
                break
    return hits


def cmd_for_path(path):
    hits = citing(load(), path)
    if not hits:
        print('no note cites %s' % path)
    for d in hits:
        print(line_for(d))


def catalog_text():
    index = load()
    by_folder = {}
    for d in index['docs']:
        cur = by_folder.get(d['folder'])
        if cur is None or (d['abstract'] and not cur['abstract']):
            by_folder[d['folder']] = d
    mains = sorted(by_folder.values(), key=lambda d: d['updated'], reverse=True)
    open_ = [d for d in mains if not is_done(d['status'])]
    done = [d for d in mains if is_done(d['status'])]
    you = os.environ.get('BRAIN_USER') or '<you>'
    head = [
        '## Team brain — %d investigations (%d open), %d lessons' % (len(mains), len(open_), len(lessons())),
        'Prior work by the whole team. Before a non-trivial task, check here and run '
        '`python3 %s/tools/brain.py show <folder>` on anything related. Write new findings to '
        '`people/%s/<topic>/` with a status line and an abstract (rules: %s/AGENTS.md).' % (ROOT, you, ROOT),
        '',
    ]
    lines = ['### Open'] + [line_for(d, 160) for d in open_] + ['', '### Done'] + [line_for(d, 160) for d in done]
    lesson_lines = ['', '### Lessons'] + ['- ' + h for h, _ in lessons()]
    text = '\n'.join(head + lines + lesson_lines)
    # Over the cap, drop the oldest finished work first, then the oldest open work.
    while len(text) > HOOK_CAP and (done or open_):
        (done or open_).pop()
        lines = ['### Open'] + [line_for(d, 160) for d in open_] + ['', '### Done'] + [line_for(d, 160) for d in done]
        text = '\n'.join(head + lines + lesson_lines + ['', '(older entries cut to fit; `brain.py find` sees all)'])
    return text[:HOOK_CAP]


def cmd_check():
    index, problems = load(), []
    paths = {d['path'] for d in index['docs']}
    folders = {}
    for d in index['docs']:
        folders.setdefault(d['folder'], []).append(d)
        if not d['status']:
            problems.append('%s: no status' % d['path'])
        for l in d['links']:
            if l not in paths and not (ROOT / l).exists():
                problems.append('%s: broken link %s' % (d['path'], l))
    for folder, ds in folders.items():
        if not any(d['abstract'] for d in ds):
            problems.append('%s: no note has a > [!abstract]' % folder)
    for h, links in lessons():
        for l in links:
            if l + '.md' not in paths:
                problems.append('LESSONS.md: "%s" links to missing %s' % (h[:50], l))
    print('\n'.join(problems) or 'ok: %d notes in %d investigations' % (len(paths), len(folders)))
    return 1 if problems else 0


def cmd_setup():
    py = 'python3 %s' % (ROOT / 'tools' / 'brain.py')
    claude = {
        'env': {'BRAIN_DIR': str(ROOT), 'BRAIN_USER': os.environ.get('USER', 'you')},
        'hooks': {
            'SessionStart': [{'hooks': [{'type': 'command', 'command': py + ' hook session-start', 'timeout': 30}]}],
            'UserPromptSubmit': [{'hooks': [{'type': 'command', 'command': py + ' hook prompt', 'timeout': 10}]}],
            'PostToolUse': [{'matcher': 'Read|Edit|MultiEdit|Write',
                             'hooks': [{'type': 'command', 'command': py + ' hook file', 'timeout': 10}]}],
            'Stop': [{'hooks': [{'type': 'command', 'command': py + ' hook stop', 'timeout': 10}]}],
            'SessionEnd': [{'hooks': [{'type': 'command', 'command': py + ' hook end', 'timeout': 10}]}],
        },
    }
    cursor = {'version': 1, 'hooks': {
        'sessionStart': [{'command': py + ' hook session-start --cursor', 'timeout': 30}],
        'postToolUse': [{'command': py + ' hook file --cursor', 'matcher': 'Read|Write', 'timeout': 10}],
    }}
    print('# Claude Code: merge into ~/.claude/settings.json')
    print(json.dumps(claude, indent=2))
    print('\n# Cursor: merge into ~/.cursor/hooks.json')
    print(json.dumps(cursor, indent=2))
    print('\n# Skills (Claude Code): ln -s %s/skills/* ~/.claude/skills/' % ROOT)


# ---------- hooks ----------

def emit(event, text, cursor):
    if not text:
        return
    if cursor:
        print(json.dumps({'additional_context': text}, ensure_ascii=False))
    else:
        print(json.dumps({'hookSpecificOutput': {'hookEventName': event, 'additionalContext': text}},
                         ensure_ascii=False))


def read_stdin():
    try:
        return json.loads(sys.stdin.read() or '{}')
    except ValueError:
        return {}


def git(*args, wait=True):
    cmd = ['git', '-C', str(ROOT), *args]
    if wait:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


def hook_session_start(cursor):
    if os.environ.get('BRAIN_AUTOPULL', '1') != '0' and (ROOT / '.git').exists():
        git('pull', '--ff-only', '--quiet', wait=False)    # everyone's notes, in the background
    for old in INDEX_DIR.glob('seen-*.json'):              # the file hook's per-session records
        if time.time() - old.stat().st_mtime > 86400:
            old.unlink(missing_ok=True)
    emit('SessionStart', catalog_text(), cursor)


def hook_prompt(payload, cursor):
    prompt = payload.get('prompt') or ''
    if not ids_in(prompt) and len(set(tokens(prompt))) < 2:
        return
    index = load()
    rows = [r for r in rank(index, prompt, limit=40)
            if r[0] >= MIN_SCORE and (r[1] >= MIN_COVERAGE or r[0] >= 30)]
    rows = best_per_folder(rows, TOP_K)
    if not rows:
        return
    hit = {r[2]['path'].removesuffix('.md') for r in rows}
    out = ['brain — prior work these words match (candidates, not verdicts: run '
           '`python3 %s/tools/brain.py show <folder>` before relying on one):' % ROOT]
    out += [line_for(d) for _, _, d in rows]
    linked = [h for h, links in lessons() if hit & set(links)]
    if linked:
        out += ['brain — lessons from those notes (read the rule in LESSONS.md before acting on it):']
        out += ['- ' + h for h in linked[:5]]
    emit('UserPromptSubmit', '\n'.join(out)[:HOOK_CAP], cursor)


def hook_file(payload, cursor):
    ti = payload.get('tool_input') or {}
    path = ti.get('file_path') or ti.get('path') or ti.get('notebook_path') or ''
    if not path or str(ROOT) in os.path.abspath(path):
        return
    session = re.sub(r'[^A-Za-z0-9_-]', '', payload.get('session_id') or payload.get('conversation_id') or 'none')
    seen_file = INDEX_DIR / ('seen-%s.json' % session)
    try:
        seen = set(json.loads(seen_file.read_text()))
    except (OSError, ValueError):
        seen = set()
    if path in seen:
        return                                              # once per file per session
    seen.add(path)
    INDEX_DIR.mkdir(exist_ok=True)
    seen_file.write_text(json.dumps(sorted(seen)))
    hits = citing(load(), path)
    if not hits:
        return
    hits.sort(key=lambda d: d['updated'], reverse=True)
    out = ['brain — %d note%s cite %s:' % (len(hits), '' if len(hits) == 1 else 's', os.path.basename(path))]
    out += [line_for(d) for d in hits[:4]]
    if len(hits) > 4:
        out.append('… %d more: `python3 %s/tools/brain.py for-path %s`' % (len(hits) - 4, ROOT, path))
    emit('PostToolUse', '\n'.join(out), cursor)


def hook_push(force):
    """Opt-in (BRAIN_AUTOPUSH=1): commit and push your own folder, never anything else."""
    user = os.environ.get('BRAIN_USER')
    if os.environ.get('BRAIN_AUTOPUSH') != '1' or not user or not (ROOT / 'people' / user).is_dir():
        return
    stamp = INDEX_DIR / 'last-push'
    if not force and stamp.exists() and time.time() - stamp.stat().st_mtime < PUSH_EVERY_S:
        return
    folder = 'people/%s' % user
    if not git('status', '--porcelain', '--', folder).stdout.strip():
        return
    INDEX_DIR.mkdir(exist_ok=True)
    stamp.touch()
    script = ('git add -- {f} && git commit -q -m "{f}: notes [auto]" -- {f} && '
              'git pull -q --rebase --autostash && git push -q').format(f=folder)
    subprocess.Popen(['sh', '-c', script], cwd=str(ROOT), stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)


def cmd_hook(event, cursor):
    payload = read_stdin()
    try:
        if event == 'session-start':
            hook_session_start(cursor)
        elif event == 'prompt':
            hook_prompt(payload, cursor)
        elif event == 'file':
            hook_file(payload, cursor)
        elif event in ('stop', 'end'):
            hook_push(force=event == 'end')
        else:
            sys.exit('unknown hook: %s' % event)
    except Exception as e:                                  # a hook must never break the session
        print('brain hook %s failed: %s' % (event, e), file=sys.stderr)


def main(argv):
    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__)
        return 0
    cmd, args = argv[0], argv[1:]
    if cmd == 'find' and args:
        cmd_find(args)
    elif cmd == 'show' and args:
        cmd_show(args[0])
    elif cmd == 'for-path' and args:
        cmd_for_path(args[0])
    elif cmd == 'catalog':
        print(catalog_text())
    elif cmd == 'check':
        return cmd_check()
    elif cmd == 'build':
        index = build()
        print('indexed %d notes' % len(index['docs']))
    elif cmd == 'setup':
        cmd_setup()
    elif cmd == 'hook' and args:
        cmd_hook(args[0], '--cursor' in args)
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
