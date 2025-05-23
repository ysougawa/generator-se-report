import argparse
import os
import pandas as pd

def generate_report(input_file: str, output_csv: str):
    """
    入力ファイル名（redmineフォルダ内）またはパスからプロジェクト・工程別の定時内/定時外レポートを生成し、CSVに出力する。
    """
    # 入力ファイルパスの決定
    if os.path.dirname(input_file) == '':
        # ファイル名のみ指定された場合は redmine フォルダを先頭に追加
        input_path = os.path.join('redmine', input_file)
    else:
        input_path = input_file

    # データ読み込み
    df = pd.read_csv(input_path)

    # "工程"列の統合（通常工程と不稼働工程）
    df['工程'] = df['工程'].fillna(df['工程(不稼働)'])

    # 日付ごとの時間集計
    raw = df.groupby(['プロジェクト', '工程', '日付'], as_index=False)['時間'].sum()

    # 定時内/定時外レコード作成
    records = []
    for date, group in raw.groupby('日付'):
        total = group['時間'].sum()
        overtime = max(0, total - 8)
        max_idx = group['時間'].idxmax() if overtime > 0 else None
        for idx, row in group.iterrows():
            if overtime > 0 and idx == max_idx:
                normal = row['時間'] - overtime
                over = overtime
            else:
                normal = row['時間']
                over = 0.0
            records.append({
                'プロジェクト': row['プロジェクト'],
                '工程': row['工程'],
                '日付': date,
                '業務時間': '定時内',
                '時間': normal
            })
            records.append({
                'プロジェクト': row['プロジェクト'],
                '工程': row['工程'],
                '日付': date,
                '業務時間': '定時外',
                '時間': over
            })

    df_rec = pd.DataFrame(records)

    # ピボット作成
    pivot = df_rec.pivot_table(
        index=['プロジェクト', '工程', '業務時間'],
        columns='日付',
        values='時間',
        aggfunc='sum',
        fill_value=0
    ).reset_index()

    # プロジェクト番号／名称抽出
    pivot[['プロジェクト番号', 'プロジェクト名']] = \
        pivot['プロジェクト'].str.extract(r'^(\d+)\s*(.*)$')

    # 列順
    date_cols = sorted([c for c in pivot.columns if isinstance(c, str) and re.match(r"\d{4}-\d{2}-\d{2}", c)])
    cols = ['プロジェクト番号', 'プロジェクト名', '工程', '業務時間'] + date_cols
    df_final = pivot[cols]

    # 合計行追加
    summary_rows = []
    for cat in ['定時内', '定時外']:
        sums = df_rec[df_rec['業務時間'] == cat].groupby('日付')['時間'].sum()
        row = {k: '' for k in ['プロジェクト番号', 'プロジェクト名', '工程']}
        row['業務時間'] = f'{cat}合計'
        for date in date_cols:
            row[date] = sums.get(date, 0.0)
        summary_rows.append(row)

    df_summary = pd.DataFrame(summary_rows, columns=cols)
    df_with_totals = pd.concat([df_final, df_summary], ignore_index=True)

    # CSVに出力
    df_with_totals.to_csv(output_csv, index=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='日報集計レポートジェネレータ')
    parser.add_argument('input_file', help='入力CSVファイル名（redmineフォルダ内）またはパス')
    parser.add_argument('output_csv', help='出力CSVファイルパス')
    args = parser.parse_args()

    generate_report(args.input_file, args.output_csv)
