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

    def _find_dec(self, token):
        if "scope" in token.keys():
            scope = token["scope"]
            while scope is not None:
                for pos, item in scope.symbols.items():
                    if item["value"] == token["value"] and (
                        item["type"] in ["VAR", "FUNCTION", "PARAMETER"]
                    ):
                        return item
                scope = scope.parent
        else:
            return None

    def construct_jump_table(self):
        for token in self.all_tokens:
            if token["type"] == "ID":
                # import pdb; pdb.set_trace()
                dec = self._find_dec(token)
                if dec is not None:
                    printlog(
                        f"Declaration of ({token['value']}, {token['position']}) is at {dec['position']}"
                    )
                    line, column_start = token["position"]
                    column_end = column_start + token["len"]
                    if line not in self.jump_table.keys():
                        self.jump_table[line] = {}
                    current_line = self.jump_table[line]
                    current_line[(column_start, column_end)] = dec["position"]
                else:
                    printlog(
                        f"Declaration of ({token['value']}, {token['position']}) not found"
                    )
        return self.jump_table

    def add_file(self, id):
        if isinstance(id, dict):
            self.imported_files.append(id["value"])
        elif isinstance(id, str):
            self.imported_files.append(id)
        else:
            raise "Invalid type. Expected str or dict, got %s" % type(id)

    def add_symbol(self, *tokens):
        self.scopes.add_symbol(*tokens)

    def parse(self) -> None:
        r"""
        Parses the file.
        """
        with open(self.file_path) as f:
            data = f.read()
        self.ast = self.parser.parse(data, self.lexer)

    def __repr__(self) -> str:
        return f"AST: {self.ast}\n\nTokens: {self.lexer.states.all_tokens}\n\nScopes: {self.scopes}\n\nImported files: {self.imported_files}"


def run_parser(file_path):
    file = FileParsed(file_path)
    file.parse()
    printlog(file)
    jumptable = file.construct_jump_table()
    # print(jumptable)


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
    import os

    filepath = os.path.join(os.path.dirname(__file__), "sample.asy")
    run_parser(filepath)
    run_test_on_base()
