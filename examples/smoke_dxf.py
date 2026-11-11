"""Create a synthetic drawing and exercise prepare, apply, and readback."""
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import ezdxf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import titleblock


def main():
    with TemporaryDirectory() as directory:
        root = Path(directory)
        source, template, output = (root / name for name in ("source.dxf", "template.dxf", "output.dxf"))
        old = ezdxf.new()
        model = old.modelspace()
        original_frame = model.add_lwpolyline([(0, 0), (200, 0), (200, 100), (0, 100)], close=True)
        model.add_circle((80, 50), 10)
        old.saveas(source)
        new = ezdxf.new()
        frame = new.modelspace().add_lwpolyline([(0, 0), (220, 0), (220, 110), (0, 110)], close=True)
        new.saveas(template)
        workdir = root / "work"
        titleblock.prepare(source, template, workdir)
        plan = root / "plan.json"
        plan.write_text(json.dumps({
            "manifest": str(workdir / "manifest.json"),
            "replacements": [{
                "layout": "Model",
                "old_handles": [original_frame.dxf.handle],
                "old_frame_only": True,
                "selection_evidence": "Synthetic frame and independent body circle",
                "template_layout": "Model",
                "template_handles": [frame.dxf.handle],
                "template_origin": [0, 0, 0],
                "insert": [0, 0, 0],
                "scale": 1,
                "rotation": 0,
                "alignment_evidence": "Both frames share their lower-left origin",
                "fields": [],
            }],
        }), encoding="utf-8")
        titleblock.apply(plan, output)
        result = ezdxf.readfile(output).modelspace()
        assert len(result.query("CIRCLE")) == 1
        assert len(result.query("INSERT")) == 1
        assert len(result.query("LWPOLYLINE")) == 0
        assert len(ezdxf.readfile(source).modelspace().query("LWPOLYLINE")) == 1
    print("Synthetic DXF replacement passed")


if __name__ == "__main__":
    main()
