# Font and frame gate

In an apply plan, `quality_gate` is an object with the following fields. In a standalone check, save that object directly as JSON.

- `layout`: layout name, defaults to Model.
- `block`: optional exact block definition name. When set, direct text handles and centered cells are checked against this block owner and use block-local coordinates. Each top-level title outside the block needs a separate gate for its actual layout. List and review every reference and its transform before editing a shared definition; this gate does not authorize changing all references.
- `font_file`: expected actual font filename, such as SongtiSC-Regular.ttf. Bind all selected styles to the verified font; check file availability separately.
- `font_family`: expected resolved font family. Supply this when selecting a TrueType font so a renderer fallback cannot pass solely by matching the STYLE filename.
- `text_layers`, `text_handles`: explicit top-level text selection, combined by union.
- `text_blocks`: block definitions whose direct text should use that font. For nested definitions, list each relevant definition explicitly.
- `tolerance`: coordinate tolerance in the drawing's units; choose based on conversion precision, not screen pixels.
- `boundaries`: objects containing `name`, `start: [x,y]`, `end: [x,y]`, in world coordinates. List each required horizontal/vertical shared boundary, including all title-stamp/frame joints. The checker rejects a gap or coverage by more than one collinear segment. It expands INSERT geometry, including mirrored inserts, before checking.

Run with the skill's configured Python:

```
python scripts/quality_gate.py drawing.dwg gate.json --output gate-result.json
```

The gate does not detect unrelated crossing strokes, arbitrary curves, unlisted boundaries or missing fonts outside its selection. Do not declare all geometry correct from a partial gate. Use selected-entity fingerprints for edit scope, font resolution checks, DWG audit and visual review too.

On this Mac, ezdxf default font scanning may miss `~/Library/Fonts`. After installing a font there, scan that directory explicitly with `fonts.font_manager.scan_all([directory])`, persist its font manager cache, and confirm `fonts.get_font_face(filename).family` matches the intended family in a fresh process. A STYLE filename with a fallback family is a failed check.

- `text_bindings`: list of `{role, handle, block, expected}`. Verify text by exact entity handle and owning block, not by searching for a matching string anywhere in the drawing. Register both preserved station headings and populated drawing-title placeholders. Configure protected headings explicitly and bind the drawing title to its actual placeholder. Rebuild bindings from the staged document after import, not from guessed original handles.

- `centered_cells`: list of `{handle, left, right, center_y, margin, tolerance, require_positive_mtext}`. For a mirrored title stamp, list the selected central rows after creating independent, positive-OCS model-space MTEXT. Set attachment point 5 and explicit paragraph center (`\pxqc;`), keeping the original row/font. The gate checks the owner layout, positive extrusion/text direction, center anchor and text box staying within the cell margin. `text_bindings` checks the MTEXT plain text, ignoring the formatting controls. These are horizontal cells in world coordinates; convert other cell orientations first. A renderer-only centered bbox inside a mirrored block is insufficient evidence of native CAD centering.

- `line_vertex_bindings`: list of `{handle, points, tolerance?}`. `points` is an ordered list of `[x, y]` coordinates: start then end for LINE, or all vertices in WCS order for LWPOLYLINE. The checker compares vertex count, order and each x/y coordinate; it does not support POLYLINE here or check z, bulges, widths or closed state. Per-item `tolerance` defaults to the gate's `tolerance`.
- `table_hatch_edges`: list of `{handle, scale, left, right, tolerance?}`. The entity must be HATCH with exactly one vertex-based boundary path and positive Z extrusion `(0,0,1)`. `scale` is required and defines the endpoint bands: within `scale * 0.8` of the minimum/maximum x. The checker takes each band's extreme-x midpoint and compares it to `left`/`right`; these are endpoint center x coordinates in the boundary's coordinate system (positive Z), not outer edges. It does not check y or general hatch geometry. Per-item `tolerance` defaults to the gate's `tolerance`.

## Rebuild bindings after import

1. Run `prepare` and select entities from the fixed source/template snapshots; their handles identify inputs only.
2. In a custom apply workflow, import and transform the selected template into the source document, then save a staging DXF and reopen it (the `prepare` → `apply` staging-document readback).
3. Locate the actual imported entities in that reopened document using the replacement report's new block/insert and verified field role, owner, text and geometry. Read their actual handles and coordinates; rebuild `text_handles`, `text_bindings`, `centered_cells`, `line_vertex_bindings` and `table_hatch_edges` as applicable. Do not reuse or guess template handles.
4. Run `check_document` on the staging document and again on the final DWG readback with the rebuilt bindings. Save the configuration and results; if handles change during conversion, explicitly re-identify and verify the entities before rebuilding them again.

The stock `titleblock.py apply` saves/reopens staging internally and passes the supplied `quality_gate` unchanged to the checker. It does not expose a staging pause or automatically rebuild these gate bindings. Imported-entity bindings therefore require an explicit custom workflow; merely adding input handles to the plan does not perform this step.
