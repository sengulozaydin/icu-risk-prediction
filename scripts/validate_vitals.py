"""Independently validate the completed Parquet in bounded batches."""
import json
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq

root=Path(__file__).resolve().parents[1]
folder=root/'data/processed'
cohort=pd.read_parquet(folder/'adult_icu_cohort_first24h.parquet')
report=json.loads((folder/'vitals_first24h.json').read_text())
items={int(k) for k in report['signature']['items']}
rows=0
seen=set()
null_values=0
error_rows=0
for batch in pq.ParquetFile(folder/'vitals_first24h.parquet').iter_batches(batch_size=65536):
    frame=batch.to_pandas()
    matched=frame.merge(cohort,on=['SUBJECT_ID','HADM_ID','ICUSTAY_ID'],how='left',validate='many_to_one')
    assert matched.INTIME.notna().all()
    assert (matched.CHARTTIME >= matched.INTIME).all()
    assert (matched.CHARTTIME < matched.INTIME+pd.Timedelta(hours=24)).all()
    assert set(frame.ITEMID).issubset(items)
    assert frame.VITAL.notna().all()
    rows+=len(frame)
    seen.update(frame.ICUSTAY_ID)
    null_values+=int(frame.VALUENUM.isna().sum())
    error_rows+=int(frame.ERROR.eq('1').sum())
assert rows==report['output_rows']
assert len(seen)==report['stays_with_vitals']
assert len(cohort)==45253
lab_ids=set(pd.read_parquet(folder/'lab_features_first24h.parquet',columns=['ICUSTAY_ID']).ICUSTAY_ID)
result={'validated_rows':rows,'cohort_stays':len(cohort),'stays_with_vitals':len(seen),'stays_without_vitals':len(cohort)-len(seen),'stays_with_vitals_without_labs':len(seen-lab_ids),'null_value_rows_retained':null_values,'error_flag_rows_retained':error_rows,'output_bytes':(folder/'vitals_first24h.parquet').stat().st_size}
(folder/'vitals_validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
