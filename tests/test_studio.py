import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEMP_ROOT = ROOT / 'tests' / '.tmp'
TEMP_ROOT.mkdir(exist_ok=True)
INITIAL = tempfile.TemporaryDirectory(prefix='conjugaison-tests-import-', dir=TEMP_ROOT)
os.environ['CONJUGAISON_DATA_DIR'] = INITIAL.name
import server
from server import core


class StudioTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='conjugaison-tests-', dir=TEMP_ROOT)
        folder = Path(self.temp.name)
        core.FILES = {key: str(folder / Path(value).name) for key, value in core.FILES.items()}
        server.ACTIVE = str(folder / 'active_session.json')
        server.HISTORY = str(folder / 'history.json')
        server.WORD_HISTORY = str(folder / 'word_history.json')
        self.studio = server.Studio()

    def tearDown(self):
        assert Path(self.temp.name).resolve().is_relative_to(TEMP_ROOT.resolve())
        self.temp.cleanup()

    def test_original_engine_is_unchanged(self):
        original = ROOT.parent / '法语练习2.0' / 'conjugaison_core.py'
        if original.exists():
            self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(), hashlib.sha256((ROOT / 'conjugaison_core.py').read_bytes()).hexdigest())

    def test_nine_original_wordlists_load(self):
        state = self.studio.state()
        self.assertEqual(len(state['wordlists']), 9)
        self.assertTrue(all(item['total'] > 0 for item in state['wordlists']))
        self.assertIn('être', state['verbs'])

    def test_fuzzy_and_strict_answers(self):
        self.assertTrue(core.verifier_reponse('ETES', 'êtes', True))
        self.assertFalse(core.verifier_reponse('ETES', 'êtes', False))
        self.assertFalse(core.verifier_reponse('', 'êtes', True))

    def test_judge_mastery_and_completion(self):
        q = self.studio.start({'count': 1})
        self.assertEqual(q['round'], 'judge')
        self.assertEqual(set(q['conjugations']), set(server.PERSONS))
        result = self.studio.answer({'id': q['id'], 'choice': 1})
        self.assertTrue(result['next']['completed'])
        self.assertEqual(len(core.charger_maitrises()), 6)
        self.assertFalse(self.studio.state()['active'])

    def solve(self, q):
        data = core.get_question_data(self.studio.session.data_dict, q)
        return self.studio.answer({'id': q['id'], 'answer': q['personne'] if q['round'] == 'reverse' else data['conjugaison']})

    def test_direct_practice_isolates_word_tense_and_regular_progress(self):
        regular = self.studio.start({'count': 3})
        progress = core.get_progress('必会', '现在时')
        q = self.studio.start({'verb': 'résoudre', 'tense': '复合过去时'})
        self.assertTrue(q['direct'])
        self.assertEqual(q['round'], 'choice')
        restarted = server.Studio()
        self.assertEqual(restarted.resume(), q)
        self.studio = restarted
        count = 0
        while not q.get('completed'):
            self.assertEqual((q['verbe'], q['temps']), ('résoudre', '复合过去时'))
            self.assertEqual(server.share_stats()['today_words'], 0)
            q = self.solve(q)['next']
            count += 1
            self.assertLessEqual(count, 18)
        self.assertEqual(count, 18)
        self.assertEqual(len(core.charger_maitrises()), 6)
        self.assertEqual(server.share_stats()['today_words'], 1)
        self.assertEqual(core.get_progress('必会', '现在时'), progress)
        self.assertEqual(self.studio.start({})['id'], regular['id'])

    def test_direct_repractice_keeps_dates_and_goal_counts_words(self):
        for p in server.PERSONS:
            core.ajouter_maitrise('être', '现在时', p, '2026-01-01')
        q = self.studio.start({'verb': 'être', 'tense': '现在时'})
        while not q.get('completed'):
            q = self.solve(q)['next']
        self.assertTrue(all(m['date_learned'] == '2026-01-01' for m in core.charger_maitrises()))
        self.assertEqual(server.share_stats()['today_words'], 1)
        self.studio.mutate('/api/settings', {'daily_goal': 7})
        self.assertEqual(self.studio.state()['settings']['daily_goal'], 7)
        for value in (0, 101, 1.5, True, '3'):
            with self.assertRaises(ValueError):
                self.studio.mutate('/api/settings', {'daily_goal': value})

    def test_returned_word_priority_survives_other_wordlists(self):
        for p in server.PERSONS:
            core.ajouter_maitrise('résoudre', '未完成过去时', p)
        regular = self.studio.start({'level': '生僻', 'tense': '未完成过去时'})
        self.studio.mutate('/api/mastered/relearn', {'keys': ['résoudre|未完成过去时']})
        self.studio.start({'tense': '现在时'})
        self.assertIn('résoudre|未完成过去时|je', core.charger_settings()['priority_learn'])
        q = self.studio.start({'level': '生僻', 'tense': '未完成过去时', 'count': 1})
        self.assertEqual(q['id'], regular['id'])
        for i in range(3):
            q = self.studio.answer({'id': q['id'], 'choice': 1})['next']
        self.assertEqual(q['verbe'], 'résoudre')
        self.assertEqual(q['round'], 'judge')

    def test_returning_word_keeps_question_retry_and_other_tense(self):
        import copy
        q = self.studio.start({'count': 6})
        returned = q['verbe']
        q = self.studio.answer({'id': q['id'], 'choice': 1})['next']
        for i in range(2):
            q = self.studio.answer({'id': q['id'], 'choice': 3})['next']
        for i in range(7):
            q = self.solve(q)['next']
        q = self.studio.answer({'id': q['id'], 'answer': '__wrong__'})['next']
        original = copy.deepcopy(self.studio.session.scheduler.state)
        self.studio.start({'tense': '复合过去时'})
        other = core.get_progress('必会', '复合过去时')
        self.studio.start({})
        self.studio.mutate('/api/mastered/relearn', {'keys': [returned + '|现在时']})
        restored = server.Studio()
        resumed = restored.resume()
        self.studio = restored
        self.assertEqual(resumed['id'], q['id'])
        for field in ('plans', 'queue', 'judges'):
            self.assertEqual(self.studio.session.scheduler.state[field], original[field])
        self.assertEqual(core.get_progress('必会', '复合过去时'), other)
        for i in range(70):
            if resumed['round'] == 'judge':
                break
            resumed = self.solve(resumed)['next']
        self.assertEqual((resumed['verbe'], resumed['round']), (returned, 'judge'))

    def test_favorite_batch_records_each_word_and_keeps_normal_progress(self):
        with self.assertRaises(ValueError):
            self.studio.start({'favorites': True})
        regular = self.studio.start({'count': 3})
        saved = core.get_progress('必会', '现在时')
        for verb, tense in [('être', '现在时'), ('résoudre', '复合过去时')]:
            self.studio.mutate('/api/favorites/toggle', {'verb': verb, 'tense': tense, 'saved': True})
        q = self.studio.start({'favorites': True})
        restarted = server.Studio()
        self.assertEqual(restarted.resume(), q)
        self.studio = restarted
        count = 0
        while not q.get('completed'):
            self.assertNotEqual(q['round'], 'judge')
            q = self.solve(q)['next']
            count += 1
            self.assertLessEqual(count, 36)
        self.assertEqual(count, 36)
        favorites = self.studio.state()['favorites']
        self.assertTrue(all(f['practice_count'] == 1 and f['last_practiced'] for f in favorites))
        self.assertEqual(core.get_progress('必会', '现在时'), saved)
        self.assertEqual(self.studio.start({})['id'], regular['id'])
        q = self.studio.start({'verb': 'être', 'tense': '现在时'})
        while not q.get('completed'):
            q = self.solve(q)['next']
        favorites = {f['verbe']: f for f in self.studio.state()['favorites']}
        self.assertEqual(favorites['être']['practice_count'], 2)
        self.assertEqual(favorites['résoudre']['practice_count'], 1)
        self.studio.mutate('/api/favorites/toggle', {'verb': 'être', 'tense': '现在时', 'saved': False})
        self.assertEqual(len(self.studio.state()['favorites']), 1)

    def test_all_rounds_complete_and_all_persons_mastered(self):
        q = self.studio.start({'count': 1})
        q = self.studio.answer({'id': q['id'], 'choice': 3})['next']
        rounds = set()
        count = 0
        while not q.get('completed'):
            rounds.add(q['round'])
            q = self.solve(q)['next']
            count += 1
            self.assertLess(count, 50, 'Learning session must terminate')
        self.assertEqual(rounds, {'reverse', 'choice', 'fill'})
        self.assertEqual(len(core.charger_maitrises()), 6)
        self.assertEqual(core.charger_statistiques(), {'correct': 18, 'total': 18})

    def test_wrong_answer_is_saved_and_retried(self):
        q = self.studio.start({'count': 1})
        q = self.studio.answer({'id': q['id'], 'choice': 3})['next']
        result = self.studio.answer({'id': q['id'], 'answer': 'wrong'})
        self.assertFalse(result['correct'])
        self.assertEqual(len(core.charger_erreurs()), 1)
        self.assertEqual(core.charger_statistiques()['total'], 1)
        self.assertFalse(core.charger_maitrises())
        self.assertEqual(result['next']['round'], 'choice')

    def test_resume_preserves_question_and_remaining_rounds(self):
        q = self.studio.start({'count': 2})
        q = self.studio.answer({'id': q['id'], 'choice': 3})['next']
        pool = self.studio.session.post_entries
        restarted = server.Studio()
        restored = restarted.resume()
        self.assertEqual(q, restored)
        self.assertEqual(pool, restarted.session.post_entries)

    def test_stale_question_cannot_score_twice(self):
        q = self.studio.start({'count': 1})
        q = self.studio.answer({'id': q['id'], 'choice': 3})['next']
        self.solve(q)
        with self.assertRaises(ValueError):
            self.studio.answer({'id': q['id'], 'answer': q['personne']})
        self.assertEqual(core.charger_statistiques()['total'], 1)

    def test_disabled_rounds_are_respected(self):
        self.studio.mutate('/api/settings', {'enable_reverse': False, 'enable_choice': False})
        q = self.studio.start({'count': 1})
        q = self.studio.answer({'id': q['id'], 'choice': 3})['next']
        count = 0
        while not q.get('completed'):
            self.assertEqual(q['round'], 'fill')
            q = self.solve(q)['next']
            count += 1
            self.assertLess(count, 10)
        self.assertEqual(len(core.charger_maitrises()), 6)

    def test_review_uses_original_schedule_and_advances(self):
        core.ajouter_maitrise('être', '现在时', 'je', core.add_days(core.get_today(), -1))
        self.assertEqual(len(self.studio.state()['review']), 1)
        q = self.studio.start({'mode': 'review'})
        self.assertEqual(q['personne'], 'je')
        result = self.studio.answer({'id': q['id'], 'answer': 'suis'})
        self.assertTrue(result['correct'])
        self.assertTrue(result['next']['completed'])
        self.assertEqual(self.studio.state()['review'], [])

    def test_errors_delete_and_relearn(self):
        core.sauvegarder_erreur('être', '现在时', 'je', 'suis')
        self.studio.mutate('/api/errors/delete', {'keys': ['être|现在时|je']})
        self.assertEqual(core.charger_erreurs(), {})
        core.ajouter_maitrise('être', '现在时', 'je')
        self.studio.mutate('/api/mastered/relearn', {'keys': ['être|现在时']})
        self.assertFalse(core.charger_maitrises())
        self.assertIn('être|现在时|je', core.charger_settings()['priority_learn'])

    def test_count_and_settings_validation(self):
        for count in [0, 101, '9', True]:
            with self.assertRaises(ValueError):
                self.studio.start({'count': count})
        with self.assertRaises(ValueError):
            self.studio.mutate('/api/settings', {'fuzzy': 'false'})

    def test_three_verb_batches_show_all_cards_before_practice(self):
        q = self.studio.start({'count': 4})
        first = []
        for _ in range(3):
            self.assertEqual(q['round'], 'judge')
            self.assertEqual(q['batch_index'], 1)
            first.append(q['verbe'])
            q = self.studio.answer({'id': q['id'], 'choice': 3})['next']
        self.assertEqual(len(set(first)), 3)
        self.assertNotEqual(q['round'], 'judge')
        count = 0
        while q['batch_index'] == 1:
            self.assertIn(q['verbe'], first)
            q = self.solve(q)['next']
            count += 1
            self.assertLess(count, 100)
        self.assertEqual(q['round'], 'judge')
        self.assertEqual(q['batch_index'], 2)
        self.assertNotIn(q['verbe'], first)
        self.assertEqual(len(core.charger_maitrises()), 18)

    def test_batch_boundary_survives_resume(self):
        q = self.studio.start({'count': 7})
        verbs = q['batch_verbs']
        for _ in range(3):
            q = self.studio.answer({'id': q['id'], 'choice': 3})['next']
        restarted = server.Studio()
        restored = restarted.resume()
        self.assertEqual(restored, q)
        self.assertEqual(restored['batch_verbs'], verbs)
        self.assertEqual(len(restarted.session.pending_groups), 2)

    def test_no_practice_tasks_exist_until_all_three_judgments(self):
        q = self.studio.start({'count': 3})
        for choice in (2, 3, 3):
            schedule = self.studio.session.scheduler.state
            self.assertEqual(schedule['queue'], [])
            self.assertEqual(schedule['plans'], [])
            self.assertEqual(q['round'], 'judge')
            q = self.studio.answer({'id': q['id'], 'choice': choice})['next']
        self.assertEqual(q['round'], 'choice')

    def test_each_verb_keeps_stage_order_and_wrong_answers_do_not_advance(self):
        q = self.studio.start({'count': 3})
        verbs = q['batch_verbs']
        for _ in range(3):
            q = self.studio.answer({'id': q['id'], 'choice': 3})['next']
        order = ['choice', 'reverse', 'fill']
        successes = {(v, r): set() for v in verbs for r in order}
        failed = set()
        waiting = {}
        count = 0
        while not q.get('completed'):
            v, r, p = q['verbe'], q['round'], q['personne']
            if v in waiting:
                self.assertEqual(r, waiting.pop(v), 'A failed verb must return at the same stage')
            for earlier in order[:order.index(r)]:
                self.assertEqual(len(successes[v, earlier]), 6, f'{v} advanced before all {earlier} answers were correct')
            if (v, r) not in failed:
                failed.add((v, r))
                waiting[v] = r
                result = self.studio.answer({'id': q['id'], 'answer': '__wrong__'})
                self.assertFalse(result['correct'])
            else:
                result = self.solve(q)
                self.assertTrue(result['correct'])
                successes[v, r].add(p)
            q = result['next']
            count += 1
            self.assertLess(count, 150)
        self.assertTrue(all(len(done) == 6 for done in successes.values()))
        self.assertEqual(core.charger_statistiques(), {'total': 63, 'correct': 54})

    def test_wrong_choice_remains_choice_after_restart(self):
        q = self.studio.start({'count': 3})
        for _ in range(3):
            q = self.studio.answer({'id': q['id'], 'choice': 3})['next']
        verb = q['verbe']
        q = self.studio.answer({'id': q['id'], 'answer': '__wrong__'})['next']
        self.assertNotEqual(q['verbe'], verb, 'Retry should allow another word to appear first')
        self.studio = server.Studio()
        restored = self.studio.resume()
        self.assertEqual(q, restored)
        for _ in range(30):
            if q['verbe'] == verb:
                self.assertEqual(q['round'], 'choice')
                break
            q = self.solve(q)['next']
        else:
            self.fail('Failed word was lost from the random queue')

    def test_old_reverse_first_progress_migrates_without_skipping_choice(self):
        q = self.studio.start({'count': 1})
        verb = q['verbe']
        tasks = [{'verbe': verb, 'temps': '现在时', 'personnes': [p], 'personne_index': 0, 'round': r} for p in server.PERSONS for r in ['reverse', 'choice', 'fill']]
        saved = {'level': '必会', 'temps': '现在时', 'count': 1, 'done': 1, 'grouped': True, 'batch_index': 1, 'batch_count': 1, 'batch_verbs': [verb], 'queue': tasks[:1], 'post_entries': tasks[1:], 'pending_groups': [], 'index': 0}
        core.set_progress('必会', '现在时', saved)
        restarted = server.Studio()
        restored = restarted.start({'count': 1})
        self.assertEqual(restored['round'], 'choice')
        self.assertEqual(restored['done'], 1)

    def test_share_counts_completed_verbs_without_counting_persons_or_tenses_twice(self):
        yesterday = core.add_days(core.get_today(), -1)
        for p in server.PERSONS:
            core.ajouter_maitrise('être', '现在时', p, yesterday)
        stats = server.share_stats()
        self.assertEqual((stats['total_words'], stats['today_words']), (1, 0))
        for p in server.PERSONS:
            core.ajouter_maitrise('être', '复合过去时', p)
        core.ajouter_maitrise('avoir', '现在时', 'je')
        stats = server.share_stats()
        self.assertEqual((stats['total_words'], stats['today_words']), (1, 1))
        self.assertEqual(stats['today_verbs'], ['être'])
        self.studio.mutate('/api/mastered/relearn', {'keys': ['être|现在时', 'être|复合过去时']})
        self.assertEqual(server.share_stats()['total_words'], 1)

    def test_share_counts_today_review_only_after_finishing_the_verb(self):
        yesterday = core.add_days(core.get_today(), -1)
        for p in server.PERSONS:
            core.ajouter_maitrise('être', '现在时', p, yesterday)
        self.assertEqual(server.share_stats()['today_words'], 0)
        q = self.studio.start({'mode': 'review'})
        for i in range(6):
            expected = core.get_question_data(server.all_data(), q)['conjugaison']
            q = self.studio.answer({'id': q['id'], 'answer': expected})['next']
            self.assertEqual(server.share_stats()['today_words'], int(i == 5))
        self.assertTrue(q['completed'])


if __name__ == '__main__':
    unittest.main()
