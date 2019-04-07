#!/usr/bin/python3
from flask import Flask, g, session, redirect, request, url_for, jsonify, abort
import psycopg2
from flask_openid import OpenID
import re
import urllib
import os
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = "@@:jrv7b))?7QB:RjQH\hB8"
steam_id_re = re.compile('steamcommunity.com/openid/id/(.*?)$')
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
    data = request.get_json()
    try:
        userid = int(data['buyer_id'])
    except:
        abort(404)
        return
    guildid = int(data['guild_id'])
    txn_id = data['txn_id']
    if data['status'] != "completed":
        cur.execute("SELECT key FROM newpremium WHERE paymentid = %s;", (txn_id,))
        key = cur.fetchone()
        key = key[0]
        cur.execute("DELETE FROM newpremium WHERE key = %s;", (key,))
        conn.commit()
        cur.execute("INSERT INTO premiumqueue (userid, guildid, added, key) VALUES (%s, %s, False, %s);", (userid, guildid, key))
        conn.commit()
    else:
        cur.execute("INSERT INTO payments (userid, paymentid) VALUES (%s, %s);", (userid, txn_id))
        conn.commit()
        key = str(uuid.uuid4())
        key = key.replace('-', '')
        key = key[:10]
        cur.execute("INSERT INTO newpremium(userid, key, paymentid) VALUES(%s, %s, %s);", (userid, key, txn_id))
        conn.commit()
        cur.execute("INSERT INTO premiumqueue (userid, guildid, added, key) VALUES (%s, %s, True, %s);", (userid, guildid, key))
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
            key = str(uuid.uuid4())
            key = key.replace('-', '')
            key = key[:10]
            cur.execute("INSERT INTO newpremium(userid, key, paymentid) VALUES(%s, %s, 0);", (userid, key))
            conn.commit()
            cur.execute("INSERT INTO votesqueue (userid, cur_votes, receiveCredit, key) VALUES (%s, %s, True, %s);", (userid, cur_votes, key))
            conn.commit()
            cur.execute("DELETE FROM votes WHERE userid = %s;", (userid,))
            conn.commit()
        else:
            cur.execute("INSERT INTO votesqueue (userid, cur_votes, receiveCredit, key) VALUES (%s, %s, False, 0);", (userid, cur_votes))
            conn.commit()
    abort(404)

@app.route('/api/steamlogin')
def steamlogin():
    key = request.args.get('key')
    if key is None:
        return "No key was detected"
    session['authkey'] = key
    cur.execute("SELECT * FROM validkeys WHERE key = %s;", (key,))
    data = cur.fetchone()
    if not data:
        return "Invalid key entered."
    steam_openid_url = 'https://steamcommunity.com/openid/login'
    params = {
        'openid.ns': "http://specs.openid.net/auth/2.0",
        'openid.identity': "http://specs.openid.net/auth/2.0/identifier_select",
        'openid.claimed_id': "http://specs.openid.net/auth/2.0/identifier_select",
        'openid.mode': 'checkid_setup',
        'openid.return_to': 'http://ticketerbot.xyz:5000/api/steamcallback',
        'openid.realm': 'http://ticketerbot.xyz:5000/' # not sure what it is
    }
    param_string = urllib.parse.urlencode(params)
    auth_url = steam_openid_url + "?" + param_string
    return redirect(auth_url)

@app.route('/api/steamcallback')
def handle():
    match = steam_id_re.search(request.args.get('openid.claimed_id'))
    steamid = match.group(1)
    cur.execute("UPDATE steamauthqueue SET isDone = True, steamid = %s WHERE key = %s;", (steamid, session['authkey']))
    conn.commit()
    cur.execute("DELETE FROM validkeys WHERE key = %s;", (session['authkey'],))
    conn.commit()
    return "Thank you for authenticating! You may return to your ticket."

if __name__ == "__main__":
    app.run(host='0.0.0.0')
    