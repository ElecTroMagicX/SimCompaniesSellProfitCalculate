from collections import defaultdict
import csv
from ctypes import sizeof
from fileinput import filename
import json
from numbers import Integral
import os
from queue import Empty
import time
import requests as rq

realm = 1
last_req_time = 0


BaseURL = "https://api.simcotools.com"
# MarketFollowedUrl = f"/v1/realms/{realm}/market/followed"
MarketResourceUrl = f"/v1/realms/{realm}/market/resources/"

SimCompaniesBaseUrl = "https://www.simcompanies.com"
ScMarketUrl = f"/api/v3/market/{realm}/"


def get_market(id, q=None):
    global last_req_time
    while time.time() - last_req_time <= 60:
        time.sleep(1)
    q_param = f"/{int(q)}" if q >= 0 else ""
    last_req_time = time.time()
    resp = rq.get(BaseURL + MarketResourceUrl + f"{id}{q_param}")
    if resp.status_code != 200:
        print(resp.status_code)
        print(resp.text)
        return {}
    resource = resp.json().get("resource")
    if resource is None or resp.status_code != 200:
        return {}
    qp = {}
    for r in resource.get("summariesByQuality", []):
        qp[int(r.get("quality"))] = r.get("price")
    return qp

def get_sc_market(id, iq=None):
    print("market start")
    global last_req_time
    while time.time() - last_req_time <= 60:
        time.sleep(1)
    last_req_time = time.time()
    time.sleep(1)
    resp = rq.get(SimCompaniesBaseUrl + ScMarketUrl + f"{id}")
    if resp.status_code != 200:
        print(resp.status_code)
        print(resp.text)
        return {}
    print(resp.status_code)
    resource = resp.json()
    if resource is None:
        return {}
    resource_dict = defaultdict(list)
    for r in resource:
        resource_dict[r.get("quality")].append(r)
    qp = {}
    if iq >= 0:
        rs = resource_dict[q]
        qp[iq] = rs[0].get("price") if len(rs) > 0 else None
        return qp
    for q, rs in resource_dict.items():
        if len(qp) > 10:
            break
        r = rs[0]
        price = r.get("price")
        qp[q] = price
    print("market end")
    return dict(sorted(qp.items()))


def culculate_income(qp, input_param):
    print("culculate start")
    sell_speeds = input_param["sell_speed"]
    sell_price = input_param["sell_price"]
    income = {}
    for q, p in qp.items():
        sell_speed = sell_speeds.get(f"{q}")
        if sell_speed is None:
            continue
        income_per_unit = sell_price - p
        income[f"{q}"] = {
            "per_unit_cost": round(p, 3),
            "per_unit_income": round(income_per_unit, 3),
            "per_hour_cost": round(p * sell_speed, 3),
            "per_hour_income": round(income_per_unit * sell_speed, 3),
            "10hour_cost": round(p * sell_speed * 10, 3),
            "10hour_income": round(income_per_unit * sell_speed * 10, 3),
            "24hour_cost": round(p * sell_speed * 24, 3),
            "24hour_income": round(income_per_unit * sell_speed * 24, 3),
        }
    print("culculate end")
    return income

def get_data_and_save(input_params, file_name):
    all_income = []
    for param in input_params:
        qp = get_sc_market(param["id"], param["q"])
        income = culculate_income(qp, param)
        # print(json.dumps(income, indent=4))
        for quality, data in income.items():
            data["name_ch"] = param["name_ch"]
            data["quality"] = quality
            all_income.append(data)

    
    all_income.sort(key=lambda x: x["per_hour_income"], reverse=True)
    # 输出表头
    print(f"{'名称':<10} {'质量':<8} {'单位成本':<12} {'每小时收入':<15} {'10小时成本':<12}")
    # 输出前三行数据
    for i in range(3):
        if i >= len(all_income):
            break
        row = all_income[i]
        print(f"{row['name_ch']:<10} {row['quality']:<8} {row['per_unit_cost']:<12} {row['per_hour_income']:<15} {row['10hour_cost']:<12}")

    # 输出到 CSV 文件
    with open(f"./销售数据/income_{file_name}.csv", "w", newline="", encoding="GBK") as csvfile:
        fieldnames = [
            "name_ch",
            "quality",
            "per_unit_cost",
            "per_unit_income",
            "per_hour_cost",
            "per_hour_income",
            "10hour_cost",
            "10hour_income",
            "24hour_cost",
            "24hour_income",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(all_income)


if __name__ == "__main__":
    sales_data_dir = './销售数据'
    
    for filename in os.listdir(sales_data_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(sales_data_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as file:
                input_params = json.load(file)
                name = filename.split('.')[0]
                print(name)
                get_data_and_save(input_params, name)


