#!/usr/bin/env python3
"""
Helper for translating the NestJS docs (content/*.md) into Vietnamese.

Workflow per file <rel> (path relative to _source/content, e.g. "controllers.md"):
  1. python nt.py skel <rel>     -> writes source skeleton part(s) to _work/skel/<rel>.pN.md
                                    (fenced code blocks replaced by [[CODE:n]] placeholders)
  2. translate each part, write to _work/vi/<rel>.pN.md (same placeholders, same headings)
  3. python nt.py build <rel>    -> merges code back verbatim, keeps original heading anchors,
                                    validates, writes vi/<rel>
  python nt.py status            -> progress overview
"""
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "_source", "content")
SKEL = os.path.join(ROOT, "_work", "skel")
WORK = os.path.join(ROOT, "_work", "vi")
OUT = os.path.join(ROOT, "vi")

PART_LIMIT = 22000  # chars of English skeleton per part

FENCE_OPEN = re.compile(r"^((?:[ \t]*>)*[ \t]*)(`{3,}|~{3,})(.*)$")
PLACEHOLDER = re.compile(r"^[ \t>]*\[\[CODE:(\d+)\]\][ \t]*$")
HEADING = re.compile(r"^(#{1,6})[ \t]+(.*?)[ \t]*#*[ \t]*$")

LABELS = {
    "Hint": "Gợi ý",
    "Warning": "Cảnh báo",
    "Note": "Lưu ý",
    "Notice": "Chú ý",
    "Optional": "Tùy chọn",
}


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def split_code(text):
    """Return (skeleton_lines, blocks). blocks[n] = list of original lines."""
    lines = text.split("\n")
    out, blocks = [], []
    i = 0
    while i < len(lines):
        m = FENCE_OPEN.match(lines[i])
        if m:
            prefix, fence = m.group(1), m.group(2)
            close = re.compile(
                r"^(?:[ \t]*>)*[ \t]*" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}[ \t]*$"
            )
            j = i + 1
            while j < len(lines) and not close.match(lines[j]):
                j += 1
            if j >= len(lines):
                raise SystemExit(f"Unclosed fence at line {i + 1}")
            blocks.append(lines[i : j + 1])
            out.append(f"{prefix}[[CODE:{len(blocks)}]]")
            i = j + 1
        else:
            out.append(lines[i])
            i += 1
    return out, blocks


class Slugger:
    """Port of tools/transforms/content-package/services/renderer/heading.renderer.ts"""

    STRIP = re.compile(r"[ -⁯⸀-⹿\\'!\"#$%&()*+,./:;<=>?@\[\]^`{|}~]")

    def __init__(self):
        self.seen = {}

    def slug(self, value):
        s = value.lower().strip()
        s = re.sub(r"<[!/a-z].*?>", "", s, flags=re.I)
        s = self.STRIP.sub("", s)
        s = re.sub(r"\s", "-", s)
        orig, slug, acc = s, s, 0
        if slug in self.seen:
            acc = self.seen[orig]
            while True:
                acc += 1
                slug = f"{orig}-{acc}"
                if slug not in self.seen:
                    break
        self.seen[orig] = acc
        self.seen[slug] = 0
        return slug


def headings(skel_lines):
    res = []
    for idx, line in enumerate(skel_lines):
        m = HEADING.match(line)
        if m:
            res.append((idx, len(m.group(1)), m.group(2)))
    return res


def parts_of(skel_lines):
    """Split skeleton into parts at heading boundaries, each <= PART_LIMIT chars when possible."""
    hs = [i for i, lvl, _ in headings(skel_lines) if lvl <= 4 and i > 0]
    cuts, start, size = [], 0, 0
    bounds = hs + [len(skel_lines)]
    prev = 0
    for b in bounds:
        seg = sum(len(l) + 1 for l in skel_lines[prev:b])
        if size + seg > PART_LIMIT and size > 0:
            cuts.append((start, prev))
            start, size = prev, 0
        size += seg
        prev = b
    cuts.append((start, len(skel_lines)))
    return [skel_lines[a:b] for a, b in cuts]


def skel_paths(rel, n):
    return [os.path.join(SKEL, f"{rel}.p{k}.md") for k in range(1, n + 1)]


def work_paths(rel, n):
    return [os.path.join(WORK, f"{rel}.p{k}.md") for k in range(1, n + 1)]


def cmd_skel(rel):
    text = read(os.path.join(SRC, rel))
    skel, blocks = split_code(text)
    parts = parts_of(skel)
    for p, lines in zip(skel_paths(rel, len(parts)), parts):
        write(p, "\n".join(lines))
    print(f"{rel}: {len(blocks)} code blocks, skeleton {sum(len(l) + 1 for l in skel)} chars, {len(parts)} part(s)")
    for k, (p, lines) in enumerate(zip(skel_paths(rel, len(parts)), parts), 1):
        print(f"  p{k}: {sum(len(l) + 1 for l in lines):>6} chars  {p}")


INLINE_CODE = re.compile(r"(`+)(.+?)\1")
LINK = re.compile(r"\]\(\s*<?([^)\s>]+)>?(?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*\)")
ATTR_URL = re.compile(r"\b(?:href|src|routerLink)\s*=\s*(['\"])(.*?)\1")
ADMON = re.compile(r"^[ \t]*>[ \t]*(info|warning|error)\b", re.M)
TAG = re.compile(r"<(/?[a-zA-Z][\w-]*)")
EN_WORDS = [" the ", " and ", " is ", " to ", " of ", " you ", " with ", " that ", " this ", " are ", " for "]


def prose(lines):
    return "\n".join(l for l in lines if not PLACEHOLDER.match(l))


def diff_counter(name, a, b, issues, show=6):
    if a == b:
        return
    missing = a - b
    extra = b - a
    msg = f"{name}:"
    if missing:
        msg += " missing " + ", ".join(repr(k) + (f"x{v}" if v > 1 else "") for k, v in list(missing.items())[:show])
    if extra:
        msg += " extra " + ", ".join(repr(k) + (f"x{v}" if v > 1 else "") for k, v in list(extra.items())[:show])
    issues.append(msg)


def cmd_build(rel, quiet=False):
    src_text = read(os.path.join(SRC, rel))
    src_skel, blocks = split_code(src_text)
    n = len(parts_of(src_skel))
    wp = work_paths(rel, n)
    single = os.path.join(WORK, rel)
    if all(os.path.exists(p) for p in wp):
        vi_text = "\n".join(read(p).rstrip("\n") for p in wp)
    elif os.path.exists(single):
        vi_text = read(single)
    else:
        missing = [os.path.basename(p) for p in wp if not os.path.exists(p)]
        raise SystemExit(f"{rel}: missing translated parts: {missing}")
    if src_text.endswith("\n") and not vi_text.endswith("\n"):
        vi_text += "\n"
    vi_lines = vi_text.split("\n")
    issues, warns = [], []

    # admonition labels -> Vietnamese (display text only; the type keyword stays)
    def fix_label(m):
        return m.group(1) + "**" + LABELS.get(m.group(2), m.group(2)) + "**"

    vi_lines = [re.sub(r"^([ \t]*>[ \t]*(?:info|warning|error)[ \t]+)\*\*([A-Za-z]+)\*\*", fix_label, l) for l in vi_lines]

    # placeholders
    seen = [int(PLACEHOLDER.match(l).group(1)) for l in vi_lines if PLACEHOLDER.match(l)]
    expected = list(range(1, len(blocks) + 1))
    if seen != expected:
        c = Counter(seen)
        miss = [k for k in expected if k not in c]
        dup = [k for k, v in c.items() if v > 1]
        issues.append(f"code placeholders mismatch: missing {miss} dup {dup} order_ok={sorted(seen) == seen}")

    # headings + anchors
    sh, vh = headings(src_skel), headings(vi_lines)
    if [l for _, l, _ in sh] != [l for _, l, _ in vh]:
        issues.append(f"heading structure differs: src {len(sh)} vs vi {len(vh)}")
        for k in range(min(len(sh), len(vh))):
            if sh[k][1] != vh[k][1]:
                issues.append(f"  first diff at heading #{k + 1}: src {'#' * sh[k][1]} {sh[k][2]!r} vs vi {'#' * vh[k][1]} {vh[k][2]!r}")
                break
    else:
        s1, s2 = Slugger(), Slugger()
        injected, generated = [], []
        for (si, lvl, stext), (vi_idx, _, vtext) in zip(sh, vh):
            vtext_clean = re.sub(r"\s*<a id=\"[^\"]*\"></a>\s*$", "", vtext)
            o, v = s1.slug(stext), s2.slug(vtext_clean)
            generated.append(v)
            if vi_idx == 0:
                continue  # first line is the page title (extractContentTitle) - keep it clean
            if o != v:
                vi_lines[vi_idx] = f"{'#' * lvl} {vtext_clean} <a id=\"{o}\"></a>"
                injected.append(o)
            else:
                vi_lines[vi_idx] = f"{'#' * lvl} {vtext_clean}"
        clash = set(injected) & set(generated)
        if clash:
            warns.append(f"anchor id clash: {sorted(clash)}")

    # content checks (prose only)
    sp, vp = prose(src_skel), prose(vi_lines)
    diff_counter("inline code", Counter(m.group(0) for m in INLINE_CODE.finditer(sp)),
                 Counter(m.group(0) for m in INLINE_CODE.finditer(vp)), warns)
    diff_counter("link targets", Counter(LINK.findall(sp)) + Counter(u for _, u in ATTR_URL.findall(sp)),
                 Counter(LINK.findall(vp)) + Counter(u for _, u in ATTR_URL.findall(vp)), issues)
    diff_counter("admonitions", Counter(ADMON.findall(sp)), Counter(ADMON.findall(vp)), issues)
    vp_tags = re.sub(r' <a id="[^"]*"></a>', "", vp)
    diff_counter("html tags", Counter(TAG.findall(sp)), Counter(TAG.findall(vp_tags)), warns)
    for tok in ["{{ '{' }}", "{{ '}' }}"]:
        if sp.count(tok) != vp.count(tok):
            issues.append(f"angular escape {tok!r}: src {sp.count(tok)} vs vi {vp.count(tok)}")
    untranslated = []
    for k, l in enumerate(vi_lines, 1):
        if PLACEHOLDER.match(l) or len(l) < 60:
            continue
        low = " " + re.sub(r"`[^`]*`", "", l.lower()) + " "
        if sum(low.count(w) for w in EN_WORDS) >= 4:
            untranslated.append(k)
    if untranslated:
        warns.append(f"possibly untranslated lines (skeleton line no.): {untranslated[:15]}")

    # merge code back verbatim
    out = []
    for l in vi_lines:
        m = PLACEHOLDER.match(l)
        if m and 1 <= int(m.group(1)) <= len(blocks):
            out.extend(blocks[int(m.group(1)) - 1])
        else:
            out.append(l)
    result = "\n".join(out)
    status = "FAIL" if issues else ("WARN" if warns else "OK")
    if not issues:
        write(os.path.join(OUT, rel), result)
    if not quiet or issues or warns:
        print(f"[{status}] {rel}  ({len(blocks)} code blocks, {len(result)} chars)")
        for x in issues:
            print("  ERROR " + x)
        for x in warns:
            print("  warn  " + x)
    return status


def all_files():
    res = []
    for d, _, fs in os.walk(SRC):
        for f in fs:
            if f.endswith(".md"):
                res.append(os.path.relpath(os.path.join(d, f), SRC).replace("\\", "/"))
    return sorted(res)


def cmd_status():
    files = all_files()
    done = [f for f in files if os.path.exists(os.path.join(OUT, f))]
    todo = [f for f in files if f not in done]
    tot = sum(os.path.getsize(os.path.join(SRC, f)) for f in files)
    dsz = sum(os.path.getsize(os.path.join(SRC, f)) for f in done)
    print(f"done {len(done)}/{len(files)} files, {dsz * 100 // max(tot, 1)}% of source bytes")
    print("todo:", " ".join(todo))


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "skel":
        for r in args:
            cmd_skel(r)
    elif cmd == "build":
        for r in args:
            cmd_build(r)
    elif cmd == "status":
        cmd_status()
    else:
        print(__doc__)
