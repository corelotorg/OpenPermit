"""Positive and adversarial tests for the public synthetic example."""
import copy
import json
import unittest
from validate import FILE, check

class ContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads(FILE.read_text(encoding="utf-8"))

    def test_fixture_passes(self):
        self.assertEqual(check(self.fixture), [])

    def test_missing_nail_rejected(self):
        modified=copy.deepcopy(self.fixture)
        modified["fastener_candidates"]["points"].pop()
        self.assertIn("fastener candidates",check(modified))

    def test_shifted_nail_rejected(self):
        modified=copy.deepcopy(self.fixture)
        modified["fastener_candidates"]["points"][0]["x"]=1
        self.assertIn("fastener candidates",check(modified))

    def test_false_authority_rejected(self):
        modified=copy.deepcopy(self.fixture)
        modified["gates"]["regulatory_approval"]="PASS"
        self.assertIn("authority/gates",check(modified))

    def test_invented_ifc_receipt_rejected(self):
        modified=copy.deepcopy(self.fixture)
        modified["deliverables"]["independent_ifc_receipt"]="PASS"
        self.assertIn("projection claims",check(modified))

    def test_unverified_candidate_must_stay_unverified(self):
        modified=copy.deepcopy(self.fixture)
        modified["fastener_candidates"]["verified_as_installable"]=True
        self.assertIn("fastener candidates",check(modified))

if __name__=="__main__":
    unittest.main()
