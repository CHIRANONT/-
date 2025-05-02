from flask import Flask, render_template, request, redirect, url_for
import threading
import time
from itertools import combinations

app = Flask(__name__)

courts = []
players = []
waiting_queue = []
match_history = []
player_counter = 1

skill_map = {'BG': 5, 'N-': 3, 'N': 1}

def update_rest_times():
    while True:
        time.sleep(10)
        for player in players:
            if player['status'] == 'waiting':
                player['rest_time'] += 10

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    global courts, players, waiting_queue, match_history, player_counter
    if request.method == 'POST':
        court_names = request.form.getlist('court_name')
        player_names = request.form.getlist('player_name')
        player_skills = request.form.getlist('player_skill')

        courts.clear()
        players.clear()
        waiting_queue.clear()
        match_history.clear()
        player_counter = 1

        for name in court_names:
            courts.append({'name': name, 'current_match': None})

        for name, skill in zip(player_names, player_skills):
            players.append({
                'name': name,
                'skill': skill,
                'status': 'waiting',
                'rest_time': 0,
                'matches_played': 0,
                'number': player_counter
            })
            player_counter += 1

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
    for group in waiting_queue:
        used_names.update(group['team_a'])
        used_names.update(group['team_b'])

    available_players = [p for p in players if p['status'] == 'waiting' and p['name'] not in used_names]
    return render_template('add_waiting.html', players=available_players)

@app.route('/delete_queue/<int:index>', methods=['POST'])
def delete_queue(index):
    if 0 <= index < len(waiting_queue):
        del waiting_queue[index]
    return redirect(url_for('home'))

@app.route('/add_player', methods=['GET', 'POST'])
def add_player():
    global player_counter
    if request.method == 'POST':
        name = request.form['name']
        skill = request.form['skill']
        players.append({
            'name': name,
            'skill': skill,
            'status': 'waiting',
            'rest_time': 0,
            'matches_played': 0,
            'number': player_counter
        })
        player_counter += 1
        return redirect(url_for('home'))
    return render_template('add_player.html')

@app.route('/mark_done/<player_name>', methods=['POST'])
def mark_done(player_name):
    for p in players:
        if p['name'] == player_name:
            p['status'] = 'done'
            break
    return redirect(url_for('home'))

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

        win_a = (scores_a1 > scores_b1) + (scores_a2 > scores_b2)
        win_b = (scores_b1 > scores_a1) + (scores_b2 > scores_a2)

        if win_a == win_b:
            result_type = 'เสมอ'
        elif win_a > win_b:
            result_type = 'ทีม A ชนะ'
        else:
            result_type = 'ทีม B ชนะ'

        match_result = {
            'court': courts[court_idx]['name'],
            'team_a': match['team_a'],
            'team_b': match['team_b'],
            'game1': {'team_a': scores_a1, 'team_b': scores_b1},
            'game2': {'team_a': scores_a2, 'team_b': scores_b2},
            'result_type': result_type
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
    return render_template('result_log.html', results=match_history)

@app.route('/suggest_match', methods=['GET', 'POST'])
def suggest_match():
    available = [p for p in players if p['status'] == 'waiting']
    best = None
    best_diff = float('inf')
    for comb in combinations(available, 4):
        for team_a in combinations(comb, 2):
            team_b = [p for p in comb if p not in team_a]
            score_a = sum(skill_map[p['skill']] for p in team_a)
            score_b = sum(skill_map[p['skill']] for p in team_b)
            diff = abs(score_a - score_b)
            if diff < best_diff:
                best = {
                    'team_a': [p['name'] for p in team_a],
                    'team_b': [p['name'] for p in team_b],
                    'diff': diff
                }
                best_diff = diff

    if request.method == 'POST' and best:
        waiting_queue.append({'team_a': best['team_a'], 'team_b': best['team_b']})
        return redirect(url_for('home'))

    return render_template('suggest_match.html', match=best)

@app.route('/auto_pair_select', methods=['GET', 'POST'])
def auto_pair_select():
    if request.method == 'POST':
        selected = request.form.getlist('selected_players')
        selected_players = [p for p in players if p['name'] in selected and p['status'] == 'waiting']

        if len(selected_players) != 4:
            return "❌ กรุณาเลือกผู้เล่น 4 คน", 400

        best_group = None
        best_diff = float('inf')
        for team_a in combinations(selected_players, 2):
            team_b = [p for p in selected_players if p not in team_a]
            score_a = sum(skill_map[p['skill']] for p in team_a)
            score_b = sum(skill_map[p['skill']] for p in team_b)
            diff = abs(score_a - score_b)
            if diff < best_diff:
                best_diff = diff
                best_group = (list(team_a), list(team_b))

        if 'confirm' in request.form:
            waiting_queue.append({
                'team_a': [p['name'] for p in best_group[0]],
                'team_b': [p['name'] for p in best_group[1]]
            })
            return redirect(url_for('home'))

        return render_template('auto_pair_result.html', team_a=best_group[0], team_b=best_group[1], diff=best_diff)

    available_players = [p for p in players if p['status'] == 'waiting']
    return render_template('auto_pair_select.html', players=available_players)

if __name__ == '__main__':
    threading.Thread(target=update_rest_times, daemon=True).start()
    app.run(host="0.0.0.0", port=81)
