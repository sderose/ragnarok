==issues with contains==

* __contains__ vs. contains

* removeNode vs. removeSelf vs. del

* empty lists are falsish -- but it seems like empty nodes/elements shouldn't be.

* Python "contains" and "in" work for testing whether one node is a
child of another. This means they are UNLIKE how they work for regular lists.
If you check whether list L2 is inside list L1 in Python, L2 is cast to a
boolean value (True if not empty, False if empty) -- by that rule a Node that
contained one empty node and one non-empty one, would seem to contain any other
node you checked (even nodes from other documents). That's pretty useless in
this context, so "contains" and "in" are overridden for Node and its
subclasses, to check whether the actual node is an actual child.

* This raises an issue with what the boolean values of nodes should be.
An empty list in Python is conventionally false; but an empty Element in DOM
can still have all kinds of information via attributes, so probably should be
True -- it's not "empty" in the same way as a bare list of dict.
Similarly, Attr nodes implement bool() as the bool() of their *value*, so
testing "if myNode.getAttribute("x")" tells you if the attribute exists and
is non-empty, which sure seems Pythonic to me.

* On the other hand, DOM has a "contains" method (not an infix operator),
and "node1.contains(node2)" checks whether node2 is a *descendant*, not
just a child. That method is also available, and does what DOM days. However,
to avoid confusion the author recommends you use the synonymous
"node1.hasDescendant(node2)" instead.


==Semantic questions==

** Should Node be constructable?
** Should cloneNode copy userData and/or ownerDocument?
** Should removeAttribute___ unlink from ownerDoc/ownerEl?
** Effect of changing xmlns: attributes.

    # A Node is its own context manager, to ensure that an unlink() call occurs.
    # This is similar to how a file object works.
    def __enter__(self):
        return self

    def __exit__(self, et, ev, tb):
        self.unlink()


==Selectors==

* is [] with arguments beyond those of just list, more useful or confusing?

* How best to interface multiple/extended selectors?


==Namespaces==

* How should ns matching in the face of None and "" work?


==Whether/how to support EntityRefs==

They can be useful b/c:
** Transclusion could unify them (esp. external/system entities) with linking;
then they should be able to show up in many places.
** Sometimes you'd like to retain the physical structure, such as having
each chapter in a separate entity, or even which characters were references.

One way to do this is to tweak a parser to issue entity start/end events
with the name (many parsers hand back extra (non-normalized) text events for
this anyway). Then dombuilder could insert an EntRef node, with at least the
name, and then a subtree constructed under it. However, that makes the tree
topology not what you'd expect, so lots of operation would be much more complicated.

Another way is to annotate nodes created within an entity with that entity.
If we assume that nodes do not start in one entity and end in another (certainly
seems like good practice), then the annotation is only needed on the topmost
node(s) of each entity, perhaps with something helpful to distinguish the
first and/or last such.

For now, I'm ignoring EntRef nodes entirely, and things like innerXML,
outerXML, and insertAdjacentXML normalize.

* auto entities, unicode-name ents


==Classes==

* SituatedList/CompositionList?

* Perhaps derive from UserList instead of list?

* Should plainnode include the list dunders?

* The validator


==Methods==

* Should toprettyxml() etc. offer options to wrap text/comments?

* should `cloneNode()` copy `userData`?

* charset vs. inputencoding

* relation of removeChild to unlink. Is there a way to tell when it *really*
gets lost?

* Should things test for bad names?
    has/get/set/removeAttribute
    create Element / Attr / Document / PI target
    ID methods???

* Should the whatwg CharacterData ...data calls return the result?
Range errors? Negatives?

* Sync forEachSaxEvent with lxml.sax.saxify

* How best to make case, whitespace, etc. switchable?

* Should useNodePath() count from the node it's invoked on? Or maybe it should
only be on Document anyway?

* What should eq/ne/lt/le/ge/gt do?
For Elements document order seems far
more useful; but what of text, attrs, maybe other CharacterData, where
normal string compare might be better? Order on Attrs is weird -- all attrs
of same node would compare equal. Maybe hide these for CharacterData?

Or should Attr compare data? They don't have position....


==Exceptions==

* Should inner/outerXml
raise HierarchyRequestError, TypeError, or NotSupportedError?

* Python NotImplementedError vs. DOM NotSupportedError.

* Should (e.g.) child-related calls on CharacterData raise
HierarchyRequestError (as now and in minidom),
or NotImplementedError vs. DOM NotSupportedError
or InvalidModificationError or TypeError or InvalidNodeTypeError?

* mixin/inclusions -- dcl like incl exceptions?

* build in xinclude (switchable of course)

* sync doctype to tree.docinfo.internalDTD

* Direct DC support?

* global attributes?


==See also==

IBM’s Websphere Development Studio Client (WDSC) has a utility that converts
DTDs to XSDs.
