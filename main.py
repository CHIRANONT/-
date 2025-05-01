from flask import Flask, render_template, request, redirect, url_for
import threading
import time

app = Flask(__name__)

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
        player_skills = request.form.getlist('player_skill')

        courts.clear()
        players.clear()
        waiting_queue.clear()
        match_history.clear()

        for name in court_names:
            name = name.strip()
            if name:
                courts.append({'name': name, 'current_match': None})

        for i, name in enumerate(player_names):
            name = name.strip()
            if name:
                skill = player_skills[i] if i < len(player_skills) else 'N'
                players.append({
                    'number': len(players) + 1,
                    'name': name,
                    'skill': skill,
                    'status': 'waiting',
                    'rest_time': 0,
                    'matches_played': 0
                })

        return redirect(url_for('home'))

    return render_template('setup.html', courts=courts, players=players)

@app.route('/add_player', methods=['GET', 'POST'])
def add_player():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        skill = request.form.get('skill', 'N')
        if name:
            players.append({
                'number': len(players) + 1,
                'name': name,
                'skill': skill,
                'status': 'waiting',
                'rest_time': 0,
                'matches_played': 0
            })
        return redirect(url_for('home'))
    return render_template('add_player.html')

@app.route('/mark_done/<player_name>', methods=['POST'])
def mark_done(player_name):
    for player in players:
        if player['name'] == player_name:
            player['status'] = 'done'
            break
    return redirect(url_for('home'))

@app.route('/')
def home():
    if not courts or not players:
        return redirect(url_for('setup'))
    return render_template('home.html', courts=courts, players=players, waiting_queue=waiting_queue)

@app.route('/add_waiting', methods=['GET', 'POST'])
def add_waiting():
    if not players:
        return redirect(url_for('setup'))

    if request.method == 'POST':
        team_a = request.form.getlist('team_a')
        team_b = request.form.getlist('team_b')

        if len(team_a) == 2 and len(team_b) == 2:
            waiting_queue.append({'team_a': team_a, 'team_b': team_b})
        return redirect(url_for('home'))

    used_names = set()
    for group in waiting_queue:
        used_names.update(group['team_a'])
        used_names.update(group['team_b'])

    available_players = [
        p for p in players
        if p['status'] == 'waiting' and p['name'] not in used_names
    ]

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
            return "❌ โปรดกรอกคะแนนให้ครบทุกช่อง", 400

        win_a = 0
        win_b = 0

        if scores_a1 > scores_b1:
            win_a += 1
        elif scores_b1 > scores_a1:
            win_b += 1

        if scores_a2 > scores_b2:
            win_a += 1
        elif scores_b2 > scores_a2:
            win_b += 1

        if win_a > win_b:
            winner = 'team_a'
        elif win_b > win_a:
            winner = 'team_b'
        else:
            winner = 'draw'

        match_result = {
            'court': courts[court_idx]['name'],
            'team_a': match['team_a'],
            'team_b': match['team_b'],
            'scores': [(scores_a1, scores_b1), (scores_a2, scores_b2)],
            'winner': match[winner] if winner != 'draw' else 'draw'
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

@app.route('/summary')
def summary():
    return render_template('summary.html', players=players, match_history=match_history)

@app.route('/result_log')
def result_log():
    formatted_results = []
    for m in match_history:
        formatted_results.append({
            'court': m['court'],
            'team_a': m['team_a'],
            'team_b': m['team_b'],
            'game1': {'team_a': m['scores'][0][0], 'team_b': m['scores'][0][1]},
            'game2': {'team_a': m['scores'][1][0], 'team_b': m['scores'][1][1]},
            'result_type': (
                'เสมอ' if m['winner'] == 'draw' else
                ('ทีม A ชนะ' if m['winner'] == m['team_a'] else 'ทีม B ชนะ')
            )
        })
    return render_template('result_log.html', results=formatted_results)

if __name__ == '__main__':
    threading.Thread(target=update_rest_times, daemon=True).start()
    app.run(host="0.0.0.0", port=81)
