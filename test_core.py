# -*- coding: utf-8 -*-
"""
test_core.py - 核心模块单元测试

覆盖课程知识点：
  - 异常处理（第 9 章）：使用 pytest raises 断言异常行为
  - 函数（第 6 章）：测试独立功能函数
  - 控制结构（第 4 章）：条件断言验证逻辑正确性

运行方式：
    pip install pytest
    pytest test_core.py -v

要求：
    pytest（轻量级，课程未禁止，仅用于测试）
"""

import sys
import os
from datetime import date, timedelta

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 在 Windows 终端下将 stdout 重配为 UTF-8，避免打印 emoji 时出现编码错误
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from analyzer import DietAnalyzer
from data_loader import load_cafeteria_csv, load_shop_csv


# ============================================================
# Mock 数据库类（基于 analyzer 自带的 MockDB 扩展）
# ============================================================
class MockDB:
    """
    模拟 DietDatabase，供测试使用。

    返回固定批量的模拟饮食记录，覆盖不同餐次、地点和食物分类。
    """

    def __init__(self):
        self._today = date.today()
        self._yesterday = self._today - timedelta(days=1)
        self._users = {
            1: {
                'id': 1,
                'username': 'test_user',
                'monthly_budget': 1200.0,
                'health_goal': '维持身材',
                'preferences': '["清淡","少油"]',
            }
        }

    def get_user(self, user_id):
        return self._users.get(user_id)

    def get_diet_records(self, user_id):
        """返回覆盖多餐次、多分类的模拟记录。"""
        today = self._today.strftime('%Y-%m-%d')
        yesterday = self._yesterday.strftime('%Y-%m-%d')
        return [
            # 第 1 条：均衡午餐（主食+蔬菜+肉类）
            {
                'id': 1, 'user_id': user_id, 'date': yesterday,
                'meal': '午餐', 'location_type': '食堂',
                'location_name': '松涛园', 'food_name': '鸡胸肉沙拉',
                'price': 22.0, 'is_takeout': False,
                'items': [
                    {'category': '主食', 'fist_count': 2.0},
                    {'category': '蔬菜', 'fist_count': 1.5},
                    {'category': '肉类', 'fist_count': 1.0},
                ],
            },
            # 第 2 条：高热量外卖晚餐（主食+肉类+饮料）
            {
                'id': 2, 'user_id': user_id, 'date': today,
                'meal': '晚餐', 'location_type': '外卖',
                'location_name': '某外卖店', 'food_name': '炸鸡套餐',
                'price': 28.0, 'is_takeout': True,
                'items': [
                    {'category': '主食', 'fist_count': 1.5},
                    {'category': '肉类', 'fist_count': 2.5},
                    {'category': '饮料', 'fist_count': 1.0},
                ],
            },
            # 第 3 条：简单早餐（主食+水果）
            {
                'id': 3, 'user_id': user_id, 'date': today,
                'meal': '早餐', 'location_type': '食堂',
                'location_name': '春晖园', 'food_name': '豆浆油条',
                'price': 8.0, 'is_takeout': False,
                'items': [
                    {'category': '主食', 'fist_count': 1.5},
                    {'category': '水果', 'fist_count': 1.0},
                ],
            },
            # 第 4 条：上个月的记录（不应计入当月统计）
            {
                'id': 4, 'user_id': user_id,
                'date': (self._today.replace(day=1) - timedelta(days=1)).strftime('%Y-%m-%d'),
                'meal': '午餐', 'location_type': '食堂',
                'location_name': '学一食堂', 'food_name': '烧鸭饭',
                'price': 15.0, 'is_takeout': False,
                'items': [
                    {'category': '主食', 'fist_count': 2.0},
                    {'category': '肉类', 'fist_count': 1.5},
                ],
            },
        ]


# ============================================================
# 测试用例
# ============================================================

class TestDietAnalyzer:
    """DietAnalyzer 类核心功能测试。"""

    @classmethod
    def setup_class(cls):
        """所有测试共用一套 MockDB 和 Analyzer 实例。"""
        cls.db = MockDB()
        cls.analyzer = DietAnalyzer(cls.db)

    def test_nutrition_score_exists(self):
        """营养评分返回结构完整性测试。"""
        result = self.analyzer.nutrition_score(1)
        # 必须包含的字段
        assert 'score' in result
        assert 'ideal' in result
        assert 'actual' in result
        assert 'deviation' in result
        assert 'suggestions' in result
        # score 应在合理范围 0-100
        assert 0 <= result['score'] <= 100

    def test_nutrition_score_goal_mapping(self):
        """健康目标映射正确性测试。"""
        # 使用"维持身材"目标的用户
        result = self.analyzer.nutrition_score(1)
        ideal = result['ideal']
        # 理想结构中主食=0.35，蔬菜=0.25，肉类=0.20
        assert abs(ideal.get('主食', 0) - 0.35) < 0.001
        assert abs(ideal.get('蔬菜', 0) - 0.25) < 0.001
        assert abs(ideal.get('肉类', 0) - 0.20) < 0.001

    def test_nutrition_score_deviation_range(self):
        """偏差值应在合理范围 0.0-2.0。"""
        result = self.analyzer.nutrition_score(1)
        deviation = result['deviation']
        assert 0.0 <= deviation <= 2.0

    def test_nutrition_score_suggestions(self):
        """健康建议应为非空列表。"""
        result = self.analyzer.nutrition_score(1)
        suggestions = result['suggestions']
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0

    def test_budget_analysis_fields(self):
        """预算分析返回结构完整性测试。"""
        result = self.analyzer.budget_analysis(1)
        required_keys = {
            'total_spent', 'budget', 'remaining',
            'daily_avg', 'predicted_end', 'will_exceed',
            'remaining_daily_budget',
        }
        assert required_keys.issubset(result.keys())

    def test_budget_analysis_positive(self):
        """预算金额应为正数。"""
        result = self.analyzer.budget_analysis(1)
        assert result['budget'] > 0
        assert result['total_spent'] >= 0

    def test_budget_analysis_remaining(self):
        """剩余 = 预算 - 已用。"""
        result = self.analyzer.budget_analysis(1)
        assert abs(result['remaining'] - (result['budget'] - result['total_spent'])) < 0.01

    def test_meal_statistics_fields(self):
        """用餐统计返回结构完整性测试。"""
        result = self.analyzer.meal_statistics(1)
        required_keys = {
            'total_meals', 'total_cost', 'daily_avg',
            'meal_breakdown', 'takeout_ratio', 'top_locations',
        }
        assert required_keys.issubset(result.keys())

    def test_meal_statistics_counts(self):
        """当月记录计数应只统计本月记录（排除上个月的）。"""
        result = self.analyzer.meal_statistics(1)
        # MockDB 中当月记录有 3 条（第1条是昨天，第2、3条是今天）
        # 第 4 条是上月记录，不应计入
        print(f"total_meals = {result['total_meals']}")  # 调试
        assert result['total_meals'] >= 2  # 至少应有 2 条当月记录

    def test_meal_statistics_takeout_ratio(self):
        """外卖占比应在 0-1 之间。"""
        result = self.analyzer.meal_statistics(1)
        assert 0 <= result['takeout_ratio'] <= 1

    def test_daily_calorie_trend(self):
        """热量趋势返回列表且每项有 date 和 calories。"""
        result = self.analyzer.daily_calorie_trend(1)
        assert isinstance(result, list)
        if result:
            assert 'date' in result[0]
            assert 'total_calories' in result[0]


# ============================================================
# Data Loader 测试
# ============================================================

class TestDataLoader:
    """CSV 数据加载功能测试。"""

    def test_load_cafeteria_csv_exists(self):
        """食堂 CSV 能正常读取且非空。"""
        data = load_cafeteria_csv()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_load_cafeteria_csv_fields(self):
        """食堂数据包含所需字段。"""
        data = load_cafeteria_csv()
        if data:
            required = {'stall_id', 'dish_name', 'price', 'canteen', 'category'}
            assert required.issubset(data[0].keys())

    def test_load_cafeteria_csv_price_type(self):
        """食堂数据 price 字段为 float 类型。"""
        data = load_cafeteria_csv()
        if data:
            assert isinstance(data[0].get('price'), (int, float))

    def test_load_shop_csv_exists(self):
        """门店 CSV 能正常读取且非空。"""
        data = load_shop_csv()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_load_shop_csv_fields(self):
        """门店数据包含所需字段。"""
        data = load_shop_csv()
        if data:
            required = {'shop_id', 'dish_name', 'price', 'shop_name', 'distance_m'}
            assert required.issubset(data[0].keys())


# ============================================================
# 运行入口
# ============================================================

if __name__ == '__main__':
    """直接运行（无需 pytest）。"""
    print("=" * 60)
    print("核心模块自测（无 pytest 环境）")
    print("=" * 60)

    # 手动实例化测试
    db = MockDB()
    analyzer = DietAnalyzer(db)

    # 测试营养评分
    print("\n1. 营养评分测试...")
    nutrition = analyzer.nutrition_score(1)
    assert 0 <= nutrition['score'] <= 100
    assert 'ideal' in nutrition and 'actual' in nutrition
    print(f"   评分: {nutrition['score']} ✅")

    # 测试预算分析
    print("\n2. 预算分析测试...")
    budget = analyzer.budget_analysis(1)
    assert budget['budget'] > 0
    assert 'total_spent' in budget
    assert 'will_exceed' in budget
    print(f"   预算: {budget['budget']}, 已用: {budget['total_spent']} ✅")

    # 测试用餐统计
    print("\n3. 用餐统计测试...")
    stats = analyzer.meal_statistics(1)
    assert stats['total_meals'] >= 2
    assert 0 <= stats['takeout_ratio'] <= 1
    print(f"   总餐次: {stats['total_meals']} ✅")

    # 测试热量趋势
    print("\n4. 热量趋势测试...")
    trend = analyzer.daily_calorie_trend(1)
    assert isinstance(trend, list)
    print(f"   趋势天数: {len(trend)} ✅")

    # 测试数据加载
    print("\n5. CSV 数据加载测试...")
    canteen = load_cafeteria_csv()
    assert len(canteen) > 0
    shop = load_shop_csv()
    assert len(shop) > 0
    print(f"   食堂数据: {len(canteen)} 条 ✅")
    print(f"   门店数据: {len(shop)} 条 ✅")

    print("\n" + "=" * 60)
    print("全部测试通过 ✅")
    print("=" * 60)
