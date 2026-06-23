# -*- coding: utf-8 -*-
"""
visualizer.py - 数据可视化模块（角色 C）

功能：使用 Matplotlib 绘制 4 种核心图表，保存到 output/ 目录。
覆盖课程知识点：
  - 数据分析与可视化（第 13 章）：Matplotlib 折线图、柱状图、饼图、水平条形图
  - 函数（第 6 章）：每个图表一个独立函数，模块化封装
  - 字符串处理（第 2 章）：图表标题、标签的 f-string 格式化
  - 文件操作（第 7 章）：图表图片保存到 output/ 目录
"""

import os
import matplotlib
matplotlib.use('Agg')  # 无头后端，避免服务器环境报错
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# 设置中文字体（兼容 Windows 和 Linux）
import matplotlib.font_manager as fm

def _find_chinese_font():
    """
    查找系统中可用的中文字体。

    :return: str 字体名称
    """
    # Windows 常见中文字体
    windows_fonts = ['Microsoft YaHei', 'SimHei', 'SimSun', 'FangSong']
    # Linux 常见中文字体
    linux_fonts = ['WenQuanYi Micro Hei', 'Noto Sans CJK SC', 'Droid Sans Fallback']
    all_fonts = windows_fonts + linux_fonts
    available = [f.name for f in fm.fontManager.ttflist]
    for font in all_fonts:
        if font in available:
            return font
    # 如果找不到，返回默认字体（图表可能无中文）
    return 'sans-serif'

_chinese_font = _find_chinese_font()
plt.rcParams['font.sans-serif'] = [_chinese_font, 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题


# 输出目录
OUTPUT_DIR = 'output'
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


# 配色方案（像素风友好，低饱和暖色调）
COLORS = {
    'primary': '#E07A5F',      # 珊瑚红
    'secondary': '#3D405B',    # 深蓝灰
    'accent': '#81B29A',       # 薄荷绿
    'warn': '#F2CC8F',         # 暖黄
    'bg': '#F4F1DE',          # 米白
    'text': '#2D3436',         # 深灰
    'palette': ['#E07A5F', '#3D405B', '#81B29A', '#F2CC8F', '#A8DADC', '#E29578', '#264653', '#2A9D8F'],
}


class Visualizer:
    """
    数据可视化器类。

    使用 Matplotlib 生成图表，保存为 PNG 文件供前端展示和 PDF 导出使用。
    """

    def __init__(self, output_dir=None):
        """
        初始化可视化器。

        :param output_dir: str 输出目录，默认 'output'
        """
        self.output_dir = output_dir or OUTPUT_DIR
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def _save_path(self, user_id, chart_name):
        """
        生成图表保存路径。

        :param user_id: int 用户 ID
        :param chart_name: str 图表名称
        :return: str 完整文件路径
        """
        return os.path.join(self.output_dir, f'user_{user_id}_{chart_name}.png')

    def _setup_figure(self, title, figsize=(10, 6)):
        """
        统一设置图表样式。

        :param title: str 图表标题
        :param figsize: tuple 图表尺寸
        :return: fig, ax
        """
        fig, ax = plt.subplots(figsize=figsize)
        fig.patch.set_facecolor(COLORS['bg'])
        ax.set_facecolor(COLORS['bg'])
        ax.set_title(title, fontsize=16, fontweight='bold', color=COLORS['text'], pad=15)
        ax.tick_params(colors=COLORS['text'])
        for spine in ax.spines.values():
            spine.set_color(COLORS['text'])
            spine.set_linewidth(1.5)
        return fig, ax

    def generate_all_charts(self, user_id, dashboard_data):
        """
        生成所有看板图表。

        :param user_id: int 用户 ID
        :param dashboard_data: dict 看板数据，包含 nutrition, budget, statistics, calorie_trend
        :return: dict {图表名称: 文件路径}
        """
        paths = {}
        paths['calorie_trend'] = self.plot_calorie_trend(
            user_id, dashboard_data.get('calorie_trend', [])
        )
        paths['nutrition_compare'] = self.plot_nutrition_compare(
            user_id, dashboard_data.get('nutrition', {})
        )
        paths['meal_pie'] = self.plot_meal_pie(
            user_id, dashboard_data.get('statistics', {})
        )
        paths['budget_bar'] = self.plot_budget_bar(
            user_id, dashboard_data.get('budget', {})
        )
        return paths

    def plot_calorie_trend(self, user_id, calorie_trend):
        """
        绘制每日热量趋势折线图。

        :param user_id: int 用户 ID
        :param calorie_trend: list[dict] 每项包含 'date' 和 'calories'
        :return: str 保存的文件路径
        """
        fig, ax = self._setup_figure('每日热量估算趋势', figsize=(12, 6))

        if not calorie_trend:
            ax.text(0.5, 0.5, '暂无数据', ha='center', va='center',
                    fontsize=14, color=COLORS['text'], transform=ax.transAxes)
            path = self._save_path(user_id, 'calorie_trend')
            fig.savefig(path, dpi=150, bbox_inches='tight', facecolor=COLORS['bg'])
            plt.close(fig)
            return path

        dates = [item['date'] for item in calorie_trend]
        calories = [item['calories'] for item in calorie_trend]

        # 绘制折线图
        ax.plot(dates, calories, color=COLORS['primary'], linewidth=2.5,
                marker='s', markersize=8, markerfacecolor=COLORS['accent'],
                markeredgecolor=COLORS['secondary'], markeredgewidth=1.5)

        # 填充区域
        ax.fill_between(dates, calories, alpha=0.3, color=COLORS['primary'])

        # 平均线
        avg_cal = sum(calories) / len(calories) if calories else 0
        ax.axhline(y=avg_cal, color=COLORS['secondary'], linestyle='--',
                   linewidth=1.5, label=f'平均值: {avg_cal:.0f} kcal')

        ax.set_xlabel('日期', fontsize=12, color=COLORS['text'])
        ax.set_ylabel('热量 (kcal)', fontsize=12, color=COLORS['text'])
        ax.legend(loc='upper right', framealpha=0.9)
        ax.grid(True, alpha=0.3, linestyle=':')

        # 旋转 x 轴标签
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        path = self._save_path(user_id, 'calorie_trend')
        fig.savefig(path, dpi=150, bbox_inches='tight', facecolor=COLORS['bg'])
        plt.close(fig)
        return path

    def plot_nutrition_compare(self, user_id, nutrition):
        """
        绘制营养结构对比柱状图（实际 vs 理想）。

        :param user_id: int 用户 ID
        :param nutrition: dict 包含 'ideal' 和 'actual'
        :return: str 保存的文件路径
        """
        fig, ax = self._setup_figure('营养结构对比', figsize=(10, 6))

        ideal = nutrition.get('ideal', {})
        actual = nutrition.get('actual', {})

        if not ideal or not actual:
            ax.text(0.5, 0.5, '暂无数据', ha='center', va='center',
                    fontsize=14, color=COLORS['text'], transform=ax.transAxes)
            path = self._save_path(user_id, 'nutrition_compare')
            fig.savefig(path, dpi=150, bbox_inches='tight', facecolor=COLORS['bg'])
            plt.close(fig)
            return path

        categories = list(ideal.keys())
        ideal_values = [ideal.get(cat, 0) * 100 for cat in categories]  # 转为百分比
        actual_values = [actual.get(cat, 0) * 100 for cat in categories]

        x = range(len(categories))
        width = 0.35

        bars1 = ax.bar([i - width/2 for i in x], ideal_values, width,
                       label='理想占比', color=COLORS['accent'], edgecolor=COLORS['secondary'],
                       linewidth=1.5)
        bars2 = ax.bar([i + width/2 for i in x], actual_values, width,
                       label='实际占比', color=COLORS['primary'], edgecolor=COLORS['secondary'],
                       linewidth=1.5)

        ax.set_xlabel('食物类别', fontsize=12, color=COLORS['text'])
        ax.set_ylabel('占比 (%)', fontsize=12, color=COLORS['text'])
        ax.set_xticks(x)
        ax.set_xticklabels(categories, fontsize=11)
        ax.legend(loc='upper right', framealpha=0.9)
        ax.set_ylim(0, max(max(ideal_values), max(actual_values)) * 1.2 + 5)
        ax.grid(True, axis='y', alpha=0.3, linestyle=':')

        # 添加数值标签
        for bar in bars1:
            height = bar.get_height()
            ax.annotate(f'{height:.1f}%', xy=(bar.get_x() + bar.get_width()/2, height),
                        xytext=(0, 3), textcoords='offset points', ha='center',
                        fontsize=9, color=COLORS['text'])
        for bar in bars2:
            height = bar.get_height()
            ax.annotate(f'{height:.1f}%', xy=(bar.get_x() + bar.get_width()/2, height),
                        xytext=(0, 3), textcoords='offset points', ha='center',
                        fontsize=9, color=COLORS['text'])

        plt.tight_layout()
        path = self._save_path(user_id, 'nutrition_compare')
        fig.savefig(path, dpi=150, bbox_inches='tight', facecolor=COLORS['bg'])
        plt.close(fig)
        return path

    def plot_meal_pie(self, user_id, statistics):
        """
        绘制餐次支出占比饼图。

        :param user_id: int 用户 ID
        :param statistics: dict 包含 'meal_breakdown'
        :return: str 保存的文件路径
        """
        fig, ax = self._setup_figure('餐次支出占比', figsize=(8, 8))

        meal_breakdown = statistics.get('meal_breakdown', {})

        if not meal_breakdown:
            ax.text(0.5, 0.5, '暂无数据', ha='center', va='center',
                    fontsize=14, color=COLORS['text'], transform=ax.transAxes)
            path = self._save_path(user_id, 'meal_pie')
            fig.savefig(path, dpi=150, bbox_inches='tight', facecolor=COLORS['bg'])
            plt.close(fig)
            return path

        labels = list(meal_breakdown.keys())
        sizes = [info['cost'] for info in meal_breakdown.values()]
        colors = COLORS['palette'][:len(labels)]

        # 绘制饼图
        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, colors=colors, autopct='%1.1f%%',
            startangle=90, pctdistance=0.75,
            wedgeprops={'edgecolor': COLORS['secondary'], 'linewidth': 2}
        )

        # 设置文字样式
        for text in texts:
            text.set_fontsize(12)
            text.set_color(COLORS['text'])
        for autotext in autotexts:
            autotext.set_fontsize(10)
            autotext.set_color('white')
            autotext.set_fontweight('bold')

        # 中心圆（甜甜圈效果）
        centre_circle = plt.Circle((0, 0), 0.50, fc=COLORS['bg'], ec=COLORS['secondary'], linewidth=2)
        ax.add_artist(centre_circle)
        ax.text(0, 0, '餐次\n分布', ha='center', va='center',
                fontsize=14, fontweight='bold', color=COLORS['text'])

        ax.axis('equal')
        plt.tight_layout()

        path = self._save_path(user_id, 'meal_pie')
        fig.savefig(path, dpi=150, bbox_inches='tight', facecolor=COLORS['bg'])
        plt.close(fig)
        return path

    def plot_budget_bar(self, user_id, budget):
        """
        绘制预算使用情况水平条形图。

        :param user_id: int 用户 ID
        :param budget: dict 包含 'total_spent', 'budget', 'remaining'
        :return: str 保存的文件路径
        """
        fig, ax = self._setup_figure('预算使用情况', figsize=(10, 6))

        total_spent = budget.get('total_spent', 0)
        total_budget = budget.get('budget', 0)
        remaining = budget.get('remaining', 0)

        if total_budget <= 0:
            ax.text(0.5, 0.5, '暂无预算数据', ha='center', va='center',
                    fontsize=14, color=COLORS['text'], transform=ax.transAxes)
            path = self._save_path(user_id, 'budget_bar')
            fig.savefig(path, dpi=150, bbox_inches='tight', facecolor=COLORS['bg'])
            plt.close(fig)
            return path

        # 水平条形图数据
        categories = ['已支出', '剩余预算']
        values = [total_spent, remaining]
        colors = [COLORS['primary'], COLORS['accent']]

        bars = ax.barh(categories, values, color=colors, edgecolor=COLORS['secondary'],
                       linewidth=2, height=0.6)

        ax.set_xlabel('金额 (元)', fontsize=12, color=COLORS['text'])
        ax.set_xlim(0, total_budget * 1.1)
        ax.grid(True, axis='x', alpha=0.3, linestyle=':')

        # 添加数值标签和百分比
        for i, (bar, val) in enumerate(zip(bars, values)):
            width = bar.get_width()
            pct = val / total_budget * 100 if total_budget > 0 else 0
            ax.annotate(f'{val:.1f}元 ({pct:.1f}%)',
                        xy=(width, bar.get_y() + bar.get_height()/2),
                        xytext=(5, 0), textcoords='offset points',
                        ha='left', va='center', fontsize=11, fontweight='bold',
                        color=COLORS['text'])

        # 添加预算总额参考线
        ax.axvline(x=total_budget, color=COLORS['secondary'], linestyle='--',
                   linewidth=1.5, label=f'预算上限: {total_budget:.1f}元')
        ax.legend(loc='lower right', framealpha=0.9)

        plt.tight_layout()
        path = self._save_path(user_id, 'budget_bar')
        fig.savefig(path, dpi=150, bbox_inches='tight', facecolor=COLORS['bg'])
        plt.close(fig)
        return path


# ==================== 自测入口 ====================

if __name__ == '__main__':
    print("=" * 60)
    print("Visualizer 自测模块")
    print("=" * 60)

    viz = Visualizer()

    # 模拟看板数据
    dashboard = {
        'calorie_trend': [
            {'date': '2026-06-20', 'calories': 1200},
            {'date': '2026-06-21', 'calories': 1500},
            {'date': '2026-06-22', 'calories': 1800},
            {'date': '2026-06-23', 'calories': 1350},
        ],
        'nutrition': {
            'ideal': {'主食': 0.35, '蔬菜': 0.25, '肉类': 0.20, '水果': 0.10, '饮料/零食': 0.05, '其他': 0.05},
            'actual': {'主食': 0.40, '蔬菜': 0.15, '肉类': 0.25, '水果': 0.08, '饮料/零食': 0.08, '其他': 0.04},
        },
        'statistics': {
            'meal_breakdown': {
                '早餐': {'cost': 120, 'ratio': 0.15, 'count': 10},
                '午餐': {'cost': 400, 'ratio': 0.50, 'count': 10},
                '晚餐': {'cost': 200, 'ratio': 0.25, 'count': 10},
                '加餐': {'cost': 80, 'ratio': 0.10, 'count': 5},
            },
        },
        'budget': {
            'total_spent': 800.0,
            'budget': 1200.0,
            'remaining': 400.0,
        },
    }

    print("\n正在生成图表...")
    paths = viz.generate_all_charts(1, dashboard)
    for name, path in paths.items():
        print(f"  [{name}] -> {path}")
    print("\n图表生成完成，请查看 output/ 目录")
