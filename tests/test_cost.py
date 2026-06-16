import threading

from househunt import cost


def test_known_model_cost_exact():
    # 1M in + 1M out of gpt-5.1-codex-mini = $0.25 + $2.00
    t = cost.CostTracker()
    t.add("gpt-5.1-codex-mini", 1_000_000, 1_000_000)
    s = t.summary()
    assert s["calls"] == 1
    assert abs(s["cost_usd"] - 2.25) < 1e-6


def test_accumulates_across_calls():
    t = cost.CostTracker()
    t.add("gpt-4.1-nano", 1_000_000, 0)      # $0.10
    t.add("gpt-4.1-nano", 0, 1_000_000)      # $0.40
    assert abs(t.summary()["cost_usd"] - 0.50) < 1e-6
    assert t.summary()["calls"] == 2


def test_unknown_model_tracks_tokens_but_not_cost():
    t = cost.CostTracker()
    t.add("mystery-model", 1000, 500)
    s = t.summary()
    assert s["input_tokens"] == 1000
    assert s["output_tokens"] == 500
    assert s["cost_usd"] == 0.0
    assert s["unpriced_calls"] == 1


def test_price_lookup_case_insensitive():
    assert cost.price_for("MiniMax-Text-01") == (0.20, 1.10)
    assert cost.price_for("minimax-text-01") == (0.20, 1.10)
    assert cost.price_for("nope") is None


def test_cost_usd_helper():
    assert abs(cost.cost_usd("gpt-5.4", 1_000_000, 1_000_000) - 17.50) < 1e-6
    assert cost.cost_usd("unknown", 100, 100) is None


def test_cost_tracker_thread_safe():
    t = cost.CostTracker()
    def work():
        for _ in range(100):
            t.add("gpt-4.1-nano", 1000, 1000)
    threads = [threading.Thread(target=work) for _ in range(20)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    s = t.summary()
    assert s["calls"] == 2000
    assert s["input_tokens"] == 2_000_000
    assert s["output_tokens"] == 2_000_000
