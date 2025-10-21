def test_self_policy_guard():
    from repoq.cli_meta import meta_self
    try:
        meta_self(2, out="/tmp/meta.json")  # level 2 ok
    except SystemExit as e:
        assert False, "Level 2 should be allowed"
