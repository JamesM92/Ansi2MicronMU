# converter.py
# -*- coding: utf-8 -*-
"""
Converts ANSI-formatted text to Nomadnet Micro Markup (MicronMU) format.
Supports 8-colour (+ bright), 256-colour, and 24-bit ANSI sequences.
Formatting codes are only emitted when state actually changes, minimising
output size for bandwidth-constrained transport.
"""
from __future__ import annotations

import re

__all__ = ["MicronConverter"]

# Represents fully plain (no active formatting).  Used as the initial
# last_state and as the target for full-reset detection.
_PLAIN: tuple[str | None, str | None, bool, bool, bool] = (None, None, False, False, False)

# MicronMU line-start characters that trigger structural interpretation:
#   #  → comment (entire line is dropped)
#   >  → section heading
#   <  → section depth reset
#   -  → horizontal divider (triggered for any line starting with -)
_LINE_SPECIALS = frozenset(('#', '>', '<', '-'))

# Matches ANSI CSI sequences that are NOT SGR (i.e. do not end with 'm').
# These include cursor movement, erase, and other control codes that carry
# no meaning in MicronMU and must be removed before conversion.
# Pattern: ESC '[' <parameter bytes 0x20-0x3F>* <final byte 0x40-0x7E except 'm'>
_ANSI_NON_SGR_RE = re.compile(r'\x1b\[[\x20-\x3f]*[\x40-\x6c\x6e-\x7e]')

# Matches bare ESC sequences (ESC + any character that is not '[').
# Covers save/restore cursor (\x1b7 / \x1b8), reverse line-feed (\x1bM), etc.
_ANSI_BARE_ESC_RE = re.compile(r'\x1b[^\[]')


class MicronConverter:
    r"""ANSI → MicronMU converter.

    All colours are output as 3-char hex (``\`F<rgb>`` / ``\`B<rgb>``).
    24-bit and 256-colour ANSI inputs are quantised to the nearest 3-hex
    value.  Formatting codes are suppressed whenever the rendered state has
    not changed, so identical adjacent segments produce no redundant tokens.
    State carries across line boundaries — no re-emission at line starts.

    Usage::

        converter = MicronConverter()
        micron_text = converter.convert(ansi_text)
    """

    ANSI_REGEX = re.compile(r'\x1b\[(?P<codes>[\d;]*)m')

    # Standard 8-colour fg/bg palettes (codes 30-37, 40-47)
    ANSI_FG = {
        30: '000', 31: 'f00', 32: '0f0', 33: 'ff0',
        34: '00f', 35: 'f0f', 36: '0ff', 37: 'fff',
    }
    ANSI_BG = {
        40: '000', 41: 'f00', 42: '0f0', 43: 'ff0',
        44: '00f', 45: 'f0f', 46: '0ff', 47: 'fff',
    }
    # Bright variants (codes 90-97, 100-107)
    ANSI_FG_BRIGHT = {
        90: '888', 91: 'f88', 92: '8f8', 93: 'ff8',
        94: '88f', 95: 'f8f', 96: '8ff', 97: 'fff',
    }
    ANSI_BG_BRIGHT = {
        100: '888', 101: 'f88', 102: '8f8', 103: 'ff8',
        104: '88f', 105: 'f8f', 106: '8ff', 107: 'fff',
    }

    def __init__(self) -> None:
        self.reset_state()

    def reset_state(self) -> None:
        self.fg        = None
        self.bg        = None
        self.bold      = False
        self.italic    = False
        self.underline = False

    def _snapshot(self) -> tuple[str | None, str | None, bool, bool, bool]:
        """Return current ANSI state as a comparable tuple."""
        return (self.fg, self.bg, self.bold, self.italic, self.underline)

    @staticmethod
    def _to_3hex(r: int, g: int, b: int) -> str:
        # MicronMU doubles each nibble (e.g. 'c' → #cccccc = 204), so the
        # correct quantisation target spacing is 17, not 16.  round(x/17)
        # minimises the error to the actual rendered colour.
        return (
            f'{min(15, round(r / 17)):x}'
            f'{min(15, round(g / 17)):x}'
            f'{min(15, round(b / 17)):x}'
        )

    @staticmethod
    def ansi_256_to_3hex(n: int | str) -> str:
        n = int(n)

        if n < 16:
            colors = [
                (  0,   0,   0), (128,   0,   0), (  0, 128,   0), (128, 128,   0),
                (  0,   0, 128), (128,   0, 128), (  0, 128, 128), (192, 192, 192),
                (128, 128, 128), (255,   0,   0), (  0, 255,   0), (255, 255,   0),
                (  0,   0, 255), (255,   0, 255), (  0, 255, 255), (255, 255, 255),
            ]
            return MicronConverter._to_3hex(*colors[n])

        if 16 <= n <= 231:
            n -= 16
            r  = n // 36
            g  = (n % 36) // 6
            b  = n % 6
            return MicronConverter._to_3hex(r * 51, g * 51, b * 51)

        if 232 <= n <= 255:
            gray = (n - 232) * 10 + 8
            return MicronConverter._to_3hex(gray, gray, gray)

        return 'fff'

    def _apply_codes(self, codes: list[str]) -> None:
        # Bare \033[m (no parameters) = full reset
        if codes == ['']:
            self.reset_state()
            return

        i = 0
        while i < len(codes):
            if codes[i] == '':
                i += 1
                continue

            code = int(codes[i])

            if code == 0:
                self.reset_state()
            elif code == 1:
                self.bold = True
            elif code == 22:               # bold/dim off
                self.bold = False
            elif code == 3:
                self.italic = True
            elif code == 23:               # italic off
                self.italic = False
            elif code == 4:
                self.underline = True
            elif code == 24:               # underline off
                self.underline = False
            elif 30 <= code <= 37:
                self.fg = self.ANSI_FG.get(code, 'fff')
            elif 40 <= code <= 47:
                self.bg = self.ANSI_BG.get(code, '000')
            elif 90 <= code <= 97:
                self.fg = self.ANSI_FG_BRIGHT.get(code, 'fff')
            elif 100 <= code <= 107:
                self.bg = self.ANSI_BG_BRIGHT.get(code, '000')
            elif code == 39:
                self.fg = None
            elif code == 49:
                self.bg = None
            elif code in (38, 48) and i + 2 < len(codes):
                if codes[i + 1] == '5':
                    hex_color = self.ansi_256_to_3hex(codes[i + 2])
                    if code == 38:
                        self.fg = hex_color
                    else:
                        self.bg = hex_color
                    i += 2
                elif codes[i + 1] == '2' and i + 4 < len(codes):
                    r = int(codes[i + 2])
                    g = int(codes[i + 3])
                    b = int(codes[i + 4])
                    hex_color = self._to_3hex(r, g, b)
                    if code == 38:
                        self.fg = hex_color
                    else:
                        self.bg = hex_color
                    i += 4

            i += 1

    @staticmethod
    def _generate_codes(
        from_state: tuple[str | None, str | None, bool, bool, bool],
        to_state: tuple[str | None, str | None, bool, bool, bool],
    ) -> str:
        """Return the MicronMU token string to transition from_state → to_state.

        Returns an empty string when the states are identical (no output
        needed).  Uses double-backtick full reset when transitioning to plain,
        and targeted per-attribute codes otherwise.
        """
        if from_state == to_state:
            return ''

        # Double-backtick resets fg + bg + bold + italic + underline at once.
        # (`f only resets fg — insufficient for a full reset.)
        if to_state == _PLAIN:
            return '``'

        from_fg, from_bg, from_bold, from_italic, from_underline = from_state
        to_fg,   to_bg,   to_bold,   to_italic,   to_underline   = to_state

        codes = ''

        if to_fg != from_fg:
            codes += f'`F{to_fg}' if to_fg else '`f'

        if to_bg != from_bg:
            codes += f'`B{to_bg}' if to_bg else '`b'

        # Bold, italic, underline use toggle codes — emit on any change in
        # either direction (MicronMU `! / `* / `_ are pure toggles).
        if to_bold != from_bold:
            codes += '`!'

        if to_italic != from_italic:
            codes += '`*'

        if to_underline != from_underline:
            codes += '`_'

        return codes

    @staticmethod
    def _escape(text: str) -> str:
        r"""Escape inline MicronMU special characters.

        ``\`` is the MicronMU escape prefix; `` ` `` opens a formatting
        sequence.  Both must be escaped to render literally.
        Backslash is escaped first to avoid double-escaping.
        """
        return text.replace('\\', '\\\\').replace('`', '\\`')

    @staticmethod
    def _escape_line_start(line: str) -> str:
        r"""Prefix *line* with ``\`` when its first character would trigger a
        MicronMU structural interpretation (comment, heading, depth-reset,
        or divider).  Lines that begin with a backtick (i.e. a formatting
        code) are already safe and left unchanged.
        """
        if line and line[0] in _LINE_SPECIALS:
            return '\\' + line
        return line

    def convert(
        self,
        text: str,
        triple_quotes: bool = False,
        trailing_newline: bool = True,
        literal_mode: bool = False,
    ) -> str:
        """Convert an ANSI-formatted string to MicronMU markup.

        Formatting codes are only emitted when the rendered state changes.
        State carries across line boundaries, so identical formatting at a
        line boundary produces no redundant tokens.

        Args:
            text:             Input string containing ANSI escape sequences.
            triple_quotes:    Wrap each output line in triple-quote blocks.
            trailing_newline: Append ``\\n`` at the end of the result
                              (default True for backwards compatibility).
            literal_mode:     Strip all ANSI codes and wrap the entire output
                              in ``\\`=`` literal blocks.  No inline formatting
                              is produced, but every character is safe — no
                              escaping required and no MicronMU tokens can
                              interfere.  Useful for plain ASCII art.

        Returns:
            MicronMU-formatted string.
        """
        # Remove non-SGR control sequences (cursor movement, erase, etc.)
        # before any further processing — they have no MicronMU equivalent
        # and would otherwise appear as raw ESC bytes in the output.
        text = _ANSI_NON_SGR_RE.sub('', text)
        text = _ANSI_BARE_ESC_RE.sub('', text)

        if literal_mode:
            plain  = self.ANSI_REGEX.sub('', text)
            result = '`=\n' + plain + '\n`='
            return result + ('\n' if trailing_newline else '')

        output     = []
        last_state = _PLAIN  # persists across lines — MicronMU state carries

        for line in text.splitlines():
            # ── First pass: collect (render_state, text_segment) pairs ──────
            # Reset ANSI tracking so this line's codes are parsed fresh,
            # but last_state is NOT reset — it carries from the previous line.
            self.reset_state()
            segments = []
            pos = 0

            for match in self.ANSI_REGEX.finditer(line):
                start, end = match.span()
                segment    = line[pos:start]
                if segment:
                    segments.append((self._snapshot(), segment))
                self._apply_codes(match.group('codes').split(';'))
                pos = end

            tail = line[pos:]
            if tail:
                segments.append((self._snapshot(), tail))

            # ── Second pass: emit only on actual state changes ───────────────
            line_output = []
            for render_state, seg_text in segments:
                codes = self._generate_codes(last_state, render_state)
                if codes:
                    line_output.append(codes)
                    last_state = render_state
                line_output.append(self._escape(seg_text))

            line_str = self._escape_line_start(''.join(line_output))

            if triple_quotes:
                output.append(f'"""{line_str}"""')
            else:
                output.append(line_str)

        # Close any formatting still active after the final line
        if last_state != _PLAIN and output:
            output[-1] += '``'

        result = "\n".join(output)
        return result + "\n" if trailing_newline else result

    # ── Utility helpers ──────────────────────────────────────────────────────
    # These produce MicronMU markup strings and do not require ANSI input.

    @staticmethod
    def heading(text: str, level: int = 1) -> str:
        """Return a MicronMU heading string.

        Args:
            text:  Heading content.
            level: Depth 1–3 (default 1); clamped to valid range.
        """
        level = max(1, min(3, int(level)))
        return '>' * level + text

    @staticmethod
    def divider(char: str | None = None) -> str:
        """Return a MicronMU horizontal divider line.

        Args:
            char: Divider character (default: ``─`` box-drawing line).
                  Only the first character of *char* is used.
        """
        if char is None:
            return '-'
        return '-' + char[0]

    @staticmethod
    def link(label: str, url: str, fields: str | None = None) -> str:
        """Return a MicronMU hyperlink.

        Args:
            label:  Display text for the link.
            url:    Link destination (Nomadnet page path or LXMF address).
            fields: Optional field string for pre-filled form data.
        """
        if fields:
            return f'`[{label}`{url}`{fields}]'
        return f'`[{label}`{url}]'

    @staticmethod
    def colored(text: str, fg: str | None = None, bg: str | None = None) -> str:
        """Wrap *text* in MicronMU colour codes followed by a full reset.

        Args:
            text: Text to colour.
            fg:   Foreground as a 3-char hex string (e.g. ``'f80'``).
            bg:   Background as a 3-char hex string.
        """
        prefix = ''
        if fg:
            prefix += f'`F{fg}'
        if bg:
            prefix += f'`B{bg}'
        return (prefix + text + '``') if prefix else text

    @staticmethod
    def aligned(text: str, alignment: str = 'center') -> str:
        """Wrap *text* with MicronMU alignment codes.

        Args:
            text:      Text to align.
            alignment: ``'center'``, ``'left'``, or ``'right'`` (default centre).
        """
        code = {'center': 'c', 'left': 'l', 'right': 'r'}.get(alignment, 'c')
        return f'`{code}{text}`a'

    @staticmethod
    def strip_ansi(text: str) -> str:
        """Return *text* with all ANSI escape sequences removed.

        Strips both SGR colour/attribute codes and non-SGR control sequences
        (cursor movement, erase, etc.), leaving only the printable characters.
        """
        text = _ANSI_NON_SGR_RE.sub('', text)
        text = _ANSI_BARE_ESC_RE.sub('', text)
        return MicronConverter.ANSI_REGEX.sub('', text)

    def mu_print(self, text: str, triple_quotes: bool = False) -> None:
        """Print the MicronMU conversion of *text* to stdout."""
        print(self.convert(text, triple_quotes))

    # Backwards-compatible alias
    MUPrint = mu_print
