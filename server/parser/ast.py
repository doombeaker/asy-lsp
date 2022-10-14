from tkinter.tix import Tree
from .asylexer import *
from .asyparser import *

from .ply.yacc import yacc

DEBUG = False


def printlog(*args, **kwargs):
    global DEBUG
    if DEBUG:
        print("----LOG----", *args, **kwargs)
    else:
        pass


class FileParsed(object):
    r"""
    The representation of a file that has been parsed.
    """

    def __init__(self, file: str) -> None:
        self.file_path = file
        self.imported_files = []
        self.scopes = Scopes()
        self.lexer = lex()
        self.lexer.all_tokens = []
        self.ast = None
        self.parser = yacc(start="file")
        self.parser.states = self

    def add_file(self, id):
        if isinstance(id, dict):
            self.imported_files.append(id["value"])
        elif isinstance(id, str):
            self.imported_files.append(id)
        else:
            raise "Invalid type. Expected str or dict, got %s" % type(id)

    def parse(self) -> None:
        r"""
        Parses the file.
        """
        with open(self.file_path) as f:
            data = f.read()
        self.ast = self.parser.parse(data, self.lexer)

    def __repr__(self) -> str:
        return f"AST: {self.ast}\n\nTokens: {self.lexer.all_tokens}\n\nScopes: {self.scopes}\n\nImported files: {self.imported_files}"


class Scopes(object):
    def __init__(self) -> None:
        self.scopes = []
        self.current_scope = None
        self.unused_scopes = []

        self.push_scope(Scope())
        self.global_scope = self.current_scope

    def add_symbol(self, position, symbol):
        if self.current_scope is None:
            self.global_scope.add_symbol(position, symbol)
        self.current_scope.add_symbol(position, symbol)

    def push_scope(self, scope):
        self.scopes.append(scope)
        self.current_scope = scope

    def pop_scope(self):
        self.unused_scopes.append(self.scopes.pop())
        if len(self.scopes) > 0:
            self.current_scope = self.scopes[-1]
        else:
            self.current_scope = None

    def __repr__(self):
        return (
            f"\nself.scopes:\n{self.scopes}\nself.unused_scoes:\n{self.unused_scopes}"
        )


class Scope(object):
    def __init__(self, start: tuple = (1, 1), end: tuple = (-1, -1)) -> None:
        self.symbols = {}
        self.start = start
        self.end = end

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
        return f"Scope(({self.start}~{self.end}),{self.symbols})"


def run_parser(file_path):
    file = FileParsed(file_path)
    file.parse()
    printlog(file)


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


def traverse_dir_files(root_dir, ext=None):
    """
    列出文件夹中的文件, 深度遍历
    :param root_dir: 根目录
    :param ext: 后缀名
    :param is_sorted: 是否排序，耗时较长
    :return: [文件路径列表, 文件名称列表]
    """
    names_list = []
    paths_list = []
    for parent, _, fileNames in os.walk(root_dir):
        for name in fileNames:
            if name.startswith('.'):  # 去除隐藏文件
                continue
            if ext:  # 根据后缀名搜索
                if name.endswith(tuple(ext)):
                    names_list.append(name)
                    paths_list.append(os.path.join(parent, name))
            else:
                names_list.append(name)
                paths_list.append(os.path.join(parent, name))
    if not names_list:  # 文件夹为空
        return paths_list, names_list
    return paths_list, names_list

def run_test_on_base():
    ROOTDIR=r"C:\mygithub\asymptote\base"
    pathlist, _ = traverse_dir_files(ROOTDIR, ext=[".asy"])
    for item in pathlist:
        run_lex_and_parser(item)

def run_lex_and_parser(filepath):
    global DEBUG
    DEBUG = False
    print("-----Parsing file: %s ----\n" % filepath)
    run_lex(filepath)
    run_parser(filepath)

if __name__ == "__main__":
    import os
    filepath = r"C:\mygithub\asy-lsp\server\parser\sample.asy"
    run_lex_and_parser(filepath)

    run_test_on_base()

# 符号表生成的逻辑：
# 1. 找到 type id，把 type 加入到符号表；把 id 加入到符号表
# 2. 在 stmts 中找到 id，如果 id 已经在符号表中，关联已有的符号
