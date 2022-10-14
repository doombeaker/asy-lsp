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
    location = Location(
        uri=dst_uri,
        range=Range(
            start=Position(line=0, character=0),
            end=Position(line=1, character=1),
        ),
    )

    location_link = LocationLink(
        target_uri=dst_uri,
        target_range=Range(
            start=Position(line=0, character=0),
            end=Position(line=1, character=1),
        ),
        target_selection_range=Range(
            start=Position(line=0, character=0),
            end=Position(line=2, character=2),
        ),
        origin_selection_range=Range(
            start=Position(line=0, character=0),
            end=Position(line=3, character=3),
        ),
    )
    return location
    # return {  # type: ignore
    #     "file://return.location": location,
    #     "file://return.location_list": [location],
    #     "file://return.location_link_list": [location_link],
    # }.get(params.text_document.uri, None)


@asy_lsp_server.feature(TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls, params: DidChangeTextDocumentParams):
    """Text document did change notification."""
    pass


@asy_lsp_server.feature(TEXT_DOCUMENT_DID_CLOSE)
def did_close(server: AsyLspServer, params: DidCloseTextDocumentParams):
    """Text document did close notification."""
    server.show_message("Text Document Did Close")


@asy_lsp_server.feature(TEXT_DOCUMENT_DID_OPEN)
async def did_open(ls, params: DidOpenTextDocumentParams):
    """Text document did open notification."""
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
