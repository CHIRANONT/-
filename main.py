from flask import Flask, render_template, redirect, url_for, request
import threading
import time

app = Flask(__name__)

players = []
results = []
court_names = []
match_status = {}
waiting_queue = []

def update_rest_times():
    while True:
        time.sleep(10)
        for player in players:
            if player['status'] == 'พัก':
                player['rest_time'] += 1

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    global players, court_names, results, match_status, waiting_queue
    if request.method == 'POST':
        court_names_raw = request.form.getlist('court_names')
        player_names_raw = request.form.getlist('player_names')

        if not court_names_raw or not player_names_raw:
            return "❌ กรุณากรอกชื่อคอร์ทและผู้เล่น!", 400

        court_names = [name.strip() for name in court_names_raw if name.strip()]
        player_names = [name.strip() for name in player_names_raw if name.strip()]

        if not court_names or not player_names:
            return "❌ อย่าเว้นช่องว่าง!", 400

        overlap = set(court_names) & set(player_names)
        if overlap:
            return f"❌ ชื่อซ้ำกัน: {', '.join(overlap)}", 400

        players = [{"name": name, "status": "พัก", "rest_time": 0, "court": None, "games_played": 0} for name in player_names]
        results = []
        match_status = {court: False for court in court_names}
        waiting_queue = []

        return redirect(url_for('home'))

    return render_template('setup.html')

@app.route('/')
def home():
    if not court_names or not players:
        return redirect(url_for('setup'))

    courts_data = []
    for court in court_names:
        now_playing = [player for player in players if player['court'] == court]
        courts_data.append({
            "court_name": court,
            "now_playing": now_playing,
            "match_in_progress": match_status.get(court, False)
        })

    waiting_players = [player for player in players if player['status'] == 'พัก' and player['court'] is None]

    return render_template('home.html', courts=courts_data, waiting_players=waiting_players, waiting_queue=waiting_queue)

@app.route('/add_waiting', methods=['GET', 'POST'])
def add_waiting():
    if request.method == 'POST':
        selected_players = request.form.getlist('selected_players')
        if len(selected_players) == 4:
            waiting_queue.append(selected_players)
        return redirect(url_for('home'))

    available_players = [player for player in players if player['status'] == 'พัก' and player['court'] is None]
    return render_template('add_waiting.html', players=available_players)

@app.route('/delete_waiting/<int:index>', methods=['POST'])
def delete_waiting(index):
    if 0 <= index < len(waiting_queue):
        del waiting_queue[index]
    return redirect(url_for('home'))

@app.route('/start_match/<court>', methods=['POST'])
def start_match(court):
    match_status[court] = True
    if waiting_queue:
        next_group = waiting_queue.pop(0)
        for name in next_group:
            for player in players:
                if player['name'] == name:
                    player['court'] = court
                    player['status'] = 'เล่น'
                    player['rest_time'] = 0
    return redirect(url_for('home'))

@app.route('/end_match/<court>', methods=['POST'])
def end_match(court):
    playing = [player for player in players if player['court'] == court]
    return render_template('record_result.html', court=court, playing=playing)

@app.route('/record_result', methods=['POST'])
def record_result():
    court = request.form['court']
    winner = request.form['winner']
    loser = request.form['loser']
    score1 = request.form['score1']
    score2 = request.form['score2']

    results.append({
        "court": court,
        "winner": winner,
        "loser": loser,
        "score1": score1,
        "score2": score2
    })

    for player in players:
        if player['court'] == court:
            player['games_played'] += 1
            player['status'] = 'พัก'
            player['court'] = None

    match_status[court] = False

    if waiting_queue:
        next_group = waiting_queue.pop(0)
        for name in next_group:
            for player in players:
                if player['name'] == name:
                    player['court'] = court
                    player['status'] = 'เล่น'
                    player['rest_time'] = 0

    return redirect(url_for('home'))

@app.route('/summary')
def summary():
    return render_template('summary.html', players=players)

@app.route('/result_log')
def result_log():
    return render_template('result_log.html', results=results)

if __name__ == "__main__":
    threading.Thread(target=update_rest_times, daemon=True).start()
    app.run(host="0.0.0.0", port=81)
