#!/usr/bin/env python3
"""Анализ аудитории Instagram по CSV-выгрузкам подписчиков.

Подходит для файлов из расширения Follower Tracker и из других сервисов: колонки
(имя, ссылка или ник, статус) определяются автоматически по названиям и содержимому.
Только стандартная библиотека Python, ничего не отправляет в сеть.

Команды:
  inspect FILE                 колонки, число строк, как распознаны имя, ссылка и статус
  changes FILE                 таблица со статусами (новые / отписались / остались):
                               цифры по группам, CSV по группам в --out-dir
  compare OLD NEW              два списка за разные даты: кто пришёл и кто ушёл
                               (--out-gained/--out-lost FILE — сохранить в CSV)
  mutual FOLLOWERS FOLLOWING   взаимные, не подписаны в ответ, фанаты
  profile FILE                 примерный состав аудитории по именам и никам (сводка)
  sample FILE                  случайная выборка профилей для ручного разбора

Общие опции (ставятся ПЕРЕД командой):
  --name-col NAME   колонка с именем профиля
  --url-col NAME    колонка со ссылкой (или ником)
  --status-col NAME колонка со статусом
  --json            вывод в JSON
Опции changes: --out-dir DIR --map "значение=new|unfollowed|stayed" (можно несколько) --show 30
Опции sample: --n 40 --seed 1 --out sample.md
Опции profile: --examples 5
"""
import argparse, csv, io, json, random, re, sys
from collections import Counter, defaultdict

URL_HINTS = ["url", "link", "href", "profile", "ссылка", "профиль", "username", "user name", "login", "логин",
             "handle", "nick", "ник", "account", "аккаунт", "instagram", "инстаграм"]
HANDLE_RE = re.compile(r"^@?[A-Za-z0-9._]{1,30}$")
NAME_HINTS = ["full name", "fullname", "full_name", "name", "имя", "display"]

# Ключевые слова в имени профиля -> сфера. Грубая эвристика: только как ориентир.
SPHERES = {
    "Красота": ["nail", "ногт", "маникюр", "manicure", "brow", "бров", "lash", "ресниц", "визаж", "makeup", "make up",
                "beauty", "бьюти", "косметолог", "cosmetolog", "hair", "волос", "парикмах", "barber", "барбер", "salon", "салон", "spa", "спа", "эпиляц", "депиляц"],
    "Здоровье и психология": ["психолог", "psycholog", "психотерап", "therap", "нутрициолог", "nutrition", "врач", "doctor", "dr.",
                              "стоматолог", "dent", "клиник", "clinic", "массаж", "massage", "остеопат", "health", "здоров"],
    "Спорт и фитнес": ["fitness", "фитнес", "trainer", "тренер", "coach fit", "yoga", "йога", "pilates", "пилатес", "sport", "спорт", "gym"],
    "Еда и рестораны": ["cafe", "кафе", "кофе", "coffee", "restaurant", "ресторан", "food", "еда", "кондитер", "торт", "cake",
                        "bakery", "пекарн", "chef", "шеф", "pizza", "пицц", "sushi", "суши", "доставка еды", "кулинар"],
    "Образование": ["school", "школ", "курс", "course", "academy", "академ", "обучени", "учител", "teacher", "репетитор", "tutor", "english", "английск", "university", "университет"],
    "Маркетинг и SMM": ["smm", "маркет", "market", "таргет", "target", "агентств", "agency", "продвижен", "promo", "контент", "content", "копирайт", "copywrit", "seo"],
    "Фото, видео, дизайн": ["photo", "фото", "video", "видео", "reels", "дизайн", "design", "illustr", "иллюстр", "художник", "artist", "creative", "креатив"],
    "Мода и магазины": ["одежд", "wear", "fashion", "мода", "стилист", "stylist", "boutique", "бутик", "showroom", "шоурум", "jewel", "украшен", "handmade", "хендмейд"],
    "Недвижимость, ремонт, строительство": ["недвиж", "realty", "estate", "риелтор", "realtor", "ремонт", "repair", "строит", "build", "интерьер", "interior", "мебел", "furniture"],
    "Путешествия": ["travel", "путешеств", "tour", "отель", "hotel", "hostel"],
    "Бизнес и финансы": ["бизнес", "business", "предприним", "entrepreneur", "финанс", "finance", "инвест", "invest", "юрист", "lawyer", "адвокат", "бухгалт", "account", "консалт", "consult", "ceo", "founder", "основател", "эксперт", "expert"],
    "Блогеры и медиа": ["blog", "блог", "influenc", "media", "медиа", "podcast", "подкаст", "news", "новост", "журнал", "magazine"],
}
BIZ_MARKERS = ["official", "официальн", "shop", "store", "studio", "студия", "салон", "магазин", "доставка", "заказ", "order", "ltd", "llc", "ооо", "ип "]
SEPARATORS = re.compile(r"[|•·/✨🔥💅📍—–]|\s-\s")
VOWELS = set("aeiouyаеёиоуыэюя")

STATUS_HINTS = ["status", "статус", "state", "состояние", "change", "изменени", "event", "событ"]
# Значения статуса из Follower Tracker и типичные варианты из других сервисов.
STATUS_VALUES = {
    "new": ["recent follow", "recent follower", "new", "new follower", "followed", "follow", "follower gained",
            "gained", "joined", "subscribed", "новый", "новая", "новые", "новый подписчик", "подписался",
            "подписалась", "подписались", "пришёл", "пришел", "пришла"],
    "unfollowed": ["unfollowed", "unfollow", "unfollower", "lost", "left", "removed", "gone", "unsubscribed",
                   "отписался", "отписалась", "отписались", "отписка", "ушёл", "ушел", "ушла", "потерян"],
    "stayed": ["stayed", "stay", "kept", "remained", "remain", "existing", "same", "unchanged", "old",
               "остался", "осталась", "остались", "без изменений", "прежний"],
}
GROUP_LABELS = {"new": "новые (recent follow)", "unfollowed": "отписались (unfollowed)", "stayed": "остались (stayed)"}


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
            sys.exit(f"--map ожидает 'значение=new|unfollowed|stayed', получено: {item}")
        val, grp = item.rsplit("=", 1)
        if grp.strip() not in STATUS_VALUES:
            sys.exit(f"Группа должна быть new, unfollowed или stayed, получено: {grp}")
        table[norm_status(val)] = grp.strip()
    return table


def detect_status_col(fields, rows, forced=None):
    if forced:
        if forced not in fields:
            sys.exit(f"Колонка '{forced}' не найдена. Есть: {fields}")
        return forced
    low = {f.lower().strip(): f for f in fields}
    by_name = next((orig for h in STATUS_HINTS for l, orig in low.items() if h in l), None)
    if by_name:
        return by_name
    known = status_lookup()
    sample = rows[:300]
    for f in fields:  # по содержимому: почти все значения — известные статусы
        vals = [norm_status(r.get(f)) for r in sample if (r.get(f) or "").strip()]
        if vals and sum(v in known for v in vals) / len(vals) >= 0.8:
            return f
    return None


def detect_cols(fields, rows, name_col=None, url_col=None, status_col=None):
    fields = [f for f in fields if f != status_col]
    for forced in (name_col, url_col):
        if forced and forced not in fields:
            sys.exit(f"Колонка '{forced}' не найдена. Есть: {fields}")
    if not url_col:
        # по содержимому: колонка, где чаще всего встречается instagram.com
        best, score = None, 0
        for f in fields:
            s = sum(1 for r in rows[:200] if "instagram.com" in (r.get(f) or "").lower())
            if s > score:
                best, score = f, s
        if not best:
            low = {f.lower().strip(): f for f in fields}
            best = next((orig for h in URL_HINTS for l, orig in low.items() if h in l), None)
        if not best:  # по содержимому: колонка, где почти все значения похожи на ники
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
                print(f"  ... и ещё {len(v) - 200}")
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
    res = {"файл": a.file, "строк": len(rows), "уникальных профилей": len(people),
           "колонки": ", ".join(fields), "колонка имени": nc, "колонка ссылки": uc,
           "колонка статуса": sc or "нет (обычный список подписчиков)"}
    if sc:
        known = status_lookup()
        vals = Counter(p["status"] for p in people.values())
        res["значения статуса"] = {(v or "<пусто>"): f"{c} → {GROUP_LABELS.get(known.get(norm_status(v)), 'НЕ РАСПОЗНАНО')}"
                                   for v, c in vals.most_common()}
    res["пример"] = [json.dumps(p, ensure_ascii=False) for p in list(people.values())[:3]]
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
        sys.exit("В файле не найдена колонка статуса. Укажите её через --status-col, "
                 "или сравните два списка за разные даты командой compare.")
    table = status_lookup(a.map)
    groups, unknown = defaultdict(list), Counter()
    for p in people.values():
        g = table.get(norm_status(p["status"]))
        if g:
            groups[g].append(p)
        else:
            unknown[p["status"] or "<пусто>"] += 1
    new, lost, stayed = len(groups["new"]), len(groups["unfollowed"]), len(groups["stayed"])
    before, after = stayed + lost, stayed + new
    res = {"колонка статуса": a._status_col,
           "было (остались + отписались)": before, "стало (остались + новые)": after,
           "пришло": new, "ушло": lost, "изменение": new - lost,
           "прирост, % от прежней базы": pct(new - lost, before), "отток, % от прежней базы": pct(lost, before)}
    if not stayed:
        res["внимание"] = ("В файле нет строк «остались» — прежнюю базу посчитать нельзя, "
                           "проценты не показательны. Смотрите абсолютные цифры.")
    if unknown:
        res["НЕРАСПОЗНАННЫЕ значения статуса (уточните у пользователя и передайте --map)"] = dict(unknown.most_common())
    if a.out_dir:
        os.makedirs(a.out_dir, exist_ok=True)
        for g in ("new", "unfollowed", "stayed"):
            if groups[g]:
                write_list(os.path.join(a.out_dir, f"{g}.csv"), groups[g])
        res["сохранено"] = f"{a.out_dir}/new.csv, unfollowed.csv, stayed.csv — запустите profile по каждому"
    for g in ("new", "unfollowed"):
        names = sorted(p["username"] for p in groups[g])
        res[f"{GROUP_LABELS[g]}, первые {a.show}"] = names[:a.show]
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
    out({"было": len(o), "стало": len(n), "изменение": len(n) - len(o),
         "прирост, %": round((len(n) - len(o)) / base * 100, 2),
         "пришло": len(gained), "ушло": len(lost), "отток, % от базы": round(len(lost) / base * 100, 2),
         "новые": sorted(gained), "ушедшие (отписки)": sorted(lost)}, a.json)


def cmd_mutual(a):
    *_, fol = load(a.followers, a)
    *_, fng = load(a.following, a)
    f, g = set(fol), set(fng)
    out({"подписчиков": len(f), "подписок": len(g), "взаимные": sorted(f & g),
         "не подписаны в ответ": sorted(g - f), "фанаты (вы не подписаны)": sorted(f - g)}, a.json)


def script_of(name):
    cyr = len(re.findall(r"[а-яёА-ЯЁ]", name)); lat = len(re.findall(r"[a-zA-Z]", name))
    other = len(re.findall(r"[^\W\d_a-zA-Zа-яёА-ЯЁ]", name))
    if not (cyr or lat or other):
        return "без букв / пусто"
    top = max((cyr, "кириллица"), (lat, "латиница"), (other, "другие алфавиты"))
    return top[1]


def suspicious(username, name):
    """Слабые признаки бота/технического аккаунта. Только пометка «проверить»."""
    reasons = []
    u = re.sub(r"[._]", "", username)
    digits = sum(c.isdigit() for c in u)
    if digits >= 6 or (digits >= 4 and digits / max(len(u), 1) > 0.5):
        reasons.append("много цифр в нике")
    for part in re.split(r"[._\d]+", username.lower()):
        lt = [c for c in part if c.isalpha()]
        run = max((len(m) for m in re.findall(r"[^aeiouyаеёиоуыэюя\W\d_]+", part)), default=0)
        if len(lt) >= 7 and sum(c in VOWELS for c in lt) / len(lt) < 0.2 and run >= 5:
            reasons.append("случайный набор букв"); break
    if not name.strip() and digits >= 3:
        reasons.append("пустое имя + цифры в нике")
    return reasons


_SPHERE_RE = {s: re.compile(r"(?<![^\W_])(?:" + "|".join(re.escape(k) for k in kws) + ")", re.I)
              for s, kws in SPHERES.items()}


def classify(text):
    # ключевое слово должно начинаться с начала слова: «арт» не найдётся внутри «квартир»
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
            kinds["пустое имя"] += 1
        elif spheres or biz:
            kinds["похоже на бизнес/специалиста (сфера в имени)"] += 1
        elif has_desc:
            kinds["в имени есть описание, сфера не распознана"] += 1
            unclassified_desc.append(f"{user} — {name}")
        else:
            kinds["только имя (вероятно, личный профиль)"] += 1
        for s in spheres:
            sphere_count[s] += 1
            if len(sphere_ex[s]) < a.examples and (name or user) not in sphere_ex[s]:
                sphere_ex[s].append(name or user)
        r = suspicious(user, name)
        if r:
            susp.append(f"{user} ({', '.join(r)})")
    out({
        "профилей": total,
        "тип профиля по имени, % ": {k: f"{v} ({pct(v, total)}%)" for k, v in kinds.most_common()},
        "сферы по ключевым словам (профиль может попасть в несколько)": {
            s: f"{c} ({pct(c, total)}%) — напр.: {'; '.join(sphere_ex[s])}" for s, c in sphere_count.most_common()},
        "алфавит имени": {k: f"{v} ({pct(v, total)}%)" for k, v in scripts.most_common()},
        "подозрительные — проверить вручную": f"{len(susp)} ({pct(len(susp), total)}%)",
        "примеры подозрительных": susp[:30],
        "описание есть, но сфера не распознана (классифицируй сам)": unclassified_desc[:300],
        "примечание": "Эвристика по именам и никам: ориентир, а не точный портрет. Большинство людей указывают в имени только имя.",
    }, a.json)


def cmd_sample(a):
    *_, people = load(a.file, a)
    items = list(people.values())
    rnd = random.Random(a.seed)
    chosen = rnd.sample(items, min(a.n, len(items)))
    lines = [f"# Выборка для ручного разбора: {len(chosen)} из {len(items)} профилей", "",
             "Откройте каждый профиль и заполните колонки. Тип: личный / специалист / бизнес / блогер / бот?.",
             "", "| № | Профиль | Тип | Сфера | Город | Заметки |", "|---|---|---|---|---|---|"]
    for i, p in enumerate(chosen, 1):
        link = p["url"] if p["url"].startswith("http") else f"https://www.instagram.com/{p['username']}/"
        label = (p["name"] or p["username"]).replace("|", "/")
        lines.append(f"| {i} | [{label}]({link}) |  |  |  |  |")
    text = "\n".join(lines) + "\n"
    if a.out:
        open(a.out, "w", encoding="utf-8").write(text)
        print(f"Сохранено: {a.out}")
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
    except BrokenPipeError:  # вывод обрезан (например, через head) — это не ошибка
        sys.stderr.close()
