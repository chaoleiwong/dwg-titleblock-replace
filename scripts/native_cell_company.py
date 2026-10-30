# Read-only cell recognition; not a publication authorization.
def _discover_simple_company_cell(f,d,l):
 co=[e for e in l if e.dxftype() in ('TEXT','MTEXT') and getattr(d,'_titleblock_company_text','') and getattr(d,'_titleblock_company_text','') in f.text(e)]
 if len(co)!=1:return []
 e=co[0];pos=f.anchor(e);h=[];v=[]
 for a in l:
  if a.dxftype() not in ('HATCH','LINE','LWPOLYLINE'):continue
  b=f.geometry_bounds(d,a)
  if not b:continue
  x0,y0,x1,y1=b;ww=x1-x0;hh=y1-y0
  if ww>50 and hh<ww*.015 and x0<pos.x<x1:h.append((x0,x1,(y0+y1)/2,a.dxf.handle))
  if hh>300 and ww<hh*.01 and y0<pos.y<y1:v.append(((x0+x1)/2,y0,y1,a.dxf.handle))
 lefts=[a for a in v if a[0]<pos.x];rights=[a for a in v if a[0]>pos.x]
 if not lefts or not rights:return []
 left=max(lefts)[0];right=min(rights)[0];width=right-left
 if width<50:return []
 rows=[a for a in h if abs(a[0]-left)<width*.02 and abs(a[1]-right)<width*.02];below=[a for a in rows if a[2]<pos.y-width*.015];above=[a for a in rows if a[2]>pos.y+width*.015]
 if not below or not above:return []
 low=max(a[2] for a in below);high=min(a[2] for a in above)
 if not .15*width<high-low<2*width:return []
 occ=[a for a in l if a.dxftype() in ('TEXT','MTEXT') and f.text(a) and left<=f.anchor(a).x<=right and low<f.anchor(a).y<high]
 if len(occ)!=1:return []
 bottom=min(a[1] for a in v if abs(a[0]-left)<width*.02);top=max(a[2] for a in v if abs(a[0]-left)<width*.02)
 if len({round(a[2]/width,2) for a in rows})<8:return []
 return [{'outline_company_only':True,'bar_box':[left,bottom,right,top],'fields':[{'role':'contractor','handle':e.dxf.handle,'value':f.text(e),'cell':[left,low,right,high]}],'geometry_evidence':'原施工单位格四边及至少8条竖栏横向分格；正文及原框线全部保留','boundary_handles':list(dict.fromkeys([a[3] for a in rows if abs(a[2]-low)<.02*width or abs(a[2]-high)<.02*width]+[a[3] for a in v if abs(a[0]-left)<width*.02 or abs(a[0]-right)<width*.02]))}]

def discover_company_cell(f,d,l):
 if not hasattr(d,'_titleblock_bbox_cache'):
  from ezdxf import bbox
  d._titleblock_bbox_cache=bbox.Cache()
 simple=_discover_simple_company_cell(f,d,l)
 if simple:return simple
 co=[e for e in l if e.dxftype() in ('TEXT','MTEXT') and getattr(d,'_titleblock_company_text','') and getattr(d,'_titleblock_company_text','') in f.text(e)]
 if len(co)!=1:return []
 entity=co[0];pos=f.anchor(entity);eh=entity.dxf.char_height if entity.dxftype()=='MTEXT' else entity.dxf.height;v=[];h=[]
 for e in l:
  if e.dxftype() not in ('HATCH','LINE','LWPOLYLINE'):continue
  b=f.geometry_bounds(d,e)
  if not b:continue
  x0,y0,x1,y1=b;ww=x1-x0;hh=y1-y0
  if hh>300 and ww<hh*.01 and y0<pos.y<y1:v.append(((x0+x1)/2,y0,y1,e.dxf.handle))
  if ww>50 and hh<ww*.015:h.append((x0,x1,(y0+y1)/2,e.dxf.handle))
 clusters=[];tol=max(.25,eh*.15)
 for a in sorted(v):
  if clusters and a[0]-clusters[-1][-1][0]<tol:clusters[-1].append(a)
  else:clusters.append([a])
 found=[]
 for ci,left_group in enumerate(clusters):
  left=sum(a[0] for a in left_group)/len(left_group)
  for right_group in clusters[ci+1:]:
   right=sum(a[0] for a in right_group)/len(right_group);width=right-left
   if width<50 or not left-width*.02<=pos.x<=right-width*.1:continue
   rows=[a for a in h if abs(a[0]-left)<width*.02 and abs(a[1]-right)<width*.02]
   if len({round(a[2]/width,2) for a in rows})<8:continue
   below=[a for a in rows if a[2]<pos.y-width*.015];above=[a for a in rows if a[2]>pos.y+width*.015]
   if not below or not above:continue
   low=max(a[2] for a in below);high=min(a[2] for a in above)
   if not .15*width<high-low<2*width:continue
   occ=[a for a in l if a.dxftype() in ('TEXT','MTEXT') and f.text(a) and left-width*.02<=f.anchor(a).x<=right and low<f.anchor(a).y<high]
   if len(occ)!=1 or occ[0] is not entity:continue
   bottom=min(a[1] for a in left_group);top=max(a[2] for a in left_group)
   if top-bottom<4*width:continue
   found.append({'outline_company_only':True,'bar_box':[left,bottom,right,top],'fields':[{'role':'contractor','handle':entity.dxf.handle,'value':f.text(entity),'cell':[left,low,right,high]}],'geometry_evidence':'重复竖边按原字高小容差聚类；同宽至少8分格和唯一单位文字；仅候选，必须逐图确认','boundary_handles':list(dict.fromkeys([a[3] for a in rows if abs(a[2]-low)<.02*width or abs(a[2]-high)<.02*width]+[a[3] for a in left_group+right_group]))})
 return found if len(found)==1 else []

