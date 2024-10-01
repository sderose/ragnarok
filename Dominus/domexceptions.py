#!/usr/bin/env python3
#
# xml.dom.minidom uses typical Python exceptions, although DOM defines
# it's own. Not sure which way to go.
#
# https://developer.mozilla.org/en-US/docs/Web/API/DOMException
# w3.org/TR/1998/REC-DOM-Level-1-19981001/level-one-core.html
# http://stackoverflow.com/questions/1319615
# https://docs.python.org/2/library/xml.dom.html
#
class DOMException(Exception):                 pass

class HIERARCHY_REQUEST_ERR(ValueError):       pass  # 3
class WRONG_DOCUMENT_ERR(ValueError):          pass  # 4
class INVALID_CHARACTER_ERR(ValueError):       pass  # 5
class NOT_FOUND_ERR(ValueError):               pass  # 8
class NOT_SUPPORTED_ERR(Exception):            pass  # 9
class NAMESPACE_ERR(ValueError):               pass
### Rest unused:
#
#class INDEX_SIZE_ERR(Index_Error):              pass  # 1
#class DOMSTRING_SIZE_ERR(Index_Error):          pass  # 2
#class NO_DATA_ALLOWED_ERR(ValueError):          pass  # 6
#class NO_MODIFICATION_ALLOWED_ERR(Exception):   pass  # 7
#class INUSE_ATTRIBUTE_ERR(Exception):           pass  # 10
#class INVALID_STATE_ERR(Exception):             pass  # 11
#class SYNTAX_ERR(Exception):                    pass  # 12
#class INVALID_MODIFICATION_ERR(Exception):      pass  # 13
#class INVALID_ACCESS_ERR(Exception):            pass  # 15
#class TYPE_MISMATCH_ERR(Exception):             pass  # 17
#class SECURITY_ERR(Exception):                  pass  # 18
#class NETWORK_ERR(Exception):                   pass  # 19
#class ABORT_ERR(Exception):                     pass  # 20
#class URL_MISMATCH_ERR(Exception):              pass  # 21
#class QUOTA_EXCEEDED_ERR(Exception):            pass  # 22
#class TIMEOUT_ERR(Exception):                   pass  # 23
class INVALID_NODE_TYPE_ERR(Exception):         pass  # 24
#class DATA_CLONE_ERR(Exception):                pass  # 25
#EncodingError, NotReadableError, UnknownError, ConstraintError, DataError,
#TransactionInactiveError, ReadOnlyError, VersionError, OperationError,
#NotAllowedError

# Not in minidom:
NAME_ERR = INVALID_CHARACTER_ERR
