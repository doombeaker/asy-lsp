from .ply.lex import lex


class Scope(object):
    def __init__(self, start: tuple = (1, 1), end: tuple = (-1, -1), depth=-1) -> None:
        self.symbols = {}
        self.start = start
        self.end = end
        self.depth = depth

    def add_symbol(self, position, symbol):
        self.symbols[position] = symbol

    def is_symbol_in_scope(self, symbol):
        for pos, sym in self.symbols.items():
            if sym["value"] == symbol["value"]:
                self.add_symbol(symbol["position"], symbol)
                symbol["position"] = sym["position"]
                symbol["type"] = sym["type"]
                return True
        return False

    def is_in_scope(self, pos: tuple):
        if (
            self.start[0] <= pos[0] <= self.end[0]
            and self.start[1] <= pos[1] <= self.end[1]
        ):
            return True

        return False

    def __repr__(self) -> str:
        return f"<Scope DEPTH:{self.depth} ({self.start}~{self.end}) SYMBOLS: {self.symbols}>"


def _find_column(input, token):
    line_start = input.rfind("\n", 0, token.lexpos) + 1
    return (token.lexpos - line_start) + 1


# --- Tokenizer

# asymptote keywords

_keywords = (
    "and",
    "controls",
    "tension",
    "atleast",
    "curl",
    "if",
    "else",
    "while",
    "for",
    "do",
    "return",
    "break",
    "continue",
    "struct",
    "typedef",
    "new",
    "access",
    "import",
    "unravel",
    "from",
    "include",
    "quote",
    "static",
    "public",
    "private",
    "restricted",
    "this",
    "explicit",
)

keywords = dict((k, k.upper()) for k in _keywords)
keywords["static"] = "MODIFIER"
keywords["public"] = "PERM"
keywords["private"] = "PERM"
keywords["restricted"] = "PERM"
keywords["return"] = "RETURN_"

# All tokens must be named in advance.
tokens = (
    "ID",
    "SELFOP",
    "DOTS",
    "COLONS",
    "DASHES",
    "INCR",
    "LONGDASH",
    "CONTROLS",
    "TENSION",
    "ATLEAST",
    "CURL",
    "COR",
    "CAND",
    "BAR",
    "AMPERSAND",
    "EQ",
    "NEQ",
    "LT",
    "LE",
    "GT",
    "GE",
    "CARETS",
    "OPERATOR",
    "ASSIGN",
    "AND",
    "ELLIPSIS",
    "ACCESS",
    "UNRAVEL",
    "IMPORT",
    "INCLUDE",
    "FROM",
    "QUOTE",
    "STRUCT",
    "TYPEDEF",
    "NEW",
    "IF",
    "ELSE",
    "WHILE",
    "DO",
    "FOR",
    "BREAK",
    "CONTINUE",
    "RETURN_",
    "THIS",
    "EXPLICIT",
    "LIT",
    "STRING",
    "PERM",
    "MODIFIER",
)

literals = [
    ",",
    ":",
    ";",
    "(",
    ")",
    "[",
    "]",
    "{",
    "}",
    "+",
    "-",
    "/",
    "*",
    "#",
    "%",
    "^",
    "?",
    ".",
]

# block comment
def t_COMMENT(t):
    r"/\*(.|\n)*?\*/"
    t.lexer.lineno += t.value.count("\n")


# line comment
def t_CPPCOMMENT(t):
    r"//.*\n"
    t.lexer.lineno += 1
    t.type = "COMMENT"


def t_CPPCOMMENTEND(t):
    r"//.*[^\n]"
    t.type = "COMMENT"


t_ignore = " \t"
t_ASSIGN = "="

# Operators
t_LT = r"<"
t_LE = r"<="
t_GT = r">"
t_GE = r">="
t_EQ = r"=="


def t_OPERATOR_EXMARK(t):
    r"!="
    t.type = "NEQ"
    return t


t_OPERATOR = r"!|<<|>>|\$|\$\$|\@|\@\@|~|<>"

# Draw operators
t_CARETS = r"\^\^"
t_COLONS = r"::"
t_DOTS = r"\.\."
t_DASHES = r"--"
t_LONGDASH = r"---"
t_CAND = r"&&"
t_COR = r"\|\|"
t_INCR = r"\+\+"
t_BAR = r"\|"

t_SELFOP = r"\+=|-=|\*=|/=|\#=|%=|^="


def t_POW(t):
    r"\*\*"
    t.type = "^"
    return t


t_AMPERSAND = r"&"

# Delimiters
t_ELLIPSIS = r"\.\.\."


def t_LIT(t):
    r"([0-9]*\.[0-9]+)|([0-9]+\.[0-9]*)|([0-9]*\.*[0-9]+e[-+]*[0-9]+)|([0-9]+\.[0-9]*e[-+]*[0-9]+)|([0-9]+)"
    t.value = float(t.value)
    return t


def t_operatorID(t):
    r"operator([ \t])*((---|--|==|!=|<=|>=|&|\||\^\^|\.\.|::|\+\+|<<|>>|$|$$|@|@@|<>|[-+*/#%^!<>~])|[a-zA-Z_][a-zA-Z_0-9]*)"
    line = t.lexer.lineno
    column = _find_column(t.lexer.lexdata, t)
    t.type = "ID"
    t.value = {
        "value": t.value,
        "position": (line, column),
        "len": len(t.value),
        "type": "ID",
    }
    if hasattr(t.lexer, "all_tokens"):
        t.lexer.states.all_tokens.append(t.value)
    return t


def t_ID(t):
    r"[a-zA-Z_][a-zA-Z_0-9]*"

    line = t.lexer.lineno
    column = _find_column(t.lexer.lexdata, t)
    t.type = keywords.get(t.value, "ID")  # Check for reserved words
    t.value = {
        "value": t.value,
        "position": (line, column),
        "len": len(t.value),
        "type": "ID",
    }
    if hasattr(t.lexer, "states"):
        t.value["depth"] = t.lexer.states.scopes.scope_depth
        t.lexer.states.all_tokens.append(t.value)
    return t


def t_lbrace(t):
    r"\{"
    line = t.lexer.lineno
    column = _find_column(t.lexer.lexdata, t)
    t.type = "{"
    t.value = {
        "value": t.value,
        "position": (line, column),
        "len": len(t.value),
        "type": None,
    }
    if hasattr(t.lexer, "states"):
        scopes = t.lexer.states.scopes
        scopes.scope_depth += 1
        scopes.push_scope(Scope(start=(line, column), depth=scopes.scope_depth))
        t.lexer.states.all_tokens.append(t.value)
    return t


def t_rbrace(t):
    r"\}"
    line = t.lexer.lineno
    column = _find_column(t.lexer.lexdata, t)
    t.type = "}"
    t.value = {
        "value": t.value,
        "position": (line, column),
        "len": len(t.value),
        "type": None,
    }
    if hasattr(t.lexer, "states"):
        scopes = t.lexer.states.scopes
        scopes.scope_depth -= 1
        scopes.current_scope.end = (line, column)
        scopes.pop_scope()
        t.lexer.states.all_tokens.append(t.value)
    return t


t_STRING = r"(\"(\\.|[^\"\\])*\")|(\'(\\.|[^\'\\])*\')"


# Ignored token with an action associated with it
def t_newline(t):
    r"\n+"
    t.lexer.lineno += t.value.count("\n")


# Error handler for illegal characters
def t_error(t):
    print(f"Illegal character {t.value[0]!r}, line:{t.lexer.lineno}")
