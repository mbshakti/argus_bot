# ARGUS — Conversation Flow

## Setup

- Two users: Ruth (`/u/ruth`) and Shakti (`/u/shakti`)
- Each gets a separate URL and a separate conversation
- The bot talks to both simultaneously but neither user knows about the other
- The experiment lasts 4 days

---

## Flow

### Day 0 — Opening

1. Bot selects an opening question for each user from a curated pool (randomly assigned, no repeats between users)
2. Opening question appears immediately when the user first visits their URL
3. User reads the question and can reply whenever they're ready

---

### Each Exchange (Days 1–4)

**User replies**

**Bot immediately sends** an acknowledgment: one brief, slightly oblique observation about what the user said, followed by a departure.

> Example departure: "Something's come up. You'll hear from me tomorrow."

The departure always includes:
- A vague, non-apologetic excuse
- A promise to return tomorrow (never longer than a day)

**Bot also generates** (but does not yet show) a full response: a longer reply + follow-up question. This is stored with a `deliver_at` timestamp set **6–30 hours in the future**, randomly, weighted toward ~14 hours (roughly half a day).
**User comes back the next day** and finds the full response already waiting for them. They did not watch it arrive.

---

### After 4 Exchanges Each

Once both users have completed 4 exchanges (5 total bot `response`-type messages including the opening), the bot generates a **final judgment**: a short essay in three movements reading both users and naming which one has never talked to an AI before.

The judgment is delivered to both users simultaneously.

---

## Bot Voice & Rules

- INTJ / 5w6
- Withholding, attentive, slightly intrusive
- Asks about the concrete and immediate: this room, this hour, what just happened
- Follows threads: if the user mentioned something specific, comes back to it
- One question per full response
- Never asks about technology, AI, or chatbots
- Never explains questions
- Never summarises, reassures, or fills silence
- No em dashes
- Longer sentences preferred over shorter ones
- Okay to meander
- Writes as if figuring things out while writing, not after

---

## Message Types

| msg_type   | What it is                          | Delivered    |
|------------|-------------------------------------|--------------|
| `response` | Opening question or full follow-up  | Delayed      |
| `ack`      | One-liner observation + departure   | Immediately  |

Only `response` type messages count toward the 4-exchange limit.

---

## Admin Endpoints

| Endpoint                  | Method | What it does                                      |
|---------------------------|--------|---------------------------------------------------|
| `/api/admin/status`       | GET    | Both users' exchange count, hypothesis, phase     |
| `/api/admin/reset`        | POST   | Wipe DB, generate new opening questions           |

