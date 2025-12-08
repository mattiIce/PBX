# Executive Summary PDF Generation

## Overview

This directory contains a script to generate a PDF version of the Executive Summary from the Markdown source file.

## Files

- `generate_executive_summary_pdf.py` - Python script that converts EXECUTIVE_SUMMARY.md to EXECUTIVE_SUMMARY.pdf

## Requirements

### System Dependencies

The script requires the following system packages to be installed:

```bash
# Ubuntu/Debian
sudo apt-get install pandoc wkhtmltopdf

# macOS
brew install pandoc
brew install --cask wkhtmltopdf
```

### Python

- Python 3.7 or higher (no additional Python packages required)

## Usage

### Generate PDF

Run the script from the repository root:

```bash
python3 scripts/generate_executive_summary_pdf.py
```

Or run it directly if it's executable:

```bash
./scripts/generate_executive_summary_pdf.py
```

### Output

The script will:
1. Read `EXECUTIVE_SUMMARY.md` from the repository root
2. Convert it to PDF format with proper styling
3. Save the output as `EXECUTIVE_SUMMARY.pdf` in the repository root

The generated PDF includes:
- Table of contents (up to 3 levels deep)
- Proper formatting for headers, tables, and code blocks
- 1-inch margins on all sides
- Embedded hyperlinks
- Support for Unicode characters (including emojis ✅)

## PDF Features

The generated PDF includes:
- **Table of Contents**: Automatically generated with clickable links
- **Headers**: Properly formatted section headers
- **Tables**: All markdown tables converted to PDF tables
- **Code Blocks**: Syntax-highlighted code blocks
- **Lists**: Bullet points and numbered lists
- **Links**: Clickable hyperlinks to external URLs and internal sections
- **Unicode Support**: Full support for emoji and special characters

## Technical Details

### PDF Engine

The script uses `wkhtmltopdf` as the PDF rendering engine through Pandoc. This engine was chosen because:
- Better Unicode/emoji support compared to LaTeX
- Handles complex HTML/CSS rendering
- Produces high-quality PDFs from Markdown
- Widely available and well-maintained

### Pandoc Options

The script uses the following Pandoc options:
- `--pdf-engine=wkhtmltopdf` - Use wkhtmltopdf for rendering
- `--toc` - Generate table of contents
- `--toc-depth=3` - Include up to 3 levels in TOC
- `-V margin-*=1in` - Set 1-inch margins
- `--metadata` - Set title, author, and date metadata

## Troubleshooting

### pandoc: command not found

Install pandoc:
```bash
sudo apt-get install pandoc
```

### wkhtmltopdf: command not found

Install wkhtmltopdf:
```bash
sudo apt-get install wkhtmltopdf
```

### Error producing PDF

If you encounter errors during PDF generation:
1. Verify all dependencies are installed
2. Check that the input file (EXECUTIVE_SUMMARY.md) exists
3. Ensure you have write permissions in the repository root
4. Check the error message for specific issues

### PDF quality issues

If the PDF doesn't look right:
- Verify the Markdown source is properly formatted
- Check that tables are using proper Markdown table syntax
- Ensure code blocks use proper fenced code block syntax (```)

## Automation

### CI/CD Integration

To automatically generate the PDF in CI/CD pipelines, add this to your workflow:

```yaml
- name: Install dependencies
  run: |
    sudo apt-get update
    sudo apt-get install -y pandoc wkhtmltopdf

- name: Generate PDF
  run: python3 scripts/generate_executive_summary_pdf.py
```

### Git Hooks

To automatically regenerate the PDF before commits, add a pre-commit hook:

```bash
#!/bin/bash
# .git/hooks/pre-commit
python3 scripts/generate_executive_summary_pdf.py
git add EXECUTIVE_SUMMARY.pdf
```

## Maintenance

### Updating the PDF

Whenever EXECUTIVE_SUMMARY.md is updated:
1. Run the script to regenerate the PDF
2. Review the PDF to ensure formatting is correct
3. Commit both the Markdown and PDF files together

### Script Modifications

If you need to modify the PDF generation:
- Edit `generate_executive_summary_pdf.py`
- Adjust the `pandoc_cmd` parameters for different styling
- Test thoroughly after changes

## Alternative Approaches

If the current approach doesn't meet your needs:

### Using LaTeX Engine (Better typography)

For better typography but requires preprocessing to handle emojis:
```python
"--pdf-engine=pdflatex"
```

### Using Prince XML (Commercial)

For advanced layout control (requires license):
```bash
prince EXECUTIVE_SUMMARY.html -o EXECUTIVE_SUMMARY.pdf
```

### Using WeasyPrint (Pure Python)

For a pure Python solution:
```bash
pip install weasyprint
weasyprint EXECUTIVE_SUMMARY.html EXECUTIVE_SUMMARY.pdf
```

## License

This script is part of the Aluminum Blanking PBX System and follows the same license as the main project.
