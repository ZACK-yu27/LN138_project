# -*- coding: utf-8 -*-
"""
recommender.py - 饮食推荐模块（角色 B）

功能：实现三类推荐算法——去哪吃、什么时候吃、吃什么。
覆盖课程知识点：
  - 函数（第 6 章）：封装推荐逻辑，位置参数、默认参数、lambda 排序
  - 类与 OOP（第 8 章）：Recommender 类，属性与方法组织
  - 控制结构（第 4 章）：循环、条件筛选、推荐规则判断
  - 列表/字典（第 3、5 章）：列表推导式过滤、字典排序、推荐结果组织
  - 字符串处理（第 2 章）：f-string 格式化推荐理由
"""

from datetime import datetime, date, time
from collections import Counter

# 从 analyzer 导入共享常量，避免重复定义
from analyzer import DietAnalyzer


class Recommender:
    """
    饮食推荐器类。

    提供三类推荐功能：
      1. 去哪吃：基于预算、距离、历史偏好推荐食堂档口或门店
      2. 什么时候吃：根据当前时间判断食堂高峰期/低谷期，推荐最佳时段
      3. 吃什么：基于营养缺口、预算、健康目标推荐餐品组合

    属性：
        db_instance: DietDatabase 实例，提供数据查询能力。
        analyzer: DietAnalyzer 实例，提供营养分析能力（可选）。
    """

    # 热量映射（共享自 analyzer 模块）
    CALORIE_MAP = DietAnalyzer.CALORIE_MAP
    # 理想营养结构（共享自 analyzer 模块）
    IDEAL_STRUCTURE = DietAnalyzer.IDEAL_STRUCTURE

    def __init__(self, db_instance, analyzer=None):
        """
        初始化推荐器。

        :param db_instance: DietDatabase 实例，需实现 query_all_cafeteria、
                            query_all_shops、get_diet_records、get_user 方法。
        :param analyzer: DietAnalyzer 实例（可选），用于获取营养缺口分析。
        """
        self.db = db_instance
        self.analyzer = analyzer

    # ==================== 辅助方法 ====================

    def _get_user(self, user_id):
        """
        获取用户配置。

        :param user_id: int 用户 ID
        :return: dict 或 None，包含 username、monthly_budget、health_goal 等
        """
        try:
            if hasattr(self.db, 'get_user'):
                return self.db.get_user(user_id)
        except Exception:
            pass
        return None

    def _get_month_records(self, user_id):
        """
        获取用户当月饮食记录。

        :param user_id: int 用户 ID
        :return: list[dict] 当月记录列表
        """
        try:
            if hasattr(self.db, 'get_diet_records'):
                all_records = self.db.get_diet_records(user_id)
                today = date.today()
                return [
                    r for r in all_records
                    if self._parse_month(r.get('date')) == (today.year, today.month)
                ]
        except Exception:
            pass
        return []

    def _parse_month(self, date_value):
        """
        解析日期为 (year, month) 元组。

        :param date_value: str 'YYYY-MM-DD' 或 date 对象
        :return: tuple (year, month) 或 (0, 0)
        """
        if not date_value:
            return (0, 0)
        if isinstance(date_value, date):
            return (date_value.year, date_value.month)
        try:
            dt = datetime.strptime(str(date_value), '%Y-%m-%d')
            return (dt.year, dt.month)
        except (ValueError, TypeError):
            return (0, 0)

    def _parse_time(self, time_str):
        """
        将时间字符串解析为 time 对象。

        :param time_str: str 如 '11:45' 或 '07:30'
        :return: time 对象或 None
        """
        if not time_str:
            return None
        try:
            return datetime.strptime(str(time_str), '%H:%M').time()
        except (ValueError, TypeError):
            return None

    def _get_remaining_daily_budget(self, user_id):
        """
        计算用户剩余日均预算。

        :param user_id: int 用户 ID
        :return: float 剩余日均预算
        """
        user = self._get_user(user_id)
        if not user:
            return 50.0  # 默认 fallback
        budget = float(user.get('monthly_budget', 0) or 0)
        today = date.today()
        days_in_month = self._days_in_month(today.year, today.month)
        passed_days = today.day
        remaining_days = days_in_month - passed_days + 1  # 含今天
        # 已用金额
        records = self._get_month_records(user_id)
        spent = sum(float(r.get('price', 0) or 0) for r in records)
        remaining = budget - spent
        return round(remaining / remaining_days, 2) if remaining_days > 0 else 0.0

    def _days_in_month(self, year, month):
        """计算指定月份天数。"""
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        return (next_month - date(year, month, 1)).days

    def _get_nutrition_gap(self, user_id):
        """
        获取用户营养缺口（摄入不足的类别）。

        :param user_id: int 用户 ID
        :return: list[str] 摄入不足的类别列表
        """
        if self.analyzer and hasattr(self.analyzer, 'nutrition_score'):
            try:
                result = self.analyzer.nutrition_score(user_id)
                if 'error' in result:
                    return []
                actual = result.get('actual', {})
                ideal = result.get('ideal', {})
                gaps = []
                for cat, ideal_ratio in ideal.items():
                    actual_ratio = actual.get(cat, 0.0)
                    if actual_ratio < ideal_ratio - 0.05:
                        gaps.append(cat)
                return gaps
            except Exception:
                pass
        # 如果没有 analyzer，尝试从记录中估算
        return self._estimate_gap_from_records(user_id)

    def _estimate_gap_from_records(self, user_id):
        """
        从记录中估算营养缺口（备用方案）。

        :param user_id: int 用户 ID
        :return: list[str] 摄入不足的类别列表
        """
        records = self._get_month_records(user_id)
        user = self._get_user(user_id)
        goal = '维持'
        if user:
            goal_map = {'减肥': '减肥', '维持身材': '维持', '健身增重': '增重'}
            goal = goal_map.get(user.get('health_goal', ''), '维持')
        ideal = self.IDEAL_STRUCTURE.get(goal, self.IDEAL_STRUCTURE['维持'])

        # 统计各类别拳数
        category_counts = Counter()
        for r in records:
            for item in r.get('items', []):
                cat = item.get('category', '其他')
                fists = item.get('fist_count', 0) or 0
                if cat in ('饮料', '零食'):
                    cat = '饮料/零食'
                category_counts[cat] += fists
        total = sum(category_counts.values())
        if total == 0:
            return []
        gaps = []
        for cat, ideal_ratio in ideal.items():
            actual_ratio = category_counts.get(cat, 0) / total
            if actual_ratio < ideal_ratio - 0.05:
                gaps.append(cat)
        return gaps

    def _get_location_history(self, user_id):
        """
        获取用户历史就餐地点频次。

        :param user_id: int 用户 ID
        :return: Counter {地点名: 次数}
        """
        records = self._get_month_records(user_id)
        counter = Counter()
        for r in records:
            loc = r.get('location_name', '未知')
            if loc and loc != '未知':
                counter[loc] += 1
        return counter

    def _score_option(self, option, gaps, history, daily_budget, location_type='食堂'):
        """
        为单个推荐选项计算综合得分。

        :param option: dict 单个菜品/门店数据
        :param gaps: list[str] 营养缺口类别
        :param history: Counter 历史地点频次
        :param daily_budget: float 剩余日均预算
        :param location_type: str 地点类型
        :return: float 综合得分（越高越推荐）
        """
        score = 0.0
        price = float(option.get('price', 0) or 0)
        # 1. 预算匹配：价格越低得分越高
        if price <= daily_budget:
            score += 30 * (1 - price / daily_budget) if daily_budget > 0 else 30
        else:
            score -= 50  # 超出预算大幅扣分
        # 2. 营养缺口匹配：包含缺口类别的菜品加分
        cat = option.get('category', '')
        for gap in gaps:
            if gap in cat:
                score += 25
                break
        # 3. 历史偏好：用户常去的地点加分
        loc_name = option.get('location_name', '') or option.get('shop_name', '') or option.get('stall_name', '')
        if loc_name in history:
            score += 10 * min(history[loc_name], 5)  # 最高加50分
        # 4. 距离加分（仅校外门店）
        distance = option.get('distance_m', 0)
        if distance and float(distance) < 200:
            score += 10
        # 5. 高峰期等待时间加分（食堂）
        wait_time = option.get('avg_wait_min', 0)
        if wait_time and float(wait_time) < 8:
            score += 5
        return score

    # ==================== 公共推荐接口 ====================

    def recommend_where(self, user_id, top_n=3):
        """
        推荐去哪吃（食堂档口或校外门店）。

        综合规则：
          - 预算过滤：价格 <= 剩余日均预算
          - 营养缺口：优先推荐含缺口类别的餐品
          - 历史偏好：常去地点加分
          - 距离：门店距离越近越优先

        :param user_id: int 用户 ID
        :param top_n: int 推荐数量，默认 3
        :return: list[dict] 推荐列表，每项包含 name, location, price, category, reason
        """
        daily_budget = self._get_remaining_daily_budget(user_id)
        gaps = self._get_nutrition_gap(user_id)
        history = self._get_location_history(user_id)

        # 获取食堂和门店数据
        canteen_items = []
        shop_items = []
        try:
            if hasattr(self.db, 'query_all_cafeteria'):
                canteen_items = self.db.query_all_cafeteria()
            if hasattr(self.db, 'query_all_shops'):
                shop_items = self.db.query_all_shops()
        except Exception:
            pass

        # 合并所有选项并计算得分
        all_options = []
        for item in canteen_items:
            item['_type'] = '食堂'
            item['_location_name'] = item.get('canteen', '未知') + ' ' + item.get('stall_name', '')
            all_options.append(item)
        for item in shop_items:
            item['_type'] = '校外门店'
            item['_location_name'] = item.get('shop_name', '未知')
            all_options.append(item)

        # 计算得分并排序（lambda 作为排序 key）
        scored = []
        for opt in all_options:
            score = self._score_option(opt, gaps, history, daily_budget, opt['_type'])
            scored.append((score, opt))
        scored.sort(key=lambda x: x[0], reverse=True)

        # 生成推荐结果
        results = []
        for score, opt in scored[:top_n]:
            price = float(opt.get('price', 0) or 0)
            cat = opt.get('category', '其他')
            reasons = []
            if price <= daily_budget:
                reasons.append(f"价格{price}元在预算内")
            for gap in gaps:
                if gap in cat:
                    reasons.append(f"含{gap}，补充营养缺口")
                    break
            loc = opt['_location_name']
            if loc in history:
                reasons.append(f"去过{history[loc]}次，口碑不错")
            distance = opt.get('distance_m', 0)
            if distance and float(distance) < 200:
                reasons.append("距离近，方便到达")
            wait = opt.get('avg_wait_min', 0)
            if wait and float(wait) < 8:
                reasons.append("排队时间短")
            if not reasons:
                reasons.append("综合评分推荐")

            results.append({
                'name': opt.get('dish_name', '未知'),
                'location': loc,
                'location_type': opt['_type'],
                'price': price,
                'category': cat,
                'score': round(score, 2),
                'reason': '；'.join(reasons),
            })
        return results

    def recommend_when(self, user_id, canteen_name=None):
        """
        推荐什么时候去食堂（避开高峰期）。

        根据当前时间判断：
          - 高峰前 15 分钟内：建议"现在就去，避开高峰"
          - 高峰期内：建议"错峰，12:30 后再去"
          - 高峰期后：建议"当前为低谷期，可前往"

        :param user_id: int 用户 ID（保留用于扩展）
        :param canteen_name: str 目标食堂名称（可选）
        :return: dict 包含 suggestion, peak_info, best_time
        """
        now = datetime.now().time()
        now_hour = now.hour
        now_minute = now.minute
        now_total = now_hour * 60 + now_minute  # 当前时间转换为分钟数

        # 获取食堂高峰期数据
        canteen_items = []
        try:
            if hasattr(self.db, 'query_all_cafeteria'):
                canteen_items = self.db.query_all_cafeteria()
        except Exception:
            pass

        # 筛选目标食堂（或全部）
        target_items = canteen_items
        if canteen_name:
            target_items = [c for c in canteen_items if canteen_name in c.get('canteen', '')]

        if not target_items:
            return {
                'suggestion': '暂无食堂高峰期数据',
                'peak_info': {},
                'best_time': '11:30 前或 12:30 后',
            }

        # 取第一个匹配项的高峰期（假设同食堂高峰期一致）
        item = target_items[0]
        peak_start = self._parse_time(item.get('peak_start', ''))
        peak_end = self._parse_time(item.get('peak_end', ''))
        avg_wait = item.get('avg_wait_min', 0)

        if not peak_start or not peak_end:
            return {
                'suggestion': '该食堂未配置高峰期数据',
                'peak_info': {},
                'best_time': '随时可前往',
            }

        start_total = peak_start.hour * 60 + peak_start.minute
        end_total = peak_end.hour * 60 + peak_end.minute

        # 判断当前时间相对高峰期的位置
        if now_total < start_total - 15:
            # 高峰前 15 分钟以上
            suggestion = f"距离高峰期还有 {start_total - now_total} 分钟，建议现在前往"
            best_time = f"{peak_start.strftime('%H:%M')} 前"
        elif start_total - 15 <= now_total < start_total:
            # 高峰前 15 分钟内
            suggestion = "现在就去，刚好避开高峰"
            best_time = "立即出发"
        elif start_total <= now_total <= end_total:
            # 高峰期内
            suggestion = f"当前为高峰期，建议 {peak_end.strftime('%H:%M')} 后再去"
            best_time = f"{peak_end.strftime('%H:%M')} 后"
        else:
            # 高峰期后
            suggestion = "当前为低谷期，可前往就餐"
            best_time = "现在即可"

        return {
            'suggestion': suggestion,
            'peak_info': {
                'peak_start': item.get('peak_start', ''),
                'peak_end': item.get('peak_end', ''),
                'avg_wait_min': avg_wait,
            },
            'best_time': best_time,
        }

    def recommend_what(self, user_id, meal='午餐', top_n=3):
        """
        推荐吃什么（餐品组合）。

        综合规则：
          - 预算过滤：价格 <= 剩余日均预算
          - 营养缺口：优先推荐含缺口类别的餐品
          - 健康目标：根据目标推荐不同组合（减肥推荐低热量、增重推荐高蛋白）

        :param user_id: int 用户 ID
        :param meal: str 餐次（早餐/午餐/晚餐/加餐）
        :param top_n: int 推荐数量，默认 3
        :return: list[dict] 推荐列表，每项包含 combo_name, items, total_price, nutrition, reason
        """
        daily_budget = self._get_remaining_daily_budget(user_id)
        gaps = self._get_nutrition_gap(user_id)
        user = self._get_user(user_id)
        goal = '维持'
        if user:
            goal_map = {'减肥': '减肥', '维持身材': '维持', '健身增重': '增重'}
            goal = goal_map.get(user.get('health_goal', ''), '维持')

        # 获取所有可选餐品
        all_dishes = []
        try:
            if hasattr(self.db, 'query_all_cafeteria'):
                all_dishes.extend(self.db.query_all_cafeteria())
            if hasattr(self.db, 'query_all_shops'):
                all_dishes.extend(self.db.query_all_shops())
        except Exception:
            pass

        # 过滤预算内的选项
        affordable = [
            d for d in all_dishes
            if float(d.get('price', 0) or 0) <= daily_budget
        ]
        if not affordable:
            affordable = all_dishes  # 如果全部超预算，返回全部

        # 根据健康目标调整权重
        goal_weights = {
            '减肥': {'蔬菜': 2.0, '主食': 0.5, '肉类': 1.0},
            '维持': {'蔬菜': 1.0, '主食': 1.0, '肉类': 1.0},
            '增重': {'蔬菜': 0.5, '主食': 1.5, '肉类': 2.0},
        }
        weights = goal_weights.get(goal, goal_weights['维持'])

        # 计算每个选项的推荐得分
        scored = []
        for dish in affordable:
            score = 0.0
            cat = dish.get('category', '其他')
            price = float(dish.get('price', 0) or 0)
            # 预算内得分
            score += 20 * (1 - price / daily_budget) if daily_budget > 0 else 20
            # 营养缺口匹配
            for gap in gaps:
                if gap in cat:
                    score += 30
                    break
            # 健康目标权重
            for w_cat, w_val in weights.items():
                if w_cat in cat:
                    score += 10 * w_val
            # 热量估算（低热量适合减肥，高热量适合增重）
            est_cal = self._estimate_dish_calorie(dish)
            if goal == '减肥' and est_cal < 500:
                score += 10
            elif goal == '增重' and est_cal > 600:
                score += 10
            scored.append((score, dish))

        # 按得分排序
        scored.sort(key=lambda x: x[0], reverse=True)

        # 生成推荐组合（每个推荐包含 1-2 个餐品）
        results = []
        used = set()
        for score, dish in scored:
            if len(results) >= top_n:
                break
            dish_name = dish.get('dish_name', '')
            if dish_name in used:
                continue
            used.add(dish_name)
            price = float(dish.get('price', 0) or 0)
            cat = dish.get('category', '其他')
            est_cal = self._estimate_dish_calorie(dish)
            reasons = []
            if price <= daily_budget:
                reasons.append(f"价格{price}元在预算内")
            for gap in gaps:
                if gap in cat:
                    reasons.append(f"补充{gap}缺口")
                    break
            if goal == '减肥' and est_cal < 500:
                reasons.append("低热量，适合减肥目标")
            elif goal == '增重' and est_cal > 600:
                reasons.append("高热量，适合增重目标")
            if not reasons:
                reasons.append("综合营养搭配推荐")
            results.append({
                'combo_name': dish_name,
                'items': [dish_name],
                'total_price': price,
                'nutrition': {
                    'estimated_calorie': est_cal,
                    'category': cat,
                },
                'reason': '；'.join(reasons),
                'score': round(score, 2),
            })
        return results

    def _estimate_dish_calorie(self, dish):
        """
        估算单个菜品的热量。

        :param dish: dict 菜品数据，包含 category 和 price
        :return: int 估算热量（kcal）
        """
        cat = dish.get('category', '其他')
        # 根据类别估算一拳，再乘以系数
        kcal_per_fist = 100
        for c, kcal in self.CALORIE_MAP.items():
            if c in cat:
                kcal_per_fist = kcal
                break
        # 按价格估算分量（价格越高分量可能越大）
        price = float(dish.get('price', 0) or 0)
        fists = max(1.0, price / 10.0)  # 粗略估计
        return int(kcal_per_fist * fists)


# ==================== 自测入口 ====================

if __name__ == '__main__':
    print("=" * 60)
    print("Recommender 自测模块")
    print("=" * 60)

    # 模拟数据库（复用 analyzer 的 MockDB 风格）
    class MockDB:
        def __init__(self):
            self._users = {
                1: {'id': 1, 'username': 'test_user', 'monthly_budget': 1200.0, 'health_goal': '维持身材'},
            }
            self._records = [
                {'id': 1, 'user_id': 1, 'date': '2026-06-23', 'meal': '午餐', 'location_type': '食堂',
                 'location_name': '松涛园', 'food_name': '烧鸭饭', 'price': 15.5, 'is_takeout': 0,
                 'items': [{'category': '主食', 'fist_count': 2.0}, {'category': '肉类', 'fist_count': 1.0}]},
            ]
            self._canteen = [
                {'stall_id': 'S001', 'stall_name': '广式烧腊档', 'canteen': '学一', 'floor': '1F',
                 'dish_name': '广式烧鸭饭', 'price': 15.5, 'category': '肉类+主食',
                 'peak_start': '11:45', 'peak_end': '12:30', 'avg_wait_min': 12.0},
                {'stall_id': 'S013', 'stall_name': '轻食沙拉档', 'canteen': '松涛园', 'floor': '1F',
                 'dish_name': '鸡胸肉轻食沙拉', 'price': 22.0, 'category': '蔬菜+肉类',
                 'peak_start': '11:45', 'peak_end': '12:30', 'avg_wait_min': 6.0},
            ]
            self._shops = [
                {'shop_id': 'T001', 'shop_name': '麦当劳（新港西路店）', 'type': '快餐',
                 'dish_name': '巨无霸套餐', 'price': 35.0, 'category': '主食+肉类', 'distance_m': 300.0},
                {'shop_id': 'T005', 'shop_name': '蜜雪冰城（下渡路店）', 'type': '奶茶',
                 'dish_name': '柠檬水', 'price': 4.0, 'category': '饮料', 'distance_m': 100.0},
            ]

        def get_user(self, user_id):
            return self._users.get(user_id)

        def get_diet_records(self, user_id):
            return [r for r in self._records if r['user_id'] == user_id]

        def query_all_cafeteria(self):
            return self._canteen

        def query_all_shops(self):
            return self._shops

    db = MockDB()
    rec = Recommender(db)

    print("\n--- 1. 去哪吃推荐 ---")
    where = rec.recommend_where(1, top_n=3)
    for item in where:
        print(f"  {item['name']} @ {item['location']} ({item['location_type']})")
        print(f"    价格: {item['price']}元 | 得分: {item['score']}")
        print(f"    推荐理由: {item['reason']}")

    print("\n--- 2. 什么时候吃推荐 ---")
    when = rec.recommend_when(1, '学一')
    print(f"  建议: {when['suggestion']}")
    print(f"  最佳时间: {when['best_time']}")
    print(f"  高峰信息: {when['peak_info']}")

    print("\n--- 3. 吃什么推荐 ---")
    what = rec.recommend_what(1, meal='午餐', top_n=3)
    for item in what:
        print(f"  {item['combo_name']}")
        print(f"    价格: {item['total_price']}元 | 热量: {item['nutrition']['estimated_calorie']}kcal")
        print(f"    推荐理由: {item['reason']}")

    print("\n" + "=" * 60)
    print("自测完成")
    print("=" * 60)
