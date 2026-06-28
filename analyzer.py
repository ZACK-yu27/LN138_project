# -*- coding: utf-8 -*-
"""
饮食分析模块 v2 (analyzer_v2.py)

中山大学《程序设计IV（实验）》期末项目
角色: Analyzer_v2 分析模块

本模块采用面向对象风格，封装营养评分、预算分析、用餐统计、热量趋势等功能。
使用 lambda、列表/字典推导式、Counter 等 Python 特性展示课程知识点。
"""

import sqlite3
from datetime import datetime, date
from collections import Counter


class DietAnalyzer:
    """
    饮食分析器 v2
    
    提供营养结构评分、预算分析、用餐统计、热量趋势等核心分析功能。
    所有统计逻辑封装为内部辅助方法，通过公共接口对外暴露。
    """
    
    # 类别热量映射 (单位: kcal/拳)
    CALORIE_MAP = {
        '主食': 200,
        '蔬菜': 50,
        '肉类': 150,
        '水果': 80,
        '饮料': 100,
        '零食': 150,
        '其他': 100,
    }
    _CALORIE_MAP = CALORIE_MAP  # 向后兼容别名
    
    # 健康目标对应的理想营养结构占比
    IDEAL_STRUCTURE = {
        '减肥': {
            '主食': 0.30,
            '蔬菜': 0.30,
            '肉类': 0.20,
            '水果': 0.10,
            '饮料/零食': 0.05,
            '其他': 0.05,
        },
        '维持': {
            '主食': 0.35,
            '蔬菜': 0.25,
            '肉类': 0.20,
            '水果': 0.10,
            '饮料/零食': 0.05,
            '其他': 0.05,
        },
        '增重': {
            '主食': 0.40,
            '蔬菜': 0.15,
            '肉类': 0.30,
            '水果': 0.05,
            '饮料/零食': 0.05,
            '其他': 0.05,
        },
    }
    _IDEAL_STRUCTURE = IDEAL_STRUCTURE  # 向后兼容别名（仅 analyzer 内部使用）
    
    # 默认健康目标
    _DEFAULT_GOAL = '维持'
    
    # 默认月度预算 (单位: 元)
    _DEFAULT_BUDGET = 1500.0
    
    def __init__(self, db_instance):
        """
        初始化分析器，绑定数据库实例。
        
        :param db_instance: DietDatabase 实例，需实现 get_diet_records(user_id) 方法
        """
        self._db = db_instance
        self._today = date.today()
        self._current_year = self._today.year
        self._current_month = self._today.month
    
    # ==================== 私有辅助方法 ====================
    
    def _get_month_records(self, user_id):
        """
        获取用户当月所有饮食记录。
        
        使用列表推导式筛选出日期属于当前年月的记录。
        
        :param user_id: 用户ID
        :return: list[dict] 当月记录列表
        """
        all_records = self._db.get_diet_records(user_id)
        # 列表推导式 + 条件筛选：只保留当前年月记录
        month_records = [
            r for r in all_records
            if self._parse_record_month(r.get('date', '')) == (self._current_year, self._current_month)
        ]
        return month_records
    
    def _parse_record_month(self, date_str):
        """
        解析记录日期字符串为 (年, 月) 元组。
        
        支持 date 对象、datetime 对象和字符串格式 'YYYY-MM-DD'。
        
        :param date_str: 日期字符串或 date/datetime 对象
        :return: (year, month) 元组，解析失败返回 (0, 0)
        """
        if isinstance(date_str, date):
            return (date_str.year, date_str.month)
        if isinstance(date_str, datetime):
            return (date_str.year, date_str.month)
        try:
            dt = datetime.strptime(str(date_str), '%Y-%m-%d')
            return (dt.year, dt.month)
        except (ValueError, TypeError):
            return (0, 0)
    
    def _extract_categories(self, records):
        """
        从记录中提取所有菜品类别及其拳数。
        
        使用 collections.Counter 进行频率统计，饮料与零食合并为饮料/零食维度。
        
        :param records: 记录列表
        :return: Counter 类别 -> 总拳数
        """
        category_counts = Counter()
        for record in records:
            items = record.get('items', []) or []
            for item in items:
                cat = item.get('category', '其他')
                fist = item.get('fist_count', 0) or 0
                # 将饮料和零食合并为一个统计维度，用于营养结构评分
                if cat in ('饮料', '零食'):
                    cat = '饮料/零食'
                category_counts[cat] += fist
        return category_counts
    
    def _calculate_actual_ratio(self, category_counts):
        """
        计算各类别实际占比。
        
        使用字典推导式计算每类占比，总拳数为0时返回全0结构。
        
        :param category_counts: Counter 类别计数
        :return: dict 类别 -> 占比 (0.0 ~ 1.0)
        """
        total = sum(category_counts.values())
        if total == 0:
            # 字典推导式：无记录时返回全0占比
            return {cat: 0.0 for cat in self._IDEAL_STRUCTURE[self._DEFAULT_GOAL]}
        # 字典推导式：计算每类实际占比
        return {cat: round(count / total, 4) for cat, count in category_counts.items()}
    
    def _compute_deviation(self, actual, ideal):
        """
        计算实际与理想结构的总偏差。
        
        遍历所有类别，求实际占比与理想占比的绝对差之和。
        
        :param actual: dict 实际占比
        :param ideal: dict 理想占比
        :return: float 总偏差值 (0.0 ~ 2.0)
        """
        all_cats = set(actual.keys()) | set(ideal.keys())
        total_deviation = sum(
            abs(actual.get(cat, 0.0) - ideal.get(cat, 0.0))
            for cat in all_cats
        )
        return total_deviation
    
    def _get_user_goal(self, user_id):
        """
        获取用户健康目标。
        
        优先从数据库用户表查询，失败时返回默认值。
        
        :param user_id: 用户ID
        :return: str 目标名称 ('减肥' / '维持' / '增重')
        """
        try:
            if hasattr(self._db, 'get_user'):
                user = self._db.get_user(user_id)
                if user and isinstance(user, dict):
                    goal = user.get('health_goal', self._DEFAULT_GOAL)
                    # 统一映射：将数据库中的值转换为内部使用的简短名称
                    goal_map = {
                        '减肥': '减肥',
                        '维持身材': '维持',
                        '健身增重': '增重',
                    }
                    return goal_map.get(goal, self._DEFAULT_GOAL)
        except Exception:
            pass
        return self._DEFAULT_GOAL
    
    def _get_user_budget(self, user_id):
        """
        获取用户月度预算。
        
        优先从数据库用户表查询，失败时返回默认值。
        
        :param user_id: 用户ID
        :return: float 月度预算 (元)
        """
        try:
            if hasattr(self._db, 'get_user'):
                user = self._db.get_user(user_id)
                if user and isinstance(user, dict):
                    budget = user.get('monthly_budget', self._DEFAULT_BUDGET)
                    return float(budget) if budget is not None else self._DEFAULT_BUDGET
        except Exception:
            pass
        return self._DEFAULT_BUDGET
    
    def _generate_suggestions(self, actual, ideal, records):
        """
        根据实际与理想结构生成健康建议。
        
        比较各类别占比与理想值的偏差，结合外卖占比给出建议。
        
        :param actual: dict 实际占比
        :param ideal: dict 理想占比
        :param records: 当月记录列表
        :return: list[str] 建议文本列表
        """
        suggestions = []
        
        # 遍历各类别，检查与理想结构的偏差（阈值 0.05）
        for cat, ideal_ratio in ideal.items():
            actual_ratio = actual.get(cat, 0.0)
            if actual_ratio < ideal_ratio - 0.05:
                suggestions.append(f"{cat}摄入不足")
            elif actual_ratio > ideal_ratio + 0.05:
                suggestions.append(f"{cat}偏多")
        
        # 检查外卖占比（超过 50% 给出建议）
        if records:
            takeout_count = sum(1 for r in records if r.get('is_takeout'))
            takeout_ratio = takeout_count / len(records)
            if takeout_ratio > 0.5:
                suggestions.append("外卖占比过高")
        
        # 若无偏差建议，返回默认提示
        return suggestions if suggestions else ["饮食结构基本合理"]
    
    def _days_in_month(self, year, month):
        """
        计算指定月份的总天数。
        
        利用下个月1号与当月1号的差值计算。
        
        :param year: 年份
        :param month: 月份 (1-12)
        :return: int 该月天数
        """
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        # 两个 date 对象相减得到 timedelta，取 days 属性
        return (next_month - date(year, month, 1)).days
    
    def _format_date_key(self, record_date):
        """
        将记录日期统一格式化为 'YYYY-MM-DD' 字符串。
        
        :param record_date: date 对象或字符串
        :return: str 格式化日期
        """
        if isinstance(record_date, date):
            return record_date.strftime('%Y-%m-%d')
        return str(record_date)
    
    # ==================== 公共分析接口 ====================
    
    def nutrition_score(self, user_id):
        """
        计算用户营养结构评分。
        
        评分公式: score = max(0, 100 - 50 * total_deviation)
        其中 total_deviation = sum(|实际占比 - 理想占比|)
        
        :param user_id: 用户ID
        :return: dict 包含 score(评分), ideal(理想结构), actual(实际结构),
                     deviation(总偏差), suggestions(建议列表)
        """
        # 获取当月记录并提取类别分布
        records = self._get_month_records(user_id)
        category_counts = self._extract_categories(records)
        actual_ratio = self._calculate_actual_ratio(category_counts)
        
        # 获取用户目标并查找对应理想结构
        goal = self._get_user_goal(user_id)
        ideal_ratio = self._IDEAL_STRUCTURE.get(goal, self._IDEAL_STRUCTURE[self._DEFAULT_GOAL]).copy()
        
        # 确保实际比例中包含所有理想类别（缺失补0）
        for cat in ideal_ratio:
            if cat not in actual_ratio:
                actual_ratio[cat] = 0.0
        
        # 计算偏差与评分
        deviation = self._compute_deviation(actual_ratio, ideal_ratio)
        score = max(0, round(100 - 50 * deviation, 2))
        suggestions = self._generate_suggestions(actual_ratio, ideal_ratio, records)
        
        return {
            'score': score,
            'ideal': ideal_ratio,
            'actual': actual_ratio,
            'deviation': round(deviation, 4),
            'suggestions': suggestions,
        }
    
    def budget_analysis(self, user_id):
        """
        分析用户本月预算使用情况并预测是否超支。
        
        按当前日均消费推算月末总支出，计算剩余日均预算。
        
        :param user_id: 用户ID
        :return: dict 包含 total_spent(已用), budget(预算), remaining(剩余),
                     daily_avg(日均), predicted_end(预测月末), will_exceed(是否超支),
                     remaining_daily_budget(剩余日均预算)
        """
        records = self._get_month_records(user_id)
        
        # 使用生成器表达式计算总支出
        total_spent = sum(r.get('price', 0) or 0 for r in records)
        
        budget = self._get_user_budget(user_id)
        remaining = round(budget - total_spent, 2)
        
        # 计算本月已过天数与剩余天数
        days_passed = self._today.day
        days_in_month = self._days_in_month(self._today.year, self._today.month)
        days_remaining = days_in_month - days_passed
        
        # 日均消费（已用金额 / 已过天数）
        daily_avg = round(total_spent / days_passed, 2) if days_passed > 0 else 0.0
        
        # 预测月末总支出 = 已用 + 日均 * 剩余天数
        predicted_end = round(total_spent + daily_avg * days_remaining, 2)
        will_exceed = predicted_end > budget
        
        # 剩余日均预算 = 剩余预算 / 剩余天数
        remaining_daily_budget = round(remaining / days_remaining, 2) if days_remaining > 0 else 0.0
        
        return {
            'total_spent': round(total_spent, 2),
            'budget': budget,
            'remaining': remaining,
            'daily_avg': daily_avg,
            'predicted_end': predicted_end,
            'will_exceed': will_exceed,
            'remaining_daily_budget': remaining_daily_budget,
        }
    
    def meal_statistics(self, user_id):
        """
        统计用户本月用餐情况。
        
        统计总餐次、总支出、日均支出、餐次分布、外卖占比、常去地点。
        
        :param user_id: 用户ID
        :return: dict 包含 total_meals(总餐次), total_cost(总支出),
                     daily_avg(日均支出), meal_breakdown(餐次分布),
                     takeout_ratio(外卖占比), top_locations(常去地点TOP5)
        """
        records = self._get_month_records(user_id)
        
        total_meals = len(records)
        total_cost = round(sum(r.get('price', 0) or 0 for r in records), 2)
        daily_avg = round(total_cost / self._today.day, 2) if self._today.day > 0 else 0.0
        
        # 使用 Counter 统计各餐次支出
        meal_costs = Counter()
        for r in records:
            meal = r.get('meal', '其他')
            meal_costs[meal] += r.get('price', 0) or 0
        
        # 使用字典推导式计算餐次分布（含金额、占比、次数）
        meal_breakdown = {
            meal: {
                'cost': round(cost, 2),
                'ratio': round(cost / total_cost, 4) if total_cost > 0 else 0.0,
                'count': sum(1 for r in records if r.get('meal') == meal),
            }
            for meal, cost in meal_costs.items()
        }
        
        # 外卖占比
        takeout_count = sum(1 for r in records if r.get('is_takeout'))
        takeout_ratio = round(takeout_count / total_meals, 4) if total_meals > 0 else 0.0
        
        # 使用 Counter 统计地点频率，再用 lambda 排序取 TOP 5
        location_counter = Counter()
        for r in records:
            loc = r.get('location_name', '未知')
            location_counter[loc] += 1
        
        # lambda 函数作为排序 key，按出现次数降序排列
        top_locations = [
            {'name': loc, 'count': count}
            for loc, count in sorted(
                location_counter.items(),
                key=lambda item: item[1],
                reverse=True
            )[:5]
        ]
        
        return {
            'total_meals': total_meals,
            'total_cost': total_cost,
            'daily_avg': daily_avg,
            'meal_breakdown': meal_breakdown,
            'takeout_ratio': takeout_ratio,
            'top_locations': top_locations,
        }
    
    def daily_calorie_trend(self, user_id):
        """
        估算用户本月每日热量摄入趋势。
        
        基于每餐菜品的拳数与类别映射计算热量，按日期汇总。
        
        :param user_id: 用户ID
        :return: list[dict] 每日热量列表，每项包含 date(日期), total_calories(热量)
        """
        records = self._get_month_records(user_id)
        
        # 使用 Counter 按日期累加热量
        daily_calories = Counter()
        for r in records:
            record_date = self._format_date_key(r.get('date', ''))
            items = r.get('items', []) or []
            # 计算该记录的总热量（使用生成器表达式 + sum）
            day_cal = sum(
                self._CALORIE_MAP.get(item.get('category', '其他'), 100) * (item.get('fist_count', 0) or 0)
                for item in items
            )
            daily_calories[record_date] += day_cal
        
        # 使用 lambda 按日期字符串排序，生成趋势列表
        trend = [
            {'date': d, 'total_calories': cal}
            for d, cal in sorted(daily_calories.items(), key=lambda x: x[0])
        ]
        
        return trend


# ==================== 自测代码 ====================

def _mock_db():
    """
    创建模拟数据库实例，用于模块独立自测。
    
    :return: MockDB 实例
    """
    class MockDB:
        def get_diet_records(self, user_id):
            """
            返回模拟饮食记录。
            
            :param user_id: 用户ID
            :return: list[dict] 模拟记录
            """
            from datetime import timedelta
            today = date.today()
            yesterday = today - timedelta(days=1)
            
            # 模拟记录数据，覆盖不同餐次、地点、类别
            return [
                {
                    'id': 1,
                    'user_id': user_id,
                    'date': today.strftime('%Y-%m-%d'),
                    'meal': '午餐',
                    'location_type': '食堂',
                    'location_name': '松涛园',
                    'food_name': '红烧肉套餐',
                    'price': 15.0,
                    'is_takeout': False,
                    'created_at': datetime.now(),
                    'items': [
                        {'category': '主食', 'fist_count': 2},
                        {'category': '蔬菜', 'fist_count': 1},
                        {'category': '肉类', 'fist_count': 1},
                    ],
                },
                {
                    'id': 2,
                    'user_id': user_id,
                    'date': yesterday.strftime('%Y-%m-%d'),
                    'meal': '晚餐',
                    'location_type': '外卖',
                    'location_name': '某外卖店',
                    'food_name': '炸鸡套餐',
                    'price': 25.0,
                    'is_takeout': True,
                    'created_at': datetime.now(),
                    'items': [
                        {'category': '主食', 'fist_count': 1},
                        {'category': '肉类', 'fist_count': 2},
                        {'category': '饮料', 'fist_count': 1},
                    ],
                },
                {
                    'id': 3,
                    'user_id': user_id,
                    'date': today.strftime('%Y-%m-%d'),
                    'meal': '早餐',
                    'location_type': '食堂',
                    'location_name': '春晖园',
                    'food_name': '豆浆油条',
                    'price': 8.0,
                    'is_takeout': False,
                    'created_at': datetime.now(),
                    'items': [
                        {'category': '主食', 'fist_count': 1},
                        {'category': '水果', 'fist_count': 1},
                    ],
                },
                {
                    'id': 4,
                    'user_id': user_id,
                    'date': today.strftime('%Y-%m-%d'),
                    'meal': '加餐',
                    'location_type': '超市',
                    'location_name': '校园超市',
                    'food_name': '零食',
                    'price': 12.0,
                    'is_takeout': False,
                    'created_at': datetime.now(),
                    'items': [
                        {'category': '零食', 'fist_count': 1},
                        {'category': '饮料', 'fist_count': 1},
                    ],
                },
            ]
    
    return MockDB()


if __name__ == '__main__':
    print("=" * 50)
    print("DietAnalyzer v2 自测模块")
    print("=" * 50)
    
    db = _mock_db()
    analyzer = DietAnalyzer(db)
    
    # 测试营养评分
    print("\n【营养结构评分】")
    nutrition = analyzer.nutrition_score(1)
    print(f"  评分: {nutrition['score']}")
    print(f"  理想结构: {nutrition['ideal']}")
    print(f"  实际结构: {nutrition['actual']}")
    print(f"  总偏差: {nutrition['deviation']}")
    print(f"  建议: {nutrition['suggestions']}")
    
    # 测试预算分析
    print("\n【预算分析】")
    budget = analyzer.budget_analysis(1)
    print(f"  已用: {budget['total_spent']} 元")
    print(f"  预算: {budget['budget']} 元")
    print(f"  剩余: {budget['remaining']} 元")
    print(f"  日均: {budget['daily_avg']} 元")
    print(f"  预测月末: {budget['predicted_end']} 元")
    print(f"  是否超支: {budget['will_exceed']}")
    print(f"  剩余日均: {budget['remaining_daily_budget']} 元")
    
    # 测试用餐统计
    print("\n【用餐统计】")
    stats = analyzer.meal_statistics(1)
    print(f"  总餐次: {stats['total_meals']}")
    print(f"  总支出: {stats['total_cost']} 元")
    print(f"  日均: {stats['daily_avg']} 元")
    print(f"  餐次分布: {stats['meal_breakdown']}")
    print(f"  外卖占比: {stats['takeout_ratio']}")
    print(f"  常去地点: {stats['top_locations']}")
    
    # 测试热量趋势
    print("\n【每日热量趋势】")
    trend = analyzer.daily_calorie_trend(1)
    for day in trend:
        print(f"  {day['date']}: {day['total_calories']} kcal")
    
    print("\n" + "=" * 50)
    print("自测完成")
    print("=" * 50)
