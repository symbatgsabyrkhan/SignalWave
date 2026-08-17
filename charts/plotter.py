"""Deterministic, Telegram-ready chart rendering for SignalWave."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis.fibonacci import FibLevel
from analysis.structure import TrendLine, Zone, strongest_zones


def _candles(ax, df: pd.DataFrame):
    x=np.arange(len(df)); width=.62
    for i,row in enumerate(df.itertuples()):
        o,h,l,c=float(row.open),float(row.high),float(row.low),float(row.close)
        up=c>=o
        color="#26a69a" if up else "#ef5350"
        ax.vlines(i,l,h,color=color,linewidth=.7,alpha=.9)
        bottom=min(o,c); height=max(abs(c-o), max(abs(c)*0.0002,1e-9))
        ax.add_patch(plt.Rectangle((i-width/2,bottom),width,height,facecolor=color,edgecolor=color,linewidth=.5))
    return x


def _finish(fig, path: str|Path):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path,dpi=140,bbox_inches="tight",facecolor=fig.get_facecolor())
    plt.close(fig); return path


def render_chart(df:pd.DataFrame,path:str|Path,zones:list[Zone]|None=None,trendlines:list[TrendLine]|None=None,fibs:list[FibLevel]|None=None,max_zones:int=6)->Path:
    """Compatibility chart: candles + MAs + zones/Fib + RSI."""
    if df.empty: raise ValueError("cannot render empty data")
    view=df.tail(220).reset_index(drop=True)
    fig=plt.figure(figsize=(11,7)); fig.patch.set_facecolor("#0b1220")
    ax=fig.add_axes([.07,.34,.9,.59]); rax=fig.add_axes([.07,.09,.9,.18],sharex=ax)
    for a in (ax,rax): a.set_facecolor("#101827"); a.grid(alpha=.12); a.tick_params(colors="#a9b7c6")
    x=_candles(ax,view)
    for p in (20,50,200):
        c=f"sma_{p}"
        if c in view and view[c].notna().any(): ax.plot(x,view[c],label=f"SMA {p}",linewidth=1.2)
    for z in strongest_zones(zones or [],max_zones): ax.axhspan(z.low,z.high,alpha=.12,label=f"{z.kind} {z.center:.0f}")
    for f in fibs or []: ax.axhline(f.price,linestyle=":",alpha=.65)
    if "rsi_14" in view:
        rax.plot(x,view["rsi_14"],label="RSI 14",linewidth=1.1); rax.axhline(70,ls="--",lw=.8); rax.axhline(30,ls="--",lw=.8); rax.set_ylim(0,100)
    ax.set_title("SignalWave — Trend + SMA / RSI",color="white",weight="bold"); ax.set_ylabel("Price",color="#a9b7c6"); rax.set_ylabel("RSI",color="#a9b7c6")
    ax.legend(loc="upper left",fontsize=7,ncol=3)
    return _finish(fig,path)


def render_structure_chart(df,path,zones,pivots):
    view=df.tail(260).reset_index(drop=True); offset=max(0,len(df)-len(view))
    fig,ax=plt.subplots(figsize=(11,6)); fig.patch.set_facecolor("#0b1220"); ax.set_facecolor("#101827"); ax.grid(alpha=.12); ax.tick_params(colors="#a9b7c6")
    _candles(ax,view)
    for z in strongest_zones(zones,6):
        ax.axhspan(z.low,z.high,alpha=.16); ax.text(len(view)*.02,z.center,f"{z.kind.title()} • {z.touches} touches",fontsize=8,va="center")
    for kind in ("low","high"):
        pts=[p for p in pivots if p.kind==kind and p.index>=offset]
        if len(pts)>=2:
            xs=np.array([p.index-offset for p in pts]); ys=np.array([p.price for p in pts]); slope,intercept=np.polyfit(xs,ys,1)
            ax.plot([xs.min(),xs.max()],[slope*xs.min()+intercept,slope*xs.max()+intercept],ls="--",lw=1.5,label=f"{kind} trendline")
    ax.set_title("Support / Resistance zones + trendlines",color="white",weight="bold"); ax.legend(fontsize=8)
    return _finish(fig,path)


def render_fibonacci_chart(df,path,fibs,pivots):
    view=df.tail(260).reset_index(drop=True); fig,ax=plt.subplots(figsize=(11,6)); fig.patch.set_facecolor("#0b1220"); ax.set_facecolor("#101827"); ax.grid(alpha=.12); ax.tick_params(colors="#a9b7c6"); _candles(ax,view)
    for f in fibs:
        ax.axhline(f.price,ls="--" if f.kind=="extension" else ":",lw=1.1,alpha=.85)
        ax.text(len(view)-1,f.price,f" {f.ratio:.3f} • {f.price:,.2f}"+(" ★ confluence" if f.confluence else ""),fontsize=8,va="center",ha="right")
    ax.set_title("Fibonacci retracement / extension",color="white",weight="bold")
    return _finish(fig,path)


def render_elliott_chart(df,path,pivots,elliott):
    view=df.tail(360).reset_index(drop=True); offset=max(0,len(df)-len(view)); fig,ax=plt.subplots(figsize=(11,6)); fig.patch.set_facecolor("#0b1220"); ax.set_facecolor("#101827"); ax.grid(alpha=.12); ax.tick_params(colors="#a9b7c6"); ax.plot(np.arange(len(view)),view["close"],lw=1.0)
    seq=sorted(pivots,key=lambda p:p.index)[-6:]
    if len(seq)==6:
        xs=[p.index-offset for p in seq]; ys=[p.price for p in seq]; ax.plot(xs,ys,lw=1.5,marker="o")
        labels=("0","1","2","3","4","5")
        for x,y,label in zip(xs,ys,labels): ax.annotate(label,(x,y),xytext=(0,10),textcoords="offset points",ha="center",weight="bold")
    ax.set_title(f"Elliott Wave — primary count • confidence {elliott.confidence}/100"+(" • alternate count possible" if elliott.alternate else ""),color="white",weight="bold")
    return _finish(fig,path)


def render_trade_plan_chart(df,path,card):
    view=df.tail(180).reset_index(drop=True); fig,ax=plt.subplots(figsize=(11,6)); fig.patch.set_facecolor("#0b1220"); ax.set_facecolor("#101827"); ax.grid(alpha=.12); ax.tick_params(colors="#a9b7c6"); _candles(ax,view)
    if card.entry_low is not None:
        ax.axhspan(card.entry_low,card.entry_high,alpha=.18); ax.text(2,(card.entry_low+card.entry_high)/2,"ENTRY ZONE",weight="bold")
    if card.invalidation is not None: ax.axhline(card.invalidation,ls="--",lw=1.4); ax.text(2,card.invalidation,"STOP / INVALIDATION",weight="bold")
    for i,t in enumerate(card.targets,1): ax.axhline(t,ls="--",lw=1.2); ax.text(2,t,f"TP{i}  {t:,.2f}",weight="bold")
    ax.set_title(f"Trade plan — {card.direction.upper()} • confidence {card.confidence}/100 • R:R {card.risk_reward or 0:.2f}",color="white",weight="bold")
    return _finish(fig,path)


def render_analysis_suite(result:dict, output_dir:str|Path, prefix:str="analysis") -> list[Path]:
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True); df=result["data"]
    return [
        render_chart(df,out/f"{prefix}_01_trend_rsi.png",result["zones"],fibs=[]),
        render_structure_chart(df,out/f"{prefix}_02_structure.png",result["zones"],result["pivots"]),
        render_fibonacci_chart(df,out/f"{prefix}_03_fibonacci.png",result["fibs"],result["pivots"]),
        render_elliott_chart(df,out/f"{prefix}_04_elliott.png",result["pivots"],result["elliott"]),
    ]
