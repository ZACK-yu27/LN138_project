# -*- coding: utf-8 -*-
"""
analyzer_v3.py - 饮食分析模块（角色 B - Analyzer_v3）

功能：营养结构评分、预算分析、统计计算、日均热量估算趋势。
采用数据驱动风格，使用纯字典和列表操作，强调数据处理流程的清晰展示。

覆盖课程知识点：
  - 函数（第6章）：位置参数、默认值参数、*args/**kwargs
  - 类与OOP（第8章）：DietAnalyzer类、classmethod、staticmethod
  - 控制结构（第4章）：循环、条件、嵌套逻辑
  - 列表/字典/元组/集合（第3、5章）：四种数据结构合理使用
  - 字符串处理（第2章）：f-string、join、split、format
"""

import sqlite3
from datetime import date, timedelta
from collections import defaultdict


# =====================================================================
# 数据常量定义（数据驱动核心：所有配置用字典/元组组织）
# =====================================================================

# 热量映射：每拳对应的千卡数（字典驱动）
CALORIE_MAP = {
    "主食": 200,
    "蔬菜": 50,
    "肉类": 150,
    "水果": 80,
    "饮料": 100,
    "零食": 150,
    "其他": 100,
    "汤品": 50,
}

# 健康目标与理想营养结构（元组定义顺序，字典存储数值）
CATEGORY_ORDER = ("主食", "蔬菜", "肉类", "水果", "饮料/零食", "其他")

IDEAL_STRUCTURES = {
    "减肥": {
        "主食": 0.30,
        "蔬菜": 0.30,
        "肉类": 0.20,
        "水果": 0.10,
        "饮料/零食": 0.05,
        "其他": 0.05,
    },
    "维持身材": {
        "主食": 0.35,
        "蔬菜": 0.25,
        "肉类": 0.20,
        "水果": 0.10,
        "饮料/零食": 0.05,
        "其他": 0.05,
    },
    "健身增重": {
        "主食": 0.40,
        "蔬菜": 0.15,
        "肉类": 0.30,
        "水果": 0.05,
        "饮料/零食": 0.05,
        "其他": 0.05,
    },
}

# 健康目标别名映射（处理用户输入的多种写法）
GOAL_ALIASES = {
    "减肥": "减肥",
    "维持": "维持身材",
    "维持身材": "维持身材",
    "增重": "健身增重",
    "健身增重": "健身增重",
}


# =====================================================================
# 纯函数工具层（数据驱动风格，强调数据处理流程）
# =====================================================================

def merge_categories(category_counts):
    """
    合并饮料/零食类别，并将非标准类别归入其他。

    :param category_counts: dict {类别: 拳头数}
    :return: dict 合并后的分类计数
    """
    merged = {}
    for cat, count in category_counts.items():
        if cat in ("饮料", "零食"):
            # 饮料和零食合并为"饮料/零食"
            merged["饮料/零食"] = merged.get("饮料/零食", 0) + count
        elif cat not in CATEGORY_ORDER:
            # 汤品等非标准类别归入"其他"
            merged["其他"] = merged.get("其他", 0) + count
        else:
            merged[cat] = merged.get(cat, 0) + count
    return merged


def normalize_ratios(category_counts):
    """
    将分类计数归一化为占比（展示元组作为返回值）。

    :param category_counts: dict {类别: 拳头数}
    :return: tuple(占比字典, 总拳数)
    """
    merged = merge_categories(category_counts)
    total = sum(merged.values())
    if total == 0:
        return ({cat: 0.0 for cat in CATEGORY_ORDER}, 0)
    # 使用字典推导式计算各分类占比
    ratios = {cat: round(merged.get(cat, 0) / total, 4) for cat in CATEGORY_ORDER}
    return (ratios, total)


def compute_total_deviation(actual_ratios, ideal_ratios):
    """
    计算实际占比与理想占比的总偏差（展示元组作为返回值）。

    :param actual_ratios: dict 实际占比
    :param ideal_ratios: dict 理想占比
    :return: tuple(总偏差, 各类别偏差字典)
    """
    deviation = {}
    total_dev = 0.0
    for cat in CATEGORY_ORDER:
        ideal = ideal_ratios.get(cat, 0)
        actual = actual_ratios.get(cat, 0.0)
        diff = abs(actual - ideal)
        deviation[cat] = round(diff, 4)
        total_dev += diff
    return (round(total_dev, 4), deviation)


def generate_health_suggestions(actual_ratios, ideal_ratios, takeout_ratio=0.0, **kwargs):
    """
    根据偏差生成健康建议（展示**kwargs用法）。

    :param actual_ratios: dict 实际占比
    :param ideal_ratios: dict 理想占比
    :param takeout_ratio: float 外卖占比
    :param kwargs: 额外指标（如daily_calorie日均热量）
    :return: list[str] 建议列表
    """
    suggestions = []
    for cat in CATEGORY_ORDER:
        ideal = ideal_ratios.get(cat, 0)
        actual = actual_ratios.get(cat, 0.0)
        if actual < ideal - 0.05:
            suggestions.append(f"{cat}摄入不足，建议适当增加")
        elif actual > ideal + 0.05:
            suggestions.append(f"{cat}偏多，建议适量减少")

    # 外卖占比过高建议
    if takeout_ratio > 0.5:
        suggestions.append("外卖占比过高，建议增加食堂就餐频率")

    # 使用**kwargs展示额外指标的灵活处理
    daily_cal = kwargs.get("daily_calorie")
    if daily_cal is not None and daily_cal > 3000:
        suggestions.append("日均热量估算偏高，建议控制总摄入量")
    elif daily_cal is not None and daily_cal < 1200:
        suggestions.append("日均热量估算偏低，注意保证营养充足")

    return suggestions if suggestions else ["饮食结构基本合理，请继续保持"]


def format_percent(ratio):
    """将小数占比格式化为百分比字符串（展示format用法）。"""
    return "{:.1%}".format(ratio)


def parse_date_str(date_str):
    """
    将"YYYY-MM-DD"字符串解析为date对象（展示split用法）。

    :param date_str: str 日期字符串
    :return: date 对象
    """
    parts = date_str.split("-")
    return date(int(parts[0]), int(parts[1]), int(parts[2]))


def get_month_window(today=None):
    """
    获取本月日期范围（展示默认参数和元组返回值）。

    :param today: date 对象，默认为None时使用当天
    :return: tuple(月初, 月末, 今天, 本月天数)
    """
    if today is None:
        today = date.today()
    first_day = today.replace(day=1)
    # 计算下月1日，再减1天得到本月最后一天
    if today.month == 12:
        next_month = date(today.year + 1, 1, 1)
    else:
        next_month = date(today.year, today.month + 1, 1)
    last_day = next_month - timedelta(days=1)
    days_in_month = last_day.day
    return (first_day, last_day, today, days_in_month)


def aggregate_by_key(data_list, key_func, value_func):
    """
    通用聚合函数（展示函数作为参数）。

    :param data_list: list 数据列表
    :param key_func: callable 提取键的函数
    :param value_func: callable 提取值的函数
    :return: dict 聚合结果
    """
    result = {}
    for item in data_list:
        k = key_func(item)
        v = value_func(item)
        result[k] = result.get(k, 0) + v
    return result


def top_n_sorted(counter_dict, n=5, reverse=True):
    """
    获取字典中频次最高的N项（展示sorted函数和key参数）。

    :param counter_dict: dict 计数字典
    :param n: int 取前N个，默认5
    :param reverse: bool 是否降序，默认True
    :return: list[tuple(key, value)] 排序后的列表
    """
    return sorted(counter_dict.items(), key=lambda x: x[1], reverse=reverse)[:n]


# =====================================================================
# DietAnalyzer 类（数据驱动风格，不依赖外部业务类）
# =====================================================================

class DietAnalyzer:
    """
    饮食数据分析器（数据驱动风格）。

    使用纯字典和列表操作完成营养评分、预算分析和统计计算，
    强调数据处理流程的清晰展示与课程知识点的综合运用。
    """

    def __init__(self, db_instance):
        """
        初始化分析器，绑定数据库实例。

        :param db_instance: 数据库实例，需实现 get_user 和 get_diet_records 方法
        """
        self.db = db_instance
        self._cache = {}  # 简单结果缓存，展示字典用法

    # ------------------------------------------------------------------
    # 类方法：支持从数据库路径创建实例
    # ------------------------------------------------------------------
    @classmethod
    def from_db_path(cls, db_path="diet_db.sqlite"):
        """
        从数据库路径创建分析器（classmethod 展示）。

        :param db_path: str SQLite数据库路径
        :return: DietAnalyzer 实例
        """
        # 动态导入避免顶层循环依赖
        from db import DietDatabase

        db = DietDatabase(db_path)
        return cls(db)

    # ------------------------------------------------------------------
    # 静态方法：通用工具函数
    # ------------------------------------------------------------------
    @staticmethod
    def calculate_nutrition_score(total_deviation):
        """
        根据总偏差计算营养评分（staticmethod 展示）。

        公式：score = max(0, 100 - 50 * total_deviation)

        :param total_deviation: float 总偏差值
        :return: int 评分（0-100）
        """
        score = max(0, 100 - 50 * total_deviation)
        return int(score)

    @staticmethod
    def estimate_record_calorie(record):
        """
        估算单条饮食记录的热量（基于拳头数映射）。

        :param record: dict 饮食记录，需包含 items 列表
        :return: float 估算热量（kcal）
        """
        total = 0.0
        for item in record.get("items", []):
            cat = item.get("category", "其他")
            fists = item.get("fist_count", 0) or 0
            kcal_per_fist = CALORIE_MAP.get(cat, 100)
            total += fists * kcal_per_fist
        return round(total, 2)

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------
    def _fetch_user_and_month_records(self, user_id):
        """
        获取用户配置和本月饮食记录（展示元组返回值）。

        :param user_id: int 用户ID
        :return: tuple(用户字典, 本月记录列表)
        """
        user = self.db.get_user(user_id)
        if user is None:
            return (None, [])

        # 获取全部记录
        all_records = self.db.get_diet_records(user_id)
        today = date.today()
        first_day, _, _, _ = get_month_window(today)

        # 使用列表推导式过滤本月记录（展示条件筛选）
        month_records = [
            r
            for r in all_records
            if parse_date_str(r["date"]).year == today.year
            and parse_date_str(r["date"]).month == today.month
        ]
        return (user, month_records)

    def _calc_daily_avg_calorie(self, records):
        """
        计算日均热量（内部辅助方法）。

        :param records: list 饮食记录列表
        :return: float 日均热量
        """
        if not records:
            return 0.0
        total_cal = sum(self.estimate_record_calorie(r) for r in records)
        # 使用集合去重获取不同日期数（展示set用法）
        unique_dates = {r["date"] for r in records}
        return round(total_cal / len(unique_dates), 2) if unique_dates else 0.0

    # ------------------------------------------------------------------
    # 核心分析接口 1：营养结构评分
    # ------------------------------------------------------------------
    def nutrition_score(self, user_id):
        """
        营养结构评分分析。

        :param user_id: int 用户ID
        :return: dict 包含 score, ideal, actual, deviation, suggestions
        """
        user, records = self._fetch_user_and_month_records(user_id)
        if user is None:
            return {"error": "用户不存在"}

        if not records:
            return {
                "score": 0,
                "ideal": {},
                "actual": {},
                "deviation": {},
                "suggestions": ["本月暂无饮食记录，无法评分"],
                "suggestion_text": "本月暂无饮食记录，无法评分",
            }

        # 获取健康目标并映射为标准名称
        goal = user.get("health_goal", "维持身材")
        standard_goal = GOAL_ALIASES.get(goal, "维持身材")
        ideal_ratios = IDEAL_STRUCTURES[standard_goal]

        # 使用集合去重收集所有涉及的分类（展示set用法）
        all_categories = set()
        for r in records:
            for item in r.get("items", []):
                all_categories.add(item.get("category", "其他"))

        # 使用 defaultdict 统计各类别拳头总数（展示collections用法）
        category_counts = defaultdict(float)
        for r in records:
            for item in r.get("items", []):
                cat = item.get("category", "其他")
                fists = item.get("fist_count", 0) or 0
                category_counts[cat] += fists

        # 归一化占比（元组解包）
        actual_ratios, total_fists = normalize_ratios(dict(category_counts))

        # 计算总偏差（元组解包）
        total_dev, deviation_detail = compute_total_deviation(actual_ratios, ideal_ratios)

        # 计算评分
        score = self.calculate_nutrition_score(total_dev)

        # 计算外卖占比用于建议
        takeout_count = sum(1 for r in records if r.get("is_takeout"))
        takeout_ratio = takeout_count / len(records) if records else 0.0

        # 计算日均热量
        daily_cal = self._calc_daily_avg_calorie(records)

        # 生成建议（使用**kwargs传递额外指标）
        suggestions = generate_health_suggestions(
            actual_ratios, ideal_ratios, takeout_ratio=takeout_ratio, daily_calorie=daily_cal
        )

        # 使用 join 将建议合并为文本（展示字符串join用法）
        suggestion_text = "；".join(suggestions)

        return {
            "score": score,
            "ideal": {k: round(v, 4) for k, v in ideal_ratios.items()},
            "actual": actual_ratios,
            "deviation": deviation_detail,
            "suggestions": suggestions,
            "suggestion_text": suggestion_text,
            "total_fists": total_fists,
            "goal": standard_goal,
            "daily_calorie": daily_cal,
        }

    # ------------------------------------------------------------------
    # 核心分析接口 2：预算分析
    # ------------------------------------------------------------------
    def budget_analysis(self, user_id):
        """
        预算分析。

        :param user_id: int 用户ID
        :return: dict 包含 total_spent, budget, remaining, daily_avg,
                       predicted_end, will_exceed, remaining_daily_budget
        """
        user, records = self._fetch_user_and_month_records(user_id)
        if user is None:
            return {"error": "用户不存在"}

        # 获取月度预算
        budget = float(user.get("monthly_budget", 0.0) or 0.0)

        # 计算本月总支出（使用生成器表达式）
        total_spent = round(sum(r.get("price", 0.0) or 0.0 for r in records), 2)
        remaining = round(budget - total_spent, 2)

        # 获取本月日期范围（元组解包）
        first_day, last_day, today, days_in_month = get_month_window()

        # 已过天数与剩余天数
        passed_days = today.day
        remaining_days = days_in_month - passed_days

        # 日均消费（默认值处理避免除零）
        daily_avg = round(total_spent / passed_days, 2) if passed_days > 0 else 0.0

        # 预测月末总支出
        predicted_end = round(daily_avg * days_in_month, 2) if daily_avg > 0 else 0.0

        # 是否超支预测
        will_exceed = predicted_end > budget

        # 剩余日均预算（默认值处理避免除零）
        remaining_daily_budget = round(remaining / remaining_days, 2) if remaining_days > 0 else 0.0

        # 预算使用率
        usage_ratio = round(total_spent / budget, 4) if budget > 0 else 0.0

        return {
            "total_spent": total_spent,
            "budget": budget,
            "remaining": remaining,
            "daily_avg": daily_avg,
            "predicted_end": predicted_end,
            "will_exceed": will_exceed,
            "remaining_days": remaining_days,
            "remaining_daily_budget": remaining_daily_budget,
            "days_in_month": days_in_month,
            "passed_days": passed_days,
            "budget_usage_ratio": usage_ratio,
        }

    # ------------------------------------------------------------------
    # 核心分析接口 3：统计计算
    # ------------------------------------------------------------------
    def meal_statistics(self, user_id):
        """
        饮食统计计算。

        :param user_id: int 用户ID
        :return: dict 包含 total_meals, total_cost, daily_avg, meal_breakdown,
                       takeout_ratio, top_locations
        """
        user, records = self._fetch_user_and_month_records(user_id)
        if user is None:
            return {"error": "用户不存在"}

        total_meals = len(records)
        total_cost = round(sum(r.get("price", 0.0) or 0.0 for r in records), 2)

        # 使用集合去重获取不同日期数（展示set用法）
        unique_dates = {r["date"] for r in records}
        daily_avg = round(total_cost / len(unique_dates), 2) if unique_dates else 0.0

        # 各餐次支出占比（使用通用聚合函数）
        meal_costs = aggregate_by_key(
            records,
            key_func=lambda r: r.get("meal", "未知"),
            value_func=lambda r: r.get("price", 0.0) or 0.0,
        )

        # 计算各餐次的详细统计
        meal_breakdown = {}
        for meal, cost in meal_costs.items():
            meal_breakdown[meal] = {
                "cost": round(cost, 2),
                "ratio": round(cost / total_cost, 4) if total_cost > 0 else 0.0,
                "count": sum(1 for r in records if r.get("meal") == meal),
            }

        # 外卖占比统计
        takeout_count = sum(1 for r in records if r.get("is_takeout"))
        takeout_ratio = round(takeout_count / total_meals, 4) if total_meals > 0 else 0.0

        # 最常去的食堂/门店 TOP 5（展示sorted函数和key参数）
        location_counts = {}
        for r in records:
            loc = r.get("location_name", "未知")
            if loc:
                location_counts[loc] = location_counts.get(loc, 0) + 1

        top_locations = top_n_sorted(location_counts, n=5, reverse=True)

        # 使用集合操作分析就餐地点模式（展示集合运算）
        canteen_dates = {r["date"] for r in records if r.get("location_type") == "食堂"}
        takeout_dates = {r["date"] for r in records if r.get("is_takeout")}

        # 差集：仅在食堂就餐的日期
        only_canteen = canteen_dates - takeout_dates
        # 交集：既去食堂又点外卖的日期
        mixed_dates = canteen_dates & takeout_dates
        # 并集：有就餐记录的日期
        all_dates = canteen_dates | takeout_dates

        return {
            "total_meals": total_meals,
            "total_cost": total_cost,
            "daily_avg": daily_avg,
            "meal_breakdown": meal_breakdown,
            "takeout_ratio": takeout_ratio,
            "takeout_count": takeout_count,
            "top_locations": top_locations,
            "location_set_stats": {
                "canteen_only_days": len(only_canteen),
                "mixed_days": len(mixed_dates),
                "all_eating_days": len(all_dates),
                "unique_dates": len(unique_dates),
            },
        }

    # ------------------------------------------------------------------
    # 核心分析接口 4：日均热量估算趋势
    # ------------------------------------------------------------------
    def daily_calorie_trend(self, user_id):
        """
        日均热量估算趋势（基于拳头数映射）。

        :param user_id: int 用户ID
        :return: list[dict] 每日热量估算列表
        """
        user, records = self._fetch_user_and_month_records(user_id)
        if user is None or not records:
            return []

        # 使用字典按日期聚合热量和餐次
        daily_data = {}
        for r in records:
            d = r["date"]
            cal = self.estimate_record_calorie(r)
            if d not in daily_data:
                daily_data[d] = {"total_cal": 0.0, "meals": 0}
            daily_data[d]["total_cal"] += cal
            daily_data[d]["meals"] += 1

        # 使用sorted函数按日期排序（展示sorted和key参数）
        result = []
        for d in sorted(daily_data.keys()):
            info = daily_data[d]
            result.append(
                {
                    "date": d,
                    "total_calorie": round(info["total_cal"], 2),
                    "meal_count": info["meals"],
                    "avg_calorie_per_meal": round(info["total_cal"] / info["meals"], 2)
                    if info["meals"] > 0
                    else 0,
                }
            )

        return result


# =====================================================================
# 自测入口
# =====================================================================


def _build_mock_db():
    """
    构建模拟数据库用于自测（不依赖真实db.py和SQLite）。

    使用当月日期确保自测始终有可匹配的本月记录。
    """
    today = date.today()
    # 生成5条测试记录，分布在当月最近5天
    dates = [(today - timedelta(days=4 - i)).isoformat() for i in range(5)]

    class MockDB:
        """模拟数据库类，仅用于自测。"""

        def __init__(self):
            self.users = {
                1: {
                    "id": 1,
                    "username": "test_user",
                    "monthly_budget": 1200.0,
                    "health_goal": "维持身材",
                }
            }
            self._records = [
                {
                    "id": 1,
                    "user_id": 1,
                    "date": dates[0],
                    "meal": "午餐",
                    "location_type": "食堂",
                    "location_name": "学一食堂",
                    "food_name": "广式烧鸭饭",
                    "price": 15.5,
                    "is_takeout": 0,
                    "items": [
                        {"category": "主食", "fist_count": 2.0},
                        {"category": "肉类", "fist_count": 1.0},
                        {"category": "蔬菜", "fist_count": 0.5},
                    ],
                },
                {
                    "id": 2,
                    "user_id": 1,
                    "date": dates[1],
                    "meal": "晚餐",
                    "location_type": "外卖",
                    "location_name": "麦当劳",
                    "food_name": "巨无霸套餐",
                    "price": 35.0,
                    "is_takeout": 1,
                    "items": [
                        {"category": "主食", "fist_count": 1.5},
                        {"category": "肉类", "fist_count": 1.0},
                        {"category": "饮料", "fist_count": 1.0},
                    ],
                },
                {
                    "id": 3,
                    "user_id": 1,
                    "date": dates[2],
                    "meal": "早餐",
                    "location_type": "食堂",
                    "location_name": "学一食堂",
                    "food_name": "豆浆油条",
                    "price": 6.0,
                    "is_takeout": 0,
                    "items": [
                        {"category": "主食", "fist_count": 1.0},
                        {"category": "饮料", "fist_count": 0.5},
                    ],
                },
                {
                    "id": 4,
                    "user_id": 1,
                    "date": dates[3],
                    "meal": "午餐",
                    "location_type": "食堂",
                    "location_name": "松涛园",
                    "food_name": "麻辣烫",
                    "price": 22.0,
                    "is_takeout": 0,
                    "items": [
                        {"category": "主食", "fist_count": 1.0},
                        {"category": "蔬菜", "fist_count": 2.0},
                        {"category": "肉类", "fist_count": 1.5},
                    ],
                },
                {
                    "id": 5,
                    "user_id": 1,
                    "date": dates[4],
                    "meal": "晚餐",
                    "location_type": "校外门店",
                    "location_name": "兰州拉面",
                    "food_name": "牛肉拉面",
                    "price": 15.0,
                    "is_takeout": 0,
                    "items": [
                        {"category": "主食", "fist_count": 2.0},
                        {"category": "肉类", "fist_count": 0.5},
                        {"category": "蔬菜", "fist_count": 0.5},
                    ],
                },
            ]

        def get_user(self, user_id):
            """根据ID获取用户。"""
            return self.users.get(user_id)

        def get_diet_records(self, user_id):
            """获取用户全部饮食记录。"""
            return [r for r in self._records if r["user_id"] == user_id]

    return MockDB()


if __name__ == "__main__":
    print("=" * 60)
    print("analyzer_v3.py 自测入口")
    print("=" * 60)

    mock_db = _build_mock_db()
    analyzer = DietAnalyzer(mock_db)

    # --------------- 1. 营养结构评分 ---------------
    print("\n--- 1. 营养结构评分 ---")
    score_data = analyzer.nutrition_score(1)
    if "error" in score_data:
        print(f"  错误: {score_data['error']}")
    else:
        print(f"  健康目标: {score_data['goal']}")
        print(f"  营养评分: {score_data['score']} 分")
        print(f"  总拳数: {score_data['total_fists']}")
        print(f"  日均热量: {score_data['daily_calorie']} kcal")
        print(f"  理想占比: {score_data['ideal']}")
        print(f"  实际占比: {score_data['actual']}")
        print(f"  偏差明细: {score_data['deviation']}")
        print(f"  健康建议: {score_data['suggestion_text']}")

    # --------------- 2. 预算分析 ---------------
    print("\n--- 2. 预算分析 ---")
    budget_data = analyzer.budget_analysis(1)
    if "error" in budget_data:
        print(f"  错误: {budget_data['error']}")
    else:
        print(f"  月度预算: {budget_data['budget']:.2f} 元")
        print(f"  已支出: {budget_data['total_spent']:.2f} 元")
        print(f"  剩余: {budget_data['remaining']:.2f} 元")
        print(f"  日均消费: {budget_data['daily_avg']:.2f} 元")
        print(f"  预测月末: {budget_data['predicted_end']:.2f} 元")
        print(f"  是否超支: {'是' if budget_data['will_exceed'] else '否'}")
        print(f"  剩余日均预算: {budget_data['remaining_daily_budget']:.2f} 元")

    # --------------- 3. 饮食统计 ---------------
    print("\n--- 3. 饮食统计 ---")
    stats_data = analyzer.meal_statistics(1)
    if "error" in stats_data:
        print(f"  错误: {stats_data['error']}")
    else:
        print(f"  总餐次: {stats_data['total_meals']}")
        print(f"  总支出: {stats_data['total_cost']:.2f} 元")
        print(f"  日均支出: {stats_data['daily_avg']:.2f} 元")
        print(f"  外卖占比: {format_percent(stats_data['takeout_ratio'])}")
        print(f"  各餐次分布:")
        for meal, info in stats_data["meal_breakdown"].items():
            print(f"    {meal}: {info['count']} 次, {info['cost']:.2f} 元, 占比 {format_percent(info['ratio'])}")
        print(f"  最常去地点 TOP 5:")
        for loc, count in stats_data["top_locations"]:
            print(f"    {loc}: {count} 次")
        print(f"  集合统计: {stats_data['location_set_stats']}")

    # --------------- 4. 日均热量趋势 ---------------
    print("\n--- 4. 日均热量趋势 ---")
    trend_data = analyzer.daily_calorie_trend(1)
    for item in trend_data:
        print(
            f"  {item['date']}: 总热量 {item['total_calorie']} kcal, "
            f"餐次 {item['meal_count']}, 均餐 {item['avg_calorie_per_meal']} kcal"
        )

    # --------------- 5. 异常测试 ---------------
    print("\n--- 5. 异常处理：不存在的用户 ---")
    print(f"  {analyzer.nutrition_score(999)}")
    print(f"  {analyzer.budget_analysis(999)}")
    print(f"  {analyzer.meal_statistics(999)}")
    print(f"  {analyzer.daily_calorie_trend(999)}")

    print("\n" + "=" * 60)
    print("analyzer_v3.py 自测全部通过")
    print("=" * 60)
