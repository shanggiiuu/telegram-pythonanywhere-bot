import os
import random
from datetime import datetime
from bot.clients import bot, BOT_INFO, store
from bot.config import COMMIT_SHA, HF_SPACE_ID, HOSTING_LABEL, MODEL, RATE_LIMIT
from bot.ai import ask_ai
from bot.helpers import is_allowed, keep_typing, send_reply, should_respond
from bot.history import clear_history
from bot.preferences import get_provider, set_provider
from bot.rate_limit import is_rate_limited

# Verbose console logging for local dev and teaching. Enabled by
# BOT_VERBOSE_LOG=1 (run_local.py sets this automatically). Prints one
# line per inbound/outbound message so kids and teachers can see the
# conversation flow in their terminal while the bot is running.
VERBOSE_LOG = os.environ.get("BOT_VERBOSE_LOG", "").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)


def _log(message, direction: str, text: str) -> None:
    """Print a one-line trace of a message in verbose mode.

    direction is "in" (user → bot) or "out" (bot → user). Text is
    truncated to 500 characters so long AI replies don't flood the
    terminal. Newlines are collapsed for single-line readability.
    """
    if not VERBOSE_LOG:
        return
    user = message.from_user
    user_name = (
        f"@{user.username}" if user.username else (user.first_name or f"user:{user.id}")
    )
    bot_name = f"@{BOT_INFO.username}"
    snippet = (text or "").replace("\n", " ").replace("\r", " ")
    if len(snippet) > 500:
        snippet = snippet[:500] + "..."
    if direction == "in":
        sender, receiver = user_name, bot_name
    else:
        sender, receiver = bot_name, user_name
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {sender} → {receiver}: {snippet}", flush=True)


@bot.message_handler(commands=["start"], func=is_allowed)
def cmd_start(message):
    bot.send_message(
        message.chat.id,
        " Heya hooman! :3 I'm Rooky the Raccoon \n your curious, slightly mischievous lil study buddy >:]",
    )


@bot.message_handler(commands=["help"], func=is_allowed)
def cmd_help(message):
    lines = [
        "/start — I say heyyy and we get going",
        "/help  — shows this lil menu of commands:D",
        "/reset — wipes our convo history, fresh start, clean slate, magic✨ ",
        "/about — peek under my hood (which AI model, storage, hosting, version) ;3",
        "/sha — which lil version of me is alive rn (git commit) 🤓",
        "/explain — paste code or a word, I break it down like ur 5 🤏",
        "/debug — paste ur broken code + error, I sniff out the bug 🐛",
        "/joke  — I tell you a unhinged funny joke👍 ",
        "/quote — something to cheer mah pookie up!!>:3",
        "/compliment — slay the day diva💅",
        "/raccoonfacts — fun facts bout raccoons n lil secrets bout me 🦝",
        "/recipe — whatcha cookin today chef? I gotchu 🍳",
        "/knowledge — random smart nugget to flex ur brain 🧠",
        "/devfact — spicy lil programming fun fact 👩‍💻🔥",
        "/finance — future-you money tips 💰 (or ask me a money Q)",
        "/uni — uni planning help, we plottin ur glowup 🎓",
        "/roll — ROLL THE DICE! 🎲",
        "/roast — imma cook :p",
        "/remember — got it inside the walnut😎",
        "/recall — I dig it back outta the walnut:3",
        "/forget — it ran away from my brain",
    ]
    if HF_SPACE_ID:
        lines.append("/model — switch AI provider")
    bot.send_message(message.chat.id, "\n".join(lines))


@bot.message_handler(commands=["reset"], func=is_allowed)
def cmd_reset(message):
    clear_history(message.from_user.id)
    bot.send_message(message.chat.id, "Conversation cleared. Starting fresh!")


@bot.message_handler(commands=["about"], func=is_allowed)
def cmd_about(message):
    if HF_SPACE_ID:
        provider = get_provider(message.from_user.id)
        model_line = f"{MODEL} (main)" if provider == "main" else f"{HF_SPACE_ID} (hf)"
    else:
        model_line = MODEL
    storage_line = "SQLite" if store is not None else "stateless (no memory)"
    lines = [
        ask_ai(message.from_user.id, "summarize your personality in one sentence"),
        f"Model  : {model_line}",
        f"Storage: {storage_line}",
        f"Hosting: {HOSTING_LABEL}",
    ]
    if COMMIT_SHA:
        lines.append(f"Version: {COMMIT_SHA}")
    bot.send_message(message.chat.id, "\n".join(lines))

@bot.message_handler(commands=["joke"], func=is_allowed)
def cmd_joke(message):
 reply = ask_ai(message.from_user.id, "Tell one short, clean programming joke.")
 bot.send_message(message.chat.id, reply)


@bot.message_handler(commands=["quote"], func=is_allowed)
def cmd_quote(message):
    with keep_typing(message.chat.id):
        reply = ask_ai(message.from_user.id, "Share one short, inspiring quote about learning or coding.")
    send_reply(message, reply)


@bot.message_handler(commands=["compliment"], func=is_allowed)
def cmd_compliment(message):
      with keep_typing(message.chat.id):
          reply = ask_ai(message.from_user.id, "Give me a warm, wholesome, encouraging compliment to brighten my day.")
      send_reply(message, reply)


@bot.message_handler(commands=["raccoonfacts"], func=is_allowed)
def cmd_raccoonfacts(message):
    # Coin-flip: a true fact about real raccoons, or a playful in-character
    # "fact" about Rooky himself. Both kept short and fun.
    if random.choice(["real", "rooky"]) == "real":
        prompt = (
            "Tell me one genuinely true, fun fact about real raccoons. Keep it "
            "short, surprising, and playful."
        )
    else:
        prompt = (
            "You are Rooky the Raccoon. Share one playful, made-up 'fun fact' "
            "about YOURSELF — your raccoon life, quirks, or personality. Keep "
            "it short, silly, and in-character; it's just for fun, not a real "
            "fact."
        )
    with keep_typing(message.chat.id):
        reply = ask_ai(message.from_user.id, prompt)
    send_reply(message, reply)


@bot.message_handler(commands=["explain"], func=is_allowed)
def cmd_explain(message):
    # Split on any whitespace (maxsplit=1) so pasted code with newlines still
    # counts as the topic — users often do "/explain\n<code block>".
    parts = (message.text or "").split(maxsplit=1)
    topic = parts[1].strip() if len(parts) > 1 else ""
    if not topic:
        bot.send_message(
            message.chat.id,
            "Gimme somethin to explain gurl!:3 paste some code or drop a word — "
            "like: /explain what is a for loop",
        )
        return
    prompt = (
        "Explain this like I'm 5 years old: super simple words, one fun "
        "everyday analogy, and keep it short. If it's code, say what it does "
        f"and walk through it step by step:\n\n{topic}"
    )
    with keep_typing(message.chat.id):
        reply = ask_ai(message.from_user.id, prompt)
    send_reply(message, reply)


@bot.message_handler(commands=["debug"], func=is_allowed)
def cmd_debug(message):
    # Split on any whitespace (maxsplit=1) so pasted code with newlines still
    # counts as the input — users paste a code block and/or an error message.
    parts = (message.text or "").split(maxsplit=1)
    snippet = parts[1].strip() if len(parts) > 1 else ""
    if not snippet:
        bot.send_message(
            message.chat.id,
            "Paste the code thats actin sus (and the error if ya got one) and "
            "I'll sniff out the bug 🐛 — like: /debug <your code>",
        )
        return
    prompt = (
        "Help me debug this. Find the most likely bug(s), explain in simple "
        "terms what's going wrong and why, then show the corrected code. If "
        "there's an error message, use it as a clue. Keep it beginner-friendly:"
        f"\n\n{snippet}"
    )
    with keep_typing(message.chat.id):
        reply = ask_ai(message.from_user.id, prompt)
    send_reply(message, reply)


@bot.message_handler(commands=["recipe"], func=is_allowed)
def cmd_recipe(message):
    # Tailored for someone who cooks for the family every day: keep it to
    # simple, everyday food with common ingredients. Rotate a random vibe so
    # daily calls don't keep serving up the same dish.
    vibe = random.choice(
        [
            "a quick breakfast",
            "a cozy one-pot meal",
            "a budget-friendly family dinner",
            "a 15-minute lunch",
            "a simple rice dish",
            "a comforting soup or stew",
            "an easy noodle or pasta dish",
            "a filling snack anyone can make",
        ]
    )
    prompt = (
        f"Suggest ONE simple everyday recipe: {vibe}. Give it a fun name, a "
        "short list of common ingredients, and 3-6 easy numbered steps. Keep "
        "it beginner-friendly and quick to cook."
    )
    with keep_typing(message.chat.id):
        reply = ask_ai(message.from_user.id, prompt)
    send_reply(message, reply)


@bot.message_handler(commands=["knowledge"], func=is_allowed)
def cmd_knowledge(message):
    # A "learn something" mini-lesson — distinct from /fact's quick trivia.
    # With a topic it teaches that subject (the how/why); with none it rotates
    # a random domain and teaches a concept, not a one-line fact.
    parts = (message.text or "").split(maxsplit=1)
    topic = parts[1].strip() if len(parts) > 1 else ""
    if topic:
        prompt = (
            "Teach me about this topic like a friendly mini-lesson: explain "
            "what it is and how or why it works, in a few clear, "
            "beginner-friendly sentences. Go deeper than a one-line fact: "
            + topic
        )
    else:
        domain = random.choice(
            [
                "science",
                "world history",
                "space and astronomy",
                "nature and animals",
                "geography",
                "the human body",
                "art and culture",
                "mathematics",
                "how everyday things work",
            ]
        )
        prompt = (
            f"Teach me one interesting concept from {domain} as a short "
            "mini-lesson. Don't just state a fact — briefly explain how or why "
            "it works, in a few clear, beginner-friendly sentences with a "
            "touch of wonder."
        )
    with keep_typing(message.chat.id):
        reply = ask_ai(message.from_user.id, prompt)
    send_reply(message, reply)


@bot.message_handler(commands=["devfact"], func=is_allowed)
def cmd_devfact(message):
    # The programming twin of /fact. Optional topic; otherwise rotate a random
    # corner of computing so calls stay varied.
    parts = (message.text or "").split(maxsplit=1)
    topic = parts[1].strip() if len(parts) > 1 else ""
    if topic:
        prompt = (
            "Tell me one fun, true programming or computer-science fact about "
            "this. Keep it short, surprising, and beginner-friendly: " + topic
        )
    else:
        subtopic = random.choice(
            [
                "the history of computing",
                "programming languages",
                "a famous software bug or glitch",
                "algorithms and data structures",
                "the internet and networking",
                "computer hardware",
                "open source software",
                "artificial intelligence",
                "cybersecurity",
                "a famous programmer or computer scientist",
            ]
        )
        prompt = (
            f"Tell me one fun, true fact about {subtopic}. Keep it short, "
            "surprising, and beginner-friendly."
        )
    with keep_typing(message.chat.id):
        reply = ask_ai(message.from_user.id, prompt)
    send_reply(message, reply)


@bot.message_handler(commands=["finance"], func=is_allowed)
def cmd_finance(message):
    # Optional money question; otherwise rotate a practical topic. Written to be
    # useful for anyone (teen or adult) and framed as friendly tips, not
    # professional financial advice.
    parts = (message.text or "").split(maxsplit=1)
    topic = parts[1].strip() if len(parts) > 1 else ""
    if topic:
        prompt = (
            "Answer this personal-finance question in a short, practical, "
            "beginner-friendly way that works for anyone, teen or adult. End "
            "with a tiny reminder that this is friendly guidance, not "
            "professional financial advice: " + topic
        )
    else:
        money_topic = random.choice(
            [
                "saving money",
                "making a simple budget",
                "needs vs wants",
                "compound interest",
                "building an emergency fund",
                "avoiding debt",
                "your first paycheck",
                "smart spending",
                "setting money goals",
            ]
        )
        prompt = (
            f"Give me one practical, beginner-friendly personal-finance tip "
            f"about {money_topic} to help me with my future money. Keep it "
            "short and encouraging. End with a tiny reminder that this is "
            "friendly guidance, not professional financial advice."
        )
    with keep_typing(message.chat.id):
        reply = ask_ai(message.from_user.id, prompt)
    send_reply(message, reply)


@bot.message_handler(commands=["uni"], func=is_allowed)
def cmd_uni(message):
    # Optional university question; otherwise rotate a planning topic. Kept
    # general and encouraging for any student.
    parts = (message.text or "").split(maxsplit=1)
    topic = parts[1].strip() if len(parts) > 1 else ""
    if topic:
        prompt = (
            "Answer this university-planning question in a short, practical, "
            "encouraging way for a student: " + topic
        )
    else:
        uni_topic = random.choice(
            [
                "choosing a major",
                "the application timeline",
                "writing a personal statement or essay",
                "finding scholarships and funding",
                "good study habits",
                "how to choose a university",
                "balancing passion with job prospects",
                "preparing for entrance exams",
                "student life and staying organized",
            ]
        )
        prompt = (
            f"Give me one helpful, practical tip about {uni_topic} to help me "
            "plan for university. Keep it short, encouraging, and useful for "
            "any student."
        )
    with keep_typing(message.chat.id):
        reply = ask_ai(message.from_user.id, prompt)
    send_reply(message, reply)


@bot.message_handler(commands=["roll"], func=is_allowed)
def cmd_roll(message):
    result = random.randint(1, 6)
    bot.send_message(message.chat.id, f"🎲 You rolled a {result}!")

@bot.message_handler(commands=["roast"], func=is_allowed)
def cmd_roast(message):
    name = message.text.split(maxsplit=1)[1] if " " in message.text else "you"
    reply = ask_ai(message.from_user.id, f"Write a short, playful, friendly roast of {name}.")
    bot.send_message(message.chat.id, reply)

@bot.message_handler(commands=["remember"], func=is_allowed)
def cmd_remember(message):
    if store is None:
        bot.send_message(message.chat.id, "mah brain ain't running without the memory rn bru, can't save anythin")
        return
    note = message.text.split(maxsplit=1)[1].strip() if " " in message.text else ""
    if not note:
        bot.send_message(message.chat.id, "Tell me what to remember gurl! Like: /remember buy snacks")
        return
    key = f"note:{message.from_user.id}"
    existing = store.get(key)
    updated = f"{existing}\n{note}" if existing else note
    store.set(key, updated)
    bot.send_message(message.chat.id, "Saved!:D stashed it with the rest in mah smol brain")


@bot.message_handler(commands=["recall"], func=is_allowed)
def cmd_recall(message):
    if store is None:
        bot.send_message(message.chat.id, "mah brain ain't running without the memory rn bru, didn't recall anythin")
        return
    note = store.get(f"note:{message.from_user.id}")
    if note:
        items = note.split("\n")
        numbered = "\n".join(f"{i}. {item}" for i, item in enumerate(items, start=1))
        bot.send_message(message.chat.id, f"Here's everythin ya told me to remember:]:\n{numbered}")
    else:
        bot.send_message(message.chat.id, "I didn't recall anythin for ya yet, Use /remember <note> gurl")


@bot.message_handler(commands=["forget"], func=is_allowed)
def cmd_forget(message):
    if store is None:
        bot.send_message(message.chat.id, "mah brain ain't running without the memory rn bru, so there's nothing to forget:p.")
        return
    if store.get(f"note:{message.from_user.id}"):
        store.delete(f"note:{message.from_user.id}")
        bot.send_message(message.chat.id, "Poof! the brain ran :/")
    else:
        bot.send_message(message.chat.id, "There's nothing saved to forget! >:D")


@bot.message_handler(commands=["sha"], func=is_allowed)
def cmd_sha(message):
    sha = COMMIT_SHA or "unknown"
    bot.send_message(message.chat.id, f"Live SHA: {sha}")


if HF_SPACE_ID:

    @bot.message_handler(commands=["model"], func=is_allowed)
    def cmd_model(message):
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) == 1:
            current = get_provider(message.from_user.id)
            bot.send_message(
                message.chat.id,
                f"Current provider: {current}\n\n"
                "Options:\n"
                "/model main — Cerebras (fast, multilingual, with memory)\n"
                "/model hf — ArmGPT (Armenian only, slow, no memory)",
            )
            return
        choice = parts[1].strip().lower()
        if choice not in ("main", "hf"):
            bot.send_message(
                message.chat.id, "Invalid choice. Use: /model main or /model hf"
            )
            return
        if not set_provider(message.from_user.id, choice):
            bot.send_message(
                message.chat.id, "Could not save preference. Try again later."
            )
            return
        if choice == "hf":
            bot.send_message(
                message.chat.id,
                "Switched to hf (ArmGPT).\n\n"
                "Note: this is a tiny base completion model trained only on Armenian text. "
                "It will continue whatever you write rather than answer questions, "
                "and it does not understand English. Replies take ~30-60s and there is no memory.",
            )
        else:
            bot.send_message(message.chat.id, "Switched to Main Provider.")


@bot.message_handler(content_types=["text"], func=is_allowed)
def handle_message(message):
    if not should_respond(message):
        return
    text = (message.text or "").replace(f"@{BOT_INFO.username}", "").strip()
    if not text:
        # Edited messages, forwards, or stickers-with-empty-caption can
        # arrive with no usable text. Don't burn rate-limit / AI calls on them.
        return
    _log(message, "in", text)
    if is_rate_limited(message.from_user.id):
        limit_msg = f"You've reached the daily limit of {RATE_LIMIT} messages. Try again tomorrow."
        bot.send_message(message.chat.id, limit_msg)
        _log(message, "out", f"[rate limited] {limit_msg}")
        return
    try:
        with keep_typing(message.chat.id):
            reply = ask_ai(message.from_user.id, text)
        send_reply(message, reply)
        _log(message, "out", reply)
    except Exception as e:
        print(f"Error in handle_message: {e}")
        bot.send_message(message.chat.id, "Something went wrong. Please try again.")
        _log(message, "out", f"[error] {e}")
