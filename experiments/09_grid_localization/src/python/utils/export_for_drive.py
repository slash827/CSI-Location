"""
Render a repo-authored Markdown document into a Google-Drive-friendly copy.

Workflow this supports:
    repo (authoritative, LaTeX preserved)  ->  export  ->  upload to Drive (read-only)

Google Docs cannot render ``$...$`` math. Uploading Markdown that contains LaTeX
leaves raw source in the shared document. This script converts the math to
Unicode plain text so the uploaded copy is readable, while the repository copy
keeps its LaTeX intact for the eventual paper.

It converts:
  - inline ``$...$`` and display ``$$...$$`` math
  - Greek letters, operators, arrows, set relations
  - ``\\frac{a}{b}`` -> ``a/b``, ``\\sqrt{x}`` -> ``sqrt(x)``
  - superscripts and subscripts to Unicode where a glyph exists, else ``^{}``/``_{}``
  - ``\\text{...}``, ``\\mathbf{...}``, ``\\operatorname{...}`` -> their contents

Anything it cannot convert is reported by name so no silent corruption occurs.

Usage:
    python export_for_drive.py --input technical_documentation.md \\
        --output drive_upload/technical_documentation_for_drive.md
    python export_for_drive.py --input technical_documentation.md --check
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

GREEK = {
    'alpha': 'α', 'beta': 'β', 'gamma': 'γ', 'delta': 'δ', 'Delta': 'Δ',
    'epsilon': 'ε', 'varepsilon': 'ε', 'zeta': 'ζ', 'eta': 'η',
    'theta': 'θ', 'Theta': 'Θ', 'iota': 'ι', 'kappa': 'κ', 'lambda': 'λ',
    'Lambda': 'Λ', 'mu': 'μ', 'nu': 'ν', 'xi': 'ξ', 'pi': 'π', 'Pi': 'Π',
    'rho': 'ρ', 'sigma': 'σ', 'Sigma': 'Σ', 'tau': 'τ', 'phi': 'φ',
    'Phi': 'Φ', 'chi': 'χ', 'psi': 'ψ', 'omega': 'ω', 'Omega': 'Ω',
}

SYMBOLS = {
    'times': '×', 'cdot': '·', 'div': '÷', 'pm': '±', 'mp': '∓',
    'approx': '≈', 'neq': '≠', 'ne': '≠', 'leq': '≤', 'le': '≤',
    'geq': '≥', 'ge': '≥', 'll': '≪', 'gg': '≫', 'equiv': '≡',
    'propto': '∝', 'sim': '~', 'infty': '∞',
    'to': '→', 'rightarrow': '→', 'leftarrow': '←', 'Rightarrow': '⇒',
    'Leftarrow': '⇐', 'leftrightarrow': '↔', 'mapsto': '↦',
    'in': '∈', 'notin': '∉', 'subset': '⊂', 'subseteq': '⊆',
    'cup': '∪', 'cap': '∩', 'forall': '∀', 'exists': '∃',
    'sum': 'Σ', 'prod': '∏', 'int': '∫', 'partial': '∂', 'nabla': '∇',
    'circ': '°', 'degree': '°', 'ldots': '...', 'dots': '...', 'cdots': '...',
    'quad': ' ', 'qquad': '  ', 'ang': '∠', 'perp': '⊥',
    'odot': '⊙', 'oplus': '⊕', 'otimes': '⊗',
}

# operator names that simply lose their backslash
FUNCTIONS = {
    'cos', 'sin', 'tan', 'tanh', 'sinh', 'cosh', 'log', 'ln', 'exp',
    'min', 'max', 'arg', 'argmax', 'argmin', 'det', 'dim', 'clamp',
    'mod', 'gcd', 'lim', 'sup', 'inf',
}

SUPERSCRIPT = {'0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵',
               '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹', '+': '⁺', '-': '⁻',
               'n': 'ⁿ', 'i': 'ⁱ'}
SUBSCRIPT = {'0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄', '5': '₅',
             '6': '₆', '7': '₇', '8': '₈', '9': '₉', '+': '₊', '-': '₋',
             'a': 'ₐ', 'e': 'ₑ', 'i': 'ᵢ', 'o': 'ₒ', 'x': 'ₓ', 'n': 'ₙ',
             't': 'ₜ', 'r': 'ᵣ', 's': 'ₛ'}

BACKSLASH = chr(92)
# in a regex, a literal backslash must itself be escaped
RE_BS = BACKSLASH * 2
CMD_RE = re.compile(RE_BS + r'([A-Za-z]+)')


def _strip_wrappers(s):
    """``\\text{x}`` / ``\\mathbf{x}`` / ``\\operatorname{x}`` -> ``x`` (repeatedly)."""
    pattern = re.compile(
        RE_BS + r'(?:text|mathbf|mathrm|mathit|mathbb|mathcal|textbf|operatorname|bm)'
        r'\s*\{([^{}]*)\}')
    prev = None
    while prev != s:
        prev = s
        s = pattern.sub(r'\1', s)
    return s


def _read_group(s, i):
    """Read a balanced ``{...}`` starting at index i. Returns (content, index_after)."""
    if i >= len(s) or s[i] != '{':
        return None, i
    depth, j = 0, i
    while j < len(s):
        if s[j] == '{':
            depth += 1
        elif s[j] == '}':
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
    return None, i


def _apply_braced(s, name, render, n_args=1):
    """Rewrite ``\\name{a}`` (or ``\\name{a}{b}``) using a brace-balanced scan."""
    token = BACKSLASH + name
    out, i = [], 0
    while i < len(s):
        k = s.find(token, i)
        if k < 0:
            out.append(s[i:])
            break
        out.append(s[i:k])
        j = k + len(token)
        while j < len(s) and s[j] == ' ':
            j += 1
        args = []
        ok = True
        for _ in range(n_args):
            arg, j2 = _read_group(s, j)
            if arg is None:
                ok = False
                break
            args.append(arg)
            j = j2
        if ok:
            out.append(render(*args))
            i = j
        else:
            out.append(token)
            i = k + len(token)
    return ''.join(out)


def _wrap(arg):
    """Parenthesise a fraction argument only when it is a compound expression."""
    return arg if re.fullmatch(r'[\w.^_⁰-₟°]+', arg or '') else f'({arg})'


def _frac(s):
    prev = None
    while prev != s:
        prev = s
        s = _apply_braced(s, 'frac',
                          lambda a, b: f'{_wrap(a)}/{_wrap(b)}', n_args=2)
    return s


def _sqrt(s):
    prev = None
    while prev != s:
        prev = s
        s = _apply_braced(s, 'sqrt', lambda a: f'sqrt({a})')
    return s


def _accents(s):
    """``\\hat{x}`` -> x with a combining circumflex, ``\\tilde{h}`` -> h with tilde."""
    for name, combining in (('hat', '̂'), ('tilde', '̃'),
                            ('bar', '̄'), ('vec', '⃗'),
                            ('dot', '̇')):
        prev = None
        while prev != s:
            prev = s
            s = _apply_braced(s, name, lambda a, c=combining: a + c if a else a)
    return s


def _script(s, marker, table):
    """Convert ``^{...}`` / ``_{...}`` and single-char ``^x`` / ``_x``."""
    def repl_braced(m):
        body = m.group(1)
        if all(ch in table for ch in body) and body:
            return ''.join(table[ch] for ch in body)
        return f'{marker}({body})'

    s = re.sub(re.escape(marker) + r'\{([^{}]*)\}', repl_braced, s)
    s = re.sub(re.escape(marker) + r'([A-Za-z0-9+\-])',
               lambda m: table.get(m.group(1), marker + m.group(1)), s)
    return s


def latex_to_unicode(expr):
    s = expr
    s = _strip_wrappers(s)
    s = _accents(s)
    s = _frac(s)
    s = _sqrt(s)
    s = s.replace(BACKSLASH + BACKSLASH, ' ')
    s = s.replace(BACKSLASH + '|', '‖').replace(BACKSLASH + ',', ' ')
    s = s.replace(BACKSLASH + ';', ' ').replace(BACKSLASH + '!', '')
    s = s.replace(BACKSLASH + ' ', ' ')
    s = re.sub(RE_BS + r'(left|right)\s*', '', s)

    def cmd(m):
        name = m.group(1)
        # Wrapper stripping runs first, so a command can end up glued to the text
        # that followed it: \Delta\text{MAE} becomes \DeltaMAE. Match the longest
        # known command that prefixes the captured name.
        for length in range(len(name), 0, -1):
            head, tail = name[:length], name[length:]
            if head in GREEK:
                return GREEK[head] + tail
            if head in SYMBOLS:
                return SYMBOLS[head] + tail
            if head in FUNCTIONS:
                return head + tail
        return m.group(0)

    s = CMD_RE.sub(cmd, s)
    s = _script(s, '^', SUPERSCRIPT)
    s = _script(s, '_', SUBSCRIPT)
    s = s.replace('{', '').replace('}', '')
    # the degree sign already reads as a superscript
    s = s.replace('^°', '°')
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def convert(text, leftovers):
    """Replace display and inline math, recording unconverted commands."""
    def do(expr):
        out = latex_to_unicode(expr)
        for m in CMD_RE.finditer(out):
            leftovers[m.group(1)] += 1
        return out

    # display math first so $$ is not eaten by the inline pattern
    text = re.sub(r'\$\$(.+?)\$\$', lambda m: do(m.group(1)), text, flags=re.S)
    text = re.sub(r'\$([^$\n]+?)\$', lambda m: do(m.group(1)), text)
    return text


def main():
    ap = argparse.ArgumentParser(
        description='Render a repo Markdown doc into a Drive-friendly copy (LaTeX -> Unicode).',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python export_for_drive.py --input ../../docs/Project_documentation/technical_documentation.md \\
      --output ../../docs/Project_documentation/drive_upload/technical_documentation_for_drive.md

  # report what would not convert, write nothing
  python export_for_drive.py --input technical_documentation.md --check
""")
    ap.add_argument('--input', required=True)
    ap.add_argument('--output')
    ap.add_argument('--check', action='store_true',
                    help='report conversion coverage, write nothing')
    args = ap.parse_args()

    src = Path(args.input)
    if not src.exists():
        raise FileNotFoundError(f'Not found: {src}')

    raw = src.read_text(encoding='utf-8')
    before = raw.count('$')
    leftovers = Counter()
    out = convert(raw, leftovers)
    after = out.count('$')

    print(f'input : {src}')
    print(f'  math delimiters before : {before}')
    print(f'  math delimiters after  : {after}')
    if leftovers:
        print('  UNCONVERTED LaTeX commands (add to the symbol table if they matter):')
        for name, n in leftovers.most_common():
            print(f'    {BACKSLASH}{name}  x{n}')
    else:
        print('  no unconverted LaTeX commands')

    if args.check:
        return 0
    if not args.output:
        ap.error('--output is required unless --check is given')

    dst = Path(args.output)
    dst.parent.mkdir(parents=True, exist_ok=True)
    header = (
        '<!-- GENERATED FILE - DO NOT EDIT -->\n'
        '<!-- Source of truth: docs/Project_documentation/technical_documentation.md -->\n'
        f'<!-- Regenerate: python utils/export_for_drive.py --input {src.name} --output {dst.name} -->\n\n')
    dst.write_text(header + out, encoding='utf-8')
    print(f'output: {dst}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
