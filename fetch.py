import os, sys, json, datetime, urllib.parse, pathlib
import requests

KEY = urllib.parse.unquote(os.environ["KRA_KEY"].strip())
BASE = "https://apis.data.go.kr/B551015/"
MEETS = {"1": "서울", "2": "제주", "3": "부산경남"}
KST = datetime.timezone(datetime.timedelta(hours=9))
TODAY = datetime.datetime.now(KST).strftime("%Y%m%d")
OUT = pathlib.Path("data")

def num(v):
    try:
        f = float(v)
        return int(f) if f == int(f) else f
    except Exception:
        return None

def get(path, **params):
    p = {"serviceKey": KEY, "pageNo": 1, "numOfRows": 500, "_type": "json"}
    p.update(params)
    r = requests.get(BASE + path, params=p, timeout=60)
    r.raise_for_status()
    body = r.json().get("response", {}).get("body", {})
    items = body.get("items") or {}
    it = items.get("item") if isinstance(items, dict) else []
    if isinstance(it, dict):
        it = [it]
    return it or []

def save(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    print("saved", path)

def entry(date):
    for m, name in MEETS.items():
        items = get("API26_2/entrySheet_2", rc_date=date, meet=m)
        if not items:
            continue
        horses = []
        for it in items:
            raw = str(it.get("jkName") or "").strip()
            allow = 0
            if raw.startswith("("):
                try:
                    allow = int(raw[1:raw.index(")")])
                except Exception:
                    allow = 0
                raw = raw[raw.index(")") + 1:].strip() if ")" in raw else raw
            st = "".join(ch for ch in str(it.get("stTime") or "") if ch.isdigit() or ch == ":").lstrip(":")
            horses.append({
                "n": num(it.get("chulNo")), "name": str(it.get("hrName") or "").strip(), "hrNo": str(it.get("hrNo") or ""),
                "age": num(it.get("age")), "sex": it.get("sex") or "", "jk": raw, "jkAllow": allow,
                "tr": str(it.get("trName") or "").strip(), "ow": str(it.get("owName") or "").strip(), "prd": it.get("prd") or "",
                "rating": num(it.get("rating")), "wt": num(it.get("wgBudam")), "budam": it.get("budam") or "",
                "starts": num(it.get("rcCntT")) or 0, "w": num(it.get("ord1CntT")) or 0, "p2": num(it.get("ord2CntT")) or 0, "p3": num(it.get("ord3CntT")) or 0,
                "startsY": num(it.get("rcCntY")) or 0, "wY": num(it.get("ord1CntY")) or 0, "p2Y": num(it.get("ord2CntY")) or 0, "p3Y": num(it.get("ord3CntY")) or 0,
                "earn6m": num(it.get("chaksun_6m")) or 0, "earnY": num(it.get("chaksunY")) or 0, "earnT": num(it.get("chaksunT")) or 0,
                "rcNo": num(it.get("rcNo")), "dist": num(it.get("rcDist")), "rcName": it.get("rcName") or "", "rank": it.get("rank") or "",
                "ageCond": it.get("ageCond") or "", "stTime": st, "dusu": num(it.get("dusu")), "prize1": num(it.get("chaksun1")) or 0,
            })
        save(OUT / "days" / f"{m}-{date}.json", {"meet": name, "date": date, "updatedAt": int(datetime.datetime.now().timestamp() * 1000), "source": "entrySheet_2", "horses": horses})

def results():
    for f in sorted((OUT / "days").glob("*.json")) if (OUT / "days").exists() else []:
        m, date = f.stem.split("-")
        age = (datetime.datetime.strptime(TODAY, "%Y%m%d") - datetime.datetime.strptime(date, "%Y%m%d")).days
        if age < 0 or age > 10:
            continue
        rf = OUT / "results" / f.name
        day = json.loads(f.read_text(encoding="utf-8"))
        n_races = len({h["rcNo"] for h in day["horses"]})
        if rf.exists():
            old = json.loads(rf.read_text(encoding="utf-8"))
            if len(old.get("done", [])) >= n_races:
                continue
        items = get("API214_1/RaceDetailResult_1", rc_date=date, meet=m, numOfRows=300)
        if not items:
            continue
        rows = []
        for it in items:
            rows.append({
                "rcNo": num(it.get("rcNo")), "n": num(it.get("chulNo")), "name": str(it.get("hrName") or "").strip(), "hrNo": str(it.get("hrNo") or ""),
                "jk": str(it.get("jkName") or "").strip(), "ord": num(it.get("ord")) or 0, "winOdds": num(it.get("winOdds")), "plcOdds": num(it.get("plcOdds")),
                "rcTime": num(it.get("rcTime")), "wgHr": str(it.get("wgHr") or ""), "track": str(it.get("track") or "").strip(), "weather": str(it.get("weather") or ""),
                "diff": str(it.get("diffUnit") or ""), "dist": num(it.get("rcDist")), "rank": str(it.get("rank") or ""),
            })
        done = sorted({r["rcNo"] for r in rows if r["rcNo"] and 1 <= (r["ord"] or 0) <= 30})
        if not done:
            continue
        save(rf, {"meet": MEETS[m], "date": date, "updatedAt": int(datetime.datetime.now().timestamp() * 1000), "source": "RaceDetailResult_1", "done": done, "results": rows})

def jockeys():
    out = []
    for m in MEETS:
        for it in get("currentjockeyInfo/getcurrentjockeyinfo", meet=m, numOfRows=300):
            out.append({
                "no": str(it.get("jkNo") or ""), "name": str(it.get("jkName") or "").strip(), "meet": m, "age": num(it.get("age")), "debut": num(it.get("debut")),
                "part": str(it.get("part") if it.get("part") is not None else ""),
                "starts": num(it.get("rcCntT")) or 0, "w": num(it.get("ord1CntT")) or 0, "p2": num(it.get("ord2CntT")) or 0, "p3": num(it.get("ord3CntT")) or 0,
                "startsY": num(it.get("rcCntY")) or 0, "wY": num(it.get("ord1CntY")) or 0, "p2Y": num(it.get("ord2CntY")) or 0, "p3Y": num(it.get("ord3CntY")) or 0,
                "wg": num(it.get("wgPart")),
            })
    if out:
        save(OUT / "jockeys" / "all.json", {"updatedAt": int(datetime.datetime.now().timestamp() * 1000), "source": "getcurrentjockeyinfo", "jockeys": out})

def trainers():
    """조교사 성적: API19_1(조교사 상세정보) 후보 주소를 차례로 시도, 안 되면 API27_1 통산기록(pr_gubun=2). 원본 항목을 그대로 저장."""
    found = None
    for op in ["API19_1/trainerInfo_1", "API19_1/trainerInfo", "API19_1/getTrainerInfo", "API19_1/currentTrainerInfo"]:
        items = []
        try:
            for m in MEETS:
                for it in get(op, meet=m, numOfRows=300):
                    it["_meet"] = m
                    items.append(it)
        except Exception as e:
            print("trainer try", op, "failed:", str(e)[:80]); items = []
        if items:
            found = (op, items); break
    if not found:
        items = []
        try:
            for m in MEETS:
                for it in get("API27_1/totalRecord_1", meet=m, pr_gubun=2, numOfRows=300):
                    it["_meet"] = m
                    items.append(it)
        except Exception as e:
            print("trainer totalRecord failed:", str(e)[:80])
        if items:
            found = ("API27_1/totalRecord_1", items)
    if found:
        save(OUT / "trainers" / "all.json", {"updatedAt": int(datetime.datetime.now().timestamp() * 1000), "source": found[0], "items": found[1]})
    else:
        print("trainers: nothing fetched")

if __name__ == "__main__":
    dates = sys.argv[1:] or [TODAY]
    for d in dates:
        entry(d)
    try:
        jockeys()
    except Exception as e:
        print("jockeys failed:", e)
    try:
        trainers()
    except Exception as e:
        print("trainers failed:", e)
    results()
