"""Recognize a verified DWF family with an L-shaped footer and eight border triangles."""
def discover_triangles(lib,doc,layout):
 outers=[(e,lib.rect(e)) for e in layout if lib.rect(e)];grids=[];markers=[];triangles=[]
 manual_outer=getattr(doc,'_titleblock_partial_outer_review',None)
 if manual_outer and manual_outer['layout']==layout.name:
  for h,expected in manual_outer['entities'].items():
   entity=doc.entitydb[h];actual=([list(v) for v in entity.vertices_in_wcs()] if entity.dxftype()=='LWPOLYLINE' else [list(entity.dxf.start),list(entity.dxf.end)]);assert len(actual)==len(expected) and all(abs(x-y)<1e-7 for a,b in zip(actual,expected) for x,y in zip(a,b)),'人工复核外框边线已变化'
  outers.append((doc.entitydb[manual_outer['outer']],manual_outer['box']))
 for e in layout:
  value=lib.text(e)
  if any(s and s in value for s in getattr(doc,'_titleblock_marker_texts',())):markers.append(e)
  if e.dxftype()=='LWPOLYLINE' and not e.is_closed:
   pts=list(e.vertices_in_wcs())
   if len(pts)==3:
    xs=[p.x for p in pts];ys=[p.y for p in pts];w=max(xs)-min(xs);h=max(ys)-min(ys)
    if h>0 and 5.8<w/h<6.2:grids.append((e,[min(xs),min(ys),max(xs),max(ys)]))
  if e.dxftype()=='HATCH' and e.dxf.extrusion.isclose((0,0,1)) and len(e.paths)==1 and hasattr(e.paths[0],'vertices') and len(e.paths[0].vertices)==3:
   pts=e.paths[0].vertices;xs=[p[0] for p in pts];ys=[p[1] for p in pts];triangles.append((e,[min(xs),min(ys),max(xs),max(ys)]))
 # Collapse only identical triangle vertex sets; retain all duplicate handles for deletion.
 triangle_unique={};triangle_duplicates={}
 for entity,b in triangles:
  key=tuple(sorted((round(v[0],6),round(v[1],6),round(v[2],6)) for v in entity.paths[0].vertices))
  if key in triangle_unique:triangle_duplicates[triangle_unique[key][0].dxf.handle].append(entity.dxf.handle)
  else:triangle_unique[key]=(entity,b);triangle_duplicates[entity.dxf.handle]=[entity.dxf.handle]
 triangles=list(triangle_unique.values())
 # Some DWF pages have no L polyline: a full footer baseline and two
 # independent vertical cell dividers still establish the same footer footprint.
 lines=[e for e in layout if e.dxftype()=='LINE']
 for baseline in lines:
  a,b=baseline.dxf.start,baseline.dxf.end
  if abs(a.y-b.y)>1e-6 or abs(a.x-b.x)<100:continue
  left,right=sorted((a.x,b.x));bottom=a.y;s=(right-left)/180
  if not any(left-s<lib.anchor(e).x<left+5*s and 20*s<lib.anchor(e).y-bottom<30*s for e in markers):continue
  dividers=[]
  for line in lines:
   p,q=line.dxf.start,line.dxf.end
   if abs(p.x-q.x)>1e-6:continue
   x=(p.x-left)/s;lo,hi=sorted((p.y,q.y))
   if (40<x<60 or 130<x<160) and lo>=bottom-s and 28*s<hi-bottom<32*s:dividers.append((p.x,hi))
  if len({round(x/s,2) for x,y in dividers})<2:continue
  tops=[y for x,y in dividers]
  if max(tops)-min(tops)>s*.1:continue
  grids.append((baseline,[left,bottom,right,sum(tops)/len(tops)]))
 found=[]
 for grid,gb in grids:
  s=(gb[2]-gb[0])/180
  hs=[e.dxf.handle for e in markers if gb[0]-s<lib.anchor(e).x<gb[2]+s and gb[1]-s<lib.anchor(e).y<gb[3]+s]
  if not hs:continue
  # Quantized DWF outer border may consist of thin filled/outlined strips.
  strips=[]
  for entity in layout:
   points=None
   if entity.dxftype()=='LWPOLYLINE' and not any(v[4] for v in entity.get_points()):points=list(entity.vertices_in_wcs())
   elif entity.dxftype()=='HATCH' and entity.dxf.extrusion.isclose((0,0,1)) and all(hasattr(path,'vertices') and not any(v[2] for v in path.vertices) for path in entity.paths):points=[v for path in entity.paths for v in path.vertices]
   if not points:continue
   b=[min(v[0] for v in points),min(v[1] for v in points),max(v[0] for v in points),max(v[1] for v in points)]
   if (b[2]-b[0]>300*s and 0<b[3]-b[1]<.25*s) or (b[3]-b[1]>300*s and 0<b[2]-b[0]<.25*s):strips.append((entity,b))
  fragment_outers=[]
  for base,bb in strips:
   if not(bb[2]-bb[0]>300*s and 8*s<gb[1]-(bb[1]+bb[3])/2<12*s):continue
   for right,rb in strips:
    if not(rb[3]-rb[1]>300*s and 8*s<(rb[0]+rb[2])/2-gb[2]<12*s):continue
    x0,x1=bb[0],(rb[0]+rb[2])/2;y0,y1=(bb[1]+bb[3])/2,rb[3]
    if abs(bb[2]-x1)>.25*s or abs(rb[1]-y0)>.25*s:continue
    selected=[];sides=set()
    for entity,b in strips:
     if abs(b[0]-x0)<.25*s and abs(b[2]-x1)<.25*s:
      cy=(b[1]+b[3])/2
      if abs(cy-y0)<.25*s:sides.add('bottom');selected.append(entity)
      elif abs(cy-y1)<.25*s:sides.add('top');selected.append(entity)
     if abs(b[1]-y0)<.25*s and abs(b[3]-y1)<.25*s:
      cx=(b[0]+b[2])/2
      if abs(cx-x0)<.25*s:sides.add('left');selected.append(entity)
      elif abs(cx-x1)<.25*s:sides.add('right');selected.append(entity)
    if len(sides)==4:fragment_outers.append((base,[x0,y0,x1,y1],[e.dxf.handle for e in selected]))
  outer_handles={entity.dxf.handle:handles for entity,b,handles in fragment_outers}
  if manual_outer and manual_outer['layout']==layout.name:outer_handles[manual_outer['outer']]=list(manual_outer['entities'])
  candidates=outers+[(entity,b) for entity,b,handles in fragment_outers]
  for outer,ob in candidates:
   if not ob or not(ob[0]<gb[0]<gb[2]<ob[2] and ob[1]<gb[1]<gb[3]<ob[3]):continue
   ow,oh=ob[2]-ob[0],ob[3]-ob[1]
   sides={'left':[],'right':[],'bottom':[],'top':[]}
   for entity,b in triangles:
    w,h=b[2]-b[0],b[3]-b[1];cx,cy=(b[0]+b[2])/2,(b[1]+b[3])/2
    if w>ow*.8 and 0<h<2*s and abs(b[2]-gb[2])<1.5*s:
     if abs(cy-gb[1])<1.5*s:sides['bottom'].append((entity,cy))
     elif 3*s<ob[3]-cy<35*s:sides['top'].append((entity,cy))
    if h>oh*.8 and 0<w<2*s and abs(b[1]-gb[1])<1.5*s:
     if abs(cx-gb[2])<1.5*s:sides['right'].append((entity,cx))
     elif 3*s<cx-ob[0]<35*s:sides['left'].append((entity,cx))
   if any(len(v)!=2 or abs(v[0][1]-v[1][1])>s*.1 for v in sides.values()):continue
   coords={}
   for side,rows in sides.items():
    axis=0 if side in ('left','right') else 1
    values=[v[axis] for entity,fixed in rows for path in entity.paths for v in path.vertices]
    coords[side]=(min(values)+max(values))/2
   ib=[coords['left'],coords['bottom'],coords['right'],coords['top']]
   if not(ob[0]<ib[0]<ib[2]<ob[2] and ob[1]<ib[1]<ib[3]<ob[3]):continue
   handles=[h for rows in sides.values() for e,v in rows for h in triangle_duplicates[e.dxf.handle]]
   if len({e.dxf.handle for rows in sides.values() for e,v in rows})!=8:continue
   found.append({'family':'eight-triangle-border','outer':outer.dxf.handle,'outer_handles':outer_handles.get(outer.dxf.handle,[outer.dxf.handle]),'inner':handles[0],'inner_handles':handles,'grid':grid.dxf.handle,'outer_box':ob,'inner_box':ib,'scale':s,'stamp_box':gb,'company_markers':hs,'old_height_mm':(gb[3]-gb[1])/s})
 unique={}
 for candidate in found:
  key=tuple(sorted(candidate['inner_handles']))
  prior=unique.get(key)
  if prior:
   preferred=getattr(doc,'_titleblock_preferred_frame_grid',None)
   if preferred==candidate['grid']:
    candidate['alternate_grid_handles']=[prior['grid']];unique[key]=candidate;continue
   if preferred==prior['grid']:
    prior.setdefault('alternate_grid_handles',[]).append(candidate['grid']);continue
   if any(abs(a-b)>candidate['scale']*.2 for a,b in zip(prior['stamp_box'],candidate['stamp_box'])):
    # A newly overlaid title grid can enclose the printed grid and additional
    # as-built company markers. Require both marker superiority and containment.
    def encloses(large,small):
     b=large['stamp_box'];a=small['stamp_box'];pad=large['scale']*.6
     return b[0]-pad<=a[0] and b[1]-pad<=a[1] and b[2]+pad>=a[2] and b[3]+pad>=a[3] and abs(b[0]-a[0])<4*large['scale']
    if len(candidate['company_markers'])>len(prior['company_markers']) and encloses(candidate,prior):
     candidate['alternate_grid_handles']=[prior['grid']];unique[key]=candidate;continue
    if len(prior['company_markers'])>len(candidate['company_markers']) and encloses(prior,candidate):
     prior.setdefault('alternate_grid_handles',[]).append(candidate['grid']);continue
    raise ValueError('同一内框对应多个不一致的标题栏边界，需逐图核对 '+repr([(v['grid'],v['stamp_box'],v['company_markers']) for v in [prior,candidate]]))
   if doc.entitydb[prior['grid']].dxftype()=='LWPOLYLINE':continue
  unique[key]=candidate
 return list(unique.values())

if __name__=='__main__':
 import argparse,json,hashlib
 from pathlib import Path
 import cad_io
 import native_vertical_company as lib
 parser=argparse.ArgumentParser(description='只读识别八三角形边框候选，需显式配置文字标记并逐图复核')
 parser.add_argument('source')
 parser.add_argument('--marker-text',action='append',default=[],help='标记文字，可重复；默认空，不产生候选')
 parser.add_argument('--output',required=True)
 args=parser.parse_args()
 source=Path(args.source)
 doc=cad_io.readfile(source)
 doc._titleblock_marker_texts=args.marker_text
 candidates=[{'layout':layout.name,**frame} for layout in doc.layouts for frame in discover_triangles(lib,doc,layout)]
 with source.open('rb') as stream:input_hash=hashlib.file_digest(stream,'sha256').hexdigest()
 Path(args.output).write_text(json.dumps({'input_sha256':input_hash,'candidates':candidates},ensure_ascii=False,indent=2))
 print('candidate triangle frames:',len(candidates))
