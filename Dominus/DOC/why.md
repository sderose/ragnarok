==Why is this useful?==

The bottom lines are:

* BaseDom includes not just DOM 1, but complete DOM2, and a lot of convenience
functions from DOM3, whatwg, HTML DOM, JNode, ETree, XPath, and more. In many
cases, you can do things the way any of those does them.

* BaseDom uses much more modern Python, including thorough unittesting, enums,
type-hints, generators, optional and union parameters, properties, and so on.

* BaseDom is about 40% faster than minidom (by my tests, at least).

* BaseDom has pretty extensive, specific, and informative error messages.
If a value is bad it typically shows you the bad value in
the message ('cuz it annoys me when software doesn't do that).

* It fixes problems of minidom like updating.
For example, getElementById() still works after attribute changes.

* BaseDom provides for shorter/more readable code:
    minidom: if x.nodeType == Node.PROCESSING_INSTRUCTION_NODE:
    BaseDom: if x.isPI:

* Conceptually, Elements are lists of children plus annotations
(it's an n-ary annotated tree, after all).
This makes it natural to suppport the usual "list" methods, [], and properties,
rather than needing special methods like appendChild, insertBefore, removeChild,
replaceChild, etc. (those, of course, are still there too).

* DOM makes you insert children in certain ways --
appendChild(newChild) for the end, but insertBefore(newChild, oldChild)
elsewhere. No way to insert by position number, though that's often handy
(and especially handy and Pythonic and fast once Elements are lists).
In BaseDom, you can pass oldChild arguments either the DOM way (as the
actual child object), or as a (signed) int, like Python lists;
or use append() or extend() (or appendChild()
for backward compatibility). Plus whatwg-style insertAdjacentXML().

* Python provides very nice slicing, which minidom does not leverage.
You can pick with x.childNodes[5], but if you insert by assigning to it,
you'll corrupt the whole minidom structure.
BaseDom lets you use all the list slicing notations normally.
In addition, you can use brackets in extended ways similar to XPath:
If you want all the "P" children of an element,
just say myElement["P"] (likewise for "#text", ["@class"],
["*"] for just elements, etc.).
If you want just the first "P", say ["P":0]; and so on.

* whatwg-like methods for dealing with attribute tokens are available, but
are not hard-coded to only work with @class.

* Similarly, Python's comparison operators are supported for testing
document order. DOM 3 isEqualNode() and whatwg compareDocumentPosition()
are also available.

* Generators are provided for children, descendants, and even SAX events.

* There are several useful
and convenient "node selection" operators, including CSS selectors, and
easy hooks to add your own.

* It turns out that storing previousSibling
and nextSibling in every node is usually counterproductive. I did that
at first, but benchmarked and found it
was worse than just looking through the array.
In theory, extreme numbers of children could change that,
but I tested pretty big, and I haven't seen XML trees
wide enough to care in a very long time.
So it's gone. It's easy to add back if desired.

* There are inner/outer XML/Text setters/getters and many serialization options.
There is even JSON i/o that can round-trip correctly (unlike any others I've seen).

* Collecting all the text from a subtree is provided, but is also conceptually
easier to build than in (say) ElementTree:

    def getAllText(node:Node) -> str;
        if node.isTextNode: return node.data
        if node.isElement: return "".join(ch.getAllText() for ch in self)
        return ""

ElementTree's approach has no text nodes, but 2 text properties on each Element,
making text access more involved. Also, text pieces in ElementTree are
just strings, which is nice for some things but means they don't know
where they "belong", so you can't "fire and forget" the way you can with nodes.

* Correct escaping is available for all contexts (escaping special characters
in attribute values is not the same as in comments or content, just as in most
any data representation or programming language). You can turn on HTML named
entity support with a single PI or API call.

* BaseDom has a pretty thorough test suite, which is set up so it can also
be applied to minidom (extensions are tested separately). That should help
reliability for everyone. Coverage is around 80%.

* BaseDom separates out a package to deal with string-specific issues like what's
an acceptable nodeName. For example you can tweak just that one file to
rule out private-use name characters, or limit to Latin-1, change the definition
of NAMEs, etc. You can choose types of case-folding (say, to switch between
HTML and XML rules), Unicode normalization,
and definitions of whitespace (which differ slightly between
original HTML, WHATWG HTML, XML, Python, Javascript, etc.).

* minidom doesn't give much access to schema information, which is fine for
many purposes and understandable given there are several important schema
languages. BaseDom can read DTDs, plus XSD-like extensions such as
XSD datatypes for attributes; name-lists; etc. Or you can set up declarations
via the API, for example to get attribute defaults and type-checking,
have int attributes *be* ints in your DOM, declare where IDs are found,....

* The parser validates.

* There's also a new XML parser. But you can use others too.
The built-in one has many extensions,
but they are all off by default (and when extensions are off,
my unittests say it's a fully-conforming XML parser).
You turn extensions on via extra pseudo-attributes in the XML declaration,
which means a regular XML parser will stop right there instead of trying to
parse things it doesn't know. Saving a DOM *out* always produces
extensionless XML (with an option for Canonical XML).

