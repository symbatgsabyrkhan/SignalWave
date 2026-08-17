from pathlib import Path

from charts.plotter import render_chart
from data.loaders import load_csv
from pipeline import analyze
from reports.render import render_detailed, render_short

root=Path(__file__).resolve().parent
vr=load_csv(root/'sample_data'/'demo.csv',symbol='DEMO',timeframe='1d')
result=analyze(vr.data)
chart=render_chart(result['data'],root/'output'/'demo_chart.png',zones=result['zones'],fibs=result['fibs'])
card=max(result['cards'],key=lambda c:c.confidence)
short=render_short('DEMO','1d',float(vr.data.close.iloc[-1]),card)
detail=render_detailed({'source':'sample CSV','rows':len(vr.data),'warnings':'; '.join(vr.warnings) or 'none'},list(result['cards']),{'indicators':'SMA/EMA, RSI, MACD, Bollinger, ATR','structure':f"{len(result['pivots'])} pivots, {len(result['zones'])} strongest zones",'Fibonacci':f"{len(result['fibs'])} levels",'Elliott':f"experimental confidence {result['elliott'].confidence}/100"},['synthetic demo data; not for market decisions'])
(root/'output'/'demo_report.txt').write_text(short+'\n\n'+detail,encoding='utf-8')
print(short)
print(f'\nChart: {chart}')
print(f'Report: {root / "output" / "demo_report.txt"}')
