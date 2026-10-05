from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import time

app = FastAPI()
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ExprRequest(BaseModel):
    expression: str

# sqlite init
def init_db():
    conn = sqlite3.connect("calc.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS calculation_history
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 expression TEXT NOT NULL,
                 result TEXT NOT NULL,
                 created_at TEXT NOT NULL)''')
    conn.commit()
    conn.close()

def insert_history(expr:str, res:str):
    conn = sqlite3.connect("calc.db")
    c = conn.cursor()
    t = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    c.execute("INSERT INTO calculation_history (expression,result,created_at) VALUES (?,?,?)",(expr,res,t))
    conn.commit()
    conn.close()

def get_all_history():
    conn = sqlite3.connect("calc.db")
    c = conn.cursor()
    rows = c.execute("SELECT id,expression,result,created_at FROM calculation_history ORDER BY id DESC").fetchall()
    conn.close()
    return rows

def delete_by_id(record_id:int):
    conn = sqlite3.connect("calc.db")
    c = conn.cursor()
    c.execute("DELETE FROM calculation_history WHERE id=?",(record_id,))
    conn.commit()
    conn.close()

def delete_all():
    conn = sqlite3.connect("calc.db")
    c = conn.cursor()
    c.execute("DELETE FROM calculation_history")
    conn.commit()
    conn.close()

# ===== Shunting-yard 表达式解析核心，禁止eval =====
def tokenize(s:str):
    tokens = []
    i=0
    n=len(s)
    while i<n:
        ch = s[i]
        if ch.isspace():
            i+=1
            continue
        if ch in "0123456789.":
            j=i
            while j<n and s[j] in "0123456789.":
                j+=1
            tokens.append(s[i:j])
            i=j
        elif ch in "+-*/()":
            tokens.append(ch)
            i+=1
        else:
            raise SyntaxError("invalid char")
    # 处理一元负号
    new_tokens=[]
    for idx,t in enumerate(tokens):
        if t == '-':
            if idx ==0 or tokens[idx-1] in "(+-*/":
                new_tokens.append("u-")
            else:
                new_tokens.append("-")
        else:
            new_tokens.append(t)
    return new_tokens

op_prio = {"+":1,"-":1,"*":2,"/":2,"u-":3}
op_assoc = {"+":"left","-":"left","*":"left","/":"left","u-":"right"}

def shunting_yard(tokens):
    out = []
    stack = []
    for tk in tokens:
        if tk.replace(".","").isdigit():
            out.append(tk)
        elif tk == "(":
            stack.append(tk)
        elif tk == ")":
            while stack and stack[-1]!="(":
                out.append(stack.pop())
            if not stack:
                raise SyntaxError("mismatched parenthesis")
            stack.pop()
        else:
            while stack and stack[-1]!="(":
                top = stack[-1]
                if (op_assoc[tk]=="left" and op_prio[tk] <= op_prio[top]) or (op_assoc[tk]=="right" and op_prio[tk]<op_prio[top]):
                    out.append(stack.pop())
                else:
                    break
            stack.append(tk)
    while stack:
        top = stack.pop()
        if top == "(":
            raise SyntaxError("mismatched parenthesis")
        out.append(top)
    return out

def calc_rpn(rpn):
    st=[]
    for tk in rpn:
        if tk.replace(".","").isdigit():
            st.append(float(tk))
        elif tk == "u-":
            a = st.pop()
            st.append(-a)
        else:
            b = st.pop()
            a = st.pop()
            if tk == "+":
                res = a+b
            elif tk == "-":
                res = a-b
            elif tk == "*":
                res = a*b
            elif tk == "/":
                if abs(b)<1e-12:
                    raise ZeroDivisionError()
                res = a/b
            else:
                raise SyntaxError()
            st.append(res)
    if len(st)!=1:
        raise SyntaxError()
    return st[0]

def evaluate_expression(expr:str):
    tokens = tokenize(expr)
    rpn = shunting_yard(tokens)
    val = calc_rpn(rpn)
    return val

# API
@app.post("/api/calculate")
async def calc(req:ExprRequest):
    try:
        val = evaluate_expression(req.expression)
        insert_history(req.expression, str(val))
        return {"success":True, "expression":req.expression, "result":val}
    except ZeroDivisionError:
        return {"success":False, "message":"Division by zero"}
    except SyntaxError:
        return {"success":False, "message":"Invalid mathematical expression"}
    except Exception as e:
        return {"success":False, "message":"Expression parse error"}

@app.get("/api/history")
async def get_history():
    rows = get_all_history()
    data = []
    for r in rows:
        data.append({"id":r[0],"expression":r[1],"result":r[2],"created_at":r[3]})
    return {"success":True, "data":data}

@app.delete("/api/history/{record_id}")
async def del_record(record_id:int):
    delete_by_id(record_id)
    return {"success":True}

@app.delete("/api/history")
async def clear_all():
    delete_all()
    return {"success":True}

init_db()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app",host="0.0.0.0",port=8000,reload=True)
