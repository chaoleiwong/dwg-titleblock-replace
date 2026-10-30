"""Align explicitly bounded, axis-aligned filled table strokes with a title stamp."""
import math

def align_table_hatches(doc,layout,stamp_box,scale,return_candidates=False):
 left,bottom,right,top=stamp_box;s=scale;changed=[];candidates=[];w=right-left
 for e in layout:
  if e.dxftype()!='HATCH' or len(e.paths)!=1 or not hasattr(e.paths[0],'vertices') or not e.dxf.extrusion.isclose((0,0,1)):continue
  vs=e.paths[0].vertices
  if not 4<=len(vs)<=2000 or any(v[2] for v in vs):continue
  xs=[v[0] for v in vs];ys=[v[1] for v in vs];x0,x1,y0,y1=min(xs),max(xs),min(ys),max(ys)
  if abs(x0-left)>1.5*s or abs(x1-right)>1.5*s or y0<top-.3*s or y1>top+300*s or y1<top+.6*s:continue
  edges=list(zip(vs,vs[1:]+vs[:1]))
  if not any(abs(a[1]-b[1])<s*1e-6 and abs(a[0]-b[0])>w*.5 for a,b in edges):continue
  if any(min(abs(a[0]-b[0]),abs(a[1]-b[1]))>s*1e-6 and math.hypot(a[0]-b[0],a[1]-b[1])>s*.8 for a,b in edges):continue
  if y1-y0>5*s:
   levels=[]
   for y in sorted(ys):
    if not levels or y-levels[-1]>s:levels.append(y)
   if len(levels)<3:
    row_levels=[]
    for line in layout.query('LINE'):
     a,b=line.dxf.start,line.dxf.end
     if abs(a.y-b.y)<s*1e-6 and y0-s*.1<=a.y<=y1+s*.1 and abs(a.x-b.x)>.8*w and abs(min(a.x,b.x)-left)<1.5*s and abs(max(a.x,b.x)-right)<1.5*s:row_levels.append(a.y)
    rows=[]
    for y in sorted(row_levels):
     if not rows or y-rows[-1]>s:rows.append(y)
    if len(rows)<3:continue
  candidates.append(e.dxf.handle)
  # Move only the two extreme edge clusters, preserving all interior table divisions.
  lx=max(v for v in xs if v<=x0+s*.8);rx=min(v for v in xs if v>=x1-s*.8)
  dl=left-(x0+lx)/2;dr=right-(x1+rx)/2
  nx=[(v[0]+dl if v[0]<=lx+s*1e-6 else v[0]+dr if v[0]>=rx-s*1e-6 else v[0],v[1],v[2]) for v in vs]
  if any(abs(a[0]-b[0])>s*1e-6 for a,b in zip(vs,nx)):
   e.paths[0].vertices=nx;changed.append(e.dxf.handle)
 return candidates if return_candidates else changed

def align_table_lines(doc,layout,stamp_box,scale,candidate_hatches):
 left,bottom,right,top=stamp_box;s=scale;w=right-left;intervals=[];rows=[];items=[]
 for h in candidate_hatches:
  vs=doc.entitydb[h].paths[0].vertices;ys=[v[1] for v in vs];intervals.append((min(ys),max(ys)))
 for e in layout:
  if e.dxftype()=='LINE':pts=[e.dxf.start,e.dxf.end]
  elif e.dxftype()=='LWPOLYLINE' and e.dxf.extrusion.isclose((0,0,1)) and not any(v[4] for v in e.get_points()):pts=list(e.vertices_in_wcs())
  else:continue
  if not 2<=len(pts)<=100:continue
  items.append((e,pts))
  for a,b in zip(pts,pts[1:]):
   if abs(a.y-b.y)<s*1e-6 and abs(a.x-b.x)>.8*w and abs(min(a.x,b.x)-left)<1.5*s and abs(max(a.x,b.x)-right)<1.5*s and top-.3*s<=a.y<=top+300*s:rows.append(a.y)
 seeds=[y for y in rows if y>top+.6*s]+[lo for lo,hi in intervals if lo>top+.6*s]
 reach=min(seeds) if seeds else top
 for _ in range(len(rows)+len(intervals)+1):
  old=reach
  for lo,hi in intervals:
   if lo>=top-.3*s and lo<=reach+20*s:reach=max(reach,hi)
  for y in sorted(rows):
   if y<=reach+20*s:reach=max(reach,y)
  if abs(old-reach)<s*1e-6:break
 proof=sorted([y for y in rows if top+.6*s<y<=reach+s*.1]+[v for a,b in intervals for v in (a,b) if top+.6*s<v<=reach+s*.1])
 distinct=[]
 for y in proof:
  if not distinct or y-distinct[-1]>s:distinct.append(y)
 grid_rows=[]
 for h in candidate_hatches:
  ys=sorted(v[1] for v in doc.entitydb[h].paths[0].vertices);clusters=[]
  for y in ys:
   if not clusters or y-clusters[-1]>s:clusters.append(y)
  if len(clusters)>=3:grid_rows.extend(clusters)
 if reach-top<8*s or (len(distinct)<3 and not grid_rows):return []
 changed=[]
 for e,pts in items:
  xs=[v.x for v in pts];ys=[v.y for v in pts]
  if min(ys)<top-.3*s or max(ys)>reach+s*.1 or min(xs)<left-1.5*s or max(xs)>right+1.5*s:continue
  if len(pts)==2:
   a,b=pts;horizontal=abs(a.y-b.y)<s*1e-6 and abs(a.x-b.x)>5*s;vertical=abs(a.x-b.x)<s*1e-6 and abs(a.y-b.y)>3*s and min(abs(a.x-left),abs(a.x-right))<1.5*s
   if not(horizontal or vertical):continue
  else:
   if max(xs)-min(xs)<.8*w or any(min(abs(a.x-b.x),abs(a.y-b.y))>s*1e-6 for a,b in zip(pts,pts[1:])):continue
  nx=[(left if abs(v.x-left)<1.5*s else right if abs(v.x-right)<1.5*s else v.x,v.y,v.z) for v in pts]
  if not any(abs(a.x-b[0])>s*1e-6 for a,b in zip(pts,nx)):continue
  if e.dxftype()=='LINE':e.dxf.start=nx[0];e.dxf.end=nx[1]
  else:
   old=list(e.get_points());e.set_points([(n[0],n[1],v[2],v[3],v[4]) for n,v in zip(nx,old)])
  changed.append({'handle':e.dxf.handle,'points':[list(v[:2]) for v in nx],'tolerance':s*1e-5})
 return changed
