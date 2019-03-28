#!/usr/bin/python3
from flask import Flask, g, session, redirect, request, url_for, jsonify, abort
import psycopg2

app = Flask(__name__)
app.debug = True
app.config['SECRET_KEY'] = "@@:jrv7b))?7QB:RjQH\hB8"
VOTES_FOR_REWARD = 30
conn = psycopg2.connect("dbname=Ticketer user=postgres password=xw!HLUI&$889 host=localhost")
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS payments(userid bigint, paymentid varchar);")
conn.commit()
cur.execute("CREATE TABLE IF NOT EXISTS votes(userid bigint PRIMARY KEY, count smallint);")
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

@app.route('/api/dblvoteswebhook', methods=['POST'])
def voteswebhook():
    if request.headers['Authorization'] != app.config['SECRET_KEY']:
        abort(404)
    data = request.get_json()
    userid = int(data['user'])
    botid = int(data['bot'])
    vote_type = data['type']
    is_weekend = data['isWeekend']
    if botid == 542709669211275296 and vote_type == "upvote":
        if is_weekend:
            vote_add = 2
        else:
            vote_add = 1
        try:
            cur.execute("INSERT INTO votes (userid, count) VALUES (%s, %s);", (userid, vote_add))
            conn.commit()
        except:
            conn.rollback()
            cur.execute("UPDATE votes SET count = count + %s WHERE userid = %s;", (vote_add, userid))
            conn.commit()
        
        cur.execute("SELECT count FROM votes WHERE userid = %s;", (userid,))
        cur_votes = cur.fetchone()
        cur_votes = cur_votes[0]
        if cur_votes >= VOTES_FOR_REWARD:
            try:
                cur.execute("INSERT INTO premium (userid, credits) VALUES (%s, 1);", (userid,))
                conn.commit()
            except:
                conn.rollback()
                cur.execute("UPDATE premium SET credits = credits + 1 WHERE userid = %s;", (userid,))
                conn.commit()
            cur.execute("INSERT INTO votesqueue (userid, cur_votes, receiveCredit) VALUES (%s, %s, True);", (userid, cur_votes))
            conn.commit()
            cur.execute("DELETE FROM votes WHERE userid = %s;", (userid,))
            conn.commit()
        else:
            cur.execute("INSERT INTO votesqueue (userid, cur_votes, receiveCredit) VALUES (%s, %s, False);", (userid, cur_votes))
            conn.commit()
    abort(404)

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
    