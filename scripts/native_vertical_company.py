"""Read-only candidates for 通用 outline-based vertical title bars."""
import re
from ezdxf.tools.text import plain_mtext

def decode(value):
    return re.sub(r'\\M\+5([0-9A-Fa-f]{4})',lambda m:bytes.fromhex(m[1]).decode('gbk','replace'),value)

def text(entity):
    if entity.dxftype()=='MTEXT':return plain_mtext(decode(entity.text))
    if entity.dxftype() in ('TEXT','ATTRIB','ATTDEF'):return decode(entity.dxf.text)
    return ''

def anchor(entity):
    if entity.dxftype()=='TEXT':return entity.ocs().to_wcs(entity.dxf.align_point if entity.dxf.halign or entity.dxf.valign else entity.dxf.insert)
    return entity.dxf.insert

def rect(entity):
    if entity.dxftype()=='LWPOLYLINE':points=list(entity.vertices_in_wcs())
    elif entity.dxftype()=='POLYLINE':points=list(entity.points())
    else:return None
    if not 4<=len(points)<=6:return None
    xs=sorted({round(v[0],3) for v in points});ys=sorted({round(v[1],3) for v in points})
    return (xs[0],ys[0],xs[1],ys[1]) if len(xs)==len(ys)==2 else None

def discover_outline_company(doc,layout):
 if not getattr(doc,'_titleblock_outline_company_review',False):return []
 rects=[(e.dxf.handle,rect(e)) for e in layout if rect(e)];companies=[e for e in layout if e.dxftype() in ('TEXT','MTEXT') and getattr(doc,'_titleblock_company_text','') and getattr(doc,'_titleblock_company_text','') in text(e)]
 if len(companies)!=1:return []
 company=companies[0];pos=anchor(company);segments=[]
 for e in layout:
  points=[]
  if e.dxftype()=='LINE':points=[e.dxf.start,e.dxf.end]
  elif e.dxftype()=='LWPOLYLINE' and not any(v[4] for v in e.get_points()):points=list(e.vertices_in_wcs())
  for a,b in zip(points,points[1:]):
   if abs(a[1]-b[1])<1e-5:segments.append((min(a[0],b[0]),max(a[0],b[0]),(a[1]+b[1])/2))
  if e.dxftype()=='HATCH' and e.dxf.extrusion.isclose((0,0,1)) and all(hasattr(path,'vertices') for path in e.paths):
   points=[v for path in e.paths for v in path.vertices]
   if points:
    x0,x1=min(v[0] for v in points),max(v[0] for v in points);y0,y1=min(v[1] for v in points),max(v[1] for v in points)
    if x1-x0>30 and y1-y0<(x1-x0)*.015:segments.append((x0,x1,(y0+y1)/2))
 found=[]
 for outer,ob in rects:
  ow,oh=ob[2]-ob[0],ob[3]-ob[1]
  if ow<100 or oh<100:continue
  for body,ib in rects:
   iw,ih=ib[2]-ib[0],ib[3]-ib[1]
   if not(ob[0]<ib[0]<ib[2]<ob[2] and ob[1]<ib[1]<ib[3]<ob[3] and iw>.75*ow and ih>.95*oh and ib[2]<=pos.x<ob[2] and ib[1]<pos.y<ib[3]):continue
   left=ib[2];potential=[v for v in segments if abs(v[0]-left)<ow*.0005 and .04*ow<v[1]-left<.18*ow and ib[1]-ow*.0005<=v[2]<=ib[3]+ow*.0005];clusters=[]
   for row in sorted(potential,key=lambda v:v[1]):
    if not clusters or row[1]-clusters[-1][-1][1]>ow*.0003:clusters.append([])
    clusters[-1].append(row)
   choices=[]
   for group in clusters:
    right=(min(v[1] for v in group)+max(v[1] for v in group))/2;width=right-left;ys=[]
    for y in sorted(v[2] for v in group):
     if not ys or y-ys[-1]>width*.015:ys.append(y)
    if len(ys)>=8 and ys[-1]-ys[0]>.95*ih and 0<ob[2]-right<ow*.03 and left<pos.x<right:choices.append((right,ys))
   if len(choices)!=1:continue
   right,ys=choices[0];width=right-left;below=[y for y in ys if y<pos.y-width*.015];above=[y for y in ys if y>pos.y+width*.015]
   if not below or not above:continue
   low,high=max(below),min(above)
   if high-low<width*.15:continue
   occupants=[e for e in layout if e.dxftype() in ('TEXT','MTEXT') and text(e) and left<=anchor(e).x<=right and low<anchor(e).y<high]
   if len(occupants)!=1 or occupants[0].dxf.handle!=company.dxf.handle:continue
   found.append({'outline_company_only':True,'outer':outer,'body_rectangle':body,'bar_box':[left,ib[1],right,ib[3]],'fields':[{'role':'contractor','handle':company.dxf.handle,'value':text(company),'cell':[left,low,right,high]}],'geometry_evidence':'原正文闭合矩形及右侧至少8条横向分格，覆盖竖栏95%以上高度；单位单元格内只有唯一可编辑施工单位'})
 unique={tuple(v['fields'][0]['cell']):v for v in found}
 if len(unique)!=1:return []
 return list(unique.values())

def geometry_bounds(doc,entity):
    from ezdxf import bbox
    points=None
    if entity.dxftype()=='LINE':points=[entity.dxf.start,entity.dxf.end]
    elif entity.dxftype()=='LWPOLYLINE' and entity.dxf.const_width==0 and not any(v[2] or v[3] or v[4] for v in entity.get_points()):points=list(entity.vertices_in_wcs())
    elif entity.dxftype()=='HATCH' and all(hasattr(path,'vertices') and not any(v[2] for v in path.vertices) for path in entity.paths):
        points=[v for path in entity.paths for v in path.vertices]
        if points and not entity.dxf.extrusion.isclose((0,0,1)):points=[entity.ocs().to_wcs((v[0],v[1],entity.dxf.elevation.z)) for v in points]
    if points:return (min(v[0] for v in points),min(v[1] for v in points),max(v[0] for v in points),max(v[1] for v in points))
    box=bbox.extents([entity],fast=True,cache=getattr(doc,"_titleblock_bbox_cache",None))
    return (box.extmin.x,box.extmin.y,box.extmax.x,box.extmax.y) if box.has_data else None

def inspect_document(doc, company_text=""):
    doc._titleblock_company_text=company_text
    import sys
    from ezdxf import bbox
    from native_cell_company import discover_company_cell
    doc._titleblock_outline_company_review=True
    doc._titleblock_bbox_cache=bbox.Cache()
    return [{'layout':layout.name,**frame} for layout in doc.layouts for frame in (discover_outline_company(doc,layout) or discover_company_cell(sys.modules[__name__],doc,layout))]

if __name__=='__main__':
    import argparse,json,hashlib
    from pathlib import Path
    import cad_io
    parser=argparse.ArgumentParser(description='只读识别通用轮廓竖式图框内的施工单位单元格，不修改图名图号和框线')
    parser.add_argument('--company-text',default='',help='单位匹配文字，默认空，不识别候选');parser.add_argument('source');parser.add_argument('--output',required=True);args=parser.parse_args()
    source=Path(args.source);result={'input_sha256':hashlib.file_digest(source.open('rb'),'sha256').hexdigest(),'candidates':inspect_document(cad_io.readfile(source),args.company_text)};Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2));print('candidate contractor cells:',len(result['candidates']))
