# -*- coding: utf-8 -*-
"""
db.py - SQLite 数据库操作模块（角色 A）

功能：数据库初始化、建表、CRUD 操作。
覆盖课程知识点：
  - 文件操作（第 7 章）：with open 读取 CSV
  - 数据库应用（第 10 章）：SQLite 连接、表创建、CRUD
  - 类与面向对象编程（第 8 章）：DietDatabase 类封装
  - 异常处理（第 9 章）：try-except 捕获文件/数据库异常
  - 列表、字典（第 3、5 章）：数据组织为字典列表后写入数据库
  - 字符串处理（第 2 章）：字段清洗、空值替换
"""

import sqlite3
import os

from data_loader import load_cafeteria_csv, load_shop_csv


class DietDatabase:
    """
    校园饮食数据库操作类（面向对象封装）

    功能：创建数据表、批量插入 CSV 数据、基础增删查改、关闭数据库连接。
    建表策略严格遵循 PRD 第 4.2 节 schema 设计：
      - users          : 用户配置（预算、健康目标、偏好）
      - diet_records   : 饮食记录主表（不含分类/分量，避免冗余）
      - record_items   : 记录的食物分类与分量（支持一餐多类）
      - cafeteria      : 食堂档口数据
      - nearby_shop    : 校外门店数据
    """

    def __init__(self, db_name="diet_db.sqlite"):
        """
        初始化数据库连接，自动执行建表。

        :param db_name: SQLite 数据库文件名，默认当前目录下 diet_db.sqlite
        """
        self.db_name = db_name
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row      # 使查询结果支持字典式访问
        self.conn.execute("PRAGMA foreign_keys = ON")  # 启用外键约束
        self.cursor = self.conn.cursor()
        self.cursor = self.conn.cursor()
        print("[OK] 数据库连接成功")
        self._create_all_tables()

    # ------------------------------------------------------------------ #
    # 建表（PRD 4.2 节严格对应）
    # ------------------------------------------------------------------ #
    def _create_all_tables(self):
        """一次性创建五张数据表（IF NOT EXISTS 避免重复建表）。"""
        # 表 1：用户配置表
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT    NOT NULL UNIQUE,
                monthly_budget REAL   NOT NULL DEFAULT 0.0,
                health_goal   TEXT    NOT NULL DEFAULT '维持身材',
                preferences   TEXT,                       -- JSON 字符串
                created_at    TEXT    DEFAULT (datetime('now', 'localtime'))
            )
            """
        )

        # 表 2：饮食记录主表（不含 category / fist_count，避免冗余）
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS diet_records (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id        INTEGER NOT NULL,
                date           TEXT    NOT NULL,
                meal           TEXT    NOT NULL CHECK(meal IN ('早餐','午餐','晚餐','加餐')),
                location_type  TEXT    NOT NULL CHECK(location_type IN ('食堂','外卖','校外门店','便利店')),
                location_name  TEXT,
                food_name      TEXT    NOT NULL,
                price          REAL    NOT NULL DEFAULT 0.0,
                is_takeout     INTEGER NOT NULL DEFAULT 0 CHECK(is_takeout IN (0, 1)),
                created_at     TEXT    DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        # 表 3：记录食物分类与分量（支持一餐多类）
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS record_items (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id  INTEGER NOT NULL,
                category   TEXT    NOT NULL CHECK(category IN (
                    '主食','蔬菜','肉类','水果','饮料','零食','汤品','其他'
                )),
                fist_count REAL    NOT NULL DEFAULT 0.0,
                FOREIGN KEY (record_id) REFERENCES diet_records(id) ON DELETE CASCADE
            )
            """
        )

        # 表 4：食堂档口数据（外部数据）
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cafeteria (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                stall_id     TEXT    NOT NULL,
                stall_name   TEXT,
                canteen      TEXT    NOT NULL,
                floor        TEXT,
                dish_name    TEXT    NOT NULL,
                price        REAL    NOT NULL DEFAULT 0.0,
                category     TEXT,
                peak_start   TEXT,
                peak_end     TEXT,
                avg_wait_min REAL    DEFAULT 0.0
            )
            """
        )

        # 表 5：校外门店数据（外部数据）
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS nearby_shop (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                shop_id    TEXT    NOT NULL,
                shop_name  TEXT,
                type       TEXT,
                dish_name  TEXT    NOT NULL,
                price      REAL    NOT NULL DEFAULT 0.0,
                category   TEXT,
                distance_m REAL    DEFAULT 0.0
            )
            """
        )

        self.conn.commit()
        print("[OK] 五张数据表创建完成 / 已存在")

    # ------------------------------------------------------------------ #
    # 用户 CRUD
    # ------------------------------------------------------------------ #
    def create_user(self, username, monthly_budget, health_goal, preferences=None):
        """
        创建用户配置。

        :param username:       str  用户名
        :param monthly_budget: float 月度预算
        :param health_goal:    str  减肥 / 维持身材 / 健身增重
        :param preferences:    str  JSON 字符串，如 '["偏辣","清淡"]'
        :return: int 新用户 id
        """
        sql = """
            INSERT INTO users (username, monthly_budget, health_goal, preferences)
            VALUES (?, ?, ?, ?)
        """
        self.cursor.execute(sql, (username, monthly_budget, health_goal, preferences))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_user(self, user_id):
        """
        根据用户 ID 获取用户配置。

        :param user_id: int
        :return: dict 或 None
        """
        self.cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def get_user_by_name(self, username):
        """根据用户名获取用户配置。"""
        self.cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def update_user(self, user_id, **kwargs):
        """
        更新用户配置（支持局部更新）。

        :param user_id: int
        :param kwargs:  可更新的字段名与值
        :return: bool 是否成功
        """
        allowed = {"username", "monthly_budget", "health_goal", "preferences"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        sql = f"UPDATE users SET {set_clause} WHERE id = ?"
        self.cursor.execute(sql, (*updates.values(), user_id))
        self.conn.commit()
        return self.cursor.rowcount > 0

    # ------------------------------------------------------------------ #
    # 饮食记录 CRUD（含 record_items 级联）
    # ------------------------------------------------------------------ #
    def create_diet_record(self, user_id, date, meal, location_type, location_name,
                           food_name, price, is_takeout, items):
        """
        创建饮食记录，并级联插入食物分类/分量。

        :param items: list[dict] 每项为 {"category": str, "fist_count": float}
        :return: int 新记录 id
        """
        sql_record = """
            INSERT INTO diet_records
            (user_id, date, meal, location_type, location_name, food_name, price, is_takeout)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.cursor.execute(
            sql_record,
            (user_id, date, meal, location_type, location_name, food_name, price, is_takeout)
        )
        record_id = self.cursor.lastrowid

        sql_item = """
            INSERT INTO record_items (record_id, category, fist_count)
            VALUES (?, ?, ?)
        """
        for item in items:
            self.cursor.execute(
                sql_item,
                (record_id, item["category"], item["fist_count"])
            )
        self.conn.commit()
        return record_id

    def get_diet_records(self, user_id, date=None, meal=None):
        """
        查询用户的饮食记录，可选按日期/餐次过滤。

        :return: list[dict] 每条记录包含关联的 items 列表
        """
        conditions = ["user_id = ?"]
        params = [user_id]
        if date:
            conditions.append("date = ?")
            params.append(date)
        if meal:
            conditions.append("meal = ?")
            params.append(meal)
        where = " AND ".join(conditions)
        sql = f"SELECT * FROM diet_records WHERE {where} ORDER BY date DESC, meal"
        self.cursor.execute(sql, params)
        rows = [dict(r) for r in self.cursor.fetchall()]

        # 补充关联的 record_items
        for row in rows:
            self.cursor.execute(
                "SELECT category, fist_count FROM record_items WHERE record_id = ?",
                (row["id"],)
            )
            row["items"] = [dict(r) for r in self.cursor.fetchall()]
        return rows

    def update_diet_record(self, record_id, **kwargs):
        """
        更新饮食记录主表（不更新 items，如需更新 items 请删除后重建）。
        """
        allowed = {"date", "meal", "location_type", "location_name",
                   "food_name", "price", "is_takeout"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        sql = f"UPDATE diet_records SET {set_clause} WHERE id = ?"
        self.cursor.execute(sql, (*updates.values(), record_id))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def delete_diet_record(self, record_id):
        """删除记录（级联删除 record_items，由外键约束自动处理）。"""
        self.cursor.execute("DELETE FROM diet_records WHERE id = ?", (record_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0

    # ------------------------------------------------------------------ #
    # 批量导入外部 CSV 数据
    # ------------------------------------------------------------------ #
    def insert_cafeteria_data(self, data_list):
        """
        批量插入食堂数据。

        :param data_list: list[dict] 由 data_loader 清洗后的字典列表
        """
        insert_sql = """
            INSERT INTO cafeteria
            (stall_id, stall_name, canteen, floor, dish_name,
             price, category, peak_start, peak_end, avg_wait_min)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        rows = [
            (
                row["stall_id"], row["stall_name"], row["canteen"], row["floor"],
                row["dish_name"], row["price"], row["category"],
                row["peak_start"], row["peak_end"], row["avg_wait_min"]
            )
            for row in data_list
        ]
        self.cursor.executemany(insert_sql, rows)
        self.conn.commit()
        print(f"[OK] 食堂数据插入完成，共 {len(rows)} 条")

    def insert_shop_data(self, data_list):
        """批量插入校外门店数据。"""
        insert_sql = """
            INSERT INTO nearby_shop
            (shop_id, shop_name, type, dish_name, price, category, distance_m)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        rows = [
            (
                row["shop_id"], row["shop_name"], row["type"],
                row["dish_name"], row["price"], row["category"], row["distance_m"]
            )
            for row in data_list
        ]
        self.cursor.executemany(insert_sql, rows)
        self.conn.commit()
        print(f"[OK] 门店数据插入完成，共 {len(rows)} 条")

    # ------------------------------------------------------------------ #
    # 辅助查询方法
    # ------------------------------------------------------------------ #
    def query_all_cafeteria(self):
        """查询全部食堂菜品。"""
        self.cursor.execute("SELECT * FROM cafeteria")
        return [dict(r) for r in self.cursor.fetchall()]

    def query_cafeteria_by_name(self, canteen_name):
        """按食堂名称筛选菜品。"""
        self.cursor.execute(
            "SELECT * FROM cafeteria WHERE canteen = ?", (canteen_name,)
        )
        return [dict(r) for r in self.cursor.fetchall()]

    def query_all_shops(self):
        """查询全部校外门店。"""
        self.cursor.execute("SELECT * FROM nearby_shop")
        return [dict(r) for r in self.cursor.fetchall()]

    def query_takeout_records(self, user_id):
        """查询某用户的全部外卖记录。"""
        self.cursor.execute(
            "SELECT * FROM diet_records WHERE user_id = ? AND is_takeout = 1",
            (user_id,)
        )
        return [dict(r) for r in self.cursor.fetchall()]

    def clear_table(self, table_name):
        """清空指定表数据（仅测试使用）。"""
        safe_tables = {"users", "diet_records", "record_items",
                       "cafeteria", "nearby_shop"}
        if table_name not in safe_tables:
            raise ValueError(f"不安全的表名: {table_name}")
        self.cursor.execute(f"DELETE FROM {table_name}")
        self.conn.commit()
        print(f"[OK] {table_name} 表数据已清空")

    # ------------------------------------------------------------------ #
    # 资源释放
    # ------------------------------------------------------------------ #
    def close(self):
        """关闭数据库连接与游标，释放资源。"""
        self.cursor.close()
        self.conn.close()
        print("[OK] 数据库连接已关闭")


# =====================================================================
# 自测入口：运行 db.py 自动完成全流程测试
# =====================================================================
if __name__ == "__main__":
    print("===== 数据库初始化与数据导入测试开始 =====")
    db = DietDatabase()

    # 1. 导入外部 CSV
    canteen_data = load_cafeteria_csv()
    shop_data = load_shop_csv()
    db.insert_cafeteria_data(canteen_data)
    db.insert_shop_data(shop_data)

    # 2. 创建示例用户
    user_id = db.create_user("test_user", 1200.0, "维持身材", '["清淡","少油"]')
    print(f"[OK] 创建用户，id={user_id}")

    # 3. 创建饮食记录（含多类分量）
    record_id = db.create_diet_record(
        user_id=user_id,
        date="2026-06-23",
        meal="午餐",
        location_type="食堂",
        location_name="学一食堂",
        food_name="广式烧鸭饭",
        price=15.5,
        is_takeout=0,
        items=[
            {"category": "主食", "fist_count": 2.0},
            {"category": "肉类", "fist_count": 1.0},
            {"category": "蔬菜", "fist_count": 0.5}
        ]
    )
    print(f"[OK] 创建饮食记录，id={record_id}")

    # 4. 查询验证
    records = db.get_diet_records(user_id)
    print("\n--- 用户饮食记录 ---")
    for r in records:
        print(f"  {r['date']} {r['meal']} {r['food_name']} 价格{r['price']}元")
        for item in r["items"]:
            print(f"    -> {item['category']}: {item['fist_count']} 拳")

    # 5. 查询食堂数据
    print("\n--- 松涛园菜品 TOP 3 ---")
    for item in db.query_cafeteria_by_name("松涛园")[:3]:
        print(f"  {item['dish_name']} 价格{item['price']}元")

    db.close()
    print("===== 数据库全部自测流程完成 =====")
