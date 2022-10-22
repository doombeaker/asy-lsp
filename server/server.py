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
from .parser.ast import FileParsed
from pygls.uris import from_fs_path, to_fs_path

from pygls.lsp.methods import (
    COMPLETION,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_CLOSE,
    TEXT_DOCUMENT_DID_OPEN,
    DEFINITION,
)
from pygls.lsp.types import (
    CompletionItem,
    CompletionList,
    CompletionOptions,
    CompletionParams,
    DefinitionParams,
    DefinitionOptions,
    Location,
    LocationLink,
    ConfigurationItem,
    ConfigurationParams,
    Diagnostic,
    DidChangeTextDocumentParams,
    DidCloseTextDocumentParams,
    DidOpenTextDocumentParams,
    MessageType,
    Position,
    Range,
    Registration,
    RegistrationParams,
    SemanticTokens,
    SemanticTokensLegend,
    SemanticTokensParams,
    Unregistration,
    UnregistrationParams,
)
from pygls.lsp.types.basic_structures import (
    WorkDoneProgressBegin,
    WorkDoneProgressEnd,
    WorkDoneProgressReport,
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
        self.parsed_files = {}

    def parse_file(self, file_uri):
        file_path = to_fs_path(file_uri)
        file = FileParsed(file_path)
        file.parse()
        file.construct_jump_table()
        self.parsed_files[file_uri] = file
        return file


asy_lsp_server = AsyLspServer()


@asy_lsp_server.feature(COMPLETION, CompletionOptions())
def completions(params: Optional[CompletionParams] = None) -> CompletionList:
    """Returns completion items."""
    return CompletionList(
        is_incomplete=False,
        items=[CompletionItem(label=item) for item in keywords_and_builtin_types],
    )


@asy_lsp_server.feature(DEFINITION, DefinitionOptions())
def defitions(
    params: DefinitionParams,
):
    dst_uri = params.text_document.uri
    if dst_uri not in asy_lsp_server.parsed_files.keys():
        asy_lsp_server.parse_file(dst_uri)
    file = asy_lsp_server.parsed_files[dst_uri]
    line, column = params.position.line + 1, params.position.character + 1
    pos = file.find_definiton(line, column)

    if pos is not None:
        return Location(
            uri=dst_uri,
            range=Range(
                start=Position(line=pos[0] - 1, character=pos[1] - 1),
                end=Position(line=pos[0] - 1, character=pos[1]),
            ),
        )

    return None


@asy_lsp_server.feature(TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls, params: DidChangeTextDocumentParams):
    """Text document did change notification."""
    dst_uri = params.text_document.uri
    _parse_file(dst_uri)


@asy_lsp_server.feature(TEXT_DOCUMENT_DID_CLOSE)
def did_close(server: AsyLspServer, params: DidCloseTextDocumentParams):
    """Text document did close notification."""
    server.show_message("Text Document Did Close")


@asy_lsp_server.feature(TEXT_DOCUMENT_DID_OPEN)
async def did_open(ls, params: DidOpenTextDocumentParams):
    file_uri = params.text_document.uri
    if file_uri not in parsed_files.keys():
        _parse_file(file_uri)
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
