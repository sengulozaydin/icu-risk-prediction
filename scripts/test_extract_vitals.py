"""Check cohort inclusion, exact time boundaries, strict parsing, and cache reuse."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq
import extract_vitals as ex

class ExtractionTest(unittest.TestCase):
    def test_boundaries_and_strict_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            ex.ROOT = Path(directory)
            ex.DATA = ex.ROOT / 'raw'
            ex.DATA.mkdir()
            (ex.ROOT / 'notebooks').mkdir()
            (ex.ROOT / 'data/processed').mkdir(parents=True)
            (ex.ROOT / 'notebooks/02_feature_engineering.ipynb').write_text(json.dumps({'cells': [{'cell_type':'code', 'source':['vital_itemids = {"Heart Rate": [211]}']}]}))
            pd.DataFrame({'SUBJECT_ID':[1,2,3], 'DOB':['2050-01-01','2095-01-01','2050-01-01']}).to_csv(ex.DATA/'PATIENTS.csv', index=False)
            pd.DataFrame({'SUBJECT_ID':[1,1,2,3], 'HADM_ID':[10,11,20,30], 'ICUSTAY_ID':[100,101,200,300], 'INTIME':['2100-01-01']*4, 'OUTTIME':['2100-01-03']*4, 'LOS':[2,2,2,0.5]}).to_csv(ex.DATA/'ICUSTAYS.csv', index=False)
            header=['ROW_ID','SUBJECT_ID','HADM_ID','ICUSTAY_ID','ITEMID','CHARTTIME','STORETIME','VALUENUM','VALUEUOM','ERROR']
            rows=[
                [1,1,10,100,211,'2100-01-01 00:00:00','2100-01-01',80,'bpm',0],
                [2,1,10,100,211,'2100-01-01 23:59:59','2100-01-02',90,'bpm',1],
                [3,1,10,100,211,'2100-01-02 00:00:00','2100-01-02',100,'bpm',0],
                [4,1,10,100,211,'2099-12-31 23:59:59','2100-01-01',70,'bpm',0],
                [5,1,11,101,211,'2100-01-01 01:00:00','2100-01-01','','bpm',0],
                [6,1,999,100,211,'2100-01-01 01:00:00','2100-01-01',80,'bpm',0],
                [7,2,20,200,211,'2100-01-01 01:00:00','2100-01-01',80,'bpm',0],
                [8,1,10,100,999,'2100-01-01 01:00:00','2100-01-01',80,'bpm',0]]
            raw=ex.DATA/'CHARTEVENTS.csv'
            with raw.open('w') as f:
                writer=csv.writer(f); writer.writerow(header); writer.writerows(rows)
            report=ex.run(expected_cohort_size=2)
            output=ex.ROOT/'data/processed/vitals_first24h.parquet'
            result=pq.read_table(output).to_pandas()
            self.assertEqual(result.ROW_ID.tolist(), [1,2,5])
            self.assertEqual(report['stays_with_vitals'], 2)
            self.assertTrue(pd.isna(result.loc[2,'VALUENUM']))
            before=output.stat().st_mtime_ns
            self.assertEqual(ex.run(expected_cohort_size=2), report)
            self.assertEqual(output.stat().st_mtime_ns,before)
            with raw.open('a') as f:
                f.write('broken,row\n')
            with self.assertRaises(Exception):
                ex.run(expected_cohort_size=2)
            self.assertEqual(output.stat().st_mtime_ns,before)

if __name__=='__main__':
    unittest.main()
