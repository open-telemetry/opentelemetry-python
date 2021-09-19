[This](https://github.com/open-telemetry/opentelemetry-python/pull/1887#discussion_r710248608)
conversation made me look deeper into what is considered to be a public,
protected and private attribute in Python. So far I have been under the
impression that there is no official way to define a protected attribute but
apparently there is at least a convention on how to do it:

-. `public_attribute`
-. `_protected_attribute`
-. `__private_attribute`

These are some places where I have found this convention:

https://towardsdatascience.com/private-protected-attributes-in-python-demystified-once-and-for-all-9456d4e56414
https://www.tutorialsteacher.com/python/public-private-protected-modifiers
https://www.geeksforgeeks.org/protected-variable-in-python/

None of them is part of the official documentation. The closest I have found is
this:

https://www.python.org/dev/peps/pep-0008/#method-names-and-instance-variables

I wish that part of the PEP was written with stronger specificity, it does not
explicitly say that protected attributes are to be prefixed by a single
underscore but it looks like it can be deduced from its wording.

The word "protected" is only mentioned once in that PEP, wich uses the term
"subclass API" to refer to the concept of protected in other languages. It
then goes to say that attributes that should not be part of the subclass API
should be named with two leading underscores.

Anyways, I think we have found at least one use case where using this
convention would be convenient. At least I would like to have a way to separate
from public, protected and private so I suggest we follow that convention in
our project.

What about module-level symbols?
--------------------------------

So far I have only referred to 



Investigate if __all__ has an effect on what is documented by Sphinx. If it
causes Sphinx not to document something then it is great because it can help
us objectively define what is our public api
