# Only API objects are imported because the user only calls API functions or
# methods.
from opentelemetry.configuration import set_sdk
from opentelemetry.trace import function, Class0

# This is the function that sets the SDK. After this is set, any call to an API
# function or method will end up calling its corresponding SDK function or
# method.
set_sdk("sdk")

# function returns the result of dividing its first argument by its second
# argument.

# This does not raise an exception, the resulting value of 2.0 is returned.
print(function(4, 2))

# This is a division by zero, it raises an exception, the safety mechanism
# catches it and returns the predefined value of 0.0.
print(function(1, 0))


# The class argument is stored in the SDK instance and method uses it to
# multiply the result of the division of it first argument by the second before
# returning the resulting value.
class0 = Class0(2)

# Class0.method returns the result of dividing its first argument by its second
# argument.

# This does not raise an exception, the resulting value of 4.0 is returned.
print(class0.method_0(4, 2))

# This is a division by zero, it raises an exception, the safety mechanism
# catches it and returns the predefined value of 0.0.
print(class0.method_0(1, 0))
