from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

root = Path(__file__).parent
target = root / 'output/pdf'
target.mkdir(parents=True, exist_ok=True)
c = canvas.Canvas(str(target / 'synthetic-rfq.pdf'), pagesize=A4)
c.setTitle('Synthetic electrical-parts RFQ - demonstration only')
c.setFont('Helvetica-Bold', 17)
c.drawString(45, 793, 'SYNTHETIC RFQ / DEMONSTRATION ONLY')
c.setFont('Helvetica', 10)
c.drawString(45, 766, 'RFQ-DEMO-001 | No real customer data | No order or payment')
c.drawString(45, 739, 'Columns: line | product code | description | quantity | unit')
lines = ['LINE ITEMS',
         '1 | EL-100 | Terminal block | 4 | pcs',
         '2 | EL-200 | Copper cable | 3.5 | m',
         '3 | EL-300 | Fuse | 2 | pcs',
         '4 | EL-999 | Unknown component | 5 | pcs',
         '5 | EL-200 | Cable with unit mismatch | 2 | pcs',
         '6 | EL-100 | Quantity needs confirmation | -3 | pcs',
         '7 | EL-400 | Ambiguous catalogue code | 1 | pcs',
         'END ITEMS']
for i, line in enumerate(lines):
    c.drawString(45, 709 - i * 25, line)
c.setFillColorRGB(.25, .25, .25)
c.drawString(45, 420, 'Expected: lines 1-3 draft; lines 4-7 require human review.')
c.drawString(45, 400, 'Approved catalogue subtotal: EUR 81.60. Review rows have no price.')
c.save()
print(target / 'synthetic-rfq.pdf')
