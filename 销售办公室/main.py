from api import SimCompaniesAPI
import config

def calculate_stock_deficit(api, stocks, buildings):
    """计算库存缺口"""
    stock_deficit = {}

    for building in filter(lambda b: b.get("kind") == "B", buildings):
        building_id = building.get("id")
        if not building_id:
            raise ValueError(f"建筑 ID 为空，建筑数据: {building}")

        orders = api.get_sales_orders(building_id)
        for order in filter(lambda o: len(o.get("resources", [])) > 0, orders):
            print('--订单信息:', order)
            for res in order.get("resources", []):
                kind = res.get("kind")
                deficit = stocks.get(kind, {}).get("amount", 0) - res.get("amount", 0)
                stock_deficit[kind] = {"amount": deficit}

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
        buying_str += f"{data['amount']} {config.kindTable.get(kind, f'unknown: :re-{kind}: ')}\n"
    print(buying_str)


if __name__ == "__main__":
    main()