from http.cookies import SimpleCookie
import requests
from config import BASE_URL, COOKIES_FILE
from utils import clear_cookies, load_cookies, save_cookies


class SimCompaniesAPI:
    _instance = None  # 用于存储单例实例
    _default_headers = {
        "referer": BASE_URL,
        "accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    }

    def __new__(cls, *args, **kwargs):
        """
        实现单例模式，确保只有一个实例。
        """
        if not cls._instance:
            cls._instance = object.__new__(cls)
        return cls._instance

    def __init__(self, realmId=0):
        """
        初始化 SimCompanies API 客户端。
        """
        # 如果实例已经初始化过，则跳过
        if hasattr(self, "_initialized") and self._initialized:
            self.realmId = realmId  # 动态更新参数
            return

        # 初始化实例
        self._current_realm_id = 0
        self.realmId = realmId
        self.session = requests.Session()
        self.session.headers.update(self._default_headers)
        self._initialized = True  # 标记实例已初始化

    def _reset_cookies(self, response):
        # 获取响应头中的 Set-Cookie 参数
        cookie = None
        set_cookie = response.headers.get("Set-Cookie")
        if set_cookie:
            print("Set-Cookie 参数:", set_cookie)

            # 解析 Set-Cookie 字符串
            cookie = SimpleCookie()
            cookie.load(set_cookie)

            # 将解析后的 Cookies 设置到 session 中
            for key, morsel in cookie.items():
                self.session.cookies.set(key, morsel.value)
            print("Cookies 已成功设置到 session 中")
        else:
            print("未找到 Set-Cookie 参数")
        return cookie

    def _compare_oldnew_cookies_same(self, old_cookies, new_cookies):
        """
        比较旧 Cookies 和新 Cookies 是否相同
        """
        if not old_cookies or not new_cookies or len(old_cookies) != len(new_cookies):
            return False

        for key, value in old_cookies.items():
            if key not in new_cookies or new_cookies[key] != value:
                return False

        return True

    def login_with_cookies(self):
        """使用 Cookies 登录"""
        if not load_cookies(self.session, COOKIES_FILE):
            return False

        # 验证 Cookies 是否有效
        if not self.check_and_change_realm_id():
            print("Cookies 无效或过期")
            return False

        print("使用 Cookies 登录成功")
        return True

    def get_csrf_token_and_set_cookies(self):
        # 获取 CSRF 令牌
        csrf_response = self.session.get(f"{BASE_URL}/api/csrf/")
        if csrf_response.status_code != 200:
            raise Exception("无法获取 CSRF 令牌，状态码:", csrf_response.status_code)

        csrf_token = csrf_response.json().get("csrfToken")
        if not csrf_token:
            raise Exception("CSRF 令牌为空")

        # 设置 CSRF 令牌到 Cookies
        self.session.cookies.set("csrftoken", csrf_token)
        return csrf_token

    def login_with_credentials(self, email, password):
        """使用账号密码登录"""
        csrf_token = self.get_csrf_token_and_set_cookies()

        # 登录请求
        login_payload = {
            "email": email,
            "password": password,
            "timezone_offset": -480,  # 根据你的时区设置
        }
        auth_response = self.session.post(
            f"{BASE_URL}/api/v2/auth/email/auth/",
            json=login_payload,
            headers={"x-csrftoken": csrf_token},
        )

        if auth_response.status_code == 200:
            print("账号密码登录成功:", auth_response.json())
            self._reset_cookies(auth_response)
            self.check_and_change_realm_id()
            save_cookies(self.session, COOKIES_FILE)
            return True
        else:
            raise Exception(
                f"登录失败，状态码: {auth_response.status_code}, 响应内容: {auth_response.text}"
            )

    def login(self, email, password):
        """登录流程"""
        # 尝试使用 Cookies 登录
        if self.login_with_cookies():
            return

        # 如果 Cookies 登录失败，则使用账号密码登录
        self.login_with_credentials(email, password)

    def check_and_change_realm_id(self):
        """检查 Realm ID 是否正确"""
        response = self.session.get(f"{BASE_URL}/api/v3/companies/auth-data/")
        if response.status_code == 200:
            realm_id = response.json().get("authCompany", {}).get("realmId")
            self._current_realm_id = realm_id
            if realm_id != self.realmId:
                clear_cookies(COOKIES_FILE)
                self.switch_realm(self.realmId)
                # raise ValueError("域Id不正确，请手动在页面切换，响应内容:", response.text)
            print("域Id正确")
            return True
        else:
            print("无法验证 Realm ID，状态码:", response.status_code)
            return False

    def switch_realm(self, realmId):
        if realmId == self._current_realm_id:
            print("当前 Realm ID 已经是", realmId)
            return
        # 切换新 session
        # self.session.cookies.get("csrftoken", None)
        # self.session.close()  # 关闭旧的 session
        # self.session = requests.Session()
        # self.session.headers.update(self._default_headers)
        csrf_token = self.get_csrf_token_and_set_cookies()
        # 切换 Realm ID
        switch = self.session.post(
            f"{BASE_URL}/api/v1/realm/{realmId}/switch/",
            headers={"x-csrftoken": csrf_token},
        )
        if switch.status_code != 200:
            raise ValueError(
                f"无法切换 Realm ID，状态码:{switch.status_code}，Reason:{switch.reason}"
            )
        old_cookies = dict(self.session.cookies.get_dict())
        if not self._compare_oldnew_cookies_same(
            old_cookies, self._reset_cookies(switch)
        ):
            sync = self.session.post(
                f"{BASE_URL}/api/v1/realm/{realmId}/sync/",
                headers={"x-csrftoken": csrf_token},
            )
            if sync.status_code != 200:
                raise ValueError(
                    f"无法同步 Realm ID，状态码:{sync.status_code}，Reason:{sync.reason}"
                )
        self._current_realm_id = realmId
        print(f"成功切换到 Realm ID {realmId}")

    def get_stock(self):
        """获取库存信息"""
        response = self.session.get(f"{BASE_URL}/api/v3/resources/4568699/")
        if response.status_code != 200:
            raise ValueError("无法获取库存信息，状态码:", response.status_code)

        stock_data = response.json()
        if not stock_data:
            raise ValueError("库存数据为空")

        stocks = {}
        for item in stock_data:
            kind = item.get("kind")
            if kind not in stocks:
                stocks[kind] = item
            else:
                stocks[kind]["amount"] += item.get("amount", 0)

        print("库存信息:", stocks)
        return stocks

    def get_buildings(self):
        """获取建筑信息"""
        response = self.session.get(f"{BASE_URL}/api/v3/companies/4568699")
        if response.status_code != 200:
            raise ValueError("无法获取建筑信息，状态码:", response.status_code)

        company_data = response.json()
        buildings = company_data.get("infrastructure", {}).get("buildings", [])
        if not buildings:
            raise ValueError("建筑信息为空")

        print("建筑信息:", buildings)
        return buildings

    def get_sales_orders(self, building_id):
        """获取指定建筑的销售订单信息"""
        response = self.session.get(
            f"{BASE_URL}/api/v2/companies/buildings/{building_id}/sales-orders/"
        )
        if response.status_code != 200:
            raise ValueError(
                f"无法获取建筑 {building_id} 的订单信息，状态码:", response.status_code
            )

        orders = response.json()
        print(f"建筑 {building_id} 的销售订单:", orders)
        return orders
