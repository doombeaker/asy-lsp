############################################################################
# Copyright(c) Open Law Library. All rights reserved.                      #
# See ThirdPartyNotices.txt in the project root for additional notices.    #
#                                                                          #
# Licensed under the Apache License, Version 2.0 (the "License")           #
# you may not use this file except in compliance with the License.         #
# You may obtain a copy of the License at                                  #
#                                                                          #
#     http: // www.apache.org/licenses/LICENSE-2.0                         #
#                                                                          #
# Unless required by applicable law or agreed to in writing, software      #
# distributed under the License is distributed on an "AS IS" BASIS,        #
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. #
# See the License for the specific language governing permissions and      #
# limitations under the License.                                           #
############################################################################
import asyncio
import re
import time
import uuid
from typing import Optional

from pytest import param
from .parser.ast import FileParsed
from pygls.uris import from_fs_path, to_fs_path

from pygls.lsp.methods import (
    COMPLETION,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_CLOSE,
    TEXT_DOCUMENT_DID_OPEN,
    DEFINITION,
    FORMATTING,
    RANGE_FORMATTING,
    DOCUMENT_SYMBOL,
)
from pygls.lsp.types import (
    CompletionItem,
    CompletionList,
    CompletionOptions,
    CompletionParams,
    DefinitionParams,
    DefinitionOptions,
    Location,
    ConfigurationItem,
    ConfigurationParams,
    DidChangeTextDocumentParams,
    DidCloseTextDocumentParams,
    DidOpenTextDocumentParams,
    DocumentFormattingOptions,
    DocumentSymbolOptions,
    Position,
    Range,
    TextEdit,
    DocumentSymbol,
    SymbolKind,
)

from pygls.server import LanguageServer

from .completionitems import keywords_and_builtin_types

COUNT_DOWN_START_IN_SECONDS = 10
COUNT_DOWN_SLEEP_IN_SECONDS = 1


class AsyLspServer(LanguageServer):
    CMD_SHOW_CONFIGURATION_ASYNC = "showConfigurationAsync"
    CMD_SHOW_CONFIGURATION_CALLBACK = "showConfigurationCallback"
    CMD_SHOW_CONFIGURATION_THREAD = "showConfigurationThread"

    CONFIGURATION_SECTION = "asyServer"

    def __init__(self):
        super().__init__()
        self.parsed_files = {}  # (fileuri:(fileparsed, time))
        self.last_change_time = {}  # (fileuri: time)

    def parse_file(self, file_uri):
        file_path = to_fs_path(file_uri)
        file = FileParsed(file_path)
        file.parse()
        file.construct_jump_table()
        self.parsed_files[file_uri] = (file, time.time())
        return file


asy_lsp_server = AsyLspServer()

from . import formatter


@asy_lsp_server.feature(DOCUMENT_SYMBOL, DocumentSymbolOptions())
def document_symbol(params):
    # import pdb;pdb.set_trace()
    file_uri = params.text_document.uri
    try_parse(file_uri)
    all_tokens_found = []
    for token in asy_lsp_server.parsed_files[file_uri][0].all_tokens:
        if token["type"] in ("STRUCT", "FUNCTION"):
            all_tokens_found.append(token)
    return_list = [
        DocumentSymbol(
            name=t["value"],
            kind=SymbolKind.Object,
            range=Range(
                start=Position(
                    line=t["position"][0] - 1, character=t["position"][1] - 1
                ),
                end=Position(
                    line=t["position"][0] - 1, character=t["position"][1] + t["len"]
                ),
            ),
            selection_range=Range(
                start=Position(
                    line=t["position"][0] - 1, character=t["position"][1] - 1
                ),
                end=Position(
                    line=t["position"][0] - 1, character=t["position"][1] + t["len"]
                ),
            ),
        )
        for t in all_tokens_found
    ]
    return return_list


@asy_lsp_server.feature(RANGE_FORMATTING)
def range_formatting(params):
    dst_uri = params.text_document.uri
    file_path = to_fs_path(dst_uri)
    start_line, start_column = (
        params.range.start.line + 1,
        params.range.start.character + 1,
    )
    end_line, end_column = params.range.end.line + 1, params.range.end.character + 1

    formatted_text = formatter.format_code_range(
        file_path, start_line, start_column, end_line, end_column
    )

    if formatted_text is not None:
        return [TextEdit(range=params.range, new_text=formatted_text)]
    return None


@asy_lsp_server.feature(
    FORMATTING,
    DocumentFormattingOptions(),
)
def formatting(params):
    dst_uri = params.text_document.uri
    file_path = to_fs_path(dst_uri)
    formatted_text = formatter.format_code(file_path)

    if formatted_text is not None:
        return [
            TextEdit(
                range=Range(
                    start=Position(line=0, character=0),
                    end=Position(line=999999, character=999999),
                ),
                new_text=formatted_text,
            )
        ]
    return None


@asy_lsp_server.feature(COMPLETION, CompletionOptions())
def completions(params: Optional[CompletionParams] = None) -> CompletionList:
    """Returns completion items."""
    return CompletionList(
        is_incomplete=False,
        items=[CompletionItem(label=item) for item in keywords_and_builtin_types],
    )


@asy_lsp_server.feature(DEFINITION, DefinitionOptions())
def defitions(params: DefinitionParams) -> Optional[Location]:
    dst_uri = params.text_document.uri
    try_parse(dst_uri)

    file, last_time = asy_lsp_server.parsed_files[dst_uri]
    if last_time < asy_lsp_server.last_change_time[dst_uri]:
        file = asy_lsp_server.parse_file(dst_uri)

    line, column = params.position.line + 1, params.position.character + 1
    definition_token = file.find_definiton(line, column)
    if definition_token is not None:
        position = definition_token["position"]
        len = definition_token["len"]
        return Location(
            uri=dst_uri,
            range=Range(
                start=Position(line=position[0] - 1, character=position[1] - 1),
                end=Position(line=position[0] - 1, character=position[1] - 1 + len),
            ),
        )

    return None


@asy_lsp_server.feature(TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls, params: DidChangeTextDocumentParams):
    """Text document did change notification."""
    dst_uri = params.text_document.uri
    asy_lsp_server.last_change_time[dst_uri] = time.time()


@asy_lsp_server.feature(TEXT_DOCUMENT_DID_CLOSE)
def did_close(server: AsyLspServer, params: DidCloseTextDocumentParams):
    """Text document did close notification."""
    server.show_message("Text Document Did Close")


def try_parse(file_uri):
    if file_uri not in asy_lsp_server.parsed_files.keys():
        asy_lsp_server.parse_file(file_uri)


@asy_lsp_server.feature(TEXT_DOCUMENT_DID_OPEN)
async def did_open(ls, params: DidOpenTextDocumentParams):
    file_uri = params.text_document.uri
    try_parse(file_uri)
    asy_lsp_server.last_change_time[file_uri] = time.time()
    ls.show_message("Text Document Did Open")


@asy_lsp_server.command(AsyLspServer.CMD_SHOW_CONFIGURATION_ASYNC)
async def show_configuration_async(ls: AsyLspServer, *args):
    """Gets exampleConfiguration from the client settings using coroutines."""
    try:
        config = await ls.get_configuration_async(
            ConfigurationParams(
                items=[
                    ConfigurationItem(
                        scope_uri="", section=AsyLspServer.CONFIGURATION_SECTION
                    )
                ]
            )
        )

        example_config = config[0].get("exampleConfiguration")

        ls.show_message(f"asyServer.exampleConfiguration value: {example_config}")

    except Exception as e:
        ls.show_message_log(f"Error ocurred: {e}")


@asy_lsp_server.command(AsyLspServer.CMD_SHOW_CONFIGURATION_CALLBACK)
def show_configuration_callback(ls: AsyLspServer, *args):
    """Gets exampleConfiguration from the client settings using callback."""

    def _config_callback(config):
        try:
            example_config = config[0].get("exampleConfiguration")

            ls.show_message(f"asyServer.exampleConfiguration value: {example_config}")

        except Exception as e:
            ls.show_message_log(f"Error ocurred: {e}")

    ls.get_configuration(
        ConfigurationParams(
            items=[
                ConfigurationItem(
                    scope_uri="", section=AsyLspServer.CONFIGURATION_SECTION
                )
            ]
        ),
        _config_callback,
    )


@asy_lsp_server.thread()
@asy_lsp_server.command(AsyLspServer.CMD_SHOW_CONFIGURATION_THREAD)
def show_configuration_thread(ls: AsyLspServer, *args):
    """Gets exampleConfiguration from the client settings using thread pool."""
    try:
        config = ls.get_configuration(
            ConfigurationParams(
                items=[
                    ConfigurationItem(
                        scope_uri="", section=AsyLspServer.CONFIGURATION_SECTION
                    )
                ]
            )
        ).result(2)

        example_config = config[0].get("exampleConfiguration")

        ls.show_message(f"asyServer.exampleConfiguration value: {example_config}")

    except Exception as e:
        ls.show_message_log(f"Error ocurred: {e}")
