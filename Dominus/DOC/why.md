==Why is this useful?==

The bottom lines are probably:

* BaseDom includes not just DOM 1, but complete DOM2, and a lot of convenience
functions (including some like prev/next that are not conceptually easy).

* BaseDom uses much more modern Python, including thorough unittesting.

* BaseDom has significantly less code than minidom.

* BaseDom is about 40% faster than minidom (by my tests, at least).


In more gory detail:

* BaseDom does much more than the (basically) DOM 1 of minidom,
which is getting a bit old.

* BaseDom uses modern Python tools such as

** Enums for things like node types, sax events, etc.
** Type hints (and the consequent lint help)
** Metaclasses (very nice given the complex hierarchy
** Properties
** Generators
** Optional and overloaded parameters.
** Far fewer _methods, leading to better performance

* BaseDom provides short alternatives for DOM things I find annoying
to type:
    if (x.nodeType == Node.PROCESSING_INSTRUCTION_NODE)...
    if (x.isPI)...

* BaseDom uses many conventions from the widespread whatwg spec,
such as extra methods, exceptions in camelCase instead of all aps, etc.

* Conceptually, Elements are essentially lists of children --
it's just a tree after all (yes, attributed trees are a thing in graph theory).
Document, NodeList, DocumentFragment, and such are minor variations on that;
This makes it more natural to let Python
programmers use the usual "list" methods and properties, rather than
needing special methods like appendChild, insertBefore, removeChild,
replaceChild, etc.

* Comment, PI, CDATA, and Text are not much different, except that they
can't have children, so list operations don't really apply. They already
subclass "CharacterData" (I would have called it "Leaf", but whatever).
I debated whether to take CharacterData out from under Node, or even make it
the base class, where Element than adds the list properties; but I didn't want
to perturb the class relationships that much. This is a violation of an OOP
rule known as the Liskov Substitution Principle. But that rule has known
difficulties, which seem to me to apply quite strongly here.

* Now that Element isa list, it turns out that storing previousSibling
and nextSibling in every node is counterproductive. I did that like minidom
at first, but benchmarked and found the overhead of building them (even lazily!)
was worse than just looking through the array. So it's gone.
In theory, extreme numbers of children could change that.
But I tested pretty big, and I haven't seen XML trees
wide enough to care in a very long time. It's easy to add back if desired
(e.g. a list alternative to substitute for regular List as superclass to
Node -- it could do chaining or indexing or skiplists or whatever).

* DOM makes you insert children is certain way --
either appendChild(newChild) for the end, or insertBefore(newChild, oldChild)
elsewhere. No way to insert by position number, though that's often handy
(and especially handy and Pythonic and fast once Elements are specialize lists.
But in BaseDom, you can pass oldChild arguments either the DOM way (as the
actual child object), or as an int. It just works. And like Python lists,
the int can count from either end, and you can append by giving any int
larger than the current max (or with append(), or extend(), or appendChild()
for backward compatibility).

* BaseDom round out obvious symmetries
** adding insertAfter for insertBefore
** prependChild for appendChild
** raise NotSupportedError when appropriate instead of quietly returning None
(for example methods minidom defines on Node but doesn't support)
** innerXML/outerXML, setters/getters on all feasible classes.

* Python provides very nice slicing, which minidom does not support.
BaseDom lets you use all the normal list slicing notations.
In addition, I noticed it's possible to overload
slicing, so you can use brackets in ways that look a lot like XPath, too
(you don't have to). If you want all the "P" children of an element,
just say myElement["P"]. Now in Elements, there may be more than one
"P", so you get a list just as you would with list[0:3] or even list[0:1].
If you want just the first one, say ["P":1]; slightly novel, but not very tough.

* While we're in brackets, you can also ask for ["@class"], or ["#text"], or
["#pi"], or ["*"] for all elements. If you know XML, these are intuitive.
They act pretty much as you'd expect for a multidict if Python had one,
or what any XPath user is used to.

* Imho, the second reason ElementTree did well is that it added several useful
and convenient "node selection" operators (such as CSS selectors).
The same thing is also done by
Node.js, XPath, and even the HTML (vs. XML) DOM. minidom never got around to
it, and didn't provide easy hooks to add your own. You have to do that *all*
the time, so it should be easy. BaseDom includes as many of those as I had time
to implement, and they can all go inside the [].

* If you want to integrate another selection process, just make a Callable
that takes a Node and returns True or False.
Pass the callable inside the brackets (it can even be a lambda like you'd do for
regex subs or sorts).

* I can't bring myself to use ElementTree because of one thing: its concept
of text just seems wrong to me.
Text is put into 2 properties of Elements (well, they do call
it "Element"Tree, after all). Most obviously, that means that a paragraph
with a bunch of text, with a few inline style changes interspersed, does not
resemble the user's model. Most users would things of all that text as
on par -- with some parts having little annotations marking tham as slightly
"special". A technical user might think of it as a sequence of text "things"
and style "things" (that in turn contain text "things"). The point, though,
is that in documents the text *is* the thing, and the markup, styles, etc.
are meta. But in ElementTree assembling the text requires checking two *properties*
of each Element, and arranging them in a kind of odd order. And, you don't
have to check *just* the things that are *inside* the paragraph (or other container) --
you also have to check the text (but not the tail) of the container. Operating
on that is a lot more complicated and error-prone than just saying:

    def getAllText(node);
        if node.isTextNode: return node.data
        if node.isElement: return "".join(ch.getAllText for ch in self)
        return ""

ElementTree's approach also yields very different trees that anything else,
making it very difficult to interoperate with the rest of the ecosystem --
it would be more difficult to implement XPath, XSLT, or XQuery on top of
ElementTree (though XPath seems to have been done). Very common operations
such as successors, testing order and containment, etc. are just way different
(and have more edge cases to worry about).

Since text pieces in ElementTree are just strings, they also don't know
who owns them -- where they "belong".
Thus you can't "fire and forget" with text the way you can with nodes.
Documents are more about their text than their elements (if you have to choose,
which I don't). But, I've included even these methods as extensions you can
used if you're so inclined; just be aware that depth and order and placement
in trees are necessarily different (though my myNode["*":4] notation
gets you the same thing that ElementTree thinks of as child #4).
other nodeTypes (afaict).

* Of course, most every later DOM-like implementation (including the HTML DOM)
provides text-gathering functions ready-made. BaseDom does, too. And you have
the correct escaping for various context available (escaping special characters
in attribute values is not the same as in comments or content; just as in most
any data representation or programming language).

* BaseDom adds a lot of functionality from related specs such as whatWG, the
HTML DOM, Node.js, CSS selectors, and so on.

* Going back to Elements, of course they can have attributes, not just children.
Attributes are kind of weird -- they're not parts of the tree.
They are (as common in OOP, formal language theory, graph theory,and elsewhere)
meta-stuff *about* nodes in the tree. I don't think a graph theoretician would
have made Attr a subclass of Node. Nevertheless, I've implemented them pretty
much as usual. Though with some additions such as the whatwg "##any" namespace,
which makes the variations on set/get/remove/has methods pretty much
just syntactic sugar (or perhaps syntactic limburger?).

* DOM is pretty good about separating the structure it cares about
from serialization to/from XML syntax. BaseDom tries to improve
that a bit by:

** Separating out a package to deal with string-specific issues like what's
an acceptable nodeName. For example you can tweak *just* that one file to
rule out private-use name characters, or limit to Latin-1, or whatever.

** Separating serializers and even including one for JSON that can (unlike any
others i've seen published) round-trip correctly.

** Hooking up to some experimental XML-like parsers.

** Providing a variation on SAX parsing that makes each attribute a separate
event, rather than packing **attrs into a flat parameter list. No varargs
needed, b/c this way no SAX events needs an unbounded number of parameters.
But you can have it the other way if you prefer.

* BaseDom has a pretty thorough test suite, which is set up so it can also
be applied to minidom (extensions are tested separately). That should help
reliability for everyone.

* ElementTree seems quite well-liked, but I think that is mainly because of
two things:

2:
1: it lets you pretend there's no text at all -- which is great if you're using XML
for what is really CSV-ish data (and indeed, that's what a very large share
of "example documents" are -- the 3-record personnel database, the config file,
etc. But XML is mainly designed and intended for *documents* -- where text is
*the* main thing. Try putting a play or novel or term paper into CSV or JSON;
it's not fun unless you re-invent XML (or at least DOM) on the way -- by which
time XML ends up *less* verbose (for example, you don't have to quote all the names
and all the text chunks, have commas between attributes, etc.


* But since BaseDom is interested in the structure and model, not the syntax,
it comes with a variety of serializers -- including one that can round-trip to
JSON.

* minidom doesn't give very good access to schema information. Which is fine for
some purposes, and understandable given there are several important schemas
languages. But even very simple things become harder. If all our DOM tools were
smart about entities (including full-fledged URIs), we wouldn't need XInclude
(or at least, not so much). If they could handle ATTLIST declarations (or some
equivalent), we could save an awful lot of space on defaults.

* Meanwhile, DTD doesn't support some obvious extensions it could have added
once XML was out, such as
** Distinguishing special-character definitions
** XSD built-in datatypes for attributes.

* I was there when we made XML, and there are a few things I wish I had gotten
that I didn't, or vice versa. Just a few. With my own DOM, which mostly
isolates serialization at the edges, I can easily experiment hooking up various
parsers -- adding support. You don't have to try any of those -- they're completely
separate tools, but in case you're interested, some things include:

** Boolean attributes:  <table +border>
** Unquoted attributes -- but only when the value is an XML NAME (to avoid
introducing a new concept):  <table class=BIG>
** Empty end-tag: </>
** Omitted end-tags (we've got the stack, right?):  <b><i><tt>foo</b>
** Simultaneous open/close:  <b|i>foo</b|i>
** "Close innermost element and re-open (nice for compact tables):  <tr><td>foo|bar|baz</tr>
**

