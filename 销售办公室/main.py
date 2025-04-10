from xmlrpc.client import MAXINT
from api import SimCompaniesAPI
from config import KIND_TABLE


def calculate_stock_deficit(api, stocks, buildings):
    """计算库存缺口"""
    stock_deficit = {}
    all_kinds_amount = {}

    for building in filter(lambda b: b.get("kind") == "B", buildings):
        building_id = building.get("id")
        if not building_id:
            raise ValueError(f"建筑 ID 为空，建筑数据: {building}")

        orders = api.get_sales_orders(building_id)
        for order in filter(lambda o: len(o.get("resources", [])) > 0, orders):
            print("--订单信息:", order)
            for res in order.get("resources", []):
                kind = res.get("kind")
                lower_price = all_kinds_amount.get(kind, {}).get("price", MAXINT)
                all_kinds_amount[kind] = {
                    "amount": all_kinds_amount.get(kind, {}).get('amount', 0) + res.get("amount", 0),
                    "price": (
                        res.get("price", 0)
                        if res.get("price") < lower_price
                        else lower_price
                    ),
                }

    print("all_kinds_amount:", all_kinds_amount)
    for kind, data in all_kinds_amount.items():
        deficit = data['amount'] - stocks.get(kind, {}).get("amount", 0)
        if deficit > 0:
            stock_deficit[kind] = deficit
            print(f"货物类型: {KIND_TABLE[kind]}, 需要购买: {deficit}, 最高0星价格: {data['price']}")
        else:
            print(
                f"货物类型: {KIND_TABLE[kind]}, 库存充足: {stocks.get(kind, {}).get('amount', 0)}"
            )

    return stock_deficit


def main():
    # 登录信息
    email = "youremail@gmail.com"  # 替换为你的邮箱
    password = "yourpassword"      # 替换为你的密码

    # 初始化 API 客户端
    api = SimCompaniesAPI(1)

    # 登录
    api.login(email, password)

    # 获取库存信息
    stocks = api.get_stock()

    # 获取建筑信息
    buildings = api.get_buildings()

    # 计算库存缺口
    stock_deficit = calculate_stock_deficit(api, stocks, buildings)

    # 输出需要购买的物品
    buying_str = "Buying\n"
    for kind, data in stock_deficit.items():
        buying_str += f"{data} {KIND_TABLE.get(kind, f'unknown: :re-{kind}: ')}\n"
    print(buying_str)


if __name__ == "__main__":
    main()
