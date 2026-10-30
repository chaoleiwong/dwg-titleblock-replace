# dwg interpreter — claude skill

A Claude Code skill that reads DWG files on Windows without AutoCAD and without BricsCAD.

The skill converts the DWG to DXF with **GNU LibreDWG** (`dwg2dxf`), reads the DXF with **ezdxf**,
and writes two files next to the drawing:

| File | Content |
|---|---|
| `<name>.dwg-views.json` | the full inventory of the drawing |
| `<name>.dxf` | the conversion, to open in a CAD application |

The source DWG is not modified. The script does not access the network.

The inventory records what a person sees when they open the drawing: layouts, viewports with
scale, named views, section and elevation labels, layers, blocks, title block attributes, texts,
dimensions, and geometry. Every item carries the entity `handle`, which locates the object in CAD.

## Why it exists

A language model cannot read DWG. Without the extraction, every question about the drawing becomes
a guess. This skill produces data verified against the file — sheet scale, units, dimension values,
which layout holds each view.

The JSON also solves the context cost. The DXF of an architectural drawing is more than 18 MB and
1.9 million lines. The equivalent JSON is 476 KB. The stdout summary is a few hundred tokens and
already answers most questions.

## Two variants

The repository holds the same skill in two languages. Install one of them.

```
en/dwg-views/       English: skill instructions, messages, unit names, view-label patterns
pt-br/dwg-views/    Portuguese: skill instructions, messages, unit names, view-label patterns
```

The two variants extract the same data with the same JSON schema. Three things change with the
language:

| Item | `en` | `pt-br` |
|---|---|---|
| `SKILL.md` and trigger phrases | English | Portuguese |
| stdout summary, stderr messages, `--help` | English | Portuguese |
| `document.insunits.name` | `millimeter`, `meter`, `undetermined` | `milimetro`, `metro`, `indeterminada` |
| `view_labels` patterns | `SECTION`, `DETAIL`, `ELEVATION`, `FLOOR PLAN`, `SCALE 1:N` | `CORTE`, `DETALHE`, `ELEVAÇÃO`, `PLANTA BAIXA`, `ESCALA 1:N` |

Match the variant to the language of the drawings you read. View-label detection is the part that
depends on it: a sheet labeled `CORTE AA` is not found by the English patterns.

## Requirements

| Item | Status |
|---|---|
| Windows | required — the backend ships as a win64 binary |
| Python | required; tested on 3.14 |
| `ezdxf` | `python -m pip install ezdxf` |
| `dwg2dxf` (LibreDWG) | install as shown below; the script does not install it |

## Installation

Copy one variant into `~/.claude/skills/`. Both folders are named `dwg-views`, so install only one
of them:

```powershell
Copy-Item -Recurse en/dwg-views "$env:USERPROFILE\.claude\skills\"
```

Install the backend one time per machine. Run it as a native PowerShell command, on one line:

```powershell
$d="$env:LOCALAPPDATA\libredwg"; New-Item -ItemType Directory -Force $d | Out-Null; Invoke-WebRequest 'https://github.com/LibreDWG/libredwg/releases/download/0.14/libredwg-0.14-win64.zip' -OutFile "$env:TEMP\libredwg.zip" -UseBasicParsing; Expand-Archive "$env:TEMP\libredwg.zip" -DestinationPath $d -Force
```

Confirm the installation:

```powershell
& "$env:LOCALAPPDATA\libredwg\dwg2dxf.exe" --version
```

The correct answer is `dwg2dxf 0.14`. The download is approximately 11.5 MB. It extracts without an
installer and without registration.

## Direct use

The script runs on its own, outside Claude Code:

```powershell
python en/dwg-views/scripts/dwg_views.py "C:\path\drawing.dwg"
```

The main flags are `--layout NAME`, `--geometry`, `--json-out`, `--no-json`, `--dxf-out`,
`--no-dxf`, `--stdout`, and `--self-check`. The full table is in
[en/dwg-views/SKILL.md](https://github.com/MatheusMeM/dwg-interpreter-claude-skill/blob/0d14cf739e89e02d4e40e2a9761d4d19111d3c8d/en/dwg-views/SKILL.md).

`--self-check` runs the internal asserts against a drawing and reports to stderr:

```powershell
python en/dwg-views/scripts/dwg_views.py --self-check "C:\path\drawing.dwg"
```

## Coverage

LibreDWG 0.14 reads DWG R10 to R2018 (signatures `AC1006` to `AC1032`). A newer file exits with
code 5 and asks you to save it again as DWG 2018 or earlier.

A `.dxf` file is accepted directly, with no conversion step.

## License

MIT. See [LICENSE](LICENSE).

GNU LibreDWG is a separate project, under GPL-3.0. It is not redistributed here.
