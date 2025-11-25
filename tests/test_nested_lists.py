#!/usr/bin/env python3
"""测试嵌套列表的渲染功能"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from md2docx.converter import Converter

def test_nested_lists():
    """测试嵌套列表能否正确转换"""
    
    # 创建测试 markdown 内容
    test_md = """# 嵌套列表测试

## 有序列表包含无序子列表

1.  **用户需求与替代性调查（N=600样本）：**
    *   **对象：** 18岁以上市民及游客。
    *   **重点问卷设计：**
        *   "如果没有共享电单车，您会选择什么交通工具？"（测试替代率）
        *   "您选择共享电单车是否因为打不到车/公交太慢？"（测试溢出需求）
2.  **存量车辆周转率监测（N=200车次/天，连续3天）：**
    *   在主要商圈、公交站点、居住区选取样本车辆，通过现场观测或后台数据协同（如具备条件），记录单车单日被使用的次数。
3.  **竞品交通方式关键指标采集：**
    *   采集当前公交车发车间隔、出租车高峰期空驶率数据，作为修正系数的输入变量。

## 无序列表包含有序子列表

*   **主要功能：**
    1.  数据采集
    2.  数据分析
    3.  报告生成
*   **次要功能：**
    1.  数据导出
    2.  图表生成

## 三层嵌套

1.  **第一层**
    *   第二层项目1
        1.  第三层项目1
        2.  第三层项目2
    *   第二层项目2
2.  **第一层项目2**
"""
    
    # 保存测试文件
    test_md_path = 'test_nested_lists.md'
    with open(test_md_path, 'w', encoding='utf-8') as f:
        f.write(test_md)
    
    # 转换为 docx
    output_path = 'test_nested_lists_output.docx'
    converter = Converter()
    
    try:
        converter.convert(test_md_path, output_path)
        print(f"✓ 测试成功！输出文件：{output_path}")
        print("请打开输出文件检查以下内容：")
        print("1. '用户需求与替代性调查' 的标题是否显示")
        print("2. 其下的子项（对象、重点问卷设计）是否显示") 
        print("3. '重点问卷设计' 下的两个更深层级的子项是否显示")
        print("4. 所有嵌套层级的缩进是否正确")
        return True
    except Exception as e:
        print(f"✗ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理测试文件
        if os.path.exists(test_md_path):
            os.remove(test_md_path)

if __name__ == '__main__':
    success = test_nested_lists()
    sys.exit(0 if success else 1)
