import argparse
import os
import re
import glob
import calendar
import pandas as pd

DEFAULT_INPUT_DIR = 'input'
DEFAULT_OUTPUT_DIR = 'output'


def find_input_csv(input_dir: str = DEFAULT_INPUT_DIR) -> str:
    pattern = os.path.join(input_dir, '*.csv')
    files = glob.glob(pattern)
    if not files:
        raise FileNotFoundError(f"{input_dir} フォルダ内に CSV ファイルが見つかりませんでした")
    return max(files, key=os.path.getmtime)


def build_full_date_list(dates):
    months = sorted({d[:7] for d in dates})
    full_dates = []
    for ym in months:
        y, m = map(int, ym.split('-'))
        last_day = calendar.monthrange(y, m)[1]
        full_dates.extend([f"{y:04d}-{m:02d}-{d:02d}" for d in range(1, last_day + 1)])
    return full_dates


def generate_report(input_file: str, output_csv: str):
    input_path = input_file if os.path.dirname(input_file) else os.path.join(DEFAULT_INPUT_DIR, input_file)
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"入力ファイルが見つかりません: {input_path}")

    output_path = output_csv if os.path.dirname(output_csv) else os.path.join(DEFAULT_OUTPUT_DIR, output_csv)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    df = pd.read_csv(input_path, encoding='utf-8-sig')
    df['工程'] = df['工程'].fillna(df['工程(不稼働)'])

    raw = df.groupby(['プロジェクト', '工程', '日付'], as_index=False)['時間'].sum()

    records = []
    for date, grp in raw.groupby('日付'):
        total = grp['時間'].sum()
        overtime = max(0, total - 8)
        idx_max = grp['時間'].idxmax() if overtime > 0 else None
        for idx, row in grp.iterrows():
            normal, over = row['時間'], 0.0
            if overtime > 0 and idx == idx_max:
                normal -= overtime; over = overtime
            records += [
                {'プロジェクト': row['プロジェクト'], '工程': row['工程'], '日付': date, '業務時間': '定時内', '時間': normal},
                {'プロジェクト': row['プロジェクト'], '工程': row['工程'], '日付': date, '業務時間': '定時外', '時間': over}
            ]

    df_rec = pd.DataFrame(records)

    pivot = (
        df_rec.pivot_table(index=['プロジェクト', '工程', '業務時間'], columns='日付', values='時間', aggfunc='sum', fill_value=0)
        .reset_index()
    )

    existing_dates = [c for c in pivot.columns if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(c))]
    full_dates = build_full_date_list(existing_dates)
    for d in full_dates:
        if d not in pivot.columns:
            pivot[d] = 0.0
    full_dates_sorted = sorted(full_dates)

    pivot[['プロジェクト番号', 'プロジェクト名']] = pivot['プロジェクト'].str.extract(r'^(\d+)\s*(.*)$')

    base_cols = ['プロジェクト番号', 'プロジェクト名', '工程', '業務時間']
    df_main = pivot[base_cols + full_dates_sorted]

    summary_rows = []
    for cat in ['定時内', '定時外']:
        sums = df_rec[df_rec['業務時間'] == cat].groupby('日付')['時間'].sum()
        row = {k: '' for k in ['プロジェクト番号', 'プロジェクト名', '工程']}
        row['業務時間'] = f'{cat}合計'
        for d in full_dates_sorted:
            row[d] = sums.get(d, 0.0)
        summary_rows.append(row)

    df_out = pd.concat([df_main, pd.DataFrame(summary_rows)], ignore_index=True, sort=False)

    numeric_block = df_out[full_dates_sorted].apply(pd.to_numeric, errors='coerce').fillna(0)
    df_out['合計時間'] = numeric_block.sum(axis=1)

    df_out[full_dates_sorted] = df_out[full_dates_sorted].where(df_out[full_dates_sorted] != 0, '')

    final_cols = base_cols + full_dates_sorted + ['合計時間']
    df_out[final_cols].to_csv(output_path, index=False, encoding='utf-8-sig')

    print("レポートを生成しました →", output_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='日報集計レポートジェネレータ')
    parser.add_argument('-o', '--output', default='report_output.csv', help='出力CSVファイル名')
    args = parser.parse_args()

    csv_in = find_input_csv()
    generate_report(csv_in, args.output)
