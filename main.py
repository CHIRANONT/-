from flask import Flask, render_template, request, redirect, url_for
import threading
import time

app = Flask(__name__)

courts = []
players = []
waiting_queue = []
match_history = []

# ฟังก์ชันอัปเดตเวลาพัก
def update_rest_times():
    while True:
        time.sleep(10)
        for player in players:
            if player['status'] == 'waiting':
                player['rest_time'] += 1

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    global courts, players, waiting_queue, match_history
    if request.method == 'POST':
        court_names = request.form.getlist('court_name')
        player_names = request.form.getlist('player_name')

        courts.clear()
        players.clear()
        waiting_queue.clear()
        match_history.clear()

        for name in court_names:
            courts.append({'name': name, 'current_match': None})
        for name in player_names:
            players.append({'name': name, 'status': 'waiting', 'rest_time': 0, 'matches_played': 0})

        return redirect(url_for('home'))
    return render_template('setup.html')

@app.route('/')
def home():
    if not courts or not players:
        return redirect(url_for('setup'))
    return render_template('home.html', courts=courts, players=players, waiting_queue=waiting_queue)

@app.route('/add_waiting', methods=['GET', 'POST'])
def add_waiting():
    if request.method == 'POST':
        team_a = request.form.getlist('team_a')
        team_b = request.form.getlist('team_b')

        if len(team_a) == 2 and len(team_b) == 2:
            waiting_queue.append({'team_a': team_a, 'team_b': team_b})
        return redirect(url_for('home'))

    available_players = [p for p in players if p['status'] == 'waiting' and all(p['name'] not in (x for group in waiting_queue for x in (group['team_a'] + group['team_b'])))]
    return render_template('add_waiting.html', players=available_players)

@app.route('/start_match/<int:court_idx>', methods=['POST'])
def start_match(court_idx):
    if court_idx < len(courts) and waiting_queue:
        next_match = waiting_queue.pop(0)
        courts[court_idx]['current_match'] = {
            'team_a': next_match['team_a'],
            'team_b': next_match['team_b'],
            'scores': []
        }
        for name in next_match['team_a'] + next_match['team_b']:
            for player in players:
                if player['name'] == name:
                    player['status'] = 'playing'
                    player['rest_time'] = 0
                    break
    return redirect(url_for('home'))

@app.route('/finish_match/<int:court_idx>', methods=['GET', 'POST'])
def finish_match(court_idx):
    if court_idx < len(courts):
        match = courts[court_idx]['current_match']
        if request.method == 'POST':
            scores_a1 = int(request.form['score_a1'])
            scores_b1 = int(request.form['score_b1'])
            scores_a2 = int(request.form['score_a2'])
            scores_b2 = int(request.form['score_b2'])

            # นับจำนวนเกมที่ชนะ
            win_a = 0
            win_b = 0
            if scores_a1 > scores_b1:
                win_a += 1
            else:
                win_b += 1
            if scores_a2 > scores_b2:
                win_a += 1
            else:
                win_b += 1

            winner = 'team_a' if win_a > win_b else 'team_b'

            match_result = {
                'court': courts[court_idx]['name'],
                'team_a': match['team_a'],
                'team_b': match['team_b'],
                'scores': [(scores_a1, scores_b1), (scores_a2, scores_b2)],
                'winner': match[winner]
            }
            match_history.append(match_result)

            for name in match['team_a'] + match['team_b']:
                for player in players:
                    if player['name'] == name:
                        player['status'] = 'waiting'
                        player['matches_played'] += 1
                        break

            courts[court_idx]['current_match'] = None
            return redirect(url_for('home'))

        return render_template('record_result.html', match=match, court_name=courts[court_idx]['name'])
    return redirect(url_for('home'))

@app.route('/summary')
def summary():
    return render_template('summary.html', players=players, match_history=match_history)

if __name__ == '__main__':
    threading.Thread(target=update_rest_times, daemon=True).start()
    app.run(host="0.0.0.0", port=81)
