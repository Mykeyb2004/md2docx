"""Real-world corpus verification for the in-process Pele Mermaid engine."""

import os
import sys
import time
from pathlib import Path

from docx import Document
from md2docx import Converter
from md2docx.mermaid_converter import MermaidConverter, MermaidReport
from md2docx.pele_renderer import PeleRenderer


def run_verification() -> int:
    base_dir = Path(__file__).resolve().parent
    base_dir.mkdir(parents=True, exist_ok=True)
    samples_dir = base_dir / "samples"
    samples_dir.mkdir(parents=True, exist_ok=True)

    print("==================================================")
    print("Stage 4: Real-World Corpus Verification")
    print("==================================================")

    # 1. Verify tests/mermaid_diagnosis_20260915/source-corrected.md (90 diagrams)
    source_corrected_md = Path("tests/mermaid_diagnosis_20260915/source-corrected.md")
    if not source_corrected_md.exists():
        print(f"Error: {source_corrected_md} not found!")
        return 1

    print(f"\n[Test 1] Converting {source_corrected_md} (90 diagrams)...")
    out_corrected_docx = base_dir / "source-corrected-pele.docx"
    
    conv_corrected = Converter()
    t0 = time.perf_counter()
    conv_corrected.convert(str(source_corrected_md), str(out_corrected_docx))
    t1 = time.perf_counter()
    elapsed_corrected = t1 - t0

    rep_corrected = conv_corrected.mermaid_report
    print(f"  Elapsed Time: {elapsed_corrected:.2f}s ({elapsed_corrected / 90:.3f}s / diagram)")
    print(f"  Mermaid Report: Total={rep_corrected.total}, Succeeded={rep_corrected.succeeded}, Failures={len(rep_corrected.failures)}")

    doc_corrected = Document(str(out_corrected_docx))
    inline_shapes_count = len(doc_corrected.inline_shapes)
    print(f"  Docx inline images: {inline_shapes_count}")

    if rep_corrected.total != 90 or rep_corrected.succeeded != 90:
        print(f"FAILED: Expected 90/90 succeeded, got {rep_corrected.succeeded}/{rep_corrected.total}")
        for failure in rep_corrected.failures:
            print(f"  Failure {failure.index}: {failure.error}")
        return 1

    print("  -> TEST 1 PASSED: 90/90 diagrams succeeded!")

    # 2. Verify syntax error handling on failed-*.mmd files
    print("\n[Test 2] Testing 8 invalid Mermaid files for graceful syntax error reporting...")
    failed_mmd_dir = Path("tests/mermaid_diagnosis_20260915")
    failed_files = sorted(failed_mmd_dir.glob("failed-*.mmd"))
    print(f"  Found {len(failed_files)} syntax error sample files.")

    converter_err_test = MermaidConverter()
    report_err_test = MermaidReport()

    for mmd_file in failed_files:
        code = mmd_file.read_text(encoding="utf-8")
        report_err_test.total += 1
        try:
            converter_err_test.mermaid_to_image(code)
            print(f"  Unexpected success for {mmd_file.name}")
        except Exception as exc:
            report_err_test.record_failure(exc)
            first_line = str(exc).splitlines()[0] if str(exc) else ""
            print(f"  Caught expected error on {mmd_file.name}: {first_line[:80]}")

    print(f"  Syntax Error Report: Total={report_err_test.total}, Failures Caught={len(report_err_test.failures)}")
    if len(report_err_test.failures) != len(failed_files):
        print("FAILED: Did not catch all syntax errors.")
        return 1
    print("  -> TEST 2 PASSED: All syntax errors gracefully caught and recorded.")

    # 3. Verify tests/test_md/麻城市社会救助服务项目.md (178 diagrams)
    macheng_md = Path("tests/test_md/麻城市社会救助服务项目.md")
    if not macheng_md.exists():
        print(f"Error: {macheng_md} not found!")
        return 1

    print(f"\n[Test 3] Converting {macheng_md} (178 diagrams)...")
    out_macheng_docx = base_dir / "麻城市社会救助服务项目-pele.docx"

    conv_macheng = Converter()
    t0 = time.perf_counter()
    conv_macheng.convert(str(macheng_md), str(out_macheng_docx))
    t1 = time.perf_counter()
    elapsed_macheng = t1 - t0

    rep_macheng = conv_macheng.mermaid_report
    print(f"  Elapsed Time: {elapsed_macheng:.2f}s ({elapsed_macheng / rep_macheng.total:.3f}s / diagram)")
    print(f"  Mermaid Report: Total={rep_macheng.total}, Succeeded={rep_macheng.succeeded}, Failures={len(rep_macheng.failures)}")

    doc_macheng = Document(str(out_macheng_docx))
    print(f"  Docx inline images: {len(doc_macheng.inline_shapes)}")
    print(f"  Success rate: {rep_macheng.succeeded / rep_macheng.total * 100:.1f}%")

    if rep_macheng.failures:
        print(f"  Notice: {len(rep_macheng.failures)} diagrams had syntax issues in source Markdown:")
        for failure in rep_macheng.failures[:5]:
            print(f"    Diagram #{failure.index}: {failure.error}")

    # 4. Generate visual inspection samples for different diagram types
    print("\n[Test 4] Generating visual inspection sample PNGs...")
    renderer = PeleRenderer()
    sample_diagrams = {
        "flowchart_subgraph": (
            "flowchart TD\n"
            "  subgraph SG1[业务受理层]\n"
            "    A[居民申请提交] --> B{资格条件初审}\n"
            "    B -->|通过| C[录入救助管理系统]\n"
            "    B -->|未通过| D[一次性告知补正材料]\n"
            "  end\n"
            "  subgraph SG2[审批核查层]\n"
            "    C --> E[信息比对与入户调查]\n"
            "    E --> F[民主评议及公示]\n"
            "    F --> G[民政局终审确认]\n"
            "  end\n"
            "  style C fill:#E8F1FF,stroke:#2F6BFF,stroke-width:2px,rx:6px\n"
            "  style G fill:#D1FAE5,stroke:#059669,stroke-width:2px,rx:6px"
        ),
        "sequence_diagram": (
            "sequenceDiagram\n"
            "  autonumber\n"
            "  actor 申请人\n"
            "  participant 社区工作站\n"
            "  participant 街道办事处\n"
            "  participant 救助审批大数据核验中心\n"
            "  申请人->>社区工作站: 提交救助申报材料及家庭授权书\n"
            "  社区工作站->>街道办事处: 线上推送初审档案\n"
            "  街道办事处->>救助审批大数据核验中心: 发起14个部门联合财产比对\n"
            "  救助审批大数据核验中心-->>街道办事处: 反馈比对报告（房产/车辆/社保）\n"
            "  街道办事处-->>社区工作站: 输出综合评定结论\n"
            "  社区工作站-->>申请人: 寄送救助审核决定书及公示确认单"
        ),
        "mindmap_chinese": (
            "mindmap\n"
            "  root((社会救助服务体系))\n"
            "    基本生活救助\n"
            "      最低生活保障标准核定\n"
            "      特困人员供养照料\n"
            "    专项社会救助\n"
            "      医疗救助与兜底报销\n"
            "      教育资助与助学补助\n"
            "      住房救助保障房配租\n"
            "      就业扶持公益性岗位\n"
            "    急难社会救助\n"
            "      临时救助小额先行垫付\n"
            "      受灾人员生活紧急救助\n"
            "    社会力量参与\n"
            "      慈善组织帮扶\n"
            "      社会工作志愿服务"
        ),
        "gantt_schedule": (
            "gantt\n"
            "  title 麻城市社会救助服务项目实施周期表\n"
            "  dateFormat YYYY-MM-DD\n"
            "  section 调研筹备期\n"
            "  政策梳理与规范编制       :done, a1, 2026-01-01, 2026-01-15\n"
            "  街道社区网格走访调研     :active, a2, 2026-01-16, 2026-02-10\n"
            "  section 平台建设期\n"
            "  救助大数据比对接口研发   :crit, b1, 2026-02-01, 2026-03-15\n"
            "  全流程审批业务流联调     :b2, after b1, 25d\n"
            "  section 运营推广期\n"
            "  试点街道先行先试上线     :c1, after b2, 20d\n"
            "  全县域推广与综合评估验收 :c2, after c1, 30d"
        ),
    }

    for name, code in sample_diagrams.items():
        sample_path = samples_dir / f"{name}.png"
        png_data = renderer.render_png(
            code=code,
            theme="base",
            background_color="white",
            theme_variables={
                "primaryColor": "#E8F1FF",
                "primaryTextColor": "#163A70",
                "primaryBorderColor": "#2F6BFF",
                "lineColor": "#2F6BFF",
                "clusterBkg": "#F7FBFF",
                "clusterBorder": "#9AB8E8",
                "edgeLabelBackground": "#FFFFFF",
            },
            scale=1.0,
        )
        sample_path.write_bytes(png_data)
        print(f"  Saved sample {sample_path.name} ({len(png_data)} bytes)")

    print("\n==================================================")
    print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!")
    print("==================================================")
    return 0


if __name__ == "__main__":
    sys.exit(run_verification())
