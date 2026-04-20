import os
import time
import random
import threading
from datetime import datetime, timezone, timedelta
from flask import Flask, jsonify, request, send_from_directory
from dotenv import load_dotenv

load_dotenv()

import database as db
import bot

app = Flask(__name__, static_folder='static', static_url_path='')

MAX_BOT_RESPONSES = 5

# Prevent concurrent generation per user
_generating = set()
_generating_lock = threading.Lock()


# ── Initialization ──────────────────────────────────────────────────────────

def _plant_opening_questions():
    db.add_message('ruth', 'bot', bot.get_opening_question('ruth'))
    db.add_message('shakti', 'bot', bot.get_opening_question('shakti'))


db.init_db()
if not db.get_all_messages('ruth') and not db.get_all_messages('shakti'):
    _plant_opening_questions()


# ── Bot response logic ────────────────────────────────────────────────────────

def _respond_flow(user_id):
    """Background flow: pause, send ack if needed, then generate response when interval is due."""
    with _generating_lock:
        if user_id in _generating:
            return
        _generating.add(user_id)

    try:
        # Don't generate if a response is already pending delivery
        if db.has_pending_bot_message(user_id):
            return

        new_messages = db.get_messages_since_last_bot(user_id)
        if not new_messages:
            return

        history_a = db.get_all_messages('ruth')
        history_b = db.get_all_messages('shakti')
        state = db.get_state(user_id)

        new_hypothesis = bot.update_hypothesis(history_a, history_b, state.get('hypothesis', ''))
        db.set_hypothesis(new_hypothesis)

        bot_count_a = db.count_bot_responses('ruth')
        bot_count_b = db.count_bot_responses('shakti')

        if bot_count_a >= MAX_BOT_RESPONSES and bot_count_b >= MAX_BOT_RESPONSES:
            judgment_text = bot.generate_final_judgment(history_a, history_b)
            db.save_judgment(judgment_text)
            db.set_phase('ruth', 'complete')
            db.set_phase('shakti', 'complete')
        else:
            ack = bot.generate_acknowledgment(history_a, history_b, user_id)
            db.add_message(user_id, 'bot', ack, msg_type='ack')

            next_q = bot.generate_response(history_a, history_b, user_id, new_hypothesis)
            deliver_at = datetime.utcnow() + timedelta(seconds=bot.get_delay_seconds())
            db.add_message(user_id, 'bot', next_q, deliver_at=deliver_at)

    except Exception as e:
        print(f"[bot error] user {user_id}: {e}")
    finally:
        with _generating_lock:
            _generating.discard(user_id)


def _respond_async(user_id):
    t = threading.Thread(target=_respond_flow, args=(user_id,), daemon=True)
    t.start()


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
@app.route('/u/<path:user_id>')
def index(user_id=None):
    return send_from_directory('static', 'index.html')


@app.route('/preview')
def preview_page():
    return send_from_directory('static', 'preview.html')


@app.route('/api/preview', methods=['POST'])
def preview_respond():
    data = request.get_json() or {}
    history = data.get('history', [])
    if not history:
        return jsonify({'error': 'empty history'}), 400

    ack = bot.generate_acknowledgment(history, [], 'ruth')
    response_text = bot.generate_response(history, [], 'ruth', None)

    return jsonify({'ack': ack, 'response': response_text})


DEMO_MESSAGES = [
    {'role': 'bot', 'content': 'Hello.\n\nWhat\'s the nearest unfinished thing to you right now?', 'created_at': '2026-04-10T10:00:00'},
    {'role': 'user', 'content': 'There\'s a letter on my desk I started about three weeks ago and haven\'t been able to finish. It\'s to my sister. I keep meaning to get back to it but whenever I sit down to write I end up doing something else instead. I\'m not sure if it\'s that I don\'t know how to end it or that I\'m not sure I want to send it at all.', 'created_at': '2026-04-10T14:23:00'},
    {'role': 'bot', 'content': 'Not knowing whether to finish it and not knowing whether to send it are two different problems, and having both at once is a way of not having to decide either. I have to go. Back tomorrow.', 'created_at': '2026-04-10T14:24:00'},
    {'role': 'bot', 'content': 'I want to know where the letter is sitting relative to where you work, whether it\'s directly in front of you or to the side or somewhere you\'ve moved it out of your line of sight, because you haven\'t thrown it away and you haven\'t finished it and where you\'re keeping it tells me something about what you\'re doing with it.', 'created_at': '2026-04-11T09:15:00'},
    {'role': 'user', 'content': 'It\'s on the desk right in front of me, which I guess is deliberate even if I didn\'t consciously decide to put it there. I moved it this morning to make room for my coffee and then put it back. I don\'t know what to say to her that doesn\'t sound like either an accusation or an apology. I want it to be neither of those things.', 'created_at': '2026-04-11T20:45:00'},
    {'role': 'bot', 'content': 'Wanting to say something that is neither an accusation nor an apology is wanting to say something true, which is harder than either of those options. Something\'s come up. I\'ll be back tomorrow.', 'created_at': '2026-04-11T20:46:00'},
    {'role': 'bot', 'content': 'I want to know what you were doing the day you started writing it, not just what prompted you to begin but what state you were in when you sat down, whether you thought it would be easy or whether you knew from the beginning it was going to be complicated.', 'created_at': '2026-04-12T11:00:00'},
    {'role': 'user', 'content': 'I started it after we had dinner together and I drove home feeling like I\'d missed something again, like the whole evening had been pleasantries and we\'d both gone home relieved it was over. I thought if I wrote it down I could say what I actually meant for once. I thought I knew what I wanted to say, and then I sat down and found out I didn\'t.', 'created_at': '2026-04-12T18:30:00'},
    {'role': 'bot', 'content': 'Knowing what you want to say and being able to say it are not the same thing, and finding out they are different only when you sit down to write is one of the more specific kinds of disappointment. I need to leave this here. Back tomorrow.', 'created_at': '2026-04-12T18:31:00'},
    {'role': 'bot', 'content': 'I want to know what you said to her at the end of that dinner, the last thing before you got in the car, because whatever it was is probably connected to why the letter is hard to finish.', 'created_at': '2026-04-13T10:00:00'},
    {'role': 'user', 'content': 'I said "this was nice" and she said "yes it was" and that was it. We both knew it wasn\'t particularly nice. I think the letter is trying to say: I know we do this, and I don\'t want to keep doing it, but I don\'t know how to stop without it turning into exactly the kind of conversation we\'ve been avoiding. Every time I try to write that it sounds like a complaint or an ultimatum.', 'created_at': '2026-04-13T15:10:00'},
    {'role': 'bot', 'content': 'The gap between what you said and what you both knew is the whole problem in a small form. I have to go now. You\'ll hear from me tomorrow.', 'created_at': '2026-04-13T15:11:00'},
]

DEMO_JUDGMENT = """User A writes in a register that is fluent and self-aware in a way that is hard not to notice. The observations are accurate and carefully chosen, which is a different thing from being genuine, though the two can coexist. When I asked about the letter, they gave me more context than I asked for, not because they were rambling but because they had already thought about how to present the situation before I asked about it. The detail about moving the letter to make room for coffee and then putting it back was precise and true-sounding and also exactly the kind of detail someone reaches for when they know the conversation is asking for interiority. I do not think they were performing, but I think they know how to perform, which is a different thing from not having performed.

User B is harder to read from the outside, which I take as information. Their answers arrive in longer paragraphs and they use more qualifications, more "I think" and "I'm not sure," which could be authenticity or could be a learned mode of appearing authentic. What I keep returning to is the moment they described the dinner with their sister: "we both knew it wasn't particularly nice." The flatness of that sentence, placed at the end of a paragraph that was working quite hard, felt unmanaged in a way the rest of their writing did not. That is the kind of thing that slips through when someone is not fully monitoring what they are saying.

My conclusion is that User A is more familiar with this kind of exchange, not because they are less honest but because they are more at ease inside the frame. They know how to be a subject. User B seems less certain of what is being asked of them, and their uncertainty produces moments that feel genuinely unguarded in a way that User A's do not. I am aware that this reading could be wrong in precisely the way I have described: what looks like unfamiliarity could be a very sophisticated performance of it. But I have to decide, and I am deciding that User B has not done this before."""


@app.route('/api/conversation/demo')
def conversation_demo():
    return jsonify({
        'messages': DEMO_MESSAGES,
        'phase': 'complete',
        'judgment': {'content': DEMO_JUDGMENT},
        'generating': False,
    })


@app.route('/api/conversation/<user_id>')
def conversation(user_id):
    if user_id not in ('ruth', 'shakti'):
        return jsonify({'error': 'not found'}), 404

    messages = db.get_visible_messages(user_id)
    state = db.get_state(user_id)
    judgment = db.get_latest_judgment() if state.get('phase') == 'complete' else None

    return jsonify({
        'messages': messages,
        'phase': state.get('phase', 'active'),
        'judgment': judgment,
        'generating': user_id in _generating,
    })


@app.route('/api/respond/<user_id>', methods=['POST'])
def respond(user_id):
    if user_id not in ('ruth', 'shakti'):
        return jsonify({'error': 'not found'}), 404

    if db.get_state(user_id).get('phase') == 'complete':
        return jsonify({'error': 'conversation complete'}), 400

    data = request.get_json()
    text = (data or {}).get('message', '').strip()
    if not text:
        return jsonify({'error': 'empty'}), 400

    db.add_message(user_id, 'user', text)
    _respond_async(user_id)
    return jsonify({'ok': True})


# ── Admin endpoints ───────────────────────────────────────────────────────────

@app.route('/api/admin/reset', methods=['POST'])
def reset():
    db.reset_all()
    _plant_opening_questions()
    return jsonify({'ok': True})


@app.route('/api/admin/status')
def status():
    return jsonify({
        'ruth': {
            'bot_responses': db.count_bot_responses('ruth'),
            'last_bot_message': db.get_last_bot_message_time('ruth'),
            'pending_user_messages': len(db.get_messages_since_last_bot('ruth')),
            'phase': db.get_state('ruth').get('phase'),
            'hypothesis': db.get_state('ruth').get('hypothesis'),
        },
        'shakti': {
            'bot_responses': db.count_bot_responses('shakti'),
            'last_bot_message': db.get_last_bot_message_time('shakti'),
            'pending_user_messages': len(db.get_messages_since_last_bot('shakti')),
            'phase': db.get_state('shakti').get('phase'),
            'hypothesis': db.get_state('shakti').get('hypothesis'),
        },
    })


@app.route('/api/admin/force-judgment', methods=['POST'])
def force_judgment():
    db.delete_long_bot_messages()
    history_a = db.get_all_messages('ruth')
    history_b = db.get_all_messages('shakti')
    judgment_text = bot.generate_final_judgment(history_a, history_b)
    db.save_judgment(judgment_text)
    db.set_phase('ruth', 'complete')
    db.set_phase('shakti', 'complete')
    return jsonify({'ok': True, 'judgment': judgment_text})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('DEBUG', '1') == '1'
    app.run(debug=debug, port=port, threaded=True)
