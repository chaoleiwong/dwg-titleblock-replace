# GitHub 调研与本机方案（2026-10-22）

本文的既往读取测试、本机环境及下述测试覆盖表述仅为历史验证背景，非本包附带的测试证据；本包未附带这些测试的输入、输出或报告，不能据此认定当前环境或具体图纸已通过验证。

## 采用的组件

1. [mozman/ezdxf](https://github.com/mozman/ezdxf)，MIT。官方 xref.Loader 可将模型空间/图纸空间中的指定实体连同所需块、图层、字体等资源导入另一张图；XREF_PREFIX 可避免重名资源污染原图。官方说明明确不支持所有代理或 ACAD_TABLE 等对象。运行时使用已安装的 ezdxf>=1.4，不自动下载主分支。
2. ODA File Converter，作为 DWG↔DXF 桥接。ODA 是官方下载软件，不是 GitHub 开源项目，不把其专有二进制当第三方开源源代码分发。
3. [monozukuri-ai/ezdwf](https://github.com/monozukuri-ai/ezdwf)，MIT，可选依赖。仅为另有原始 DWF/DWFx 时的实验只读诊断。其 README 明确为 pre-alpha、二维范围，可能截断未知 W2D opcode，不是完整 DWF→DWG 恢复器。用上游测试样本完成读取测试，诊断报告保留字体降级警告。

上述 GitHub 仓库的 README、许可证、ezdxf xref 文档/源代码及官方 DWG 示例已下载至 upstream/。每个下载地址与提交号记录在 [upstream/sources.json](upstream/sources.json)。这些源代码用于调研与 API 核对；实际执行调用本机已安装且测试过的库，不自动执行 GitHub 第三方 skill。

## 还检查的候选及未采用原因

- [abueno78/dwg-dani](https://github.com/abueno78/dwg-dani)：也采用 ezdxf+ODA 的 skill 思路，可佐证桥接路线，但不直接解决本用户的字段迁移、散线选框和正文保留校验；未作为运行依赖。
- [MatheusMeM/dwg-interpreter-claude-skill](https://github.com/MatheusMeM/dwg-interpreter-claude-skill)：偏 Windows/LibreDWG 读取与清点。当前默认采用 ODA，其他转换路径需单独验证。
- [xiaodongliang/ViewData-DWG-TitleBlock-Signature](https://github.com/xiaodongliang/ViewData-DWG-TitleBlock-Signature)：云端 Autodesk 示例，且旧示例按 AM_BOR 图层识别，不适合未知图层和本地保密图纸处理。
- [monozukuri-ai/cad2d-ir](https://github.com/monozukuri-ai/cad2d-ir)：统一二维表示/导出用于转换，但当前目标是保留已有 DWG 的正文、布局与资源，不为换框将整图降成中间几何模型；未安装。
- [kveretennicov/dwf-toolkit](https://github.com/kveretennicov/dwf-toolkit)：旧 C++/Visual Studio 构建资料；不能据此声称 macOS 可无损逆向原 CAD，未安装。
- [zheimr/DWG-to-DXF-Converter](https://github.com/zheimr/DWG-to-DXF-Converter)：包装商业 Aspose.CAD，不替代已配置 ODA，也不额外引入评估水印或许可证依赖。

## 运行环境

安装 ezdxf>=1.4 和 ODA File Converter；可选安装 ezdwf 进行实验只读诊断。建议用原生 CAD 复核。不上传图纸到在线转换站，不因读取失败静默切换云端服务。

## 验证范围与限制

合成 DXF 和实际经 ODA 转成的 DWG 均覆盖：共享旧图框只替换一个实例、模型/布局、散线散字图框、正文位于框内且与框共层、同名资源冲突、中文属性迁移、统一缩放旋转、原值不匹配拒绝、哈希变更拒绝。还独立检查字段目标冲突、共享嵌套定义串改和块内部校验。

模拟 DWF 转换的散线测试不是用户真实 DWF 转换器全覆盖测试。未提供真实原图/新框时，不能承诺某一实际图纸一定能自动识别图框或无损替换。用户发来原图、模板及字段要求后，以其实际文件清点和视觉核对。
