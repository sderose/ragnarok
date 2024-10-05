#!/usr/bin/env python3
#
# https://developer.mozilla.org/en-US/docs/Web/API/DOMException
# w3.org/TR/1998/REC-DOM-Level-1-19981001/level-one-core.html
# http://stackoverflow.com/questions/1319615
# https://docs.python.org/2/library/xml.dom.html
# https://webidl.spec.whatwg.org/#dfn-error-names-table
#
class DOMException(Exception):                  pass
DE = DOMException

class RangeError(Exception):                    pass

# Are these better as subclasses of DOMException, or of
# applicable Python ones such as IndexError, TypeError, etc.?
#
class IndexSizeError(DE): pass        # Deprecated. Use RangeError. (1)
class HierarchyRequestError(DE): pass # would yield an incorrect node tree. (3)
class WrongDocumentError(DE): pass    # object is in the wrong document. (4)
class InvalidCharacterError(DE): pass # string contains invalid characters. (5)
class NoModificationAllowedError(DE): pass # object can not be modified. (7)
class NotFoundError(DE): pass         # object can not be found here. (8)
class NotSupportedError(DE): pass     # operation not supported. (9)
class InUseAttributeError(DE): pass   # attribute in use by another element. (10)
class InvalidStateError(DE): pass     # object is in an invalid state. (11)
# Not defining this since Python has conflicting builtin.
#class SyntaxError(DE): pass           # string !~ expected pattern. (12)
class InvalidModificationError(DE): pass  # obj cannot be modified this way. (13)
class NamespaceError(DE): pass        # not allowed by Namespaces in XML. (14)
class InvalidAccessError(DE): pass    # Deprecated. (15)
#    Use TypeError for invalid arguments,
#    Use "NotSupportedError" DOMException for unsupported operations,
#    Use "NotAllowedError" DOMException for denied requests instead.
class TypeMismatchError(DE): pass     # Deprecated. Use TypeError instead. (17)
class SecurityError(DE): pass         # operation is insecure. (18)
class NetworkError(DE): pass          # network error occurred. (19)
class AbortError(DE): pass            # operation was aborted. (20)
class QuotaExceededError(DE): pass    # quota has been exceeded. (22)
# Not defining this since Python has conflicting builtin.
#class TimeoutError(DE): pass          # operation timed out. (23)
class InvalidNodeTypeError(DE): pass  # bad node (or anc) for op. (24)
class DataCloneError(DE): pass        # object can not be cloned. (25)
###
class EncodingError(DE): pass   # en/decoding operation failed.
class NotReadableError(DE): pass# I/O read operation failed.
class UnknownError(DE): pass    # unknown transient reason
class ConstraintError(DE): pass # mutation op failed b/c constraint [INDEXEDDB]
class DataError(DE): pass       # Provided data is inadequate.
class TransactionInactiveError(DE): pass  # request on inactive transaction [INDEXEDDB]
class ReadOnlyError(DE): pass   # mutating in readonly transaction. [INDEXEDDB]
class VersionError(DE): pass    # open db of lower version. [INDEXEDDB]
class OperationError(DE): pass  # operation-specific failure.
class NotAllowedError(DE): pass # not allowed by user agent/platform/user.
class OptOutError(DE): pass

### Legacy DOM names
#
legacyExceptions = True
if (legacyExceptions):
    INDEX_SIZE_ERR = DOMException                   # 1 (GENERIC)
    DOMSTRING_SIZE_ERR = DOMException               # 2 (GENERIC)
    HIERARCHY_REQUEST_ERR = HierarchyRequestError   # 3
    WRONG_DOCUMENT_ERR = WrongDocumentError         # 4
    INVALID_CHARACTER_ERR = InvalidCharacterError   # 5
    NO_DATA_ALLOWED_ERR = DOMException              # 6 (GENERIC)
    NO_MODIFICATION_ALLOWED_ERR = NoModificationAllowedError # 7
    NOT_FOUND_ERR = NotFoundError                   # 8
    NOT_SUPPORTED_ERR = NotSupportedError           # 9
    INUSE_ATTRIBUTE_ERR = InUseAttributeError       # 10
    INVALID_STATE_ERR = InvalidStateError           # 11
    SYNTAX_ERR = SyntaxError                        # 12 (BUILTIN)
    INVALID_MODIFICATION_ERR = InvalidModificationError # 13
    NAMESPACE_ERR = NamespaceError                  # 14
    INVALID_ACCESS_ERR = DOMException               # 15 (GENERIC)
    TYPE_MISMATCH_ERR = TypeMismatchError           # 17
    SECURITY_ERR = SecurityError                    # 18
    NETWORK_ERR = NetworkError                      # 19
    ABORT_ERR = AbortError                          # 20
    URL_MISMATCH_ERR = DOMException                 # 21 (GENERIC)
    QUOTA_EXCEEDED_ERR = DOMException               # 22 (GENERIC)
    TIMEOUT_ERR = TimeoutError                      # 23 (BUILTIN)
    INVALID_NODE_TYPE_ERR = InvalidNodeTypeError    # 24
    DATA_CLONE_ERR = DataCloneError                 # 25
