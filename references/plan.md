# 计划文件与坐标

先运行 prepare，读取 manifest.json 和两个 inventory.json。plan 中 manifest 使用绝对路径。source/template 的 sha256 及 snapshot_sha256 必须保持不变。

示意（句柄、文字和坐标须替换，不能直接用于真实图纸）：

```json
{
  "manifest": "/当前任务/work/frame-job/manifest.json",
  "dwg_version": "R2018",
  "replacements": [{
    "layout": "Model",
    "old_handles": ["35"],
    "old_frame_only": true,
    "selection_evidence": "预览和实体清单确认 35 仅为图框；正文是其他实体",
    "template_layout": "Model",
    "template_handles": ["48"],
    "template_origin": [0, 0, 0],
    "insert": [100, 200, 0],
    "scale": 1,
    "rotation": 0,
    "alignment_evidence": "双方单位为 mm，以左下框角对齐并以右下、左上角核对",
    "fields": [{
      "name": "图名",
      "source_path": ["35", "37"],
      "expected": "道路平面图",
      "evidence": "旧框 TITLE 属性及预览一致",
      "target": {"path": ["48"], "tag": "TITLE"}
    }]
  }]
}
```

- old_handles：指定布局的顶层实体。散线散字需完整枚举，不能仅选择文本而遗留边框。
- template_handles：指定模板布局中要导入的顶层实体，不自动选择整张模板。
- source_path：inventory 中嵌套文字的真实路径，首项必须是 old_handles 之一；脚本检查 expected 完全匹配。
- target.path：模板选区中实体路径。带 tag 时目标必须是 INSERT，已有属性会更新，缺属性但有对应 ATTDEF 时会按定义生成；无定义则拒绝。
- 无 tag 时目标须为 TEXT/MTEXT/ATTRIB。不自动把普通文字转成属性；检查新框对齐与字体后决定是否需要人工布局。
- literal 可代替 source_path/expected，表示用户给出的新值或已人工核实的轮廓文字。evidence 必须说明来源，不能用猜测冒充核实。
- template_origin：模板原始布局坐标中的基点；insert：目标布局插入点。scale 为大于零的统一比例，rotation 为角度（度）。该变换不会自动换算单位或视口比例。
- old_frame_only 和证据字段是可审阅的记录，不是通用的“跳过检查”开关。无法证明整块只包含框时不得填 true。
- 当前脚本不直接支持删除 XREF/MINSERT 或混合总块。复杂对象需另写最小修改，再重新生成快照和清单。
- MTEXT 值按现有字体和格式承载，迁移后必须视觉核对。多行/格式化文本可能需要针对实际模板适配。

共享定义中的字段（包括嵌套 INSERT 的属性）若会影响其他实例，脚本拒绝。应先隔离该模板实例的块定义，再重新 prepare；不能删掉共享检查。模板图像、底图、代理、ACAD_TABLE、外参或阵列块同样需原生 CAD 专门导入，当前脚本不自动执行。

顶层可选 `protected_titles` 是完整标题字符串列表，默认 `[]`。当目标 TEXT/MTEXT/ATTRIB 的原文字属于此列表时，只允许迁移相同值；具体图名应绑定独立占位实体。该保护不替代 `quality_gate.text_bindings` 的导出后位置检查。

`manual_review.number_lines` 和 `manual_review.extra_old_frame_lines` 属于定制流程的复核约定，分别记录图号分行和额外旧框线选择；`titleblock.py apply` 不读取它们，不会据此自动换行或删除实体。需由定制流程显式执行并验证。
