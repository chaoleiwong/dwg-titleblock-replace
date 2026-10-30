"""Check explicit font bindings and continuous, singly drawn frame boundaries."""
import argparse,json,math
from pathlib import Path
import cad_io
from ezdxf.fonts import fonts
from ezdxf import bbox

def strokes(entities):
    for e in entities:
        kind=e.dxftype()
        if kind=='INSERT':
            yield from strokes(e.virtual_entities())
        elif kind=='LINE':
            yield tuple(e.dxf.start)[:2],tuple(e.dxf.end)[:2]
        elif kind in ('LWPOLYLINE','POLYLINE'):
            pts=list(e.get_points('xy')) if kind=='LWPOLYLINE' else [tuple(v)[:2] for v in e.points()]
            for a,b in zip(pts,pts[1:]):yield a,b
            if e.is_closed and len(pts)>2:yield pts[-1],pts[0]

def check_document(doc,config):
    tol=float(config.get('tolerance',1e-7));layout=doc.blocks[config['block']] if config.get('block') else doc.layout(config.get('layout','Model'));errors=[];text_count=0
    selected=[];layers=set(config.get('text_layers',[]));handles=set(config.get('text_handles',[]))
    selected.extend(e for e in layout if e.dxf.layer in layers or e.dxf.handle in handles)
    for name in config.get('text_blocks',[]):selected.extend(doc.blocks[name])
    expected=config.get('font_file')
    for e in selected:
        if e.dxftype() not in ('TEXT','MTEXT','ATTRIB','ATTDEF'):continue
        text_count+=1;style=doc.styles.get(e.dxf.style);font=style.dxf.font
        family=config.get('font_family')
        if family and fonts.get_font_face(font).family!=family:errors.append({'kind':'font_resolution','handle':e.dxf.handle,'resolved_family':fonts.get_font_face(font).family,'expected_family':family})
        if expected and Path(font).name.casefold()!=Path(expected).name.casefold():errors.append({'kind':'font','handle':e.dxf.handle,'actual':font,'expected':expected})
        if e.dxftype()=='MTEXT' and ('\\f' in e.text.lower()):errors.append({'kind':'inline_font_override','handle':e.dxf.handle})
    if expected and not text_count:errors.append({'kind':'empty_text_selection'})
    for binding in config.get('text_bindings',[]):
        entity=doc.entitydb.get(binding['handle'])
        if entity is None or entity.dxftype() not in ('TEXT','MTEXT','ATTRIB','ATTDEF'):
            errors.append({'kind':'text_binding_missing','binding':binding});continue
        actual=entity.plain_text() if entity.dxftype()=='MTEXT' else entity.dxf.text
        block=binding.get('block')
        owner_ok=not block or entity.dxf.owner==doc.blocks[block].block_record_handle
        if actual!=binding['expected'] or not owner_ok:
            errors.append({'kind':'text_binding','role':binding.get('role',''),'handle':binding['handle'],'actual':actual,'expected':binding['expected'],'owner_ok':owner_ok})
    for cell in config.get('centered_cells',[]):
        e=doc.entitydb.get(cell['handle']);ctol=cell.get('tolerance',tol);cx=(cell['left']+cell['right'])/2
        if e is None or e.dxftype() not in ('TEXT','MTEXT'):
            errors.append({'kind':'center_missing','handle':cell['handle']});continue
        if cell.get('require_positive_mtext'):
            valid=(e.dxftype()=='MTEXT' and e.dxf.owner==layout.layout_key and e.dxf.attachment_point==5 and e.dxf.extrusion.isclose((0,0,1)) and e.dxf.text_direction.isclose((1,0,0)) and '\\pxqc;' in e.text)
            if not valid:errors.append({'kind':'native_center_format','handle':cell['handle']});continue
        point=e.dxf.insert if e.dxftype()=='MTEXT' else e.dxf.align_point
        if abs(point.x-cx)>ctol or ('center_y' in cell and abs(point.y-cell['center_y'])>ctol):errors.append({'kind':'center_anchor','handle':cell['handle'],'actual':[point.x,point.y],'expected_x':cx})
        box=bbox.extents([e],fast=False);margin=cell.get('margin',0)
        if not box.has_data or box.extmin.x<cell['left']+margin-ctol or box.extmax.x>cell['right']-margin+ctol:errors.append({'kind':'cell_overflow','handle':cell['handle']})
    for item in config.get('line_vertex_bindings',[]):
        e=doc.entitydb.get(item['handle']);expected=item['points'];vtol=item.get('tolerance',tol)
        actual=[tuple(e.dxf.start)[:2],tuple(e.dxf.end)[:2]] if e is not None and e.dxftype()=='LINE' else [tuple(v)[:2] for v in e.vertices_in_wcs()] if e is not None and e.dxftype()=='LWPOLYLINE' else []
        if len(actual)!=len(expected) or any(abs(a[0]-b[0])>vtol or abs(a[1]-b[1])>vtol for a,b in zip(actual,expected)):errors.append({'kind':'line_vertex_binding','handle':item['handle']})
    for item in config.get('table_hatch_edges',[]):
        e=doc.entitydb.get(item['handle']);stol=item.get('tolerance',tol);scale=item['scale']
        if e is None or e.dxftype()!='HATCH' or len(e.paths)!=1 or not hasattr(e.paths[0],'vertices') or not e.dxf.extrusion.isclose((0,0,1)):
            errors.append({'kind':'table_hatch_missing','handle':item['handle']});continue
        xs=[v[0] for v in e.paths[0].vertices]
        if not xs:errors.append({'kind':'table_hatch_empty','handle':item['handle']});continue
        lo,hi=min(xs),max(xs);lc=(lo+max(v for v in xs if v<=lo+scale*.8))/2;rc=(hi+min(v for v in xs if v>=hi-scale*.8))/2
        if abs(lc-item['left'])>stol or abs(rc-item['right'])>stol:errors.append({'kind':'table_hatch_edge_mismatch','handle':item['handle'],'actual':[lc,rc],'expected':[item['left'],item['right']]})
    lines=list(strokes(layout)) if config.get('boundaries') else [];boundaries=[]
    for item in config.get('boundaries',[]):
        a,b=item['start'],item['end'];axis=0 if abs(a[1]-b[1])<=tol else 1
        if abs(a[1-axis]-b[1-axis])>tol:raise ValueError('Boundary must be axis-aligned')
        lo,hi=sorted((a[axis],b[axis]));fixed=a[1-axis];intervals=[]
        for p,q in lines:
            if abs(p[1-axis]-fixed)>tol or abs(q[1-axis]-fixed)>tol:continue
            x,y=sorted((p[axis],q[axis]));x=max(lo,x);y=min(hi,y)
            if y-x>tol:intervals.append((x,y))
        cuts=sorted({lo,hi,*[x for pair in intervals for x in pair]});bad=[]
        for x,y in zip(cuts,cuts[1:]):
            if y-x<=tol:continue
            mid=(x+y)/2;count=sum(u-tol<=mid<=v+tol for u,v in intervals)
            if count!=1:bad.append({'interval':[x,y],'coverage':count})
        boundaries.append({'name':item.get('name',''),'bad_intervals':bad})
        if bad:errors.append({'kind':'gap_or_duplicate','boundary':item.get('name',''),'intervals':bad})
    return {'passed':not errors,'texts_checked':text_count,'boundaries':boundaries,'errors':errors}

def main():
    p=argparse.ArgumentParser();p.add_argument('drawing');p.add_argument('config');p.add_argument('--output',required=True);a=p.parse_args()
    result=check_document(cad_io.readfile(a.drawing),json.loads(Path(a.config).read_text()));Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False));raise SystemExit(0 if result['passed'] else 1)
if __name__=='__main__':main()
