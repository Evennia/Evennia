"""

Test the funcparser module.

"""

import time
from unittest.mock import MagicMock, patch
from ast import literal_eval
from simpleeval import simple_eval
from parameterized import parameterized
from django.test import TestCase, override_settings

from evennia.utils import funcparser, test_resources


def _test_callable(*args, **kwargs):
    kwargs.pop("funcparser", None)
    kwargs.pop("raise_errors", None)
    argstr = ", ".join(args)
    kwargstr = ""
    if kwargs:
        kwargstr = (", " if args else "") + (
            ", ".join(f"{key}={val}" for key, val in kwargs.items())
        )
    return f"_test({argstr}{kwargstr})"


def _repl_callable(*args, **kwargs):
    if args:
        return f"r{args[0]}r"
    return "rr"


def _double_callable(*args, **kwargs):
    if args:
        try:
            return int(args[0]) * 2
        except ValueError:
            pass
    return "N/A"


def _eval_callable(*args, **kwargs):
    if args:
        return simple_eval(args[0])

    return ""


def _clr_callable(*args, **kwargs):
    clr, string, *rest = args
    return f"|{clr}{string}|n"


def _typ_callable(*args, **kwargs):
    try:
        if isinstance(args[0], str):
            return type(literal_eval(args[0]))
        else:
            return type(args[0])
    except (SyntaxError, ValueError):
        return type("")


def _add_callable(*args, **kwargs):
    if len(args) > 1:
        return literal_eval(args[0]) + literal_eval(args[1])
    return ""


def _lit_callable(*args, **kwargs):
    return literal_eval(args[0])


def _lsum_callable(*args, **kwargs):
    if isinstance(args[0], (list, tuple)):
        return sum(val for val in args[0])
    return ""


_test_callables = {
    "foo": _test_callable,
    "bar": _test_callable,
    "with spaces": _test_callable,
    "repl": _repl_callable,
    "double": _double_callable,
    "eval": _eval_callable,
    "clr": _clr_callable,
    "typ": _typ_callable,
    "add": _add_callable,
    "lit": _lit_callable,
    "sum": _lsum_callable,
}


class TestFuncParser(TestCase):
    """
    Test the FuncParser class

    """

    def setUp(self):

        self.parser = funcparser.FuncParser(_test_callables)

    @parameterized.expand(
        [
            ("Test normal string", "Test normal string"),
            ("Test noargs1 $foo()", "Test noargs1 _test()"),
            ("Test noargs2 $bar() etc.", "Test noargs2 _test() etc."),
            ("Test noargs3 $with spaces() etc.", "Test noargs3 _test() etc."),
            ("Test noargs4 $foo(), $bar() and $foo", "Test noargs4 _test(), _test() and $foo"),
            ("$foo() Test noargs5", "_test() Test noargs5"),
            ("Test args1 $foo(a,b,c)", "Test args1 _test(a, b, c)"),
            ("Test args2 $bar(foo, bar,    too)", "Test args2 _test(foo, bar, too)"),
            (r"Test args3 $bar(foo, bar, '   too')", "Test args3 _test(foo, bar,    too)"),
            ("Test args4 $foo('')", "Test args4 _test()"),
            ('Test args4 $foo("")', "Test args4 _test()"),
            ("Test args5 $foo(\(\))", "Test args5 _test(())"),
            ("Test args6 $foo(\()", "Test args6 _test(()"),
            ("Test args7 $foo(())", "Test args7 _test(())"),
            ("Test args8 $foo())", "Test args8 _test())"),
            ("Test args9 $foo(=)", "Test args9 _test(=)"),
            ("Test args10 $foo(\,)", "Test args10 _test(,)"),
            ("Test args10 $foo(',')", "Test args10 _test(,)"),
            ("Test args11 $foo(()", "Test args11 $foo(()"),  # invalid syntax
            (
                "Test kwarg1 $bar(foo=1, bar='foo', too=ere)",
                "Test kwarg1 _test(foo=1, bar=foo, too=ere)",
            ),
            ("Test kwarg2 $bar(foo,bar,too=ere)", "Test kwarg2 _test(foo, bar, too=ere)"),
            ("test kwarg3 $foo(foo = bar, bar = ere )", "test kwarg3 _test(foo=bar, bar=ere)"),
            (
                r"test kwarg4 $foo(foo =\' bar \',\" bar \"= ere )",
                "test kwarg4 _test(foo=' bar ', \" bar \"=ere)",
            ),
            (
                "Test nest1 $foo($bar(foo,bar,too=ere))",
                "Test nest1 _test(_test(foo, bar, too=ere))",
            ),
            (
                "Test nest2 $foo(bar,$repl(a),$repl()=$repl(),a=b) etc",
                "Test nest2 _test(bar, rar, rr=rr, a=b) etc",
            ),
            ("Test nest3 $foo(bar,$repl($repl($repl(c))))", "Test nest3 _test(bar, rrrcrrr)"),
            (
                "Test nest4 $foo($bar(a,b),$bar(a,$repl()),$bar())",
                "Test nest4 _test(_test(a, b), _test(a, rr), _test())",
            ),
            ("Test escape1 \\$repl(foo)", "Test escape1 $repl(foo)"),
            (
                'Test escape2 "This is $foo() and $bar($bar())", $repl()',
                'Test escape2 "This is _test() and _test(_test())", rr',
            ),
            (
                "Test escape3 'This is $foo() and $bar($bar())', $repl()",
                "Test escape3 'This is _test() and _test(_test())', rr",
            ),
            (
                "Test escape4 $$foo() and $$bar(a,b), $repl()",
                "Test escape4 $foo() and $bar(a,b), rr",
            ),
            ("Test with color |r$foo(a,b)|n is ok", "Test with color |r_test(a, b)|n is ok"),
            ("Test malformed1 This is $foo( and $bar(", "Test malformed1 This is $foo( and $bar("),
            (
                "Test malformed2 This is $foo( and $bar()",
                "Test malformed2 This is $foo( and _test()",
            ),
            ("Test malformed3 $", "Test malformed3 $"),
            (
                "Test malformed4 This is $foo(a=b and $bar(",
                "Test malformed4 This is $foo(a=b and $bar(",
            ),
            (
                "Test malformed5 This is $foo(a=b, and $repl()",
                "Test malformed5 This is $foo(a=b, and rr",
            ),
            ("Test nonstr 4x2 = $double(4)", "Test nonstr 4x2 = 8"),
            ("Test nonstr 4x2 = $double(foo)", "Test nonstr 4x2 = N/A"),
            ("Test clr $clr(r, This is a red string!)", "Test clr |rThis is a red string!|n"),
            ("Test eval1 $eval(21 + 21 - 10)", "Test eval1 32"),
            ("Test eval2 $eval((21 + 21) / 2)", "Test eval2 21.0"),
            ("Test eval3 $eval(\"'21' + 'foo' + 'bar'\")", "Test eval3 21foobar"),
            (r"Test eval4 $eval(\'21\' + \'$repl()\' + \"''\" + str(10 // 2))", "Test eval4 21rr5"),
            (
                r"Test eval5 $eval(\'21\' + \'\$repl()\' + \'\' + str(10 // 2))",
                "Test eval5 21$repl()5",
            ),
            ("Test eval6 $eval(\"'$repl(a)' + '$repl(b)'\")", "Test eval6 rarrbr"),
            ("Test type1 $typ([1,2,3,4])", "Test type1 <class 'list'>"),
            ("Test type2 $typ((1,2,3,4))", "Test type2 <class 'tuple'>"),
            ("Test type3 $typ({1,2,3,4})", "Test type3 <class 'set'>"),
            ("Test type4 $typ({1:2,3:4})", "Test type4 <class 'dict'>"),
            ("Test type5 $typ(1), $typ(1.0)", "Test type5 <class 'int'>, <class 'float'>"),
            (
                "Test type6 $typ(\"'1'\"), $typ('\"1.0\"')",
                "Test type6 <class 'str'>, <class 'str'>",
            ),
            ("Test add1 $add(1, 2)", "Test add1 3"),
            ("Test add2 $add([1,2,3,4], [5,6])", "Test add2 [1, 2, 3, 4, 5, 6]"),
            ("Test literal1 $sum($lit([1,2,3,4,5,6]))", "Test literal1 21"),
            ("Test literal2 $typ($lit(1))", "Test literal2 <class 'int'>"),
            ("Test literal3 $typ($lit(1)aaa)", "Test literal3 <class 'str'>"),
            ("Test literal4 $typ(aaa$lit(1))", "Test literal4 <class 'str'>"),
            ("Test spider's thread", "Test spider's thread"),
        ]
    )
    def test_parse(self, string, expected):
        """
        Test parsing of string.

        """
        # t0 = time.time()
        # from evennia import set_trace;set_trace()
        ret = self.parser.parse(string, raise_errors=True)
        # t1 = time.time()
        # print(f"time: {(t1-t0)*1000} ms")
        self.assertEqual(expected, ret)

    def test_parse_raise(self):
        """
        Make sure error is raised if told to do so.

        """
        string = "Test malformed This is $dummy(a, b) and $bar("
        with self.assertRaises(funcparser.ParsingError):
            self.parser.parse(string, raise_errors=True)

    def test_parse_strip(self):
        """
        Test the parser's strip functionality.

        """
        string = "Test $foo(a,b, $bar()) and $repl($eval(3+2)) things"
        ret = self.parser.parse(string, strip=True)
        self.assertEqual("Test  and  things", ret)

    def test_parse_escape(self):
        """
        Test the parser's escape functionality.

        """
        string = "Test $foo(a) and $bar() and $rep(c) things"
        ret = self.parser.parse(string, escape=True)
        self.assertEqual("Test \$foo(a) and \$bar() and \$rep(c) things", ret)

    def test_parse_lit(self):
        """
        Get non-strings back from parsing.

        """
        string = "$lit(123)"

        # normal parse
        ret = self.parser.parse(string)
        self.assertEqual("123", ret)
        self.assertTrue(isinstance(ret, str))

        # parse lit
        ret = self.parser.parse_to_any(string)
        self.assertEqual(123, ret)
        self.assertTrue(isinstance(ret, int))

        ret = self.parser.parse_to_any("$lit([1,2,3,4])")
        self.assertEqual([1, 2, 3, 4], ret)
        self.assertTrue(isinstance(ret, list))

        ret = self.parser.parse_to_any("$lit(\"''\")")
        self.assertEqual("", ret)
        self.assertTrue(isinstance(ret, str))

        ret = self.parser.parse_to_any(r"$lit(\'\')")
        self.assertEqual("", ret)
        self.assertTrue(isinstance(ret, str))

        # mixing a literal with other chars always make a string
        ret = self.parser.parse_to_any(string + "aa")
        self.assertEqual("123aa", ret)
        self.assertTrue(isinstance(ret, str))

        ret = self.parser.parse_to_any("test")
        self.assertEqual("test", ret)
        self.assertTrue(isinstance(ret, str))

    def test_kwargs_overrides(self):
        """
        Test so default kwargs are added and overridden properly

        """
        # default kwargs passed on initializations
        parser = funcparser.FuncParser(_test_callables, test="foo")
        ret = parser.parse("This is a $foo() string")
        self.assertEqual("This is a _test(test=foo) string", ret)

        # override in the string itself

        ret = parser.parse("This is a $foo(test=bar,foo=moo) string")
        self.assertEqual("This is a _test(test=bar, foo=moo) string", ret)

        # parser kwargs override the other types

        ret = parser.parse("This is a $foo(test=bar,foo=moo) string", test="override", foo="bar")
        self.assertEqual("This is a _test(test=override, foo=bar) string", ret)

        # non-overridden kwargs shine through

        ret = parser.parse("This is a $foo(foo=moo) string", foo="bar")
        self.assertEqual("This is a _test(test=foo, foo=bar) string", ret)


class _DummyObj:
    def __init__(self, name):
        self.name = name

    def get_display_name(self, looker=None):
        return self.name


class TestDefaultCallables(TestCase):
    """
    Test default callables.

    """

    def setUp(self):
        from django.conf import settings

        self.parser = funcparser.FuncParser(
            {**funcparser.FUNCPARSER_CALLABLES, **funcparser.ACTOR_STANCE_CALLABLES}
        )

        self.obj1 = _DummyObj("Char1")
        self.obj2 = _DummyObj("Char2")

    @parameterized.expand(
        [
            ("Test py1 $eval('')", "Test py1 "),
        ]
    )
    def test_callable(self, string, expected):
        """
        Test callables with various input strings

        """
        ret = self.parser.parse(string, raise_errors=True)
        self.assertEqual(expected, ret)

    @parameterized.expand(
        [
            ("$You() $conj(smile) at him.", "You smile at him.", "Char1 smiles at him."),
            ("$You() $conj(smile) at $You(char1).", "You smile at You.", "Char1 smiles at Char1."),
            ("$You() $conj(smile) at $You(char2).", "You smile at Char2.", "Char1 smiles at You."),
            (
                "$You(char2) $conj(smile) at $you(char1).",
                "Char2 smile at you.",
                "You smiles at Char1.",
            ),
            (
                "$You() $conj(smile) to $pron(yourself,m).",
                "You smile to yourself.",
                "Char1 smiles to himself.",
            ),
            (
                "$You() $conj(smile) to $pron(herself).",
                "You smile to yourself.",
                "Char1 smiles to herself.",
            ),  # reverse reference
        ]
    )
    def test_conjugate(self, string, expected_you, expected_them):
        """
        Test callables with various input strings

        """
        mapping = {"char1": self.obj1, "char2": self.obj2}
        ret = self.parser.parse(
            string, caller=self.obj1, receiver=self.obj1, mapping=mapping, raise_errors=True
        )
        self.assertEqual(expected_you, ret)
        ret = self.parser.parse(
            string, caller=self.obj1, receiver=self.obj2, mapping=mapping, raise_errors=True
        )
        self.assertEqual(expected_them, ret)

    @parameterized.expand(
        [
            ("Test $pad(Hello, 20, c, -) there", "Test -------Hello-------- there"),
            (
                "Test $pad(Hello, width=20, align=c, fillchar=-) there",
                "Test -------Hello-------- there",
            ),
            ("Test $crop(This is a long test, 12)", "Test This is[...]"),
            ("Some $space(10) here", "Some            here"),
            ("Some $clr(b, blue color) now", "Some |bblue color|n now"),
            ("Some $add(1, 2) things", "Some 3 things"),
            ("Some $sub(10, 2) things", "Some 8 things"),
            ("Some $mult(3, 2) things", "Some 6 things"),
            ("Some $div(6, 2) things", "Some 3.0 things"),
            ("Some $toint(6) things", "Some 6 things"),
            ("Some $ljust(Hello, 30)", "Some Hello                         "),
            ("Some $rjust(Hello, 30)", "Some                          Hello"),
            ("Some $rjust(Hello, width=30)", "Some                          Hello"),
            ("Some $cjust(Hello, 30)", "Some             Hello             "),
            ("Some $eval(\"'-'*20\")Hello", "Some --------------------Hello"),
            ('$crop("spider\'s silk", 5)', "spide"),
        ]
    )
    def test_other_callables(self, string, expected):
        """
        Test default callables.

        """
        ret = self.parser.parse(string, raise_errors=True)
        self.assertEqual(expected, ret)

    def test_random(self):
        string = "$random(1,10)"
        for i in range(100):
            ret = self.parser.parse_to_any(string, raise_errors=True)
            self.assertTrue(1 <= ret <= 10)

        string = "$random()"
        for i in range(100):
            ret = self.parser.parse_to_any(string, raise_errors=True)
            self.assertTrue(0 <= ret <= 1)

        string = "$random(1.0, 3.0)"
        for i in range(100):
            ret = self.parser.parse_to_any(string, raise_errors=True)
            self.assertTrue(isinstance(ret, float))
            self.assertTrue(1.0 <= ret <= 3.0)

    def test_randint(self):
        string = "$randint(1.0, 3.0)"
        ret = self.parser.parse_to_any(string, raise_errors=True)
        self.assertTrue(isinstance(ret, int))
        self.assertTrue(1.0 <= ret <= 3.0)

    def test_nofunc(self):
        self.assertEqual(
            self.parser.parse("as$382ewrw w we w werw,|44943}"),
            "as$382ewrw w we w werw,|44943}",
        )

    def test_incomplete(self):
        self.assertEqual(
            self.parser.parse("testing $blah{without an ending."),
            "testing $blah{without an ending.",
        )

    def test_single_func(self):
        self.assertEqual(
            self.parser.parse("this is a test with $pad(centered, 20) text in it."),
            "this is a test with       centered       text in it.",
        )

    def test_nested(self):
        self.assertEqual(
            self.parser.parse(
                "this $crop(is a test with $pad(padded, 20) text in $pad(pad2, 10) a crop, 80)"
            ),
            "this is a test with        padded        text in    pad2    a crop",
        )

    def test_escaped(self):
        self.assertEqual(
            self.parser.parse(
                "this should be $pad('''escaped,''' and '''instead,''' cropped $crop(with a long,5) text., 80)"
            ),
            "this should be                    escaped, and instead, cropped with  text.                    ",
        )

    def test_escaped2(self):
        raw_str = 'this should be $pad("""escaped,""" and """instead,""" cropped $crop(with a long,5) text., 80)'
        expected = "this should be                    escaped, and instead, cropped with  text.                    "
        result = self.parser.parse(raw_str)
        self.assertEqual(
            result,
            expected,
        )


class TestCallableSearch(test_resources.BaseEvenniaTest):
    """
    Test the $search(query) callable

    """

    def setUp(self):
        super().setUp()
        self.parser = funcparser.FuncParser(funcparser.SEARCHING_CALLABLES)

    def test_search_obj(self):
        """
        Test searching for an object

        """
        string = "$search(Char)"
        expected = self.char1

        ret = self.parser.parse(string, caller=self.char1, return_str=False, raise_errors=True)
        self.assertEqual(expected, ret)

    def test_search_account(self):
        """
        Test searching for an account

        """
        string = "$search(TestAccount, type=account)"
        expected = self.account

        ret = self.parser.parse(string, caller=self.char1, return_str=False, raise_errors=True)
        self.assertEqual(expected, ret)

    def test_search_script(self):
        """
        Test searching for a script

        """
        string = "$search(Script, type=script)"
        expected = self.script

        ret = self.parser.parse(string, caller=self.char1, return_str=False, raise_errors=True)
        self.assertEqual(expected, ret)

    def test_search_obj_embedded(self):
        """
        Test searching for an object - embedded in str

        """
        string = "This is $search(Char) the guy."
        expected = "This is " + str(self.char1) + " the guy."

        ret = self.parser.parse(string, caller=self.char1, return_str=False, raise_errors=True)
        self.assertEqual(expected, ret)
