from nox import session


def test(session, number):
    session.install("-r", f"test-requirements-{number}.txt")
    session.install(".")

    if session.posargs:
        session.run("pytest", *session.posargs)
    else:
        session.run("pytest", "-rf", "tests")


@session(python=["3.8", "3.9", "3.10", "3.11"], reuse_venv=True)
def test_0(session):
    test(session, 0)


@session(python=["3.8", "3.9", "3.10", "3.11"], reuse_venv=True)
def test_1(session):
    test(session, 1)


@session(python=["3.8"], reuse_venv=True)
def lint(session):
    session.install("-r", "test-requirements-1.txt")
    session.install("-r", "lint-requirements.txt")
    session.install(".")

    session.run("black", "src")
    session.run("isort", "src")
    session.run("pylint", "src")
