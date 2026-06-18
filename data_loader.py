# data_loader.py
"""
角色A专属数据加载模块
功能：读取3份CSV，清洗缺失值、转换数据类型、异常捕获
覆盖知识点：文件操作、字符串处理、列表字典、异常处理、函数封装
"""
import os

def load_cafeteria_csv(file_path: str = "data/cafeteria_data.csv") -> list[dict]:
    """
    读取食堂CSV文件，清洗并返回字典列表
    :param file_path: CSV文件路径，默认data下食堂文件
    :return: 列表，每个元素是一行数据的字典
    """
    # 存储最终所有数据
    data_result = []
    try:
        # with open自动关闭文件，课程文件操作知识点
        with open(file_path, "r", encoding="utf-8") as f:
            # 读取全部行
            all_lines = f.readlines()
            # 判断文件为空
            if len(all_lines) == 0:
                print(f"警告：{file_path} 文件为空")
                return data_result
            # 第一行是表头，strip()去除换行空格（字符串处理）
            header = [col.strip() for col in all_lines[0].split(",")]
            # 循环遍历每一条数据，跳过表头
            for line in all_lines[1:]:
                # 清除每行首尾换行、空格
                single_line = line.strip()
                # 空行直接跳过
                if not single_line:
                    continue
                # 按逗号分割一行所有字段
                line_data = single_line.split(",")
                row_dict = {}
                # 表头和当前行一一对应，存入字典
                for index, key_name in enumerate(header):
                    value = line_data[index].strip()
                    # 空字符串统一替换为"未知"，清洗脏数据
                    if value == "":
                        value = "未知"
                    # 数字字段强制转换浮点型
                    if key_name in ["price", "avg_wait_min"]:
                        try:
                            value = float(value)
                        except:
                            value = 0.0
                    row_dict[key_name] = value
                data_result.append(row_dict)
        print(f"✅ 食堂数据读取成功，共{len(data_result)}条")
        return data_result
    # 文件不存在捕获
    except FileNotFoundError:
        print(f"❌ 错误：找不到文件 {file_path}，检查data文件夹")
        return []
    # 其他全部异常统一捕获
    except Exception as err:
        print(f"❌ 读取食堂文件出错：{str(err)}")
        return []


def load_shop_csv(file_path: str = "data/nearby_shops.csv") -> list[dict]:
    """读取校外门店CSV，逻辑和食堂一致"""
    data_result = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            if len(all_lines) == 0:
                print(f"警告：{file_path} 文件为空")
                return data_result
            header = [col.strip() for col in all_lines[0].split(",")]
            for line in all_lines[1:]:
                single_line = line.strip()
                if not single_line:
                    continue
                line_data = single_line.split(",")
                row_dict = {}
                for index, key_name in enumerate(header):
                    value = line_data[index].strip()
                    if value == "":
                        value = "未知"
                    # 价格、距离转为数字
                    if key_name in ["price", "distance_m"]:
                        try:
                            value = float(value)
                        except:
                            value = 0.0
                    row_dict[key_name] = value
                data_result.append(row_dict)
        print(f"✅ 门店数据读取成功，共{len(data_result)}条")
        return data_result
    except FileNotFoundError:
        print(f"❌ 错误：找不到文件 {file_path}")
        return []
    except Exception as err:
        print(f"❌ 读取门店文件出错：{str(err)}")
        return []


def load_diet_sample(file_path: str = "data/diet_records_sample.csv") -> list[dict]:
    """读取用户饮食记录CSV"""
    data_result = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            if len(all_lines) == 0:
                print(f"警告：{file_path} 文件为空")
                return data_result
            header = [col.strip() for col in all_lines[0].split(",")]
            for line in all_lines[1:]:
                single_line = line.strip()
                if not single_line:
                    continue
                line_data = single_line.split(",")
                row_dict = {}
                for index, key_name in enumerate(header):
                    value = line_data[index].strip()
                    if value == "":
                        value = "未知"
                    # 价格、拳头数、是否外卖转数字
                    if key_name == "price":
                        value = float(value)
                    elif key_name == "fist_count":
                        value = float(value)
                    elif key_name == "is_takeout":
                        value = int(value)
                    row_dict[key_name] = value
                data_result.append(row_dict)
        print(f"✅ 饮食记录读取成功，共{len(data_result)}条")
        return data_result
    except FileNotFoundError:
        print(f"❌ 错误：找不到文件 {file_path}")
    except Exception as err:
        print(f"❌ 读取饮食文件出错：{str(err)}")
        return []


# 自测入口：直接运行本文件测试读取功能
if __name__ == "__main__":
    print("===== 开始测试CSV读取 =====")
    canteen_data = load_cafeteria_csv()
    shop_data = load_shop_csv()
    diet_data = load_diet_sample()
    print("===== 读取测试完成 =====")
    # 打印第一条数据查看效果
    if canteen_data:
        print("食堂第一条示例：", canteen_data[0])

