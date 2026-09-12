import pandas as pd
import numpy as np
import altair as alt

DEFAULT_SAFE_MIN = 2.0
DEFAULT_SAFE_MAX = 8.0

def compute_risk(row, safe_min=DEFAULT_SAFE_MIN, safe_max=DEFAULT_SAFE_MAX):
    score = 0
    # Temperature value
    temp = None
    if 'temperature' in row.index:
        try:
            temp = float(row['temperature'])
        except Exception:
            temp = None
    # Direct temperature excursion
    if temp is not None:
        if temp < safe_min or temp > safe_max:
            score += 60

    # temp_min / temp_max indicators
    if 'temp_min' in row.index and 'temp_max' in row.index:
        try:
            tmin = float(row['temp_min']) if pd.notnull(row['temp_min']) else None
            tmax = float(row['temp_max']) if pd.notnull(row['temp_max']) else None
            if (tmin is not None and tmin < safe_min) or (tmax is not None and tmax > safe_max):
                score += 40
        except Exception:
            pass

    # Delay-based scoring
    if 'delay_hours' in row.index:
        try:
            d = float(row['delay_hours'])
            if d > 24:
                score += 20
            elif d > 6:
                score += 10
        except Exception:
            pass

    # Missing critical fields
    required = ['shipment_id','temperature']
    for c in required:
        if c in row.index:
            if pd.isnull(row[c]):
                score += 10
        else:
            score += 5

    return score

def analyze_shipments(df: pd.DataFrame):
    df = df.copy()
    # normalize column names
    df.columns = [c.lower().strip() for c in df.columns.astype(str)]

    # try to find shipment id column
    if 'shipment_id' not in df.columns:
        for candidate in ['id','shipment','tracking_id','tracking']:
            if candidate in df.columns:
                df = df.rename(columns={candidate:'shipment_id'})
                break

    # compute risk score
    df['risk_score'] = df.apply(compute_risk, axis=1)

    # detect temperature excursions
    df['is_temp_excursion'] = False
    if 'temperature' in df.columns:
        def is_exc(t):
            try:
                if pd.isnull(t):
                    return False
                v = float(t)
                return v < DEFAULT_SAFE_MIN or v > DEFAULT_SAFE_MAX
            except Exception:
                return False
        df['is_temp_excursion'] = df['temperature'].apply(is_exc)
    elif 'temp_min' in df.columns and 'temp_max' in df.columns:
        def is_exc2(r):
            try:
                if pd.notnull(r.get('temp_min')) and float(r.get('temp_min')) < DEFAULT_SAFE_MIN:
                    return True
                if pd.notnull(r.get('temp_max')) and float(r.get('temp_max')) > DEFAULT_SAFE_MAX:
                    return True
            except Exception:
                pass
            return False
        df['is_temp_excursion'] = df.apply(is_exc2, axis=1)

    total = len(df)
    high_risk = int((df['risk_score'] >= 60).sum())
    temp_excursions = int(df['is_temp_excursion'].sum())

    top5 = df.sort_values('risk_score', ascending=False).head(5)

    # build Altair chart for distribution
    chart_df = df[['risk_score']].copy()
    chart_df['risk_score'] = chart_df['risk_score'].astype(int)
    chart = alt.Chart(chart_df).mark_bar().encode(
        x=alt.X('risk_score:Q', bin=alt.Bin(maxbins=20), title='Risk score'),
        y=alt.Y('count()', title='Count')
    ).properties(height=300)

    recommendation = generate_recommendation(total, high_risk, temp_excursions)

    return {
        'metrics': {'total': total, 'high_risk': high_risk, 'temp_excursions': temp_excursions},
        'top5': top5,
        'chart': chart,
        'recommendation': recommendation,
        'risk_df': chart_df
    }

def generate_recommendation(total, high_risk, temp_excursions):
    if total == 0:
        return "No shipments found in the dataset."
    pct = high_risk / total * 100
    parts = []
    if high_risk == 0:
        parts.append("No high-risk shipments detected. Continue routine monitoring and preserve cold-chain logs.")
    else:
        parts.append(f"{high_risk} shipments ({pct:.1f}%) flagged as high risk.")
        if temp_excursions > 0:
            parts.append(f"{temp_excursions} temperature excursions detected — prioritize checking impacted batches and sensors.")
        parts.append("Recommended next steps: quarantine affected batches, review detailed temperature logs, investigate carrier performance, and increase sensor sampling frequency on critical routes.")

    return " ".join(parts)
