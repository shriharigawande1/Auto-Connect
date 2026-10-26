
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_file
import sqlite3, os, secrets, io, qrcode
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from math import radians, sin, cos, asin, sqrt

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "autoconnect.db")
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "autoconnect-demo-secret-change-me")

SERVICES = {
    "Electrician": (300, 600), "Plumber": (250, 700), "Mechanic": (400, 1200),
    "Tutor": (300, 800), "Cleaner": (300, 900), "Carpenter": (500, 1500),
    "AC Repair": (500, 1800), "Other": (300, 1000)
}

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
      password TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'user', phone TEXT DEFAULT '',
      location TEXT DEFAULT 'Nagpur', created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS workers(
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE, skill TEXT, experience INTEGER DEFAULT 1,
      skills TEXT DEFAULT '', rate INTEGER DEFAULT 500, location TEXT DEFAULT 'Nagpur',
      available INTEGER DEFAULT 1, verified INTEGER DEFAULT 0, rating REAL DEFAULT 4.5,
      reviews INTEGER DEFAULT 0,
      latitude REAL, longitude REAL
    );
    CREATE TABLE IF NOT EXISTS bookings(
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, worker_id INTEGER, service TEXT,
      problem TEXT, date TEXT, time TEXT, urgency TEXT, amount INTEGER DEFAULT 0,
      status TEXT DEFAULT 'Requested', payment_status TEXT DEFAULT 'Pending',
      emergency INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS reviews(
      id INTEGER PRIMARY KEY AUTOINCREMENT, booking_id INTEGER, user_id INTEGER, worker_id INTEGER,
      rating INTEGER, review TEXT, quality INTEGER DEFAULT 5, behaviour INTEGER DEFAULT 5,
      on_time INTEGER DEFAULT 5, created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS favourites(
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, worker_id INTEGER,
      UNIQUE(user_id, worker_id)
    );
    CREATE TABLE IF NOT EXISTS messages(
      id INTEGER PRIMARY KEY AUTOINCREMENT, booking_id INTEGER, sender_id INTEGER, message TEXT,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS notifications(
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT, is_read INTEGER DEFAULT 0,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    # Backward-compatible location columns for databases created by older versions
    cols = {row[1] for row in con.execute("PRAGMA table_info(workers)").fetchall()}
    if "latitude" not in cols:
        con.execute("ALTER TABLE workers ADD COLUMN latitude REAL")
    if "longitude" not in cols:
        con.execute("ALTER TABLE workers ADD COLUMN longitude REAL")
    
    # Demo accounts
    if not con.execute("SELECT 1 FROM users WHERE email='user@autoconnect.demo'").fetchone():
        con.execute("INSERT INTO users(name,email,password,role,phone,location) VALUES(?,?,?,?,?,?)",
                    ("Mrunmayi Demo","user@autoconnect.demo",generate_password_hash("123456"),"user","9999999999","Nagpur"))
        uid = con.execute("SELECT last_insert_rowid()").fetchone()[0]
        con.execute("INSERT INTO notifications(user_id,message) VALUES(?,?)",(uid,"Welcome to AutoConnect!"))
    if not con.execute("SELECT 1 FROM users WHERE email='rahul@autoconnect.demo'").fetchone():
        con.execute("INSERT INTO users(name,email,password,role,phone,location) VALUES(?,?,?,?,?,?)",
                    ("Rahul Patil","rahul@autoconnect.demo",generate_password_hash("123456"),"worker","8888888888","Nagpur"))
        uid = con.execute("SELECT last_insert_rowid()").fetchone()[0]
        con.execute("""INSERT INTO workers(user_id,skill,experience,skills,rate,location,available,verified,rating,reviews,latitude,longitude)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (uid,"Electrician",5,"Fan Repair, Wiring, Switch Repair, Electrical Installation",500,"Nagpur",1,1,4.8,126,21.1458,79.0882))
    if not con.execute("SELECT 1 FROM users WHERE email='admin@autoconnect.demo'").fetchone():
        con.execute("INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)",
                    ("Admin","admin@autoconnect.demo",generate_password_hash("admin123"),"admin"))
    con.commit(); con.close()

def current_user():
    if not session.get("uid"): return None
    con=db(); u=con.execute("SELECT * FROM users WHERE id=?",(session["uid"],)).fetchone(); con.close()
    return u

def notify(uid, msg):
    con=db(); con.execute("INSERT INTO notifications(user_id,message) VALUES(?,?)",(uid,msg)); con.commit(); con.close()

@app.context_processor
def inject():
    u=current_user()
    count=0
    if u:
        con=db(); count=con.execute("SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0",(u["id"],)).fetchone()[0]; con.close()
    return {"user":u,"notification_count":count}

@app.route("/")
def home():
    return render_template("index.html", services=list(SERVICES.keys()))

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method=="POST":
        name=request.form["name"].strip(); email=request.form["email"].strip().lower()
        pwd=request.form["password"]; role=request.form.get("role","user")
        if role not in ("user","worker"): role="user"
        con=db()
        try:
            con.execute("INSERT INTO users(name,email,password,role,phone,location) VALUES(?,?,?,?,?,?)",
                        (name,email,generate_password_hash(pwd),role,request.form.get("phone",""),request.form.get("location","Nagpur")))
            uid=con.execute("SELECT last_insert_rowid()").fetchone()[0]
            if role=="worker":
                lat = request.form.get("latitude") or None
            lng = request.form.get("longitude") or None
            con.execute("""INSERT INTO workers(user_id,skill,experience,skills,rate,location,available,verified,latitude,longitude)
                               VALUES(?,?,?,?,?,?,?,?,?,?)""",
                            (uid,request.form.get("skill","Other"),int(request.form.get("experience",1) or 1),
                             request.form.get("skills",""),int(request.form.get("rate",500) or 500),
                             request.form.get("location","Nagpur"),1,0,lat,lng))
            con.commit()
        except sqlite3.IntegrityError:
            con.close(); flash("Email already registered.","error"); return redirect(url_for("register"))
        con.close()
        flash("Registration successful. Please login.","success"); return redirect(url_for("login"))
    return render_template("auth.html", mode="register")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        con=db(); u=con.execute("SELECT * FROM users WHERE email=?",(request.form["email"].strip().lower(),)).fetchone(); con.close()
        if u and check_password_hash(u["password"],request.form["password"]):
            session["uid"]=u["id"]
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.","error")
    return render_template("auth.html", mode="login")

@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for("home"))

@app.route("/dashboard")
def dashboard():
    u=current_user()
    if not u: return redirect(url_for("login"))
    if u["role"]=="worker": return redirect(url_for("worker_dashboard"))
    if u["role"]=="admin": return redirect(url_for("admin_dashboard"))
    con=db()
    bookings=con.execute("""SELECT b.*, wu.name worker_name FROM bookings b
                            LEFT JOIN workers w ON w.id=b.worker_id
                            LEFT JOIN users wu ON wu.id=w.user_id
                            WHERE b.user_id=? ORDER BY b.id DESC LIMIT 8""",(u["id"],)).fetchall()
    favs=con.execute("""SELECT w.*,u.name FROM favourites f JOIN workers w ON w.id=f.worker_id
                        JOIN users u ON u.id=w.user_id WHERE f.user_id=?""",(u["id"],)).fetchall()
    con.close()
    return render_template("dashboard.html", bookings=bookings, favs=favs, services=list(SERVICES.keys()))

@app.route("/analyze", methods=["POST"])
def analyze():
    problem=request.form.get("problem","").strip().lower()
    mapping = [
      (["fan","wiring","switch","light","electric","current"],"Electrician","Medium",(300,600)),
      (["leak","tap","pipe","water","toilet"],"Plumber","High",(250,700)),
      (["bike","car","engine","brake","vehicle"],"Mechanic","Medium",(400,1200)),
      (["ac","air conditioner","cooling"],"AC Repair","High",(500,1800)),
      (["clean","dirt","house"],"Cleaner","Low",(300,900)),
      (["table","door","wood","furniture"],"Carpenter","Medium",(500,1500)),
    ]
    service="Other"; urgency="Medium"; cost=SERVICES["Other"]
    for words,s,u,c in mapping:
        if any(x in problem for x in words): service,urgency,cost=s,u,c; break
    if any(x in problem for x in ["smoke","spark","fire","flood","accident","danger"]): urgency="Critical"
    return jsonify({"service":service,"urgency":urgency,"min":cost[0],"max":cost[1],
                    "message":"Demo Smart Analysis: category inferred from your problem description."})

@app.route("/workers")
def workers():
    service=request.args.get("service","")
    location=request.args.get("location","")
    user_lat=request.args.get("lat", type=float)
    user_lng=request.args.get("lng", type=float)
    max_distance=request.args.get("max_distance", type=float)
    con=db()
    q="""SELECT w.*,u.name,u.phone FROM workers w JOIN users u ON u.id=w.user_id
         WHERE w.verified=1"""
    args=[]
    if service:
        q+=" AND (w.skill=? OR w.skills LIKE ?)"; args += [service,"%"+service+"%"]
    if location:
        q+=" AND w.location LIKE ?"; args += ["%"+location+"%"]
    q+=" ORDER BY w.available DESC,w.rating DESC"
    rows=con.execute(q,args).fetchall()
    con.close()

    def distance_km(lat1, lon1, lat2, lon2):
        if None in (lat1, lon1, lat2, lon2): return None
        p1,p2=radians(lat1),radians(lat2)
        dp=radians(lat2-lat1); dl=radians(lon2-lon1)
        a=sin(dp/2)**2+cos(p1)*cos(p2)*sin(dl/2)**2
        return 6371*2*asin(sqrt(a))

    enriched=[]
    for row in rows:
        item=dict(row)
        item["distance_km"]=distance_km(user_lat,user_lng,row["latitude"],row["longitude"])
        if max_distance is None or item["distance_km"] is None or item["distance_km"] <= max_distance:
            enriched.append(item)
    if user_lat is not None and user_lng is not None:
        enriched.sort(key=lambda x: (x["distance_km"] is None, x["distance_km"] if x["distance_km"] is not None else 999999, not bool(x["available"]), -float(x["rating"] or 0)))
    return render_template("workers.html", workers=enriched, service=service, location=location, user_lat=user_lat, user_lng=user_lng, max_distance=max_distance)

@app.route("/worker/<int:wid>")
def worker_profile(wid):
    con=db()
    w=con.execute("SELECT w.*,u.name,u.phone,u.email FROM workers w JOIN users u ON u.id=w.user_id WHERE w.id=?",(wid,)).fetchone()
    con.close()
    if not w: return "Worker not found",404
    return render_template("worker_profile.html", w=w)

@app.route("/booking/new/<int:wid>", methods=["GET","POST"])
def new_booking(wid):
    u=current_user()
    if not u: return redirect(url_for("login"))
    con=db(); w=con.execute("SELECT w.*,u.name FROM workers w JOIN users u ON u.id=w.user_id WHERE w.id=?",(wid,)).fetchone(); con.close()
    if not w: return "Worker not found",404
    if request.method=="POST":
        service=request.form["service"]; problem=request.form["problem"]
        amount=int(request.form.get("amount",w["rate"]) or w["rate"])
        con=db()
        con.execute("""INSERT INTO bookings(user_id,worker_id,service,problem,date,time,urgency,amount,emergency)
                       VALUES(?,?,?,?,?,?,?,?,?)""",
                    (u["id"],wid,service,problem,request.form["date"],request.form["time"],request.form["urgency"],amount,int(request.form.get("emergency",0))))
        bid=con.execute("SELECT last_insert_rowid()").fetchone()[0]; con.commit(); con.close()
        notify(w["user_id"],f"New booking request #{bid} for {service}.")
        flash("Booking request sent to worker.","success"); return redirect(url_for("booking_detail",bid=bid))
    return render_template("booking.html", w=w, services=list(SERVICES.keys()))

@app.route("/booking/<int:bid>")
def booking_detail(bid):
    u=current_user()
    if not u: return redirect(url_for("login"))
    con=db()
    b=con.execute("""SELECT b.*,u.name user_name,u.phone user_phone,w.user_id worker_user_id,
                     wu.name worker_name,w.skill,w.rating FROM bookings b
                     JOIN users u ON u.id=b.user_id JOIN workers w ON w.id=b.worker_id
                     JOIN users wu ON wu.id=w.user_id WHERE b.id=?""",(bid,)).fetchone()
    msgs=con.execute("""SELECT m.*,u.name FROM messages m JOIN users u ON u.id=m.sender_id
                        WHERE m.booking_id=? ORDER BY m.id""",(bid,)).fetchall()
    con.close()
    if not b or (u["role"]=="user" and b["user_id"]!=u["id"]) or (u["role"]=="worker" and b["worker_user_id"]!=u["id"]):
        return "Unauthorized",403
    return render_template("booking_detail.html",b=b,msgs=msgs)

@app.route("/booking/<int:bid>/status", methods=["POST"])
def update_status(bid):
    u=current_user()
    if not u: return redirect(url_for("login"))
    status=request.form["status"]
    allowed=["Accepted","In Progress","Completed","Rejected"]
    if status not in allowed: return "Bad status",400
    con=db()
    b=con.execute("""SELECT b.*,w.user_id worker_user_id FROM bookings b JOIN workers w ON w.id=b.worker_id WHERE b.id=?""",(bid,)).fetchone()
    if not b: con.close(); return "Not found",404
    if u["role"]=="worker" and b["worker_user_id"]!=u["id"]: con.close(); return "Unauthorized",403
    if u["role"]=="user" and b["user_id"]!=u["id"]: con.close(); return "Unauthorized",403
    con.execute("UPDATE bookings SET status=? WHERE id=?",(status,bid)); con.commit(); con.close()
    target=b["user_id"] if u["role"]=="worker" else b["worker_user_id"]
    notify(target,f"Booking #{bid} status changed to {status}.")
    return redirect(url_for("booking_detail",bid=bid))

@app.route("/booking/<int:bid>/pay", methods=["POST"])
def pay(bid):
    u=current_user()
    if not u: return redirect(url_for("login"))
    con=db(); b=con.execute("SELECT * FROM bookings WHERE id=? AND user_id=?",(bid,u["id"])).fetchone()
    if not b: con.close(); return "Unauthorized",403
    con.execute("UPDATE bookings SET payment_status='Paid',status='Paid' WHERE id=?",(bid,)); con.commit(); con.close()
    flash("Demo payment successful.","success"); return redirect(url_for("receipt",bid=bid))

@app.route("/booking/<int:bid>/review", methods=["POST"])
def review(bid):
    u=current_user()
    if not u: return redirect(url_for("login"))
    con=db(); b=con.execute("SELECT * FROM bookings WHERE id=? AND user_id=?",(bid,u["id"])).fetchone()
    if not b: con.close(); return "Unauthorized",403
    con.execute("""INSERT INTO reviews(booking_id,user_id,worker_id,rating,review,quality,behaviour,on_time)
                   VALUES(?,?,?,?,?,?,?,?)""",(bid,u["id"],b["worker_id"],int(request.form["rating"]),request.form.get("review",""),
                   int(request.form.get("quality",5)),int(request.form.get("behaviour",5)),int(request.form.get("on_time",5))))
    con.execute("""UPDATE workers SET rating=(rating*reviews+?)/(reviews+1),reviews=reviews+1 WHERE id=?""",
                (int(request.form["rating"]),b["worker_id"]))
    con.commit(); con.close(); notify(u["id"],"Thanks for your feedback!"); return redirect(url_for("receipt",bid=bid))

@app.route("/message/<int:bid>", methods=["POST"])
def message(bid):
    u=current_user()
    if not u: return redirect(url_for("login"))
    msg=request.form["message"].strip()
    if msg:
        con=db()
        b=con.execute("""SELECT b.*,w.user_id worker_user_id FROM bookings b JOIN workers w ON w.id=b.worker_id WHERE b.id=?""",(bid,)).fetchone()
        if b and u["id"] in (b["user_id"],b["worker_user_id"]):
            con.execute("INSERT INTO messages(booking_id,sender_id,message) VALUES(?,?,?)",(bid,u["id"],msg)); con.commit()
        con.close()
    return redirect(url_for("booking_detail",bid=bid))

@app.route("/favorite/<int:wid>", methods=["POST"])
def favorite(wid):
    u=current_user()
    if not u: return redirect(url_for("login"))
    con=db()
    exists=con.execute("SELECT 1 FROM favourites WHERE user_id=? AND worker_id=?",(u["id"],wid)).fetchone()
    if exists: con.execute("DELETE FROM favourites WHERE user_id=? AND worker_id=?",(u["id"],wid))
    else: con.execute("INSERT OR IGNORE INTO favourites(user_id,worker_id) VALUES(?,?)",(u["id"],wid))
    con.commit(); con.close(); return redirect(request.referrer or url_for("dashboard"))

@app.route("/notifications")
def notifications():
    u=current_user()
    if not u: return redirect(url_for("login"))
    con=db(); rows=con.execute("SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC",(u["id"],)).fetchall()
    con.execute("UPDATE notifications SET is_read=1 WHERE user_id=?",(u["id"],)); con.commit(); con.close()
    return render_template("notifications.html", rows=rows)

@app.route("/worker/dashboard")
def worker_dashboard():
    u=current_user()
    if not u or u["role"]!="worker": return redirect(url_for("login"))
    con=db(); w=con.execute("SELECT * FROM workers WHERE user_id=?",(u["id"],)).fetchone()
    bookings=con.execute("""SELECT b.*,u.name user_name,u.phone user_phone FROM bookings b
                            JOIN users u ON u.id=b.user_id WHERE b.worker_id=? ORDER BY b.id DESC""",(w["id"],)).fetchall()
    con.close()
    return render_template("worker_dashboard.html",w=w,bookings=bookings)

@app.route("/worker/toggle", methods=["POST"])
def worker_toggle():
    u=current_user()
    if not u: return redirect(url_for("login"))
    con=db(); con.execute("UPDATE workers SET available=1-available WHERE user_id=?",(u["id"],)); con.commit(); con.close()
    return redirect(url_for("worker_dashboard"))

@app.route("/admin")
def admin_dashboard():
    u=current_user()
    if not u or u["role"]!="admin": return redirect(url_for("login"))
    con=db()
    stats={
      "users":con.execute("SELECT COUNT(*) FROM users WHERE role='user'").fetchone()[0],
      "workers":con.execute("SELECT COUNT(*) FROM workers").fetchone()[0],
      "pending":con.execute("SELECT COUNT(*) FROM workers WHERE verified=0").fetchone()[0],
      "active":con.execute("SELECT COUNT(*) FROM bookings WHERE status NOT IN ('Completed','Paid','Rejected')").fetchone()[0],
      "completed":con.execute("SELECT COUNT(*) FROM bookings WHERE status IN ('Completed','Paid')").fetchone()[0],
      "payments":con.execute("SELECT COALESCE(SUM(amount),0) FROM bookings WHERE payment_status='Paid'").fetchone()[0]
    }
    pending=con.execute("""SELECT w.*,u.name,u.email FROM workers w JOIN users u ON u.id=w.user_id WHERE w.verified=0""").fetchall()
    bookings=con.execute("""SELECT b.*,u.name user_name,wu.name worker_name FROM bookings b
                            JOIN users u ON u.id=b.user_id JOIN workers w ON w.id=b.worker_id
                            JOIN users wu ON wu.id=w.user_id ORDER BY b.id DESC LIMIT 15""").fetchall()
    con.close(); return render_template("admin.html",stats=stats,pending=pending,bookings=bookings)

@app.route("/admin/verify/<int:wid>", methods=["POST"])
def verify_worker(wid):
    u=current_user()
    if not u or u["role"]!="admin": return "Unauthorized",403
    action=request.form["action"]
    con=db(); w=con.execute("SELECT user_id FROM workers WHERE id=?",(wid,)).fetchone()
    if action=="approve": con.execute("UPDATE workers SET verified=1 WHERE id=?",(wid,))
    else: con.execute("DELETE FROM workers WHERE id=?",(wid,))
    con.commit(); con.close()
    if w and action=="approve": notify(w["user_id"],"Your worker profile has been verified by Admin.")
    return redirect(url_for("admin_dashboard"))

@app.route("/receipt/<int:bid>")
def receipt(bid):
    u=current_user()
    if not u: return redirect(url_for("login"))
    con=db(); b=con.execute("""SELECT b.*,u.name user_name,w.user_id worker_user_id,wu.name worker_name
                              FROM bookings b JOIN users u ON u.id=b.user_id
                              JOIN workers w ON w.id=b.worker_id JOIN users wu ON wu.id=w.user_id
                              WHERE b.id=?""",(bid,)).fetchone()
    r=con.execute("SELECT * FROM reviews WHERE booking_id=? ORDER BY id DESC LIMIT 1",(bid,)).fetchone()
    con.close()
    if not b or u["id"] not in (b["user_id"],b["worker_user_id"]) and u["role"]!="admin": return "Unauthorized",403
    return render_template("receipt.html",b=b,r=r)

@app.route("/qr/<int:bid>")
def qr(bid):
    u=current_user()
    if not u: return "Login required",403
    con=db(); b=con.execute("SELECT * FROM bookings WHERE id=?",(bid,)).fetchone(); con.close()
    if not b: return "Not found",404
    payload=f"AUTOCONNECT|BOOKING:{bid}|AMOUNT:{b['amount']}|DEMO_PAYMENT"
    img=qrcode.make(payload); out=io.BytesIO(); img.save(out,format="PNG"); out.seek(0)
    return send_file(out,mimetype="image/png")

@app.route("/emergency")
def emergency():
    return render_template("emergency.html")

@app.route("/api/emergency")
def api_emergency():
    con=db(); rows=con.execute("""SELECT w.*,u.name FROM workers w JOIN users u ON u.id=w.user_id
                                  WHERE w.verified=1 AND w.available=1 ORDER BY w.rating DESC LIMIT 6""").fetchall()
    con.close()
    return jsonify([dict(r) for r in rows])

if __name__=="__main__":
    init_db()
    app.run(debug=True, host="127.0.0.1", port=5000)
