"""Typeset the saved J1939 research manuscript; performs no scientific fits."""
from pathlib import Path
import re
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Table, TableStyle, KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'output/pdf'
SOURCE=FOLDER/'J1939+2134_Candidate_Report.md'
OUTPUT=FOLDER/'J1939+2134_Candidate_Report.pdf'
FONT=Path('/System/Library/Fonts/Supplemental')
for name,file in [('Research','Times New Roman.ttf'),('Research-Bold','Times New Roman Bold.ttf'),('Research-Italic','Times New Roman Italic.ttf'),('Research-BoldItalic','Times New Roman Bold Italic.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(FONT/file)))
pdfmetrics.registerFontFamily('Research',normal='Research',bold='Research-Bold',italic='Research-Italic',boldItalic='Research-BoldItalic')
styles={
 'body':ParagraphStyle('body',fontName='Research',fontSize=10.6,leading=13.7,spaceAfter=8,alignment=TA_JUSTIFY),
 'title':ParagraphStyle('title',fontName='Research-Bold',fontSize=20,leading=23,spaceAfter=14),
 'h2':ParagraphStyle('h2',fontName='Research-Bold',fontSize=13,leading=16,spaceBefore=7,spaceAfter=8,keepWithNext=True),
 'h3':ParagraphStyle('h3',fontName='Research-Bold',fontSize=11.4,leading=14,spaceBefore=6,spaceAfter=7,keepWithNext=True),
 'meta':ParagraphStyle('meta',fontName='Research',fontSize=10.5,leading=13,spaceAfter=7),
 'caption':ParagraphStyle('caption',fontName='Research',fontSize=9.2,leading=11.5,spaceAfter=9),
 'table':ParagraphStyle('table',fontName='Research',fontSize=9.3,leading=11.5),
 'reference':ParagraphStyle('reference',fontName='Research',fontSize=9,leading=11,spaceAfter=6),
 'provenance':ParagraphStyle('provenance',fontName='Research',fontSize=9.3,leading=12,spaceAfter=8),
}
def markup(text):
    text=escape(text)
    text=text.replace("⁻γ", "<sup>-γ</sup>")
    for char,value in zip('₀₁₂₃₄₅₆₇₈₉ₛᵢⱼₖ','0123456789sijk'):
        text=text.replace(char,'<sub>'+value+'</sub>')
    for char,value in zip('⁰¹²³⁴⁵⁶⁷⁸⁹⁻ᵀ','0123456789-T'):
        text=text.replace(char,'<sup>'+value+'</sup>')
    text=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',text)
    text=re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)',r'<i>\1</i>',text)
    text=re.sub(r'(https://[^\s]+)',lambda m:'<link href="'+m[1]+'" color="#245781">'+m[1]+'</link>',text)
    return text

def para(text,style='body'):
    return Paragraph(markup(text),styles[style])

class PagedCanvas(canvas.Canvas):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.states=[]
    def showPage(self):
        self.states.append(dict(self.__dict__));self._startPage()
    def save(self):
        total=len(self.states)
        for state in self.states:
            self.__dict__.update(state)
            self.setFont('Research',8.2);self.setFillColor(colors.HexColor('#444444'))
            self.drawString(52,765,'PROJECT RECHERCHE  |  PSR J1939+2134')
            self.drawRightString(560,765,'Research report PR-J1939-2026-01')
            self.setStrokeColor(colors.HexColor('#999999'));self.setLineWidth(.35);self.line(52,758,560,758)
            self.drawString(52,29,'Version 1.0  |  9 September 2026')
            self.drawRightString(560,29,f'{self._pageNumber} / {total}')
            super().showPage()
        super().save()

blocks=SOURCE.read_text().split('\n\n');story=[];refs=False;first=True
for block in blocks:
    b=block.strip()
    if not b:continue
    if b=='---':story.append(PageBreak());continue
    if b.startswith('# '):story.append(para(b[2:],'title'));continue
    if b.startswith('## '):
        refs=b[3:]=='References';story.append(para(b[3:],'h2'));continue
    if b.startswith('### '):story.append(para(b[4:],'h3'));continue
    if b.startswith('!['):
        path=re.search(r'\]\(([^)]+)\)',b)[1];w,h=ImageReader(str(FOLDER/path)).getSize();width=508
        story.append(Image(str(FOLDER/path),width=width,height=width*h/w));story.append(Spacer(1,5));continue
    if b.startswith('|'):
        lines=[line for line in b.splitlines() if not re.match(r'^\|[ :|\-]+\|$',line)]
        rows=[[para(cell.strip(),'table') for cell in line.strip('|').split('|')] for line in lines]
        count=len(rows[0]);widths={2:[280,228],3:[228,140,140],4:[230,60,112,106],5:[190,76,76,76,90]}[count]
        table=Table(rows,colWidths=widths,repeatRows=1,hAlign='LEFT')
        table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('LINEABOVE',(0,0),(-1,0),.7,colors.black),('LINEBELOW',(0,0),(-1,0),.5,colors.black),('LINEBELOW',(0,-1),(-1,-1),.6,colors.black),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eeeeee'))]))
        story.extend([table,Spacer(1,9)]);continue
    style='reference' if refs else 'provenance' if b.startswith('Primary review code:') else 'caption' if b.startswith(('Figure ','Table ')) else 'meta' if b.startswith(('Project Recherche','Research report PR-')) else 'body'
    story.append(para(b.replace('\n',' '),style))
doc=SimpleDocTemplate(str(OUTPUT),pagesize=(612,792),rightMargin=52,leftMargin=52,topMargin=46,bottomMargin=48,title='A bounded noise and cross-source review of PSR J1939+2134',author='Project Recherche',subject='Observed pulsar-timing candidate and bounded diagnostic review',pageCompression=1)
doc.build(story,canvasmaker=PagedCanvas)
print(OUTPUT)
