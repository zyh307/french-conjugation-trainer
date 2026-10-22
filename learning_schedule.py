"""Three-verb batches with a round barrier for each verb and randomized retries."""
import copy
import random

ROUND_ORDER = ['choice', 'reverse', 'fill']


def verb_key(entry):
    return entry['verbe'] + '|' + entry['temps']


class GroupedPractice:
    VERSION = 2

    def __init__(self, groups=None, settings=None, state=None):
        self.state = state if state is not None else {
            'version': self.VERSION,
            'rounds': [r for r in ROUND_ORDER if settings.get('enable_' + r, True)],
            'groups': [{'entries': copy.deepcopy(group)} for group in groups],
            'cursor': -1, 'offset': 0, 'judges': [], 'plans': [], 'queue': [],
            'entries': [], 'decisions': {}, 'last_verb': None,
        }

    @classmethod
    def from_progress(cls, saved, settings):
        if saved.get('schedule', {}).get('version') == cls.VERSION:
            return cls(state=copy.deepcopy(saved['schedule']))

        def convert(queue, pool):
            entries, judged, starts = {}, set(), {}
            for item in queue + pool:
                k = verb_key(item)
                entry = entries.setdefault(k, {'verbe': item['verbe'], 'temps': item['temps'], 'personnes': [], 'personne_index': 0, 'round': 'judge'})
                for p in item.get('personnes', []):
                    if p not in entry['personnes']:
                        entry['personnes'].append(p)
                if item['round'] == 'judge':
                    judged.add(k)
                elif item['round'] in ROUND_ORDER:
                    starts[k] = min(starts.get(k, 99), ROUND_ORDER.index(item['round']))
            return {'entries': list(entries.values()), 'judge_keys': list(judged), 'starts': starts}

        queue = copy.deepcopy(saved.get('queue', []))
        pool = copy.deepcopy(saved.get('post_entries', []))
        groups = []
        if saved.get('grouped'):
            groups.append(convert(queue, pool))
            for group in saved.get('pending_groups', []):
                groups.append(convert(group['queue'], group.get('post_entries', [])))
            offset = max(saved.get('batch_index', 1) - 1, 0)
        else:
            for group in saved.get('groups', [])[saved.get('group_index', 0) + 1:]:
                queue.extend(copy.deepcopy(group))
            order = list(dict.fromkeys(verb_key(e) for e in queue + pool))
            for i in range(0, len(order), 3):
                keys = set(order[i:i + 3])
                groups.append(convert([e for e in queue if verb_key(e) in keys], [e for e in pool if verb_key(e) in keys]))
            offset = 0
        scheduler = cls([], settings)
        scheduler.state.update(groups=[g for g in groups if g['entries']], offset=offset)
        return scheduler

    def remove_words(self, selected):
        s = self.state
        for group in s['groups']:
            group['entries'] = [e for e in group['entries'] if verb_key(e) not in selected]
            if 'judge_keys' in group:
                group['judge_keys'] = [k for k in group['judge_keys'] if k not in selected]
            for k in selected:
                group.get('starts', {}).pop(k, None)
        for field in ('entries', 'judges', 'plans', 'queue'):
            s[field] = [e for e in s[field] if verb_key(e) not in selected]
        for k in selected:
            s['decisions'].pop(k, None)
        if s['last_verb'] in selected:
            s['last_verb'] = None

    def return_words(self, entries):
        s = self.state
        self.remove_words({verb_key(e) for e in entries})
        at = max(s['cursor'] + 1, 0)
        s['groups'][at:at] = [{'entries': copy.deepcopy(entries[i:i + 3])} for i in range(0, len(entries), 3)]

    def _activate(self):
        s = self.state
        s['cursor'] += 1
        if s['cursor'] >= len(s['groups']):
            return False
        group = s['groups'][s['cursor']]
        s['entries'] = copy.deepcopy(group['entries'])
        judge_keys = set(group.get('judge_keys', [verb_key(e) for e in s['entries']]))
        s['judges'] = [copy.deepcopy(e) for e in s['entries'] if verb_key(e) in judge_keys]
        s['decisions'] = {verb_key(e): 3 for e in s['entries'] if verb_key(e) not in judge_keys}
        s['plans'] = []
        s['queue'] = []
        s['prepared'] = False
        return True

    @staticmethod
    def _tasks(plan):
        return [{'verbe': plan['verbe'], 'temps': plan['temps'], 'personnes': [p], 'personne_index': 0, 'round': plan['rounds'][plan['stage']]} for p in plan['remaining']]

    def _mix(self):
        s = self.state
        random.shuffle(s['queue'])
        alternatives = [i for i, e in enumerate(s['queue']) if verb_key(e) != s['last_verb']]
        if alternatives:
            i = random.choice(alternatives)
            s['queue'][0], s['queue'][i] = s['queue'][i], s['queue'][0]

    def _prepare(self):
        s = self.state
        group = s['groups'][s['cursor']]
        for entry in s['entries']:
            if s['decisions'].get(verb_key(entry)) == 1 or not s['rounds']:
                continue
            # Old saves may already have completed earlier stages. Keep their progress.
            start = group.get('starts', {}).get(verb_key(entry), 0)
            rounds = [r for r in s['rounds'] if ROUND_ORDER.index(r) >= start]
            if not rounds:
                continue
            plan = {**copy.deepcopy(entry), 'rounds': rounds, 'stage': 0, 'remaining': list(entry['personnes'])}
            s['plans'].append(plan)
            s['queue'].extend(self._tasks(plan))
        s['prepared'] = True
        self._mix()

    def current(self):
        s = self.state
        while True:
            if s['cursor'] < 0 and not self._activate():
                return None
            if s['cursor'] >= len(s['groups']):
                return None
            if s['judges']:
                return s['judges'][0]
            if not s.get('prepared'):
                self._prepare()
            if s['queue']:
                return s['queue'][0]
            if not self._activate():
                return None

    def judge(self, choice):
        s = self.state
        entry = s['judges'].pop(0)
        s['decisions'][verb_key(entry)] = choice
        # No practice task is created until current() sees that every judge is done.
        return entry

    def answer(self, correct):
        s = self.state
        entry = s['queue'].pop(0)
        plan = next(p for p in s['plans'] if verb_key(p) == verb_key(entry))
        person = entry['personnes'][0]
        final = correct and plan['stage'] == len(plan['rounds']) - 1
        if correct:
            plan['remaining'].remove(person)
            if not plan['remaining']:
                plan['stage'] += 1
                if plan['stage'] < len(plan['rounds']):
                    plan['remaining'] = list(plan['personnes'])
                    s['queue'].extend(self._tasks(plan))
        else:
            # A wrong task returns unchanged; its verb cannot advance past this stage.
            s['queue'].append(entry)
        s['last_verb'] = verb_key(entry)
        self._mix()
        return entry, final

    def remaining(self):
        s = self.state
        def tasks(entry, group):
            start = group.get('starts', {}).get(verb_key(entry), 0)
            return len(entry['personnes']) * sum(ROUND_ORDER.index(r) >= start for r in s['rounds'])
        future = 0
        for group in s['groups'][s['cursor'] + 1:]:
            judges = set(group.get('judge_keys', [verb_key(e) for e in group['entries']]))
            future += sum(1 if verb_key(e) in judges else tasks(e, group) for e in group['entries'])
        if s['cursor'] >= len(s['groups']):
            return 0
        if not s.get('prepared'):
            return future + len(s['judges']) + sum(tasks(e, s['groups'][s['cursor']]) for e in s['entries'] if s['decisions'].get(verb_key(e)) in (2, 3))
        return future + sum(len(p['remaining']) + max(0, len(p['rounds']) - p['stage'] - 1) * len(p['personnes']) for p in s['plans'])

    def batch_info(self):
        s = self.state
        return {'batch_index': s['offset'] + s['cursor'] + 1, 'batch_count': s['offset'] + len(s['groups']), 'batch_verbs': [e['verbe'] for e in s['entries']]}
