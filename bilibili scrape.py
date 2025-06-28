#%%
import time, json, csv, random, requests
from urllib3.util import Retry
from requests.adapters import HTTPAdapter

# ★ 请替换 ↓
BVID        = "BV19sCpYTEWS"
HEADERS     = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"}
COOKIES     = {"SESSDATA": "b6df1a89%2C1765109083%2C0c1ed%2A61CjAi4m7i50EEYEWRzH9GCDTfLKL_5rzzxG6Yme_J5NWpwouLBa52JqZb2Vule9D4NGkSVjBXanNNNHdlMlp6b0lEMENFQjFZYXpsQlRYS2Nic29SZzc2bXNydUZpY21HVEkxb3hjNTJCVXpKcFFIYUNWRXVhZVFnUVNlekFXYndOSGs5OXpZckVRIIEC", "buvid3": "4C04BFED-22B8-1762-C192-4C6C3F97B92656278infoc", "bili_jct": "f7d79a1deb1a08fe33093722ed938286"}

session = requests.Session()
session.headers.update(HEADERS)
session.cookies.update(COOKIES)
session.mount("https://", HTTPAdapter(max_retries=Retry(total=5,
                                                        backoff_factor=0.3,
                                                        status_forcelist=[500, 502, 503, 504])))

def get_level1(bvid, max_pages=2000, pause=1):
    """抓取 /x/v2/reply/main —— 一级评论"""
    next_idx, all_rows = 0, []
    for page in range(max_pages):
        url = (
            "https://api.bilibili.com/x/v2/reply/main"
            f"?next={next_idx}&type=1&mode=3&oid={bvid}"
        )
        r = session.get(url, timeout=10).json()
        replies = r["data"].get("replies") or []
        if not replies:
            break
        # 记录
        for c in replies:
            all_rows.append(
                {
                    "rpid":      c["rpid"],          # 后面要用来抓二级
                    "uname":     c["member"]["uname"],
                    "sex":       c["member"]["sex"],
                    "level":     c["member"]["level_info"]["current_level"],
                    "message":   c["content"]["message"],
                    "like":      c["like"],
                    "ctime":     time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(c["ctime"])),
                }
            )
        # 翻页游标
        next_idx = r["data"]["cursor"]["next"]
        time.sleep(pause + random.random())  # 防止触发风控
    return all_rows

def get_level2(bvid, root_rpid, max_pages=50, pause=1):
    """抓取 root_rpid 对应楼层的二级评论"""
    for pn in range(1, max_pages + 1):
        url = (
            "https://api.bilibili.com/x/v2/reply/reply"
            f"?oid={bvid}&type=1&root={root_rpid}&ps=20&pn={pn}"
        )
        r = session.get(url, timeout=10).json()
        replies = (r["data"] or {}).get("replies") or []
        if not replies:
            break
        for c in replies:
            yield {
                "root":      root_rpid,
                "uname":     c["member"]["uname"],
                "message":   c["content"]["message"],
                "like":      c["like"],
                "ctime":     time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(c["ctime"])),
            }
        time.sleep(pause + random.random())

def crawl_all(bvid, out_csv="bilibili_comments2.csv"):
    lvl1 = get_level1(bvid)
    with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
        fieldnames = ["层级", "root", "rpid", "uname", "sex", "level", "message", "like", "ctime"]
        writer = csv.DictWriter(f, fieldnames)
        writer.writeheader()

        # 一级
        for row in lvl1:
            row["层级"] = "L1"
            row["root"] = row["rpid"]
            writer.writerow(row)

            # 二级
            for sub in get_level2(bvid, row["rpid"]):
                sub.update({"层级": "L2"})
                writer.writerow(sub)

    print(f"✅ 完成！共抓一级 {len(lvl1)} 楼，文件已保存 {out_csv}")

if __name__ == "__main__":
    crawl_all(BVID)