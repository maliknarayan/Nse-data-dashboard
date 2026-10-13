"""Parse a quarter's concall MD files into JSON snapshots for dashboard ingestion.

Usage:
    python -m dashboard.concall_md_parser C:/misc-project/Nse-data-dashboard/concall-data/<quarter>

Reads all *.md files in md-files/, extracts verdict/highlights/monitorables,
outputs JSON snapshots to result-json/. Run dashboard.concall_merge afterwards
to fold the new snapshots into that quarter's concalls-summary.json.
"""

import json
import os
import re
import sys
from datetime import date
from pathlib import Path


def extract_verdict_block(text: str) -> dict:
    """Extract verdict, classification, date, confidence from header."""
    lines = text.split('\n')[:10]
    result = {}
    for line in lines:
        if line.startswith('**Verdict:**'):
            result['verdict'] = line.replace('**Verdict:**', '').strip()
        elif line.startswith('**Classification:**'):
            result['classification'] = line.replace('**Classification:**', '').strip()
        elif line.startswith('**Date of Analysis:**'):
            result['analyzed_on'] = line.replace('**Date of Analysis:**', '').strip()
        elif line.startswith('**Management Confidence:**'):
            confidence_str = line.replace('**Management Confidence:**', '').strip()
            if '/' in confidence_str:
                try:
                    # keep the 0-10 scale the rest of the app expects — don't normalize to 0-1
                    result['confidence'] = float(confidence_str.split('/')[0])
                except (ValueError, IndexError):
                    result['confidence'] = 5.0
    return result


def extract_title_company(text: str) -> tuple[str, str]:
    """Extract title line (company name + quarter)."""
    first_line = text.split('\n')[0]
    # Remove markdown heading marker
    title = first_line.replace('#', '').strip()
    # Extract company name (before " — ")
    company = title.split(' — ')[0].strip() if ' — ' in title else title
    return company, title


def extract_section(text: str, section_name: str) -> str:
    """Extract text between section headers. Numeric prefix ('## 2. Foo') is optional, and
    the heading level varies between '##' and '###' across MD templates — matched by
    backreference so a '##' section isn't cut short by a nested '###' sub-header
    (e.g. Financial Snapshot's Consolidated/Standalone sub-tables)."""
    pattern = rf'^(#{{2,3}}) (?:\d+\.\s*)?{re.escape(section_name)}.*?(?=^\1 |\Z)'
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    return match.group(0) if match else ''


def parse_highlights(text: str) -> list[dict]:
    """Parse Financial Snapshot + Growth Guidance as highlights."""
    highlights = []

    # Extract Financial Snapshot section
    fin_section = extract_section(text, 'Financial Snapshot')
    if fin_section:
        # Find table rows (lines starting with |)
        lines = fin_section.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('|') and '|' in line[1:]:
                # Skip header/separator rows
                if '---|' not in line and 'Metric' not in line:
                    cells = [c.strip() for c in line.split('|')[1:-1]]
                    if len(cells) >= 2 and cells[0] and cells[1]:
                        # Extract metric + value
                        metric = cells[0]
                        value = cells[1]
                        if value and value not in ('+', '-', '—', 'n/a'):
                            highlights.append({
                                'point': f'{metric}: {value}',
                                'sentiment': 'neutral'
                            })

    # Extract Growth Guidance section
    guid_section = extract_section(text, 'Growth Guidance')
    if guid_section:
        # Find bullet points (lines starting with -)
        lines = guid_section.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('- **'):
                # Extract bold text (firm targets)
                match = re.search(r'\*\*([^*]+)\*\*:?\s*(.*)', line)
                if match:
                    target = match.group(1)
                    detail = match.group(2).strip()
                    highlights.append({
                        'point': f'{target}: {detail}' if detail else target,
                        'sentiment': 'good'
                    })

    return highlights[:15]  # Limit to 15 highlights


def parse_key_monitorables(text: str) -> list[str]:
    """Extract key monitorables from section 4."""
    monitorables = []
    kmon_section = extract_section(text, 'Key Monitorables')
    if kmon_section:
        lines = kmon_section.split('\n')
        for line in lines:
            line = line.strip()
            # Match table rows or bullet patterns
            if line.startswith('|') and 'Metric' not in line and '---|' not in line:
                cells = [c.strip() for c in line.split('|')[1:-1]]
                if cells:
                    monitorables.append(cells[0])
            elif line.startswith('- '):
                monitorables.append(line[2:])

    return monitorables[:12]


def parse_md_to_snapshot(md_path: str, quarter_dir: str = '') -> dict:
    """Convert one MD file to JSON snapshot. quarter_dir is the quarter folder name
    (e.g. 'Q4FY26'), used both for the label and so 'same quarter' filenames don't collide."""
    with open(md_path, 'r', encoding='utf-8') as fh:
        text = fh.read()

    company, title = extract_title_company(text)
    verdict_block = extract_verdict_block(text)
    highlights = parse_highlights(text)
    monitorables = parse_key_monitorables(text)

    quarter = re.sub(r'(Q\d)(FY\d+)', r'\1 \2', quarter_dir) if quarter_dir else 'Unknown'

    # 'verdict' must hold the CALL (BUY/HOLD/AVOID/...) — that's what downstream
    # BUY/ACCUMULATE filtering keys off. The tone (GOOD/BAD/MIXED) goes in the rationale.
    call = verdict_block.get('classification') or verdict_block.get('verdict', 'NO_VIEW')
    tone = verdict_block.get('verdict', '')

    snapshot = {
        'company': company,
        'quarter': quarter,
        'call_date': verdict_block.get('analyzed_on', ''),
        'source_pdf': os.path.basename(md_path).replace('.md', '.pdf'),
        'source_md': os.path.basename(md_path),
        'highlights': highlights,
        'verdict': call,
        'verdict_rationale': f"Extracted from MD analysis. Tone: {tone or 'N/A'}",
        'confidence': verdict_block.get('confidence', 5.0),
        'key_monitorables': monitorables,
        'analyzed_on': date.today().isoformat(),
        'note': 'Auto-converted from MD file; JSON conversion may need manual review for full accuracy'
    }

    return snapshot


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2

    qdir = os.path.abspath(argv[1])
    qname = os.path.basename(qdir.rstrip('\\/'))
    md_dir = os.path.join(qdir, 'md-files')
    out_dir = os.path.join(qdir, 'result-json')

    if not os.path.isdir(md_dir):
        print(f'md-files not found: {md_dir}')
        return 1

    os.makedirs(out_dir, exist_ok=True)

    # recursive — some quarters archive already-processed MDs into md-files/done/
    md_files = sorted(Path(md_dir).rglob('*.md'))
    print(f'Found {len(md_files)} MD files')

    converted = 0
    for md_path in md_files:
        try:
            snapshot = parse_md_to_snapshot(str(md_path), qname)
            company = snapshot['company']
            # Sanitize filename: remove special chars, use company name
            safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', company)
            json_path = os.path.join(out_dir, f'{safe_name}_{qname}.json')

            with open(json_path, 'w', encoding='utf-8') as fh:
                json.dump(snapshot, fh, indent=2, ensure_ascii=False)

            print(f'[OK] {company}')
            converted += 1
        except Exception as exc:
            print(f'[ERR] {md_path.name}: {exc}')

    print(f'\nConverted {converted}/{len(md_files)} MD files to JSON snapshots')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
