# -*- coding: utf-8 -*-
# conjugaison_core.py - 法语变位练习器核心逻辑

import csv
import random
import os
import json
import shutil
import unicodedata
import sys
from datetime import datetime, timedelta
from collections import defaultdict


# ====================================================================
#                          路径配置
# ====================================================================

def get_base_dir():
    """获取用户数据目录（exe 同目录）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_resource_dir():
    """获取资源文件目录（wordlists 所在目录）"""
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            return sys._MEIPASS
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = get_base_dir()
RESOURCE_DIR = get_resource_dir()

FILES = {
    'erreurs': os.path.join(BASE_DIR, "erreurs.csv"),
    'stats': os.path.join(BASE_DIR, "stats.json"),
    'settings': os.path.join(BASE_DIR, "settings.json"),
    'maitrises': os.path.join(BASE_DIR, "maitrises.json"),
    'review': os.path.join(BASE_DIR, "review.json"),
    'progress': os.path.join(BASE_DIR, "progress.json"),
    'review_progress': os.path.join(BASE_DIR, "review_progress.json"),
}


# ====================================================================
#                       数据备份/恢复
# ====================================================================

def backup_file(fichier):
    if os.path.exists(fichier):
        try:
            shutil.copy2(fichier, fichier + ".bak")
            return True
        except:
            return False
    return False


def restore_from_backup(fichier):
    backup = fichier + ".bak"
    if os.path.exists(backup):
        try:
            shutil.copy2(backup, fichier)
            return True
        except:
            return False
    return False


def safe_save_json(fichier, donnees):
    backup_file(fichier)
    try:
        with open(fichier, 'w', encoding='utf-8') as f:
            json.dump(donnees, f, ensure_ascii=False, indent=2)
        return True
    except:
        restore_from_backup(fichier)
        return False


# ====================================================================
#                      通用 JSON 加载 / 保存
# ====================================================================

def charger_json(fichier, default):
    if os.path.exists(fichier):
        try:
            with open(fichier, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            if restore_from_backup(fichier):
                try:
                    with open(fichier, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except:
                    pass
    return default


def sauvegarder_json(fichier, donnees):
    return safe_save_json(fichier, donnees)


# ====================================================================
#                        归一化
# ====================================================================

def normalize(s):
    if not isinstance(s, str):
        return ''
    nfkd = unicodedata.normalize('NFKD', s)
    no_marks = ''.join(c for c in nfkd if not unicodedata.combining(c))
    return ''.join(c for c in no_marks if c.isalpha()).lower()


# ====================================================================
#                          词干提取
# ====================================================================

def extraire_stem_et_suffixe(verbe, conjugaison):
    suffixes = ["er", "ir", "re", "oir"]
    stem = None
    for suf in suffixes:
        if verbe.endswith(suf):
            stem = verbe[:-len(suf)]
            break
    if stem is None or not conjugaison.startswith(stem):
        return conjugaison, ""
    return stem, conjugaison[len(stem):]


# ====================================================================
#                        CSV 数据加载（带缓存）
# ====================================================================

def normaliser_personne(personne):
    p = personne.strip().lower()
    if p in ["elle", "il"]:
        return "il"
    elif p in ["elles", "ils"]:
        return "ils"
    return p


_data_cache = {}


def charger_conjugaisons(fichier=None):
    if fichier is None:
        fichier = os.path.join(BASE_DIR, "conjugations.csv")
    
    if not os.path.exists(fichier):
        return {}, []
    
    data_dict = {}
    try:
        with open(fichier, 'r', encoding='utf-8-sig') as f:
            lecteur = csv.reader(f)
            try:
                first_row = next(lecteur)
            except StopIteration:
                return {}, []
            
            if not any('verbe' in col.lower() or '动词' in col for col in first_row):
                if len(first_row) >= 4:
                    try:
                        verbe, temps, personne, conjugaison = [x.strip() for x in first_row[:4]]
                        personne = normaliser_personne(personne)
                        stem, suffixe = extraire_stem_et_suffixe(verbe, conjugaison)
                        data_dict[(verbe, temps, personne)] = (conjugaison, stem, suffixe)
                    except:
                        pass
            
            for ligne in lecteur:
                if len(ligne) < 4:
                    continue
                try:
                    verbe, temps, personne, conjugaison = [x.strip() for x in ligne[:4]]
                    personne = normaliser_personne(personne)
                    stem, suffixe = extraire_stem_et_suffixe(verbe, conjugaison)
                    data_dict[(verbe, temps, personne)] = (conjugaison, stem, suffixe)
                except:
                    continue
    except:
        return {}, []
    
    return data_dict, list(data_dict.keys())


def charger_wordlist(level, temps):
    # 使用 RESOURCE_DIR 读取 wordlists
    fichier = os.path.join(RESOURCE_DIR, "wordlists", level, f"{temps}.csv")
    return charger_conjugaisons(fichier)


def charger_wordlist_cached(level, temps):
    key = f"{level}|{temps}"
    if key not in _data_cache:
        _data_cache[key] = charger_wordlist(level, temps)
    return _data_cache[key]


def clear_cache():
    _data_cache.clear()


def get_available_levels():
    levels = []
    # 使用 RESOURCE_DIR 读取 wordlists
    wordlists_dir = os.path.join(RESOURCE_DIR, "wordlists")
    if os.path.exists(wordlists_dir):
        for level in ["必会", "常用", "生僻"]:
            path = os.path.join(wordlists_dir, level)
            if os.path.exists(path):
                levels.append(level)
    return levels


def get_available_temps(level):
    temps_list = []
    path = os.path.join(RESOURCE_DIR, "wordlists", level)
    if not os.path.exists(path):
        return temps_list
    for f in os.listdir(path):
        if f.endswith(".csv"):
            temps_list.append(f.replace(".csv", ""))
    return temps_list


def get_wordlist_stats(level, temps):
    wl_dict, wl_list = charger_wordlist_cached(level, temps)
    
    classes = set()
    for verbe, t, personne in wl_list:
        classes.add((verbe, t))
    total = len(classes)
    
    maitrises = charger_maitrises()
    maitrise_keys = set(entry_to_key(m['verbe'], m['temps'], m['personne']) for m in maitrises)
    
    mastered = 0
    for verbe, t in classes:
        all_mastered = True
        for personne in ["je", "tu", "il", "nous", "vous", "ils"]:
            if (verbe, t, personne) in wl_dict:
                if entry_to_key(verbe, t, personne) not in maitrise_keys:
                    all_mastered = False
                    break
        if all_mastered:
            mastered += 1
    
    return total, mastered


# ====================================================================
#                       进度管理
# ====================================================================

def charger_progress():
    return charger_json(FILES['progress'], {})


def sauvegarder_progress(progress):
    return sauvegarder_json(FILES['progress'], progress)


def get_progress(level, temps):
    progress = charger_progress()
    return progress.get(level, {}).get(temps, {})


def set_progress(level, temps, data):
    progress = charger_progress()
    if level not in progress:
        progress[level] = {}
    progress[level][temps] = data
    return sauvegarder_progress(progress)


def clear_progress(level, temps):
    progress = charger_progress()
    if level in progress and temps in progress[level]:
        del progress[level][temps]
    return sauvegarder_progress(progress)


# ====================================================================
#                           复习进度管理
# ====================================================================

def charger_review_progress():
    return charger_json(FILES['review_progress'], {})


def sauvegarder_review_progress(progress):
    return sauvegarder_json(FILES['review_progress'], progress)


def get_review_progress():
    return charger_review_progress()


def set_review_progress(data):
    return sauvegarder_review_progress(data)


def clear_review_progress():
    return sauvegarder_review_progress({})


# ====================================================================
#                           错题本
# ====================================================================

def charger_erreurs():
    fichier = FILES['erreurs']
    donnees = {}
    if not os.path.exists(fichier):
        return donnees
    try:
        with open(fichier, 'r', encoding='utf-8') as f:
            lecteur = csv.reader(f)
            next(lecteur)
            for ligne in lecteur:
                if len(ligne) >= 4:
                    try:
                        verbe, temps, personne, conjugaison = [x.strip() for x in ligne[:4]]
                        personne = normaliser_personne(personne)
                        donnees[(verbe, temps, personne)] = conjugaison
                    except:
                        continue
    except:
        return donnees
    return donnees


def sauvegarder_erreur(verbe, temps, personne, conjugaison):
    personne = normaliser_personne(personne)
    existe = os.path.exists(FILES['erreurs'])
    with open(FILES['erreurs'], "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if not existe:
            writer.writerow(["verbe", "temps", "personne", "conjugaison"])
        writer.writerow([verbe, temps, personne, conjugaison])


def ecrire_tout_erreurs(donnees_erreurs):
    with open(FILES['erreurs'], "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["verbe", "temps", "personne", "conjugaison"])
        for (verbe, temps, personne), conjugaison in donnees_erreurs.items():
            writer.writerow([verbe, temps, personne, conjugaison])


def compter_erreurs():
    return len(charger_erreurs())


# ====================================================================
#                       掌握列表 + 天数管理
# ====================================================================

def charger_maitrises():
    return charger_json(FILES['maitrises'], [])


def sauvegarder_maitrises(liste):
    return sauvegarder_json(FILES['maitrises'], liste)


def ajouter_maitrise(verbe, temps, personne, date_learned=None):
    personne = normaliser_personne(personne)
    if date_learned is None:
        date_learned = datetime.now().strftime("%Y-%m-%d")
    liste = charger_maitrises()
    for item in liste:
        if item['verbe'] == verbe and item['temps'] == temps and item['personne'] == personne:
            return False
    liste.append({
        "verbe": verbe,
        "temps": temps,
        "personne": personne,
        "date_learned": date_learned,
        "days": 1,
        "needs_review": False,
        "review_completed": False
    })
    return sauvegarder_maitrises(liste)


def compter_maitrises():
    return len(charger_maitrises())


def remove_from_maitrise(verbe, temps, personne):
    personne = normaliser_personne(personne)
    liste = charger_maitrises()
    liste = [item for item in liste if not (item['verbe'] == verbe and item['temps'] == temps and item['personne'] == personne)]
    sauvegarder_maitrises(liste)
    review_list = charger_review()
    review_list = [r for r in review_list if not (r['verbe'] == verbe and r['temps'] == temps and r['personne'] == personne)]
    sauvegarder_review(review_list)


def update_all_days():
    maitrises = charger_maitrises()
    today = datetime.now().date()
    for item in maitrises:
        date_learned = datetime.strptime(item['date_learned'], "%Y-%m-%d").date()
        days = (today - date_learned).days + 1
        item['days'] = days
    sauvegarder_maitrises(maitrises)


# ====================================================================
#                           复习本
# ====================================================================

def charger_review():
    return charger_json(FILES['review'], [])


def sauvegarder_review(review_list):
    return sauvegarder_json(FILES['review'], review_list)


def update_review_status():
    update_all_days()
    maitrises = charger_maitrises()
    today = datetime.now().date()
    review_list = charger_review()
    review_keys = set((r['verbe'], r['temps'], r['personne']) for r in review_list)

    for item in maitrises:
        days = item.get('days', 1)
        needs = days in [2, 4, 7, 15, 30] and not item.get('review_completed', False)
        key = (item['verbe'], item['temps'], item['personne'])

        if needs and key not in review_keys:
            review_list.append({
                "verbe": item['verbe'],
                "temps": item['temps'],
                "personne": item['personne'],
                "due_date": today.strftime("%Y-%m-%d")
            })
            item['needs_review'] = True
        elif key in review_keys and not needs:
            review_list = [r for r in review_list if (r['verbe'], r['temps'], r['personne']) != key]
            item['needs_review'] = False

    sauvegarder_maitrises(maitrises)
    sauvegarder_review(review_list)
    return review_list


def get_review_list():
    update_review_status()
    return charger_review()


def has_review_needed():
    return len(get_review_list()) > 0


def complete_review(verbe, temps, personne):
    personne = normaliser_personne(personne)
    review_list = charger_review()
    review_list = [r for r in review_list if not (r['verbe'] == verbe and r['temps'] == temps and r['personne'] == personne)]
    sauvegarder_review(review_list)

    maitrises = charger_maitrises()
    for item in maitrises:
        if item['verbe'] == verbe and item['temps'] == temps and item['personne'] == personne:
            item['needs_review'] = False
            item['review_completed'] = True
            break
    sauvegarder_maitrises(maitrises)


def get_review_items_by_verb():
    review_list = get_review_list()
    grouped = defaultdict(list)
    for r in review_list:
        grouped[(r['verbe'], r['temps'])].append(r)
    return grouped


# ====================================================================
#                           统计
# ====================================================================

def charger_statistiques():
    return charger_json(FILES['stats'], {"total": 0, "correct": 0})


def sauvegarder_statistiques(stats):
    return sauvegarder_json(FILES['stats'], stats)


def calculer_taux_reussite(stats):
    total = stats.get('total', 0)
    correct = stats.get('correct', 0)
    return (correct / total * 100) if total > 0 else 0


def incrementer_correct(stats):
    stats['correct'] += 1
    stats['total'] += 1
    return sauvegarder_statistiques(stats)


def incrementer_total(stats):
    stats['total'] += 1
    return sauvegarder_statistiques(stats)


# ====================================================================
#                           设置
# ====================================================================

def charger_settings():
    defaults = {
        "fuzzy": True,
        "show_stem": True,
        "enable_reverse": True,
        "enable_choice": True,
        "enable_fill": True,
        "priority_learn": []
    }
    loaded = charger_json(FILES['settings'], defaults)
    for k in defaults:
        if k not in loaded:
            loaded[k] = defaults[k]
    return loaded


def sauvegarder_settings(settings):
    return sauvegarder_json(FILES['settings'], settings)


# ====================================================================
#                        工具函数
# ====================================================================

def entry_to_key(verbe, temps, personne):
    personne = normaliser_personne(personne)
    return f"{verbe}|{temps}|{personne}"


def get_today():
    return datetime.now().strftime("%Y-%m-%d")


def add_days(date_str, days):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return (dt + timedelta(days=days)).strftime("%Y-%m-%d")


# ====================================================================
#                      获取题目数据
# ====================================================================

def get_question_data(data_dict, entry):
    v = entry["verbe"]
    t = entry["temps"]
    p = normaliser_personne(entry.get("personne", "je"))
    
    if (v, t, p) in data_dict:
        conjugaison, stem, suffixe = data_dict[(v, t, p)]
        return {
            "verbe": v,
            "temps": t,
            "personne": p,
            "conjugaison": conjugaison,
            "stem": stem,
            "suffixe": suffixe,
            "exists": True
        }
    else:
        return {
            "verbe": v,
            "temps": t,
            "personne": p,
            "conjugaison": "—",
            "stem": "",
            "suffixe": "",
            "exists": False
        }


def get_judge_display_data(data_dict, verbe, temps):
    result = {}
    personnes = ["je", "tu", "il", "nous", "vous", "ils"]
    for p in personnes:
        key = (verbe, temps, p)
        if key in data_dict:
            conjugaison, _, _ = data_dict[key]
            result[p] = conjugaison
        else:
            result[p] = "—"
    return result


# ====================================================================
#                       生成干扰项
# ====================================================================

def generer_interferents(verbe, temps, personne, conjugaison, data_dict):
    personne = normaliser_personne(personne)
    pool = []
    for (v, t, p), (c, _, _) in data_dict.items():
        if v == verbe and t == temps and p != personne:
            pool.append(c)
    if len(pool) < 3:
        for (v, t, p), (c, _, _) in data_dict.items():
            if v == verbe and t != temps and p != personne:
                pool.append(c)
    if len(pool) < 3:
        for (v, t, p), (c, _, _) in data_dict.items():
            if v != verbe and p == personne and t == temps:
                pool.append(c)
    unique = []
    seen = set()
    for item in pool:
        if item not in seen and item != conjugaison:
            seen.add(item)
            unique.append(item)
    random.shuffle(unique)
    return unique[:3]


def generer_options(conjugaison, data_dict, verbe, temps, personne):
    personne = normaliser_personne(personne)
    inter = generer_interferents(verbe, temps, personne, conjugaison, data_dict)
    options = [conjugaison] + inter
    options = list(dict.fromkeys(options))
    while len(options) < 4:
        options.append("???")
    random.shuffle(options)
    return options


# ====================================================================
#                       核心验证
# ====================================================================

def verifier_reponse(user_input, conjugaison, fuzzy=True):
    if not user_input:
        return False
    if fuzzy:
        return normalize(user_input) == normalize(conjugaison)
    return user_input == conjugaison


def generer_hint(stem, suffixe, show_stem=True):
    if not show_stem or not stem:
        return ""
    return f"词干：{stem} + 后缀（{len(suffixe)}个字母）"


# ====================================================================
#                   学习状态管理
# ====================================================================

class LearnSession:
    ROUND_ORDER = ["judge", "reverse", "choice", "fill"]
    ROUND_NAMES = {
        "judge": "判断轮",
        "reverse": "反向选择",
        "choice": "选择题",
        "fill": "填空"
    }
    
    def __init__(self, data_dict, settings, level, temps, count=9):
        self.data_dict = data_dict
        self.settings = settings
        self.level = level
        self.temps = temps
        self.count = count
        self.queue = []
        self.groups = []
        self.post_entries = []
        self.index = 0
        self.current_entry = None
        self.is_completed = False
        self.total_classes = 0
        
        self._load_queue()
    
    def _load_queue(self):
        wl_dict, wl_list = charger_wordlist_cached(self.level, self.temps)
        if not wl_list:
            self.queue = []
            self.groups = []
            return

        maitrises = charger_maitrises()
        maitrise_keys = set(entry_to_key(m['verbe'], m['temps'], m['personne']) for m in maitrises)

        # 按动词原型分组，再按时态分组，保持单词表顺序
        verb_groups = {}
        verb_order = []

        for verbe, temps, personne in wl_list:
            if verbe not in verb_groups:
                verb_groups[verbe] = {}
                verb_order.append(verbe)
            if temps not in verb_groups[verbe]:
                verb_groups[verbe][temps] = []
            if personne not in verb_groups[verbe][temps]:
                verb_groups[verbe][temps].append(personne)

        priority_list = self.settings.get('priority_learn', [])
        priority_keys = set(priority_list)

        all_entries = []

        # 按单词表顺序遍历
        for verbe in verb_order:
            temps_dict = verb_groups[verbe]
            
            all_temps_mastered = True
            for temps, personnes in temps_dict.items():
                for p in personnes:
                    if entry_to_key(verbe, temps, p) not in maitrise_keys:
                        all_temps_mastered = False
                        break
                if not all_temps_mastered:
                    break

            if all_temps_mastered:
                continue

            is_priority = entry_to_key(verbe, temps, "je") in priority_keys
            
            for temps, personnes in temps_dict.items():
                unmastered_personnes = []
                for p in personnes:
                    if entry_to_key(verbe, temps, p) not in maitrise_keys:
                        unmastered_personnes.append(p)

                if not unmastered_personnes:
                    continue

                personne_order = ["je", "tu", "il", "nous", "vous", "ils"]
                unmastered_personnes.sort(key=lambda x: personne_order.index(x) if x in personne_order else 999)

                all_entries.append({
                    "verbe": verbe,
                    "temps": temps,
                    "personnes": unmastered_personnes,
                    "personne_index": 0,
                    "round": "judge",
                    "choice_skip": False,
                    "choice_error": False,
                    "priority": is_priority
                })

        if priority_list:
            priority_entries = [e for e in all_entries if e["priority"]]
            normal_entries = [e for e in all_entries if not e["priority"]]
            all_entries = priority_entries + normal_entries
            self.settings['priority_learn'] = []
            sauvegarder_settings(self.settings)

        # 限制用户选择的数量
        if len(all_entries) > self.count:
            all_entries = all_entries[:self.count]

        # ===== 分离判断轮和后续题目 =====
        judge_entries = []
        
        # 后续题目：按 (原型, 人称) 分组，每组内部固定 反向→选择→填空
        post_groups = []
        
        for entry in all_entries:
            # 判断轮
            judge_entries.append({
                "verbe": entry['verbe'],
                "temps": entry['temps'],
                "personnes": entry['personnes'],
                "personne_index": 0,
                "round": "judge",
                "choice_skip": False,
                "choice_error": False,
                "priority": entry.get('priority', False)
            })
            
            # 后续题目：每个人称单独成组，组内 反向→选择→填空
            for p in entry['personnes']:
                group = []
                if self.settings.get('enable_reverse', True):
                    group.append({
                        "verbe": entry['verbe'],
                        "temps": entry['temps'],
                        "personnes": [p],
                        "personne_index": 0,
                        "round": "reverse",
                        "choice_skip": False,
                        "choice_error": False,
                        "priority": entry.get('priority', False)
                    })
                if self.settings.get('enable_choice', True):
                    group.append({
                        "verbe": entry['verbe'],
                        "temps": entry['temps'],
                        "personnes": [p],
                        "personne_index": 0,
                        "round": "choice",
                        "choice_skip": False,
                        "choice_error": False,
                        "priority": entry.get('priority', False)
                    })
                if self.settings.get('enable_fill', True):
                    group.append({
                        "verbe": entry['verbe'],
                        "temps": entry['temps'],
                        "personnes": [p],
                        "personne_index": 0,
                        "round": "fill",
                        "choice_skip": False,
                        "choice_error": False,
                        "priority": entry.get('priority', False)
                    })
                post_groups.append(group)

        # 打乱组的顺序（不同原型+人称之间乱序，但每组内部固定顺序）
        random.shuffle(post_groups)

        # 展平为 post_entries
        post_entries = []
        for group in post_groups:
            post_entries.extend(group)
        
        self.post_entries = post_entries

        # 判断轮：按3个一组分组（保持单词表顺序）
        self.groups = []
        for i in range(0, len(judge_entries), 3):
            self.groups.append(judge_entries[i:i+3])

        # 第一组作为当前队列
        if self.groups:
            self.queue = self.groups[0]
        else:
            self.queue = []

        self.total_classes = len(judge_entries) + len(post_entries)
    
    def has_next(self):
        return len(self.queue) > 0 and not self.is_completed
    
    def get_current_entry(self):
        if self.index < len(self.queue):
            self.current_entry = self.queue[self.index]
            return self.current_entry
        return None
    
    def get_progress(self):
        total_rounds = len(self.queue) * 4
        done_rounds = 0
        for entry in self.queue[:self.index]:
            round_idx = LearnSession.ROUND_ORDER.index(entry['round'])
            done_rounds += round_idx + 1
        if self.index < len(self.queue):
            current_round_idx = LearnSession.ROUND_ORDER.index(self.queue[self.index]['round'])
            done_rounds += current_round_idx
        return done_rounds, total_rounds
    
    def get_current_personne(self):
        entry = self.get_current_entry()
        if entry is None:
            return None
        personnes = entry.get('personnes', [])
        idx = entry.get('personne_index', 0)
        if idx < len(personnes):
            return personnes[idx]
        return None
    
    def get_question_data_for_personne(self, personne):
        if self.current_entry is None:
            return None
        return get_question_data(
            self.data_dict,
            {"verbe": self.current_entry['verbe'], "temps": self.current_entry['temps'], "personne": personne}
        )
    
    def get_judge_display(self):
        if self.current_entry is None:
            return {}
        v = self.current_entry['verbe']
        t = self.current_entry['temps']
        return get_judge_display_data(self.data_dict, v, t)
    
    def process_judge(self, choice):
        entry = self.current_entry
        if entry is None:
            return {"status": "error"}
        
        if choice == 1:
            for personne in entry['personnes']:
                ajouter_maitrise(entry['verbe'], entry['temps'], personne)
            self.queue.pop(self.index)
            if self.index >= len(self.queue):
                self.index = 0
            # 从后续题目池中移除该词条的所有后续题目
            self._remove_post_entries(entry['verbe'], entry['temps'])
            return {"status": "mastered"}
        elif choice == 2:
            # 不确定：从后续题目池中取下一题
            self._load_next_post_entry()
            return {"status": "choice"}
        else:
            # 完全不懂：从后续题目池中取下一题
            self._load_next_post_entry()
            return {"status": "reverse"}
    
    def _remove_post_entries(self, verbe, temps):
        """从后续题目池中移除指定词条的所有后续题目"""
        self.post_entries = [
            e for e in self.post_entries 
            if not (e['verbe'] == verbe and e['temps'] == temps)
        ]
    
    def _load_next_post_entry(self):
        """从后续题目池中取下一题"""
        # 从队列中移除当前词条
        self.queue.pop(self.index)
        if self.index >= len(self.queue):
            self.index = 0
        
        # 从后续题目池中取第一题
        if self.post_entries:
            next_entry = self.post_entries.pop(0)
            self.queue.insert(self.index, next_entry)
    
    def process_reverse(self, correct):
        entry = self.current_entry
        if entry is None:
            return {"status": "error"}
        
        if correct:
            # 从队列移除当前题目
            self.queue.pop(self.index)
            if self.index >= len(self.queue):
                self.index = 0
            
            # 从池子里找同一个 (原型, 人称) 的下一题（选择）
            found = False
            for i, pe in enumerate(self.post_entries):
                if pe['verbe'] == entry['verbe'] and pe['temps'] == entry['temps'] and pe['personnes'][0] == entry['personnes'][0]:
                    next_entry = self.post_entries.pop(i)
                    self.queue.insert(self.index, next_entry)
                    found = True
                    break
            
            if not found:
                # 没有下一题了，取其他词条的题
                if self.post_entries:
                    next_entry = self.post_entries.pop(0)
                    self.queue.insert(self.index, next_entry)
            
            return {"status": "next_post"}
        else:
            self._postpone_current(3)
            return {"status": "retry"}
    
    def process_choice(self, correct):
        entry = self.current_entry
        if entry is None:
            return {"status": "error"}
        
        if correct:
            self.queue.pop(self.index)
            if self.index >= len(self.queue):
                self.index = 0
            
            # 从池子里找同一个 (原型, 人称) 的下一题（填空）
            found = False
            for i, pe in enumerate(self.post_entries):
                if pe['verbe'] == entry['verbe'] and pe['temps'] == entry['temps'] and pe['personnes'][0] == entry['personnes'][0]:
                    next_entry = self.post_entries.pop(i)
                    self.queue.insert(self.index, next_entry)
                    found = True
                    break
            
            if not found:
                if self.post_entries:
                    next_entry = self.post_entries.pop(0)
                    self.queue.insert(self.index, next_entry)
            
            return {"status": "next_post"}
        else:
            entry['choice_error'] = True
            self._postpone_current(3)
            return {"status": "choice_error"}
    
    def process_fill(self, correct):
        entry = self.current_entry
        if entry is None:
            return {"status": "error"}
        
        if correct:
            self.queue.pop(self.index)
            if self.index >= len(self.queue):
                self.index = 0
            
            # 填空完成，该 (原型, 人称) 所有题型完成，取其他词条的题
            if self.post_entries:
                next_entry = self.post_entries.pop(0)
                self.queue.insert(self.index, next_entry)
            
            return {"status": "next_post"}
        else:
            self._postpone_current(3)
            return {"status": "retry"}
    
    def _advance_index(self):
        self.index += 1
        if self.index >= len(self.queue):
            self.index = 0
            if len(self.queue) == 0:
                self.is_completed = True
    
    def _postpone_current(self, offset=3):
        if len(self.queue) <= 1:
            return
        entry = self.queue.pop(self.index)
        insert_pos = min(self.index + offset, len(self.queue))
        self.queue.insert(insert_pos, entry)
        if insert_pos <= self.index:
            self.index += 1
        if len(self.queue) == 1:
            self.index = 0
    
    def get_reverse_choice_data(self):
        personne = self.get_current_personne()
        if personne is None:
            return None
        qdata = self.get_question_data_for_personne(personne)
        if qdata is None:
            return None
        
        v = self.current_entry['verbe']
        t = self.current_entry['temps']
        all_conjugaisons = get_judge_display_data(self.data_dict, v, t)
        
        personnes = ["je", "tu", "il", "nous", "vous", "ils"]
        
        # 按变位去重，保留第一个出现的人称
        seen_conjugaisons = set()
        options = []
        for p in personnes:
            if p in all_conjugaisons:
                conj = all_conjugaisons[p]
                if conj not in seen_conjugaisons:
                    seen_conjugaisons.add(conj)
                    display_p = "il/elle" if p == "il" else "ils/elles" if p == "ils" else p
                    options.append({
                        "personne": p,
                        "conjugaison": conj,
                        "display": f"{display_p}: {conj}"
                    })
        
        return {
            "conjugaison": qdata['conjugaison'],
            "temps": t,
            "verbe": v,
            "correct_personne": personne,
            "options": options
        }
    
    def get_options(self):
        personne = self.get_current_personne()
        if personne is None:
            return []
        qdata = self.get_question_data_for_personne(personne)
        if qdata is None:
            return []
        options = generer_options(qdata['conjugaison'], self.data_dict, qdata['verbe'], qdata['temps'], qdata['personne'])
        random.shuffle(options)
        return options
    
    def check_answer(self, user_input, expected):
        fuzzy = self.settings.get('fuzzy', True)
        return verifier_reponse(user_input, expected, fuzzy)
    
    def get_current_round_name(self):
        if self.current_entry is None:
            return "未知"
        return LearnSession.ROUND_NAMES.get(self.current_entry.get('round', 'judge'), "未知")
    
    def is_empty(self):
        return len(self.queue) == 0
    
    def should_skip_choice(self):
        if self.current_entry is None:
            return False
        return self.current_entry.get('choice_skip', False)
    
    def should_skip_fill(self):
        if self.current_entry is None:
            return False
        return self.current_entry.get('choice_error', False)
    
    def get_current_word_info(self):
        if self.current_entry is None:
            return None
        return {
            "verbe": self.current_entry['verbe'],
            "temps": self.current_entry['temps'],
            "personne": self.get_current_personne()
        }


# ====================================================================
#                   复习状态管理
# ====================================================================

class ReviewSession:
    def __init__(self, data_dict, settings):
        self.data_dict = data_dict
        self.settings = settings
        self.review_items = {}
        self.keys = []
        self.index = 0
        self.current_verb = None
        self.current_personnes = []
        self.sub_index = 0
        self.is_completed = False
        
        self._load_review_items()
    
    def _load_review_items(self):
        self.review_items = get_review_items_by_verb()
        self.keys = list(self.review_items.keys())
        
        personne_order = ["je", "tu", "il", "nous", "vous", "ils"]
        for key in self.keys:
            self.review_items[key].sort(
                key=lambda x: personne_order.index(x['personne'])
                if x['personne'] in personne_order else 999
            )
    
    def has_next(self):
        return self.index < len(self.keys) and not self.is_completed
    
    def get_progress(self):
        total = sum(len(items) for items in self.review_items.values())
        done = 0
        for i, key in enumerate(self.keys):
            if i < self.index:
                done += len(self.review_items[key])
            elif i == self.index:
                done += self.sub_index
        return done, total
    
    def get_total_count(self):
        return sum(len(items) for items in self.review_items.values())
    
    def load_next_question(self):
        if not self.has_next():
            self.is_completed = True
            return None
        
        if self.index >= len(self.keys):
            self.is_completed = True
            return None
        
        self.current_verb = self.keys[self.index]
        self.current_personnes = self.review_items[self.current_verb]
        
        if self.sub_index >= len(self.current_personnes):
            v, t = self.current_verb
            complete_review(v, t, None)
            self.index += 1
            self.sub_index = 0
            return self.load_next_question()
        
        item = self.current_personnes[self.sub_index]
        return item
    
    def get_current_question_data(self):
        if self.sub_index >= len(self.current_personnes):
            return None
        item = self.current_personnes[self.sub_index]
        v = item['verbe']
        t = item['temps']
        p = item['personne']
        
        key = (v, t, p)
        if key in self.data_dict:
            conjugaison, stem, suffixe = self.data_dict[key]
            return {
                "verbe": v,
                "temps": t,
                "personne": p,
                "conjugaison": conjugaison,
                "stem": stem,
                "suffixe": suffixe,
                "exists": True
            }
        else:
            return {
                "verbe": v,
                "temps": t,
                "personne": p,
                "conjugaison": "—",
                "stem": "",
                "suffixe": "",
                "exists": False
            }
    
    def check_answer(self, user_input):
        qdata = self.get_current_question_data()
        if qdata is None or not qdata.get('exists', False):
            return False, None
        fuzzy = self.settings.get('fuzzy', True)
        ok = verifier_reponse(user_input, qdata['conjugaison'], fuzzy)
        return ok, qdata['conjugaison'] if not ok else None
    
    def advance(self):
        self.sub_index += 1
        return self.load_next_question()
    
    def is_empty(self):
        return len(self.review_items) == 0


# ====================================================================
#                   查找功能
# ====================================================================

_all_data_cache = None


def load_all_data():
    global _all_data_cache
    if _all_data_cache is not None:
        return _all_data_cache
    
    cache = {}
    levels = get_available_levels()
    
    for level in levels:
        temps_list = get_available_temps(level)
        for temps in temps_list:
            fichier = os.path.join(RESOURCE_DIR, "wordlists", level, f"{temps}.csv")
            if os.path.exists(fichier):
                data_dict, _ = charger_conjugaisons(fichier)
                for (verbe, t, personne), (conjugaison, _, _) in data_dict.items():
                    if verbe not in cache:
                        cache[verbe] = {}
                    if level not in cache[verbe]:
                        cache[verbe][level] = {}
                    if temps not in cache[verbe][level]:
                        cache[verbe][level][temps] = {}
                    cache[verbe][level][temps][personne] = conjugaison
    
    _all_data_cache = cache
    return cache


def search_verb(verbe):
    all_data = load_all_data()
    if verbe not in all_data:
        return None
    return all_data[verbe]


def get_all_verbs():
    all_data = load_all_data()
    return sorted(list(all_data.keys()))