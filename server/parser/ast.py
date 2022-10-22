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
        if hasattr(token, "scope"):
            scope = token["scope"]
            while scope.parent is not None:
                for pos, item in scope.items():
                    if item["value"] == token["value"] and (
                        item["type"] in ["ID", "FUNCTION", "PARAMETER"]):
                        return item
                scope = scope.parent
        else:
            return None
        


    def construct_jump_table(self):
        for token in self.all_tokens:
            if token["type"] == "ID":
                #import pdb; pdb.set_trace()
                dec = self._find_dec(token)
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


#   符号表
# 1. 有缩进关系的 Block，是父子关系
# 2. 并列关系的 Block， 是兄弟关系

# { // B1                             B1
#     { // B2                        /  \
#                                  B2  -> B3
#     }                                    \
#                                          B4
#     { // B3
#         {  // B4
#
#         }
#     }
# }

class Scope(object):
    def __init__(
        self,
        start: tuple = (1, 1),
        end: tuple = (-1, -1),
        depth=-1,
        parent=None,
        prev=None,
        next=None,
    ) -> None:
        self.symbols = {}
        self.start = start
        self.end = end
        self.depth = depth

        # link the scopes
        self.parent = parent  # parent scope
        self.prev = prev  # prev block scope in same depth
        self.next = next  # next block scope in same depth

        if self.prev:
            self.prev.next = self

    def add_symbol(self, *tokens):
        for token in tokens:
            if token is not None:
                self.symbols[token["position"]] = token
    
    def pop_symbol(self, *tokens):
        for token in tokens:
            if token is not None:
                self.symbols.pop(token["position"])

    def is_in_scope(self, pos: tuple):
        if (
            self.start[0] <= pos[0] <= self.end[0]
            and self.start[1] <= pos[1] <= self.end[1]
        ):
            return True

        return False

    def __repr__(self) -> str:
        return f"<Scope DEPTH:{self.depth} ({self.start}~{self.end}) SYMBOLS: {[(v['position'],v['value'], v['type']) for v in self.symbols.values()]}>"

class Scopes(object):
    def __init__(self) -> None:
        self.scopes = []
        self.current_scope = None # the top scope
        self.last_scopes = {} # the last scope at each depth ( right after '}' )
        self.unused_scopes = []
        self.depth_symbols = {}

        self.scope_depth = 0  # depth of global scope is 0
        self.last_scopes[self.scope_depth] = None
        self.push_scope(Scope(depth=self.scope_depth))
        self.global_scope = self.current_scope

    def add_symbol(self, *tokens):
        if self.current_scope is None:
            self.global_scope.add_symbol(*tokens)
        self.current_scope.add_symbol(*tokens)
        #self._add_to_depth_symbols(self.scope_depth, symbol)

    def push_scope(self, scope):
        self.scopes.append(scope)
        self.current_scope = scope

    def pop_scope(self):
        self.unused_scopes.append(self.scopes.pop())
        if len(self.scopes) > 0:
            self.current_scope = self.scopes[-1]
        else:
            self.current_scope = None

    # def revert_scope(self):
    #     self.scopes.append(self.unused_scopes.pop())
    #     self.current_scope = self.scopes[-1]

    # def _add_to_depth_symbols(self, depth, value):
    #     depth_symbols = self.depth_symbols
    #     value["depth"] = depth
    #     if value["type"] == "PARAMETER" or value["type"] == "PARA_TYPE":
    #         value[
    #             "depth"
    #         ] += 1  # depth of parameter is 1 more than the depth of the function
    #     key = value["depth"]
    #     if key not in depth_symbols.keys():
    #         depth_symbols[key] = []
    #     depth_symbols[key].append(value)

    #     if type(value["type"]) is not str:
    #         value["type"] = "ID"

    def __repr__(self):
        return f"\nself.scopes:\n{self.scopes}\nself.unused_scoes:\n{self.unused_scopes}\nself.global_scope:{self.global_scope}"


def run_parser(file_path):
    file = FileParsed(file_path)
    file.parse()
    printlog(file)
    jumptable = file.construct_jump_table()
    #print(jumptable)


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
    # run_test_on_base()
