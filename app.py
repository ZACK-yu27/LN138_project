# -*- coding: utf-8 -*-
"""
app.py - Flask 后端入口（角色 B）

功能：注册所有 API 路由，提供 RESTful 接口供前端调用。
覆盖课程知识点：
  - 函数（第 6 章）：路由处理函数封装
  - 类与 OOP（第 8 章）：Flask 应用对象、蓝图思维
  - 控制结构（第 4 章）：请求参数校验、异常处理
  - 列表/字典（第 3、5 章）：请求/响应数据的字典组织
  - 字符串处理（第 2 章）：URL 参数解析、JSON 响应格式化
  - 异常处理（第 9 章）：try-except 捕获数据库/API 异常
"""

import os
import sys
from datetime import date

from flask import Flask, request, jsonify, send_from_directory, render_template

# =====================================================================
# 导入项目模块
# =====================================================================
from db import DietDatabase
from analyzer import DietAnalyzer
from recommender import Recommender

# visualizer 和 pdf_exporter 可能尚未创建，使用动态导入
_visualizer = None
_pdf_exporter = None

try:
    from visualizer import Visualizer
    _visualizer = Visualizer
except ImportError:
    pass

try:
    from pdf_exporter import PDFExporter
    _pdf_exporter = PDFExporter
except ImportError:
    pass


# =====================================================================
# Flask 应用初始化
# =====================================================================
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # 支持中文 JSON 输出

# 数据库实例（全局单例，避免重复连接）
DB_PATH = os.environ.get('DB_PATH', 'diet_db.sqlite')
db = DietDatabase(DB_PATH)
analyzer = DietAnalyzer(db)
recommender = Recommender(db, analyzer)


# =====================================================================
# 辅助函数
# =====================================================================

def _json_response(data, status_code=200):
    """
    统一 JSON 响应格式。

    :param data: dict 响应数据
    :param status_code: int HTTP 状态码
    :return: flask.Response
    """
    response = jsonify(data)
    response.status_code = status_code
    return response


def _error_response(message, status_code=400):
    """
    统一错误响应格式。

    :param message: str 错误信息
    :param status_code: int HTTP 状态码
    :return: flask.Response
    """
    return _json_response({'success': False, 'error': message}, status_code)


def _parse_record_items(items_data):
    """
    解析前端传入的 record_items 数据。

    :param items_data: list[dict] 或 dict
    :return: list[dict] 每项为 {"category": str, "fist_count": float}
    """
    if not items_data:
        return []
    if isinstance(items_data, dict):
        items_data = [items_data]
    parsed = []
    for item in items_data:
        if isinstance(item, dict):
            parsed.append({
                'category': str(item.get('category', '其他')),
                'fist_count': float(item.get('fist_count', 0) or 0),
            })
    return parsed


# =====================================================================
# 页面路由（前端入口）
# =====================================================================

@app.route('/')
def index_page():
    """信息录入页（首页）。"""
    return render_template('index.html')


@app.route('/record')
def record_page():
    """饮食记录页。"""
    return render_template('record.html')


@app.route('/dashboard')
def dashboard_page():
    """数据看板页。"""
    return render_template('dashboard.html')


@app.route('/recommend')
def recommend_page():
    """推荐页。"""
    return render_template('recommend.html')


# =====================================================================
# API 路由：用户管理
# =====================================================================

@app.route('/api/user', methods=['POST'])
def create_user():
    """
    创建用户配置。

    请求体 JSON：
        {
            "username": str,
            "monthly_budget": float,
            "health_goal": str ("减肥"/"维持身材"/"健身增重"),
            "preferences": list[str] (可选)
        }

    返回：
        {"success": True, "user_id": int, "user": dict}
    """
    try:
        data = request.get_json() or {}
        username = data.get('username', '').strip()
        if not username:
            return _error_response('用户名不能为空')
        # 若用户名已存在，给出友好提示，避免暴露数据库唯一约束异常
        if db.get_user_by_name(username):
            return _error_response('用户名已存在，请直接登录')
        monthly_budget = float(data.get('monthly_budget', 0))
        health_goal = data.get('health_goal', '维持身材')
        preferences = data.get('preferences')
        # 将 preferences 列表转为 JSON 字符串
        import json
        preferences_str = json.dumps(preferences, ensure_ascii=False) if preferences else None
        user_id = db.create_user(username, monthly_budget, health_goal, preferences_str)
        user = db.get_user(user_id)
        return _json_response({'success': True, 'user_id': user_id, 'user': user})
    except Exception as e:
        return _error_response(f'创建用户失败: {str(e)}', 500)


@app.route('/api/login', methods=['POST'])
def login():
    """
    用户登录（根据用户名查询）。

    请求体 JSON：
        {"username": str}

    返回：
        {"success": True, "user": dict}
    """
    try:
        data = request.get_json() or {}
        username = data.get('username', '').strip()
        if not username:
            return _error_response('用户名不能为空')
        user = db.get_user_by_name(username)
        if not user:
            return _error_response('用户不存在，请先注册', 404)
        return _json_response({'success': True, 'user': user})
    except Exception as e:
        return _error_response(f'登录失败: {str(e)}', 500)


@app.route('/api/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """
    获取用户配置。

    返回：
        {"success": True, "user": dict}
    """
    try:
        user = db.get_user(user_id)
        if not user:
            return _error_response('用户不存在', 404)
        return _json_response({'success': True, 'user': user})
    except Exception as e:
        return _error_response(f'获取用户失败: {str(e)}', 500)


@app.route('/api/user/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """
    更新用户配置。

    请求体 JSON（可选字段）：
        {"username": str, "monthly_budget": float, "health_goal": str, "preferences": list[str]}

    返回：
        {"success": True, "user": dict}
    """
    try:
        data = request.get_json() or {}
        updates = {}
        if 'username' in data:
            updates['username'] = data['username'].strip()
        if 'monthly_budget' in data:
            updates['monthly_budget'] = float(data['monthly_budget'])
        if 'health_goal' in data:
            updates['health_goal'] = data['health_goal']
        if 'preferences' in data:
            import json
            updates['preferences'] = json.dumps(data['preferences'], ensure_ascii=False)
        if not updates:
            return _error_response('没有可更新的字段')
        ok = db.update_user(user_id, **updates)
        if not ok:
            return _error_response('更新失败，用户可能不存在', 404)
        user = db.get_user(user_id)
        return _json_response({'success': True, 'user': user})
    except Exception as e:
        return _error_response(f'更新用户失败: {str(e)}', 500)


# =====================================================================
# API 路由：饮食记录
# =====================================================================

@app.route('/api/records', methods=['GET'])
def get_records():
    """
    获取饮食记录列表。

    查询参数（可选）：
        user_id: int
        date: str 'YYYY-MM-DD'
        meal: str '早餐'/'午餐'/'晚餐'/'加餐'

    返回：
        {"success": True, "records": list[dict]}
    """
    try:
        user_id = request.args.get('user_id', type=int)
        if not user_id:
            return _error_response('缺少 user_id 参数')
        record_date = request.args.get('date')
        meal = request.args.get('meal')
        records = db.get_diet_records(user_id, date=record_date, meal=meal)
        return _json_response({'success': True, 'records': records})
    except Exception as e:
        return _error_response(f'获取记录失败: {str(e)}', 500)


@app.route('/api/records', methods=['POST'])
def create_record():
    """
    新增饮食记录。

    请求体 JSON：
        {
            "user_id": int,
            "date": str "YYYY-MM-DD",
            "meal": str "早餐"/"午餐"/"晚餐"/"加餐",
            "location_type": str "食堂"/"外卖"/"校外门店"/"便利店",
            "location_name": str,
            "food_name": str,
            "price": float,
            "is_takeout": int 0/1,
            "items": [{"category": str, "fist_count": float}, ...]
        }

    返回：
        {"success": True, "record_id": int, "record": dict}
    """
    try:
        data = request.get_json() or {}
        user_id = int(data.get('user_id', 0))
        if not user_id:
            return _error_response('缺少 user_id')
        record_date = data.get('date', date.today().isoformat())
        meal = data.get('meal', '午餐')
        location_type = data.get('location_type', '食堂')
        location_name = data.get('location_name', '')
        food_name = data.get('food_name', '')
        if not food_name:
            return _error_response('食物名称不能为空')
        price = float(data.get('price', 0) or 0)
        is_takeout = int(data.get('is_takeout', 0))
        items = _parse_record_items(data.get('items'))
        record_id = db.create_diet_record(
            user_id, record_date, meal, location_type, location_name,
            food_name, price, is_takeout, items
        )
        # 重新查询获取完整记录
        records = db.get_diet_records(user_id, date=record_date)
        record = None
        for r in records:
            if r['id'] == record_id:
                record = r
                break
        return _json_response({'success': True, 'record_id': record_id, 'record': record})
    except Exception as e:
        return _error_response(f'创建记录失败: {str(e)}', 500)


@app.route('/api/records/<int:record_id>', methods=['PUT'])
def update_record(record_id):
    """
    更新饮食记录。

    请求体 JSON（可选字段）：
        {"date": str, "meal": str, "location_type": str, "location_name": str,
         "food_name": str, "price": float, "is_takeout": int}

    返回：
        {"success": True}
    """
    try:
        data = request.get_json() or {}
        updates = {}
        for key in ['date', 'meal', 'location_type', 'location_name', 'food_name']:
            if key in data:
                updates[key] = data[key]
        if 'price' in data:
            updates['price'] = float(data['price'])
        if 'is_takeout' in data:
            updates['is_takeout'] = int(data['is_takeout'])
        if not updates:
            return _error_response('没有可更新的字段')
        ok = db.update_diet_record(record_id, **updates)
        if not ok:
            return _error_response('更新失败，记录可能不存在', 404)
        return _json_response({'success': True})
    except Exception as e:
        return _error_response(f'更新记录失败: {str(e)}', 500)


@app.route('/api/records/<int:record_id>', methods=['DELETE'])
def delete_record(record_id):
    """
    删除饮食记录。

    返回：
        {"success": True}
    """
    try:
        ok = db.delete_diet_record(record_id)
        if not ok:
            return _error_response('删除失败，记录可能不存在', 404)
        return _json_response({'success': True})
    except Exception as e:
        return _error_response(f'删除记录失败: {str(e)}', 500)


# =====================================================================
# API 路由：分析与看板
# =====================================================================

@app.route('/api/dashboard/<int:user_id>', methods=['GET'])
def get_dashboard(user_id):
    """
    获取看板数据聚合。
    同时自动生成最新图表，确保前端加载到最新数据。

    返回：
        {
            "success": True,
            "nutrition": dict,
            "budget": dict,
            "statistics": dict,
            "calorie_trend": list
        }
    """
    try:
        nutrition = analyzer.nutrition_score(user_id)
        budget = analyzer.budget_analysis(user_id)
        statistics = analyzer.meal_statistics(user_id)
        calorie_trend = analyzer.daily_calorie_trend(user_id)

        # 自动生成最新图表（实时渲染，确保数据最新）
        dashboard_data = {
            'nutrition': nutrition,
            'budget': budget,
            'statistics': statistics,
            'calorie_trend': calorie_trend,
        }
        if _visualizer:
            try:
                viz = _visualizer()
                viz.generate_all_charts(user_id, dashboard_data)
            except Exception:
                pass  # 图表生成失败不影响看板数据返回

        return _json_response({
            'success': True,
            'nutrition': nutrition,
            'budget': budget,
            'statistics': statistics,
            'calorie_trend': calorie_trend,
        })
    except Exception as e:
        return _error_response(f'获取看板数据失败: {str(e)}', 500)


@app.route('/api/nutrition/<int:user_id>', methods=['GET'])
def get_nutrition(user_id):
    """
    获取营养评分。

    返回：
        {"success": True, "nutrition": dict}
    """
    try:
        nutrition = analyzer.nutrition_score(user_id)
        return _json_response({'success': True, 'nutrition': nutrition})
    except Exception as e:
        return _error_response(f'获取营养评分失败: {str(e)}', 500)


@app.route('/api/budget/<int:user_id>', methods=['GET'])
def get_budget(user_id):
    """
    获取预算分析。

    返回：
        {"success": True, "budget": dict}
    """
    try:
        budget = analyzer.budget_analysis(user_id)
        return _json_response({'success': True, 'budget': budget})
    except Exception as e:
        return _error_response(f'获取预算分析失败: {str(e)}', 500)


# =====================================================================
# API 路由：推荐
# =====================================================================

@app.route('/api/recommend/<int:user_id>', methods=['GET'])
def get_recommend(user_id):
    """
    获取推荐结果。

    查询参数（可选）：
        meal: str '早餐'/'午餐'/'晚餐'/'加餐'
        canteen: str 目标食堂名称

    返回：
        {
            "success": True,
            "where": list,      # 去哪吃
            "when": dict,       # 什么时候吃
            "what": list        # 吃什么
        }
    """
    try:
        meal = request.args.get('meal', '午餐')
        canteen = request.args.get('canteen')
        where = recommender.recommend_where(user_id, top_n=3)
        when = recommender.recommend_when(user_id, canteen)
        what = recommender.recommend_what(user_id, meal=meal, top_n=3)
        return _json_response({
            'success': True,
            'where': where,
            'when': when,
            'what': what,
        })
    except Exception as e:
        return _error_response(f'获取推荐失败: {str(e)}', 500)


# =====================================================================
# API 路由：导出
# =====================================================================

@app.route('/api/export/<int:user_id>', methods=['GET'])
def export_pdf(user_id):
    """
    导出 PDF 看板报告。

    返回：PDF 文件下载
    """
    try:
        if not _pdf_exporter:
            return _error_response('PDF 导出模块未加载', 503)
        # 生成看板数据
        dashboard_data = {
            'nutrition': analyzer.nutrition_score(user_id),
            'budget': analyzer.budget_analysis(user_id),
            'statistics': analyzer.meal_statistics(user_id),
            'calorie_trend': analyzer.daily_calorie_trend(user_id),
        }
        # 生成图表（如果 visualizer 已加载）
        chart_paths = {}
        if _visualizer:
            viz = _visualizer()
            chart_paths = viz.generate_all_charts(user_id, dashboard_data)
        # 生成 PDF
        exporter = _pdf_exporter()
        pdf_path = exporter.export(user_id, dashboard_data, chart_paths)
        if not os.path.exists(pdf_path):
            return _error_response('PDF 生成失败', 500)
        return send_from_directory(
            os.path.dirname(pdf_path),
            os.path.basename(pdf_path),
            as_attachment=True,
            download_name=f'diet_report_{user_id}.pdf'
        )
    except Exception as e:
        return _error_response(f'导出 PDF 失败: {str(e)}', 500)


# =====================================================================
# 静态文件服务（开发环境）
# =====================================================================

@app.route('/static/<path:filename>')
def serve_static(filename):
    """提供静态文件服务。"""
    return send_from_directory('static', filename)


# =====================================================================
# 错误处理
# =====================================================================

@app.errorhandler(404)
def not_found(e):
    """404 错误处理。"""
    return _error_response('接口不存在', 404)


@app.errorhandler(500)
def internal_error(e):
    """500 错误处理。"""
    return _error_response('服务器内部错误', 500)


# =====================================================================
# 启动入口
# =====================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("饮食记录 & 推荐系统 - Flask 后端")
    print("访问 http://127.0.0.1:5001")
    print("=" * 60)
    app.run(debug=False, host='127.0.0.1', port=5001, use_reloader=False, threaded=False)
