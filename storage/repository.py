"""Small SQLite repository for reproducible analyses and price alerts."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class Repository:
    def __init__(self,path:str|Path=":memory:"):
        self.conn=sqlite3.connect(str(path)); self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS analyses(id INTEGER PRIMARY KEY, file_hash TEXT, settings TEXT, result TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS alerts(id INTEGER PRIMARY KEY, chat_id INTEGER, symbol TEXT, level REAL, direction TEXT, active INTEGER DEFAULT 1);
        """)
    def save_analysis(self,file_hash:str,settings:dict,result:dict)->int:
        cur=self.conn.execute("INSERT INTO analyses(file_hash,settings,result) VALUES(?,?,?)",(file_hash,json.dumps(settings,sort_keys=True),json.dumps(result,sort_keys=True))); self.conn.commit(); return int(cur.lastrowid)
    def get_analysis(self,id:int)->dict|None:
        row=self.conn.execute("SELECT file_hash,settings,result FROM analyses WHERE id=?",(id,)).fetchone()
        return None if not row else {"file_hash":row[0],"settings":json.loads(row[1]),"result":json.loads(row[2])}
    def add_alert(self,chat_id:int,symbol:str,level:float,direction:str)->int:
        if direction not in {"above","below"}: raise ValueError("direction must be above/below")
        cur=self.conn.execute("INSERT INTO alerts(chat_id,symbol,level,direction) VALUES(?,?,?,?)",(chat_id,symbol.upper(),float(level),direction)); self.conn.commit(); return int(cur.lastrowid)
    def triggered_alerts(self,symbol:str,price:float)->list[dict]:
        rows=self.conn.execute("SELECT id,chat_id,level,direction FROM alerts WHERE symbol=? AND active=1",(symbol.upper(),)).fetchall(); out=[]
        for id,chat,level,direction in rows:
            if (direction=="above" and price>=level) or (direction=="below" and price<=level): out.append({"id":id,"chat_id":chat,"level":level,"direction":direction})
        return out
    def deactivate_alert(self,id:int)->None:
        self.conn.execute("UPDATE alerts SET active=0 WHERE id=?",(id,)); self.conn.commit()
    def close(self): self.conn.close()
