# ansi2micron

Convert ANSI escape sequences to [Nomadnet](https://github.com/markqvist/NomadNet) MicronMU markup.

Supports 8-colour (+ bright), 256-colour, and 24-bit ANSI sequences. Formatting codes are only emitted when state actually changes, minimising output size for bandwidth-constrained transport.

## Installation

**From PyPI** (once published):
```
pip install ansi2micron
```

**From GitHub** (current method):
```
pip install git+https://github.com/JamesM92/Ansi2MicronMU.git
```

**From a local clone:**
```
git clone https://github.com/JamesM92/Ansi2MicronMU.git
pip install ./Ansi2MicronMU
```

## Quick start

```python
from ansi2micron import MicronConverter

mc = MicronConverter()

ansi_text = "\x1b[1;32mHello\x1b[0m, world!"
print(mc.convert(ansi_text))
# `!`F0f0Hello``, world!
```

## API

### `MicronConverter.convert(text, *, triple_quotes=False, trailing_newline=True, literal_mode=False)`

Convert an ANSI-formatted string to MicronMU markup.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `text` | `str` | — | Input string containing ANSI escape sequences |
| `triple_quotes` | `bool` | `False` | Wrap each output line in `"""..."""` blocks |
| `trailing_newline` | `bool` | `True` | Append `\n` to the result |
| `literal_mode` | `bool` | `False` | Strip all ANSI and wrap output in `` `= `` literal blocks (safe for ASCII art) |

---

### Utility helpers

These produce MicronMU markup directly and do not require ANSI input.

```python
MicronConverter.heading(text, level=1)       # >text, >>text, >>>text
MicronConverter.divider(char=None)           # - or -<char>
MicronConverter.link(label, url, fields=None) # `[label`url] or `[label`url`fields]
MicronConverter.colored(text, fg=None, bg=None) # `Fff0text``
MicronConverter.aligned(text, alignment='center') # `ctext`a
MicronConverter.strip_ansi(text)             # Remove all ANSI sequences
```

---

### `MicronConverter.ansi_256_to_3hex(n)`

Convert a 256-colour palette index to a 3-char hex string (e.g. `'f80'`). Static method — can be called without an instance.

## Colour support

| ANSI type | Example | Notes |
|---|---|---|
| 8-colour | `\x1b[31m` | Maps to fixed MicronMU hex values |
| 8-colour bright | `\x1b[91m` | Bright variants |
| 256-colour | `\x1b[38;5;202m` | Quantised to nearest 3-hex |
| 24-bit truecolor | `\x1b[38;2;255;128;0m` | Quantised to nearest 3-hex |

MicronMU uses 3-hex colours where each hex digit is doubled for rendering (e.g. `f80` → `#ff8800`). Quantisation uses a divisor of 17 (not 16) to minimise perceptual error.

## License

GNU General Public License v3.0 — see [LICENSE](LICENSE).
