import os
import json
import time
import requests
from http.cookies import SimpleCookie

kindTable = {
    91: "SOR :re-91: ",
    95: "JUM :re-95: ",
    96: "LUX :re-96: ",
    97: "SEP :re-97: ",
    99: "SAT :re-99: ",
    94: "BFR :re-94: ",
}

# Cookies 文件路径
COOKIES_FILE = "./销售办公室/cookies.json"

# 创建会话
session = requests.session()
session.headers.update(
    {
        "referer": "https://www.simcompanies.com/",
        "accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    }
)

# 尝试从文件加载 Cookies
if os.path.exists(COOKIES_FILE):
    with open(COOKIES_FILE, "r") as f:
        try:
            cookies = json.load(f)
            session.cookies.update(cookies)
            print("已加载本地 Cookies")
        except json.JSONDecodeError:
            print("Cookies 文件损坏，重新登录")
else:
    print("Cookies 文件不存在，重新登录")


def checkRealmId(response):
    if response.status_code == 200:
        realm_id = response.json().get("authCompany").get("realmId")
        if realm_id != 1:
            raise ValueError("域Id不是1，响应内容:", response.text)
    else:
        raise ValueError("无法获取 realmId，状态码:", response.status_code)
    print("域Id正确")
    return realm_id


# 测试 Cookies 是否有效
authData = session.get("https://www.simcompanies.com/api/v3/companies/auth-data/")
if authData.status_code == 200:
    print("使用 Cookies 登录成功:", authData.json())
else:
    print("Cookies 无效，重新登录")

    # 获取主页面，初始化 Cookies
    main_page = session.get("https://www.simcompanies.com/zh-cn/")
    if main_page.status_code != 200:
        raise Exception("无法访问主页面，状态码:", main_page.status_code)

    # 获取 CSRF 令牌
    csrf_response = session.get("https://www.simcompanies.com/api/csrf/")
    if csrf_response.status_code != 200:
        raise Exception("无法获取 CSRF 令牌，状态码:", csrf_response.status_code)

    csrf_token = csrf_response.json().get("csrfToken")
    if not csrf_token:
        raise Exception("CSRF 令牌为空")

    # 设置 CSRF 令牌到 Cookies
    session.cookies.set("csrftoken", csrf_token)

    # 模拟登录
    login_payload = {
        "email": "youremail@gmail.com",  # 替换为你的邮箱
        "password": "yourpassword",  # 替换为你的密码
        "timezone_offset": -480,  # 根据你的时区设置
    }

    auth_response = session.post(
        "https://www.simcompanies.com/api/v2/auth/email/auth/",
        json=login_payload,
        headers={"x-csrftoken": csrf_token},
    )

    # 检查登录结果
    if auth_response.status_code == 200:
        print("登录成功:", auth_response.json())
        authData = session.get(
            "https://www.simcompanies.com/api/v3/companies/auth-data/"
        )
        for key, value in auth_response.headers.items():
            print(f"{key}: {value}")

        # 获取响应头中的 Set-Cookie 参数
        set_cookie = auth_response.headers.get("Set-Cookie")
        if set_cookie:
            print("Set-Cookie 参数:", set_cookie)

            # 解析 Set-Cookie 字符串
            cookie = SimpleCookie()
            cookie.load(set_cookie)

            # 将解析后的 Cookies 设置到 session 中
            for key, morsel in cookie.items():
                session.cookies.set(key, morsel.value)
            print("Cookies 已成功设置到 session 中")
        else:
            print("未找到 Set-Cookie 参数")

        # 保存 Cookies 到文件
        with open(COOKIES_FILE, "w") as f:
            json.dump(session.cookies.get_dict(), f)
            print("Cookies 已保存到文件")
    else:
        print("登录失败，状态码:", auth_response.status_code)
        try:
            print("错误信息:", auth_response.json())
        except ValueError:
            print("无法解析错误信息，响应内容:", auth_response.text)
    checkRealmId(authData)


def getStock():
    response = session.get("https://www.simcompanies.com/api/v3/resources/4568699/")
    if response.status_code != 200:
        raise ValueError("无法获取库存信息，状态码:", response.status_code)
    print(response.text)
    r = response.json()
    assert r is not None, "no stock response"
    stocks = {}
    for s in r:
        kind = s.get("kind")
        if stocks.get(kind, None) is None:
            stocks[kind] = s
        else:
            stocks[kind]["amount"] = s.get("amount") + stocks[kind]["amount"]
    print(stocks)
    return stocks


stocks = getStock()
stockLess = {}
# 获取建筑信息
companies = session.get("https://www.simcompanies.com/api/v3/companies/4568699")
if companies.status_code == 200:
    companiesJson = companies.json()
    # print("建筑信息:", companiesJson)
    buildings = companiesJson.get("infrastructure", {}).get("buildings", {})
    if buildings is None:
        raise ValueError("无法解析建筑信息，响应内容:", companies.text)
    else:
        filtedBuilds = filter(lambda x: x.get("kind") == "B", buildings)
        for building in filtedBuilds:
            id = building.get("id")
            if id is None:
                raise ValueError("建筑 ID 为空，响应内容:", building)
            print("建筑 ID:", id)
            orders = session.get(
                f"https://www.simcompanies.com/api/v2/companies/buildings/{id}/sales-orders/"
            )
            if orders.status_code == 200:
                ordersJson = orders.json()
                if ordersJson is None:
                    raise ValueError("无法解析订单信息，响应内容:", orders.text)
                filtedOrders = filter(lambda x: len(x.get("resources")) > 0, ordersJson)
                for order in filtedOrders:
                    print("订单信息:", order)
                    resources = order.get("resources")
                    for res in resources:
                        kind = res.get("kind")
                        stockLess[kind]["amount"] = stocks.get(kind, {}).get(
                            "amount", 0
                        ) - res.get("amount", 0)
                        print("货物类型:", res.get("kind"))
                        print("货物数量:", res.get("amount"))
                        print("库存余量:", stockLess[kind]["amount"])
            else:
                print(f"无法获取建筑 {id} 的订单信息，状态码:", orders.status_code)
                print(orders.reason)
else:
    print("无法获取公司信息，状态码:", companies.status_code)
    print(companies.reason)

buyingStr = "Buying\n"
for kind, a in stockLess.items():
    buyingStr += f"{a} {kindTable.get(kind, f'unknow: :re-{kind}: ')}\n"
print(buyingStr)
