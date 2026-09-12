"""Conservative source-record quality rules; no feature selection or imputation."""
import numpy as np
import pandas as pd

# MIT-LCP MIMIC-III vitals_first_day.sql (accessed 2026-09-12).
# These are broad extraction bounds, not normal reference intervals.
VITAL_BOUNDS = {
    'Heart Rate': (0, 300), 'Respiratory Rate': (0, 70),
    'Systolic BP': (0, 400), 'Diastolic BP': (0, 300), 'Mean BP': (0, 300),
    'SpO2': (0, 100), 'Temperature F': (70, 120), 'Temperature C': (10, 50),
    'Temperature': (10, 50), 'GCS Total': (3, 15),
}

def vital_valid(name, values):
    low, high = VITAL_BOUNDS[name]
    finite = np.isfinite(values)
    if name == 'GCS Total':
        return finite & values.between(low, high) & values.mod(1).eq(0)
    return finite & values.gt(low) & (values.le(high) if name == 'SpO2' else values.lt(high))

def clean_vitals(frame):
    frame = frame.copy()
    audits = []
    error = pd.to_numeric(frame['ERROR'], errors='raise').fillna(0).ne(0)
    for name, index in frame.groupby('VITAL').groups.items():
        values = frame.loc[index, 'VALUENUM']
        bad_range = values.notna() & ~vital_valid(name, values)
        bad_error = error.loc[index] & values.notna()
        frame.loc[index[bad_range | bad_error], 'VALUENUM'] = np.nan
        audits.append({'vital': name, 'range_invalid_records': int(bad_range.sum()),
                       'error_flag_records': int(bad_error.sum()),
                       'invalid_union': int((bad_range | bad_error).sum())})
    mask = frame.VITAL.eq('Temperature F')
    frame.loc[mask, 'VALUENUM'] = (frame.loc[mask, 'VALUENUM'] - 32) * 5 / 9
    frame.loc[frame.VITAL.isin(['Temperature F','Temperature C']), 'VITAL'] = 'Temperature'
    # Rows/group keys remain present, so missingness indicators retain their semantics.
    return frame, pd.DataFrame(audits)

def clean_labs(frame):
    frame = frame.copy()
    values = frame.VALUENUM
    nonfinite = values.notna() & ~np.isfinite(values)
    invalid_zero = frame.ITEMID.isin([51222,51237]) & values.le(0)
    bad = nonfinite | invalid_zero
    audit = frame.loc[bad].groupby('ITEMID').size().rename('invalid_records')
    frame.loc[bad,'VALUENUM'] = np.nan
    return frame, audit

def clean_urine(frame):
    values = frame.VALUE
    bad = values.notna() & (~np.isfinite(values) | values.lt(0) | values.gt(100000))
    # >100 L in a single urine entry is an explicit gross-error screen, not winsorization.
    # Smaller extreme entries (including 47,050 mL) require review and are retained.
    audit = frame.loc[bad,['ICUSTAY_ID','ITEMID','VALUE']].copy()
    return frame.loc[~bad].copy(), audit

def numeric_audit(frame):
    rows=[]
    for name in frame.select_dtypes(include='number'):
        if name == 'ICUSTAY_ID':
            continue
        values=frame[name]
        finite=values[np.isfinite(values)]
        rows.append({'column':name,'missing':int(values.isna().sum()),
            'infinite':int(np.isinf(values).sum()),'negative':int(values.lt(0).sum()),
            'zero':int(values.eq(0).sum()),'min':finite.min(),'p001':finite.quantile(.001),
            'p01':finite.quantile(.01),'median':finite.median(),'p99':finite.quantile(.99),
            'p995':finite.quantile(.995),'p999':finite.quantile(.999),'max':finite.max()})
    return pd.DataFrame(rows)
