"""Protocol handler registration and parsing utilities"""

import urllib
import sys
from nxdrive.logging_config import get_logger
log = get_logger(__name__)


NXDRIVE_EDIT_URL_FORM = ('nxdrive://edit/scheme/server[:port]'
                         '/webappname/nxdoc/reponame/docref')

# Protocol handler parsing


def parse_protocol_url(url_string):
    """Parse URL for which nxdrive is registered as a protocol handler

    Return None if url_string is not a supported URL pattern or raise a
    ValueError is the URL structure is invalid.

    """
    if "://" not in url_string:
        return None

    protocol_name, data_string = url_string.split('://', 1)
    if protocol_name != 'nxdrive':
        return None

    if '/' not in data_string:
        raise ValueError("Invalid nxdrive URL: " + url_string)

    command, data_string = data_string.split('/', 1)
    if command == 'edit':
        return parse_edit_protocol(data_string)
    else:
        raise ValueError("Unsupported command '%s' in " + url_string)


def parse_edit_protocol(data_string):
    """Parse a nxdriveedit:// URL for quick editing of nuxeo documents"""
    invalid_msg = ('Invalid URL: got nxdrive://edit/%s while expecting %s'
                   % (data_string, NXDRIVE_EDIT_URL_FORM))

    if '/' not in data_string:
        raise ValueError(invalid_msg)

    scheme, data_string = data_string.split('/', 1)
    if scheme not in ('http', 'https'):
        raise ValueError(
            invalid_msg + ' : scheme should be http or https')

    if '/nxdocid/' not in data_string:
        raise ValueError(invalid_msg)

    server_part, doc_part = data_string.split('/repo/', 1)
    server_url = "%s://%s" % (scheme, server_part)
    repo, doc_part = doc_part.split('/nxdocid/', 1)
    doc_id, filename = doc_part.split('/filename/', 1)

    return dict(command='edit', server_url=server_url, repo=repo,
                doc_id=doc_id, filename=filename)


# Protocol handler registration


def register_protocol_handlers(controller):
    """Platform specific protocol handler registration using lazy imports"""
    if sys.platform == 'win32':
        from nxdrive.protocol_handler.win32 import register_protocol_handlers
        register_protocol_handlers(controller)
    elif sys.platform == 'darwin':
        from nxdrive.protocol_handler.darwin import register_protocol_handlers
        register_protocol_handlers(controller)
    else:
        # TODO: implement me
        log.debug("Protocol handler registration for '%s' not yet implemented",
                 sys.platform)
