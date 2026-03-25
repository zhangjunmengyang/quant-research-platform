"""因子查询服务最小测试"""
import sys
import os

# 确保可以import domains
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from domains.stock_hub.services.stock_factor_service import StockFactorService


def test_factor_service():
    print("=" * 60)
    print("Stock Hub - 因子查询服务测试")
    print("=" * 60)

    service = StockFactorService()

    # 测试1: 分类统计
    print("\n[测试1] 因子分类统计...")
    categories = service.get_categories()
    total = sum(categories.values())
    print(f"  总计: {total} 个因子")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count} 个")

    assert total > 1000, f"因子总数应>1000，实际: {total}"
    print("  ✓ 通过")

    # 测试2: 列表查询
    print("\n[测试2] 因子列表查询...")
    factors, count = service.list_factors(page=1, page_size=5)
    print(f"  返回 {len(factors)} 个因子（共 {count} 个）")
    for f in factors:
        desc = f.description[:50] if f.description else ""
        print(f"  - {f.name} [{f.category}] {desc}")
    assert len(factors) == 5
    assert count > 1000
    print("  ✓ 通过")

    # 测试3: 按分类筛选
    print("\n[测试3] 按分类筛选 H财务...")
    h_factors, h_count = service.list_factors(category="H财务", page_size=3)
    print(f"  H财务因子: {h_count} 个")
    for f in h_factors:
        print(f"  - {f.name}: fin_cols={f.fin_cols[:2]}...")
        assert f.name.startswith("H"), f"H财务因子应以H开头: {f.name}"
    print("  ✓ 通过")

    # 测试4: 关键词搜索
    print("\n[测试4] 关键词搜索 '市盈率'...")
    results, r_count = service.list_factors(search="市盈率")
    print(f"  搜索到 {r_count} 个因子")
    for f in results[:3]:
        print(f"  - {f.name}")
    assert r_count > 0
    print("  ✓ 通过")

    # 测试5: 单因子详情
    print("\n[测试5] 获取因子详情 H估值_市盈率TTM...")
    detail = service.get_factor("H估值_市盈率TTM")
    assert detail is not None
    print(f"  名称: {detail.name}")
    print(f"  分类: {detail.category}")
    print(f"  fin_cols: {detail.fin_cols}")
    desc = detail.description[:100] if detail.description else "(无)"
    print(f"  描述: {desc}...")
    assert detail.has_add_factor
    assert len(detail.fin_cols) > 0
    print("  ✓ 通过")

    # 测试6: 获取源代码
    print("\n[测试6] 获取因子源代码...")
    code = service.get_factor_code("H估值_市盈率TTM")
    assert code is not None
    assert "add_factor" in code
    print(f"  代码长度: {len(code)} 字符")
    print("  ✓ 通过")

    # 测试7: 截面因子
    print("\n[测试7] 截面因子查询...")
    sec_factors, sec_count = service.list_factors(category="截面", page_size=3)
    print(f"  截面因子: {sec_count} 个")
    for f in sec_factors:
        print(f"  - {f.name} [{f.library}]")
    assert sec_count > 100
    print("  ✓ 通过")

    print("\n" + "=" * 60)
    cat_str = ", ".join(f"{k}:{v}" for k, v in categories.items())
    print(f"全部测试通过! 共 {total} 个因子 ({cat_str})")
    print("=" * 60)


if __name__ == "__main__":
    test_factor_service()
