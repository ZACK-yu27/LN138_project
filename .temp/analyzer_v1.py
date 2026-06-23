"""
饮食分析器模块 (Analyzer_v1)
中山大学《程序设计IV（实验）》期末项目

本模块提供 DietAnalyzer 类，用于分析用户的饮食记录、营养结构、预算和热量趋势。
严格使用原生 Python 实现，不依赖 pandas 等外部数据分析库。

课程知识点展示：
- 函数（第6章）：合理封装功能模块，使用位置参数和默认返回值
- 类与OOP（第8章）：DietAnalyzer 类，包含属性与多个方法
- 控制结构（第4章）：循环遍历、条件筛选
- 列表/字典（第3、5章）：列表推导式、字典统计与聚合、defaultdict、Counter
- 字符串处理（第2章）：f-string 格式化输出、类别名称归一化
"""

import sqlite3
from datetime import datetime, date, timedelta
from collections import defaultdict, Counter


# -------------- 常量定义 --------------

# 热量映射（单位：kcal/拳）
CALORIE_MAP = {
    '主食': 200,
    '蔬菜': 50,
    '肉类': 150,
    '水果': 80,
    '饮料': 100,
    '零食': 150,
    '其他': 100,
}

# 理想营养结构（按健康目标）
IDEAL_STRUCTURE = {
    'lose_weight': {
        '主食': 0.30,
        '蔬菜': 0.30,
        '肉类': 0.20,
        '水果': 0.10,
        '饮料/零食': 0.05,
        '其他': 0.05,
    },
    'maintain': {
        '主食': 0.35,
        '蔬菜': 0.25,
        '肉类': 0.20,
        '水果': 0.10,
        '饮料/零食': 0.05,
        '其他': 0.05,
    },
    'gain_weight': {
        '主食': 0.40,
        '蔬菜': 0.15,
        '肉类': 0.30,
        '水果': 0.05,
        '饮料/零食': 0.05,
        '其他': 0.05,
    },
}

# 健康目标名称映射
GOAL_NAMES = {
    'lose_weight': '减肥',
    'maintain': '维持',
    'gain_weight': '增重',
}

# 默认配置
DEFAULT_BUDGET = 1500.0
DEFAULT_GOAL = 'maintain'


# -------------- 主类定义 --------------

class DietAnalyzer:
    """饮食分析器类，用于分析用户的饮食记录、营养结构和预算情况。

    属性：
        db_instance: DietDatabase 实例，提供数据库访问能力。
        _default_budget: 默认月度预算，单位为元。
        _default_goal: 默认健康目标，可选值为 'lose_weight', 'maintain', 'gain_weight'。
    """

    def __init__(self, db_instance):
        """初始化 DietAnalyzer 实例。

        参数：
            db_instance: DietDatabase 类的实例，需实现 get_diet_records(user_id) 方法。
        """
        self.db_instance = db_instance
        self._default_budget = DEFAULT_BUDGET
        self._default_goal = DEFAULT_GOAL

    # -------------- 辅助函数（第6章：函数封装）--------------

    def _get_user_config(self, user_id):
        """获取用户配置信息（预算和健康目标）。

        尝试从数据库查询用户配置，如果失败则返回默认值。

        参数：
            user_id: 用户ID。

        返回：
            dict，包含 'budget' 和 'goal' 键。
        """
        # 尝试调用 db_instance 的用户配置方法（如果存在）
        try:
            if hasattr(self.db_instance, 'get_user_profile'):
                profile = self.db_instance.get_user_profile(user_id)
                if profile and isinstance(profile, dict):
                    budget = profile.get('budget', self._default_budget)
                    goal = profile.get('goal', self._default_goal)
                    return {'budget': budget, 'goal': goal}
        except Exception:
            pass
        # 回退到默认配置
        return {'budget': self._default_budget, 'goal': self._default_goal}

    def _get_month_records(self, user_id, year=None, month=None):
        """获取指定月份的所有饮食记录。

        参数：
            user_id: 用户ID。
            year: 年份，默认为当前年份。
            month: 月份，默认为当前月份。

        返回：
            list[dict]，过滤后的记录列表。
        """
        today = date.today()
        target_year = year or today.year
        target_month = month or today.month

        # 获取所有记录
        all_records = self.db_instance.get_diet_records(user_id)

        # 使用列表推导式过滤当月记录（第5章：列表推导式）
        month_records = [
            record for record in all_records
            if self._parse_record_date(record.get('date')) == (target_year, target_month)
        ]
        return month_records

    def _parse_record_date(self, date_value):
        """解析日期值，返回 (year, month) 元组。

        参数：
            date_value: 日期值，支持字符串 'YYYY-MM-DD' 或 date/datetime 对象。

        返回：
            tuple: (year, month) 或 None。
        """
        if not date_value:
            return None
        # 如果已经是 date 或 datetime 对象（第4章：条件筛选）
        if isinstance(date_value, (date, datetime)):
            dt = date_value if isinstance(date_value, date) else date_value.date()
            return (dt.year, dt.month)
        try:
            dt = datetime.strptime(str(date_value), '%Y-%m-%d')
            return (dt.year, dt.month)
        except ValueError:
            return None

    def _parse_record_day(self, date_value):
        """解析日期值，返回完整的 date 对象。

        参数：
            date_value: 日期值，支持字符串或 date/datetime 对象。

        返回：
            date 对象或 None。
        """
        if not date_value:
            return None
        if isinstance(date_value, (date, datetime)):
            return date_value if isinstance(date_value, date) else date_value.date()
        try:
            return datetime.strptime(str(date_value), '%Y-%m-%d').date()
        except ValueError:
            return None

    def _get_category_fists(self, records):
        """从记录中统计各类别的总拳数。

        参数：
            records: list[dict]，饮食记录列表。

        返回：
            dict: {category: total_fists}。
        """
        # 使用 defaultdict 进行字典统计（第5章：字典聚合）
        category_fists = defaultdict(float)
        for record in records:
            items = record.get('items', [])
            for item in items:
                category = item.get('category', '其他')
                fists = item.get('fist_count', 0) or 0
                category_fists[category] += float(fists)
        return dict(category_fists)

    def _calculate_calorie(self, category, fists):
        """计算指定类别和拳数的热量。

        参数：
            category: 食物类别。
            fists: 拳数。

        返回：
            float: 热量值（kcal）。
        """
        calorie_per_fist = CALORIE_MAP.get(category, 100)
        return float(fists) * calorie_per_fist

    def _get_meal_type(self, meal_str):
        """将餐次字符串归一化为标准餐次名称。

        参数：
            meal_str: 餐次字符串，如 '早餐'、'lunch' 等。

        返回：
            str: 标准餐次名称（早餐/午餐/晚餐/加餐/其他）。
        """
        if not meal_str:
            return '其他'

        # 统一转小写并去除首尾空格（第2章：字符串处理）
        meal_str = str(meal_str).strip().lower()

        # 使用条件筛选（第4章：条件语句）
        if meal_str in ('早餐', 'breakfast', '早'):
            return '早餐'
        elif meal_str in ('午餐', 'lunch', '午'):
            return '午餐'
        elif meal_str in ('晚餐', 'dinner', '晚'):
            return '晚餐'
        elif meal_str in ('加餐', 'snack', '加'):
            return '加餐'
        else:
            return '其他'

    # -------------- 核心分析方法（第8章：类与OOP）--------------

    def nutrition_score(self, user_id):
        """计算用户的营养结构评分。

        基于用户的健康目标，将实际饮食结构与理想结构进行对比，
        计算偏差并给出评分和建议。

        参数：
            user_id: 用户ID。

        返回：
            dict，包含：
                - score: 营养评分（0-100）
                - ideal: 理想结构占比
                - actual: 实际结构占比
                - deviation: 各类别偏差
                - suggestions: 健康建议列表
        """
        # 获取用户配置
        config = self._get_user_config(user_id)
        goal = config.get('goal', self._default_goal)

        # 获取当月记录
        records = self._get_month_records(user_id)

        # 统计各类别拳数
        category_fists = self._get_category_fists(records)

        # 如果没有数据，返回空结果
        if not category_fists:
            return {
                'score': 0,
                'ideal': IDEAL_STRUCTURE.get(goal, IDEAL_STRUCTURE['maintain']),
                'actual': {},
                'deviation': {},
                'suggestions': ['本月暂无饮食记录，请开始记录您的饮食。'],
            }

        # 获取理想结构
        ideal = IDEAL_STRUCTURE.get(goal, IDEAL_STRUCTURE['maintain'])
        ideal_categories = set(ideal.keys())

        # 合并饮料和零食为统一类别，未在 ideal 中的类别归入"其他"
        # 使用 defaultdict 进行字典聚合（第5章：字典）
        unified_fists = defaultdict(float)
        for category, fists in category_fists.items():
            if category in ('饮料', '零食'):
                unified_key = '饮料/零食'
            elif category in ideal_categories:
                unified_key = category
            else:
                # 未在 ideal 中的类别统一归入"其他"
                unified_key = '其他'
            unified_fists[unified_key] += fists
        unified_fists = dict(unified_fists)

        total_unified = sum(unified_fists.values())

        # 计算实际占比和偏差（第4章：循环遍历）
        actual = {}
        deviation = {}
        total_deviation = 0.0

        for category in ideal.keys():
            fists = unified_fists.get(category, 0.0)
            actual_ratio = fists / total_unified if total_unified > 0 else 0.0
            ideal_ratio = ideal.get(category, 0.0)
            diff = abs(actual_ratio - ideal_ratio)

            actual[category] = round(actual_ratio, 4)
            deviation[category] = round(diff, 4)
            total_deviation += diff

        # 计算评分：score = max(0, 100 - 50 * total_deviation)
        score = max(0, 100 - 50 * total_deviation)
        score = round(score, 2)

        # 生成健康建议
        suggestions = self._generate_nutrition_suggestions(
            actual, ideal, unified_fists, total_unified, records
        )

        return {
            'score': score,
            'ideal': ideal,
            'actual': actual,
            'deviation': deviation,
            'suggestions': suggestions,
        }

    def _generate_nutrition_suggestions(self, actual, ideal, category_fists, total_fists, records):
        """根据营养结构生成健康建议。

        参数：
            actual: 实际占比字典。
            ideal: 理想占比字典。
            category_fists: 各类别拳数字典。
            total_fists: 总拳数。
            records: 原始记录列表。

        返回：
            list[str]: 建议列表。
        """
        suggestions = []

        for category, ideal_ratio in ideal.items():
            actual_ratio = actual.get(category, 0.0)
            fists = category_fists.get(category, 0.0)

            # 使用 f-string 格式化（第2章：字符串处理）
            if actual_ratio < ideal_ratio * 0.5:
                suggestions.append(f'{category}摄入严重不足，建议增加{fists:.1f}拳以上')
            elif actual_ratio < ideal_ratio * 0.8:
                suggestions.append(f'{category}摄入不足，建议适当补充')
            elif actual_ratio > ideal_ratio * 1.5:
                suggestions.append(f'{category}偏多，建议减少摄入')

        # 检查外卖占比
        if records:
            takeout_count = sum(1 for r in records if r.get('is_takeout'))
            takeout_ratio = takeout_count / len(records)
            if takeout_ratio > 0.5:
                suggestions.append(
                    f'外卖占比过高（{takeout_ratio*100:.1f}%），建议多选择食堂就餐'
                )

        # 如果没有明显问题，给出正面反馈
        if not suggestions:
            suggestions.append('营养结构较为均衡，请继续保持')

        return suggestions

    def budget_analysis(self, user_id):
        """分析用户本月预算使用情况。

        计算已用预算、剩余预算、日均消费，并预测本月是否超支。

        参数：
            user_id: 用户ID。

        返回：
            dict，包含：
                - total_spent: 本月已支出
                - budget: 月度预算
                - remaining: 剩余预算
                - daily_avg: 日均支出
                - predicted_end: 预测月末总支出
                - will_exceed: 是否会超支
                - remaining_daily: 剩余日均预算
        """
        today = date.today()
        year, month = today.year, today.month

        # 获取用户配置
        config = self._get_user_config(user_id)
        budget = config.get('budget', self._default_budget)

        # 获取当月记录
        records = self._get_month_records(user_id, year, month)

        # 计算总支出（使用列表推导式聚合）
        total_spent = sum(float(r.get('price', 0) or 0) for r in records)
        total_spent = round(total_spent, 2)

        # 计算剩余预算
        remaining = budget - total_spent
        remaining = round(remaining, 2)

        # 计算本月天数（使用 datetime，不导入 calendar）
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        days_in_month = (next_month - date(year, month, 1)).days

        # 计算已过天数（包含今天）
        passed_days = today.day

        # 计算日均支出
        daily_avg = total_spent / passed_days if passed_days > 0 else 0.0
        daily_avg = round(daily_avg, 2)

        # 按当前日均消费预测本月总支出
        predicted_end = daily_avg * days_in_month
        predicted_end = round(predicted_end, 2)

        # 判断是否超支
        will_exceed = predicted_end > budget

        # 计算剩余日均预算
        remaining_days = days_in_month - passed_days + 1  # 包含今天
        remaining_daily = remaining / remaining_days if remaining_days > 0 else 0.0
        remaining_daily = round(remaining_daily, 2)

        return {
            'total_spent': total_spent,
            'budget': budget,
            'remaining': remaining,
            'daily_avg': daily_avg,
            'predicted_end': predicted_end,
            'will_exceed': will_exceed,
            'remaining_daily': remaining_daily,
        }

    def meal_statistics(self, user_id):
        """计算用户本月饮食统计信息。

        参数：
            user_id: 用户ID。

        返回：
            dict，包含：
                - total_meals: 总餐次
                - total_cost: 总支出
                - daily_avg: 日均支出
                - meal_breakdown: 各餐次支出占比
                - takeout_ratio: 外卖占比
                - top_locations: 最常去的门店 TOP5
        """
        today = date.today()
        year, month = today.year, today.month

        # 获取当月记录
        records = self._get_month_records(user_id, year, month)

        # 总餐次
        total_meals = len(records)

        # 总支出
        total_cost = sum(float(r.get('price', 0) or 0) for r in records)
        total_cost = round(total_cost, 2)

        # 日均支出
        passed_days = today.day
        daily_avg = total_cost / passed_days if passed_days > 0 else 0.0
        daily_avg = round(daily_avg, 2)

        # 各餐次支出占比（使用 defaultdict 进行字典聚合）
        meal_costs = defaultdict(float)
        for record in records:
            meal_type = self._get_meal_type(record.get('meal'))
            price = float(record.get('price', 0) or 0)
            meal_costs[meal_type] += price

        # 计算各餐次占比（第4章：条件分支）
        meal_breakdown = {}
        if total_cost > 0:
            for meal_type, cost in meal_costs.items():
                meal_breakdown[meal_type] = {
                    'cost': round(cost, 2),
                    'ratio': round(cost / total_cost, 4),
                    'percentage': f'{cost/total_cost*100:.2f}%',
                }

        # 外卖占比
        if total_meals > 0:
            takeout_count = sum(1 for r in records if r.get('is_takeout'))
            takeout_ratio = round(takeout_count / total_meals, 4)
        else:
            takeout_ratio = 0.0

        # 最常去的食堂/门店 TOP5（使用 Counter）
        location_counter = Counter()
        for record in records:
            loc_name = record.get('location_name', '未知')
            location_counter[loc_name] += 1

        # 获取 TOP5 并格式化（列表推导式）
        top_locations = [
            {
                'name': loc,
                'count': count,
                'percentage': f'{count/total_meals*100:.1f}%' if total_meals > 0 else '0.0%',
            }
            for loc, count in location_counter.most_common(5)
        ]

        return {
            'total_meals': total_meals,
            'total_cost': total_cost,
            'daily_avg': daily_avg,
            'meal_breakdown': dict(meal_breakdown),
            'takeout_ratio': takeout_ratio,
            'top_locations': top_locations,
        }

    def daily_calorie_trend(self, user_id):
        """计算每日热量估算趋势。

        基于拳头数映射，按天聚合所有记录的热量。

        参数：
            user_id: 用户ID。

        返回：
            list[dict]: 每日热量列表，每个字典包含 'date' 和 'calories'。
        """
        # 获取当月记录
        records = self._get_month_records(user_id)

        # 按日期分组统计热量（使用 defaultdict 聚合）
        daily_calories = defaultdict(float)

        for record in records:
            day = self._parse_record_day(record.get('date'))
            if not day:
                continue

            items = record.get('items', [])
            for item in items:
                category = item.get('category', '其他')
                fists = item.get('fist_count', 0) or 0
                calories = self._calculate_calorie(category, fists)
                daily_calories[day] += calories

        # 按日期排序并转换为列表（列表推导式）
        result = [
            {'date': str(day), 'calories': round(cal, 2)}
            for day, cal in sorted(daily_calories.items())
        ]

        return result


# ==================== 自测入口 ====================

class _MockDB:
    """模拟 DietDatabase 类，用于自测。

    提供 get_diet_records 方法返回测试数据。
    """

    def __init__(self):
        """初始化模拟数据库，使用当前日期生成测试数据。"""
        from datetime import date, timedelta
        today = date.today()

        # 使用最近3天的日期生成测试数据，确保在本月内
        d1 = today - timedelta(days=2)
        d2 = today - timedelta(days=1)
        d3 = today

        # 如果跨月，则全部使用今天
        if d1.month != today.month:
            d1 = today
        if d2.month != today.month:
            d2 = today

        d1_str = d1.isoformat()
        d2_str = d2.isoformat()
        d3_str = d3.isoformat()

        self._records = [
            {
                'id': 1, 'user_id': 1, 'date': d1_str, 'meal': '早餐',
                'location_type': '食堂', 'location_name': '松涛园',
                'food_name': '粥+包子', 'price': 8.0, 'is_takeout': 0,
                'created_at': f'{d1_str} 08:00:00',
                'items': [
                    {'category': '主食', 'fist_count': 1.0},
                    {'category': '饮料', 'fist_count': 0.5},
                ],
            },
            {
                'id': 2, 'user_id': 1, 'date': d1_str, 'meal': '午餐',
                'location_type': '食堂', 'location_name': '松涛园',
                'food_name': '米饭+青菜+鸡腿', 'price': 18.0, 'is_takeout': 0,
                'created_at': f'{d1_str} 12:00:00',
                'items': [
                    {'category': '主食', 'fist_count': 1.5},
                    {'category': '蔬菜', 'fist_count': 1.0},
                    {'category': '肉类', 'fist_count': 1.0},
                ],
            },
            {
                'id': 3, 'user_id': 1, 'date': d1_str, 'meal': '晚餐',
                'location_type': '外卖', 'location_name': '麦当劳',
                'food_name': '汉堡套餐', 'price': 35.0, 'is_takeout': 1,
                'created_at': f'{d1_str} 18:00:00',
                'items': [
                    {'category': '主食', 'fist_count': 2.0},
                    {'category': '肉类', 'fist_count': 1.5},
                    {'category': '饮料', 'fist_count': 1.0},
                ],
            },
            {
                'id': 4, 'user_id': 1, 'date': d2_str, 'meal': '早餐',
                'location_type': '食堂', 'location_name': '春晖园',
                'food_name': '面条', 'price': 10.0, 'is_takeout': 0,
                'created_at': f'{d2_str} 08:00:00',
                'items': [
                    {'category': '主食', 'fist_count': 1.5},
                ],
            },
            {
                'id': 5, 'user_id': 1, 'date': d2_str, 'meal': '午餐',
                'location_type': '食堂', 'location_name': '松涛园',
                'food_name': '米饭+红烧肉', 'price': 20.0, 'is_takeout': 0,
                'created_at': f'{d2_str} 12:00:00',
                'items': [
                    {'category': '主食', 'fist_count': 1.5},
                    {'category': '肉类', 'fist_count': 1.5},
                    {'category': '蔬菜', 'fist_count': 0.5},
                ],
            },
            {
                'id': 6, 'user_id': 1, 'date': d2_str, 'meal': '晚餐',
                'location_type': '外卖', 'location_name': '肯德基',
                'food_name': '炸鸡套餐', 'price': 40.0, 'is_takeout': 1,
                'created_at': f'{d2_str} 18:00:00',
                'items': [
                    {'category': '肉类', 'fist_count': 2.0},
                    {'category': '主食', 'fist_count': 1.0},
                    {'category': '饮料', 'fist_count': 1.0},
                ],
            },
            {
                'id': 7, 'user_id': 1, 'date': d3_str, 'meal': '早餐',
                'location_type': '食堂', 'location_name': '松涛园',
                'food_name': '豆浆+油条', 'price': 6.0, 'is_takeout': 0,
                'created_at': f'{d3_str} 08:00:00',
                'items': [
                    {'category': '主食', 'fist_count': 1.0},
                    {'category': '饮料', 'fist_count': 0.5},
                ],
            },
            {
                'id': 8, 'user_id': 1, 'date': d3_str, 'meal': '午餐',
                'location_type': '食堂', 'location_name': '学五食堂',
                'food_name': '盖浇饭', 'price': 16.0, 'is_takeout': 0,
                'created_at': f'{d3_str} 12:00:00',
                'items': [
                    {'category': '主食', 'fist_count': 1.5},
                    {'category': '肉类', 'fist_count': 1.0},
                    {'category': '蔬菜', 'fist_count': 1.0},
                ],
            },
            {
                'id': 9, 'user_id': 1, 'date': d3_str, 'meal': '晚餐',
                'location_type': '食堂', 'location_name': '学五食堂',
                'food_name': '粥+小菜', 'price': 12.0, 'is_takeout': 0,
                'created_at': f'{d3_str} 18:00:00',
                'items': [
                    {'category': '主食', 'fist_count': 1.0},
                    {'category': '蔬菜', 'fist_count': 1.0},
                ],
            },
            {
                'id': 10, 'user_id': 1, 'date': d3_str, 'meal': '加餐',
                'location_type': '超市', 'location_name': '教育超市',
                'food_name': '水果+零食', 'price': 15.0, 'is_takeout': 0,
                'created_at': f'{d3_str} 20:00:00',
                'items': [
                    {'category': '水果', 'fist_count': 1.0},
                    {'category': '零食', 'fist_count': 0.5},
                ],
            },
        ]

    def get_diet_records(self, user_id):
        """获取指定用户的饮食记录。

        参数：
            user_id: 用户ID。

        返回：
            list[dict]: 记录列表。
        """
        return [r for r in self._records if r['user_id'] == user_id]


if __name__ == '__main__':
    """自测入口：创建模拟数据库并运行所有分析功能。"""
    print('=== DietAnalyzer 自测 ===')
    print()

    # 创建模拟数据库实例
    mock_db = _MockDB()

    # 创建分析器实例
    analyzer = DietAnalyzer(mock_db)

    # 测试1：营养结构评分
    print('--- 1. 营养结构评分 ---')
    nutrition = analyzer.nutrition_score(1)
    print(f'评分: {nutrition["score"]}')
    print(f'理想结构: {nutrition["ideal"]}')
    print(f'实际结构: {nutrition["actual"]}')
    print(f'偏差: {nutrition["deviation"]}')
    print(f'建议: {nutrition["suggestions"]}')
    print()

    # 测试2：预算分析
    print('--- 2. 预算分析 ---')
    budget = analyzer.budget_analysis(1)
    print(f'已支出: {budget["total_spent"]} 元')
    print(f'月度预算: {budget["budget"]} 元')
    print(f'剩余: {budget["remaining"]} 元')
    print(f'日均支出: {budget["daily_avg"]} 元')
    print(f'预测月末: {budget["predicted_end"]} 元')
    print(f'是否会超支: {budget["will_exceed"]}')
    print(f'剩余日均预算: {budget["remaining_daily"]} 元')
    print()

    # 测试3：统计信息
    print('--- 3. 统计信息 ---')
    stats = analyzer.meal_statistics(1)
    print(f'总餐次: {stats["total_meals"]}')
    print(f'总支出: {stats["total_cost"]} 元')
    print(f'日均支出: {stats["daily_avg"]} 元')
    print(f'餐次分布: {stats["meal_breakdown"]}')
    print(f'外卖占比: {stats["takeout_ratio"]}')
    print(f'常去门店 TOP5: {stats["top_locations"]}')
    print()

    # 测试4：热量趋势
    print('--- 4. 每日热量趋势 ---')
    trend = analyzer.daily_calorie_trend(1)
    for day in trend:
        print(f'{day["date"]}: {day["calories"]} kcal')
    print()

    print('=== 自测完成 ===')
