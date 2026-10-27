"""Invented country delivery states, independent from research uncertainties."""
from copy import deepcopy
import unittest
from web import batch_progress


class ProgressTests(unittest.TestCase):
    def report(self):
        return {'key':'invented-key','edition':'invented-edition','model':{
            'version_label':'Report v3','preparation':{'overview':'published'},
            'delivery_checks':{'photo':'available'},'review':{'human':{'state':'not_requested'}},
            'coverage':[{'state':'investigated_unresolved','detail':'Future fees unknown'}]}}

    def test_independent_countries_and_missing_photo_have_named_recovery(self):
        before=self.report();rows=batch_progress.countries(['GBR','DNK'],{'GBR':before})
        self.assertTrue(rows[0]['available']);self.assertEqual(rows[0]['outstanding'],[])
        self.assertFalse(rows[1]['available']);self.assertEqual(rows[1]['outstanding'][0]['item'],'Prepared report')
        later=deepcopy(before);later['model']['delivery_checks']={'photo':'unavailable','photo_reason':'License could not be verified; Ali must locate a licensed source.'}
        rows=batch_progress.countries(['GBR','DNK'],{'GBR':before,'DNK':later})
        self.assertEqual(rows[0]['outstanding'],[]);self.assertIn('Ali',rows[1]['outstanding'][0]['owner'])
        self.assertIn('License',rows[1]['outstanding'][0]['reason']);self.assertIn('Acquire',rows[1]['outstanding'][0]['action'])
        self.assertEqual(batch_progress.summary(rows,'partial')['outstanding_count'],1)

    def test_uncertainty_and_human_nonapproval_do_not_keep_bounded_delivery_partial(self):
        rows=batch_progress.countries(['GBR','DNK'],{'GBR':self.report(),'DNK':self.report()})
        summary=batch_progress.summary(rows,'complete')
        self.assertEqual(summary['outstanding_count'],0);self.assertEqual(summary['published'],2)
        self.assertIn('bounded response complete',summary['label'])
        self.assertIn('response partial',batch_progress.summary(rows,'partial')['label'])
        self.assertEqual(rows[0]['review']['human']['state'],'not_requested')

    def test_university_only_work_does_not_invent_a_missing_country_report_deliverable(self):
        row=batch_progress.countries(['DNK'],{},requires_reports=False)[0]
        self.assertFalse(row['required']);self.assertEqual(row['outstanding'],[])


if __name__=='__main__':unittest.main()
