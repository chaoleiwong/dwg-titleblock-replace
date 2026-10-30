"""Prepare inventories and apply explicit, hash-bound CAD title-block replacements."""
import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
import uuid
import ezdxf
from ezdxf import bbox, xref
from ezdxf.lldxf.tagwriter import TagCollector
import cad_io


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def write_json(path,data):
    with Path(path).open('x',encoding='utf-8') as f:
        json.dump(data,f,ensure_ascii=False,indent=2,default=str)


def fingerprint(e):
    c=TagCollector(dxfversion=e.doc.dxfversion)
    e.export_dxf(c)
    # Owner and entity handles are identity metadata, not visual content.
    return hashlib.sha256(repr([(t.code,t.value) for t in c.tags if t.code not in (5,105,330)]).encode()).hexdigest()


def semantic_fingerprint(e):
    c=TagCollector(dxfversion=e.doc.dxfversion);e.export_dxf(c)
    tags=[];subclass=''
    for t in c.tags:
        if t.code==100:subclass=t.value
        if t.code in (5,105,330):continue
        # ODA makes these documented default flags explicit; omission has the same meaning.
        if subclass in ('AcDbAttribute','AcDbAttributeDefinition') and t.code==280 and t.value==0:continue
        if e.dxftype()=='VIEWPORT' and t.code==292 and t.value==1:continue
        if e.dxftype()=='LWPOLYLINE' and t.code==43 and t.value==0:continue
        v=round(t.value,9) if isinstance(t.value,float) else t.value
        tags.append((t.code,v))
    return hashlib.sha256(repr(tags).encode()).hexdigest()


def document_signature(doc):
    blocks={}
    for b in doc.blocks:
        if b.is_any_layout:continue
        blocks[b.name]={'origin':list(b.block.dxf.base_point),'entities':[semantic_fingerprint(e) for e in b]}
    resources={}
    for table,keys in [('layers',['color','true_color','linetype','lineweight','flags','plot']),('styles',['font','bigfont','height','width','oblique','flags'])]:
        resources[table]={e.dxf.name:{k:str(e.dxf.get(k)) for k in keys if e.dxf.is_supported(k)} for e in getattr(doc,table)}
    return {'layouts':{l.name:[semantic_fingerprint(e) for e in l] for l in doc.layouts},'blocks':blocks,'resources':resources,'units':doc.units}


def locator(doc,path,root_order,target_tag=None):
    loc=[{'root':root_order.index(path[0])}];e=resolve(doc,[path[0]])
    for h in path[1:]:
        a=next((x for x in e.attribs if x.dxf.handle==h),None)
        if a is not None:loc.append({'attribute':a.dxf.tag});e=a
        else:
            children=list(e.block());idx=next(i for i,x in enumerate(children) if x.dxf.handle==h)
            loc.append({'child':idx});e=children[idx]
    if target_tag is not None:loc.append({'attribute':target_tag})
    return loc


def bound_text(ref,loc):
    e=list(ref.block())[loc[0]['root']]
    for step in loc[1:]:
        if 'attribute' in step:
            e=e.get_attrib(step['attribute'])
        else:e=list(e.block())[step['child']]
        if e is None:raise RuntimeError('Mapped field target missing')
    return text_value(e)


def validate_bindings(doc,replacements):
    for j in replacements:
        refs=[e for e in doc.layouts.get(j['layout']).query('INSERT') if e.dxf.name==j['new_block']]
        if len(refs)!=1:raise RuntimeError('Expected exactly one inserted replacement block')
        for binding in j['bindings']:
            if bound_text(refs[0],binding['locator'])!=binding['value']:
                raise RuntimeError('Mapped field value mismatch: '+binding['name'])


def extent(e):
    try:
        b=bbox.extents([e],fast=True)
        return [list(b.extmin),list(b.extmax)] if b.has_data else None
    except Exception:return None


def text_value(e):
    if e.dxftype()=='MTEXT':return e.plain_text()
    if e.dxftype() in ('TEXT','ATTRIB','ATTDEF'):return e.dxf.text
    return None


def walk_text(e,path,depth=0,stack=()):
    value=text_value(e)
    if value is not None:
        yield {'path':path,'type':e.dxftype(),'text':value,'tag':e.dxf.tag if e.dxf.is_supported('tag') else ''}
    if e.dxftype()!='INSERT' or depth>=12:return
    for a in e.attribs:
        yield from walk_text(a,path+[a.dxf.handle],depth+1,stack)
    name=e.dxf.name
    if name in stack:return
    b=e.block()
    if b is not None:
        for child in b:
            yield from walk_text(child,path+[child.dxf.handle],depth+1,stack+(name,))


def inventory(doc):
    layouts=[]
    for layout in doc.layouts:
        entities=[]
        for e in layout:
            row={'handle':e.dxf.handle,'type':e.dxftype(),'layer':e.dxf.layer,'bbox':extent(e),'fingerprint':fingerprint(e)}
            if e.dxftype()=='INSERT':
                row.update(block=e.dxf.name,insert=list(e.dxf.insert),rotation=e.dxf.rotation,scale=[e.dxf.xscale,e.dxf.yscale,e.dxf.zscale],array=[e.dxf.row_count,e.dxf.column_count])
            row['texts']=list(walk_text(e,[e.dxf.handle]))
            entities.append(row)
        layouts.append({'layout':layout.name,'entity_count':len(layout),'types':dict(Counter(e.dxftype() for e in layout)),'entities':entities})
    return {'units_code':doc.units,'dxf_version':doc.dxfversion,'layouts':layouts,
        'warnings':['Bounding boxes are candidates only, never automatic deletion instructions.','TEXT outlines, raster-only text and proprietary proxy data may not yield fields.','Nested text paths identify definitions; bbox on each top-level INSERT is in its layout coordinates.']}


def draw(doc,path,layout='Model'):
    os.environ.setdefault('MPLCONFIGDIR',str(Path(tempfile.gettempdir())/'titleblock-mpl'))
    os.environ.setdefault('MPLBACKEND','Agg')
    from ezdxf.addons.drawing import matplotlib
    matplotlib.qsave(doc.layouts.get(layout),path,dpi=100)


def prepare(source,template,workdir):
    source,template=Path(source).resolve(),Path(template).resolve()
    w=Path(workdir).resolve();w.mkdir(parents=True,exist_ok=False)
    manifest={'schema':1}
    for role,p in [('source',source),('template',template)]:
        h=digest(p);doc=cad_io.readfile(p);snap=w/(role+'.snapshot.dxf');doc.saveas(snap)
        if digest(p)!=h:raise RuntimeError('Input changed while preparing')
        # Reopen so all later handles/fingerprints refer to the exact persisted snapshot.
        doc=ezdxf.readfile(snap)
        write_json(w/(role+'.inventory.json'),inventory(doc))
        manifest[role]={'path':str(p),'sha256':h,'snapshot':str(snap),'snapshot_sha256':digest(snap)}
    write_json(w/'manifest.json',manifest)
    print(w/'manifest.json')


def checked_inputs(manifest):
    docs={}
    for role in ['source','template']:
        info=manifest[role]
        if digest(info['path'])!=info['sha256'] or digest(info['snapshot'])!=info['snapshot_sha256']:
            raise ValueError(role+' hash mismatch; prepare again')
        docs[role]=ezdxf.readfile(info['snapshot'])
    return docs


def select(layout,handles):
    if not handles or len(handles)!=len(set(handles)):raise ValueError('Selection empty or duplicate handles')
    lookup={e.dxf.handle:e for e in layout}
    missing=set(handles)-set(lookup)
    if missing:raise ValueError('Handles not in requested layout: '+str(missing))
    return [lookup[h] for h in handles]


def resolve(doc,path):
    if not path:raise ValueError('Empty text path')
    e=doc.entitydb.get(path[0])
    if e is None or not e.is_alive:raise ValueError('Unknown root handle '+path[0])
    for h in path[1:]:
        if e.dxftype()!='INSERT':raise ValueError('Text path must traverse INSERT')
        children=list(e.attribs)+list(e.block() or [])
        e=next((x for x in children if x.dxf.handle==h),None)
        if e is None:raise ValueError('Invalid nested text path '+h)
    return e


def fields(source,template,mappings,old_handles,template_handles,protected_titles=()):
    extracted={};tag_groups={};targets=set();bindings=[]
    root_order=[e.dxf.handle for layout in template.layouts for e in layout if e.dxf.handle in template_handles]
    for m in mappings:
        if not m.get('name') or not m.get('evidence'):raise ValueError('Each field needs name and evidence')
        if 'source_path' in m:
            if m['source_path'][0] not in old_handles:raise ValueError('Field source outside old-frame selection')
            e=resolve(source,m['source_path']);value=text_value(e)
            if value is None:raise ValueError('Source is not editable text')
            if 'expected' not in m or value!=m['expected']:raise ValueError('Field expected text mismatch')
        elif 'literal' in m:
            value=str(m['literal'])
        else:raise ValueError('Field requires source_path or evidenced literal')
        if m['name'] in extracted:raise ValueError('Duplicate field name')
        extracted[m['name']]=value
        target=m['target'];path=target['path']
        if path[0] not in template_handles:raise ValueError('Target outside template selection')
        e=resolve(template,path)
        semantic_text=e.plain_text() if e.dxftype()=='MTEXT' else text_value(e)
        if semantic_text in protected_titles and value!=semantic_text:
            raise ValueError('Protected title; select the actual drawing-title placeholder')
        key=(e.dxf.handle,target.get('tag'))
        if key in targets:raise ValueError('Two fields map to the same target entity/tag')
        targets.add(key)
        # Every traversal into a shared definition can affect other instances,
        # including nested INSERT attributes. Root INSERT attributes are local.
        for prefix_len in range(1,len(path)):
            parent=resolve(template,path[:prefix_len]);child=path[prefix_len]
            if any(a.dxf.handle==child for a in parent.attribs):continue
            refs=sum(1 for x in template.entitydb.values() if x.is_alive and x.dxftype()=='INSERT' and x.dxf.name==parent.dxf.name)
            if refs>1:raise ValueError('Shared block definition field requires instance isolation before prepare')
        bindings.append({'name':m['name'],'value':value,'locator':locator(template,path,root_order,target.get('tag'))})
        if 'tag' in target:
            if e.dxftype()!='INSERT':raise ValueError('Attribute target must be INSERT')
            if sum(1 for a in e.attribs if a.dxf.tag==target['tag'])>1:raise ValueError('Ambiguous duplicate attribute tag')
            tag_groups.setdefault(tuple(path),{})[target['tag']]=value
        elif e.dxftype() in ('TEXT','MTEXT','ATTRIB'):
            if e.dxftype()=='MTEXT':e.text=value
            else:e.dxf.text=value
        else:raise ValueError('Target must be TEXT/MTEXT/ATTRIB or INSERT plus tag')
    for path,values in tag_groups.items():
        ins=resolve(template,path);missing={}
        for tag,value in values.items():
            a=ins.get_attrib(tag)
            if a is not None:a.dxf.text=value
            else:
                b=ins.block()
                if b is None or b.get_attdef(tag) is None:raise ValueError('Unknown target attribute tag '+tag)
                missing[tag]=value
        if missing:ins.add_auto_attribs(missing)
    return extracted,bindings


def check_importable(entities,stack=()):
    for e in entities:
        if e.dxftype() in ('VIEWPORT','IMAGE','PDFUNDERLAY','DWFUNDERLAY','DGNUNDERLAY','ACAD_TABLE','ACAD_PROXY_ENTITY') or e.__class__.__name__=='DXFTagStorage':
            raise ValueError('Template requires native CAD import: '+e.dxftype())
        if e.dxftype()=='INSERT':
            if e.is_xref() or e.dxf.row_count>1 or e.dxf.column_count>1:raise ValueError('Template XREF/MINSERT not supported')
            if e.dxf.name in stack:raise ValueError('Recursive block definition')
            block=e.block()
            if block is None:raise ValueError('Missing block definition')
            check_importable(block,stack+(e.dxf.name,))


def all_graphics(doc):
    # Includes block-definition contents and attached ATTRIBs so shared-block mutations are detected.
    return {h:fingerprint(e) for h,e in doc.entitydb.items() if e.is_alive and hasattr(e,'graphic_properties')}


def validate_untouched(doc,expected):
    failures=[]
    for h,sig in expected.items():
        e=doc.entitydb.get(h)
        if e is None or not e.is_alive or fingerprint(e)!=sig:failures.append(h)
    if failures:raise RuntimeError('Untouched geometry changed: '+str(failures[:25]))


def apply(plan_path,output):
    plan=json.loads(Path(plan_path).read_text());manifest=json.loads(Path(plan['manifest']).read_text())
    docs=checked_inputs(manifest);doc=docs['source'];baseline=all_graphics(doc)
    output=Path(output).resolve();report_path=output.with_suffix(output.suffix+'.audit.json')
    if output.exists() or report_path.exists():raise FileExistsError('Output or report exists')
    if output.suffix.lower() not in ('.dwg','.dxf'):raise ValueError('Output must be DWG or DXF')
    if not plan.get('replacements'):raise ValueError('Empty replacements')
    report={'inputs':manifest,'replacements':[],'scope':'Explicit selected entities only; unchanged graphics fingerprint checked in staging DXF.'}
    deleted=set();new_inserts=[]
    for job in plan['replacements']:
        if not job.get('selection_evidence') or not job.get('old_frame_only'):
            raise ValueError('Need visual/structural selection evidence and old_frame_only=true')
        layout=doc.layouts.get(job['layout']);old=select(layout,job['old_handles'])
        if deleted.intersection(job['old_handles']):raise ValueError('Overlapping removal selections')
        if any(e.dxftype() in ('VIEWPORT','IMAGE','PDFUNDERLAY','DWFUNDERLAY','DGNUNDERLAY','ACAD_PROXY_ENTITY') for e in old):
            raise ValueError('Cannot remove viewport/image/underlay/proxy as a title frame')
        # Reject external references: their entire contents cannot be treated as a proven frame.
        if any(e.dxftype()=='INSERT' and (e.is_xref() or e.dxf.row_count>1 or e.dxf.column_count>1) for e in old):
            raise ValueError('XREF/MINSERT removal requires a separate, specific workflow')
        template=ezdxf.readfile(manifest['template']['snapshot'])
        tl=template.layouts.get(job['template_layout']);chosen=select(tl,job['template_handles'])
        check_importable(chosen)
        extracted,bindings=fields(doc,template,job.get('fields',[]),job['old_handles'],job['template_handles'],plan.get('protected_titles',[]))
        scale=float(job['scale']);angle=float(job['rotation'])
        if not math.isfinite(scale) or scale<=0 or not math.isfinite(angle):raise ValueError('Invalid uniform scale/rotation')
        origin=job['template_origin'];insert=job['insert']
        if len(origin)!=3 or len(insert)!=3 or not all(math.isfinite(float(x)) for x in origin+insert):raise ValueError('Expected finite XYZ coordinates')
        if not job.get('alignment_evidence'):raise ValueError('Need explicit alignment and units evidence')
        name='FRAME_'+uuid.uuid4().hex[:12];block=doc.blocks.new(name,base_point=origin)
        loader=xref.Loader(template,doc,conflict_policy=xref.ConflictPolicy.XREF_PREFIX)
        keep=set(job['template_handles'])
        if tl.name=='Model':loader.load_modelspace(block,filter_fn=lambda e:e.dxf.handle in keep)
        else:loader.load_paperspace_layout_into(tl,block,filter_fn=lambda e:e.dxf.handle in keep)
        loader.execute(xref_prefix=name)
        if len(block)!=len(chosen):raise RuntimeError('Importer skipped a selected entity')
        ref=layout.add_blockref(name,insert,dxfattribs={'xscale':scale,'yscale':scale,'zscale':scale,'rotation':angle})
        new_inserts.append(ref.dxf.handle)
        removed=[]
        for e in old:
            removed.append({'handle':e.dxf.handle,'type':e.dxftype(),'layer':e.dxf.layer,'texts':list(walk_text(e,[e.dxf.handle]))})
            deleted.add(e.dxf.handle)
            if hasattr(e,'all_sub_entities'):deleted.update(a.dxf.handle for a in e.all_sub_entities())
            layout.delete_entity(e)
        report['replacements'].append({'layout':layout.name,'deleted':removed,'new_block':name,'new_insert':ref.dxf.handle,'fields':extracted,'bindings':bindings,'alignment':{'origin':origin,'insert':insert,'scale':scale,'rotation':angle}})
    expected={h:s for h,s in baseline.items() if h not in deleted}
    validate_untouched(doc,expected)
    validate_bindings(doc,report['replacements'])
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='frame-stage-',dir=output.parent) as tmp:
        tmp=Path(tmp);stage=tmp/'result.dxf';doc.saveas(stage)
        reopened=ezdxf.readfile(stage);validate_untouched(reopened,expected)
        validate_bindings(reopened,report['replacements'])
        audit=reopened.audit()
        if audit.has_errors:raise RuntimeError('Unresolved DXF audit errors: '+str(audit.errors[:5]))
        if output.suffix.lower()=='.dwg':
            candidate=tmp/'result.dwg';cad_io.convert(stage,candidate,version=plan.get('dwg_version','R2018'))
            roundtrip=cad_io.readfile(candidate)
            report['dwg_reopened']=True
            validate_bindings(roundtrip,report['replacements'])
            report['dwg_geometry_equivalent']=document_signature(ezdxf.readfile(stage))==document_signature(roundtrip)
            if not report['dwg_geometry_equivalent']:raise RuntimeError('DWG conversion changed layout/block/resource signatures; native CAD review required')
        else:candidate=stage
        if plan.get('quality_gate'):
            from quality_gate import check_document
            report['quality_gate']=check_document(roundtrip if output.suffix.lower()=='.dwg' else reopened,plan['quality_gate'])
            if not report['quality_gate']['passed']:raise RuntimeError('Font/frame quality gate failed: '+str(report['quality_gate']['errors']))
        if digest(manifest['source']['path'])!=manifest['source']['sha256'] or digest(manifest['template']['path'])!=manifest['template']['sha256']:raise RuntimeError('Original input changed')
        with candidate.open('rb') as r,output.open('xb') as w:shutil.copyfileobj(r,w)
    report.update(output=str(output),output_sha256=digest(output),unchanged_graphics_checked=len(expected),source_preserved=True,template_preserved=True)
    write_json(report_path,report);print(output)


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='cmd',required=True)
    a=sub.add_parser('prepare');a.add_argument('source');a.add_argument('template');a.add_argument('--workdir',required=True)
    a=sub.add_parser('apply');a.add_argument('plan');a.add_argument('--output',required=True)
    a=sub.add_parser('render');a.add_argument('source');a.add_argument('--layout',default='Model');a.add_argument('--output',required=True)
    args=p.parse_args()
    if args.cmd=='prepare':prepare(args.source,args.template,args.workdir)
    elif args.cmd=='apply':apply(args.plan,args.output)
    else:
        if Path(args.output).exists():raise FileExistsError(args.output)
        draw(cad_io.readfile(args.source),args.output,args.layout)


if __name__=='__main__':main()
