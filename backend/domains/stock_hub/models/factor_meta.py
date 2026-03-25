"""因子元数据模型"""
from typing import Optional, List, Dict
from pydantic import BaseModel


class FactorMeta(BaseModel):
    """因子元数据"""
    name: str                                    # 因子名称（文件名去.py）
    category: str                                # 分类: H财务 / 技术 / 截面
    library: str                                 # 所属库: 因子库 / 截面因子库
    has_add_factor: bool = True                  # 是否有add_factor函数
    fin_cols: List[str] = []                     # 财务字段依赖
    ov_cols: List[str] = []                      # 其他字段依赖
    extra_data: List[str] = []                   # 额外数据依赖
    description: str = ""                        # FA_INTRO中的因子说明
    example_select: Optional[str] = None         # 选股因子案例
    example_filter: Optional[str] = None         # 过滤因子案例
    file_path: str = ""                          # 文件绝对路径


class FactorListResponse(BaseModel):
    """因子列表响应"""
    factors: List[FactorMeta]
    total: int
    categories: Dict[str, int] = {}             # 各分类数量
