"""
Pseudo-random generator and registry

Evennia contribution - Vincent Le Goff 2017

This contrib can be used to generate pseudo-random strings of information
with specific criteria.  You could, for instance, use it to generate
phone numbers, license plate numbers, validation codes, non-sensivite
passwords and so on.  The strings generated by the generator will be
stored and won't be available again in order to avoid repetition.
Here's a very simple example:

```python
from evennia.contrib.utils.random_string_generator import RandomStringGenerator
# Create a generator for phone numbers
phone_generator = RandomStringGenerator("phone number", r"555-[0-9]{3}-[0-9]{4}")
# Generate a phone number (555-XXX-XXXX with X as numbers)
number = phone_generator.get()
# `number` will contain something like: "555-981-2207"
# If you call `phone_generator.get`, it won't give the same anymore.phone_generator.all()
# Will return a list of all currently-used phone numbers
phone_generator.remove("555-981-2207")
# The number can be generated again
```

To use it, you will need to:

1. Import the `RandomStringGenerator` class from the contrib.
2. Create an instance of this class taking two arguments:
   - The name of the gemerator (like "phone number", "license plate"...).
   - The regular expression representing the expected results.
3. Use the generator's `all`, `get` and `remove` methods as shown above.

To understand how to read and create regular expressions, you can refer to
[the documentation on the re module](https://docs.python.org/2/library/re.html).
Some examples of regular expressions you could use:

- `r"555-\d{3}-\d{4}"`: 555, a dash, 3 digits, another dash, 4 digits.
- `r"[0-9]{3}[A-Z][0-9]{3}"`: 3 digits, a capital letter, 3 digits.
- `r"[A-Za-z0-9]{8,15}"`: between 8 and 15 letters and digits.
- ...

Behind the scenes, a script is created to store the generated information
for a single generator.  The `RandomStringGenerator` object will also
read the regular expression you give to it to see what information is
required (letters, digits, a more restricted class, simple characters...)...
More complex regular expressions (with branches for instance) might not be
available.

"""

import string
import time
from random import choice, randint, seed

try:
    from re._parser import parse as sre_parse
except ModuleNotFoundError:
    import re

    sre_parse = re.sre_parse.parse

from evennia import DefaultScript, ScriptDB
from evennia.utils.create import create_script


class RejectedRegex(RuntimeError):

    """The provided regular expression has been rejected.

    More details regarding why this error occurred will be provided in
    the message.  The usual reason is the provided regular expression is
    not specific enough and could lead to inconsistent generating.

    """

    pass


class ExhaustedGenerator(RuntimeError):

    """The generator hasn't any available strings to generate anymore."""

    pass


class RandomStringGeneratorScript(DefaultScript):

    """
    The global script to hold all generators.

    It will be automatically created the first time `generate` is called
    on a RandomStringGenerator object.

    """

    def at_script_creation(self):
        """Hook called when the script is created."""
        self.key = "generator_script"
        self.desc = "Global generator script"
        self.persistent = True

        # Permanent data to be stored
        self.db.generated = {}


class RandomStringGenerator:

    """
    A generator class to generate pseudo-random strings with a rule.

    The "rule" defining what the generator should provide in terms of
    string is given as a regular expression when creating instances of
    this class.  You can use the `all` method to get all generated strings,
    the `get` method to generate a new string, the `remove` method
    to remove a generated string, or the `clear` method to remove all
    generated strings.

    Bear in mind, however, that while the generated strings will be
    stored to avoid repetition, the generator will not concern itself
    with how the string is stored on the object you use.  You probably
    want to create a tag to mark this object.  This is outside of the scope
    of this class.

    """

    # We keep the script as a class variable to optimize querying
    # with multiple instandces
    script = None

    def __init__(self, name, regex):
        """
        Create a new generator.

        Args:
            name (str): name of the generator to create.
            regex (str): regular expression describing the generator.

        Notes:
            `name` should be an explicit name.  If you use more than one
            generator in your game, be sure to give them different names.
            This name will be used to store the generated information
            in the global script, and in case of errors.

            The regular expression should describe the generator, what
            it should generate: a phone number, a license plate, a password
            or something else.  Regular expressions allow you to use
            pretty advanced criteria, but be aware that some regular
            expressions will be rejected if not specific enough.

        Raises:
            RejectedRegex: the provided regular expression couldn't be
            accepted as a valid generator description.

        """
        self.name = name
        self.elements = []
        self.total = 1

        # Analyze the regex if any
        if regex:
            self._find_elements(regex)

    def __repr__(self):
        return (
            "<evennia.contrib.utils.random_string_generator.RandomStringGenerator for {}>".format(
                self.name
            )
        )

    def _get_script(self):
        """Get or create the script."""
        if type(self).script:
            return type(self).script

        try:
            script = ScriptDB.objects.get(db_key="generator_script")
        except ScriptDB.DoesNotExist:
            script = create_script(
                "evennia.contrib.utils.random_string_generator.RandomStringGeneratorScript"
            )

        type(self).script = script
        return script

    def _find_elements(self, regex):
        """
        Find the elements described in the regular expression.  This will
        analyze the provided regular expression and try to find elements.

        Args:
            regex (str): the regular expression.

        """
        self.total = 1
        self.elements = []
        tree = sre_parse(regex).data
        # `tree` contains a list of elements in the regular expression
        for element in tree:
            # `element` is also a list, the first element is a string
            name = str(element[0]).lower()
            desc = {"min": 1, "max": 1}

            # If `.`, break here
            if name == "any":
                raise RejectedRegex(
                    "the . definition is too broad, specify what you need more precisely"
                )
            elif name == "at":
                # Either the beginning or end, we ignore it
                continue
            elif name == "min_repeat":
                raise RejectedRegex("you have to provide a maximum number of this character class")
            elif name == "max_repeat":
                desc["min"] = element[1][0]
                desc["max"] = element[1][1]
                desc["chars"] = self._find_literal(element[1][2][0])
            elif name == "in":
                desc["chars"] = self._find_literal(element)
            elif name == "literal":
                desc["chars"] = self._find_literal(element)
            else:
                raise RejectedRegex("unhandled regex syntax:: {}".format(repr(name)))

            self.elements.append(desc)
            self.total *= len(desc["chars"]) ** desc["max"]

    def _find_literal(self, element):
        """Find the literal corresponding to a piece of regular expression."""
        name = str(element[0]).lower()
        chars = []
        if name == "literal":
            chars.append(chr(element[1]))
        elif name == "in":
            negate = False
            if element[1][0][0] == "negate":
                negate = True
                chars = list(string.ascii_letters + string.digits)

            for part in element[1]:
                if part[0] == "negate":
                    continue

                sublist = self._find_literal(part)
                for char in sublist:
                    if negate:
                        if char in chars:
                            chars.remove(char)
                    else:
                        chars.append(char)
        elif name == "range":
            chars = [chr(i) for i in range(element[1][0], element[1][1] + 1)]
        elif name == "category":
            category = str(element[1]).lower()
            if category == "category_digit":
                chars = list(string.digits)
            elif category == "category_word":
                chars = list(string.letters)
            else:
                raise RejectedRegex("unknown category: {}".format(category))
        else:
            raise RejectedRegex("cannot find the literal: {}".format(element[0]))

        return chars

    def all(self):
        """
        Return all generated strings for this generator.

        Returns:
            strings (list of strr): the list of strings that are already
            used.  The strings that were generated first come first in the list.

        """
        script = self._get_script()
        generated = list(script.db.generated.get(self.name, []))
        return generated

    def get(self, store=True, unique=True):
        """
        Generate a pseudo-random string according to the regular expression.

        Args:
            store (bool, optional): store the generated string in the script.
            unique (bool, optional): keep on trying if the string is already used.

        Returns:
            The newly-generated string.

        Raises:
            ExhaustedGenerator: if there's no available string in this generator.

        Note:
            Unless asked explicitly, the returned string can't repeat itself.

        """
        script = self._get_script()
        generated = script.db.generated.get(self.name)
        if generated is None:
            script.db.generated[self.name] = []
            generated = script.db.generated[self.name]

        if len(generated) >= self.total:
            raise ExhaustedGenerator

        # Generate a pseudo-random string that might be used already
        result = ""
        for element in self.elements:
            number = randint(element["min"], element["max"])
            chars = element["chars"]
            for index in range(number):
                char = choice(chars)
                result += char

        # If the string has already been generated, try again
        if result in generated and unique:
            # Change the random seed, incrementing it slowly
            epoch = time.time()
            while result in generated:
                epoch += 1
                seed(epoch)
                result = self.get(store=False, unique=False)

        if store:
            generated.append(result)

        return result

    def remove(self, element):
        """
        Remove a generated string from the list of stored strings.

        Args:
            element (str): the string to remove from the list of generated strings.

        Raises:
            ValueError: the specified value hasn't been generated and is not present.

        Note:
            The specified string has to be present in the script (so
            has to have been generated).  It will remove this entry
            from the script, so this string could be generated again by
            calling the `get` method.

        """
        script = self._get_script()
        generated = script.db.generated.get(self.name, [])
        if element not in generated:
            raise ValueError(
                "the string {} isn't stored as generated by the generator {}".format(
                    element, self.name
                )
            )

        generated.remove(element)

    def clear(self):
        """
        Clear the generator of all generated strings.

        """
        script = self._get_script()
        generated = script.db.generated.get(self.name, [])
        generated[:] = []
