import argparse
import os
import re
import glob
import calendar
import pandas as pd

DEFAULT_INPUT_DIR = 'input'
DEFAULT_OUTPUT_DIR = 'output'


def find_input_csv(input_dir: str = DEFAULT_INPUT_DIR) -> str:
    files = glob.glob(os.path.join(input_dir, '*.csv'))
    if not files:
        raise FileNotFoundError(f"{input_dir} フォルダ内に CSV ファイルが見つかりません")
    return max(files, key=os.path.getmtime)


def build_full_dates(dates):
    months = sorted({d[:7] for d in dates})
    full = []
    for ym in months:
        y, m = map(int, ym.split('-'))
        for d in range(1, calendar.monthrange(y, m)[1] + 1):
            full.append(f"{y:04d}-{m:02d}-{d:02d}")
    return full


def split_regular_overtime(day_df: pd.DataFrame) -> list[dict]:
    """順次割当てで残業を分散し、負の通常時間を作らないレコードを返す"""
    total = day_df['時間'].sum()
    ot_left = max(0, total - 8)

    # 作業時間の大きい順で処理
    day_df = day_df.sort_values('時間', ascending=False).reset_index(drop=True)
    rows = []
    for _, r in day_df.iterrows():
        avail = r['時間']
        take_ot = min(avail, ot_left)
        reg = avail - take_ot
        rows.append({**r, '業務時間': '定時内', '時間': reg})
        rows.append({**r, '業務時間': '定時外', '時間': take_ot})
        ot_left -= take_ot
    return rows


def generate_report(input_file: str, output_csv: str):
    inp = input_file if os.path.dirname(input_file) else os.path.join(DEFAULT_INPUT_DIR, input_file)
    if not os.path.exists(inp):
        raise FileNotFoundError(inp)
    outp = output_csv if os.path.dirname(output_csv) else os.path.join(DEFAULT_OUTPUT_DIR, output_csv)
    os.makedirs(os.path.dirname(outp), exist_ok=True)

    df = pd.read_csv(inp, encoding='utf-8-sig')
    df['工程'] = df['工程'].fillna(df['工程(不稼働)'])

    # 1 日あたりの作業時間集計
    day_grp = df.groupby(['プロジェクト', '工程', '日付'], as_index=False)['時間'].sum()

    recs = []
    for date, g in day_grp.groupby('日付'):
        recs.extend(split_regular_overtime(g))

    df_rec = pd.DataFrame(recs)

    # Pivot
    pivot = df_rec.pivot_table(index=['プロジェクト', '工程', '業務時間'], columns='日付', values='時間', aggfunc='sum', fill_value=0).reset_index()

    date_cols_exist = [c for c in pivot.columns if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(c))]
    full_dates = build_full_dates(date_cols_exist)
    for d in full_dates:
        if d not in pivot.columns:
            pivot[d] = 0.0
    full_dates.sort()

    pivot[['プロジェクト番号', 'プロジェクト名']] = pivot['プロジェクト'].str.extract(r'^(\d+)\s*(.*)$')
    base_cols = ['プロジェクト番号', 'プロジェクト名', '工程', '業務時間']
    df_main = pivot[base_cols + full_dates]

    # summary (totals per day)
    summary = []
    for cat in ['定時内', '定時外']:
        sums = df_rec[df_rec['業務時間'] == cat].groupby('日付')['時間'].sum()
        row = {k: '' for k in ['プロジェクト番号', 'プロジェクト名', '工程']}
        row['業務時間'] = f'{cat}合計'
        for d in full_dates:
            row[d] = sums.get(d, 0.0)
        summary.append(row)

    df_out = pd.concat([df_main, pd.DataFrame(summary)], ignore_index=True)

    numeric_block = df_out[full_dates].apply(pd.to_numeric, errors='coerce').fillna(0)
    df_out['合計時間'] = numeric_block.sum(axis=1)
    df_out[full_dates] = df_out[full_dates].where(df_out[full_dates] != 0, '')

    final_cols = base_cols + full_dates + ['合計時間']
    df_out[final_cols].to_csv(outp, index=False, encoding='utf-8-sig')
    print('レポートを生成しました →', outp)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output', default='report_output.csv')
    args = parser.parse_args()

    csv_in = find_input_csv()
    generate_report(csv_in, args.output)
