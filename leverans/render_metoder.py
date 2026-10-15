from pathlib import Path
import pypdfium2 as pdfium
out=Path('leverans/qa-metoder');out.mkdir(exist_ok=True)
p=pdfium.PdfDocument('leverans/Borscase-funktioner-och-metoder.pdf')
print('Pages',len(p))
for i,page in enumerate(p):
 page.render(scale=1.5).to_pil().save(str(out/f'page-{i+1}.png'))
 print(i+1,page.get_textpage().get_text_range()[:85].replace('\r\n',' '))
