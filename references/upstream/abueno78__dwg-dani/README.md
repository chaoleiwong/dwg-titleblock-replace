# dwg-dani

Skill para leitura, edição e criação de arquivos **DWG/DXF** (AutoCAD) de forma programática usando Python.

## Arquitetura

```
DWG ←→ [ODA File Converter] ←→ DXF ←→ [ezdxf Python] ←→ manipulação
```

- **ezdxf**: Biblioteca Python que lê/escreve DXF (R12 até R2018).
- **ODA File Converter**: Ferramenta externa que converte entre DWG, DXF e DXB.
- **ezdxf.addons.odafc**: Add-on integrado que encapsula o ODA File Converter.

## Instalação

```bash
pip install -r requirements.txt
```

### ODA File Converter (necessário para DWG)

Baixe em: https://www.opendesign.com/guestfiles/oda_file_converter

**Linux (AppImage):**
```bash
mkdir -p ~/Apps
chmod a+x ~/Apps/ODAFileConverter_QT6_lnxX64_8.3dll_25.11.AppImage
```

Configure o `~/.config/ezdxf/ezdxf.ini`:
```ini
[odafc-addon]
unix_exec_path = /home/<user>/Apps/ODAFileConverter_QT6_lnxX64_8.3dll_25.11.AppImage
```

## Uso

### Ler um arquivo DWG

```python
from ezdxf.addons import odafc

doc = odafc.readfile("desenho.dwg")
msp = doc.modelspace()

for entity in msp:
    print(entity.dxftype(), entity.dxf.layer)
```

### Criar um desenho

```python
import ezdxf

doc = ezdxf.new(dxfversion="R2018")
msp = doc.modelspace()
doc.layers.add("WALLS", color=1)
msp.add_line(start=(0, 0), end=(10, 0), dxfattribs={"layer": "WALLS"})
doc.saveas("output.dxf")
```

### Exportar para SVG

```python
from ezdxf.addons.drawing import Frontend, RenderContext, svg

ctx = RenderContext(doc)
out = svg.SVGBackend()
frontend = Frontend(ctx, out)
frontend.draw_layout(msp)
with open("preview.svg", "wt") as f:
    f.write(out.get_string())
```

## Exemplos

Veja a pasta `examples/` para scripts completos:
- `read_dwg.py` — Ler e inspecionar arquivo DWG
- `create_drawing.py` — Criar desenho do zero
- `modify_entities.py` — Editar entidades existentes

## Dependências

- Python 3.10+
- ezdxf
- ODA File Converter (para DWG)
- matplotlib (opcional, para export PNG)

## Licença

MIT
