import os
import json


def load_cookies(session, cookies_file):
    """从文件加载 Cookies"""
    if os.path.exists(cookies_file):
        with open(cookies_file, "r") as f:
            try:
                cookies = json.load(f)
                session.cookies.update(cookies)
                print("已加载本地 Cookies")
                return True
            except json.JSONDecodeError:
                print("Cookies 文件损坏，重新登录")
    else:
        print("Cookies 文件不存在，重新登录")
    return False


def save_cookies(session, cookies_file):
    """保存 Cookies 到文件"""
    with open(cookies_file, "w") as f:
        json.dump(session.cookies.get_dict(), f)
        print("Cookies 已保存到文件")

        
def clear_cookies(cookies_file):
    """清除 Cookies"""
    if os.path.exists(cookies_file):
        os.remove(cookies_file)
        print("Cookies 文件已删除")
    else:
        print("Cookies 文件不存在，无需删除")