"""Tests for ansi2micron.MicronConverter."""
import pytest
from ansi2micron import MicronConverter


ESC = '\x1b'


def ansi(*codes, text='X', reset=True):
    """Build an ANSI-escaped string for use in tests."""
    code_str = ';'.join(str(c) for c in codes)
    suffix = f'{ESC}[0m' if reset else ''
    return f'{ESC}[{code_str}m{text}{suffix}'


@pytest.fixture
def mc():
    return MicronConverter()


# ── Plain text ────────────────────────────────────────────────────────────────

class TestPlainText:
    def test_passthrough(self, mc):
        assert mc.convert('hello', trailing_newline=False) == 'hello'

    def test_empty_string(self, mc):
        assert mc.convert('', trailing_newline=False) == ''

    def test_trailing_newline_true(self, mc):
        assert mc.convert('hi').endswith('\n')

    def test_trailing_newline_false(self, mc):
        assert not mc.convert('hi', trailing_newline=False).endswith('\n')

    def test_multiline(self, mc):
        result = mc.convert('a\nb', trailing_newline=False)
        assert result == 'a\nb'


# ── Escaping ──────────────────────────────────────────────────────────────────

class TestEscaping:
    def test_backslash_escaped(self, mc):
        result = mc.convert('a\\b', trailing_newline=False)
        assert result == 'a\\\\b'

    def test_backtick_escaped(self, mc):
        result = mc.convert('a`b', trailing_newline=False)
        assert result == 'a\\`b'

    def test_hash_at_line_start_escaped(self, mc):
        result = mc.convert('#comment', trailing_newline=False)
        assert result.startswith('\\#')

    def test_gt_at_line_start_escaped(self, mc):
        result = mc.convert('>heading', trailing_newline=False)
        assert result.startswith('\\>')

    def test_lt_at_line_start_escaped(self, mc):
        result = mc.convert('<reset', trailing_newline=False)
        assert result.startswith('\\<')

    def test_dash_at_line_start_escaped(self, mc):
        result = mc.convert('-divider', trailing_newline=False)
        assert result.startswith('\\-')

    def test_special_char_mid_line_not_escaped(self, mc):
        result = mc.convert('a#b', trailing_newline=False)
        assert result == 'a#b'


# ── 8-colour ANSI ─────────────────────────────────────────────────────────────

class TestEightColor:
    def test_fg_red(self, mc):
        result = mc.convert(ansi(31, text='hi', reset=False), trailing_newline=False)
        assert '`Ff00' in result

    def test_fg_green(self, mc):
        result = mc.convert(ansi(32, text='hi', reset=False), trailing_newline=False)
        assert '`F0f0' in result

    def test_bg_blue(self, mc):
        result = mc.convert(ansi(44, text='hi', reset=False), trailing_newline=False)
        assert '`B00f' in result

    def test_bright_fg_red(self, mc):
        result = mc.convert(ansi(91, text='hi', reset=False), trailing_newline=False)
        assert '`Ff88' in result

    def test_bright_bg_green(self, mc):
        result = mc.convert(ansi(102, text='hi', reset=False), trailing_newline=False)
        assert '`B8f8' in result

    def test_reset_emits_double_backtick(self, mc):
        result = mc.convert(ansi(31, text='hi'), trailing_newline=False)
        assert '``' in result

    def test_fg_default_code_39(self, mc):
        # Set fg then clear with 39 — state returns to _PLAIN → double-backtick reset
        result = mc.convert(f'{ESC}[31mhi{ESC}[39m', trailing_newline=False)
        assert '`Ff00' in result  # colour was set
        assert '``' in result     # and then fully reset


# ── 256-colour ────────────────────────────────────────────────────────────────

class TestColor256:
    def test_system_color_black(self, mc):
        assert MicronConverter.ansi_256_to_3hex(0) == '000'

    def test_system_color_white(self, mc):
        assert MicronConverter.ansi_256_to_3hex(15) == 'fff'

    def test_color_cube_pure_red(self, mc):
        # Index 196 = 6x6x6 cube position (5,0,0) → rgb(255,0,0)
        assert MicronConverter.ansi_256_to_3hex(196) == 'f00'

    def test_color_cube_pure_blue(self, mc):
        # Index 21 = 6x6x6 cube position (0,0,5) → rgb(0,0,255)
        assert MicronConverter.ansi_256_to_3hex(21) == '00f'

    def test_grayscale_low(self, mc):
        # Index 232 → gray level 8 → 3-hex
        result = MicronConverter.ansi_256_to_3hex(232)
        assert len(result) == 3
        assert result[0] == result[1] == result[2]  # equal channels = gray

    def test_grayscale_high(self, mc):
        # Index 255 → gray level 238
        result = MicronConverter.ansi_256_to_3hex(255)
        assert result[0] == result[1] == result[2]

    def test_string_input(self, mc):
        # Called with string codes from ANSI parser
        assert MicronConverter.ansi_256_to_3hex('196') == 'f00'

    def test_256_in_convert(self, mc):
        result = mc.convert(f'{ESC}[38;5;196mhi{ESC}[0m', trailing_newline=False)
        assert '`Ff00' in result


# ── 24-bit truecolor ──────────────────────────────────────────────────────────

class TestTruecolor:
    def test_pure_red(self, mc):
        result = mc.convert(f'{ESC}[38;2;255;0;0mhi{ESC}[0m', trailing_newline=False)
        assert '`Ff00' in result

    def test_pure_green(self, mc):
        result = mc.convert(f'{ESC}[38;2;0;255;0mhi{ESC}[0m', trailing_newline=False)
        assert '`F0f0' in result

    def test_mid_gray(self, mc):
        result = mc.convert(f'{ESC}[38;2;128;128;128mhi{ESC}[0m', trailing_newline=False)
        assert '`F888' in result

    def test_to_3hex_quantisation(self):
        # 255 → f, 0 → 0, 128 → 8 (round(128/17) = 8)
        assert MicronConverter._to_3hex(255, 0, 128) == 'f08'

    def test_to_3hex_clamps_at_f(self):
        assert MicronConverter._to_3hex(255, 255, 255) == 'fff'


# ── Text styles ───────────────────────────────────────────────────────────────

class TestStyles:
    def test_bold(self, mc):
        result = mc.convert(ansi(1, text='hi', reset=False), trailing_newline=False)
        assert '`!' in result

    def test_italic(self, mc):
        result = mc.convert(ansi(3, text='hi', reset=False), trailing_newline=False)
        assert '`*' in result

    def test_underline(self, mc):
        result = mc.convert(ansi(4, text='hi', reset=False), trailing_newline=False)
        assert '`_' in result

    def test_bold_off_code_22(self, mc):
        # Bold on, then off with code 22 → state returns to _PLAIN → full reset
        result = mc.convert(f'{ESC}[1mhi{ESC}[22m', trailing_newline=False)
        assert '`!' in result   # bold was toggled on
        assert '``' in result   # then fully reset to plain

    def test_italic_off_code_23(self, mc):
        # Italic on, then off with code 23 → full reset
        result = mc.convert(f'{ESC}[3mhi{ESC}[23m', trailing_newline=False)
        assert '`*' in result
        assert '``' in result

    def test_underline_off_code_24(self, mc):
        # Underline on, then off with code 24 → full reset
        result = mc.convert(f'{ESC}[4mhi{ESC}[24m', trailing_newline=False)
        assert '`_' in result
        assert '``' in result

    def test_combined_bold_color(self, mc):
        result = mc.convert(ansi(1, 31, text='hi', reset=False), trailing_newline=False)
        assert '`!' in result
        assert '`Ff00' in result


# ── State optimisation ────────────────────────────────────────────────────────

class TestStateOptimisation:
    def test_no_redundant_codes_on_same_state(self, mc):
        # Two adjacent segments with the same colour → only one code emitted
        text = f'{ESC}[31mfoo{ESC}[31mbar{ESC}[0m'
        result = mc.convert(text, trailing_newline=False)
        assert result.count('`Ff00') == 1

    def test_state_carries_across_lines(self, mc):
        # Red set on line 1; line 2 also red — no re-emission on line 2
        text = f'{ESC}[31mfoo\nbar{ESC}[0m'
        result = mc.convert(text, trailing_newline=False)
        assert result.count('`Ff00') == 1

    def test_full_reset_to_plain_emits_double_backtick(self, mc):
        text = f'{ESC}[31mhi{ESC}[0m'
        result = mc.convert(text, trailing_newline=False)
        assert '``' in result

    def test_bare_sgr_reset(self, mc):
        text = f'{ESC}[31mhi{ESC}[m'
        result = mc.convert(text, trailing_newline=False)
        assert '``' in result


# ── Non-SGR sequence stripping ────────────────────────────────────────────────

class TestNonSgrStripping:
    def test_cursor_movement_stripped(self, mc):
        # ESC[2J is an erase-display command (non-SGR)
        result = mc.convert(f'{ESC}[2Jhello', trailing_newline=False)
        assert result == 'hello'

    def test_bare_esc_stripped(self, mc):
        result = mc.convert(f'{ESC}Mhello', trailing_newline=False)
        assert result == 'hello'


# ── Convert options ───────────────────────────────────────────────────────────

class TestConvertOptions:
    def test_triple_quotes(self, mc):
        result = mc.convert('hello', triple_quotes=True, trailing_newline=False)
        assert result == '"""hello"""'

    def test_triple_quotes_multiline(self, mc):
        result = mc.convert('a\nb', triple_quotes=True, trailing_newline=False)
        lines = result.split('\n')
        assert all(l.startswith('"""') and l.endswith('"""') for l in lines)

    def test_literal_mode_strips_ansi(self, mc):
        result = mc.convert(ansi(31, text='hi'), literal_mode=True, trailing_newline=False)
        assert '`Ff00' not in result
        assert 'hi' in result

    def test_literal_mode_wraps_in_literal_block(self, mc):
        result = mc.convert('hello', literal_mode=True, trailing_newline=False)
        assert result.startswith('`=')
        assert result.endswith('`=')

    def test_literal_mode_trailing_newline(self, mc):
        result = mc.convert('hello', literal_mode=True, trailing_newline=True)
        assert result.endswith('\n')


# ── Utility helpers ───────────────────────────────────────────────────────────

class TestUtilityHelpers:
    def test_heading_level1(self):
        assert MicronConverter.heading('Title') == '>Title'

    def test_heading_level2(self):
        assert MicronConverter.heading('Sub', level=2) == '>>Sub'

    def test_heading_level3(self):
        assert MicronConverter.heading('Deep', level=3) == '>>>Deep'

    def test_heading_clamped_below_1(self):
        assert MicronConverter.heading('X', level=0) == '>X'

    def test_heading_clamped_above_3(self):
        assert MicronConverter.heading('X', level=10) == '>>>X'

    def test_divider_default(self):
        assert MicronConverter.divider() == '-'

    def test_divider_custom_char(self):
        assert MicronConverter.divider('=') == '-='

    def test_divider_uses_first_char_only(self):
        assert MicronConverter.divider('==') == '-='

    def test_link_basic(self):
        assert MicronConverter.link('Click', '/page') == '`[Click`/page]'

    def test_link_with_fields(self):
        result = MicronConverter.link('Go', '/page', 'key=val')
        assert result == '`[Go`/page`key=val]'

    def test_colored_fg_only(self):
        result = MicronConverter.colored('hi', fg='f00')
        assert result == '`Ff00hi``'

    def test_colored_bg_only(self):
        result = MicronConverter.colored('hi', bg='00f')
        assert result == '`B00fhi``'

    def test_colored_fg_and_bg(self):
        result = MicronConverter.colored('hi', fg='f00', bg='00f')
        assert result == '`Ff00`B00fhi``'

    def test_colored_no_args_passthrough(self):
        assert MicronConverter.colored('hi') == 'hi'

    def test_aligned_center(self):
        assert MicronConverter.aligned('hi') == '`chi`a'

    def test_aligned_left(self):
        assert MicronConverter.aligned('hi', alignment='left') == '`lhi`a'

    def test_aligned_right(self):
        assert MicronConverter.aligned('hi', alignment='right') == '`rhi`a'

    def test_aligned_unknown_defaults_center(self):
        assert MicronConverter.aligned('hi', alignment='justify') == '`chi`a'

    def test_strip_ansi_removes_sgr(self):
        result = MicronConverter.strip_ansi(f'{ESC}[31mhello{ESC}[0m')
        assert result == 'hello'

    def test_strip_ansi_removes_non_sgr(self):
        result = MicronConverter.strip_ansi(f'{ESC}[2Jhello')
        assert result == 'hello'

    def test_strip_ansi_plain_text_unchanged(self):
        assert MicronConverter.strip_ansi('hello') == 'hello'


# ── mu_print / MUPrint alias ──────────────────────────────────────────────────

class TestMuPrint:
    def test_mu_print(self, mc, capsys):
        mc.mu_print('hello')
        captured = capsys.readouterr()
        assert 'hello' in captured.out

    def test_muprint_alias(self, mc, capsys):
        mc.MUPrint('hello')
        captured = capsys.readouterr()
        assert 'hello' in captured.out
