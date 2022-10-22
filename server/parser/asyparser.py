from msilib.schema import Error
from .ply.yacc import yacc
from .utils import printlog


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
        self.current_scope = None  # the top scope
        self.last_scopes = {}  # the last scope at each depth ( right after '}' )
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
        # self._add_to_depth_symbols(self.scope_depth, symbol)

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


precedence = [
    ("right", "ASSIGN", "SELFOP"),
    ("right", "?", ":"),
    ("left", "COR"),
    ("left", "CAND"),
    ("left", "BAR"),
    ("left", "AMPERSAND"),
    ("left", "EQ", "NEQ"),
    ("left", "LT", "LE", "GT", "GE"),
    ("left", "OPERATOR"),
    ("left", "CARETS"),
    ("left", "JOIN_PREC", "DOTS", "COLONS", "DASHES", "INCR", "LONGDASH"),
    ("left", "DIRTAG", "CONTROLS", "TENSION", "ATLEAST", "AND"),
    ("left", "CURL", "{", "}"),
    ("left", "+", "-"),
    ("left", "*", "/", "%", "#", "LIT"),
    ("left", "UNARY"),
    ("right", "^"),
    ("left", "EXP_IN_PARENS_RULE"),
    ("left", "(", ")"),
    ("right", "ELSE"),
]


def p_file_1(p):
    """file : fileblock"""
    printlog("fileblock", *p[1:])
    p[0] = p[1]
    # { absyntax::root = $1; }


def p_fileblock_1(p):
    """fileblock :"""
    printlog("fileblock-empty", *p[1:])
    p[0] = {"rule": "fileblock", "list": []}
    # { $$ = new file(lexerPos(), false); }


def p_fileblock_2(p):
    """fileblock : fileblock runnable"""
    printlog("fileblock-runnable", *p[1:])
    p[0] = p[1]
    p[0]["list"].append(p[2])
    # { $$ = $1; $$->add($2); }


def p_bareblock_1(p):
    """bareblock :"""
    printlog("bareblock-empty,scope:", p.parser.states.scopes.current_scope)
    p[0] = p.parser.states.scopes.current_scope


def p_bareblock_2(p):
    """bareblock : bareblock runnable"""
    p[0] = p.parser.states.scopes.current_scope
    # { $$ = $1; $$->add($2); }


def p_name_1(p):
    """name : ID"""
    printlog("name-ID", *p[1:])
    p[1]["scope"] = p.parser.states.scopes.current_scope
    p[0] = p[1]

    p.parser.states.scopes.current_scope.add_symbol(p[1])
    # { $$ = new simpleName($1.pos, $1.sym); }


def p_name_2(p):
    """name : name '.' ID"""
    printlog("name-name-ID", *p[1:])
    p[3]["value"] = ".".join([p[1]["value"], p[3]["value"]])
    p[3]["type"] = p[1]

    p[0] = p[3]

    p.parser.states.add_symbol(p[1])
    # { $$ = new qualifiedName($2, $1, $3.sym); }


def p_name_3(p):
    """name : '%'"""
    printlog("name-%")
    # { $$ = new simpleName($1.pos,
    #                                   symbol::trans("operator answer")); }


def p_runnable_1(p):
    """runnable : dec"""
    printlog("runnable-dec", *p[1:])
    p[0] = p[1]
    # { $$ = $1; }


def p_runnable_2(p):
    """runnable : stm"""
    printlog("runnable-stm", *p[1:])
    p[0] = p[1]
    # { $$ = $1; }


def p_runnable_3(p):
    """runnable : modifiers dec"""
    # { $$ = new modifiedRunnable($1->getPos(), $1, $2); }


def p_runnable_4(p):
    """runnable : modifiers stm"""
    # { $$ = new modifiedRunnable($1->getPos(), $1, $2); }


def p_modifiers_1(p):
    """modifiers : MODIFIER"""
    # { $$ = new modifierList($1.pos); $$->add($1.val); }


def p_modifiers_2(p):
    """modifiers : PERM"""
    # { $$ = new modifierList($1.pos); $$->add($1.val); }


def p_modifiers_3(p):
    """modifiers : modifiers MODIFIER"""
    # { $$ = $1; $$->add($2.val); }


def p_modifiers_4(p):
    """modifiers : modifiers PERM"""
    # { $$ = $1; $$->add($2.val); }


def p_dec_1(p):
    """dec : vardec"""
    # { $$ = $1; }


def p_dec_2(p):
    """dec : fundec"""
    # { $$ = $1; }


def p_dec_3(p):
    """dec : typedec"""
    # { $$ = $1; }


def p_dec_4(p):
    """dec : ACCESS stridpairlist ';'"""
    # { $$ = new accessdec($1, $2); }


def p_dec_5(p):
    """dec : FROM name UNRAVEL idpairlist ';'"""
    printlog("FROM-NAME-UNRAVEL-IDPAIRLIST")
    # { $$ = new unraveldec($1, $2, $4); }


def p_dec_6(p):
    """dec : FROM name UNRAVEL '*' ';'"""
    printlog("FROM-NAME-UNRAVEL-ALL")
    # { $$ = new unraveldec($1, $2, WILDCARD); }


def p_dec_7(p):
    """dec : UNRAVEL name ';'"""
    # { $$ = new unraveldec($1, $2, WILDCARD); }


def p_dec_8(p):
    """dec : FROM strid ACCESS idpairlist ';'"""
    # { $$ = new fromaccessdec($1, $2.sym, $4); }


def p_dec_9(p):
    """dec : FROM strid ACCESS '*' ';'"""
    # { $$ = new fromaccessdec($1, $2.sym, WILDCARD); }


def p_dec_10(p):
    """dec : IMPORT stridpair ';'"""
    printlog("IMPORT-stridpair", *p[1:])
    p[0] = p[2]
    # { $$ = new importdec($1, $2); }


def p_dec_11(p):
    """dec : INCLUDE ID ';'"""
    # { $$ = new includedec($1, $2.sym); }


def p_dec_12(p):
    """dec : INCLUDE STRING ';'"""
    # { $$ = new includedec($1, $2->getString()); }


def p_idpair_1(p):
    """idpair : ID"""
    # { $$ = new idpair($1.pos, $1.sym); }


def p_idpair_2(p):
    """idpair : ID ID ID"""
    # { $$ = new idpair($1.pos, $1.sym, $2.sym , $3.sym); }


def p_idpairlist_1(p):
    """idpairlist : idpair"""
    # { $$ = new idpairlist(); $$->add($1); }


def p_idpairlist_2(p):
    """idpairlist : idpairlist ',' idpair"""
    # { $$ = $1; $$->add($3); }


def p_strid_1(p):
    """strid : ID"""

    p[0] = p[1]
    # { $$ = $1; }


def p_strid_2(p):
    """strid : STRING"""
    p[0] = p[1]
    # { $$.pos = $1->getPos();
    #                      $$.sym = symbol::literalTrans($1->getString()); }


def p_stridpair_1(p):
    """stridpair : ID"""
    p[1]["type"] = "MODULE"
    p[0] = p[1]

    p.parser.states.add_symbol(p[1])
    # { $$ = new idpair($1.pos, $1.sym); }


def p_stridpair_2(p):
    """stridpair : strid ID ID"""
    p[1]["type"] = "MODULE"
    p[3]["type"] = p[1]
    p[0] = {"rule": "stridpair-id-id", "list": [p[1], p[3]]}

    # add to symbole table
    p.parser.states.add_symbol(p[1], p[3])
    # { $$ = new idpair($1.pos, $1.sym, $2.sym , $3.sym); }


def p_stridpairlist_1(p):
    """stridpairlist : stridpair"""
    p[0] = p[1]
    # { $$ = new idpairlist(); $$->add($1); }


def p_stridpairlist_2(p):
    """stridpairlist : stridpairlist ',' stridpair"""
    p[0] = p[1]
    p[0]["list"].append(p[3])
    # { $$ = $1; $$->add($3); }


def p_vardec_1(p):
    """vardec : barevardec ';'"""
    p[0] = p[1]
    # { $$ = $1; }


def p_barevardec_1(p):
    """barevardec : type decidlist"""
    printlog(
        "barevardec", *p[1:], "current scope", p.parser.states.scopes.current_scope
    )
    p[1]["type"] = "TYPE"
    for item in p[2]:
        item["type"] = "VAR"
        p.parser.states.add_symbol(item)
    # { $$ = new vardec($1->getPos(), $1, $2); }

    p.parser.states.add_symbol(p[1])


def p_type_1(p):
    """type : celltype"""
    p[0] = p[1]
    # { $$ = $1; }


def p_type_2(p):
    """type : name dims"""
    p[0] = p[1]
    # { $$ = new arrayTy($1, $2); }


def p_celltype_1(p):
    """celltype : name"""
    p[0] = p[1]
    # { $$ = new nameTy($1); }


def p_dims_1(p):
    """dims : '[' ']'"""
    # { $$ = new dimensions($1); }


def p_dims_2(p):
    """dims : dims '[' ']'"""
    # { $$ = $1; $$->increase(); }


def p_dimexps_1(p):
    """dimexps : '[' exp ']'"""
    # { $$ = new explist($1); $$->add($2); }


def p_dimexps_2(p):
    """dimexps : dimexps '[' exp ']'"""
    # { $$ = $1; $$->add($3); }


def p_decidlist_1(p):
    """decidlist : decid"""
    p[0] = [p[1]]
    # { $$ = new decidlist($1->getPos()); $$->add($1); }


def p_decidlist_2(p):
    """decidlist : decidlist ',' decid"""
    p[0] = p[1]
    p[0].append(p[3])
    # { $$ = $1; $$->add($3); }


def p_decid_1(p):
    """decid : decidstart"""
    p[0] = p[1]
    # { $$ = new decid($1->getPos(), $1); }


def p_decid_2(p):
    """decid : decidstart ASSIGN varinit"""
    p[0] = p[1]
    # { $$ = new decid($1->getPos(), $1, $3); }


def p_decidstart_1(p):
    """decidstart : ID"""
    p[0] = p[1]
    # { $$ = new decidstart($1.pos, $1.sym); }


def p_decidstart_2(p):
    """decidstart : ID dims"""
    p[0] = p[1]
    # { $$ = new decidstart($1.pos, $1.sym, $2); }


def p_decidstart_3(p):
    """decidstart : ID '(' ')'"""
    p[1]["type"] = "FUNCTION"
    p[0] = p[1]
    # { $$ = new fundecidstart($1.pos, $1.sym, 0,
    #                                             new formals($2)); }


def p_decidstart_4(p):
    """decidstart : ID '(' formals ')'"""
    p[1]["type"] = "FUNCTION"
    p[0] = p[1]
    # { $$ = new fundecidstart($1.pos, $1.sym, 0, $3); }


def p_varinit_1(p):
    """varinit : exp"""
    # { $$ = $1; }


def p_varinit_2(p):
    """varinit : arrayinit"""
    # { $$ = $1; }


def p_block_begin(p):
    """block_begin : '{'"""
    scopes = p.parser.states.scopes
    # save last scope
    if scopes.scope_depth not in scopes.last_scopes.keys():
        scopes.last_scopes[scopes.scope_depth] = None
    prev = scopes.last_scopes[scopes.scope_depth]

    # create new scope
    scopes.scope_depth += 1
    new_scope = Scope(
        start=p[1]["position"],
        depth=scopes.scope_depth,
        parent=scopes.current_scope,
        prev=prev,
        next=None,
    )
    scopes.push_scope(new_scope)


def p_block_end(p):
    """block_end : '}'"""
    # update last scope in the same level
    scopes = p.parser.states.scopes
    scopes.scope_depth -= 1
    scopes.current_scope.end = p[1]["position"]
    scopes.last_scopes[scopes.scope_depth] = scopes.current_scope
    scopes.pop_scope()


def p_block_1(p):
    """block : block_begin bareblock block_end"""
    p[0] = p[2]
    # { $$ = $2; }


def p_arrayinit_1(p):
    """arrayinit : '{' '}'"""
    # { $$ = new arrayinit($1); }


def p_arrayinit_2(p):
    """arrayinit : '{' ELLIPSIS varinit '}'"""
    # { $$ = new arrayinit($1); $$->addRest($3); }


def p_arrayinit_3(p):
    """arrayinit : '{' basearrayinit '}'"""
    # { $$ = $2; }


def p_arrayinit_4(p):
    """arrayinit : '{' basearrayinit ELLIPSIS varinit '}'"""
    # { $$ = $2; $$->addRest($4); }


def p_basearrayinit_1(p):
    """basearrayinit : ','"""
    # { $$ = new arrayinit($1); }


def p_basearrayinit_2(p):
    """basearrayinit : varinits"""
    # { $$ = $1; }


def p_basearrayinit_3(p):
    """basearrayinit : varinits ','"""
    # { $$ = $1; }


def p_varinits_1(p):
    """varinits : varinit"""
    # { $$ = new arrayinit($1->getPos());
    # 		     $$->add($1);}


def p_varinits_2(p):
    """varinits : varinits ',' varinit"""
    # { $$ = $1; $$->add($3); }


def p_formals_1(p):
    """formals : formal"""
    p[0] = [p[1]]
    # { $$ = new formals($1->getPos()); $$->add($1); }


def p_formals_2(p):
    """formals : ELLIPSIS formal"""
    p[0] = [p[1]]
    # { $$ = new formals($1); $$->addRest($2); }


def p_formals_3(p):
    """formals : formals ',' formal"""
    p[0] = p[1]
    p[0].append(p[3])
    # { $$ = $1; $$->add($3); }


def p_formals_4(p):
    """formals : formals ELLIPSIS formal"""
    p[0] = p[1]
    p[0].append(p[3])
    # { $$ = $1; $$->addRest($3); }


def p_explicitornot_1(p):
    """explicitornot : EXPLICIT"""
    # { $$ = true; }


def p_explicitornot_2(p):
    """explicitornot :"""
    # { $$ = false; }


def p_formal_1(p):
    """formal : explicitornot type"""
    p[0] = p[2]
    p[2]["type"] = "PARA_TYPE"
    p[0] = (p[2], None)
    # { $$ = new formal($2->getPos(), $2, 0, 0, $1, 0); }


def p_formal_2(p):
    """formal : explicitornot type decidstart"""
    p[2]["type"] = "PARA_TYPE"
    p[3]["type"] = "PARAMETER"
    p[0] = (p[2], p[3])
    # { $$ = new formal($2->getPos(), $2, $3, 0, $1, 0); }


def p_formal_3(p):
    """formal : explicitornot type decidstart ASSIGN varinit"""
    p[2]["type"] = "PARA_TYPE"
    # p[3]["type"] = p[2]
    p[0] = (p[2], p[3])
    # { $$ = new formal($2->getPos(), $2, $3, $5, $1, 0); }


def p_formal_4(p):
    """formal : explicitornot type ID decidstart"""
    # { bool k = checkKeyword($3.pos, $3.sym);
    #                      $$ = new formal($2->getPos(), $2, $4, 0, $1, k); }


def p_formal_5(p):
    """formal : explicitornot type ID decidstart ASSIGN varinit"""
    # { bool k = checkKeyword($3.pos, $3.sym);
    #                      $$ = new formal($2->getPos(), $2, $4, $6, $1, k); }


def p_fundec_1(p):
    """fundec : type ID '(' ')' blockstm"""
    p[1]["type"] = "RETURN"
    p[2]["type"] = "FUNCTION"

    p[0] = p[2]

    p.parser.states.add_symbol(p[1], p[2])
    # { $$ = new fundec($3, $1, $2.sym, new formals($3), $5); }


def p_fundec_2(p):
    """fundec : type ID '(' formals ')' blockstm"""  # 得在 blockstm 时添加items
    p[1]["type"] = "TYPE"
    p[2]["type"] = "FUNCTION"
    p[0] = p[2]

    p.parser.states.add_symbol(p[1], p[2])

    # function paramters belongs to <blockstm> scope
    for type, param in p[4]:
        printlog("param", type, param)
        type["scope"] = p[6]
        type["type"] = "TYPE"
        if param is not None:
            param["scope"] = p[6]
            param["type"] = "PARAMETER"
        p[6].add_symbol(type, param)
    # { $$ = new fundec($3, $1, $2.sym, $4, $6); }


def p_typedec_1(p):
    """typedec : STRUCT ID block"""
    # { $$ = new recorddec($1, $2.sym, $3); }


def p_typedec_2(p):
    """typedec : TYPEDEF vardec"""
    # { $$ = new typedec($1, $2); }


def p_slice_1(p):
    """slice : ':'"""
    # { $$ = new slice($1, 0, 0); }


def p_slice_2(p):
    """slice : exp ':'"""
    # { $$ = new slice($2, $1, 0); }


def p_slice_3(p):
    """slice : ':' exp"""
    # { $$ = new slice($1, 0, $2); }


def p_slice_4(p):
    """slice : exp ':' exp"""
    # { $$ = new slice($2, $1, $3); }


def p_value_1(p):
    """value : value '.' ID"""
    # { $$ = new fieldExp($2, $1, $3.sym); }


def p_value_2(p):
    """value : name '[' exp ']'"""
    # { $$ = new subscriptExp($2,
    #                               new nameExp($1->getPos(), $1), $3); }


def p_value_3(p):
    """value : value '[' exp ']'"""
    # { $$ = new subscriptExp($2, $1, $3); }


def p_value_4(p):
    """value : name '[' slice ']'"""
    # { $$ = new sliceExp($2,
    #                               new nameExp($1->getPos(), $1), $3); }


def p_value_5(p):
    """value : value '[' slice ']'"""
    # { $$ = new sliceExp($2, $1, $3); }


def p_value_6(p):
    """value : name '(' ')'"""
    # { $$ = new callExp($2,
    #                                       new nameExp($1->getPos(), $1),
    #                                       new arglist()); }


def p_value_7(p):
    """value : name '(' arglist ')'"""
    # { $$ = new callExp($2,
    #                                       new nameExp($1->getPos(), $1),
    #                                       $3); }


def p_value_8(p):
    """value : value '(' ')'"""
    # { $$ = new callExp($2, $1, new arglist()); }


def p_value_9(p):
    """value : value '(' arglist ')'"""
    # { $$ = new callExp($2, $1, $3); }


def p_value_10(p):
    """value : '(' exp ')' %prec EXP_IN_PARENS_RULE"""
    # { $$ = $2; }


def p_value_11(p):
    """value : '(' name ')' %prec EXP_IN_PARENS_RULE"""
    # { $$ = new nameExp($2->getPos(), $2); }


def p_value_12(p):
    """value : THIS"""
    # { $$ = new thisExp($1); }


def p_argument_1(p):
    """argument : exp"""
    # { $$.name = symbol::nullsym; $$.val=$1; }


def p_argument_2(p):
    """argument : ID ASSIGN exp"""
    # { $$.name = $1.sym; $$.val=$3; }


def p_arglist_1(p):
    """arglist : argument"""
    # { $$ = new arglist(); $$->add($1); }


def p_arglist_2(p):
    """arglist : ELLIPSIS argument"""
    # { $$ = new arglist(); $$->addRest($2); }


def p_arglist_3(p):
    """arglist : arglist ',' argument"""
    # { $$ = $1; $$->add($3); }


def p_arglist_4(p):
    """arglist : arglist ELLIPSIS argument"""
    # { $$ = $1; $$->addRest($3); }


def p_tuple_1(p):
    """tuple : exp ',' exp"""
    # { $$ = new arglist(); $$->add($1); $$->add($3); }


def p_tuple_2(p):
    """tuple : tuple ',' exp"""
    # { $$ = $1; $$->add($3); }


def p_exp_1(p):
    """exp : name"""
    printlog("exp-name:", *p[1:])
    # p[1]["type"] = "NAME"
    p[0] = p[1]

    # { $$ = new nameExp($1->getPos(), $1); }


def p_exp_2(p):
    """exp : value"""
    printlog("exp-name:", *p[1:])
    p[0] = p[1]
    # { $$ = $1; }


def p_exp_3(p):
    """exp : LIT"""
    # { $$ = $1; }


def p_exp_4(p):
    """exp : STRING"""
    # { $$ = $1; }


def p_exp_5(p):
    """exp : LIT exp"""
    # { $$ = new scaleExp($1->getPos(), $1, $2); }


def p_exp_6(p):
    """exp : '(' name ')' exp"""
    # { $$ = new castExp($2->getPos(), new nameTy($2), $4); }


def p_exp_7(p):
    """exp : '(' name dims ')' exp"""
    # { $$ = new castExp($2->getPos(), new arrayTy($2, $3), $5); }


def p_exp_8(p):
    """exp : '+' exp %prec UNARY"""
    # { $$ = new unaryExp($1.pos, $2, $1.sym); }


def p_exp_9(p):
    """exp : '-' exp %prec UNARY"""
    # { $$ = new unaryExp($1.pos, $2, $1.sym); }


def p_exp_10(p):
    """exp : OPERATOR exp"""
    # { $$ = new unaryExp($1.pos, $2, $1.sym); }


def p_exp_11(p):
    """exp : exp '+' exp"""
    # { $$ = new binaryExp($2.pos, $1, $2.sym, $3); }


def p_exp_12(p):
    """exp : exp '-' exp"""
    # { $$ = new binaryExp($2.pos, $1, $2.sym, $3); }


def p_exp_13(p):
    """exp : exp '*' exp"""
    # { $$ = new binaryExp($2.pos, $1, $2.sym, $3); }


def p_exp_14(p):
    """exp : exp '/' exp"""
    # { $$ = new binaryExp($2.pos, $1, $2.sym, $3); }


def p_exp_15(p):
    """exp : exp '%' exp"""
    # { $$ = new binaryExp($2.pos, $1, $2.sym, $3); }


def p_exp_16(p):
    """exp : exp '#' exp"""
    # { $$ = new binaryExp($2.pos, $1, $2.sym, $3); }


def p_exp_17(p):
    """exp : exp '^' exp"""
    # { $$ = new binaryExp($2.pos, $1, $2.sym, $3); }


def p_exp_18(p):
    """exp : exp LT exp"""
    # { $$ = new binaryExp($2.pos, $1, $2.sym, $3); }


def p_exp_19(p):
    """exp : exp LE exp"""
    # { $$ = new binaryExp($2.pos, $1, $2.sym, $3); }


def p_exp_20(p):
    """exp : exp GT exp"""
    # { $$ = new binaryExp($2.pos, $1, $2.sym, $3); }


def p_exp_21(p):
    """exp : exp GE exp"""
    # { $$ = new binaryExp($2.pos, $1, $2.sym, $3); }


def p_exp_22(p):
    """exp : exp EQ exp"""
    # { $$ = new equalityExp($2.pos, $1, $2.sym, $3); }


def p_exp_23(p):
    """exp : exp NEQ exp"""
    # { $$ = new equalityExp($2.pos, $1, $2.sym, $3); }


def p_exp_24(p):
    """exp : exp CAND exp"""
    # { $$ = new andExp($2.pos, $1, $2.sym, $3); }


def p_exp_25(p):
    """exp : exp COR exp"""
    # { $$ = new orExp($2.pos, $1, $2.sym, $3); }


def p_exp_26(p):
    """exp : exp CARETS exp"""
    # { $$ = new binaryExp($2.pos, $1, $2.sym, $3); }


def p_exp_27(p):
    """exp : exp AMPERSAND exp"""
    # { $$ = new binaryExp($2.pos, $1, $2.sym, $3); }


def p_exp_28(p):
    """exp : exp BAR exp"""
    # { $$ = new binaryExp($2.pos, $1, $2.sym, $3); }


def p_exp_29(p):
    """exp : exp OPERATOR exp"""
    # { $$ = new binaryExp($2.pos, $1, $2.sym, $3); }


def p_exp_30(p):
    """exp : exp INCR exp"""
    # { $$ = new binaryExp($2.pos, $1, $2.sym, $3); }


def p_exp_31(p):
    """exp : NEW celltype"""
    # { $$ = new newRecordExp($1, $2); }


def p_exp_32(p):
    """exp : NEW celltype dimexps"""
    # { $$ = new newArrayExp($1, $2, $3, 0, 0); }


def p_exp_33(p):
    """exp : NEW celltype dimexps dims"""
    # { $$ = new newArrayExp($1, $2, $3, $4, 0); }


def p_exp_34(p):
    """exp : NEW celltype dims"""
    # { $$ = new newArrayExp($1, $2, 0, $3, 0); }


def p_exp_35(p):
    """exp : NEW celltype dims arrayinit"""
    # { $$ = new newArrayExp($1, $2, 0, $3, $4); }


def p_exp_36(p):
    """exp : NEW celltype '(' ')' blockstm"""
    # { $$ = new newFunctionExp($1, $2, new formals($3), $5); }


def p_exp_37(p):
    """exp : NEW celltype dims '(' ')' blockstm"""
    # { $$ = new newFunctionExp($1,
    #                                              new arrayTy($2->getPos(), $2, $3),
    #                                              new formals($4),
    #                                              $6); }


def p_exp_38(p):
    """exp : NEW celltype '(' formals ')' blockstm"""
    # { $$ = new newFunctionExp($1, $2, $4, $6); }


def p_exp_39(p):
    """exp : NEW celltype dims '(' formals ')' blockstm"""
    # { $$ = new newFunctionExp($1,
    #                                              new arrayTy($2->getPos(), $2, $3),
    #                                              $5,
    #                                              $7); }


def p_exp_40(p):
    """exp : exp '?' exp ':' exp"""
    # { $$ = new conditionalExp($2, $1, $3, $5); }


def p_exp_41(p):
    """exp : exp ASSIGN exp"""
    # { $$ = new assignExp($2, $1, $3); }


def p_exp_42(p):
    """exp : '(' tuple ')'"""
    # { $$ = new callExp($1, new nameExp($1, SYM_TUPLE), $2); }


def p_exp_43(p):
    """exp : exp join exp %prec JOIN_PREC"""
    # { $2->pushFront($1); $2->pushBack($3); $$ = $2; }


def p_exp_44(p):
    """exp : exp dir %prec DIRTAG"""
    # { $2->setSide(camp::OUT);
    #                      joinExp *jexp =
    #                          new joinExp($2->getPos(), SYM_DOTS);
    #                      $$=jexp;
    #                      jexp->pushBack($1); jexp->pushBack($2); }


def p_exp_45(p):
    """exp : INCR exp %prec UNARY"""
    # { $$ = new prefixExp($1.pos, $2, SYM_PLUS); }


def p_exp_46(p):
    """exp : DASHES exp %prec UNARY"""
    # { $$ = new prefixExp($1.pos, $2, SYM_MINUS); }


def p_exp_47(p):
    """exp : exp INCR %prec UNARY"""
    # { $$ = new postfixExp($2.pos, $1, SYM_PLUS); }


def p_exp_48(p):
    """exp : exp SELFOP exp"""
    # { $$ = new selfExp($2.pos, $1, $2.sym, $3); }


def p_exp_49(p):
    """exp : QUOTE '{' fileblock '}'"""
    # { $$ = new quoteExp($1, $3); }


def p_join_1(p):
    """join : DASHES"""
    # { $$ = new joinExp($1.pos,$1.sym); }


def p_join_2(p):
    """join : basicjoin %prec JOIN_PREC"""
    # { $$ = $1; }


def p_join_3(p):
    """join : dir basicjoin %prec JOIN_PREC"""
    # { $1->setSide(camp::OUT);
    #                      $$ = $2; $$->pushFront($1); }


def p_join_4(p):
    """join : basicjoin dir %prec JOIN_PREC"""
    # { $2->setSide(camp::IN);
    #                      $$ = $1; $$->pushBack($2); }


def p_join_5(p):
    """join : dir basicjoin dir %prec JOIN_PREC"""
    # { $1->setSide(camp::OUT); $3->setSide(camp::IN);
    #                      $$ = $2; $$->pushFront($1); $$->pushBack($3); }


def p_dir_1(p):
    """dir : '{' CURL exp '}'"""
    # { $$ = new specExp($2.pos, $2.sym, $3); }


def p_dir_2(p):
    """dir : '{' exp '}'"""
    # { $$ = new specExp($1, symbol::opTrans("spec"), $2); }


def p_dir_3(p):
    """dir : '{' exp ',' exp '}'"""
    # { $$ = new specExp($1, symbol::opTrans("spec"),
    # 				      new pairExp($3, $2, $4)); }


def p_dir_4(p):
    """dir : '{' exp ',' exp ',' exp '}'"""
    # { $$ = new specExp($1, symbol::opTrans("spec"),
    # 				      new tripleExp($3, $2, $4, $6)); }


def p_basicjoin_1(p):
    """basicjoin : DOTS"""
    # { $$ = new joinExp($1.pos, $1.sym); }


def p_basicjoin_2(p):
    """basicjoin : DOTS tension DOTS"""
    # { $$ = new joinExp($1.pos, $1.sym); $$->pushBack($2); }


def p_basicjoin_3(p):
    """basicjoin : DOTS controls DOTS"""
    # { $$ = new joinExp($1.pos, $1.sym); $$->pushBack($2); }


def p_basicjoin_4(p):
    """basicjoin : COLONS"""
    # { $$ = new joinExp($1.pos, $1.sym); }


def p_basicjoin_5(p):
    """basicjoin : LONGDASH"""
    # { $$ = new joinExp($1.pos, $1.sym); }


def p_tension_1(p):
    """tension : TENSION exp"""
    # { $$ = new binaryExp($1.pos, $2, $1.sym,
    #                               new booleanExp($1.pos, false)); }


def p_tension_2(p):
    """tension : TENSION exp AND exp"""
    # { $$ = new ternaryExp($1.pos, $2, $1.sym, $4,
    #                               new booleanExp($1.pos, false)); }


def p_tension_3(p):
    """tension : TENSION ATLEAST exp"""
    # { $$ = new binaryExp($1.pos, $3, $1.sym,
    #                               new booleanExp($2.pos, true)); }


def p_tension_4(p):
    """tension : TENSION ATLEAST exp AND exp"""
    # { $$ = new ternaryExp($1.pos, $3, $1.sym, $5,
    #                               new booleanExp($2.pos, true)); }


def p_controls_1(p):
    """controls : CONTROLS exp"""
    # { $$ = new unaryExp($1.pos, $2, $1.sym); }


def p_controls_2(p):
    """controls : CONTROLS exp AND exp"""
    # { $$ = new binaryExp($1.pos, $2, $1.sym, $4); }


def p_stm_1(p):
    """stm : ';'"""
    # { $$ = new emptyStm($1); }


def p_stm_2(p):
    """stm : blockstm"""
    printlog("stm-blockstm", *p[1:])
    p[0] = p[1]
    # { $$ = $1; }


def p_stm_3(p):
    """stm : stmexp ';'"""
    printlog("stm-stmexp")
    # { $$ = $1; }


def p_stm_4(p):
    """stm : IF '(' exp ')' stm ELSE stm"""
    printlog("if-else", *p[1])
    # { $$ = new ifStm($1, $3, $5, $7); }


def p_stm_5(p):
    """stm : IF '(' exp ')' stm"""
    printlog("if-(exp)")
    # { $$ = new ifStm($1, $3, $5); }


def p_stm_6(p):
    """stm : WHILE '(' exp ')' stm"""
    # { $$ = new whileStm($1, $3, $5); }


def p_stm_7(p):
    """stm : DO stm WHILE '(' exp ')' ';'"""
    # { $$ = new doStm($1, $2, $5); }


def p_stm_8(p):
    """stm : FOR '(' forinit ';' fortest ';' forupdate ')' stm"""
    # { $$ = new forStm($1, $3, $5, $7, $9); }


def p_stm_9(p):
    """stm : FOR '(' type ID ':' exp ')' stm"""
    p[4]["scope"] = p.parser.scopes.current_scope
    # { $$ = new extendedForStm($1, $3, $4.sym, $6, $8); }


def p_stm_10(p):
    """stm : BREAK ';'"""
    # { $$ = new breakStm($1); }


def p_stm_11(p):
    """stm : CONTINUE ';'"""
    # { $$ = new continueStm($1); }


def p_stm_12(p):
    """stm : RETURN_ ';'"""
    # { $$ = new returnStm($1); }


def p_stm_13(p):
    """stm : RETURN_ exp ';'"""
    # { $$ = new returnStm($1, $2); }


def p_stmexp_1(p):
    """stmexp : exp"""
    # { $$ = new expStm($1->getPos(), $1); }


def p_blockstm_1(p):
    """blockstm : block"""
    printlog("blockstm-block", *p[1:])
    p[0] = p[1]
    # { $$ = new blockStm($1->getPos(), $1); }


def p_forinit_1(p):
    """forinit :"""
    # { $$ = 0; }


def p_forinit_2(p):
    """forinit : stmexplist"""
    # { $$ = $1; }


def p_forinit_3(p):
    """forinit : barevardec"""
    # { $$ = $1; }


def p_fortest_1(p):
    """fortest :"""
    # { $$ = 0; }


def p_fortest_2(p):
    """fortest : exp"""
    # { $$ = $1; }


def p_forupdate_1(p):
    """forupdate :"""
    # { $$ = 0; }


def p_forupdate_2(p):
    """forupdate : stmexplist"""
    # { $$ = $1; }


def p_stmexplist_1(p):
    """stmexplist : stmexp"""
    # { $$ = new expList($1->getPos(), $1); }


def p_stmexplist_2(p):
    """stmexplist : stmexplist ',' stmexp"""
    # { $$ = $1; $$->pushBack($3); }


# Error rule for syntax errors
def p_error(p):
    print(f"Syntax error at {p.value!r}, line:{p.lexer.lineno}")
    raise Error("Stop")
