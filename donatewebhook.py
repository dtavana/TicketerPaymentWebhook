#!/usr/bin/python3
from flask import Flask, g, session, redirect, request, url_for, jsonify, abort
import psycopg2

app = Flask(__name__)
app.debug = True
app.config['SECRET_KEY'] = "@@:jrv7b))?7QB:RjQH\hB8"
conn = psycopg2.connect("dbname=Ticketer user=postgres password=xw!HLUI&$889 host=localhost")
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS payments(userid bigint, paymentid varchar);")
conn.commit()

@app.route('/api/donatewebhook', methods=['POST'])
def donatewebhook():
    if request.headers['authorization'] != app.config['SECRET_KEY']:
        abort(404)
    data = request.form
    userid = int(data['buyer_id'])
    guildid = int(data['guild_id'])
    txn_id = data['txn_id']
    if data['status'] != "completed":
        cur.execute("SELECT premium FROM servers WHERE userid = %s AND premium = True;", (userid,))
        premiumData = cur.fetchone()
        if premiumData is None:
            cur.execute("UPDATE premium SET credits = credits - 1 WHERE userid = %s;", (userid,))
            conn.commit()
        else:
            cur.execute("UPDATE servers SET premium = False WHERE userid = %s;", (userid,))
            conn.commit()
        cur.execute("INSERT INTO premiumqueue (userid, guildid, added) VALUES (%s, %s, False);", (userid, guildid))
        conn.commit()
    else:
        cur.execute("INSERT INTO payments (userid, paymentid) VALUES (%s, %s);", (userid, txn_id))
        conn.commit()
        try:
            cur.execute("INSERT INTO premium (userid, credits) VALUES (%s, 1);", (userid,))
        except:
            conn.rollback()
            cur.execute("UPDATE premium SET credits = credits + 1 WHERE userid = %s;", (userid,))
        conn.commit()
        cur.execute("INSERT INTO premiumqueue (userid, guildid, added) VALUES (%s, %s, True);", (userid, guildid))
        conn.commit()
    abort(404)

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
    