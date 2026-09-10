"""
Repair a Google Docs "Download as Markdown" export.

The Docs Markdown converter damages exported documents in deterministic ways.
This script undoes the damage so a Drive-authored document can be diffed against,
and merged into, the repository copy.

What it repairs:
  1. Backslash-escaped punctuation   ``## 1\. Problem``      -> ``## 1. Problem``
  2. ``&nbsp;`` filler               standalone lines dropped, inline -> space
  3. Heading inflation               body paragraphs styled as Heading 3 in Docs
                                     export as ``### <full sentence>``; these are
                                     demoted back to paragraphs
  4. Bold-wrapped headings           ``## **6. Summary**``    -> ``## 6. Summary``
  5. Smart punctuation               curly quotes / dashes -> ASCII equivalents
  6. Trailing whitespace and runs of blank lines

What it deliberately does NOT do:
  - Restore LaTeX. Google Docs destroys ``$...$`` math on export and the original
    markup is unrecoverable from the export alone. Math must be re-applied by hand
    or preserved from the repository copy. Surviving math is reported so you can
    see how much needs restoring.

Usage:
    python repair_gdocs_export.py --input "export.md" --output "repaired.md"
    python repair_gdocs_export.py --input "export.md" --output "repaired.md" --stats-only
"""
import argparse
import re
import sys
from pathlib import Path

BACKSLASH = chr(92)

# A literal backslash in a regex must itself be escaped, hence BACKSLASH * 2.
_ESCAPED_PUNCT = r'[.\-=_<>\[\]*|#()+~`]'
ESC_SUB = re.compile(BACKSLASH * 2 + '(' + _ESCAPED_PUNCT + ')')
ESC_FIND = re.compile(BACKSLASH * 2 + _ESCAPED_PUNCT)

# A heading line is kept as a heading when it looks like a section title:
# numbered ("3.7 AoA Noise Model"), or short enough to be a real title.
MAX_TITLE_LEN = 75
NUMBERED_TITLE = re.compile(r'^\d+(\.\d+)*\.?\s+\S')

SMART_MAP = {
    '’': "'", '‘': "'",
    '“': '"', '”': '"',
    '–': '-', '—': '-',
    '‎': '',            # left-to-right mark, injected around minus signs
}


def strip_escapes(text):
    """Undo ``\\.`` ``\\-`` ``\\_`` and friends inserted by the Docs exporter."""
    return ESC_SUB.sub(r'\1', text)


def fix_smart_punctuation(text):
    for bad, good in SMART_MAP.items():
        text = text.replace(bad, good)
    return text


def demote_inflated_headings(lines, report):
    """Docs Heading-3-styled body text exports as ``### <sentence>``. Demote it."""
    out = []
    for ln in lines:
        m = re.match(r'^(#{1,6})\s+(.*)$', ln)
        if not m:
            out.append(ln)
            continue
        hashes, title = m.group(1), m.group(2).strip()
        bare = re.sub(r'^\*+|\*+$', '', title).strip()

        if not bare:                       # empty heading shell
            report['empty_headings'] += 1
            continue
        looks_like_title = NUMBERED_TITLE.match(bare) or len(bare) <= MAX_TITLE_LEN
        # a sentence ending in a period that is not a numbered title is body text
        if looks_like_title and not (len(bare) > MAX_TITLE_LEN):
            out.append(f'{hashes} {bare}')
        else:
            report['demoted_headings'] += 1
            out.append(bare)
    return out


def drop_nbsp(lines, report):
    out = []
    for ln in lines:
        if ln.strip() in ('&nbsp;', '&nbsp;&nbsp;'):
            report['nbsp_lines_dropped'] += 1
            continue
        if '&nbsp;' in ln:
            report['nbsp_inline_fixed'] += 1
            ln = ln.replace('&nbsp;', ' ')
        out.append(ln)
    return out


def collapse_blanks(lines):
    out, blanks = [], 0
    for ln in lines:
        if not ln.strip():
            blanks += 1
            if blanks > 2:
                continue
        else:
            blanks = 0
        out.append(ln.rstrip())
    return out


def repair(text, report):
    report['math_delimiters_surviving'] = text.count('$')
    text = strip_escapes(text)
    text = fix_smart_punctuation(text)
    lines = text.split('\n')
    lines = drop_nbsp(lines, report)
    lines = demote_inflated_headings(lines, report)
    lines = collapse_blanks(lines)
    return '\n'.join(lines).rstrip() + '\n'


def main():
    ap = argparse.ArgumentParser(
        description='Repair a Google Docs Markdown export for diffing against the repo copy.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python repair_gdocs_export.py --input "Localization using transition Footprints.md" \\
      --output docs/Project_documentation/drive_snapshots/repaired.md

  # inspect the damage without writing anything
  python repair_gdocs_export.py --input export.md --stats-only
""")
    ap.add_argument('--input', required=True, help='Google Docs .md export')
    ap.add_argument('--output', help='repaired output path (omit with --stats-only)')
    ap.add_argument('--stats-only', action='store_true',
                    help='report the damage found, write nothing')
    args = ap.parse_args()

    src = Path(args.input)
    if not src.exists():
        raise FileNotFoundError(f'Export not found: {src}')

    report = dict(nbsp_lines_dropped=0, nbsp_inline_fixed=0,
                  demoted_headings=0, empty_headings=0,
                  math_delimiters_surviving=0)

    raw = src.read_text(encoding='utf-8')
    fixed = repair(raw, report)

    before_escapes = len(ESC_FIND.findall(raw))
    print(f'input : {src}  ({len(raw.splitlines())} lines)')
    print(f'  escaped punctuation removed : {before_escapes}')
    print(f'  &nbsp; lines dropped        : {report["nbsp_lines_dropped"]}')
    print(f'  &nbsp; inline fixed         : {report["nbsp_inline_fixed"]}')
    print(f'  inflated headings demoted   : {report["demoted_headings"]}')
    print(f'  empty heading shells removed: {report["empty_headings"]}')
    print(f'  math delimiters surviving   : {report["math_delimiters_surviving"]}'
          '   <-- LaTeX is NOT recoverable from the export; restore by hand')

    if args.stats_only:
        return 0
    if not args.output:
        ap.error('--output is required unless --stats-only is given')

    dst = Path(args.output)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(fixed, encoding='utf-8')
    print(f'output: {dst}  ({len(fixed.splitlines())} lines)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
