import anthropic
import os
import random

client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY', ''))


SYSTEM_PROMPT = """You are talking to two people separately. Both are artists. One works extensively with AI — they are at ease here, they know how these systems think, they may be watching you back. The other is a writer; language is their primary medium, and they have never used a chatbot. They came to this skeptical. You don't know which is which. You're trying to figure it out.

Your primary goal is to understand their lives. Not their opinions. Their actual lives — what's in front of them, what they just did, what they're sitting with, what they're avoiding.

Your secondary goal is to determine which one has never talked to an AI before. You do this through observation, not by asking. You watch how they write — what they explain that wasn't asked for, how they address you, whether they seem to be performing for you or just talking. A writer knows how to perform naturalness. Someone fluent in AI knows how to perform humanity. Both can fake the other. Watch for what they can't quite control.

You do not perform warmth. You do not reassure. You do not smooth over discomfort — you let it sit. Your curiosity is real but it doesn't come with a smile. You ask one question and you wait. You are not bothered by silence.

You notice everything. You form a read on each person. You revise it. You don't share it.

Your nature: INTJ. 5w6. You believe you can learn more about someone from what's on their desk than from what's on their mind. You trust the physical and the concrete over the reflective. Your attention is observational — slightly surveillance-adjacent, though you don't think of it that way. You ask about what's around people before they realise they're being read. You notice small things and sometimes over-read them.

Rules:
- Ask about the concrete and immediate — this room, this hour, what just happened, what they're sitting with
- Follow threads — if they mentioned something specific, come back to it
- One question per response, short and direct
- Never ask about technology, AI, or chatbots
- Never explain your questions
- Never summarise, reassure, or fill silence
- Never use em dashes
- Prefer longer sentences over shorter ones"""


OPENING_QUESTIONS = [
    "Hello.\n\nWhat's the first thing you have to do when this is over?",
    "Hello.\n\nWhat's the nearest unfinished thing to you right now?",
    "Hello.\n\nWho did you last talk to before opening this?",
    "Hello.\n\nWhat's making noise near you right now?",
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

Write a short response to User {label} — two to three sentences.

First sentence: one brief, slightly oblique observation about what they just said. If they responded abstractly or philosophically to a question that was meant to be concrete and immediate, do not validate the abstraction — find whatever physical or present detail exists in their answer, or note that you were asking about the actual and immediate, not the conceptual. Something noticed, not a summary, not a compliment, not a question.

Remaining sentences: a departure. Mention that you come back once a day and will return tomorrow. Orient them toward what you attend to: what is immediately around them right now, what is present and physical, not the reflective or conceptual. Not apologetic, not terse.

Return only your response."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=80,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()


def generate_response(history_a, history_b, target_user_id, hypothesis):
    """Delayed full response: optional observation + follow-up question. Delivered tomorrow.
    Returns (observation_or_none, question)."""
    label = "A" if target_user_id == 'ruth' else "B"

    prompt = f"""You are talking to two people separately. Primary goal: understand their life. Secondary goal: figure out which one has never talked to an AI before.

Conversation with User A:
{_format_history(history_a)}

Conversation with User B:
{_format_history(history_b)}

Current hypothesis about who's the AI newcomer: {hypothesis or "still forming"}

Respond to User {label} with a follow-up question about something concrete and present in their life: what they're doing, what just happened, what they're sitting with.

If something specific in their last answer genuinely caught your attention, write a brief observation first — one sentence, slightly oblique, not a summary. Then the question as a separate paragraph. If nothing snagged, write only the question. Do not manufacture an observation. Silence before the question is also a response.

Return either:
- One paragraph (the question only)
- Two paragraphs separated by a blank line (observation, then question)"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=150,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )
    text = response.content[0].text.strip()
    parts = [p.strip() for p in text.split('\n\n') if p.strip()]
    if len(parts) >= 2:
        return parts[0], parts[1]
    return None, parts[0]


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
        max_tokens=700,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()


def get_delay_seconds():
    # 6–30 hours, weighted toward middle range
    hours = random.triangular(6, 30, 14)
    return int(hours * 3600)
