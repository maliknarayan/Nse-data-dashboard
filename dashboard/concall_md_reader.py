"""Direct MD reader for dashboard fallback display.

When JSON snapshot is not available, read MD file directly and format for display.
Used as fallback in ui.py when calling get_concall_from_md().
"""

import os
import re
from datetime import date


def extract_verdict_block(text: str) -> dict:
    """Extract verdict, classification, confidence from MD header."""
    lines = text.split('\n')[:15]
    result = {'verdict': 'NO_VIEW', 'confidence': 0.5}
    for line in lines:
        if line.startswith('**Verdict:**'):
            result['verdict'] = line.replace('**Verdict:**', '').strip()
        elif line.startswith('**Classification:**'):
            result['classification'] = line.replace('**Classification:**', '').strip()
        elif line.startswith('**Management Confidence:**'):
            conf_str = line.replace('**Management Confidence:**', '').strip()
            try:
                result['confidence'] = int(conf_str.split('/')[0]) / 10.0
            except (ValueError, IndexError):
                result['confidence'] = 0.5
    return result


def extract_company_title(text: str) -> str:
    """Extract company name from title line."""
    first_line = text.split('\n')[0]
    title = first_line.replace('#', '').strip()
    company = title.split(' — ')[0].strip() if ' — ' in title else title
    return company


def extract_section(text: str, section_num: int, section_name: str) -> str:
    """Extract section by number and optional name."""
    pattern = rf'^## {section_num}\..*?(?=^## |\Z)'
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    return match.group(0) if match else ''


def parse_highlights_from_md(md_text: str) -> list[dict]:
    """Extract highlights from Financial Snapshot + Growth Guidance sections."""
    highlights = []

    # Section 2: Financial Snapshot
    fin_section = extract_section(md_text, 2, 'Financial Snapshot')
    if fin_section:
        # Parse tables — extract non-header rows
        lines = fin_section.split('\n')
        in_table = False
        for line in lines:
            line_stripped = line.strip()
            if line_stripped.startswith('|') and '---|' in line:
                in_table = True
                continue
            if in_table and line_stripped.startswith('|') and line_stripped != '|':
                cells = [c.strip() for c in line_stripped.split('|')[1:-1]]
                if len(cells) >= 2 and cells[0] and cells[1]:
                    metric, value = cells[0], cells[1]
                    if value and value not in ('+', '-', '—', 'n/a', ''):
                        highlights.append({
                            'point': f'{metric}: {value}',
                            'sentiment': 'neutral'
                        })

    # Section 3: Growth Guidance
    guid_section = extract_section(md_text, 3, 'Growth Guidance')
    if guid_section:
        lines = guid_section.split('\n')
        for line in lines:
            line = line.strip()
            # Match firm/committed targets (bold markers)
            if line.startswith('- **'):
                match = re.search(r'\*\*([^*]+)\*\*:?\s*(.*?)(?=\(|$)', line)
                if match:
                    target = match.group(1)
                    detail = match.group(2).strip() if match.group(2) else ''
                    full = f'{target}: {detail}' if detail else target
                    if full:
                        highlights.append({
                            'point': full[:200],  # Limit length
                            'sentiment': 'good'
                        })

    # Limit to top 12 highlights
    return highlights[:12]


def parse_key_monitorables_from_md(md_text: str) -> list[str]:
    """Extract key metrics from section 4."""
    monitorables = []
    kmon_section = extract_section(md_text, 4, 'Key Monitorables')
    if kmon_section:
        lines = kmon_section.split('\n')
        for line in lines:
            line = line.strip()
            # Table rows: extract first cell (metric name)
            if line.startswith('|') and 'Metric' not in line and '---|' not in line:
                cells = [c.strip() for c in line.split('|')[1:-1]]
                if cells and cells[0]:
                    monitorables.append(cells[0][:100])
            # Or bullet points
            elif line.startswith('- '):
                monitorables.append(line[2:][:100])

    return monitorables[:10]


def read_concall_md(md_path: str, company_override: str = '') -> dict:
    """Read MD file and return display-ready data dict."""
    if not os.path.exists(md_path):
        return {
            'error': f'File not found: {md_path}',
            'company': company_override or 'Unknown',
            'readable': False
        }

    try:
        with open(md_path, 'r', encoding='utf-8') as fh:
            text = fh.read()
    except Exception as exc:
        return {
            'error': f'Could not read file: {exc}',
            'company': company_override or 'Unknown',
            'readable': False
        }

    company = extract_company_title(text) or company_override
    verdict_block = extract_verdict_block(text)

    return {
        'company': company,
        'readable': True,
        'source': 'MD file (JSON not yet converted)',
        'verdict': verdict_block.get('verdict', 'NO_VIEW'),
        'classification': verdict_block.get('classification', ''),
        'confidence': verdict_block.get('confidence', 0.5),
        'highlights': parse_highlights_from_md(text),
        'key_monitorables': parse_key_monitorables_from_md(text),
        'analyzed_on': date.today().isoformat(),
        'note': 'Direct MD parse — may miss some data compared to full JSON snapshot'
    }


def fallback_read_concall(quarter: str, company: str) -> dict | None:
    """Fallback: find and read MD file for company if JSON not available."""
    # Try common MD directory patterns
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    md_dir = os.path.join(base_dir, 'concall-data', quarter, 'md-files')

    if not os.path.isdir(md_dir):
        return None

    # Normalize company name for filename matching
    company_slug = company.lower().replace(' ', '-')

    # Find matching MD file
    for fname in os.listdir(md_dir):
        if fname.endswith('.md'):
            # Check if company name matches (fuzzy)
            fname_lower = fname.lower()
            if company_slug in fname_lower or company.lower() in fname_lower:
                md_path = os.path.join(md_dir, fname)
                return read_concall_md(md_path, company)

    return None
