from valkey_agentic_demo.launcher import userdata


def test_userdata_marker():
    data = userdata.render().strip().splitlines()
    assert data[-1] == "### USERDATA OK ###"
