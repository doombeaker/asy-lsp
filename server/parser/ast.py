from tkinter.tix import Tree
from .asylexer import *
from .asyparser import *
from .utils import traverse_dir_files, printlog

from .ply.yacc import yacc


class FileParsed(object):
    r"""
    The representation of a file that has been parsed.
    """

    def __init__(self, file: str) -> None:
        self.file_path = file
        self.imported_files = []
        self.scopes = Scopes()
        self.lexer = lex()
        self.lexer.states = self
        self.all_tokens = []
        self.ast = None
        self.parser = yacc(start="file")
        self.parser.states = self
        self.jump_table = {}

    def find_definiton(self, line, column):
        if line not in self.jump_table.keys():
            return None
        current_line_dict = self.jump_table[line]
        for key in current_line_dict.keys():
            if key[0] <= column <= key[1]:
                return current_line_dict[key]
        return None

    def construct_jump_table(self):
        for token in self.all_tokens:
            if token["type"] == "ID":
                dec = self.scopes._find_dec(token)
                if dec is not None:
                    printlog("Declaration of %s is at %s" % (token, dec["position"]))
                    line, column_start = token["position"]
                    column_end = column_start + token["len"]
                    if line not in self.jump_table.keys():
                        self.jump_table[line] = {}
                    current_line = self.jump_table[line]
                    current_line[(column_start, column_end)] = dec["position"]
                else:
                    printlog("Declaration of %s not found" % token)
        return self.jump_table

    def add_file(self, id):
        if isinstance(id, dict):
            self.imported_files.append(id["value"])
        elif isinstance(id, str):
            self.imported_files.append(id)
        else:
            raise "Invalid type. Expected str or dict, got %s" % type(id)

    def add_symbol(self, *tokens):
        for token in tokens:
            self.scopes.add_symbol(token["position"], token)

    def parse(self) -> None:
        r"""
        Parses the file.
        """
        with open(self.file_path) as f:
            data = f.read()
        self.ast = self.parser.parse(data, self.lexer)

    def __repr__(self) -> str:
        return f"AST: {self.ast}\n\nTokens: {self.lexer.states.all_tokens}\n\nScopes: {self.scopes}\n\nImported files: {self.imported_files}"


class Scopes(object):
    def __init__(self) -> None:
        self.scopes = []
        self.current_scope = None
        self.unused_scopes = []
        self.depth_symbols = {}

        self.scope_depth = 0  # depth of global scope is 0
        self.push_scope(Scope(depth=self.scope_depth))
        self.global_scope = self.current_scope

    def add_symbol(self, position, symbol):
        if self.current_scope is None:
            self.global_scope.add_symbol(position, symbol)
        self.current_scope.add_symbol(position, symbol)
        self._add_to_depth_symbols(self.scope_depth, symbol)

    def push_scope(self, scope):
        self.scopes.append(scope)
        self.current_scope = scope

    def pop_scope(self):
        self.unused_scopes.append(self.scopes.pop())
        if len(self.scopes) > 0:
            self.current_scope = self.scopes[-1]
        else:
            self.current_scope = None

    def revert_scope(self):
        self.scopes.append(self.unused_scopes.pop())
        self.current_scope = self.scopes[-1]

    def _find_dec(self, token):
        begin_depth = token["depth"]
        while begin_depth >= 0:
            for symbol in self.depth_symbols[begin_depth]:
                if symbol["value"] == token["value"]:
                    return symbol
            begin_depth -= 1
        return None

    def _add_to_depth_symbols(self, depth, value):
        depth_symbols = self.depth_symbols
        value["depth"] = depth
        if value["type"] == "PARAMETER" or value["type"] == "PARA_TYPE":
            value[
                "depth"
            ] += 1  # depth of parameter is 1 more than the depth of the function
        key = value["depth"]
        if key not in depth_symbols.keys():
            depth_symbols[key] = []
        depth_symbols[key].append(value)

        if type(value["type"]) is not str:
            value["type"] = "ID"

    def __repr__(self):
        return f"\nself.scopes:\n{self.scopes}\nself.unused_scoes:\n{self.unused_scopes}\nself.global_scope:{self.global_scope}"


def run_parser(file_path):
    file = FileParsed(file_path)
    file.parse()
    printlog(file)
    jumptable = file.construct_jump_table()
    print(jumptable)


def run_lex(filepath):
    # Build the lexer object
    from .asylexer import lex

    lexer = lex()
    with open(filepath) as f:
        data = f.read()
    lexer.input(data)
    while True:
        token = lexer.token()
        if not token:
            break
        printlog(token)


def run_test_on_base():
    ROOTDIR = r"C:\mygithub\asymptote\base"
    pathlist, _ = traverse_dir_files(ROOTDIR, ext=[".asy"])
    for item in pathlist:
        run_lex_and_parser(item)


def run_lex_and_parser(filepath):
    print("-----Parsing file: %s ----\n" % filepath)
    run_lex(filepath)
    run_parser(filepath)


if __name__ == "__main__":
    # run_test_on_base()
