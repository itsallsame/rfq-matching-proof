import csv
import tempfile
import unittest
from pathlib import Path
from reportlab.pdfgen import canvas
from quote import match, number, read_items, run, safe_cell

ROOT = Path(__file__).parent


class QuoteTests(unittest.TestCase):
    def test_actual_pdf_to_csv_reference_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run(ROOT / 'output/pdf/synthetic-rfq.pdf', ROOT / 'catalogue.csv', tmp)
            self.assertEqual((result['rows'], result['draft_rows'], result['review_rows']), (7, 3, 4))
            # Independent arithmetic: 4*12.50 + 3.5*8.40 + 2*1.10 = 81.60.
            self.assertEqual(result['approved_catalogue_draft_totals_by_currency'], {'EUR': '81.60'})
            self.assertEqual([r['line_total'] for r in result['rows_detail']],
                             ['50.00', '29.40', '2.20', '', '', '', ''])
            with Path(tmp, 'quotation-draft.csv').open(encoding='utf-8-sig') as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 7)
            self.assertTrue(all(r['source_page'] == '1' for r in rows))

    def test_never_pick_first_ambiguous_price(self):
        rows, totals = match([dict(item='1', code='A', request_description='x', quantity='2', unit='pcs')],
                            [dict(code='A', description='v1', unit='pcs', currency='EUR', unit_price='1'),
                             dict(code='A', description='v2', unit='pcs', currency='EUR', unit_price='9')])
        self.assertEqual(rows[0]['status'], 'REVIEW')
        self.assertEqual(rows[0]['unit_price'], '')
        self.assertEqual(totals, {})

    def test_no_mixed_currency_total(self):
        items = [dict(item=str(i), code=code, request_description='x', quantity='2', unit='pcs')
                 for i, code in enumerate(['A', 'B'], 1)]
        catalogue = [dict(code='A', description='a', unit='pcs', currency='EUR', unit_price='1.25'),
                     dict(code='B', description='b', unit='pcs', currency='USD', unit_price='4.00')]
        self.assertEqual(match(items, catalogue)[1], {'EUR': '2.50', 'USD': '8.00'})

    def test_invalid_numeric_values(self):
        for value in ['NaN', 'Infinity', '-1', '0', 'one']:
            with self.assertRaises(ValueError):
                number(value, positive=True)

    def test_unsafe_spreadsheet_text_is_neutralized(self):
        for value in ['=HYPERLINK("x")', '+2', '-3', '@SUM(A1)', '  =1+1']:
            self.assertTrue(safe_cell(value).startswith("'"))
        self.assertEqual(safe_cell('EL-100'), 'EL-100')

    def test_malformed_item_is_not_silently_dropped(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp, 'bad.pdf')
            c = canvas.Canvas(str(file))
            c.drawString(30, 750, 'LINE ITEMS')
            c.drawString(30, 730, '1 | A | truncated row')
            c.drawString(30, 710, 'END ITEMS')
            c.save()
            with self.assertRaisesRegex(ValueError, 'Unrecognized item row'):
                read_items(file)


if __name__ == '__main__':
    unittest.main()
