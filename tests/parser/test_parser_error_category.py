#  Copyright (c) 2025 Tobias Erbsland - https://erbsland.dev
#  SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest

from erbsland.conf.error import Error, ErrorCategory
from erbsland.conf.parser import loads


unexpected_end_cases = [
    pytest.param("#comment\r", ErrorCategory.UNEXPECTED_END, id="0"),
    pytest.param("[", ErrorCategory.UNEXPECTED_END, id="1"),
    pytest.param("[\n", ErrorCategory.SYNTAX, id="2"),
    pytest.param("[\r\n", ErrorCategory.SYNTAX, id="3"),
    pytest.param("[main", ErrorCategory.UNEXPECTED_END, id="4"),
    pytest.param("[main\n", ErrorCategory.SYNTAX, id="5"),
    pytest.param("[main\r\n", ErrorCategory.SYNTAX, id="6"),
    pytest.param("[main ", ErrorCategory.UNEXPECTED_END, id="7"),
    pytest.param("[main \n", ErrorCategory.SYNTAX, id="8"),
    pytest.param("[main \r\n", ErrorCategory.SYNTAX, id="9"),
    pytest.param("[main.", ErrorCategory.UNEXPECTED_END, id="10"),
    pytest.param("[main.\n", ErrorCategory.SYNTAX, id="11"),
    pytest.param("[main.\r\n", ErrorCategory.SYNTAX, id="12"),
    pytest.param("[main. ", ErrorCategory.UNEXPECTED_END, id="13"),
    pytest.param("[main. \n", ErrorCategory.SYNTAX, id="14"),
    pytest.param("[main. \r\n", ErrorCategory.SYNTAX, id="15"),
    pytest.param("[main.sub", ErrorCategory.UNEXPECTED_END, id="16"),
    pytest.param("[main.sub\n", ErrorCategory.SYNTAX, id="17"),
    pytest.param("[main.sub\r\n", ErrorCategory.SYNTAX, id="18"),
    pytest.param("[main.sub ", ErrorCategory.UNEXPECTED_END, id="19"),
    pytest.param("[main.sub \n", ErrorCategory.SYNTAX, id="20"),
    pytest.param("[main.sub \r\n", ErrorCategory.SYNTAX, id="21"),
    pytest.param("[main.sub.", ErrorCategory.UNEXPECTED_END, id="22"),
    pytest.param("[main.sub.\n", ErrorCategory.SYNTAX, id="23"),
    pytest.param("[main.sub.\r\n", ErrorCategory.SYNTAX, id="24"),
    pytest.param("[main.sub. ", ErrorCategory.UNEXPECTED_END, id="25"),
    pytest.param("[main.sub. \n", ErrorCategory.SYNTAX, id="26"),
    pytest.param("[main.sub. \r\n", ErrorCategory.SYNTAX, id="27"),
    pytest.param('[main."', ErrorCategory.UNEXPECTED_END, id="28"),
    pytest.param('[main."\n', ErrorCategory.SYNTAX, id="29"),
    pytest.param('[main."\r\n', ErrorCategory.SYNTAX, id="30"),
    pytest.param('[main."sub', ErrorCategory.UNEXPECTED_END, id="31"),
    pytest.param('[main."sub\n', ErrorCategory.SYNTAX, id="32"),
    pytest.param('[main."sub\r\n', ErrorCategory.SYNTAX, id="33"),
    pytest.param('[main."sub"', ErrorCategory.UNEXPECTED_END, id="34"),
    pytest.param('[main."sub"\n', ErrorCategory.SYNTAX, id="35"),
    pytest.param('[main."sub"\r\n', ErrorCategory.SYNTAX, id="36"),
    pytest.param('[main."sub" ', ErrorCategory.UNEXPECTED_END, id="37"),
    pytest.param('[main."sub" \n', ErrorCategory.SYNTAX, id="38"),
    pytest.param('[main."sub" \r\n', ErrorCategory.SYNTAX, id="39"),
    pytest.param('[main."sub".', ErrorCategory.UNEXPECTED_END, id="40"),
    pytest.param('[main."sub".\n', ErrorCategory.SYNTAX, id="41"),
    pytest.param('[main."sub".\r\n', ErrorCategory.SYNTAX, id="42"),
    pytest.param('[main."sub". ', ErrorCategory.UNEXPECTED_END, id="43"),
    pytest.param('[main."sub". \n', ErrorCategory.SYNTAX, id="44"),
    pytest.param('[main."sub". \r\n', ErrorCategory.SYNTAX, id="45"),
    pytest.param("[main]\nvalue", ErrorCategory.UNEXPECTED_END, id="46"),
    pytest.param("[main]\nvalue\n", ErrorCategory.SYNTAX, id="47"),
    pytest.param("[main]\nvalue    ", ErrorCategory.UNEXPECTED_END, id="48"),
    pytest.param("[main]\nvalue # comment", ErrorCategory.SYNTAX, id="49"),
    pytest.param("[main]\nvalue:", ErrorCategory.UNEXPECTED_END, id="50"),
    pytest.param("[main]\nvalue: # comment", ErrorCategory.UNEXPECTED_END, id="51"),
    pytest.param("[main]\nvalue=", ErrorCategory.UNEXPECTED_END, id="52"),
    pytest.param("[main]\nvalue= # comment", ErrorCategory.UNEXPECTED_END, id="53"),
    pytest.param("[main]\nvalue   :", ErrorCategory.UNEXPECTED_END, id="54"),
    pytest.param("[main]\nvalue   : # comment", ErrorCategory.UNEXPECTED_END, id="55"),
    pytest.param("[main]\nvalue:\n", ErrorCategory.UNEXPECTED_END, id="56"),
    pytest.param("[main]\nvalue: # comment\n", ErrorCategory.UNEXPECTED_END, id="57"),
    pytest.param("[main]\nvalue=\n", ErrorCategory.UNEXPECTED_END, id="58"),
    pytest.param("[main]\nvalue= # comment\n", ErrorCategory.UNEXPECTED_END, id="59"),
    pytest.param('[main]\n"', ErrorCategory.UNEXPECTED_END, id="60"),
    pytest.param('[main]\n"text ', ErrorCategory.UNEXPECTED_END, id="61"),
    pytest.param('[main]\n"text value', ErrorCategory.UNEXPECTED_END, id="62"),
    pytest.param('[main]\n"text value"', ErrorCategory.UNEXPECTED_END, id="63"),
    pytest.param('[main]\n"text value"\n', ErrorCategory.SYNTAX, id="64"),
    pytest.param('[main]\n"text value"    ', ErrorCategory.UNEXPECTED_END, id="65"),
    pytest.param('[main]\n"text value" # comment', ErrorCategory.SYNTAX, id="66"),
    pytest.param('[main]\n"text value":', ErrorCategory.UNEXPECTED_END, id="67"),
    pytest.param('[main]\n"text value": # comment', ErrorCategory.UNEXPECTED_END, id="68"),
    pytest.param('[main]\n"text value"   :', ErrorCategory.UNEXPECTED_END, id="69"),
    pytest.param('[main]\n"text value"   : # comment', ErrorCategory.UNEXPECTED_END, id="70"),
    pytest.param('[main]\n"text value":\n', ErrorCategory.UNEXPECTED_END, id="71"),
    pytest.param('[main]\n"text value": # comment\n', ErrorCategory.UNEXPECTED_END, id="72"),
    pytest.param('[main]\nvalue: "', ErrorCategory.UNEXPECTED_END, id="73"),
    pytest.param('[main]\nvalue: "\n', ErrorCategory.SYNTAX, id="74"),
    pytest.param('[main]\nvalue: "text', ErrorCategory.UNEXPECTED_END, id="75"),
    pytest.param('[main]\nvalue: "text\n', ErrorCategory.SYNTAX, id="76"),
    pytest.param("[main]\nvalue: `", ErrorCategory.UNEXPECTED_END, id="77"),
    pytest.param("[main]\nvalue: `\n", ErrorCategory.SYNTAX, id="78"),
    pytest.param("[main]\nvalue: `text", ErrorCategory.UNEXPECTED_END, id="79"),
    pytest.param("[main]\nvalue: `text\n", ErrorCategory.SYNTAX, id="80"),
    pytest.param("[main]\nvalue: /", ErrorCategory.UNEXPECTED_END, id="81"),
    pytest.param("[main]\nvalue: /\n", ErrorCategory.SYNTAX, id="82"),
    pytest.param("[main]\nvalue: /text", ErrorCategory.UNEXPECTED_END, id="83"),
    pytest.param("[main]\nvalue: /text\n", ErrorCategory.SYNTAX, id="84"),
    pytest.param("[main]\nvalue: <", ErrorCategory.UNEXPECTED_END, id="85"),
    pytest.param("[main]\nvalue: <\n", ErrorCategory.SYNTAX, id="86"),
    pytest.param("[main]\nvalue: <hex", ErrorCategory.UNEXPECTED_END, id="87"),
    pytest.param("[main]\nvalue: <hex\n", ErrorCategory.SYNTAX, id="88"),
    pytest.param("[main]\nvalue: <hex:", ErrorCategory.UNEXPECTED_END, id="89"),
    pytest.param("[main]\nvalue: <hex:\n", ErrorCategory.SYNTAX, id="90"),
    pytest.param("[main]\nvalue: <0102", ErrorCategory.UNEXPECTED_END, id="91"),
    pytest.param("[main]\nvalue: <0102\n", ErrorCategory.SYNTAX, id="92"),
    pytest.param('[main]\nvalue: """', ErrorCategory.UNEXPECTED_END, id="93"),
    pytest.param('[main]\nvalue: """\n    text', ErrorCategory.UNEXPECTED_END, id="94"),
    pytest.param('[main]\nvalue: """\n    text\n', ErrorCategory.UNEXPECTED_END, id="95"),
    pytest.param("[main]\nvalue: ```", ErrorCategory.UNEXPECTED_END, id="96"),
    pytest.param("[main]\nvalue: ```\n    text", ErrorCategory.UNEXPECTED_END, id="97"),
    pytest.param("[main]\nvalue: ```\n    text\n", ErrorCategory.UNEXPECTED_END, id="98"),
    pytest.param("[main]\nvalue: ///", ErrorCategory.UNEXPECTED_END, id="99"),
    pytest.param("[main]\nvalue: ///\n    text", ErrorCategory.UNEXPECTED_END, id="100"),
    pytest.param("[main]\nvalue: ///\n    text\n", ErrorCategory.UNEXPECTED_END, id="101"),
    pytest.param("[main]\nvalue: <<<", ErrorCategory.UNEXPECTED_END, id="102"),
    pytest.param("[main]\nvalue: <<<\n    0102", ErrorCategory.UNEXPECTED_END, id="103"),
    pytest.param("[main]\nvalue: <<<\n    0102\n", ErrorCategory.UNEXPECTED_END, id="104"),
    pytest.param("[main]\nvalue: 100'", ErrorCategory.UNEXPECTED_END, id="105"),
    pytest.param("[main]\nvalue: 0x", ErrorCategory.UNEXPECTED_END, id="106"),
    pytest.param("[main]\nvalue: 0x1000'", ErrorCategory.UNEXPECTED_END, id="107"),
    pytest.param("[main]\nvalue: 0x\n", ErrorCategory.SYNTAX, id="108"),
    pytest.param("[main]\nvalue: 0b", ErrorCategory.UNEXPECTED_END, id="109"),
    pytest.param("[main]\nvalue: 0b1111'", ErrorCategory.UNEXPECTED_END, id="110"),
    pytest.param("[main]\nvalue: 0b\n", ErrorCategory.SYNTAX, id="111"),
    pytest.param("[main]\nvalue: 1, 2,", ErrorCategory.UNEXPECTED_END, id="112"),
    pytest.param("[main]\nvalue: 1, 2, ", ErrorCategory.UNEXPECTED_END, id="113"),
    pytest.param("[main]\nvalue: 1, 2,\n", ErrorCategory.SYNTAX, id="114"),
    pytest.param("[main]\nvalue: 100e", ErrorCategory.UNEXPECTED_END, id="115"),
    pytest.param("[main]\nvalue: 0.1e+", ErrorCategory.UNEXPECTED_END, id="116"),
    pytest.param("[main]\nvalue: 100e\n", ErrorCategory.SYNTAX, id="117"),
    pytest.param("[main]\nvalue: 0.1e+\n", ErrorCategory.SYNTAX, id="118"),
    pytest.param("[main]\nvalue: 2025-", ErrorCategory.UNEXPECTED_END, id="119"),
    pytest.param("[main]\nvalue: 2025-0", ErrorCategory.UNEXPECTED_END, id="120"),
    pytest.param("[main]\nvalue: 2025-08", ErrorCategory.UNEXPECTED_END, id="121"),
    pytest.param("[main]\nvalue: 2025-08-", ErrorCategory.UNEXPECTED_END, id="122"),
    pytest.param("[main]\nvalue: 2025-08-0", ErrorCategory.UNEXPECTED_END, id="123"),
    pytest.param("[main]\nvalue: 2025-08-01t", ErrorCategory.UNEXPECTED_END, id="124"),
    pytest.param("[main]\nvalue: 2025-08-01 12:", ErrorCategory.UNEXPECTED_END, id="125"),
    pytest.param("[main]\nvalue: 2025-08-01 12:0", ErrorCategory.UNEXPECTED_END, id="126"),
    pytest.param("[main]\nvalue: 2025-08-01 12:05:", ErrorCategory.UNEXPECTED_END, id="127"),
    pytest.param("[main]\nvalue: 2025-08-01 12:05:3", ErrorCategory.UNEXPECTED_END, id="128"),
    pytest.param("[main]\nvalue: 2025-08-01 12:05:34+", ErrorCategory.UNEXPECTED_END, id="129"),
    pytest.param("[main]\nvalue: 2025-08-01 12:05:34+0", ErrorCategory.UNEXPECTED_END, id="130"),
    pytest.param("[main]\nvalue: 2025-08-01 12:05:34+01:", ErrorCategory.UNEXPECTED_END, id="131"),
    pytest.param("[main]\nvalue: 2025-08-01 12:05:34+01:3", ErrorCategory.UNEXPECTED_END, id="132"),
    pytest.param("[main]\nvalue: 12:", ErrorCategory.UNEXPECTED_END, id="133"),
    pytest.param("[main]\nvalue: 12:0", ErrorCategory.UNEXPECTED_END, id="134"),
    pytest.param("[main]\nvalue: 12:05:", ErrorCategory.UNEXPECTED_END, id="135"),
    pytest.param("[main]\nvalue: 12:05:3", ErrorCategory.UNEXPECTED_END, id="136"),
    pytest.param("[main]\nvalue: 12:05:34+", ErrorCategory.UNEXPECTED_END, id="137"),
    pytest.param("[main]\nvalue: 12:05:34+0", ErrorCategory.UNEXPECTED_END, id="138"),
    pytest.param("[main]\nvalue: 12:05:34+01:", ErrorCategory.UNEXPECTED_END, id="139"),
    pytest.param("[main]\nvalue: 12:05:34+01:3", ErrorCategory.UNEXPECTED_END, id="140"),
    pytest.param("[main]\nvalue: 2025-\n", ErrorCategory.SYNTAX, id="141"),
    pytest.param("[main]\nvalue: 2025-0\n", ErrorCategory.SYNTAX, id="142"),
    pytest.param("[main]\nvalue: 2025-08\n", ErrorCategory.SYNTAX, id="143"),
    pytest.param("[main]\nvalue: 2025-08-\n", ErrorCategory.SYNTAX, id="144"),
    pytest.param("[main]\nvalue: 2025-08-0\n", ErrorCategory.SYNTAX, id="145"),
    pytest.param("[main]\nvalue: 2025-08-01t\n", ErrorCategory.SYNTAX, id="146"),
    pytest.param("[main]\nvalue: 2025-08-01 12:\n", ErrorCategory.SYNTAX, id="147"),
    pytest.param("[main]\nvalue: 2025-08-01 12:0\n", ErrorCategory.SYNTAX, id="148"),
    pytest.param("[main]\nvalue: 2025-08-01 12:05:\n", ErrorCategory.SYNTAX, id="149"),
    pytest.param("[main]\nvalue: 2025-08-01 12:05:3\n", ErrorCategory.SYNTAX, id="150"),
    pytest.param("[main]\nvalue: 2025-08-01 12:05:34+\n", ErrorCategory.SYNTAX, id="151"),
    pytest.param("[main]\nvalue: 2025-08-01 12:05:34+0\n", ErrorCategory.SYNTAX, id="152"),
    pytest.param("[main]\nvalue: 2025-08-01 12:05:34+01:\n", ErrorCategory.SYNTAX, id="153"),
    pytest.param("[main]\nvalue: 2025-08-01 12:05:34+01:3\n", ErrorCategory.SYNTAX, id="154"),
    pytest.param("[main]\nvalue: 12:\n", ErrorCategory.SYNTAX, id="155"),
    pytest.param("[main]\nvalue: 12:0\n", ErrorCategory.SYNTAX, id="156"),
    pytest.param("[main]\nvalue: 12:05:\n", ErrorCategory.SYNTAX, id="157"),
    pytest.param("[main]\nvalue: 12:05:3\n", ErrorCategory.SYNTAX, id="158"),
    pytest.param("[main]\nvalue: 12:05:34+\n", ErrorCategory.SYNTAX, id="159"),
    pytest.param("[main]\nvalue: 12:05:34+0\n", ErrorCategory.SYNTAX, id="160"),
    pytest.param("[main]\nvalue: 12:05:34+01:\n", ErrorCategory.SYNTAX, id="161"),
    pytest.param("[main]\nvalue: 12:05:34+01:3\n", ErrorCategory.SYNTAX, id="162"),
]

unsupported_cases = [
    pytest.param('@version: "0.9"\n', ErrorCategory.UNSUPPORTED, id="0"),
    pytest.param("@version: `0.9`\n", ErrorCategory.SYNTAX, id="1"),
    pytest.param("@version: `1.0`\n", ErrorCategory.SYNTAX, id="2"),
    pytest.param('@version: """\n    1.0\n    """\n', ErrorCategory.SYNTAX, id="3"),
    pytest.param("@version: 1\n", ErrorCategory.SYNTAX, id="4"),
    pytest.param("@version: 2\n", ErrorCategory.SYNTAX, id="5"),
    pytest.param('@features: "abcde"\n', ErrorCategory.UNSUPPORTED, id="6"),
    pytest.param('@features: "core abcde"\n', ErrorCategory.UNSUPPORTED, id="7"),
    pytest.param("@features: `core`\n", ErrorCategory.SYNTAX, id="8"),
    pytest.param('@features: """\n    core\n    """\n', ErrorCategory.SYNTAX, id="9"),
    pytest.param("[main]\nvalue: <base64: 01234>\n", ErrorCategory.UNSUPPORTED, id="10"),
    pytest.param("[main]\nvalue: <none$: 01234>\n", ErrorCategory.SYNTAX, id="11"),
    pytest.param("[main]\nvalue: <<<base64\n    01234\n    >>>\n", ErrorCategory.UNSUPPORTED, id="12"),
    pytest.param("[main]\nvalue: <<<none$\n    01234>\n    >>>\n", ErrorCategory.SYNTAX, id="13"),
]

indentation_cases = [
    pytest.param('[main]\nv: """\n  t\n t\n  """\n', ErrorCategory.INDENTATION, id="0"),
    pytest.param('[main]\nv: """\n  t\n_ t\n  """\n', ErrorCategory.SYNTAX, id="1"),
    pytest.param('[main]\nv: """\n\tt\n        t\n\t"""\n', ErrorCategory.INDENTATION, id="2"),
    pytest.param('[main]\nv:\n  """\n t  """\n', ErrorCategory.INDENTATION, id="3"),
    pytest.param("[main]\nv: ```\n  t\n t\n  ```\n", ErrorCategory.INDENTATION, id="4"),
    pytest.param("[main]\nv: ```\n  t\n_ t\n  ```\n", ErrorCategory.SYNTAX, id="5"),
    pytest.param("[main]\nv: ```\n\tt\n        t\n\t```\n", ErrorCategory.INDENTATION, id="6"),
    pytest.param("[main]\nv:\n  ```\n t  ```\n", ErrorCategory.INDENTATION, id="7"),
    pytest.param("[main]\nv: <<<\n  00\n 00\n  >>>\n", ErrorCategory.INDENTATION, id="8"),
    pytest.param("[main]\nv: <<<\n  00\n_ 00\n  >>>\n", ErrorCategory.SYNTAX, id="9"),
    pytest.param("[main]\nv: <<<\n\t00\n        00\n\t>>>\n", ErrorCategory.INDENTATION, id="10"),
    pytest.param("[main]\nv:\n  <<<\n 00  >>>\n", ErrorCategory.INDENTATION, id="11"),
    pytest.param("[main]\nv:\n  * 1\n * 2\n", ErrorCategory.INDENTATION, id="12"),
]

overlong_line1 = "0" * 4000 + "\n"
exact_4000_line2 = "0" * 3999 + "\n"
over_long_name1 = "[" + "a" * 101 + "_]\n"
over_long_name2 = "[" + "a" * 100 + "_]\n"
exact_100_name = "[" + "a" * 99 + "_]\n"
oversized_name_path1 = "[a.b.c.d.e.f.g.h.i.j.k]\n"
oversized_name_path2 = "[a.b.c.d.e.f.g.h.i.j.k._]\n"
name_path_with_syntax_error = "[a.b.c.d.e.f.g.h.i.j._]\n"
limit_cases = [
    pytest.param(overlong_line1, ErrorCategory.LIMIT_EXCEEDED, id="0"),
    pytest.param(exact_4000_line2, ErrorCategory.SYNTAX, id="1"),
    pytest.param(over_long_name1, ErrorCategory.LIMIT_EXCEEDED, id="2"),
    pytest.param(over_long_name2, ErrorCategory.LIMIT_EXCEEDED, id="3"),
    pytest.param(exact_100_name, ErrorCategory.SYNTAX, id="4"),
    pytest.param(oversized_name_path1, ErrorCategory.LIMIT_EXCEEDED, id="5"),
    pytest.param(oversized_name_path2, ErrorCategory.LIMIT_EXCEEDED, id="6"),
    pytest.param(name_path_with_syntax_error, ErrorCategory.SYNTAX, id="7"),
]


class TestParserErrorCategory:
    @pytest.mark.parametrize("text, expected", unexpected_end_cases)
    def test_unexpected_end_vs_syntax_error(self, text: str, expected: ErrorCategory) -> None:
        with pytest.raises(Error) as exc_info:
            loads(text)
        assert exc_info.value.category == expected

    @pytest.mark.parametrize("text, expected", unsupported_cases)
    def test_unsupported_vs_syntax_error(self, text: str, expected: ErrorCategory) -> None:
        with pytest.raises(Error) as exc_info:
            loads(text)
        assert exc_info.value.category == expected

    @pytest.mark.parametrize("text, expected", indentation_cases)
    def test_indentation_vs_syntax_error(self, text: str, expected: ErrorCategory) -> None:
        with pytest.raises(Error) as exc_info:
            loads(text)
        assert exc_info.value.category == expected

    def test_character_vs_syntax_error(self) -> None:
        test_document = (
            "# Comment\n"
            "[main]\n"
            "v1: true\n"
            "v2: 123'456\n"
            "v3:\n\t0xab'01\n"
            "v4:\n 0b11'00#c\n"
            "v5: 12kb #c\n"
            "v6: 12 kb\t\n"
            "v7: 123'456 \n"
            'v8: "t"\n'
            "v9: 0.7e+2\t#c\n"
            "v10: 01:02:03.123+01:30\n"
            "v11: 2025-01-02\n"
            "v12: 2025-01-02 01:02:03.123+01:30\n"
            "v13: 2025-01-02t01:02:03.123+01:30\n"
            "v14: 12h\n"
            "v15: 5 years\n"
            "v16: `c`\n"
            "v17: <01>\n"
            'v18: """\n t\n """\n'
            'v19: """ #c\n t\n """ #c\n'
            "v20: ```\n c\n ```\n"
            "v21: <<<\n 01\n >>>\n"
            "#c"
        )
        loads(test_document)
        for i in range(len(test_document) + 1):
            mutated = test_document[:i] + "\b" + test_document[i:]
            with pytest.raises(Error) as exc_info:
                loads(mutated)
            assert exc_info.value.category == ErrorCategory.CHARACTER

    @pytest.mark.parametrize("text, expected", limit_cases)
    def test_limit_exceeded_vs_syntax_error(self, text: str, expected: ErrorCategory) -> None:
        with pytest.raises(Error) as exc_info:
            loads(text)
        assert exc_info.value.category == expected
