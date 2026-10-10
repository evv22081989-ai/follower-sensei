#!/usr/bin/env python3
"""Instagram audience analysis from CSV follower exports.

Works with files from the Follower Tracker extension and from other services: columns
(name, link or username, status) are detected automatically by header and content.
Python standard library only; sends nothing to the network.

Commands:
  inspect FILE                 columns, row count, how name, link and status were detected
  changes FILE                 status table (new / unfollowed / stayed):
                               numbers per group, CSV per group in --out-dir
  compare OLD NEW              two lists from different dates: who arrived and who left
                               (--out-gained/--out-lost FILE to save as CSV)
  mutual FOLLOWERS FOLLOWING   mutual follows, not following back, fans
  profile FILE                 approximate audience composition from names and usernames
  sample FILE                  random sample of profiles for manual review

Global options (go BEFORE the command):
  --name-col NAME   profile name column
  --url-col NAME    link (or username) column
  --status-col NAME status column
  --json            JSON output
changes options: --out-dir DIR --map "value=new|unfollowed|stayed" (repeatable) --show 30
sample options: --n 40 --seed 1 --out sample.md
profile options: --examples 5
"""
import argparse, csv, io, json, random, re, sys
from collections import Counter, defaultdict

URL_HINTS = ["url", "link", "href", "profile", "ссылка", "профиль", "username", "user name", "login", "логин",
             "handle", "nick", "ник", "account", "аккаунт", "instagram", "инстаграм"]
HANDLE_RE = re.compile(r"^@?[A-Za-z0-9._]{1,30}$")
NAME_HINTS = ["full name", "fullname", "full_name", "name", "имя", "display"]

# Keywords in a profile name -> field. Rough heuristic, indicative only.
# Keywords cover English and Russian, since profile names come in both.
SPHERES = {
    "Beauty": ["nail", "ногт", "маникюр", "manicure", "brow", "бров", "lash", "ресниц", "визаж", "makeup", "make up",
                "beauty", "бьюти", "косметолог", "cosmetolog", "hair", "волос", "парикмах", "barber", "барбер", "salon", "салон", "spa", "спа", "эпиляц", "депиляц"],
    "Health and psychology": ["психолог", "psycholog", "психотерап", "therap", "нутрициолог", "nutrition", "врач", "doctor", "dr.",
                              "стоматолог", "dent", "клиник", "clinic", "массаж", "massage", "остеопат", "health", "здоров"],
    "Sports and fitness": ["fitness", "фитнес", "trainer", "тренер", "coach fit", "yoga", "йога", "pilates", "пилатес", "sport", "спорт", "gym"],
    "Food and restaurants": ["cafe", "кафе", "кофе", "coffee", "restaurant", "ресторан", "food", "еда", "кондитер", "торт", "cake",
                        "bakery", "пекарн", "chef", "шеф", "pizza", "пицц", "sushi", "суши", "доставка еды", "кулинар"],
    "Education": ["school", "школ", "курс", "course", "academy", "академ", "обучени", "учител", "teacher", "репетитор", "tutor", "english", "английск", "university", "университет"],
    "Marketing and SMM": ["smm", "маркет", "market", "таргет", "target", "агентств", "agency", "продвижен", "promo", "контент", "content", "копирайт", "copywrit", "seo"],
    "Photo, video, design": ["photo", "фото", "video", "видео", "reels", "дизайн", "design", "illustr", "иллюстр", "художник", "artist", "creative", "креатив"],
    "Fashion and shops": ["одежд", "wear", "fashion", "мода", "стилист", "stylist", "boutique", "бутик", "showroom", "шоурум", "jewel", "украшен", "handmade", "хендмейд"],
    "Real estate, renovation, construction": ["недвиж", "realty", "estate", "риелтор", "realtor", "ремонт", "repair", "строит", "build", "интерьер", "interior", "мебел", "furniture"],
    "Travel": ["travel", "путешеств", "tour", "отель", "hotel", "hostel"],
    "Business and finance": ["бизнес", "business", "предприним", "entrepreneur", "финанс", "finance", "инвест", "invest", "юрист", "lawyer", "адвокат", "бухгалт", "account", "консалт", "consult", "ceo", "founder", "основател", "эксперт", "expert"],
    "Bloggers and media": ["blog", "блог", "influenc", "media", "медиа", "podcast", "подкаст", "news", "новост", "журнал", "magazine"],
}
BIZ_MARKERS = ["official", "официальн", "shop", "store", "studio", "студия", "салон", "магазин", "доставка", "заказ", "order", "ltd", "llc", "ооо", "ип "]
SEPARATORS = re.compile(r"[|•·/✨🔥💅📍—–]|\s-\s")
VOWELS = set("aeiouyаеёиоуыэюя")

STATUS_HINTS = ["status", "статус", "state", "состояние", "change", "изменени", "event", "событ"]
# Status values from Follower Tracker and common variants from other services (English and Russian).
STATUS_VALUES = {
    "new": ["recent follow", "recent follower", "new", "new follower", "followed", "follow", "follower gained",
            "gained", "joined", "subscribed", "новый", "новая", "новые", "новый подписчик", "подписался",
            "подписалась", "подписались", "пришёл", "пришел", "пришла"],
    "unfollowed": ["unfollowed", "unfollow", "unfollower", "lost", "left", "removed", "gone", "unsubscribed",
                   "отписался", "отписалась", "отписались", "отписка", "ушёл", "ушел", "ушла", "потерян"],
    "stayed": ["stayed", "stay", "kept", "remained", "remain", "existing", "same", "unchanged", "old",
               "остался", "осталась", "остались", "без изменений", "прежний"],
}
GROUP_LABELS = {"new": "new (recent follow)", "unfollowed": "unfollowed", "stayed": "stayed"}


def read_csv(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp1251", "latin-1"):
        try:
            text = raw.decode(enc); break
        except UnicodeDecodeError:
            continue
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    rows = [r for r in reader if any((v or "").strip() for v in r.values() if isinstance(v, str))]
    return reader.fieldnames or [], rows


def norm_status(v):
    return re.sub(r"[\s_\-]+", " ", (v or "").strip().lower())


def status_lookup(extra=None):
    table = {norm_status(v): g for g, vals in STATUS_VALUES.items() for v in vals}
    for item in extra or []:
        if "=" not in item:
            sys.exit(f"--map expects 'value=new|unfollowed|stayed', got: {item}")
        val, grp = item.rsplit("=", 1)
        if grp.strip() not in STATUS_VALUES:
            sys.exit(f"Group must be new, unfollowed or stayed, got: {grp}")
        table[norm_status(val)] = grp.strip()
    return table


def detect_status_col(fields, rows, forced=None):
    if forced:
        if forced not in fields:
            sys.exit(f"Column '{forced}' not found. Available: {fields}")
        return forced
    low = {f.lower().strip(): f for f in fields}
    by_name = next((orig for h in STATUS_HINTS for l, orig in low.items() if h in l), None)
    if by_name:
        return by_name
    known = status_lookup()
    sample = rows[:300]
    for f in fields:  # by content: nearly all values are known statuses
        vals = [norm_status(r.get(f)) for r in sample if (r.get(f) or "").strip()]
        if vals and sum(v in known for v in vals) / len(vals) >= 0.8:
            return f
    return None


def detect_cols(fields, rows, name_col=None, url_col=None, status_col=None):
    fields = [f for f in fields if f != status_col]
    for forced in (name_col, url_col):
        if forced and forced not in fields:
            sys.exit(f"Column '{forced}' not found. Available: {fields}")
    if not url_col:
        # by content: the column where instagram.com appears most
        best, score = None, 0
        for f in fields:
            s = sum(1 for r in rows[:200] if "instagram.com" in (r.get(f) or "").lower())
            if s > score:
                best, score = f, s
        if not best:
            low = {f.lower().strip(): f for f in fields}
            best = next((orig for h in URL_HINTS for l, orig in low.items() if h in l), None)
        if not best:  # by content: the column where nearly all values look like usernames
            for f in fields:
                vals = [(r.get(f) or "").strip() for r in rows[:200] if (r.get(f) or "").strip()]
                if vals and sum(bool(HANDLE_RE.match(v)) for v in vals) / len(vals) >= 0.9 \
                        and len(set(vals)) / len(vals) > 0.9:
                    best = f; break
        url_col = best
    if not name_col:
        low = {f.lower().strip(): f for f in fields if f != url_col}
        name_col = next((orig for h in NAME_HINTS for l, orig in low.items() if h in l), None)
        if not name_col:
            rest = [f for f in fields if f != url_col]
            name_col = rest[0] if rest else None
    return name_col, url_col


def username_of(value):
    v = (value or "").strip()
    m = re.search(r"instagram\.com/([^/?#\s]+)", v, re.I)
    if m:
        v = m.group(1)
    return v.lstrip("@").strip("/").lower()


def load(path, a):
    fields, rows = read_csv(path)
    status_col = detect_status_col(fields, rows, a.status_col)
    name_col, url_col = detect_cols(fields, rows, a.name_col, a.url_col, status_col)
    a._status_col = status_col
    people = {}
    for r in rows:
        key = username_of(r.get(url_col)) if url_col else ""
        name = (r.get(name_col) or "").strip() if name_col else ""
        if not key:
            key = name.lower()
        if key:
            people[key] = {"username": key, "name": name, "url": (r.get(url_col) or "").strip() if url_col else "",
                           "status": (r.get(status_col) or "").strip() if status_col else ""}
    return fields, rows, name_col, url_col, people


def out(result, as_json):
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2)); return
    for k, v in result.items():
        if isinstance(v, list):
            print(f"\n{k} ({len(v)}):")
            for x in v[:200]:
                print(f"  {x}")
            if len(v) > 200:
                print(f"  ... and {len(v) - 200} more")
        elif isinstance(v, dict):
            print(f"\n{k}:")
            for kk, vv in v.items():
                print(f"  {kk}: {vv}")
        else:
            print(f"{k}: {v}")


def pct(n, total):
    return round(n / total * 100, 1) if total else 0.0


def cmd_inspect(a):
    fields, rows, nc, uc, people = load(a.file, a)
    sc = a._status_col
    res = {"file": a.file, "rows": len(rows), "unique profiles": len(people),
           "columns": ", ".join(fields), "name column": nc, "link column": uc,
           "status column": sc or "none (plain follower list)"}
    if sc:
        known = status_lookup()
        vals = Counter(p["status"] for p in people.values())
        res["status values"] = {(v or "<empty>"): f"{c} → {GROUP_LABELS.get(known.get(norm_status(v)), 'NOT RECOGNIZED')}"
                                   for v, c in vals.most_common()}
    res["sample rows"] = [json.dumps(p, ensure_ascii=False) for p in list(people.values())[:3]]
    out(res, a.json)


def write_list(path, items):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["Name", "Profile URL"])
        for p in sorted(items, key=lambda x: x["username"]):
            w.writerow([p["name"], p["url"] or f"https://www.instagram.com/{p['username']}/"])


def cmd_changes(a):
    import os
    *_, people = load(a.file, a)
    if not a._status_col:
        sys.exit("No status column found in the file. Set it with --status-col, "
                 "or compare two lists from different dates with the compare command.")
    table = status_lookup(a.map)
    groups, unknown = defaultdict(list), Counter()
    for p in people.values():
        g = table.get(norm_status(p["status"]))
        if g:
            groups[g].append(p)
        else:
            unknown[p["status"] or "<empty>"] += 1
    new, lost, stayed = len(groups["new"]), len(groups["unfollowed"]), len(groups["stayed"])
    before, after = stayed + lost, stayed + new
    res = {"status column": a._status_col,
           "before (stayed + unfollowed)": before, "after (stayed + new)": after,
           "arrived": new, "left": lost, "net change": new - lost,
           "growth, % of previous base": pct(new - lost, before), "churn, % of previous base": pct(lost, before)}
    if not stayed:
        res["warning"] = ("The file has no 'stayed' rows, so the previous base can't be calculated "
                          "and percentages aren't meaningful. Use the absolute numbers.")
    if unknown:
        res["UNRECOGNIZED status values (ask the user, then pass --map)"] = dict(unknown.most_common())
    if a.out_dir:
        os.makedirs(a.out_dir, exist_ok=True)
        for g in ("new", "unfollowed", "stayed"):
            if groups[g]:
                write_list(os.path.join(a.out_dir, f"{g}.csv"), groups[g])
        res["saved"] = f"{a.out_dir}/new.csv, unfollowed.csv, stayed.csv; run profile on each"
    for g in ("new", "unfollowed"):
        names = sorted(p["username"] for p in groups[g])
        res[f"{GROUP_LABELS[g]}, first {a.show}"] = names[:a.show]
    out(res, a.json)


def cmd_compare(a):
    *_, old = load(a.old, a)
    *_, new = load(a.new, a)
    o, n = set(old), set(new)
    gained, lost = n - o, o - n
    for path, keys, src in ((a.out_gained, gained, new), (a.out_lost, lost, old)):
        if path:
            write_list(path, [src[k] for k in keys])
    base = len(o) or 1
    out({"before": len(o), "after": len(n), "net change": len(n) - len(o),
         "growth, %": round((len(n) - len(o)) / base * 100, 2),
         "arrived": len(gained), "left": len(lost), "churn, % of base": round(len(lost) / base * 100, 2),
         "new followers": sorted(gained), "unfollowers": sorted(lost)}, a.json)


def cmd_mutual(a):
    *_, fol = load(a.followers, a)
    *_, fng = load(a.following, a)
    f, g = set(fol), set(fng)
    out({"followers": len(f), "following": len(g), "mutual": sorted(f & g),
         "not following back": sorted(g - f), "fans (you don't follow them)": sorted(f - g)}, a.json)


def script_of(name):
    cyr = len(re.findall(r"[а-яёА-ЯЁ]", name)); lat = len(re.findall(r"[a-zA-Z]", name))
    other = len(re.findall(r"[^\W\d_a-zA-Zа-яёА-ЯЁ]", name))
    if not (cyr or lat or other):
        return "no letters / empty"
    top = max((cyr, "Cyrillic"), (lat, "Latin"), (other, "other scripts"))
    return top[1]


def suspicious(username, name):
    """Weak signs of a bot or throwaway account. Only a "check this" flag."""
    reasons = []
    u = re.sub(r"[._]", "", username)
    digits = sum(c.isdigit() for c in u)
    if digits >= 6 or (digits >= 4 and digits / max(len(u), 1) > 0.5):
        reasons.append("many digits in username")
    for part in re.split(r"[._\d]+", username.lower()):
        lt = [c for c in part if c.isalpha()]
        run = max((len(m) for m in re.findall(r"[^aeiouyаеёиоуыэюя\W\d_]+", part)), default=0)
        if len(lt) >= 7 and sum(c in VOWELS for c in lt) / len(lt) < 0.2 and run >= 5:
            reasons.append("random-looking letters"); break
    if not name.strip() and digits >= 3:
        reasons.append("empty name + digits in username")
    return reasons


_SPHERE_RE = {s: re.compile(r"(?<![^\W_])(?:" + "|".join(re.escape(k) for k in kws) + ")", re.I)
              for s, kws in SPHERES.items()}


def classify(text):
    # a keyword must start at a word boundary, so a short keyword isn't matched inside a longer word
    return [s for s, rx in _SPHERE_RE.items() if rx.search(text)]


def cmd_profile(a):
    *_, people = load(a.file, a)
    total = len(people)
    sphere_count, sphere_ex = Counter(), defaultdict(list)
    scripts, kinds = Counter(), Counter()
    susp, unclassified_desc = [], []
    for p in people.values():
        name, user = p["name"], p["username"]
        scripts[script_of(name)] += 1
        spheres = classify(name + " " + user.replace("_", " ").replace(".", " "))
        has_desc = bool(SEPARATORS.search(name)) or len(name.split()) >= 4
        biz = any(m in (" " + name.lower() + " " + user) for m in BIZ_MARKERS)
        if not name.strip():
            kinds["empty name"] += 1
        elif spheres or biz:
            kinds["looks like a business/specialist (field in name)"] += 1
        elif has_desc:
            kinds["name has a description, field not recognized"] += 1
            unclassified_desc.append(f"{user} — {name}")
        else:
            kinds["name only (probably a personal profile)"] += 1
        for s in spheres:
            sphere_count[s] += 1
            if len(sphere_ex[s]) < a.examples and (name or user) not in sphere_ex[s]:
                sphere_ex[s].append(name or user)
        r = suspicious(user, name)
        if r:
            susp.append(f"{user} ({', '.join(r)})")
    out({
        "profiles": total,
        "profile type by name": {k: f"{v} ({pct(v, total)}%)" for k, v in kinds.most_common()},
        "fields by keyword (a profile can be in several)": {
            s: f"{c} ({pct(c, total)}%) — e.g.: {'; '.join(sphere_ex[s])}" for s, c in sphere_count.most_common()},
        "name alphabet": {k: f"{v} ({pct(v, total)}%)" for k, v in scripts.most_common()},
        "suspicious — check by hand": f"{len(susp)} ({pct(len(susp), total)}%)",
        "suspicious examples": susp[:30],
        "described but field not recognized (classify these yourself)": unclassified_desc[:300],
        "note": "Heuristic based on names and usernames: indicative, not a precise portrait. Most people put only their name in the profile name.",
    }, a.json)


def cmd_sample(a):
    *_, people = load(a.file, a)
    items = list(people.values())
    rnd = random.Random(a.seed)
    chosen = rnd.sample(items, min(a.n, len(items)))
    lines = [f"# Sample for manual review: {len(chosen)} of {len(items)} profiles", "",
             "Open each profile and fill in the columns. Type: personal / specialist / business / creator / bot?",
             "", "| # | Profile | Type | Field | City | Notes |", "|---|---|---|---|---|---|"]
    for i, p in enumerate(chosen, 1):
        link = p["url"] if p["url"].startswith("http") else f"https://www.instagram.com/{p['username']}/"
        label = (p["name"] or p["username"]).replace("|", "/")
        lines.append(f"| {i} | [{label}]({link}) |  |  |  |  |")
    text = "\n".join(lines) + "\n"
    if a.out:
        open(a.out, "w", encoding="utf-8").write(text)
        print(f"Saved: {a.out}")
    else:
        print(text)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--name-col"); p.add_argument("--url-col"); p.add_argument("--status-col")
    p.add_argument("--json", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("inspect"); s.add_argument("file"); s.set_defaults(fn=cmd_inspect)
    s = sub.add_parser("changes"); s.add_argument("file"); s.add_argument("--out-dir")
    s.add_argument("--map", action="append", default=[]); s.add_argument("--show", type=int, default=30)
    s.set_defaults(fn=cmd_changes)
    s = sub.add_parser("compare"); s.add_argument("old"); s.add_argument("new")
    s.add_argument("--out-gained"); s.add_argument("--out-lost"); s.set_defaults(fn=cmd_compare)
    s = sub.add_parser("mutual"); s.add_argument("followers"); s.add_argument("following"); s.set_defaults(fn=cmd_mutual)
    s = sub.add_parser("profile"); s.add_argument("file"); s.add_argument("--examples", type=int, default=5); s.set_defaults(fn=cmd_profile)
    s = sub.add_parser("sample"); s.add_argument("file"); s.add_argument("--n", type=int, default=40)
    s.add_argument("--seed", type=int, default=None); s.add_argument("--out"); s.set_defaults(fn=cmd_sample)
    a = p.parse_args(); a.fn(a)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:  # output was cut short (e.g. piped to head); not an error
        sys.stderr.close()
