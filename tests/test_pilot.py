import copy
import json
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import yaml

from pilot import core
from pilot.runner import APIError, run_notify, sync_one

REPO = 'fixture-org/pilot'
NOW = core.stamp('2026-09-14T01:00:00Z')


def comment(number, login, body, when='2026-09-13T00:00:00Z', issue=1):
    return {'id':number, 'user':{'login':login,'id':number+100,'type':'User'}, 'body':body,
            'created_at':when,'updated_at':when, 'issue_url':f'https://api.github.com/repos/{REPO}/issues/{issue}'}


def setup_data():
    settings = yaml.safe_load(Path('config/pilot-settings.yml').read_text())
    settings.update(pilot_owner='fixture-ops', participants=['fixture-ops','fixture-primary','fixture-backup','fixture-submitter'],
        enabled_routes=['brand-and-growth'], activation_date='2026-09-14', intake_close_at='2026-09-29T23:59:00+09:00',
        weekly_ops_budget_minutes=60, activation_issue=1, activation_approval=99,
        role_acceptances={'pilot_owner':11,'brand-and-growth.primary':12,'brand-and-growth.backup':13})
    settings['routing_map']['brand-and-growth'].update(primary='fixture-primary',backup='fixture-backup')
    accepts = [comment(11,'fixture-ops','/pilot-accept pilot_owner'),comment(12,'fixture-primary','/pilot-accept brand-and-growth.primary'),
        comment(13,'fixture-backup','/pilot-accept brand-and-growth.backup'),comment(99,'fixture-ops',f'/pilot-activate {core.config_hash(settings)}')]
    body = '\n\n'.join(f'### {key}\n\n'+('모르겠음' if key == 'Purpose Team' else '구체적인 테스트 내용') for key in core.PRODUCT_FIELDS)
    issue = {'number':2,'user':{'login':'fixture-submitter'},'title':'private email: example@example.invalid', 'body':body,
        'created_at':'2026-09-14T00:01:00Z','updated_at':'2026-09-14T00:01:00Z','labels':['proposal','proposal:product'],'assignees':[],
        'html_url':f'https://github.com/{REPO}/issues/2'}
    return settings, accepts, issue


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.settings, self.activation, self.issue = setup_data()
        self.comments = []
        self.events = []

    def run_case(self, state=None, now=NOW, active='true'):
        return core.reconcile(self.settings, self.issue, self.comments, self.events, now, REPO, self.activation, active, state)

    def routed(self):
        self.comments.append(comment(110,'fixture-ops','/pilot-route brand-and-growth primary','2026-09-14T01:01:00Z',2))
        result = self.run_case()
        self.issue['assignees'] = [{'login':result['assignee']}]
        return self.run_case(result['state'])['state']

    def decide(self, decision='Active', holder='fixture-primary', acceptance='Self accepted'):
        body = f'## First decision\n- Decision: {decision}\n- Reason: 재현 근거 확인\n- Proposal DRI: @{holder}\n- Acceptance: {acceptance}\n- Next action: @{holder} 다음 검증 수행\n- Reconsideration condition/date: 2026-09-21 결과 확인'
        self.comments.append(comment(120,'fixture-primary',body,'2026-09-14T02:00:00Z',2))
        self.issue['labels'].append('decision:'+decision.lower())
        self.events.append({'event':'labeled','label':{'name':'decision:'+decision.lower()},'created_at':'2026-09-14T02:01:00Z'})

    def test_inactive_and_malformed_settings_never_intake(self):
        for active in ('false','','True','1'):
            result = self.run_case(active=active)
            self.assertNotIn('valid_at',result['state'])
            self.assertFalse(result['state']['delivery_allowed'])
            self.assertIsNone(result['assignee'])
        self.settings['pilot_owner'] = None
        self.assertNotIn('valid_at',self.run_case()['state'])

    def test_activation_requires_real_role_authors_and_current_fingerprint(self):
        self.assertEqual([],core.activation_errors(self.settings,self.activation,REPO,'true'))
        self.activation[1]['user']['login'] = 'fixture-submitter'
        self.assertTrue(core.activation_errors(self.settings,self.activation,REPO,'true'))
        self.settings,self.activation,self.issue=setup_data()
        self.settings['weekly_ops_budget_minutes']=90
        self.assertTrue(core.activation_errors(self.settings,self.activation,REPO,'true'))

    def test_acceptance_from_other_issue_is_rejected(self):
        self.activation[0]['issue_url'] = f'https://api.github.com/repos/{REPO}/issues/20'
        self.assertNotIn('valid_at',self.run_case()['state'])

    def test_scenario_is_safe_even_if_active(self):
        self.issue['labels'].append('pilot:scenario')
        result=self.run_case()
        self.assertTrue(result['state']['scenario'])
        self.assertNotIn('valid_at',result['state'])
        self.assertNotIn('deliveries',result['state'])

    def test_valid_unknown_purpose_stays_manual(self):
        result=self.run_case()
        self.assertIn('needs:routing',result['labels'])
        self.assertIsNone(result['assignee'])
        self.assertEqual('2026-09-17T14:59:00Z',result['state']['decision_due_at'])

    def test_missing_fields_and_oversized_body(self):
        self.issue['body']='### 사용자 문제\n\n_No response_'
        self.assertIn('needs:information',self.run_case()['labels'])
        self.assertNotIn('valid_at',self.run_case()['state'])
        self.issue['body']='x'*12001
        self.assertTrue(core.form_errors(self.issue)[0])

    def test_design_node_link_or_absence(self):
        self.issue['labels']=['proposal','proposal:design-system']
        for value, valid in [('https://www.figma.com/design/test/fixture?node-id=1-2',True),('미존재: 새 원칙 제안',True),('https://figma.com.evil.invalid/design/x?node-id=1-2',False),('https://www.figma.com/design/x',False),('미존재:',False)]:
            self.issue['body']='\n\n'.join(f'### {key}\n\n'+(value if key.startswith('Figma') else '테스트 내용') for key in core.DESIGN_FIELDS)
            self.assertEqual(not valid,bool(core.form_errors(self.issue)[0]),value)

    def test_holidays_and_observation_dates(self):
        self.assertEqual(date(2026,9,29),core.add_business_days(date(2026,9,14),9,self.settings))
        self.assertEqual('2026-10-02T14:59:00Z',core.deadline('2026-09-29T14:59:00Z',self.settings))
        self.assertEqual(date(2026,10,6),core.add_business_days(date(2026,10,2),1,self.settings))
        self.assertEqual('2026-09-30T14:59:00Z',core.deadline('2026-09-26T00:00:00Z',self.settings))

    def test_edits_keep_original_due_and_routing(self):
        state=self.routed()
        self.issue['body']+='\n상세 보완'
        result=self.run_case(state,core.stamp('2026-09-16T00:00:00Z'))
        self.assertEqual(state['valid_at'],result['state']['valid_at'])
        self.assertEqual(state['decision_due_at'],result['state']['decision_due_at'])
        self.assertEqual(state['route'],result['state']['route'])
        self.assertIsNone(result['assignee'])

    def test_only_ops_can_route_and_bad_route_does_not_choose_owner(self):
        self.comments=[comment(110,'fixture-submitter','/pilot-route brand-and-growth primary',issue=2)]
        self.assertIsNone(self.run_case()['assignee'])
        self.comments=[comment(110,'fixture-ops','/pilot-route unknown primary',issue=2)]
        self.assertIn('needs:routing',self.run_case()['labels'])

    def test_intake_close_does_not_stop_existing_decision(self):
        state=self.routed()
        self.decide()
        late=core.stamp('2026-10-01T00:00:00Z')
        self.assertNotIn('valid_at',self.run_case(now=late)['state'])
        self.assertIsNotNone(self.run_case(state,late)['state']['current_decision'])

    def test_valid_self_acceptance_first_decision_and_no_late_reminder(self):
        state=self.routed();self.decide()
        result=self.run_case(state)
        self.assertEqual('2026-09-14T02:01:00Z',result['state']['first_decision_at'])
        self.assertNotIn('decision:pending',result['labels'])
        later=self.run_case(result['state'],core.stamp('2026-09-18T01:00:00Z'))
        self.assertNotIn('escalation',later['state']['deliveries'])

    def test_impostor_or_label_mismatch_is_not_a_decision(self):
        state=self.routed();self.decide()
        self.comments[-1]['user']['login']='fixture-submitter'
        self.assertNotIn('first_decision_at',self.run_case(state)['state'])
        self.comments[-1]['user']['login']='fixture-primary'
        self.issue['labels'].append('decision:parked')
        self.assertNotIn('first_decision_at',self.run_case(state)['state'])

    def test_owner_acceptance_binds_to_decision_and_author(self):
        state=self.routed()
        link=f'https://github.com/{REPO}/issues/2#issuecomment-130'
        self.decide(holder='fixture-submitter',acceptance=link)
        self.assertIn('needs:owner-acceptance',self.run_case(state)['labels'])
        self.comments.append(comment(130,'fixture-submitter','/pilot-accept-decision 119','2026-09-14T03:00:00Z',2))
        self.assertNotIn('first_decision_at',self.run_case(state)['state'])
        self.comments[-1]['body']='/pilot-accept-decision 120'
        result=self.run_case(state)
        self.assertEqual('2026-09-14T03:00:00Z',result['state']['first_decision_at'])

    def test_parked_can_use_no_execution_owner_but_needs_next_action(self):
        state=self.routed();self.decide('Parked')
        self.comments[-1]['body']=self.comments[-1]['body'].replace('Proposal DRI: @fixture-primary','Proposal DRI: None (실행 보류)')
        self.assertIn('first_decision_at',self.run_case(state)['state'])
        self.comments[-1]['body']=self.comments[-1]['body'].replace('2026-09-21 결과 확인','N/A')
        self.assertNotIn('first_decision_at',self.run_case(state)['state'])

    def test_acceptance_before_decision_edit_requires_confirmation_again(self):
        state=self.routed()
        self.decide(holder='fixture-submitter',acceptance=f'https://github.com/{REPO}/issues/2#issuecomment-130')
        self.comments.append(comment(130,'fixture-submitter','/pilot-accept-decision 120','2026-09-14T03:00:00Z',2))
        self.comments[-2]['updated_at']='2026-09-14T04:00:00Z'
        self.assertNotIn('first_decision_at',self.run_case(state)['state'])

    def test_invalid_new_decision_does_not_fall_back_to_old_valid_one(self):
        state=self.routed();self.decide()
        self.comments.append(comment(140,'fixture-primary','## First decision\n- Decision: Active\n- Decision: Rejected','2026-09-14T04:00:00Z',2))
        self.assertNotIn('first_decision_at',self.run_case(state)['state'])

    def test_decision_deleted_preserves_first_measurement(self):
        state=self.routed();self.decide()
        state=self.run_case(state)['state']
        self.comments.pop()
        revised=self.run_case(state)['state']
        self.assertEqual(state['first_decision_at'],revised['first_decision_at'])
        self.assertIsNone(revised['current_decision'])

    def test_due_escalation_are_not_queued_twice(self):
        state=self.routed()
        due=self.run_case(state,core.stamp('2026-09-17T00:00:00Z'))['state']
        self.assertEqual('queued',due['deliveries']['due']['status'])
        due['deliveries']['due']['status']='sent'
        late=self.run_case(due,core.stamp('2026-09-18T00:00:00Z'))['state']
        self.assertEqual('sent',late['deliveries']['due']['status'])
        self.assertEqual('queued',late['deliveries']['escalation']['status'])
        late['deliveries']['escalation']['status']='uncertain'
        self.assertEqual('uncertain',self.run_case(late,core.stamp('2026-09-21T00:00:00Z'))['state']['deliveries']['escalation']['status'])

    def test_forged_state_and_duplicate_trusted_markers(self):
        fake=comment(1,'fixture-submitter',core.render_state({'valid_at':'forged'}))
        self.assertEqual(({},None),core.read_state([fake]))
        fake['user'].update(id=core.BOT_ID,type='Bot')
        self.assertEqual('forged',core.read_state([fake])[0]['valid_at'])
        with self.assertRaises(ValueError): core.read_state([fake,copy.deepcopy(fake)])

    def test_notification_omits_arbitrary_user_text_and_mentions(self):
        state=self.routed()
        payload=core.notification_payload(REPO,self.issue,state,'new',self.settings)
        rendered=json.dumps(payload)
        self.assertNotIn(self.issue['title'],rendered)
        self.assertNotIn(self.issue['body'],rendered)
        self.assertEqual([],payload['allowed_mentions']['parse'])


class ConfigAndFormTests(unittest.TestCase):
    def test_checked_in_config_cannot_activate(self):
        settings=yaml.safe_load(Path('config/pilot-settings.yml').read_text())
        self.assertTrue(core.activation_errors(settings,[],REPO,'true'))
        self.assertIsNone(settings['pilot_owner'])
        self.assertEqual([],settings['participants'])

    def test_form_headings_match_parser_and_yaml_is_well_formed(self):
        for filename,expected in [('product.yml',core.PRODUCT_FIELDS),('design-system.yml',core.DESIGN_FIELDS)]:
            form=yaml.safe_load(Path('.github/ISSUE_TEMPLATE',filename).read_text())
            self.assertEqual(expected,tuple(x['attributes']['label'] for x in form['body'] if x['type']!='markdown'))
            self.assertNotIn('projects',form)
            self.assertEqual(len(form['body']),len({x.get('id','intro') for x in form['body']}))
        for path in Path('.github/workflows').glob('*.yml'):
            # BaseLoader preserves the YAML 1.2 key 'on', unlike PyYAML's YAML 1.1 boolean resolver.
            workflow=yaml.load(path.read_text(),Loader=yaml.BaseLoader)
            self.assertIn('on',workflow)
            self.assertNotIn('write-all',path.read_text())

    def test_local_markdown_links(self):
        import re
        for path in [Path('README.md'),Path('START-HERE.md'),*Path('docs').glob('*.md')]:
            for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)',path.read_text()):
                if '://' not in target and not target.startswith('#'):
                    self.assertTrue((path.parent/target.split('#')[0]).exists(),f'{path}: {target}')


class FakeAPI:
    """In-memory API boundary for delivery failure tests; never performs HTTP."""
    def __init__(self):
        self.settings,self.activation,self.issue=setup_data()
        self.repo=REPO
        self.proposal_comments=[]
        self.saved=[]

    def base(self,suffix=''): return f'/repos/{REPO}'+suffix

    def comments(self,number):
        return copy.deepcopy(self.activation if number==1 else self.proposal_comments)

    def paged(self,path):
        return [] if path.endswith('/events') else [copy.deepcopy(self.issue)]

    def request(self,method,path,payload=None):
        if method=='GET': return copy.deepcopy(self.issue)
        if method=='POST' and path.endswith('/labels'):
            self.issue['labels']=list(set(self.issue['labels'])|set(payload['labels']))
            return []
        if method=='DELETE': return None
        raise AssertionError((method,path))

    def save_state(self,number,state,comment_id):
        self.saved.append(copy.deepcopy(state))
        record=comment(900,'github-actions[bot]',core.render_state(state),issue=number)
        record['user'].update(id=core.BOT_ID,type='Bot')
        self.proposal_comments=[record]


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.api=FakeAPI()
        state=core.reconcile(self.api.settings,self.api.issue,[],[],NOW,REPO,self.api.activation,'true')['state']
        self.api.save_state(2,state,None)

    def test_inactive_never_posts_even_with_existing_queue(self):
        with patch('pilot.runner.discord_post') as post:
            run_notify(self.api,self.api.settings,'false','unused')
            post.assert_not_called()

    def test_uncertain_delivery_is_reserved_before_post_and_not_retried(self):
        def fail(*args):
            self.assertEqual('sending',self.api.saved[-1]['deliveries']['new']['status'])
            raise APIError('Discord delivery uncertain; check channel before retry')
        with patch('pilot.runner.discord_post',side_effect=fail) as post:
            with self.assertRaises(APIError): run_notify(self.api,self.api.settings,'true','unused')
            self.assertEqual('uncertain',self.api.saved[-1]['deliveries']['new']['status'])
            # A second job reconciles but does not blindly POST a second time.
            run_notify(self.api,self.api.settings,'true','unused')
            self.assertEqual(1,post.call_count)
        self.assertEqual('2026-09-17T14:59:00Z',self.api.saved[-1]['decision_due_at'])

    def test_webhook_missing_preserves_github_intake(self):
        with self.assertRaises(APIError): run_notify(self.api,self.api.settings,'true','')
        self.assertEqual('failed',self.api.saved[-1]['deliveries']['new']['status'])
        self.assertIn('valid_at',self.api.saved[-1])

    def test_sent_event_is_not_replayed(self):
        with patch('pilot.runner.discord_post',return_value='fixture-message') as post:
            run_notify(self.api,self.api.settings,'true','unused')
            run_notify(self.api,self.api.settings,'true','unused')
            self.assertEqual(1,post.call_count)
        self.assertEqual('sent',self.api.saved[-1]['deliveries']['new']['status'])


if __name__ == '__main__':
    unittest.main()
