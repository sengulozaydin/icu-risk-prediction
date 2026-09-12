"""Bounded-memory, strict CSV extraction of the notebook's selected vital events."""
from contextlib import ExitStack
import ast
import json
import time
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.csv as csv
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
DATA = Path('/mnt/c/Users/vetts/Downloads/MimicIII/mimic-iii-clinical-database-1.4')

def source(name):
    path = DATA / (name + '.csv')
    return path if path.is_file() else path / (name + '.csv')

def run(expected_cohort_size=45253):
    nb = json.loads((ROOT / 'notebooks/02_lab_vital_features.ipynb').read_text())
    mappings = []
    for cell in nb['cells']:
        if cell['cell_type'] != 'code':
            continue
        for node in ast.parse(''.join(cell['source'])).body:
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'vital_itemids' for t in node.targets):
                mappings.append(ast.literal_eval(node.value))
    assert len(mappings) == 1
    items = {str(i): name for name, ids in mappings[0].items() for i in ids}
    stays = pd.read_csv(source('ICUSTAYS'))
    patients = pd.read_csv(source('PATIENTS'), usecols=['SUBJECT_ID', 'DOB'])
    stays = stays.merge(patients, on='SUBJECT_ID', validate='many_to_one')
    for c in ['INTIME', 'OUTTIME', 'DOB']:
        stays[c] = pd.to_datetime(stays[c]).astype('datetime64[us]')
    age = (stays.INTIME - stays.DOB).dt.total_seconds() / (365.25 * 86400)
    keys = ['SUBJECT_ID', 'HADM_ID', 'ICUSTAY_ID']
    cohort = stays.loc[(age >= 18) & (stays.LOS >= 1) & stays.OUTTIME.notna(), keys + ['INTIME']].copy()
    assert not cohort.ICUSTAY_ID.duplicated().any() and not cohort.isna().any().any()
    assert len(cohort) == expected_cohort_size, 'Unexpected target cohort size'
    output = ROOT / 'data/processed/vitals_first24h.parquet'
    report_path = output.with_suffix('.json')
    signature = {'inputs': {name: [source(name).stat().st_size, source(name).stat().st_mtime_ns] for name in ['CHARTEVENTS', 'ICUSTAYS', 'PATIENTS']}, 'items': items, 'version': 1}
    if output.exists() and report_path.exists():
        report = json.loads(report_path.read_text())
        if report['signature'] == signature and pq.ParquetFile(output).metadata.num_rows == report['output_rows']:
            return report
    cols = ['ROW_ID'] + keys + ['ITEMID', 'CHARTTIME', 'STORETIME', 'VALUENUM', 'VALUEUOM', 'ERROR']
    schema = pa.schema([(c, pa.int64()) for c in cols[:5]] + [('CHARTTIME', pa.timestamp('us')), ('STORETIME', pa.timestamp('us')), ('VALUENUM', pa.float64()), ('VALUEUOM', pa.string()), ('ERROR', pa.string()), ('VITAL', pa.string())])
    counts = dict(source_rows=0, selected_item_rows=0, cohort_event_rows=0, missing_charttime_rows=0, output_rows=0)
    seen = set()
    started = time.monotonic()
    partial = output.with_suffix('.parquet.partial')
    with ExitStack() as resources:
        raw_file = resources.enter_context(open(source('CHARTEVENTS'), 'rb'))
        reader = resources.enter_context(csv.open_csv(raw_file, read_options=csv.ReadOptions(block_size=1024*1024, use_threads=False), parse_options=csv.ParseOptions(newlines_in_values=True), convert_options=csv.ConvertOptions(include_columns=cols, column_types={c: pa.string() for c in cols})))
        with reader, pq.ParquetWriter(partial, schema, compression='zstd') as writer:
            for n, batch in enumerate(reader):
                frame = batch.to_pandas()
                counts['source_rows'] += len(frame)
                frame = frame.loc[frame.ITEMID.isin(items)].copy()
                counts['selected_item_rows'] += len(frame)
                for c in cols[:5]:
                    frame[c] = pd.to_numeric(frame[c], errors='raise').astype('Int64')
                frame = frame.merge(cohort, on=keys, how='inner', validate='many_to_one')
                counts['cohort_event_rows'] += len(frame)
                frame['CHARTTIME'] = pd.to_datetime(frame.CHARTTIME, errors='raise')
                counts['missing_charttime_rows'] += int(frame.CHARTTIME.isna().sum())
                frame = frame.loc[(frame.CHARTTIME >= frame.INTIME) & (frame.CHARTTIME < frame.INTIME + pd.Timedelta(hours=24))].copy()
                frame['STORETIME'] = pd.to_datetime(frame.STORETIME, errors='raise')
                frame['VALUENUM'] = pd.to_numeric(frame.VALUENUM, errors='raise')
                frame['VITAL'] = frame.ITEMID.astype(str).map(items)
                seen.update(frame.ICUSTAY_ID.tolist())
                counts['output_rows'] += len(frame)
                if len(frame):
                    writer.write_table(pa.Table.from_pandas(frame[schema.names], schema=schema, preserve_index=False))
                if n % 100 == 0:
                    print(f"Read {counts['source_rows']:,}; retained {counts['output_rows']:,}; {time.monotonic()-started:.0f}s", flush=True)
    assert pq.ParquetFile(partial).metadata.num_rows == counts['output_rows'] > 0
    cohort.to_parquet(output.parent / 'adult_icu_cohort_first24h.parquet', index=False)
    partial.replace(output)
    report = {'signature': signature, **counts, 'cohort_stays': len(cohort), 'stays_with_vitals': len(seen), 'stays_without_vitals': len(cohort)-len(seen), 'elapsed_seconds': round(time.monotonic()-started, 1), 'window': 'INTIME <= CHARTTIME < INTIME + 24 hours', 'policy': 'Strict CSV parsing. Raw units, null values, and ERROR flags retained; no silent malformed-row skipping.'}
    report_path.write_text(json.dumps(report, indent=2) + '\n')
    return report

if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
