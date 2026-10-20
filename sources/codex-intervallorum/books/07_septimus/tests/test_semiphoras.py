import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('sv', ROOT/'semiphoras/semiphoras.py')
sv=importlib.util.module_from_spec(spec);spec.loader.exec_module(sv)

class SemiphorasTests(unittest.TestCase):
    def test_active_questions_recover_every_normalized_letter(self):
        result=sv.manifest()
        self.assertEqual([len(x) for x in result['normalized']], [72]*3)
        self.assertEqual(sv.recover(result['names']),tuple(result['normalized']))
        self.assertEqual(result['unique_identifiers'],72)

    def test_old_collision_remains_visible_with_distinct_ids(self):
        result=sv.manifest(sv.ORIGINAL_SENTENCES)
        self.assertEqual(result['names'][60], 'SNO')
        self.assertEqual(result['names'][68], 'SNO')
        self.assertEqual(result['distinct_names'],71)
        self.assertNotEqual(result['records'][60]['id'],result['records'][68]['id'])

    def test_recovery_does_not_claim_to_restore_word_boundaries(self):
        self.assertEqual(sv.letters('A b, c?'), 'ABC')
        self.assertNotIn(' ',sv.recover(sv.names(*sv.SENTENCES))[0])

    def test_rejects_wrong_size_and_invalid_recovered_symbols(self):
        with self.assertRaises(ValueError):sv.names('A',*sv.SENTENCES[1:])
        ns=sv.names(*sv.SENTENCES);ns[4]='A?C'
        with self.assertRaises(ValueError):sv.recover(ns)

if __name__=='__main__':unittest.main()
