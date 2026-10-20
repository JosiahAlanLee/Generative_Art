"""Tests of catalogue coverage, decodable seals, dependency semantics and portable output."""
import hashlib,html,json,math,re,unittest
from itertools import combinations
from pathlib import Path
from xml.etree import ElementTree as ET
from generator.reachability import Task,evaluate,specimen_cases,escalation_tasks
from generator.art import seal,anchor
from generator.tx import encode,decode
ROOT=Path(__file__).resolve().parents[1]
B=json.loads((ROOT/'manuscript/catalogue.json').read_text())
NS='{http://www.w3.org/2000/svg}'

class Scheduling(unittest.TestCase):
 # Retained evaluator properties from Intervallorum test_reachability.py.
 def test_parallel_and_join_uses_maximum(self):
  t={'a':Task(4),'b':Task(6),'c':Task(2,('a','b'))};self.assertEqual(evaluate(t,'c').completion,8)
 def test_shared_prerequisite_charged_once(self):
  t={'a':Task(1,cost=3),'b':Task(1,('a',),cost=2),'c':Task(1,('a','b'),cost=1)}
  self.assertTrue(evaluate(t,'c',budget=6).feasible);self.assertEqual(evaluate(t,'c').cost,6)
 def test_exact_deadline_and_budget(self):
  t={'a':Task(3,valid_until=3,cost=2)}
  self.assertTrue(evaluate(t,'a',deadline=3).feasible);self.assertFalse(evaluate(t,'a',now=.1).feasible);self.assertFalse(evaluate(t,'a',budget=1).feasible)
 def test_invalid_dependencies_and_values_rejected(self):
  for t in [{'a':Task(1,('a',))},{'a':Task(1,('missing',))},{'a':Task(-1)},{'a':Task(float('nan'))}]:
   with self.assertRaises(ValueError):evaluate(t,'a')
 def test_every_bypass_still_waits_for_bael(self):
  cases=specimen_cases()
  for name in ['ordinary','commercial','departmental','direct','emergency']:
   self.assertFalse(cases[name]['feasible']);self.assertEqual(cases[name]['completion'],103)
   self.assertEqual(cases[name]['schedule']['bael_approval'],(90,95))
   tasks=escalation_tasks(name,absent=True)
   self.assertFalse(evaluate(tasks,'repair',deadline=1000).feasible)
 def test_absence_is_not_reported_as_executable_schedule(self):
  c=specimen_cases()['continuous_absence'];self.assertIsNone(c['completion']);self.assertEqual(c['schedule'],{})
 def test_counterfactual_removes_the_actual_dependency(self):
  c=specimen_cases()['delegated_counterfactual'];self.assertTrue(c['feasible']);self.assertEqual(c['completion'],13);self.assertNotIn('bael_approval',c['schedule'])
 def test_available_executive_changes_timing(self):
  self.assertEqual(evaluate(escalation_tasks('emergency',executive_release=0),'repair').completion,20)

class Catalogue(unittest.TestCase):
 def test_complete_upper_triangle_no_reverse_or_duplicate(self):
  self.assertEqual([t['id'] for t in B['tiers']],list(range(7)))
  edges=[(h['source'],h['target']) for h in B['handoffs']]
  self.assertEqual(sorted(edges),list(combinations(range(7),2)))
 def test_every_entry_preserves_indictment(self):
  all_entries=B['tiers']+B['handoffs']
  for e in all_entries:
   for f in ['name','office','legions','appearance','powers','binding','seal','actual_effect']:self.assertTrue(e[f])
  self.assertEqual(len({e['actual_effect'] for e in all_entries}),28)
 def test_gradients(self):
  self.assertEqual([t['authority'] for t in B['tiers']],list(range(7)))
  for field in ['competence','liability']:self.assertEqual([t[field] for t in B['tiers']],list(range(6,-1,-1)))
 def test_endpoint_geometry_decodes_pair_without_metadata(self):
  for e in B['handoffs']:
   root=ET.fromstring(seal(e['source'],e['target'],e['name'],core=e['mark']).svg())
   for role,rad,expected in [('departure',7,e['source']),('receipt',5,e['target'])]:
    group=root.find(f"{NS}g[@id='{role}']")
    # First arc's moveto is the circle's leftmost point. Infer the station from that geometry.
    path=group.find(NS+'path').get('d');m=re.match(r'M(-?[\d.]+),(-?[\d.]+)a',path)
    center=(float(m[1])+rad,float(m[2]));actual=min(range(7),key=lambda i:math.dist(center,anchor(i)))
    self.assertEqual(actual,expected);self.assertLess(math.dist(center,anchor(actual)),.15)
 def test_names_round_trip_through_inherited_hand(self):
  for e in B['tiers']+B['handoffs']:self.assertEqual(decode(encode(e['name'])),e['name'])
 def test_seal_determinism_and_uniqueness(self):
  hashes=[]
  for e in B['handoffs']:
   one=seal(e['source'],e['target'],e['name'],core=e['mark']).svg();self.assertEqual(one,seal(e['source'],e['target'],e['name'],core=e['mark']).svg());hashes.append(hashlib.sha256(one.encode()).hexdigest())
  self.assertEqual(len(set(hashes)),21)

class PortableOutput(unittest.TestCase):
 def test_no_original_workspace_or_hosted_runtime_dependencies(self):
  # Adapted from Intervallorum test_portability.py.
  for folder in ['generator','manuscript']:
   for p in (ROOT/folder).rglob('*'):
    if p.suffix in ['.py','.json','.md']:
     for forbidden in ['/home/'+'claude','/tmp/'+'claude-','/_'+'blob/','support'+'.js','DC'+'Logic','/workspace/'+'scratch/']:
      self.assertNotIn(forbidden,p.read_text())
 def test_all_effects_in_html_and_manuscript(self):
  h=html.unescape((ROOT/'output/Pseudomonarchia_Escalationum.html').read_text());m=(ROOT/'output/reading-edition.md').read_text()
  for e in B['tiers']+B['handoffs']:self.assertIn(e['actual_effect'],h);self.assertIn(e['actual_effect'],m)
 def test_no_remote_dependencies_in_reader(self):
  h=(ROOT/'output/Pseudomonarchia_Escalationum.html').read_text()
  self.assertNotRegex(h,r'(?:src|href)=["\']https?://');self.assertIn('data:font/ttf;base64,',h)
 def test_svg_masters_are_vector_only(self):
  for p in (ROOT/'output/plates').glob('*.svg'):
   r=ET.parse(p).getroot()
   for n in r.iter():self.assertNotIn(n.tag.split('}')[-1],['text','image','foreignObject','use'])
 def test_plotter_exports_are_strokes_not_filled_type(self):
  paths=list((ROOT/'output/plotter-a4').glob('*.svg'));self.assertEqual(len(paths),126)
  for p in paths:
   r=ET.parse(p).getroot();self.assertEqual(r.get('width'),'210mm')
   for n in r.iter(NS+'path'):self.assertEqual(n.get('fill'),'none')
 def test_output_hashes_match_manifest(self):
  m=json.loads((ROOT/'output/build-manifest.json').read_text())
  for p,d in m['output_sha256'].items():self.assertEqual(hashlib.sha256((ROOT/'output'/p).read_bytes()).hexdigest(),d,p)
 def test_html_identifiers_and_jump_targets(self):
  from html.parser import HTMLParser
  class IDs(HTMLParser):
   def __init__(self):super().__init__();self.ids=[];self.targets=[]
   def handle_starttag(self,tag,attrs):
    a=dict(attrs)
    if 'id' in a:self.ids.append(a['id'])
    if tag=='option':self.targets.append(a['value'])
  p=IDs();p.feed((ROOT/'output/Pseudomonarchia_Escalationum.html').read_text())
  self.assertEqual(len(p.ids),len(set(p.ids)));self.assertTrue(set(p.targets)<=set(p.ids));self.assertEqual(len(p.targets),47)
 def test_manifest_tracks_current_inputs(self):
  m=json.loads((ROOT/'output/build-manifest.json').read_text())
  for p,d in m['input_sha256'].items():self.assertEqual(hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),d,p)
 def test_no_body_evidence_tags(self):
  for s in [B['front'],B['tiers'],B['handoffs']]:self.assertNotRegex(json.dumps(s),r'\[[EDHVF]\]')

if __name__=='__main__':unittest.main()
