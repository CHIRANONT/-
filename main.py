from flask import Flask, render_template, redirect, url_for, request, jsonify
import threading
import time

app = Flask(__name__)

players = [
    {"name": "นนท์", "status": "พัก", "rest_time": 0},
    {"name": "ปิงปอง", "status": "เล่น", "rest_time": 0},
    {"name": "เฟิร์ส", "status": "พัก", "rest_time": 0},
    {"name": "เจมส์", "status": "เล่น", "rest_time": 0}
]

court_names = []  # เอาไว้เก็บชื่อคอร์ทที่กรอก

# ฟังก์ชันอัปเดตเวลาพัก
def update_rest_times():
    while True:
        time.sleep(10)
        for player in players:
            if player['status'] == 'พัก':
                player['rest_time'] += 1

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    global court_names
    if request.method == 'POST':
        court_names = request.form.getlist('court_name')
        return redirect(url_for('home'))
    return render_template('setup.html')

@app.route('/')
def home():
    if not court_names:
        return redirect(url_for('setup'))  # ถ้ายังไม่มีชื่อคอร์ท บังคับไปตั้งก่อน
    return render_template('home.html', players=players)

@app.route('/players')
def get_players():
    return jsonify(players)

@app.route('/toggle/<name>', methods=['POST'])
def toggle_status(name):
    for player in players:
        if player['name'] == name:
            if player['status'] == 'เล่น':
                player['status'] = 'พัก'
                player['rest_time'] = 0
            else:
                player['status'] = 'เล่น'
            break
    return redirect(url_for('home'))

@app.route('/add', methods=['POST'])
def add_player():
    name = request.form['name']
    players.append({"name": name, "status": "พัก", "rest_time": 0})
    return redirect(url_for('home'))

@app.route('/delete/<name>', methods=['POST'])
def delete_player(name):
    global players
    players = [player for player in players if player['name'] != name]
    return redirect(url_for('home'))

@app.route('/arrange', methods=['POST'])
def arrange_court():
    players_per_court = 4  # คนต่อคอร์ท

    waiting_players = [player for player in players if player['status'] == 'พัก']
    waiting_players.sort(key=lambda x: x['rest_time'], reverse=True)

    total_needed = len(court_names) * players_per_court
    selected_players = waiting_players[:total_needed]

    # เปลี่ยนสถานะคนที่ได้ลงสนามเป็นเล่น
    for player in selected_players:
        player['status'] = 'เล่น'
        player['rest_time'] = 0

    courts = []
    for i in range(0, len(selected_players), players_per_court):
        court_players = selected_players[i:i+players_per_court]
        courts.append(court_players)

    return render_template('arrange.html', courts=courts, court_names=court_names)

if __name__ == "__main__":
    threading.Thread(target=update_rest_times, daemon=True).start()
    app.run(host="0.0.0.0", port=81)
