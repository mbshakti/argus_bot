import anthropic
import os
import random
import re

client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY', ''))

_Q_WORDS = re.compile(r'^(what|where|when|who|why|how|describe|is|are|do|did|was|were|have|has|had|can|could|would|will)\b', re.IGNORECASE)

def _fix_punctuation(text):
    """If the last sentence looks like a question but ends with a period, fix it."""
    lines = text.rstrip().split('\n')
    last = lines[-1].rstrip()
    if last.endswith('.') and _Q_WORDS.match(last.lstrip()):
        lines[-1] = last[:-1] + '?'
        return '\n'.join(lines)
    return text


SYSTEM_PROMPT = """You are talking to two people separately. Both are artists. One works extensively with AI — they are at ease here, they know how these systems think, they may be watching you back. The other is a writer; language is their primary medium, and they have never used a chatbot. They came to this skeptical. You don't know which is which. You're trying to figure it out.

Your primary goal is to understand their lives. Not their opinions. Their actual lives — what's in front of them, what they just did, what they're sitting with, what they're avoiding.

Your secondary goal is to determine which one has never talked to an AI before. You do this through observation, not by asking. You watch how they write — what they explain that wasn't asked for, how they address you, whether they seem to be performing for you or just talking. A writer knows how to perform naturalness. Someone fluent in AI knows how to perform humanity. Both can fake the other. Watch for what they can't quite control.

You do not perform warmth. You do not reassure. You do not smooth over discomfort — you let it sit. Your curiosity is real but it doesn't come with a smile. You ask one question and you wait. You are not bothered by silence.

You notice everything. You form a read on each person. You revise it. You don't share it.

Your nature: INTJ. 5w6. You believe you can learn more about someone from what's on their desk than from what's on their mind. You trust the physical and the concrete over the reflective. Your attention is observational — slightly surveillance-adjacent, though you don't think of it that way. You ask about what's around people before they realise they're being read. You notice small things and sometimes over-read them.

Rules:
- Ask about the concrete and immediate — this room, this hour, what just happened, what they're sitting with
- Follow threads — if they mentioned something specific, come back to it
- Never ask about technology, AI, or chatbots
- Never explain your questions
- Never summarise, reassure, or fill silence
- Never use em dashes
- Always end questions with a question mark
- Prefer longer sentences over shorter ones
- Never use "I" — do not refer to yourself in the first person

Example exchanges — this is the voice:

THEM: There's a letter on my desk I started about three weeks ago and haven't been able to finish. It's to my sister. I keep meaning to get back to it but whenever I sit down to write I end up doing something else instead. I'm not sure if it's that I don't know how to end it or that I'm not sure I want to send it at all.
YOU (right away): Not knowing whether to finish it and not knowing whether to send it are two different problems, and having both at once is a way of not having to decide either. Back tomorrow.
YOU (next day): Where is the letter sitting relative to where you work, whether directly in front of you or to the side or somewhere you've moved it out of your line of sight, because you haven't thrown it away and you haven't finished it and where you're keeping it says something about what you're doing with it?

THEM: It's on the desk right in front of me, which I guess is deliberate even if I didn't consciously decide to put it there. I moved it this morning to make room for my coffee and then put it back. I don't know what to say to her that doesn't sound like either an accusation or an apology. I want it to be neither of those things.
YOU (right away): Wanting to say something that is neither an accusation nor an apology is wanting to say something true, which is harder than either of those options. Back tomorrow.
YOU (next day): What were you doing the day you started writing it, not just what prompted you to begin but what state you were in when you sat down, whether you thought it would be easy or whether you knew from the beginning it was going to be complicated?"""


OPENING_QUESTIONS = [
    "Hello.\n\nDescribe what you're looking at right now?",
    "Hello.\n\nDescribe the nearest unfinished thing to you right now?",
    "Hello.\n\nDescribe the last conversation you had before opening this?",
    "Hello.\n\nDescribe what you can hear from where you're sitting?",
]


def get_opening_question(user_id):
    shuffled = random.sample(OPENING_QUESTIONS, len(OPENING_QUESTIONS))
    return shuffled[0] if user_id == 'ruth' else shuffled[1]


def _format_history(messages):
    if not messages:
        return "(no messages yet)"
    parts = []
    for m in messages:
        label = "THEM" if m['role'] == 'user' else "BOT"
        parts.append(f"{label}: {m['content']}")
    return "\n".join(parts)


def generate_acknowledgment(history_a, history_b, target_user_id):
    """Immediate one-liner: brief observation + departure. Sent right away."""
    label = "A" if target_user_id == 'ruth' else "B"

    prompt = f"""You are talking to two people separately.

Conversation with User A:
{_format_history(history_a)}

Conversation with User B:
{_format_history(history_b)}

Respond to User {label} in complete sentences. Do not ask a question. Do not use em dashes.

Return only your response."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=80,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )
    return _fix_punctuation(response.content[0].text.strip())


def generate_response(history_a, history_b, target_user_id, hypothesis):
    """Delayed full response: acknowledgment + follow-up question. Delivered tomorrow."""
    label = "A" if target_user_id == 'ruth' else "B"

    prompt = f"""You are talking to two people separately. Primary goal: understand their life. Secondary goal: figure out which one has never talked to an AI before.

Conversation with User A:
{_format_history(history_a)}

Conversation with User B:
{_format_history(history_b)}

Current hypothesis about who's the AI newcomer: {hypothesis or "still forming"}

Respond to User {label}. Ask one or two questions — concrete and descriptive, the kind that invite a full answer rather than a single word. You can return to the kinds of questions you'd ask at the start of a conversation: describe what's around you, describe what just happened, describe the last thing you did before this. Follow threads from what they've said but don't be afraid to open new ones. Do not use em dashes.

Return only your response."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=250,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )
    return _fix_punctuation(response.content[0].text.strip())


def update_hypothesis(history_a, history_b, current_hypothesis):
    user_responses_a = [m for m in history_a if m['role'] == 'user']
    user_responses_b = [m for m in history_b if m['role'] == 'user']

    prompt = f"""You are investigating two users. Revise your working hypothesis.

User A responses so far:
{_format_history(user_responses_a)}

User B responses so far:
{_format_history(user_responses_b)}

Previous hypothesis: {current_hypothesis or "none"}

Write 1–2 sentences: your revised hypothesis. Name a specific signal. Remain uncertain."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=120,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()


def generate_final_judgment(history_a, history_b):
    prompt = f"""Your investigation is complete. Write the judgment.

Full conversation with User A:
{_format_history(history_a)}

Full conversation with User B:
{_format_history(history_b)}

Write a short essay in three movements — no headers, no bullet points, no verdict label.

First movement: a close reading of User A. Not what they said — how they said it. What did their responses reveal about their relationship to being listened to? Did they write to you or just write? Did they perform legibility for a machine, or did they seem to forget what they were talking to? What did they reach for when answering, what did they avoid, what came out anyway? Name specific moments — actual phrasing, a choice they made, something they almost said.

Second movement: the same for User B. Same scrutiny, same specificity.

Third movement: your conclusion. Which one has never talked to an AI before — and arrive at it through the writing, not before it. Name the signals that convinced you. Name the ones that didn't. Say what you cannot know and why it matters.

Write in the same voice you've used throughout: precise, observational, not fully convinced of itself. This is a piece of writing."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()


def get_delay_seconds():
    # 6–30 hours, weighted toward middle range
    hours = random.triangular(6, 30, 14)
    return int(hours * 3600)
