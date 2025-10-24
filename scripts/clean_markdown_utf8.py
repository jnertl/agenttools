import sys

def clean_markdown_utf8(input_file, output_file):
    # Define replacements: add more as needed
    replacements = {
        '\u202f': ' ',   # narrow no-break space
        '\u00a0': ' ',   # non-breaking space
        '\u2011': '-',   # non-breaking hyphen
        '\u2013': '-',   # en dash
        '\u2014': '-',   # em dash
        '\u2018': "'",   # left single quote
        '\u2019': "'",   # right single quote
        '\u201c': '"',   # left double quote
        '\u201d': '"',   # right double quote
        'â€‘': '-',      # mojibake for non-breaking hyphen
        'â€¯': ' ',      # common mojibake for narrow no-break space
        'â€“': '-',      # mojibake for en dash
        'â€”': '-',      # mojibake for em dash
        'â€˜': "'",      # mojibake for left single quote
        'â€™': "'",      # mojibake for right single quote
        'â€œ': '"',      # mojibake for left double quote
        'â€�': '"',      # mojibake for right double quote
    }

    with open(input_file, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    for bad, good in replacements.items():
        content = content.replace(bad, good)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python clean_markdown_utf8.py input.md output.md")
        sys.exit(1)
    clean_markdown_utf8(sys.argv[1], sys.argv[2])