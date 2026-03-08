# micron_converter.py
# -*- coding: utf-8 -*-

import re


class MicronConverter:
    r"""High-performance ANSI → MicronMU converter."""

    ANSI_REGEX = re.compile(r'\x1b\[(?P<codes>[\d;]*)m')

    ANSI_FG = {
        30: '000', 31: 'f00', 32: '0f0', 33: 'ff0',
        34: '00f', 35: 'f0f', 36: '0ff', 37: 'fff'
    }

    ANSI_BG = {
        40: '000', 41: 'f00', 42: '0f0', 43: 'ff0',
        44: '00f', 45: 'f0f', 46: '0ff', 47: 'fff'
    }

    def __init__(self):
        self.reset_state()

    def reset_state(self):
        self.fg = None
        self.bg = None
        self.bold = False
        self.italic = False
        self.underline = False

    def _is_plain(self):
        return (
            self.fg is None and
            self.bg is None and
            not self.bold and
            not self.italic and
            not self.underline
        )

    @staticmethod
    def _to_3hex(r, g, b):
        return f'{r>>4:x}{g>>4:x}{b>>4:x}'

    @staticmethod
    def ansi_256_to_3hex(n):

        n = int(n)

        if n < 16:
            colors = [
                (0,0,0),(128,0,0),(0,128,0),(128,128,0),
                (0,0,128),(128,0,128),(0,128,128),(192,192,192),
                (128,128,128),(255,0,0),(0,255,0),(255,255,0),
                (0,0,255),(255,0,255),(0,255,255),(255,255,255)
            ]
            return MicronConverter._to_3hex(*colors[n])

        elif 16 <= n <= 231:

            n -= 16
            r = n // 36
            g = (n % 36) // 6
            b = n % 6

            return MicronConverter._to_3hex(r*51, g*51, b*51)

        elif 232 <= n <= 255:

            gray = (n - 232) * 10 + 8
            return MicronConverter._to_3hex(gray, gray, gray)

        return 'fff'

    def _apply_codes(self, codes):

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

            elif code == 3:
                self.italic = True

            elif code == 4:
                self.underline = True

            elif 30 <= code <= 37:
                self.fg = self.ANSI_FG.get(code, 'fff')

            elif 40 <= code <= 47:
                self.bg = self.ANSI_BG.get(code, '000')

            elif code == 39:
                self.fg = None

            elif code == 49:
                self.bg = None

            elif code in (38, 48) and i + 2 < len(codes):

                if codes[i+1] == '5':

                    n = codes[i+2]
                    hex_color = self.ansi_256_to_3hex(n)

                    if code == 38:
                        self.fg = hex_color
                    else:
                        self.bg = hex_color

                    i += 2

                elif codes[i+1] == '2' and i + 4 < len(codes):

                    r = int(codes[i+2])
                    g = int(codes[i+3])
                    b = int(codes[i+4])

                    hex_color = self._to_3hex(r, g, b)

                    if code == 38:
                        self.fg = hex_color
                    else:
                        self.bg = hex_color

                    i += 4

            i += 1

    def _generate_codes(self, last_state):

        codes = ''

        last_fg, last_bg, last_bold, last_italic, last_underline = last_state

        if self._is_plain() and (
            last_fg is not None or
            last_bg is not None or
            last_bold or
            last_italic or
            last_underline
        ):
            return '`f', (None, None, False, False, False)

        if self.fg != last_fg:
            if self.fg:
                codes += f'`F{self.fg}'
            last_fg = self.fg

        if self.bg != last_bg:
            if self.bg:
                codes += f'`B{self.bg}'
            last_bg = self.bg

        if self.bold != last_bold:
            if self.bold:
                codes += '`!'
            last_bold = self.bold

        if self.italic != last_italic:
            if self.italic:
                codes += '`*'
            last_italic = self.italic

        if self.underline != last_underline:
            if self.underline:
                codes += '`_'
            last_underline = self.underline

        return codes, (last_fg, last_bg, last_bold, last_italic, last_underline)

    def _escape(self, text):

        text = text.replace("\\", "\\\\")
        text = text.replace('"', '\\"')
        return text

    def convert(self, text, triple_quotes=False):

        output = []

        lines = text.splitlines()

        for line in lines:

            self.reset_state()
            last_state = (None, None, False, False, False)

            pos = 0
            line_output = []

            for match in self.ANSI_REGEX.finditer(line):

                start, end = match.span()

                segment = line[pos:start]

                if segment:

                    codes, last_state = self._generate_codes(last_state)
                    line_output.append(codes)
                    line_output.append(self._escape(segment))

                codes_list = match.group('codes').split(';')
                self._apply_codes(codes_list)

                pos = end

            segment = line[pos:]

            if segment:

                codes, last_state = self._generate_codes(last_state)
                line_output.append(codes)
                line_output.append(self._escape(segment))

            line_output.append('`f')

            line_str = ''.join(line_output)

            if triple_quotes:
                output.append(f'"""{line_str}"""')
            else:
                output.append(line_str)

        return "\n".join(output) + "\n"

    def MUPrint(self, text, triple_quotes=False):
        print(self.convert(text, triple_quotes))
