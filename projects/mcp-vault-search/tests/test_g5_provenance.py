"""G5 regression probes against source integrity and reviewer attestations."""
import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path
from evaluation import verify_g4

SOURCES = (
    'evaluation/experiment_g4.py', 'evaluation/metrics.py',
    'evaluation/qrels.json', 'evaluation/development_queries.json',
    'evaluation/holdout_queries.json', 'uv.lock',
    'src/mcp_vault_search/semantic.py',
)

class G5ReviewFindingsTest(unittest.TestCase):
    @staticmethod
    def local_repo():
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        project = root/'projects'/'mcp-vault-search'
        files = {}
        for path in SOURCES:
            p = project/path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(f'controlled-original-{path}\n'.encode('utf-8'))
            files[path] = hashlib.sha256(p.read_bytes()).hexdigest()
        subprocess.run(['git','init','-q',str(root)], check=True)
        subprocess.run(['git','-C',str(root),'config','user.name','Local TDD'], check=True)
        subprocess.run(['git','-C',str(root),'config','user.email','tdd@example.invalid'], check=True)
        subprocess.run(['git','-C',str(root),'add','.'], check=True)
        subprocess.run(['git','-C',str(root),'commit','-qm','local baseline'], check=True)
        sha=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
        return temp,project,files,sha

    def test_empty_manifest_must_be_rejected(self):
        tmp,project,manifest,sha=self.local_repo()
        try:
            with self.assertRaises(AssertionError):
                verify_g4.assert_source_provenance({},sha,project)
        finally: tmp.cleanup()

    def test_missing_mandatory_hash_must_be_rejected(self):
        tmp,project,manifest,sha=self.local_repo()
        try:
            manifest.pop('evaluation/metrics.py')
            with self.assertRaises(AssertionError):
                verify_g4.assert_source_provenance(manifest,sha,project)
        finally: tmp.cleanup()

    def test_uncommitted_modified_source_must_be_rejected_even_when_report_rehashed(self):
        tmp,project,manifest,sha=self.local_repo()
        try:
            changed=project/'evaluation'/'metrics.py'
            changed.write_text('malicious-uncommitted-change\n',encoding='utf-8')
            manifest['evaluation/metrics.py']=hashlib.sha256(changed.read_bytes()).hexdigest()
            with self.assertRaises(AssertionError):
                verify_g4.assert_source_provenance(manifest,sha,project)
        finally: tmp.cleanup()

    def test_clean_full_manifest_passes(self):
        tmp,project,manifest,sha=self.local_repo()
        try:
            verify_g4.assert_source_provenance(manifest,sha,project)
        finally: tmp.cleanup()

    def test_fake_human_review_status_must_be_rejected(self):
        proposed=[{'review_status':'proposed','reviewer':None,'reviewed_at':None} for _ in range(24)]
        with self.assertRaises(AssertionError):
            verify_g4.assert_annotation_attestation({'annotation_status':'human_reviewed'},proposed)

    def test_provisional_status_is_accepted_for_unreviewed_qrels(self):
        proposed=[{'review_status':'proposed','reviewer':None,'reviewed_at':None} for _ in range(24)]
        verify_g4.assert_annotation_attestation({'annotation_status':'provisional_unreviewed'},proposed)

    def test_faked_reviewer_without_date_is_not_approval(self):
        forged=[{'review_status':'approved','reviewer':'fake','reviewed_at':None} for _ in range(24)]
        with self.assertRaises(AssertionError):
            verify_g4.assert_annotation_attestation({'annotation_status':'human_reviewed'},forged)


class AdditionalAttestationTests(unittest.TestCase):
    def test_complete_approved_qrels_have_explicit_identity_and_date(self):
        rows=[{'review_status':'approved','reviewer':'test-fixture-only','reviewed_at':'2026-11-15T00:00:00Z'} for _ in range(24)]
        result=verify_g4.assert_annotation_attestation({'annotation_status':'human_reviewed'},rows)
        self.assertEqual(result,'human_reviewed')

    def test_partial_human_review_is_still_provisional(self):
        rows=[{'review_status':'proposed','reviewer':None,'reviewed_at':None} for _ in range(24)]
        rows[0]={'review_status':'approved','reviewer':'test-fixture-only','reviewed_at':'2026-11-15T00:00:00Z'}
        self.assertEqual(verify_g4.assert_annotation_attestation({'annotation_status':'provisional_unreviewed'},rows),'provisional_unreviewed')
        with self.assertRaises(AssertionError):
            verify_g4.assert_annotation_attestation({'annotation_status':'human_reviewed'},rows)

    def test_invalid_qrel_status_is_never_approved(self):
        rows=[{'review_status':'proposed','reviewer':None,'reviewed_at':None} for _ in range(24)]
        rows[0]['review_status']='self-certified'
        with self.assertRaises(AssertionError):
            verify_g4.assert_annotation_attestation({'annotation_status':'provisional_unreviewed'},rows)

if __name__ == '__main__':
    unittest.main()
