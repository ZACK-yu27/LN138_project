# -*- coding: utf-8 -*-
"""
data_loader.py - 角色 A 数据加载模块

功能：读取 3 份 CSV 文件，清洗缺失值、转换数据类型、异常捕获。
覆盖课程知识点：
  - 文件操作（第 7 章）：with open(...) 读写 CSV
  - 字符串处理（第 2 章）：strip、split、空值判断与替换
  - 列表、字典（第 3、5 章）：字典列表组织数据，enumerate 遍历
  - 异常处理（第 9 章）：try-except 捕获 FileNotFoundError、ValueError
  - 函数（第 6 章）：三个独立加载函数，模块化封装
"""

import os


def _resolve_path(file_path):
    """
    辅助函数：若路径为相对路径且不存在，则尝试从脚本所在目录解析。

    :param file_path: str 原始路径
    :return: str 解析后的绝对路径
    """
    if os.path.isabs(file_path):
        return file_path
    if os.path.exists(file_path):
        return file_path
    # 从脚本所在目录拼接
    base_dir = os.path.dirname(os.path.abspath(__file__))
    alt = os.path.join(base_dir, file_path)
    return alt if os.path.exists(alt) else file_path


def load_cafeteria_csv(file_path="data/cafeteria_data.csv"):
    """
    读取食堂 CSV 文件，清洗并返回字典列表。

    :param file_path: CSV 文件路径，默认 data/cafeteria_data.csv
    :return: list[dict] 每行一个字典，键为表头字段
    """
    file_path = _resolve_path(file_path)
    data_result = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            if not all_lines:
                print(f"警告：{file_path} 文件为空")
                return data_result

            # 第一行是表头，strip() 去除换行与空格（字符串处理）
            header = [col.strip() for col in all_lines[0].split(",")]

            for line in all_lines[1:]:
                single_line = line.strip()
                if not single_line:
                    continue
                line_data = single_line.split(",")
                row_dict = {}
                for index, key_name in enumerate(header):
                    value = line_data[index].strip() if index < len(line_data) else ""
                    # 空字符串统一替换为 "未知"，清洗脏数据
                    if value == "":
                        value = "未知"
                    # 数字字段强制转换
                    if key_name in {"price", "avg_wait_min"}:
                        try:
                            value = float(value)
                        except ValueError:
                            value = 0.0
                    row_dict[key_name] = value
                data_result.append(row_dict)
        print(f"[OK] 食堂数据读取成功，共 {len(data_result)} 条")
        return data_result

    except FileNotFoundError:
        print(f"[ERROR] 找不到文件 {file_path}，请检查 data 文件夹")
        return []
    except Exception as err:
        print(f"[ERROR] 读取食堂文件出错：{err}")
        return []


def load_shop_csv(file_path="data/nearby_shops.csv"):
    """
    读取校外门店 CSV 文件，逻辑与 load_cafeteria_csv 一致。

    :param file_path: CSV 文件路径，默认 data/nearby_shops.csv
    :return: list[dict]
    """
    file_path = _resolve_path(file_path)
    data_result = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            if not all_lines:
                print(f"[WARN] {file_path} 文件为空")
                return data_result

            header = [col.strip() for col in all_lines[0].split(",")]
            for line in all_lines[1:]:
                single_line = line.strip()
                if not single_line:
                    continue
                line_data = single_line.split(",")
                row_dict = {}
                for index, key_name in enumerate(header):
                    value = line_data[index].strip() if index < len(line_data) else ""
                    if value == "":
                        value = "未知"
                    if key_name in {"price", "distance_m"}:
                        try:
                            value = float(value)
                        except ValueError:
                            value = 0.0
                    row_dict[key_name] = value
                data_result.append(row_dict)
        print(f"[OK] 门店数据读取成功，共 {len(data_result)} 条")
        return data_result

    except FileNotFoundError:
        print(f"[ERROR] 找不到文件 {file_path}")
        return []
    except Exception as err:
        print(f"[ERROR] 读取门店文件出错：{err}")
        return []


def load_diet_sample(file_path="data/diet_records_sample.csv"):
    """
    读取用户饮食记录 CSV 文件（旧格式，单条记录含 category/fist_count）。
    注意：PRD 新 schema 已将 category/fist_count 拆分到 record_items 表，
          本函数仅用于迁移旧示例数据，新项目请使用 DietDatabase.create_diet_record。

    :param file_path: CSV 文件路径，默认 data/diet_records_sample.csv
    :return: list[dict]
    """
    file_path = _resolve_path(file_path)
    data_result = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            if not all_lines:
                print(f"[WARN] {file_path} 文件为空")
                return data_result

            header = [col.strip() for col in all_lines[0].split(",")]
            for line in all_lines[1:]:
                single_line = line.strip()
                if not single_line:
                    continue
                line_data = single_line.split(",")
                row_dict = {}
                for index, key_name in enumerate(header):
                    value = line_data[index].strip() if index < len(line_data) else ""
                    if value == "":
                        value = "未知"
                    if key_name == "price":
                        try:
                            value = float(value)
                        except ValueError:
                            value = 0.0
                    elif key_name == "fist_count":
                        try:
                            value = float(value)
                        except ValueError:
                            value = 0.0
                    elif key_name == "is_takeout":
                        try:
                            value = int(value)
                        except ValueError:
                            value = 0
                    row_dict[key_name] = value
                data_result.append(row_dict)
        print(f"[OK] 饮食记录读取成功，共 {len(data_result)} 条")
        return data_result

    except FileNotFoundError:
        print(f"[ERROR] 找不到文件 {file_path}")
        return []
    except Exception as err:
        print(f"[ERROR] 读取饮食文件出错：{err}")
        return []


def migrate_old_diet_to_db(db, data_list, user_id=1):
    """
    将旧格式饮食记录迁移到新的数据库 schema（diet_records + record_items）。

    :param db:        DietDatabase 实例
    :param data_list: 旧格式字典列表（含 category/fist_count）
    :param user_id:   关联用户 ID，默认 1
    """
    for row in data_list:
        # 解析旧格式 category 字段（可能包含 "+" 连接的多分类）
        raw_cat = row.get("category", "其他")
        raw_fist = row.get("fist_count", 0.0)
        # 将 "主食+肉类" 拆分为多条 items
        categories = [c.strip() for c in raw_cat.split("+")]
        items = [{"category": c, "fist_count": raw_fist / len(categories)}
                 for c in categories]

        db.create_diet_record(
            user_id=user_id,
            date=row.get("date", ""),
            meal=row.get("meal", "午餐"),
            location_type=row.get("location_type", "食堂"),
            location_name=row.get("location_name", "未知"),
            food_name=row.get("food_name", "未知"),
            price=row.get("price", 0.0),
            is_takeout=row.get("is_takeout", 0),
            items=items
        )
    print(f"[OK] 旧格式饮食记录迁移完成，共 {len(data_list)} 条")


# =====================================================================
# 自测入口
# =====================================================================
if __name__ == "__main__":
    print("===== 开始测试 CSV 读取 =====")
    canteen = load_cafeteria_csv()
    shop = load_shop_csv()
    diet = load_diet_sample()
    print("===== 读取测试完成 =====")
    if canteen:
        print("食堂第一条示例：", canteen[0])
    if shop:
        print("门店第一条示例：", shop[0])
    if diet:
        print("饮食记录第一条示例：", diet[0])
