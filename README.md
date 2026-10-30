# 通用 DWG 图框提取与替换

从 DWG/DXF 旧图框提取字段，将用户提供的新模板导入并替换选定图框，保留正文、其他图框与布局。通过固定快照、实体句柄、输入哈希和回读检查控制修改范围，另存结果，不覆盖原件。

## 流程说明

分阶段操作顺序、决策点与交付物见 [`docs/workflow.md`](docs/workflow.md)。完整规则与禁令仍以 [`SKILL.md`](SKILL.md) 为准。

## 依赖

- Python>=3.11（脚本使用 `hashlib.file_digest`），并安装 ezdxf>=1.4，以所选 Python `$PY` 表示：`"$PY" -m pip install -r requirements.txt`。
- DWG 读写需要另行安装 ODA File Converter。可设置 `ODA_FILE_CONVERTER` 为可执行文件路径；否则依次尝试 PATH 中的 `ODAFileConverter` 和 macOS 标准应用位置。DXF 直接读写无需 ODA。
- `scripts/inspect_dwf.py` 的 DWF/DWFx 实验只读诊断需可选依赖 ezdwf；预览渲染需 matplotlib。可用 `"$PY" -m pip install -r requirements-optional.txt` 安装这两项可选依赖。

## 目录

- `SKILL.md`：操作流程与质量要求。
- `scripts/`：图框提取替换、转换、识别与质量门脚本。
- `references/`：计划格式、质量门及复核说明。
- `references/upstream/`：上游研究材料及其原有许可证。
- `agents/`：技能界面配置。

## 基本用法

在技能目录执行，先将 `PY` 设置为所选 Python 解释器：

```sh
PY=python3
"$PY" scripts/titleblock.py prepare 原图.dwg 新框.dwg --workdir work/frame-job
"$PY" scripts/titleblock.py render work/frame-job/source.snapshot.dxf --layout Model --output work/source.png
# 按 references/plan.md、实体清单和预览编写 plan.json
"$PY" scripts/titleblock.py apply plan.json --output outputs/更新图框.dwg
"$PY" scripts/native_vertical_company.py 原图.dwg --company-text "待匹配单位文字" --output work/candidates.json
"$PY" scripts/triangle_frames.py 原图.dwg --marker-text "待匹配标记" --output work/triangles.json
```

`plan.json` 顶层 `protected_titles` 为禁止改写的完整标题字符串列表，默认 `[]`。只读单位识别的 `--company-text` 为子串匹配，默认空，因此默认不产生单位候选。`--marker-text` 也为子串匹配，可重复传入以配置多个标记（匹配任一非空标记即可），默认空列表，不产生候选。

定制识别脚本可设置文档对象的 `_titleblock_company_text`（单位文字，默认空）、`_titleblock_marker_texts`（标记字符串列表，默认空）。三角形边框识别仍要求原有几何证据，不配置标记时不产生候选。人工复核开关、边界计划、首选格线及缓存统一采用 `_titleblock_` 前缀，详见脚本；这些内部设置不由 `titleblock.py apply` 自动读取。

## 限制

不会自动恢复轮廓文字语义，不支持任意混合总块、代理对象、外参或行业对象的无损编辑。几何识别只覆盖相应结构，候选必须结合实际图纸复核。字段来源、删除范围和对齐控制点需逐图确认；机械质量门只检查显式配置的对象。建议用原生 CAD 检查字体、打印范围及复杂对象，交付时列出未核实项。

本项目未指定新的许可证；上游材料沿用各自附带的许可证。
