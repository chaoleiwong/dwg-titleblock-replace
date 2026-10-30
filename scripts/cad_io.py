"""DXF/DWG I/O through the official ODA converter. Never overwrite sources."""
from pathlib import Path
import os
import shutil
import tempfile
import ezdxf
from ezdxf.addons import odafc

def configure():
    configured = os.environ.get('ODA_FILE_CONVERTER')
    executable = configured or shutil.which('ODAFileConverter') or '/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter'
    oda = Path(executable).expanduser()
    if not oda.is_file():
        raise FileNotFoundError(f'ODA converter missing: {oda}; set ODA_FILE_CONVERTER')
    ezdxf.options.set('odafc-addon', 'unix_exec_path', str(oda.resolve()))

def readfile(source):
    source = Path(source).resolve()
    if source.suffix.lower() == '.dxf':
        return ezdxf.readfile(source)
    if source.suffix.lower() != '.dwg':
        raise ValueError('Expected .dwg or .dxf')
    configure()
    # Isolate the converter from other drawings in the source directory.
    with tempfile.TemporaryDirectory(prefix='cad-dwg-') as tmp:
        p = Path(tmp)/"source.dwg"
        shutil.copy2(source,p)
        return odafc.readfile(p, version='R2018', audit=False)

def convert(source, target, version='R2018'):
    configure()
    source,target=Path(source).resolve(),Path(target).resolve()
    if source.suffix.lower() not in ('.dwg','.dxf') or target.suffix.lower() not in ('.dwg','.dxf'):
        raise ValueError('Conversion supports .dwg and .dxf only')
    if source==target or target.exists():
        raise FileExistsError(f'Output already exists: {target}')
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='cad-convert-') as tmp:
        folder=Path(tmp);inp=folder/'input';inp.mkdir()
        p=inp/source.name;shutil.copy2(source,p)
        out=folder/('result'+target.suffix.lower())
        odafc.convert(p,out,version=version,audit=False,replace=False)
        if not out.is_file() or not out.stat().st_size:
            raise RuntimeError('ODA produced no output')
        with out.open('rb') as r,target.open('xb') as w:shutil.copyfileobj(r,w)
    return target
