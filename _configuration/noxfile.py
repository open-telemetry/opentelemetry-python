from nox import session


@session(python=["3.11"], reuse_venv=True)
def test(session):
    session.install(".")
    session.install("-r", "requirements.txt")

    if session.posargs:
        session.run("pytest", *session.posargs)
    else:
        session.run("pytest", "tests/test_configuration.py")
