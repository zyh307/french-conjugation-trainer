"""Local HTTP adapter for the unchanged 2.0 conjugation engine. No Python dependencies."""
import argparse
import copy
import json
import mimetypes
import os
from pathlib import Path
import random
import shutil
import sys
import uuid
from datetime import date, datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

import conjugaison_core as core
from learning_schedule import GroupedPractice

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('CONJUGAISON_DATA_DIR', ROOT / 'data')).resolve()
DATA.mkdir(parents=True, exist_ok=True)
for name, original in list(core.FILES.items()):
    target = DATA / Path(original).name
    # Migrate only on first launch, without touching the original project's data.
    if 'CONJUGAISON_DATA_DIR' not in os.environ:
        old = ROOT.parent / '法语练习2.0' / target.name
        if old.exists() and not target.exists():
            shutil.copy2(old, target)
    core.FILES[name] = str(target)

PERSONS = ['je', 'tu', 'il', 'nous', 'vous', 'ils']
TENSES = ['现在时', '复合过去时', '未完成过去时']
HISTORY = str(DATA / 'history.json')
ACTIVE = str(DATA / 'active_session.json')
WORD_HISTORY = str(DATA / 'word_history.json')
core.FILES['favorites'] = str(DATA / 'favorites.json')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def record(correct):
    stats = core.charger_statistiques()
    (core.incrementer_correct if correct else core.incrementer_total)(stats)
    history = core.charger_json(HISTORY, {})
    day = history.setdefault(core.get_today(), {'total': 0, 'correct': 0})
    day['total'] += 1
    day['correct'] += int(correct)
    core.sauvegarder_json(HISTORY, history)


def all_data():
    data = {}
    for level in core.get_available_levels():
        for tense in TENSES:
            data.update(core.charger_wordlist_cached(level, tense)[0])
    return data


def remember_word(journal, verb, day):
    item = journal.setdefault(verb, {'first_learned': day, 'days': []})
    item['first_learned'] = min(item['first_learned'], day)
    if day not in item['days']:
        item['days'].append(day)


def word_history():
    journal = core.charger_json(WORD_HISTORY, {})
    before = json.dumps(journal, sort_keys=True)
    groups = {}
    for item in core.charger_maitrises():
        groups.setdefault((item['verbe'], item['temps']), {})[item['personne']] = item['date_learned']
    data = all_data()
    for (verb, tense), people in groups.items():
        expected = [p for p in PERSONS if (verb, tense, p) in data]
        if expected and all(p in people for p in expected):
            remember_word(journal, verb, max(people[p] for p in expected))
    if json.dumps(journal, sort_keys=True) != before:
        require(core.sauvegarder_json(WORD_HISTORY, journal), '背词记录保存失败。')
    return journal


def record_completed_word(verb, tense):
    journal = word_history()
    known = {m['personne'] for m in core.charger_maitrises() if m['verbe'] == verb and m['temps'] == tense}
    expected = [p for p in PERSONS if (verb, tense, p) in all_data()]
    if expected and all(p in known for p in expected):
        remember_word(journal, verb, core.get_today())
        require(core.sauvegarder_json(WORD_HISTORY, journal), '背词记录保存失败。')


def share_stats():
    journal = word_history()
    today = core.get_today()
    verbs = sorted(v for v, item in journal.items() if today in item['days'])
    return {'total_words': len(journal), 'today_words': len(verbs), 'today_verbs': verbs, 'date': today}


class Studio:
    def __init__(self):
        self.session = None
        self.mode = None
        self.question = None

    def save(self):
        if not self.session:
            return
        s = self.session
        if self.mode == 'learn':
            payload = {k: getattr(s, k) for k in ('queue', 'post_entries', 'index', 'level', 'temps', 'count', 'total_classes', 'pending_groups', 'batch_index', 'batch_count', 'batch_verbs')}
            payload['grouped'] = True
            payload['schedule'] = s.scheduler.state
            payload['settings'] = s.settings
            payload['question'] = self.question
            payload['mode'] = 'learn'
            payload['done'] = getattr(s, 'done', 0)
            payload['direct'] = getattr(s, 'direct', False)
            payload['verb'] = getattr(s, 'verb', None)
            if payload['direct']:
                payload['direct_entries'] = s.direct_entries
                payload['completed_words'] = s.completed_words
            if not payload['direct']:
                core.set_progress(s.level, s.temps, payload)
        else:
            payload = {'mode': 'review', 'items': s, 'question': self.question, 'total': self.review_total, 'done': self.review_done}
            core.set_review_progress(payload)
        require(core.sauvegarder_json(ACTIVE, payload), '学习进度未能写入磁盘，请检查 data 目录权限。')

    def finish(self):
        if self.mode == 'learn' and self.session:
            s = self.session
            if getattr(s, 'direct', False):
                for entry in s.direct_entries:
                    self.complete_direct_word(entry)
            else:
                core.clear_progress(s.level, s.temps)
        elif self.mode == 'review':
            core.clear_review_progress()
        self.session = None
        self.question = None
        core.sauvegarder_json(ACTIVE, {})
        return {'completed': True, 'mode': self.mode}

    def complete_direct_word(self, entry):
        s = self.session
        k = entry['verbe'] + '|' + entry['temps']
        if k in s.completed_words:
            return
        for p in PERSONS:
            if (entry['verbe'], entry['temps'], p) in s.data_dict:
                core.ajouter_maitrise(entry['verbe'], entry['temps'], p)
        record_completed_word(entry['verbe'], entry['temps'])
        favorites = core.charger_json(core.FILES['favorites'], {})
        if k in favorites:
            favorites[k]['practice_count'] = favorites[k].get('practice_count', 0) + 1
            favorites[k]['last_practiced'] = datetime.now().astimezone().isoformat(timespec='seconds')
            require(core.sauvegarder_json(core.FILES['favorites'], favorites), '收藏练习记录保存失败。')
        s.completed_words.append(k)

    def start(self, body, saved_direct=None):
        mode = body.get('mode', 'learn')
        require(mode in ('learn', 'review'), '未知的练习类型。')
        self.mode = mode
        if mode == 'review':
            items = sorted(core.get_review_list(), key=lambda x: (x['verbe'], x['temps'], PERSONS.index(x['personne'])))
            self.session = items
            self.review_total = len(items)
            self.review_done = 0
            return self.next_question()
        tense = body.get('tense', '现在时')
        level = body.get('level') or next((l for l in core.get_available_levels() if (body.get('verb'), tense, 'je') in core.charger_wordlist_cached(l, tense)[0]), '必会')
        require(level in core.get_available_levels() and tense in TENSES, '请选择有效的等级和时态。')
        direct_entries = (saved_direct or {}).get('direct_entries')
        if direct_entries is None:
            if body.get('favorites'):
                direct_entries = list(core.charger_json(core.FILES['favorites'], {}).values())
                require(bool(direct_entries), '先收藏一个动词，再开始练习。')
            elif body.get('verb'):
                direct_entries = [{'verbe': body['verb'], 'temps': tense}]
        direct = bool(direct_entries)
        data = core.charger_wordlist_cached(level, tense)[0]
        if direct:
            data = all_data()
            for e in direct_entries:
                require((e['verbe'], e['temps'], 'je') in data, '此词不在所选时态和词表中。')
        saved = saved_direct or (core.get_progress(level, tense) if not direct and body.get('resume', True) else {})
        count = body.get('count', saved.get('count', 3))
        require(isinstance(count, int) and not isinstance(count, bool) and 1 <= count <= 100, '每组动词数量需在 1–100 之间。')
        settings = saved.get('settings', core.charger_settings()) if saved else core.charger_settings()
        persisted_settings = copy.deepcopy(core.charger_settings())
        settings = copy.deepcopy(settings)
        if direct:
            settings.update(enable_choice=True, enable_reverse=True, enable_fill=True)
        self.session = core.LearnSession(data, settings, level, tense, count)
        s = self.session
        s.direct, s.verb = direct, body.get('verb')
        s.direct_entries = direct_entries or []
        s.completed_words = copy.deepcopy(saved.get('completed_words', []))
        selected = {e['verbe'] for group in s.groups for e in group} if not direct and not saved else set()
        persisted_settings['priority_learn'] = [k for k in persisted_settings.get('priority_learn', []) if k not in {core.entry_to_key(v, tense, 'je') for v in selected}]
        core.sauvegarder_settings(persisted_settings)
        if saved.get('queue') or saved.get('schedule'):
            s.scheduler = GroupedPractice.from_progress(saved, settings)
            s.done = saved.get('done', 0)
            self.question = saved.get('question') if saved.get('schedule', {}).get('version') == GroupedPractice.VERSION else None
            if self.question:
                self.sync_schedule()
                self.save()
                return self.question
        else:
            if direct:
                groups = []
                for t in TENSES:
                    entries = [{'verbe': e['verbe'], 'temps': t, 'personnes': [p for p in PERSONS if (e['verbe'], t, p) in data], 'personne_index': 0, 'round': 'judge'} for e in direct_entries if e['temps'] == t]
                    groups.extend(entries[i:i + 3] for i in range(0, len(entries), 3))
                s.scheduler = GroupedPractice(groups, settings)
                for group in s.scheduler.state['groups']:
                    group['judge_keys'] = []
            else:
                s.scheduler = GroupedPractice(s.groups, settings)
            s.done = 0
        return self.next_question()

    def sync_schedule(self):
        s = self.session
        entry = s.scheduler.current()
        s.queue = [entry] if entry else []
        s.post_entries = []
        s.index = 0
        info = s.scheduler.batch_info()
        for name, value in info.items():
            setattr(s, name, value)
        state = s.scheduler.state
        s.pending_groups = state['groups'][state['cursor'] + 1:]
        return entry

    def resume(self):
        saved = core.charger_json(ACTIVE, {})
        if self.session:
            return self.question or self.next_question()
        if saved.get('mode') == 'learn' and saved.get('queue'):
            if saved.get('direct'):
                return self.start({'level': saved['level'], 'tense': saved['temps'], 'verb': saved['verb']}, saved)
            return self.start({'level': saved['level'], 'tense': saved['temps'], 'resume': True})
        if saved.get('mode') == 'review' and saved.get('items'):
            self.mode = 'review'
            self.session = saved['items']
            self.review_total = saved['total']
            self.review_done = saved['done']
            self.question = saved.get('question')
            return self.question or self.next_question()
        return {'completed': True}

    def next_question(self):
        if self.mode == 'review':
            if not self.session:
                return self.finish()
            entry = self.session[0]
            q = core.get_question_data(all_data(), entry)
            q.pop('conjugaison', None)
            q.update({'round': 'fill', 'mode': 'review', 'done': self.review_done, 'total': self.review_total})
        else:
            s = self.session
            if self.sync_schedule() is None:
                return self.finish()
            entry = s.get_current_entry()
            if getattr(s, 'direct', False):
                s.level = next(l for l in core.get_available_levels() if (entry['verbe'], entry['temps'], 'je') in core.charger_wordlist_cached(l, entry['temps'])[0])
            q = {k: entry[k] for k in ('verbe', 'temps', 'round')}
            q.update({'level': s.level, 'direct': getattr(s, 'direct', False), 'personne': s.get_current_personne(), 'mode': 'learn', 'done': s.done,
                      'total': max(s.done + s.scheduler.remaining(), 1),
                      'batch_index': s.batch_index, 'batch_count': s.batch_count, 'batch_verbs': s.batch_verbs})
            if q['round'] == 'judge':
                q['conjugations'] = s.get_judge_display()
            else:
                data = s.get_question_data_for_personne(q['personne'])
                if q['round'] == 'reverse':
                    q['display'] = data['conjugaison']
                    q['options'] = PERSONS
                elif q['round'] == 'choice':
                    q['options'] = s.get_options()
                elif s.settings.get('show_stem', True):
                    q['hint'] = core.generer_hint(data['stem'], data['suffixe'])
        q['id'] = uuid.uuid4().hex
        self.question = q
        self.save()
        return q

    def answer(self, body):
        q = self.question
        require(q and self.session is not None, '当前没有练习，请先开始一组练习。')
        require(body.get('id') == q['id'], '这道题已更新，请刷新后继续。')
        if self.mode == 'review':
            answer = str(body.get('answer', '')).strip()
            require(bool(answer), '请先输入答案。')
            entry = self.session[0]
            expected = core.get_question_data(all_data(), entry)['conjugaison']
            correct = core.verifier_reponse(answer, expected, core.charger_settings()['fuzzy'])
            record(correct)
            if correct:
                core.complete_review(entry['verbe'], entry['temps'], entry['personne'])
                self.session.pop(0)
                self.review_done += 1
                if not any(e['verbe'] == entry['verbe'] and e['temps'] == entry['temps'] for e in self.session):
                    record_completed_word(entry['verbe'], entry['temps'])
            else:
                core.sauvegarder_erreur(entry['verbe'], entry['temps'], entry['personne'], expected)
            next_q = self.next_question()
            return {'correct': correct, 'expected': expected, 'next': next_q}
        s = self.session
        entry = s.get_current_entry()
        if q['round'] == 'judge':
            choice = body.get('choice')
            require(choice in (1, 2, 3), '请选择掌握程度。')
            if choice == 1:
                for p in entry['personnes']:
                    core.ajouter_maitrise(entry['verbe'], entry['temps'], p)
                record_completed_word(entry['verbe'], entry['temps'])
            s.scheduler.judge(choice)
            if choice != 1 and not any(s.settings.get('enable_' + r) for r in ('reverse', 'choice', 'fill')):
                for p in entry['personnes']:
                    core.ajouter_maitrise(entry['verbe'], entry['temps'], p)
                record_completed_word(entry['verbe'], entry['temps'])
            s.done += 1
            return {'correct': True, 'judged': True, 'next': self.next_question()}
        answer = str(body.get('answer', '')).strip()
        require(bool(answer), '请先选择或输入答案。')
        data = s.get_question_data_for_personne(q['personne'])
        expected = q['personne'] if q['round'] == 'reverse' else data['conjugaison']
        if q['round'] == 'reverse':
            # Several persons can share the same written conjugation.
            correct = answer in PERSONS and s.get_judge_display().get(answer) == data['conjugaison']
        else:
            correct = s.check_answer(answer, expected)
        record(correct)
        if not correct:
            core.sauvegarder_erreur(data['verbe'], data['temps'], data['personne'], data['conjugaison'])
        _, mastered_person = s.scheduler.answer(correct)
        if correct:
            s.done += 1
            if mastered_person and not getattr(s, 'direct', False):
                core.ajouter_maitrise(data['verbe'], data['temps'], data['personne'])
                record_completed_word(data['verbe'], data['temps'])
            elif mastered_person and getattr(s, 'direct', False) and any(p['verbe'] == q['verbe'] and p['temps'] == q['temps'] and p['stage'] == len(p['rounds']) for p in s.scheduler.state['plans']):
                self.complete_direct_word(q)
        return {'correct': correct, 'expected': expected, 'next': self.next_question()}

    def state(self):
        review = core.get_review_list()
        mastered = core.charger_maitrises()
        errors = [dict(zip(('verbe', 'temps', 'personne', 'conjugaison'), (*key, value))) for key, value in core.charger_erreurs().items()]
        lists = []
        for level in core.get_available_levels():
            for tense in TENSES:
                total, known = core.get_wordlist_stats(level, tense)
                lists.append({'level': level, 'tense': tense, 'total': total, 'mastered': known,
                              'resume': bool(core.get_progress(level, tense).get('queue'))})
        return {'stats': core.charger_statistiques(), 'mastered': mastered, 'errors': errors, 'review': review,
                'settings': core.charger_settings(), 'wordlists': lists, 'verbs': core.get_all_verbs(),
                'history': core.charger_json(HISTORY, {}), 'favorites': list(core.charger_json(core.FILES['favorites'], {}).values()), 'active': bool(core.charger_json(ACTIVE, {}).get('mode')), 'share_stats': share_stats()}

    def return_words(self, selected):
        def affected(e):
            return e.get('verbe', '') + '|' + e.get('temps', '') in selected

        def patch(saved):
            if not saved:
                return saved
            if saved.get('mode') == 'review':
                saved['items'] = [e for e in saved['items'] if not affected(e)]
                saved['total'] = saved['done'] + len(saved['items'])
                if affected(saved.get('question') or {}):
                    saved['question'] = None
                return saved
            if saved.get('direct'):
                entries = saved.get('direct_entries', [{'verbe': saved.get('verb'), 'temps': saved['temps']}])
                if not any(affected(e) for e in entries):
                    return saved
                saved['direct_entries'] = [e for e in entries if not affected(e)]
                if not saved['direct_entries']:
                    return {}
                scheduler = GroupedPractice.from_progress(saved, saved['settings'])
                scheduler.remove_words(selected)
                current = scheduler.current()
                saved.update(schedule=scheduler.state, queue=[current] if current else [], **scheduler.batch_info())
                if affected(saved.get('question') or {}):
                    saved['question'] = None
                elif saved.get('question'):
                    saved['question'].update(total=saved.get('done', 0) + scheduler.remaining(), **scheduler.batch_info())
                return saved
            entries = []
            data = core.charger_wordlist_cached(saved['level'], saved['temps'])[0]
            for k in sorted(selected):
                verb, tense = k.split('|')
                people = [p for p in PERSONS if (verb, tense, p) in data]
                if tense == saved['temps'] and people:
                    entries.append({'verbe': verb, 'temps': tense, 'personnes': people, 'personne_index': 0, 'round': 'judge'})
            if not entries:
                return saved
            scheduler = GroupedPractice.from_progress(saved, saved['settings'])
            scheduler.return_words(entries)
            current = scheduler.current()
            saved.update(schedule=scheduler.state, queue=[current] if current else [], post_entries=[], index=0,
                         pending_groups=scheduler.state['groups'][scheduler.state['cursor'] + 1:], **scheduler.batch_info())
            q = saved.get('question')
            if q and affected(q):
                saved['question'] = None
            elif q:
                q.update(total=saved.get('done', 0) + scheduler.remaining(), **scheduler.batch_info())
            return saved

        progress = core.charger_progress()
        for by_tense in progress.values():
            for tense, saved in by_tense.items():
                if saved:
                    by_tense[tense] = patch(saved)
        require(core.sauvegarder_progress(progress), '练习进度保存失败。')
        active = core.charger_json(ACTIVE, {})
        if active.get('mode') == 'learn' and not active.get('direct'):
            active = copy.deepcopy(progress.get(active['level'], {}).get(active['temps']) or patch(active))
        else:
            active = patch(active)
        core.set_review_progress(patch(core.get_review_progress()))
        require(core.sauvegarder_json(ACTIVE, active), '练习进度保存失败。')
        # Reload the updated payload on resume; unrelated questions retain their IDs/options.
        self.session = None
        self.question = None

    def mutate(self, path, body):
        if path == '/api/favorites/toggle':
            verb, tense = body.get('verb'), body.get('tense')
            require(tense in TENSES and (verb, tense, 'je') in all_data(), '请选择有效的动词和时态。')
            require(type(body.get('saved')) is bool, '收藏状态无效。')
            favorites = core.charger_json(core.FILES['favorites'], {})
            k = verb + '|' + tense
            if body['saved']:
                favorites.setdefault(k, {'verbe': verb, 'temps': tense, 'added': core.get_today(), 'practice_count': 0, 'last_practiced': None})
            else:
                favorites.pop(k, None)
            require(core.sauvegarder_json(core.FILES['favorites'], favorites), '收藏保存失败。')
            return {'ok': True}
        if path == '/api/session/start':
            return self.start(body)
        if path == '/api/session/resume':
            return self.resume()
        if path == '/api/session/answer':
            return self.answer(body)
        if path == '/api/settings':
            settings = core.charger_settings()
            if 'daily_goal' in body:
                value = body['daily_goal']
                require(type(value) is int and 1 <= value <= 100, '每日目标需为 1–100 个动词。')
                settings['daily_goal'] = value
            for key in ('fuzzy', 'show_stem', 'enable_reverse', 'enable_choice', 'enable_fill'):
                if key in body:
                    require(isinstance(body[key], bool), '设置值必须是开关状态。')
                    settings[key] = body[key]
            require(core.sauvegarder_settings(settings), '设置保存失败。')
            return settings
        if path == '/api/errors/delete':
            keys = body.get('keys', [])
            errors = core.charger_erreurs()
            for key in list(errors):
                if body.get('all') or core.entry_to_key(*key) in keys:
                    del errors[key]
            core.ecrire_tout_erreurs(errors)
            return {'ok': True}
        if path == '/api/mastered/relearn':
            requested = set(body.get('keys', []))
            keys = {m['verbe'] + '|' + m['temps'] for m in core.charger_maitrises() if m['verbe'] + '|' + m['temps'] in requested}
            settings = core.charger_settings()
            for item in core.charger_maitrises():
                if item['verbe'] + '|' + item['temps'] in keys:
                    core.remove_from_maitrise(item['verbe'], item['temps'], item['personne'])
                    priority = core.entry_to_key(item['verbe'], item['temps'], 'je')
                    if priority not in settings['priority_learn']:
                        settings['priority_learn'].append(priority)
            core.sauvegarder_settings(settings)
            self.return_words(keys)
            return {'ok': True}
        if path == '/api/progress/reset':
            level, tense = body.get('level'), body.get('tense')
            require(level in core.get_available_levels() and tense in TENSES, '等级或时态无效。')
            core.clear_progress(level, tense)
            active = core.charger_json(ACTIVE, {})
            if active.get('level') == level and active.get('temps') == tense:
                self.session = None
                self.question = None
                core.sauvegarder_json(ACTIVE, {})
            return {'ok': True}
        raise ValueError('不存在的操作。')


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / 'dist'), **kwargs)

    def log_message(self, fmt, *args):
        if args and str(args[0]).startswith('/api'):
            return
        super().log_message(fmt, *args)

    def json_response(self, payload, status=200):
        raw = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path = urlparse(self.path).path
        try:
            if path == '/api/state':
                return self.json_response(studio.state())
            if path == '/api/dictionary':
                return self.json_response(core.load_all_data())
            if path == '/api/share':
                return self.json_response(share_stats())
            if path.startswith('/api/'):
                return self.json_response({'error': '接口不存在。'}, 404)
            if path == '/' and not (ROOT / 'dist' / 'index.html').exists():
                return self.json_response({'error': '请先运行 npm run build。'}, 503)
            return super().do_GET()
        except Exception:
            self.json_response({'error': '读取数据失败，请查看本地服务日志。'}, 500)
            import traceback
            traceback.print_exc()

    def do_POST(self):
        try:
            require(self.headers.get('X-Conjugaison-Client') == '3.0', '请求来源无效。')
            origin = self.headers.get('Origin')
            require(not origin or origin in (f'http://127.0.0.1:{self.server.server_port}', 'http://127.0.0.1:5173'), '请求来源无效。')
            length = int(self.headers.get('Content-Length', '0'))
            require(0 < length <= 1024 * 128, '请求体大小无效。')
            body = json.loads(self.rfile.read(length))
            require(isinstance(body, dict), '请求格式无效。')
            self.json_response(studio.mutate(urlparse(self.path).path, body))
        except (ValueError, TypeError, KeyError) as exc:
            self.json_response({'error': str(exc)}, 400)
        except Exception:
            self.json_response({'error': '操作未完成，请查看本地服务日志。'}, 500)
            import traceback
            traceback.print_exc()


studio = Studio()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--open', action='store_true', help='Open the local app in the default browser')
    args = parser.parse_args()
    mimetypes.add_type('application/javascript', '.js')
    mimetypes.add_type('text/css', '.css')
    server = HTTPServer(('127.0.0.1', args.port), Handler)
    print(f'Conjugaison 3.0 ready at http://127.0.0.1:{args.port}', flush=True)
    if args.open:
        import webbrowser
        webbrowser.open(f'http://127.0.0.1:{args.port}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
