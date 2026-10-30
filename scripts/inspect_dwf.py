"""Optional read-only DWF/DWFx diagnostics; never claims CAD editability."""
import argparse,json
from pathlib import Path
import ezdwf
p=argparse.ArgumentParser(description=__doc__);p.add_argument('source');p.add_argument('--output',required=True);a=p.parse_args()
out=Path(a.output)
if out.exists():raise FileExistsError(out)
d=ezdwf.read(a.source)
report={'source':str(Path(a.source).resolve()),'stats':d.stats(),'diagnostics':d.diagnostics,
 'mode':'experimental read-only; not a DWF to editable DWG converter',
 'warning':'Truncation/unsupported-opcode diagnostics forbid claims of complete extraction.'}
with out.open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2,default=str)
print(out)
