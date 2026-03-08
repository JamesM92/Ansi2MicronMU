# demo.py
from micron_converter import MicronConverter

mc = MicronConverter()

STYLES = {
    'Normal': '',
    'Bold': '1',
    'Italic': '3',
    'Underline': '4',
    'Bold+Italic': '1;3',
    'Bold+Underline': '1;4',
    'Italic+Underline': '3;4',
    'Bold+Italic+Underline': '1;3;4'
}

COLORS_8 = {
    'Black': 30, 'Red': 31, 'Green': 32, 'Yellow': 33,
    'Blue': 34, 'Magenta': 35, 'Cyan': 36, 'White': 37
}

COLORS_256 = {
    'Orange': 202, 'BrightG': 46, 'Blue': 21, 'Pink': 213
}

COLORS_TRUE = {
    'Pink': (255,105,180),
    'SeaGrn': (60,179,113),
    'SteelB': (70,130,180)
}

print("=== MicronMU Style + Color Table ===\n")

# 8-color ANSI with styles
print("**8-color ANSI with Styles**")
for style_name, style_code in STYLES.items():
    line = f"{style_name:20}: "
    for color_name, color_code in COLORS_8.items():
        label = color_name[:6]
        ansi = f"\x1b[{style_code};{color_code}m{label}\x1b[0m"
        line += mc.convert(ansi) + " "
    print(line)

# 256-color ANSI with styles
print("\n**256-color ANSI with Styles**")
for style_name, style_code in STYLES.items():
    line = f"{style_name:20}: "
    for color_name, color_index in COLORS_256.items():
        label = color_name[:6]
        ansi = f"\x1b[{style_code};38;5;{color_index}m{label}\x1b[0m"
        line += mc.convert(ansi) + " "
    print(line)

# Truecolor ANSI with styles
print("\n**24-bit Truecolor ANSI with Styles**")
for style_name, style_code in STYLES.items():
    line = f"{style_name:20}: "
    for color_name, (r,g,b) in COLORS_TRUE.items():
        label = color_name[:6]
        ansi = f"\x1b[{style_code};38;2;{r};{g};{b}m{label}\x1b[0m"
        line += mc.convert(ansi) + " "
    print(line)

print("\n=== End of MicronMU Style Table ===")
