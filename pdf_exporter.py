# -*- coding: utf-8 -*-
"""
pdf_exporter.py - PDF 报告导出模块（角色 C）

功能：将看板数据与图表整合为多页 PDF 报告。
覆盖课程知识点：
  - 文件操作（第 7 章）：PDF 文件生成与保存
  - 函数（第 6 章）：模块化导出函数
  - 字符串处理（第 2 章）：报告标题、日期格式化
  - Matplotlib（第 13 章）：使用 PdfPages 后端生成多页 PDF
"""

import os
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.font_manager as fm


# 中文字体设置（与 visualizer.py 保持一致）
def _find_chinese_font():
    """查找系统中可用的中文字体。"""
    windows_fonts = ['Microsoft YaHei', 'SimHei', 'SimSun', 'FangSong']
    linux_fonts = ['WenQuanYi Micro Hei', 'Noto Sans CJK SC', 'Droid Sans Fallback']
    all_fonts = windows_fonts + linux_fonts
    available = [f.name for f in fm.fontManager.ttflist]
    for font in all_fonts:
        if font in available:
            return font
    return 'sans-serif'

_chinese_font = _find_chinese_font()
plt.rcParams['font.sans-serif'] = [_chinese_font, 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


# 输出目录
OUTPUT_DIR = 'output'
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


# 配色方案
COLORS = {
    'primary': '#E07A5F',
    'secondary': '#3D405B',
    'accent': '#81B29A',
    'warn': '#F2CC8F',
    'bg': '#F4F1DE',
    'text': '#2D3436',
}


class PDFExporter:
    """
    PDF 报告导出器类。

    将看板数据、图表、推荐结果整合为多页 PDF 报告。
    """

    def __init__(self, output_dir=None):
        """
        初始化导出器。

        :param output_dir: str 输出目录，默认 'output'
        """
        self.output_dir = output_dir or OUTPUT_DIR
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def export(self, user_id, dashboard_data, chart_paths=None):
        """
        导出 PDF 看板报告。

        :param user_id: int 用户 ID
        :param dashboard_data: dict 看板数据，包含 nutrition, budget, statistics, calorie_trend
        :param chart_paths: dict 图表文件路径，可选
        :return: str 生成的 PDF 文件路径
        """
        pdf_path = os.path.join(self.output_dir, f'diet_report_{user_id}.pdf')
        now = datetime.now().strftime('%Y-%m-%d %H:%M')

        with PdfPages(pdf_path) as pdf:
            # 第 1 页：报告封面
            self._draw_cover_page(pdf, user_id, now)
            # 第 2 页：统计摘要
            self._draw_summary_page(pdf, dashboard_data)
            # 第 3 页：营养分析
            self._draw_nutrition_page(pdf, dashboard_data)
            # 第 4 页：预算分析
            self._draw_budget_page(pdf, dashboard_data)
            # 第 5 页：图表页（如果提供了图表路径）
            if chart_paths:
                self._draw_charts_page(pdf, chart_paths)

        return pdf_path

    def _draw_cover_page(self, pdf, user_id, now):
        """
        绘制报告封面页。

        :param pdf: PdfPages 对象
        :param user_id: int 用户 ID
        :param now: str 当前时间字符串
        """
        fig = plt.figure(figsize=(8.27, 11.69))  # A4 尺寸
        fig.patch.set_facecolor(COLORS['bg'])

        # 标题
        fig.text(0.5, 0.75, '饮食记录 & 推荐系统',
                 ha='center', va='center', fontsize=28,
                 fontweight='bold', color=COLORS['secondary'])
        fig.text(0.5, 0.68, '数据看板报告',
                 ha='center', va='center', fontsize=20,
                 color=COLORS['primary'])

        # 分隔线
        fig.patches.extend([plt.Rectangle((0.2, 0.62), 0.6, 0.005,
                                           facecolor=COLORS['accent'], transform=fig.transFigure)])

        # 信息
        fig.text(0.5, 0.55, f'用户 ID: {user_id}',
                 ha='center', va='center', fontsize=14, color=COLORS['text'])
        fig.text(0.5, 0.50, f'生成时间: {now}',
                 ha='center', va='center', fontsize=12, color=COLORS['text'])
        fig.text(0.5, 0.45, '中山大学《程序设计IV（实验）》期末项目',
                 ha='center', va='center', fontsize=12, color=COLORS['text'])

        # 底部装饰
        fig.text(0.5, 0.15, '本报告由系统自动生成，仅供参考',
                 ha='center', va='center', fontsize=10, color='gray')

        pdf.savefig(fig, facecolor=COLORS['bg'])
        plt.close(fig)

    def _draw_summary_page(self, pdf, dashboard_data):
        """
        绘制统计摘要页。

        :param pdf: PdfPages 对象
        :param dashboard_data: dict 看板数据
        """
        fig = plt.figure(figsize=(8.27, 11.69))
        fig.patch.set_facecolor(COLORS['bg'])

        statistics = dashboard_data.get('statistics', {})
        nutrition = dashboard_data.get('nutrition', {})
        budget = dashboard_data.get('budget', {})

        fig.text(0.5, 0.92, '一、统计摘要',
                 ha='center', va='center', fontsize=20,
                 fontweight='bold', color=COLORS['secondary'])

        y_pos = 0.85
        line_height = 0.06

        # 饮食统计
        total_meals = statistics.get('total_meals', 0)
        total_cost = statistics.get('total_cost', 0)
        daily_avg = statistics.get('daily_avg', 0)
        takeout_ratio = statistics.get('takeout_ratio', 0)

        fig.text(0.15, y_pos, f'本月总餐次: {total_meals} 次',
                 fontsize=14, color=COLORS['text'])
        y_pos -= line_height
        fig.text(0.15, y_pos, f'本月总支出: {total_cost:.2f} 元',
                 fontsize=14, color=COLORS['text'])
        y_pos -= line_height
        fig.text(0.15, y_pos, f'日均支出: {daily_avg:.2f} 元',
                 fontsize=14, color=COLORS['text'])
        y_pos -= line_height
        fig.text(0.15, y_pos, f'外卖占比: {takeout_ratio*100:.1f}%',
                 fontsize=14, color=COLORS['text'])
        y_pos -= line_height * 1.5

        # 营养评分
        score = nutrition.get('score', 0)
        fig.text(0.15, y_pos, f'营养结构评分: {score} 分',
                 fontsize=14, color=COLORS['text'], fontweight='bold')
        y_pos -= line_height
        suggestions = nutrition.get('suggestions', [])
        if suggestions:
            fig.text(0.15, y_pos, '健康建议:',
                     fontsize=14, color=COLORS['text'])
            y_pos -= line_height
            for s in suggestions[:5]:
                fig.text(0.20, y_pos, f'  - {s}',
                         fontsize=12, color=COLORS['text'])
                y_pos -= line_height * 0.8

        y_pos -= line_height * 1.5

        # 预算概况
        total_spent = budget.get('total_spent', 0)
        remaining = budget.get('remaining', 0)
        will_exceed = budget.get('will_exceed', False)
        fig.text(0.15, y_pos, f'预算已用: {total_spent:.2f} 元',
                 fontsize=14, color=COLORS['text'])
        y_pos -= line_height
        fig.text(0.15, y_pos, f'预算剩余: {remaining:.2f} 元',
                 fontsize=14, color=COLORS['text'])
        y_pos -= line_height
        exceed_text = '预计超支' if will_exceed else '预计不会超支'
        fig.text(0.15, y_pos, f'超支预测: {exceed_text}',
                 fontsize=14, color=COLORS['warn'] if will_exceed else COLORS['accent'])

        pdf.savefig(fig, facecolor=COLORS['bg'])
        plt.close(fig)

    def _draw_nutrition_page(self, pdf, dashboard_data):
        """
        绘制营养分析页。

        :param pdf: PdfPages 对象
        :param dashboard_data: dict 看板数据
        """
        fig = plt.figure(figsize=(8.27, 11.69))
        fig.patch.set_facecolor(COLORS['bg'])

        nutrition = dashboard_data.get('nutrition', {})
        ideal = nutrition.get('ideal', {})
        actual = nutrition.get('actual', {})
        deviation = nutrition.get('deviation', {})
        score = nutrition.get('score', 0)

        fig.text(0.5, 0.92, '二、营养结构分析',
                 ha='center', va='center', fontsize=20,
                 fontweight='bold', color=COLORS['secondary'])

        fig.text(0.5, 0.87, f'综合评分: {score} 分',
                 ha='center', va='center', fontsize=16,
                 color=COLORS['primary'], fontweight='bold')

        # 绘制表格
        ax = fig.add_axes([0.15, 0.45, 0.70, 0.35])
        ax.axis('off')
        ax.set_facecolor(COLORS['bg'])

        categories = list(ideal.keys()) if ideal else []
        if categories:
            table_data = []
            for cat in categories:
                ideal_v = ideal.get(cat, 0)
                actual_v = actual.get(cat, 0)
                dev_v = deviation.get(cat, 0)
                table_data.append([
                    cat,
                    f'{ideal_v*100:.1f}%',
                    f'{actual_v*100:.1f}%',
                    f'{dev_v*100:.1f}%',
                ])

            table = ax.table(
                cellText=table_data,
                colLabels=['类别', '理想占比', '实际占比', '偏差'],
                loc='center',
                cellLoc='center',
            )
            table.auto_set_font_size(False)
            table.set_fontsize(12)
            table.scale(1, 2.5)

            # 设置表头样式
            for i in range(4):
                cell = table[(0, i)]
                cell.set_facecolor(COLORS['accent'])
                cell.set_text_props(color='white', fontweight='bold')

            # 设置数据行样式
            for i in range(1, len(table_data) + 1):
                for j in range(4):
                    cell = table[(i, j)]
                    cell.set_facecolor(COLORS['bg'])
                    cell.set_edgecolor(COLORS['secondary'])

        # 健康建议
        y_pos = 0.35
        suggestions = nutrition.get('suggestions', [])
        if suggestions:
            fig.text(0.15, y_pos, '健康建议:',
                     fontsize=14, color=COLORS['text'], fontweight='bold')
            y_pos -= 0.05
            for s in suggestions:
                fig.text(0.20, y_pos, f'  {s}',
                         fontsize=12, color=COLORS['text'])
                y_pos -= 0.04

        pdf.savefig(fig, facecolor=COLORS['bg'])
        plt.close(fig)

    def _draw_budget_page(self, pdf, dashboard_data):
        """
        绘制预算分析页。

        :param pdf: PdfPages 对象
        :param dashboard_data: dict 看板数据
        """
        fig = plt.figure(figsize=(8.27, 11.69))
        fig.patch.set_facecolor(COLORS['bg'])

        budget = dashboard_data.get('budget', {})
        total_spent = budget.get('total_spent', 0)
        total_budget = budget.get('budget', 0)
        remaining = budget.get('remaining', 0)
        daily_avg = budget.get('daily_avg', 0)
        predicted_end = budget.get('predicted_end', 0)
        will_exceed = budget.get('will_exceed', False)
        remaining_daily = budget.get('remaining_daily', 0)

        fig.text(0.5, 0.92, '三、预算控制分析',
                 ha='center', va='center', fontsize=20,
                 fontweight='bold', color=COLORS['secondary'])

        y_pos = 0.85
        line_height = 0.06

        fig.text(0.15, y_pos, f'月度预算: {total_budget:.2f} 元',
                 fontsize=14, color=COLORS['text'])
        y_pos -= line_height
        fig.text(0.15, y_pos, f'已用金额: {total_spent:.2f} 元',
                 fontsize=14, color=COLORS['text'])
        y_pos -= line_height
        fig.text(0.15, y_pos, f'剩余金额: {remaining:.2f} 元',
                 fontsize=14, color=COLORS['text'])
        y_pos -= line_height
        fig.text(0.15, y_pos, f'日均消费: {daily_avg:.2f} 元',
                 fontsize=14, color=COLORS['text'])
        y_pos -= line_height
        fig.text(0.15, y_pos, f'预测月末: {predicted_end:.2f} 元',
                 fontsize=14, color=COLORS['warn'] if will_exceed else COLORS['text'])
        y_pos -= line_height
        fig.text(0.15, y_pos, f'剩余日均预算: {remaining_daily:.2f} 元',
                 fontsize=14, color=COLORS['text'])
        y_pos -= line_height * 1.5

        exceed_text = '⚠ 注意：按当前消费趋势，本月预计会超支' if will_exceed else '✓ 按当前消费趋势，本月预计不会超支'
        fig.text(0.15, y_pos, exceed_text,
                 fontsize=14, color=COLORS['warn'] if will_exceed else COLORS['accent'],
                 fontweight='bold')

        # 绘制进度条
        if total_budget > 0:
            ax = fig.add_axes([0.15, 0.25, 0.70, 0.05])
            ax.set_xlim(0, total_budget)
            ax.set_ylim(0, 1)
            ax.barh(0.5, total_spent, height=0.6, color=COLORS['primary'], edgecolor=COLORS['secondary'])
            ax.barh(0.5, remaining, left=total_spent, height=0.6, color=COLORS['accent'], edgecolor=COLORS['secondary'])
            ax.axvline(x=total_budget, color=COLORS['secondary'], linestyle='--', linewidth=2)
            ax.text(total_spent / 2, 0.5, f'已用 {total_spent:.0f}',
                    ha='center', va='center', fontsize=10, color='white', fontweight='bold')
            ax.text(total_spent + remaining / 2, 0.5, f'剩余 {remaining:.0f}',
                    ha='center', va='center', fontsize=10, color='white', fontweight='bold')
            ax.set_yticks([])
            ax.set_xticks([0, total_budget])
            ax.set_xticklabels(['0', f'{total_budget:.0f}'])
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_visible(False)

        pdf.savefig(fig, facecolor=COLORS['bg'])
        plt.close(fig)

    def _draw_charts_page(self, pdf, chart_paths):
        """
        绘制图表页（嵌入已生成的 PNG 图表）。

        :param pdf: PdfPages 对象
        :param chart_paths: dict 图表文件路径
        """
        from matplotlib.image import imread

        for name, path in chart_paths.items():
            if not os.path.exists(path):
                continue
            try:
                img = imread(path)
                fig = plt.figure(figsize=(8.27, 11.69))
                fig.patch.set_facecolor(COLORS['bg'])
                ax = fig.add_axes([0.05, 0.05, 0.90, 0.90])
                ax.imshow(img)
                ax.axis('off')
                pdf.savefig(fig, facecolor=COLORS['bg'])
                plt.close(fig)
            except Exception as e:
                print(f'[WARN] 嵌入图表 {name} 失败: {e}')


# ==================== 自测入口 ====================

if __name__ == '__main__':
    print("=" * 60)
    print("PDFExporter 自测模块")
    print("=" * 60)

    exporter = PDFExporter()

    dashboard = {
        'nutrition': {
            'score': 78,
            'ideal': {'主食': 0.35, '蔬菜': 0.25, '肉类': 0.20, '水果': 0.10, '饮料/零食': 0.05, '其他': 0.05},
            'actual': {'主食': 0.40, '蔬菜': 0.15, '肉类': 0.25, '水果': 0.08, '饮料/零食': 0.08, '其他': 0.04},
            'deviation': {'主食': 0.05, '蔬菜': 0.10, '肉类': 0.05, '水果': 0.02, '饮料/零食': 0.03, '其他': 0.01},
            'suggestions': ['蔬菜摄入不足，建议适当增加', '主食偏多，建议适量减少'],
        },
        'budget': {
            'total_spent': 800.0,
            'budget': 1200.0,
            'remaining': 400.0,
            'daily_avg': 34.78,
            'predicted_end': 1043.0,
            'will_exceed': False,
            'remaining_daily': 22.22,
        },
        'statistics': {
            'total_meals': 23,
            'total_cost': 800.0,
            'daily_avg': 34.78,
            'takeout_ratio': 0.13,
            'meal_breakdown': {
                '早餐': {'cost': 120, 'ratio': 0.15, 'count': 10},
                '午餐': {'cost': 400, 'ratio': 0.50, 'count': 10},
                '晚餐': {'cost': 200, 'ratio': 0.25, 'count': 10},
                '加餐': {'cost': 80, 'ratio': 0.10, 'count': 5},
            },
        },
        'calorie_trend': [
            {'date': '2026-06-20', 'calories': 1200},
            {'date': '2026-06-21', 'calories': 1500},
            {'date': '2026-06-22', 'calories': 1800},
            {'date': '2026-06-23', 'calories': 1350},
        ],
    }

    print("\n正在生成 PDF 报告...")
    path = exporter.export(1, dashboard)
    print(f"PDF 报告已生成: {path}")
