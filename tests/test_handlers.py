from unittest.mock import patch, MagicMock


def make_message(text="hello", user_id=123, chat_id=456, chat_type="private"):
    msg = MagicMock()
    msg.text = text
    msg.from_user.id = user_id
    msg.chat.id = chat_id
    msg.chat.type = chat_type
    msg.reply_to_message = None
    return msg


HANDLER_PATCHES = {
    "bot.handlers.should_respond": True,
    "bot.handlers.is_rate_limited": False,
    "bot.handlers.BOT_INFO": MagicMock(id=42, username="testbot"),
}


def test_handle_message_calls_ask_ai():
    with (
        patch("bot.handlers.should_respond", return_value=True),
        patch("bot.handlers.is_rate_limited", return_value=False),
        patch("bot.handlers.BOT_INFO", MagicMock(username="testbot")),
        patch("bot.handlers.ask_ai", return_value="AI reply") as mock_ask,
        patch("bot.handlers.send_reply") as mock_send,
        patch("bot.handlers.bot"),
    ):
        from bot.handlers import handle_message

        msg = make_message(text="hello")
        handle_message(msg)
        mock_ask.assert_called_once_with(123, "hello")
        mock_send.assert_called_once_with(msg, "AI reply")


def test_handle_message_skips_when_not_responding():
    with (
        patch("bot.handlers.should_respond", return_value=False),
        patch("bot.handlers.ask_ai") as mock_ask,
    ):
        from bot.handlers import handle_message

        handle_message(make_message())
        mock_ask.assert_not_called()


def test_handle_message_rate_limited():
    with (
        patch("bot.handlers.should_respond", return_value=True),
        patch("bot.handlers.is_rate_limited", return_value=True),
        patch("bot.handlers.BOT_INFO", MagicMock(username="testbot")),
        patch("bot.handlers.ask_ai") as mock_ask,
        patch("bot.handlers.bot") as mock_bot,
    ):
        from bot.handlers import handle_message

        handle_message(make_message())
        mock_ask.assert_not_called()
        mock_bot.send_message.assert_called_once()
        assert "daily limit" in mock_bot.send_message.call_args[0][1]


def test_handle_message_sends_generic_error():
    with (
        patch("bot.handlers.should_respond", return_value=True),
        patch("bot.handlers.is_rate_limited", return_value=False),
        patch("bot.handlers.BOT_INFO", MagicMock(username="testbot")),
        patch("bot.handlers.ask_ai", side_effect=Exception("API key invalid")),
        patch("bot.handlers.bot") as mock_bot,
    ):
        from bot.handlers import handle_message

        handle_message(make_message())
        error_msg = mock_bot.send_message.call_args[0][1]
        assert "Something went wrong" in error_msg
        assert "API key" not in error_msg


def test_handle_message_none_text_skipped():
    """Stickers/photos/edits arriving with text=None must NOT call ask_ai
    (would burn rate limit and AI quota for no reason)."""
    with (
        patch("bot.handlers.should_respond", return_value=True),
        patch("bot.handlers.is_rate_limited", return_value=False),
        patch("bot.handlers.BOT_INFO", MagicMock(username="testbot")),
        patch("bot.handlers.ask_ai") as mock_ask,
        patch("bot.handlers.send_reply") as mock_send,
        patch("bot.handlers.bot"),
    ):
        from bot.handlers import handle_message

        msg = make_message()
        msg.text = None
        handle_message(msg)
        mock_ask.assert_not_called()
        mock_send.assert_not_called()


def test_handle_message_mention_only_skipped():
    """In a group, '@testbot' alone strips to empty — don't call ask_ai."""
    with (
        patch("bot.handlers.should_respond", return_value=True),
        patch("bot.handlers.is_rate_limited", return_value=False),
        patch("bot.handlers.BOT_INFO", MagicMock(username="testbot")),
        patch("bot.handlers.ask_ai") as mock_ask,
        patch("bot.handlers.send_reply"),
        patch("bot.handlers.bot"),
    ):
        from bot.handlers import handle_message

        msg = make_message(text="@testbot")
        handle_message(msg)
        mock_ask.assert_not_called()


# ── /start ──────────────────────────────────────────────────────────────────


def test_cmd_start_sends_greeting():
    with patch("bot.handlers.bot") as mock_bot:
        from bot.handlers import cmd_start

        cmd_start(make_message(text="/start"))
        mock_bot.send_message.assert_called_once()
        chat_id, text = mock_bot.send_message.call_args[0]
        assert chat_id == 456
        assert "Rooky" in text


# ── /help ─────────────────────────────────────────────────────────────────────


def test_cmd_help_lists_commands():
    """Without HF, /help lists the base commands and omits /model."""
    with (
        patch("bot.handlers.bot") as mock_bot,
        patch("bot.handlers.HF_SPACE_ID", ""),
    ):
        from bot.handlers import cmd_help

        cmd_help(make_message(text="/help"))
        sent = mock_bot.send_message.call_args[0][1]
        assert "/start" in sent
        assert "/reset" in sent
        assert "/roast" in sent
        assert "/recipe" in sent
        assert "/explain" in sent
        assert "/knowledge" in sent
        assert "/devfact" in sent
        assert "/finance" in sent
        assert "/uni" in sent
        assert "/debug" in sent
        assert "/raccoonfacts" in sent
        assert "/fact" not in sent  # merged into /knowledge
        assert "/model" not in sent


def test_cmd_help_includes_model_when_hf_enabled():
    """When HF_SPACE_ID is set, /help advertises the /model command."""
    with (
        patch("bot.handlers.bot") as mock_bot,
        patch("bot.handlers.HF_SPACE_ID", "fake/space"),
    ):
        from bot.handlers import cmd_help

        cmd_help(make_message(text="/help"))
        sent = mock_bot.send_message.call_args[0][1]
        assert "/model" in sent


# ── /reset ────────────────────────────────────────────────────────────────────


def test_cmd_reset_clears_history():
    with (
        patch("bot.handlers.clear_history") as mock_clear,
        patch("bot.handlers.bot") as mock_bot,
    ):
        from bot.handlers import cmd_reset

        cmd_reset(make_message(text="/reset"))
        mock_clear.assert_called_once_with(123)  # make_message default user_id
        assert "cleared" in mock_bot.send_message.call_args[0][1].lower()


# ── /joke ─────────────────────────────────────────────────────────────────────


def test_cmd_joke_asks_ai_and_replies():
    with (
        patch("bot.handlers.ask_ai", return_value="Why did the dev...") as mock_ask,
        patch("bot.handlers.bot") as mock_bot,
    ):
        from bot.handlers import cmd_joke

        cmd_joke(make_message(text="/joke"))
        mock_ask.assert_called_once()
        assert mock_ask.call_args[0][0] == 123  # user_id
        assert mock_bot.send_message.call_args[0][1] == "Why did the dev..."


# ── /quote, /compliment (keep_typing + send_reply pattern) ──────────────────────


def test_cmd_quote_uses_keep_typing_and_send_reply():
    with (
        patch("bot.handlers.ask_ai", return_value="Keep learning.") as mock_ask,
        patch("bot.handlers.send_reply") as mock_send,
        patch("bot.handlers.keep_typing") as mock_keep,
        patch("bot.handlers.bot"),
    ):
        mock_keep.return_value.__enter__ = MagicMock(return_value=None)
        mock_keep.return_value.__exit__ = MagicMock(return_value=None)
        from bot.handlers import cmd_quote

        msg = make_message(text="/quote")
        cmd_quote(msg)
        mock_keep.assert_called_once_with(456)  # chat_id
        mock_ask.assert_called_once()
        mock_send.assert_called_once_with(msg, "Keep learning.")


def test_cmd_compliment_uses_keep_typing_and_send_reply():
    with (
        patch("bot.handlers.ask_ai", return_value="You're doing great!"),
        patch("bot.handlers.send_reply") as mock_send,
        patch("bot.handlers.keep_typing") as mock_keep,
        patch("bot.handlers.bot"),
    ):
        mock_keep.return_value.__enter__ = MagicMock(return_value=None)
        mock_keep.return_value.__exit__ = MagicMock(return_value=None)
        from bot.handlers import cmd_compliment

        msg = make_message(text="/compliment")
        cmd_compliment(msg)
        mock_keep.assert_called_once_with(456)
        mock_send.assert_called_once_with(msg, "You're doing great!")


# ── /raccoonfacts ─────────────────────────────────────────────────────────────


def test_cmd_raccoonfacts_real_branch_asks_for_true_raccoon_fact():
    with (
        patch("bot.handlers.ask_ai", return_value="Raccoons wash their food!") as mock_ask,
        patch("bot.handlers.send_reply") as mock_send,
        patch("bot.handlers.keep_typing") as mock_keep,
        patch("bot.handlers.random.choice", return_value="real"),
        patch("bot.handlers.bot"),
    ):
        mock_keep.return_value.__enter__ = MagicMock(return_value=None)
        mock_keep.return_value.__exit__ = MagicMock(return_value=None)
        from bot.handlers import cmd_raccoonfacts

        msg = make_message(text="/raccoonfacts")
        cmd_raccoonfacts(msg)
        mock_keep.assert_called_once_with(456)  # chat_id
        assert "real raccoons" in mock_ask.call_args[0][1]  # true-fact branch
        mock_send.assert_called_once_with(msg, "Raccoons wash their food!")


def test_cmd_raccoonfacts_rooky_branch_asks_for_in_character_fact():
    with (
        patch("bot.handlers.ask_ai", return_value="I once heist-ed a cookie jar!") as mock_ask,
        patch("bot.handlers.send_reply") as mock_send,
        patch("bot.handlers.keep_typing") as mock_keep,
        patch("bot.handlers.random.choice", return_value="rooky"),
        patch("bot.handlers.bot"),
    ):
        mock_keep.return_value.__enter__ = MagicMock(return_value=None)
        mock_keep.return_value.__exit__ = MagicMock(return_value=None)
        from bot.handlers import cmd_raccoonfacts

        cmd_raccoonfacts(make_message(text="/raccoonfacts"))
        assert "Rooky the Raccoon" in mock_ask.call_args[0][1]  # in-character branch
        mock_send.assert_called_once()


def test_cmd_recipe_uses_keep_typing_and_send_reply():
    with (
        patch("bot.handlers.ask_ai", return_value="🍳 Sunny Egg Toast: ...") as mock_ask,
        patch("bot.handlers.send_reply") as mock_send,
        patch("bot.handlers.keep_typing") as mock_keep,
        patch("bot.handlers.bot"),
    ):
        mock_keep.return_value.__enter__ = MagicMock(return_value=None)
        mock_keep.return_value.__exit__ = MagicMock(return_value=None)
        from bot.handlers import cmd_recipe

        msg = make_message(text="/recipe")
        cmd_recipe(msg)
        mock_keep.assert_called_once_with(456)  # chat_id
        mock_ask.assert_called_once()
        assert mock_ask.call_args[0][0] == 123  # user_id
        assert "recipe" in mock_ask.call_args[0][1].lower()  # prompt asks for a recipe
        mock_send.assert_called_once_with(msg, "🍳 Sunny Egg Toast: ...")


# ── /explain ──────────────────────────────────────────────────────────────────


def test_cmd_explain_with_topic_uses_keep_typing_and_send_reply():
    """'/explain <topic>' threads the topic into an ELI5 prompt and replies."""
    with (
        patch("bot.handlers.ask_ai", return_value="It's like a recipe!") as mock_ask,
        patch("bot.handlers.send_reply") as mock_send,
        patch("bot.handlers.keep_typing") as mock_keep,
        patch("bot.handlers.bot"),
    ):
        mock_keep.return_value.__enter__ = MagicMock(return_value=None)
        mock_keep.return_value.__exit__ = MagicMock(return_value=None)
        from bot.handlers import cmd_explain

        msg = make_message(text="/explain what is a for loop")
        cmd_explain(msg)
        mock_keep.assert_called_once_with(456)  # chat_id
        mock_ask.assert_called_once()
        assert mock_ask.call_args[0][0] == 123  # user_id
        prompt = mock_ask.call_args[0][1]
        assert "what is a for loop" in prompt  # user's topic threaded in
        assert "5 years old" in prompt  # ELI5 framing
        mock_send.assert_called_once_with(msg, "It's like a recipe!")


def test_cmd_explain_without_topic_shows_usage_hint():
    """Bare '/explain' must NOT call the AI (it can't see code it wasn't given);
    it shows a usage hint instead."""
    with (
        patch("bot.handlers.ask_ai") as mock_ask,
        patch("bot.handlers.bot") as mock_bot,
    ):
        from bot.handlers import cmd_explain

        cmd_explain(make_message(text="/explain"))
        mock_ask.assert_not_called()
        assert "/explain" in mock_bot.send_message.call_args[0][1]


# ── /debug ────────────────────────────────────────────────────────────────────


def test_cmd_debug_with_code_threads_snippet_into_prompt():
    with (
        patch("bot.handlers.ask_ai", return_value="Missing a colon!") as mock_ask,
        patch("bot.handlers.send_reply") as mock_send,
        patch("bot.handlers.keep_typing") as mock_keep,
        patch("bot.handlers.bot"),
    ):
        mock_keep.return_value.__enter__ = MagicMock(return_value=None)
        mock_keep.return_value.__exit__ = MagicMock(return_value=None)
        from bot.handlers import cmd_debug

        msg = make_message(text="/debug def f() return 1")
        cmd_debug(msg)
        mock_keep.assert_called_once_with(456)  # chat_id
        mock_ask.assert_called_once()
        assert mock_ask.call_args[0][0] == 123  # user_id
        prompt = mock_ask.call_args[0][1]
        assert "def f() return 1" in prompt  # pasted code threaded in
        assert "debug" in prompt.lower()  # framed as a debugging task
        mock_send.assert_called_once_with(msg, "Missing a colon!")


def test_cmd_debug_without_code_shows_usage_hint():
    """Bare '/debug' must NOT call the AI (nothing to debug); shows a hint."""
    with (
        patch("bot.handlers.ask_ai") as mock_ask,
        patch("bot.handlers.bot") as mock_bot,
    ):
        from bot.handlers import cmd_debug

        cmd_debug(make_message(text="/debug"))
        mock_ask.assert_not_called()
        assert "/debug" in mock_bot.send_message.call_args[0][1]


# ── /knowledge, /devfact, /finance, /uni (optional-arg + random-topic) ──────────


def test_cmd_knowledge_with_topic_threads_topic_into_prompt():
    with (
        patch("bot.handlers.ask_ai", return_value="Black holes are wild!") as mock_ask,
        patch("bot.handlers.send_reply") as mock_send,
        patch("bot.handlers.keep_typing") as mock_keep,
        patch("bot.handlers.bot"),
    ):
        mock_keep.return_value.__enter__ = MagicMock(return_value=None)
        mock_keep.return_value.__exit__ = MagicMock(return_value=None)
        from bot.handlers import cmd_knowledge

        msg = make_message(text="/knowledge black holes")
        cmd_knowledge(msg)
        mock_keep.assert_called_once_with(456)  # chat_id
        assert mock_ask.call_args[0][0] == 123  # user_id
        assert "black holes" in mock_ask.call_args[0][1]  # topic threaded in
        assert "mini-lesson" in mock_ask.call_args[0][1]  # explainer, not a one-liner
        mock_send.assert_called_once_with(msg, "Black holes are wild!")


def test_cmd_knowledge_without_topic_uses_random_domain():
    with (
        patch("bot.handlers.ask_ai", return_value="Did you know...") as mock_ask,
        patch("bot.handlers.send_reply") as mock_send,
        patch("bot.handlers.keep_typing") as mock_keep,
        patch("bot.handlers.random.choice", return_value="science"),
        patch("bot.handlers.bot"),
    ):
        mock_keep.return_value.__enter__ = MagicMock(return_value=None)
        mock_keep.return_value.__exit__ = MagicMock(return_value=None)
        from bot.handlers import cmd_knowledge

        cmd_knowledge(make_message(text="/knowledge"))
        mock_ask.assert_called_once()  # no-arg still calls the AI
        assert "science" in mock_ask.call_args[0][1]  # random domain used
        assert "mini-lesson" in mock_ask.call_args[0][1]  # a lesson, not /fact-style trivia
        mock_send.assert_called_once()


def test_cmd_devfact_with_topic_threads_topic_into_prompt():
    with (
        patch("bot.handlers.ask_ai", return_value="Python fact!") as mock_ask,
        patch("bot.handlers.send_reply") as mock_send,
        patch("bot.handlers.keep_typing") as mock_keep,
        patch("bot.handlers.bot"),
    ):
        mock_keep.return_value.__enter__ = MagicMock(return_value=None)
        mock_keep.return_value.__exit__ = MagicMock(return_value=None)
        from bot.handlers import cmd_devfact

        msg = make_message(text="/devfact python")
        cmd_devfact(msg)
        mock_keep.assert_called_once_with(456)
        assert "python" in mock_ask.call_args[0][1]
        mock_send.assert_called_once_with(msg, "Python fact!")


def test_cmd_devfact_without_topic_uses_random_subtopic():
    with (
        patch("bot.handlers.ask_ai", return_value="A fun bug...") as mock_ask,
        patch("bot.handlers.send_reply") as mock_send,
        patch("bot.handlers.keep_typing") as mock_keep,
        patch("bot.handlers.random.choice", return_value="cybersecurity"),
        patch("bot.handlers.bot"),
    ):
        mock_keep.return_value.__enter__ = MagicMock(return_value=None)
        mock_keep.return_value.__exit__ = MagicMock(return_value=None)
        from bot.handlers import cmd_devfact

        cmd_devfact(make_message(text="/devfact"))
        mock_ask.assert_called_once()
        assert "cybersecurity" in mock_ask.call_args[0][1]
        mock_send.assert_called_once()


def test_cmd_finance_with_question_includes_topic_and_disclaimer():
    with (
        patch("bot.handlers.ask_ai", return_value="Save 10%...") as mock_ask,
        patch("bot.handlers.send_reply") as mock_send,
        patch("bot.handlers.keep_typing") as mock_keep,
        patch("bot.handlers.bot"),
    ):
        mock_keep.return_value.__enter__ = MagicMock(return_value=None)
        mock_keep.return_value.__exit__ = MagicMock(return_value=None)
        from bot.handlers import cmd_finance

        msg = make_message(text="/finance how do I save")
        cmd_finance(msg)
        mock_keep.assert_called_once_with(456)
        prompt = mock_ask.call_args[0][1]
        assert "how do I save" in prompt  # question threaded in
        assert "not professional financial advice" in prompt  # safety framing
        mock_send.assert_called_once_with(msg, "Save 10%...")


def test_cmd_finance_without_question_uses_random_topic_and_disclaimer():
    with (
        patch("bot.handlers.ask_ai", return_value="Budget tip...") as mock_ask,
        patch("bot.handlers.send_reply") as mock_send,
        patch("bot.handlers.keep_typing") as mock_keep,
        patch("bot.handlers.random.choice", return_value="saving money"),
        patch("bot.handlers.bot"),
    ):
        mock_keep.return_value.__enter__ = MagicMock(return_value=None)
        mock_keep.return_value.__exit__ = MagicMock(return_value=None)
        from bot.handlers import cmd_finance

        cmd_finance(make_message(text="/finance"))
        mock_ask.assert_called_once()
        prompt = mock_ask.call_args[0][1]
        assert "saving money" in prompt  # random topic used
        assert "not professional financial advice" in prompt
        mock_send.assert_called_once()


def test_cmd_uni_with_question_threads_topic_into_prompt():
    with (
        patch("bot.handlers.ask_ai", return_value="Pick what you love!") as mock_ask,
        patch("bot.handlers.send_reply") as mock_send,
        patch("bot.handlers.keep_typing") as mock_keep,
        patch("bot.handlers.bot"),
    ):
        mock_keep.return_value.__enter__ = MagicMock(return_value=None)
        mock_keep.return_value.__exit__ = MagicMock(return_value=None)
        from bot.handlers import cmd_uni

        msg = make_message(text="/uni how do I pick a major")
        cmd_uni(msg)
        mock_keep.assert_called_once_with(456)
        assert "how do I pick a major" in mock_ask.call_args[0][1]
        mock_send.assert_called_once_with(msg, "Pick what you love!")


def test_cmd_uni_without_question_uses_random_topic():
    with (
        patch("bot.handlers.ask_ai", return_value="Study tip...") as mock_ask,
        patch("bot.handlers.send_reply") as mock_send,
        patch("bot.handlers.keep_typing") as mock_keep,
        patch("bot.handlers.random.choice", return_value="choosing a major"),
        patch("bot.handlers.bot"),
    ):
        mock_keep.return_value.__enter__ = MagicMock(return_value=None)
        mock_keep.return_value.__exit__ = MagicMock(return_value=None)
        from bot.handlers import cmd_uni

        cmd_uni(make_message(text="/uni"))
        mock_ask.assert_called_once()
        assert "choosing a major" in mock_ask.call_args[0][1]
        mock_send.assert_called_once()


# ── /roll ─────────────────────────────────────────────────────────────────────


def test_cmd_roll_reports_dice_value():
    """The roll is 1-6 and echoed in the reply. Patch randint for determinism."""
    with (
        patch("bot.handlers.random.randint", return_value=4) as mock_rand,
        patch("bot.handlers.bot") as mock_bot,
    ):
        from bot.handlers import cmd_roll

        cmd_roll(make_message(text="/roll"))
        mock_rand.assert_called_once_with(1, 6)
        assert "4" in mock_bot.send_message.call_args[0][1]


# ── /roast ────────────────────────────────────────────────────────────────────


def test_cmd_roast_uses_target_name_from_text():
    """'/roast Sam' should feed the name into the AI prompt."""
    with (
        patch("bot.handlers.ask_ai", return_value="Sam, bless your heart...") as mock_ask,
        patch("bot.handlers.bot") as mock_bot,
    ):
        from bot.handlers import cmd_roast

        cmd_roast(make_message(text="/roast Sam"))
        assert "Sam" in mock_ask.call_args[0][1]
        assert mock_bot.send_message.call_args[0][1] == "Sam, bless your heart..."


def test_cmd_roast_defaults_to_you_without_arg():
    """'/roast' with no target roasts 'you'."""
    with (
        patch("bot.handlers.ask_ai", return_value="ok") as mock_ask,
        patch("bot.handlers.bot"),
    ):
        from bot.handlers import cmd_roast

        cmd_roast(make_message(text="/roast"))
        assert "you" in mock_ask.call_args[0][1]


# ── /about ────────────────────────────────────────────────────────────────────


def test_cmd_about_with_sqlite():
    """When SQLite is configured, /about should reference SQLite."""
    with (
        patch("bot.handlers.bot") as mock_bot,
        patch("bot.handlers.ask_ai", return_value="A curious raccoon."),
        patch("bot.handlers.store", MagicMock()),
        patch("bot.handlers.HF_SPACE_ID", ""),
    ):
        from bot.handlers import cmd_about

        cmd_about(make_message())
        sent = mock_bot.send_message.call_args[0][1]
        assert "SQLite" in sent
        assert "stateless" not in sent


def test_cmd_about_includes_commit_sha_when_set():
    """When COMMIT_SHA is populated (worker booted inside a git repo),
    /about exposes a Version line so users can validate which commit is
    live."""
    with (
        patch("bot.handlers.bot") as mock_bot,
        patch("bot.handlers.ask_ai", return_value="A curious raccoon."),
        patch("bot.handlers.store", MagicMock()),
        patch("bot.handlers.HF_SPACE_ID", ""),
        patch("bot.handlers.COMMIT_SHA", "abc1234"),
    ):
        from bot.handlers import cmd_about

        cmd_about(make_message())
        sent = mock_bot.send_message.call_args[0][1]
        assert "Version: abc1234" in sent


def test_cmd_about_omits_version_line_when_sha_unknown():
    """If git rev-parse failed at boot, the Version line is dropped
    entirely rather than showing 'unknown' — clearer for the user."""
    with (
        patch("bot.handlers.bot") as mock_bot,
        patch("bot.handlers.ask_ai", return_value="A curious raccoon."),
        patch("bot.handlers.store", MagicMock()),
        patch("bot.handlers.HF_SPACE_ID", ""),
        patch("bot.handlers.COMMIT_SHA", ""),
    ):
        from bot.handlers import cmd_about

        cmd_about(make_message())
        sent = mock_bot.send_message.call_args[0][1]
        assert "Version" not in sent


def test_cmd_about_without_store():
    """When no backend is configured, /about must say stateless. Regression
    guard for the NameError that occurred when `store` was missing from
    bot.handlers' imports."""
    with (
        patch("bot.handlers.bot") as mock_bot,
        patch("bot.handlers.ask_ai", return_value="A curious raccoon."),
        patch("bot.handlers.store", None),
        patch("bot.handlers.HF_SPACE_ID", ""),
    ):
        from bot.handlers import cmd_about

        cmd_about(make_message())
        sent = mock_bot.send_message.call_args[0][1]
        assert "stateless" in sent


# ── /sha ─────────────────────────────────────────────────────────────────────


def test_cmd_sha_reports_live_commit_sha():
    with (
        patch("bot.handlers.bot") as mock_bot,
        patch("bot.handlers.COMMIT_SHA", "abc1234"),
    ):
        from bot.handlers import cmd_sha

        cmd_sha(make_message())
        mock_bot.send_message.assert_called_once_with(456, "Live SHA: abc1234")


def test_cmd_sha_reports_unknown_when_git_sha_unavailable():
    with (
        patch("bot.handlers.bot") as mock_bot,
        patch("bot.handlers.COMMIT_SHA", ""),
    ):
        from bot.handlers import cmd_sha

        cmd_sha(make_message())
        mock_bot.send_message.assert_called_once_with(456, "Live SHA: unknown")


# ── /model command ────────────────────────────────────────────────────────────


def _import_cmd_model_with_hf_enabled():
    """Re-import handlers module with HF_SPACE_ID set so cmd_model exists."""
    import importlib
    import bot.config
    import bot.handlers

    original = bot.config.HF_SPACE_ID
    bot.config.HF_SPACE_ID = "fake/space"
    # Also patch the import in handlers module (already imported via `from ... import HF_SPACE_ID`)
    bot.handlers.HF_SPACE_ID = "fake/space"
    importlib.reload(bot.handlers)
    cmd_model = getattr(bot.handlers, "cmd_model", None)
    # Restore
    bot.config.HF_SPACE_ID = original
    bot.handlers.HF_SPACE_ID = original
    return cmd_model


def test_cmd_model_no_args_shows_current():
    cmd_model = _import_cmd_model_with_hf_enabled()
    assert cmd_model is not None
    with (
        patch("bot.handlers.get_provider", return_value="main"),
        patch("bot.handlers.bot") as mock_bot,
    ):
        msg = make_message(text="/model")
        cmd_model(msg)
        sent = mock_bot.send_message.call_args[0][1]
        assert "Current provider: main" in sent
        assert "/model main" in sent
        assert "/model hf" in sent


def test_cmd_model_switch_to_hf():
    cmd_model = _import_cmd_model_with_hf_enabled()
    with (
        patch("bot.handlers.set_provider", return_value=True) as mock_set,
        patch("bot.handlers.bot") as mock_bot,
    ):
        msg = make_message(text="/model hf")
        cmd_model(msg)
        mock_set.assert_called_once_with(123, "hf")
        sent = mock_bot.send_message.call_args[0][1]
        assert "hf" in sent
        assert "Armenian" in sent


def test_cmd_model_switch_to_main():
    cmd_model = _import_cmd_model_with_hf_enabled()
    with (
        patch("bot.handlers.set_provider", return_value=True) as mock_set,
        patch("bot.handlers.bot") as mock_bot,
    ):
        msg = make_message(text="/model main")
        cmd_model(msg)
        mock_set.assert_called_once_with(123, "main")
        sent = mock_bot.send_message.call_args[0][1]
        assert "Main" in sent


def test_cmd_model_invalid_choice():
    cmd_model = _import_cmd_model_with_hf_enabled()
    with (
        patch("bot.handlers.set_provider") as mock_set,
        patch("bot.handlers.bot") as mock_bot,
    ):
        msg = make_message(text="/model bogus")
        cmd_model(msg)
        mock_set.assert_not_called()
        assert "Invalid" in mock_bot.send_message.call_args[0][1]


def test_cmd_model_redis_error_reports_failure():
    cmd_model = _import_cmd_model_with_hf_enabled()
    with (
        patch("bot.handlers.set_provider", return_value=False),
        patch("bot.handlers.bot") as mock_bot,
    ):
        msg = make_message(text="/model hf")
        cmd_model(msg)
        assert "Could not save" in mock_bot.send_message.call_args[0][1]


def test_cmd_model_not_registered_without_hf_space_id():
    """When HF_SPACE_ID is empty, cmd_model should not exist."""
    import importlib
    import bot.config
    import bot.handlers

    bot.config.HF_SPACE_ID = ""
    bot.handlers.HF_SPACE_ID = ""
    # reload() doesn't delete existing attributes, so clear it first
    if hasattr(bot.handlers, "cmd_model"):
        delattr(bot.handlers, "cmd_model")
    importlib.reload(bot.handlers)
    assert not hasattr(bot.handlers, "cmd_model")


def test_handle_message_uses_keep_typing():
    """handle_message should wrap ask_ai in the keep_typing context."""
    with (
        patch("bot.handlers.should_respond", return_value=True),
        patch("bot.handlers.is_rate_limited", return_value=False),
        patch("bot.handlers.BOT_INFO", MagicMock(username="testbot")),
        patch("bot.handlers.ask_ai", return_value="reply"),
        patch("bot.handlers.send_reply"),
        patch("bot.handlers.keep_typing") as mock_keep,
        patch("bot.handlers.bot"),
    ):
        mock_keep.return_value.__enter__ = MagicMock(return_value=None)
        mock_keep.return_value.__exit__ = MagicMock(return_value=None)
        from bot.handlers import handle_message

        msg = make_message()
        handle_message(msg)
        mock_keep.assert_called_once_with(456)
