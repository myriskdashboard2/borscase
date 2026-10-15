from pathlib import Path
import pypdfium2 as pdfium
p=pdfium.PdfDocument('leverans/Borscase-produktpresentation.pdf')
print('Pages',len(p))
for i,page in enumerate(p):
 page.render(scale=1.6).to_pil().save(f'leverans/qa/page-{i+1}.png')
 print(i+1,len(page.get_textpage().get_text_range()))
