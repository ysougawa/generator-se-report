# generator-se-report

[SE 日報](https://oec-itsol.cloud.redmine.jp/time_entries?set_filter=1&sort=spent_on%2Cproject&f%5B%5D=spent_on&op%5Bspent_on%5D=lm&f%5B%5D=author_id&op%5Bauthor_id%5D=%3D&v%5Bauthor_id%5D%5B%5D=me&f%5B%5D=project_id&op%5Bproject_id%5D=%3D&v%5Bproject_id%5D%5B%5D=mine&f%5B%5D=&c%5B%5D=spent_on&c%5B%5D=project&c%5B%5D=issue.cf_902&c%5B%5D=issue.cf_614&c%5B%5D=hours&group_by=&t%5B%5D=)

##

1. `Python`と`pip`が認識されることを確認。

```bash
python --version
pip --version
```

1. `pandas`のインストール

```bash
pip install pandas
```

1. 権限エラーが出る場合

```bash
python -m pip install --user pandas
```
