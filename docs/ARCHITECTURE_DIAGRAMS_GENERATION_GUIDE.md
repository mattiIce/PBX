# Architecture Diagrams - PDF Generation Guide

## Available Formats

### 1. Markdown Format (Primary)
**File:** `ARCHITECTURE_DIAGRAMS.md`

Contains all 19 diagrams in Mermaid syntax. This is the primary reference document.

**View:**
- Native rendering on GitHub (automatically displays all diagrams)
- Local Markdown editor with Mermaid support
- Mermaid CLI renderer

### 2. HTML Format (Interactive)
**File:** `ARCHITECTURE_DIAGRAMS.html`

Fully interactive HTML with live Mermaid rendering using CDN.

**View:**
- Open in any modern web browser
- All diagrams render dynamically
- Fully printable to PDF

### 3. PDF Format (Recommended)

## How to Generate PDF

### Option A: Print from HTML (Easiest)

1. **Open the HTML file:**
   ```bash
   open docs/ARCHITECTURE_DIAGRAMS.html
   # or
   firefox docs/ARCHITECTURE_DIAGRAMS.html
   # or
   chrome docs/ARCHITECTURE_DIAGRAMS.html
   ```

2. **Print to PDF:**
   - Press `Ctrl+P` (Windows/Linux) or `Cmd+P` (Mac)
   - Select "Save as PDF"
   - Choose output location
   - Click "Save"

**Note:** All Mermaid diagrams will be preserved in the PDF output.

### Option B: Using Pandoc (if available)

Install pandoc:
```bash
# Ubuntu/Debian
sudo apt-get install pandoc wkhtmltopdf

# macOS
brew install pandoc wkhtmltopdf

# Windows
choco install pandoc
```

Convert with pandoc:
```bash
# Convert Markdown to PDF with HTML intermediary
pandoc ARCHITECTURE_DIAGRAMS.md -o ARCHITECTURE_DIAGRAMS.pdf \
  --filter mermaid-filter \
  --pdf-engine=wkhtmltopdf \
  -V papersize=a4

# Or use pandoc with xhtml2pdf
pandoc ARCHITECTURE_DIAGRAMS.md -o ARCHITECTURE_DIAGRAMS.html
wkhtmltopdf ARCHITECTURE_DIAGRAMS.html ARCHITECTURE_DIAGRAMS.pdf
```

### Option C: Using Python Libraries

Install required libraries:
```bash
pip install weasyprint
# or
pip install reportlab
# or
pip install fpdf2
```

Convert HTML to PDF with weasyprint:
```bash
weasyprint docs/ARCHITECTURE_DIAGRAMS.html docs/ARCHITECTURE_DIAGRAMS.pdf
```

Python script using weasyprint:
```python
from weasyprint import HTML

HTML('docs/ARCHITECTURE_DIAGRAMS.html').write_pdf('docs/ARCHITECTURE_DIAGRAMS.pdf')
```

### Option D: Using Docker

If you have Docker installed:

```bash
# Using dockwal/pandoc
docker run --rm -v $(pwd):/data \
  pandoc/pandoc:latest \
  /data/docs/ARCHITECTURE_DIAGRAMS.md \
  -o /data/docs/ARCHITECTURE_DIAGRAMS.pdf \
  --pdf-engine=xvfb-run

# Or using image with mermaid support
docker run --rm -v $(pwd):/app -w /app \
  -v /var/run/docker.sock:/var/run/docker.sock \
  minlag/mermaid-cli -i docs/ARCHITECTURE_DIAGRAMS.md -o docs/ARCHITECTURE_DIAGRAMS.pdf
```

### Option E: Online Tools

Convert without installing software:

1. **Markdown to PDF Online:**
   - Visit: https://md-to-pdf.herokuapp.com/
   - Upload `ARCHITECTURE_DIAGRAMS.md`
   - Download PDF

2. **Mermaid Diagram Exporter:**
   - Visit: https://mermaid.live/
   - Copy each diagram code
   - Export as SVG/PNG
   - Combine into PDF using tool like https://www.ilovepdf.com/

3. **HTML to PDF Converters:**
   - https://cloudconvert.com/ (HTML to PDF)
   - https://smallpdf.com/
   - https://www.zamzar.com/

## Complete Diagram List

| # | Name | Type | File |
|---|------|------|------|
| 1 | High-Level System Overview | Graph | ARCHITECTURE_DIAGRAMS.md |
| 2 | Core Engine Request Flow | Flow | ARCHITECTURE_DIAGRAMS.md |
| 3 | Call Processing Pipeline | Process | ARCHITECTURE_DIAGRAMS.md |
| 4 | SIP Protocol Flow - Call Setup | Sequence | ARCHITECTURE_DIAGRAMS.md |
| 5 | RTP Media Stream - Detailed Flow | Flow | ARCHITECTURE_DIAGRAMS.md |
| 6 | Module Dependency Graph | Dependency | ARCHITECTURE_DIAGRAMS.md |
| 7 | Database Schema - Complete ERD | ERD | ARCHITECTURE_DIAGRAMS.md |
| 8 | Call State Machine - Full State Diagram | State | ARCHITECTURE_DIAGRAMS.md |
| 9 | API Layer Architecture | Architecture | ARCHITECTURE_DIAGRAMS.md |
| 10 | Request Processing Pipeline - Detailed | Sequence | ARCHITECTURE_DIAGRAMS.md |
| 11 | Frontend State Management & Data Flow | Flow | ARCHITECTURE_DIAGRAMS.md |
| 12 | Feature Module System | Architecture | ARCHITECTURE_DIAGRAMS.md |
| 13 | Feature Module Lifecycle | Sequence | ARCHITECTURE_DIAGRAMS.md |
| 14 | Conference Bridge Architecture | Flow | ARCHITECTURE_DIAGRAMS.md |
| 15 | Security & Authentication Architecture | Flow | ARCHITECTURE_DIAGRAMS.md |
| 16 | Authentication & Authorization Flow | Flow | ARCHITECTURE_DIAGRAMS.md |
| 17 | Voicemail Processing Pipeline | Flow | ARCHITECTURE_DIAGRAMS.md |
| 18 | Deployment & Runtime Architecture | Architecture | ARCHITECTURE_DIAGRAMS.md |
| 19 | System Monitoring & Observability Stack | Architecture | ARCHITECTURE_DIAGRAMS.md |

## PDF Quality & Rendering

### Best Results:
- **Chrome/Chromium**: Best mermaid diagram rendering
- **Firefox**: Good rendering, reliable PDF output
- **Safari**: Good rendering on macOS

### Tips for Best PDF:
1. Use a modern browser (Chrome, Firefox, Safari)
2. Set page orientation to Landscape for wide diagrams
3. Adjust margins if needed (typically 0.5 inch)
4. Disable headers/footers in print settings
5. Use "Print Background Graphics" option

## File Structure

```
docs/
├── ARCHITECTURE_DIAGRAMS.md                          (19 diagrams in Markdown)
├── ARCHITECTURE_DIAGRAMS.html                        (Interactive HTML)
├── ARCHITECTURE_DIAGRAMS.pdf                         (Generated PDF)
├── ARCHITECTURE_DIAGRAMS_GENERATION_GUIDE.md         (This file)
├── SYSTEM_ARCHITECTURE.md                            (Original Part 1)
└── DETAILED_COMPONENT_DIAGRAMS.md                    (Original Part 2)
```

## Recommended Workflow

1. **View diagrams:** Use `ARCHITECTURE_DIAGRAMS.md` on GitHub
2. **Share with team:** Export to `ARCHITECTURE_DIAGRAMS.pdf`
3. **Modify/update:** Edit `ARCHITECTURE_DIAGRAMS.md`
4. **Browser preview:** Open `ARCHITECTURE_DIAGRAMS.html` locally
5. **Print to PDF:** Use Chrome's print-to-PDF feature

## Mermaid Diagram Support

All diagrams use Mermaid syntax and are compatible with:
- ✅ GitHub (native rendering)
- ✅ GitLab (native rendering)
- ✅ Gitea (with plugin)
- ✅ Jira (with plugin)
- ✅ Confluence (with plugin)
- ✅ Notion (with embed)
- ✅ Most Markdown editors (with extension)

## Document Information

- **Total Size:** ~200 KB (Markdown), ~500 KB (HTML)
- **Diagrams:** 19 comprehensive architecture visualizations
- **Components:** 250+ system components documented
- **Pages (PDF):** Estimated 50-80 pages depending on formatting

## Troubleshooting

### Mermaid diagrams not rendering in PDF:
- Ensure using Chromium/Chrome for PDF export
- Try HTML export instead of direct markdown PDF
- Use weasyprint or wkhtmltopdf with mermaid-filter

### PDF file too large:
- Use compression tools like ghostscript
- Export individual diagrams instead of full document

### Some diagrams not fitting on page:
- Use Landscape orientation
- Reduce margins in print settings
- Use smaller font sizes

## Contact & Support

For questions about the architecture or diagrams, refer to:
- `CLAUDE.md` - Project documentation and guidelines
- GitHub Issues - For bug reports and suggestions
- Pull Requests - To contribute improvements

---

**Last Updated:** February 24, 2026
**Maintained By:** Claude Code
**Version:** 1.0
