# db.py
import sqlite3
from data_loader import load_cafeteria_csv, load_shop_csv, load_diet_sample

class DietDatabase:
    """
    校园饮食数据库操作类（面向对象封装）
    功能：创建数据表、批量插入CSV数据、基础增删查改、关闭数据库连接
    """
    def __init__(self, db_name="diet_db.sqlite"):
        # 初始化：创建数据库连接与游标
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        print("✅ 数据库连接成功")
        # 自动执行建表
        self.create_all_table()

    def create_all_table(self):
        """一次性创建三张数据表"""
        # 表1：食堂菜品表 cafeteria
        create_canteen_sql = '''
        CREATE TABLE IF NOT EXISTS cafeteria (
            stall_id TEXT,
            stall_name TEXT,
            canteen TEXT,
            floor TEXT,
            dish_name TEXT,
            price REAL,
            category TEXT,
            peak_start TEXT,
            peak_end TEXT,
            avg_wait_min REAL
        )
        '''
        self.cursor.execute(create_canteen_sql)

        # 表2：校外门店表 nearby_shop
        create_shop_sql = '''
        CREATE TABLE IF NOT EXISTS nearby_shop (
            shop_id TEXT,
            shop_name TEXT,
            type TEXT,
            dish_name TEXT,
            price REAL,
            category TEXT,
            distance_m REAL
        )
        '''
        self.cursor.execute(create_shop_sql)

        # 表3：用户饮食记录表 diet_record
        create_diet_sql = '''
        CREATE TABLE IF NOT EXISTS diet_record (
            date TEXT,
            meal TEXT,
            location_type TEXT,
            location_name TEXT,
            food_name TEXT,
            price REAL,
            category TEXT,
            fist_count REAL,
            is_takeout INTEGER
        )
        '''
        self.cursor.execute(create_diet_sql)
        self.conn.commit()
        print("✅ 三张数据表创建完成/已存在")

    def insert_cafeteria_data(self, data_list):
        """批量插入食堂数据"""
        insert_sql = '''
        INSERT INTO cafeteria 
        (stall_id, stall_name, canteen, floor, dish_name, price, category, peak_start, peak_end, avg_wait_min)
        VALUES (?,?,?,?,?,?,?,?,?,?)
        '''
        # 遍历清洗后的数据字典，转为元组批量插入
        insert_rows = []
        for row in data_list:
            one_row = (
                row["stall_id"], row["stall_name"], row["canteen"], row["floor"],
                row["dish_name"], row["price"], row["category"], row["peak_start"],
                row["peak_end"], row["avg_wait_min"]
            )
            insert_rows.append(one_row)
        self.cursor.executemany(insert_sql, insert_rows)
        self.conn.commit()
        print(f"✅ 食堂数据插入完成，共{len(insert_rows)}条")

    def insert_shop_data(self, data_list):
        """批量插入校外门店数据"""
        insert_sql = '''
        INSERT INTO nearby_shop 
        (shop_id, shop_name, type, dish_name, price, category, distance_m)
        VALUES (?,?,?,?,?,?,?)
        '''
        insert_rows = []
        for row in data_list:
            one_row = (
                row["shop_id"], row["shop_name"], row["type"], row["dish_name"],
                row["price"], row["category"], row["distance_m"]
            )
            insert_rows.append(one_row)
        self.cursor.executemany(insert_sql, insert_rows)
        self.conn.commit()
        print(f"✅ 门店数据插入完成，共{len(insert_rows)}条")

    def insert_diet_data(self, data_list):
        """批量插入用户饮食记录"""
        insert_sql = '''
        INSERT INTO diet_record 
        (date, meal, location_type, location_name, food_name, price, category, fist_count, is_takeout)
        VALUES (?,?,?,?,?,?,?,?,?)
        '''
        insert_rows = []
        for row in data_list:
            one_row = (
                row["date"], row["meal"], row["location_type"], row["location_name"],
                row["food_name"], row["price"], row["category"], row["fist_count"],
                row["is_takeout"]
            )
            insert_rows.append(one_row)
        self.cursor.executemany(insert_sql, insert_rows)
        self.conn.commit()
        print(f"✅ 饮食记录插入完成，共{len(insert_rows)}条")

    # 基础查询方法1：查询全部食堂菜品
    def query_all_canteen(self):
        self.cursor.execute("SELECT * FROM cafeteria")
        return self.cursor.fetchall()

    # 基础查询方法2：按食堂名称筛选菜品（示例：松涛园/学一/学五/春晖）
    def query_canteen_by_name(self, canteen_name):
        sql = "SELECT * FROM cafeteria WHERE canteen = ?"
        self.cursor.execute(sql, (canteen_name,))
        return self.cursor.fetchall()

    # 基础查询方法3：查询所有外卖饮食记录
    def query_takeout_diet(self):
        self.cursor.execute("SELECT * FROM diet_record WHERE is_takeout = 1")
        return self.cursor.fetchall()

    # 清空表数据（测试用）
    def clear_table(self, table_name):
        self.cursor.execute(f"DELETE FROM {table_name}")
        self.conn.commit()
        print(f"✅ {table_name} 表数据已清空")

    # 关闭数据库连接（必须调用，释放资源）
    def close_db(self):
        self.cursor.close()
        self.conn.close()
        print("✅ 数据库连接已关闭")

# 程序自测入口：运行db.py自动完成全流程测试
if __name__ == "__main__":
    print("===== 数据库初始化与数据导入测试开始 =====")
    # 1. 实例化数据库对象，自动建表
    db = DietDatabase()

    # 2. 读取三份清洗后的CSV数据
    canteen_data = load_cafeteria_csv()
    shop_data = load_shop_csv()
    diet_data = load_diet_sample()

    # 3. 批量插入数据库
    db.insert_cafeteria_data(canteen_data)
    db.insert_shop_data(shop_data)
    db.insert_diet_data(diet_data)

    # 4. 简单查询测试
    print("\n--- 查询松涛园所有菜品 ---")
    songtao_data = db.query_canteen_by_name("松涛园")
    for item in songtao_data[:3]:  # 只打印前3条
        print(item)

    print("\n--- 查询所有外卖记录 ---")
    takeout_list = db.query_takeout_diet()
    for item in takeout_list[:2]:
        print(item)

    # 5. 关闭连接
    db.close_db()
    print("===== 数据库全部自测流程完成 =====")
