from opentelemetry.sdk.error_handler import GlobalErrorHandler

# ZeroDivisionError to be handled by ErrorHandler0
with GlobalErrorHandler():
    1 / 0

print()

# IndexError to be handled by ErrorHandler1
with GlobalErrorHandler():
    [1][2]

print()

# KeyError to be handled by ErrorHandler1
with GlobalErrorHandler():
    {1: 2}[2]

print()

# AssertionError to be handled by DefaultErrorHandler
with GlobalErrorHandler():
    assert False

print()

# No error raised
with GlobalErrorHandler():
    print("No error raised")
