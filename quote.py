"""Bounded PDF-to-CSV quotation proof; all prices come from the supplied catalogue."""
import argparse
import csv
import json
import re
from collections import defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from pypdf import PdfReader


def number(value, *, positive=False):
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError('Invalid decimal') from exc
    if not result.is_finite() or result < 0 or (positive and result == 0):
        raise ValueError('Non-positive or invalid value')
    return result


def read_items(pdf):
    items = []
    active = False
    ended = False
    for page_no, page in enumerate(PdfReader(pdf).pages, 1):
        for line_no, raw in enumerate((page.extract_text() or '').splitlines(), 1):
            line = raw.strip()
            if line == 'LINE ITEMS':
                if active or ended:
                    raise ValueError('Repeated item section')
                active = True
                continue
            if line == 'END ITEMS':
                if not active:
                    raise ValueError('Unexpected section end')
                active, ended = False, True
                continue
            if active and line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) != 5 or not re.fullmatch(r'\d+', parts[0]):
                    raise ValueError(f'Unrecognized item row at PDF page {page_no}, text line {line_no}')
                items.append(dict(zip(['item', 'code', 'request_description', 'quantity', 'unit'], parts),
                                  source_page=str(page_no), source_line=str(line_no)))
    if active or not ended or not items:
        raise ValueError('Missing/empty complete item section; scanned PDFs require a separate extraction path')
    if len({r['item'] for r in items}) != len(items):
        raise ValueError('Duplicate RFQ line identifiers')
    return items


def match(items, catalogue):
    index = defaultdict(list)
    for row in catalogue:
        number(row['unit_price'])
        if not row['code'] or not row['unit'] or not re.fullmatch('[A-Z]{3}', row['currency']):
            raise ValueError('Incomplete catalogue row')
        index[row['code']].append(row)
    output, totals = [], defaultdict(Decimal)
    for item in items:
        row = dict(item, status='REVIEW', reason='', catalogue_description='', currency='', unit_price='', line_total='')
        candidates = index[item['code']]
        try:
            quantity = number(item['quantity'], positive=True)
        except ValueError:
            row['reason'] = 'Invalid quantity; confirm with requester'
        else:
            if not candidates:
                row['reason'] = 'Code absent from approved catalogue; no substitution'
            elif len(candidates) != 1:
                row['reason'] = 'Ambiguous catalogue code; human selection required'
            elif item['unit'] != candidates[0]['unit']:
                row['reason'] = 'Requested and approved units differ; no automatic conversion'
            else:
                candidate = candidates[0]
                total = (quantity * number(candidate['unit_price'])).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
                row.update(status='DRAFT', reason='Exact code and unit match; final human approval required',
                           catalogue_description=candidate['description'], currency=candidate['currency'],
                           unit_price=candidate['unit_price'], line_total=str(total))
                totals[candidate['currency']] += total
        output.append(row)
    return output, {currency: str(total) for currency, total in sorted(totals.items())}


def safe_cell(value):
    text = str(value)
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@')) else text


def run(pdf, catalogue_path, output_dir):
    with open(catalogue_path, newline='', encoding='utf-8') as stream:
        catalogue = list(csv.DictReader(stream))
    rows, totals = match(read_items(pdf), catalogue)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / 'quotation-draft.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows({key: safe_cell(value) for key, value in row.items()} for row in rows)
    report = {'run_mode': 'demonstration', 'source_pdf': Path(pdf).name,
              'rows': len(rows), 'draft_rows': sum(r['status'] == 'DRAFT' for r in rows),
              'review_rows': sum(r['status'] == 'REVIEW' for r in rows),
              'approved_catalogue_draft_totals_by_currency': totals,
              'rows_detail': rows,
              'limits': 'One delimited text PDF layout; no OCR, fuzzy substitutions, ERP integration or automatic sending. CSV is Excel-compatible, not an XLSX workbook.'}
    (output_dir / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('pdf')
    parser.add_argument('catalogue')
    parser.add_argument('--output', default='output')
    args = parser.parse_args()
    print(json.dumps(run(args.pdf, args.catalogue, args.output), indent=2))
