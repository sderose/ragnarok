| Property/Method | Node | Element | Attr | Ch | Text | Comment | PI | Doc |
|-----------------|------|---------|------|----|------|---------|----|-----|
| **Constants**
    ATTRIBUTE_NODE
    CDATA_SECTION_NODE
    COMMENT_NODE
    DOCUMENT_FRAGMENT_NODE
    DOCUMENT_NODE
    DOCUMENT_TYPE_NODE
    ELEMENT_NODE
    ENTITY_NODE
    ENTITY_REFERENCE_NODE
    NOTATION_NODE
    PROCESSING_INSTRUCTION_NODE
    TEXT_NODE

| **Instance Variables** |
| nodeType        | +    | +       | +    | +  | +    | +       | +  | +   |
| nodeName        | +    | !       | !    | !  | !    | !       | !  | !   |
| nodeValue       | -    | -       | !    | !  | !    | !       | !  | -   |
| namespaceURI    | ~    | !       | !    | -  | -    | -       | -  | !   |
| prefix          | ~    | !       | !    | -  | -    | -       | -  | !   |
| localName       | ~    | !       | !    | -  | -    | -       | -  | -   |
| ownerDocument   | +    | +       | +    | +  | +    | +       | +  | !   |
| parentNode      | +    | +       | !    | +  | +    | +       | +  | -   |
| childNodes      | +    | +       | 0    | +  | -    | -       | -  | +   |
| firstChild      | +    | +       | 0    | +  | -    | -       | -  | +   |
| lastChild       | +    | +       | 0    | +  | -    | -       | -  | +   |
| previousSibling | +    | +       | 0    | +  | +    | +       | +  | -   |
| nextSibling     | +    | +       | 0    | +  | +    | +       | +  | -   |
| attributes      | -    | +       | -    | -  | -    | -       | -  | -   |
| textContent     | +    | !       | !    | !  | !    | !       | !  | !   |
| data            | -    | -       | -    | +  | !    | !       | +  | -   |
| length          | -    | -       | -    | +  | !    | !       | +  | -   |
| documentElement | -    | -       | -    | -  | -    | -       | -  | +   |
| doctype         | -    | -       | -    | -  | -    | -       | -  | +   |
| implementation  | -    | -       | -    | -  | -    | -       | -  | +   |
| URL             | -    | -       | -    | -  | -    | -       | -  | +   |
| documentURI     | -    | -       | -    | -  | -    | -       | -  | +   |
| characterSet    | -    | -       | -    | -  | -    | -       | -  | +   |
| wholeText       | -    | -       | -    | -  | +    | -       | -  | -   |
| **Constructors** |
| createElement   | -    | -       | -    | -  | -    | -       | -  | +   |
| createElementNS | -    | -       | -    | -  | -    | -       | -  | +   |
| createTextNode  | -    | -       | -    | -  | -    | -       | -  | +   |
| createComment   | -    | -       | -    | -  | -    | -       | -  | +   |
| createP'I'      | -    | -       | -    | -  | -    | -       | -  | +   |
| createAttribute | -    | -       | -    | -  | -    | -       | -  | +   |
| createAttributeNS | -  | -       | -    | -  | -    | -       | -  | +   |
| createDocumentFragment | - | -   | -    | -  | -    | -       | -  | +   |
| createCDATASection | - | -       | -    | -  | -    | -       | -  | +   |
| **Predicates** |
| hasChildNodes   | +    | +       | 0    | +  | -    | -       | -  | +   |
| isEqualNode     | +    | !       | !    | !  | !    | !       | !  | !   |
| isSameNode      | +    | +       | +    | +  | +    | +       | +  | +   |
| isConnected     | +    | +       | +    | +  | +    | +       | +  | +   |
| contains        | +    | +       | 0    | +  | -    | -       | -  | +   |
| matches         | -    | +       | -    | -  | -    | -       | -  | -   |
| **Tree Navigators/Searchers** |
| getElementsByClassName | - | +   | -    | -  | -    | -       | -  | +   |
| getElementsByTagName| -| +       | -    | -  | -    | -       | -  | +   |
| closest         | -    | +       | -    | -  | -    | -       | -  | -   |
| getRootNode     | +    | +       | +    | +  | +    | +       | +  | !   |
| **Tree Mutators** |
| appendChild     | +    | !       | 0    | !  | -    | -       | -  | !   |
| removeChild     | +    | !       | 0    | !  | -    | -       | -  | !   |
| replaceChild    | +    | !       | 0    | !  | -    | -       | -  | !   |
| insertBefore    | +    | !       | 0    | !  | -    | -       | -  | !   |
| cloneNode       | +    | !       | !    | !  | !    | !       | !  | !   |
| normalize       | +    | !       | 0    | +  | -    | -       | -  | !   |
| prepend         | -    | +       | -    | -  | -    | -       | -  | +   |
| append          | -    | +       | -    | -  | -    | -       | -  | +   |
| before          | -    | +       | -    | +  | +    | +       | +  | -   |
| after           | -    | +       | -    | +  | +    | +       | +  | -   |
| replaceWith     | -    | +       | -    | +  | +    | +       | +  | -   |
| remove          | -    | +       | -    | +  | +    | +       | +  | -   |
| insertAdjacentElement | - | +    | -    | -  | -    | -       | -  | -   |
| insertAdjacentText | - | +       | -    | -  | -    | -       | -  | -   |
| insertAdjacentHTML | - | +       | -    | -  | -    | -       | -  | -   |
| **Other Methods** |
| compareDocumentPosition | + | +  | +    | +  | +    | +       | +  | +   |
| lookupPrefix       | + | !       | ! ?  | +  | +    | +       | +  | !   |
| lookupNamespaceURI | + | !       | ! ?  | +  | +    | +       | +  | !   |
| isDefaultNamespace | + | !       | ! ?  | +  | +    | +       | +  | !   |
| importNode      | -    | -       | -    | -  | -    | -       | -  | +   |
| adoptNode       | -    | -       | -    | -  | -    | -       | -  | +   |
| appendData      | -    | -       | -    | +  | +    | +       | +  | -   |
| insertData      | -    | -       | -    | +  | +    | +       | +  | -   |
| deleteData      | -    | -       | -    | +  | +    | +       | +  | -   |
| replaceData     | -    | -       | -    | +  | +    | +       | +  | -   |
| substringData   | -    | -       | -    | +  | +    | +       | +  | -   |
| splitText       | -    | -       | -    | -  | +    | -       | -  | -   |
| **HTML only**   |
| assignedSlot    | -    | +       | -    | +  | +    | +       | -  | -   |
| baseURI         | +    | !       | +    | +  | +    | +       | +  | !   |
| compatMode      | -    | -       | -    | -  | -    | -       | -  | +   |
| contentType     | -    | -       | -    | -  | -    | -       | -  | +   |
| createEvent     | -    | -       | -    | -  | -    | -       | -  | +   |
| createNodeIterator | - | -       | -    | -  | -    | -       | -  | +   |
| createTreeWalker | -   | -       | -    | -  | -    | -       | -  | +   |
| innerHTML       | -    | +       | -    | -  | -    | -       | -  | -   |
| outerHTML       | -    | +       | -    | -  | -    | -       | -  | -   |
| innerText       | -    | +       | -    | -  | -    | -       | -  | -   |??
| origin          | -    | -       | -    | -  | -    | -       | -  | +   |
| style           |
| className       |
| addEventListener |
| removeEventListener |
| querySelector   | -    | +       | -    | -  | -    | -       | -  | +   |
| querySelectorAll| -    | +       | -    | -  | -    | -       | -  | +   |
| dataset         |


**Serializers and parser** |
| innerXML |
| outerXML |
| outerJSON |
| writexml |
| toprettyxml |
| tostring |

From being a Python list:
    __bool__ ***
    __class__
    __delattr__
    __dict__
    __dir__
    __eq__
    __ge__
    __gt__
    __hash__
    __init__
    __le__
    __lt__
    __module__
    __ne__
    __repr__
    __sizeof__

'Document' in minidom:
    getElementById
    getElementsByTagNameNS
    getUserData
    setUserData

    __doc__
    __enter__
    __exit__
    __format__ ***
    __getattribute__
    __getstate__
    __init_subclass__
    __new__
    __reduce__
    __reduce_ex__
    __setattr__
    __slots__
    __str__ ***
    __subclasshook__
    __weakref__
    _call_user_data_handler
    _child_node_types
    _create_entity
    _create_notation
    _elem_info
    _get_actualEncoding
    _get_async
    _get_childNodes
    _get_doctype
    _get_documentElement
    _get_documentURI
    _get_elem_info
    _get_encoding
    _get_errorHandler
    _get_firstChild
    _get_lastChild
    _get_localName
    _get_standalone
    _get_strictErrorChecking
    _get_version
    _id_cache
    _id_search_stack
    _magic_id_count
    _set_async

    abort
    actualEncoding
    async_
    doctype ***
    documentURI ***
    encoding ***
    errorHandler
    getInterface
    implementation ***
    importNode  ***
    isSupported  ***
    load ***
    loadXML ***
    renameNode ***
    saveXML ***
    standalone ***
    strictErrorChecking ***

* Legend:
    + : Property/method is available and meaningful for this class
    ~ : Property/method exists but may not be meaningful or is abstract
    - : Property/method is not available for this class
    ! : Property/method is available but likely overrides or
        significantly modifies behavior from its parent class
    0 : Is removed, but existed in superclass

* Only 3 methods of Node exists but are meaningless
(namespaceURI, prefix, localName). Is that right?
What about Node methods like isFirstChild, childNodes, etc. on Attr?

* The attribute-related items [has|get|set|remove]Attribute[Node][NS] are
omitted, as they are only on Element.

* HTML also has various items specific to forms, tables, windows, and cookies;
as well as document.title.


| Symbol | Node | Element | Attr | Ch | Text | Comment | PI | Document |
|--------|------|---------|------|--- |------|---------|----|----------|
| +      | 25   | 29      | 9    | 27 | 20   | 20      | 19 | 16       |
| ~      | 3    | 0       | 0    | 0  | 0    | 0       | 0  | 0        |
| -      | 55   | 45      | 74   | 56 | 63   | 63      | 64 | 39       |
| !      | 0    | 19      | 10   | 10 | 10   | 10      | 10 | 38       |
| Total  | 83   | 93      | 93   | 93 | 93   | 93      | 93 | 93       |
