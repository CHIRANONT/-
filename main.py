from flask import Flask, render_template, request, redirect, url_for, flash
import threading
import time

app = Flask(__name__)
app.secret_key = 'supersecret'  # สำหรับ flash message

courts = []
players = []
waiting_queue = []
match_history = []

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
        skill_levels = request.form.getlist('skill_level')

        courts.clear()
        players.clear()
        waiting_queue.clear()
        match_history.clear()

        for idx, name in enumerate(court_names):
            courts.append({'name': name, 'current_match': None})

        for idx, name in enumerate(player_names):
            players.append({
                'name': name,
                'status': 'waiting',
                'rest_time': 0,
                'matches_played': 0,
                'skill': skill_levels[idx] if idx < len(skill_levels) else 'N',
                'number': idx + 1
            })

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

    used_names = set()
    for match in waiting_queue:
        used_names.update(match['team_a'] + match['team_b'])

    available_players = [p for p in players if p['status'] == 'waiting' and p['name'] not in used_names]
    return render_template('add_waiting.html', players=available_players)

@app.route('/start_match/<int:court_idx>', methods=['POST'])
def start_match(court_idx):
    if court_idx < len(courts) and waiting_queue:
        match = waiting_queue.pop(0)
        courts[court_idx]['current_match'] = {
            'team_a': match['team_a'],
            'team_b': match['team_b'],
            'scores': []
        }
        for name in match['team_a'] + match['team_b']:
            for player in players:
                if player['name'] == name:
                    player['status'] = 'playing'
                    player['rest_time'] = 0
                    break
    return redirect(url_for('home'))

@app.route('/finish_match/<int:court_idx>', methods=['GET', 'POST'])
def finish_match(court_idx):
    if court_idx >= len(courts):
        return redirect(url_for('home'))

    match = courts[court_idx].get('current_match')
    if not match:
        return redirect(url_for('home'))

    if request.method == 'POST':
        try:
            scores_a1 = int(request.form['score_a1'])
            scores_b1 = int(request.form['score_b1'])
            scores_a2 = int(request.form['score_a2'])
            scores_b2 = int(request.form['score_b2'])
        except (KeyError, ValueError):
            flash("โปรดกรอกคะแนนให้ครบทุกช่อง", "error")
            return redirect(url_for('finish_match', court_idx=court_idx))

        win_a = int(scores_a1 > scores_b1) + int(scores_a2 > scores_b2)
        win_b = int(scores_b1 > scores_a1) + int(scores_b2 > scores_a2)

        result_type = 'draw' if win_a == win_b else 'team_a' if win_a > win_b else 'team_b'

        match_history.append({
            'court': courts[court_idx]['name'],
            'team_a': match['team_a'],
            'team_b': match['team_b'],
            'scores': [(scores_a1, scores_b1), (scores_a2, scores_b2)],
            'winner': match['team_a'] if result_type == 'team_a' else match['team_b'] if result_type == 'team_b' else 'draw'
        })

        for name in match['team_a'] + match['team_b']:
            for player in players:
                if player['name'] == name:
                    player['status'] = 'waiting'
                    player['matches_played'] += 1
                    break

        courts[court_idx]['current_match'] = None
        return redirect(url_for('home'))

    return render_template('record_result.html', match=match, court_name=courts[court_idx]['name'])

@app.route('/suggest_match', methods=['GET', 'POST'])
def suggest_match():
    available_players = [p for p in players if p['status'] == 'waiting']

    if request.method == 'POST':
        selected_names = request.form.getlist('selected_players')
        if len(selected_names) != 4:
            flash("กรุณาเลือกผู้เล่น 4 คน", "error")
            return redirect(url_for('suggest_match'))

        selected = [p for p in available_players if p['name'] in selected_names]
        skill_map = {'BG': 3, 'N-': 2, 'N': 1}
        sorted_players = sorted(selected, key=lambda p: skill_map.get(p['skill'], 1), reverse=True)

        team_a = [sorted_players[0]['name'], sorted_players[3]['name']]
        team_b = [sorted_players[1]['name'], sorted_players[2]['name']]

        waiting_queue.append({'team_a': team_a, 'team_b': team_b})
        return redirect(url_for('home'))

    return render_template('suggest_match.html', players=available_players)

@app.route('/summary')
def summary():
    return render_template('summary.html', players=players, match_history=match_history)

if __name__ == '__main__':
    threading.Thread(target=update_rest_times, daemon=True).start()
    app.run(host="0.0.0.0", port=81)
