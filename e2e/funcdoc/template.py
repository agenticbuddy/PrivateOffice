#!/usr/bin/env python3
"""Write /tmp/funcdoc-template.xlsx: a workbook with 3 EMPTY sheets named for the three
formula-entry methods. The skeleton (empty named sheets) is uploaded; every formula is then
filled through the live editor UI (ribbon menu / Function Wizard / direct typing)."""
import zipfile

SHEETS = ["Через меню", "Через мастер", "Прямой ввод"]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


sheet_xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
             '<sheetData/></worksheet>')
sheets_tags = "".join(f'<sheet name="{esc(n)}" sheetId="{i+1}" r:id="rId{i+1}"/>' for i, n in enumerate(SHEETS))
WORKBOOK = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
            ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f'<sheets>{sheets_tags}</sheets></workbook>')
wb_rels = "".join(f'<Relationship Id="rId{i+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i+1}.xml"/>' for i in range(len(SHEETS)))
WB_RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
           f'{wb_rels}</Relationships>')
RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
overrides = "".join(f'<Override PartName="/xl/worksheets/sheet{i+1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(len(SHEETS)))
CT = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
      '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
      '<Default Extension="xml" ContentType="application/xml"/>'
      '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
      f'{overrides}</Types>')
with zipfile.ZipFile("/tmp/funcdoc-template.xlsx", "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml", CT)
    z.writestr("_rels/.rels", RELS)
    z.writestr("xl/workbook.xml", WORKBOOK)
    z.writestr("xl/_rels/workbook.xml.rels", WB_RELS)
    for i in range(len(SHEETS)):
        z.writestr(f"xl/worksheets/sheet{i+1}.xml", sheet_xml)
print("wrote /tmp/funcdoc-template.xlsx with sheets:", SHEETS)
