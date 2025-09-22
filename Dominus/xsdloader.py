#!/usr/bin/env python3
#
# XSD Loader for Schemera - uses expat to parse XSD files and populate DocumentType
#
import xml.parsers.expat as expat
from typing import Dict, List, Optional, Any, Union, Tuple
import logging
from collections import defaultdict

from documenttype import (
    DocumentType, ElementDef, AttrDef, SimpleType, ComplexType,
    Model, ModelGroup, ModelItem, ContentType, SeqType, RepType,
    DftType, AttrKey #, SourceThing
)
#from ragnaroktypes import NMTOKEN_t, QName_t
#from xsdtypes import XSDDatatypes

lg = logging.getLogger("xsdloader")

__metadata__ = {
    "title": "xsdloader",
    "description": "Load XSD schemas into Schemera DocumentType objects",
    "creator": "Claude & Steven J. DeRose",
    "created": "2025-01-27",
    "language": "Python 3.11",
}

# XSD namespace
XS_NS = "http://www.w3.org/2001/XMLSchema"

class XSDParseContext:
    """Tracks parsing state as we walk through the XSD"""
    def __init__(self):
        self.element_stack: List[Tuple[str, Dict[str, str]]] = []
        self.current_complex_type: Optional[ComplexType] = None
        self.current_simple_type: Optional[SimpleType] = None
        self.current_element: Optional[ElementDef] = None
        self.current_group_stack: List[ModelGroup] = []
        self.pending_particle_rep: Optional[RepType] = None
        self.target_namespace: Optional[str] = None
        self.namespace_prefixes: Dict[str, str] = {}

    def current_tag(self) -> Optional[str]:
        return self.element_stack[-1][0] if self.element_stack else None

    def current_attrs(self) -> Dict[str, str]:
        return self.element_stack[-1][1] if self.element_stack else {}

class XSDLoader:
    """Loads XSD schemas into Schemera DocumentType objects using expat"""

    def __init__(self, document_type: Optional[DocumentType] = None):
        self.document_type = document_type or DocumentType()
        self.context = XSDParseContext()
        self.parser = None

        # Maps for resolving forward references
        self.pending_type_refs: Dict[str, List[Any]] = defaultdict(list)
        self.defined_types: Dict[str, Union[SimpleType, ComplexType]] = {}
        self.global_elements: Dict[str, ElementDef] = {}
        self.global_attributes: Dict[str, AttrDef] = {}

    def load_from_file(self, filepath: str) -> DocumentType:
        """Load an XSD file and return populated DocumentType"""
        with open(filepath, 'rb') as f:
            return self.load_from_string(f.read())

    def load_from_string(self, xsd_content: Union[str, bytes]) -> DocumentType:
        """Load XSD from string content"""
        if isinstance(xsd_content, str):
            xsd_content = xsd_content.encode('utf-8')

        # xml.parsers.expat doesn't seem to have this...
        #self.parser = expat.ParserCreateNS(encoding='utf-8', namespace_separator='|')
        self.parser.StartElementHandler = self._start_element
        self.parser.EndElementHandler = self._end_element
        self.parser.CharacterDataHandler = self._char_data
        self.parser.StartNamespaceDeclHandler = self._start_namespace

        try:
            self.parser.Parse(xsd_content, True)
            self._resolve_pending_references()
            return self.document_type
        except expat.ExpatError as e:
            lg.error("XML parsing error: %s", e)
            raise
        except Exception as e:
            lg.error("XSD processing error: %s", e)
            raise

    def _start_namespace(self, prefix: str, uri: str) -> None:
        """Track namespace declarations"""
        self.context.namespace_prefixes[prefix or ''] = uri

    def _start_element(self, name: str, attrs: Dict[str, str]) -> None:
        """Handle start of XML element"""
        # Split namespace and local name
        if '|' in name:
            namespace, local_name = name.split('|', 1)
        else:
            namespace, local_name = '', name

        self.context.element_stack.append((local_name, attrs))

        # Only process XSD elements
        if namespace != XS_NS:
            return

        lg.debug("Processing XSD element: %s", local_name)

        # Dispatch to appropriate handler
        handler_name = f"_handle_{local_name.replace('-', '_')}"
        if hasattr(self, handler_name):
            getattr(self, handler_name)(attrs)
        else:
            lg.debug("No handler for XSD element: %s", local_name)

    def _end_element(self, name: str) -> None:
        """Handle end of XML element"""
        if '|' in name:
            namespace, local_name = name.split('|', 1)
        else:
            namespace, local_name = '', name

        if namespace == XS_NS:
            # Handle end of XSD elements
            end_handler_name = f"_end_{local_name.replace('-', '_')}"
            if hasattr(self, end_handler_name):
                getattr(self, end_handler_name)()

        self.context.element_stack.pop()

    def _char_data(self, data: str) -> None:
        """Handle character data - mostly ignored for XSD structure"""
        pass

    # XSD Element Handlers

    def _handle_schema(self, attrs: Dict[str, str]) -> None:
        """Handle xs:schema root element"""
        self.context.target_namespace = attrs.get('targetNamespace')
        lg.info("Processing schema with target namespace: %s", self.context.target_namespace)

    def _handle_element(self, attrs: Dict[str, str]) -> None:
        """Handle xs:element"""
        name = attrs.get('name')
        type_ref = attrs.get('type')
        min_occurs = int(attrs.get('minOccurs', '1'))
        max_occurs = attrs.get('maxOccurs', '1')

        if max_occurs == 'unbounded':
            max_occurs = -1  # UNLIMITED
        else:
            max_occurs = int(max_occurs)

        # Create repetition
        rep = self._make_repetition(min_occurs, max_occurs)

        if name:  # Global element declaration
            element_def = ElementDef(name, model=None, ownerSchema=self.document_type)

            if type_ref:
                # Reference to existing type - may need to resolve later
                self.pending_type_refs[type_ref].append(('element_type', element_def))

            self.global_elements[name] = element_def
            self.document_type.elementDefs[name] = element_def
            self.context.current_element = element_def

        else:  # Local element in content model
            ref = attrs.get('ref')
            if ref:
                # Element reference
                if self.context.current_group_stack:
                    item = ModelItem(ref, rep)
                    self.context.current_group_stack[-1].childItems.append(item)
            else:
                # Inline element declaration
                elem_name = attrs.get('name', 'anonymous')
                if self.context.current_group_stack:
                    item = ModelItem(elem_name, rep)
                    self.context.current_group_stack[-1].childItems.append(item)

    def _handle_complexType(self, attrs: Dict[str, str]) -> None:
        """Handle xs:complexType"""
        name = attrs.get('name')

        complex_type = ComplexType(
            name=name or 'anonymous',
            baseType=None  # Will be set if there's extension/restriction
        )

        if attrs.get('abstract') == 'true':
            complex_type.abstract = True

        if attrs.get('final'):
            complex_type.final = attrs['final']

        if attrs.get('block'):
            complex_type.block = attrs['block']

        self.context.current_complex_type = complex_type

        if name:
            self.defined_types[name] = complex_type

    def _end_complexType(self) -> None:
        """Handle end of xs:complexType"""
        if self.context.current_element and self.context.current_complex_type:
            # Attach the complex type to the current element
            self.context.current_element.model = self.context.current_complex_type.model
            self.context.current_element.attrDefs = self.context.current_complex_type.attrDefs

        self.context.current_complex_type = None

    def _handle_simpleType(self, attrs: Dict[str, str]) -> None:
        """Handle xs:simpleType"""
        name = attrs.get('name')

        simple_type = SimpleType(
            name=name or 'anonymous',
            baseType=None  # Will be set in restriction/extension
        )

        self.context.current_simple_type = simple_type

        if name:
            self.defined_types[name] = simple_type

    def _end_simpleType(self) -> None:
        """Handle end of xs:simpleType"""
        self.context.current_simple_type = None

    def _handle_sequence(self, attrs: Dict[str, str]) -> None:
        """Handle xs:sequence"""
        min_occurs = int(attrs.get('minOccurs', '1'))
        max_occurs = attrs.get('maxOccurs', '1')

        if max_occurs == 'unbounded':
            max_occurs = -1
        else:
            max_occurs = int(max_occurs)

        rep = self._make_repetition(min_occurs, max_occurs)

        group = ModelGroup(seq=SeqType.SEQUENCE, rep=rep)

        # Add to parent group or make it the model
        if self.context.current_group_stack:
            self.context.current_group_stack[-1].childItems.append(group)
        elif self.context.current_complex_type:
            self.context.current_complex_type.model = Model(
                tokens=None,
                contentType=ContentType.X_MODEL
            )
            self.context.current_complex_type.model.childItems = [group]
        elif self.context.current_element:
            self.context.current_element.model = Model(
                tokens=None,
                contentType=ContentType.X_MODEL
            )
            self.context.current_element.model.childItems = [group]

        self.context.current_group_stack.append(group)

    def _end_sequence(self) -> None:
        """Handle end of xs:sequence"""
        if self.context.current_group_stack:
            self.context.current_group_stack.pop()

    def _handle_choice(self, attrs: Dict[str, str]) -> None:
        """Handle xs:choice"""
        min_occurs = int(attrs.get('minOccurs', '1'))
        max_occurs = attrs.get('maxOccurs', '1')

        if max_occurs == 'unbounded':
            max_occurs = -1
        else:
            max_occurs = int(max_occurs)

        rep = self._make_repetition(min_occurs, max_occurs)
        group = ModelGroup(seq=SeqType.CHOICE, rep=rep)

        if self.context.current_group_stack:
            self.context.current_group_stack[-1].childItems.append(group)
        elif self.context.current_complex_type:
            self.context.current_complex_type.model = Model(
                tokens=None,
                contentType=ContentType.X_MODEL
            )
            self.context.current_complex_type.model.childItems = [group]
        elif self.context.current_element:
            self.context.current_element.model = Model(
                tokens=None,
                contentType=ContentType.X_MODEL
            )
            self.context.current_element.model.childItems = [group]

        self.context.current_group_stack.append(group)

    def _end_choice(self) -> None:
        """Handle end of xs:choice"""
        if self.context.current_group_stack:
            self.context.current_group_stack.pop()

    def _handle_all(self) -> None:
        """Handle xs:all.  TODO: attrs: Dict[str, str]?
        """
        # xs:all is like sequence but unordered, each element 0 or 1 time
        group = ModelGroup(seq=SeqType.ALL, rep=RepType.NOREP)

        if self.context.current_group_stack:
            self.context.current_group_stack[-1].childItems.append(group)
        elif self.context.current_complex_type:
            self.context.current_complex_type.model = Model(
                tokens=None,
                contentType=ContentType.X_MODEL
            )
            self.context.current_complex_type.model.childItems = [group]
        elif self.context.current_element:
            self.context.current_element.model = Model(
                tokens=None,
                contentType=ContentType.X_MODEL
            )
            self.context.current_element.model.childItems = [group]

        self.context.current_group_stack.append(group)

    def _end_all(self) -> None:
        """Handle end of xs:all"""
        if self.context.current_group_stack:
            self.context.current_group_stack.pop()

    def _handle_attribute(self, attrs: Dict[str, str]) -> None:
        """Handle xs:attribute"""
        name = attrs.get('name')
        type_ref = attrs.get('type', 'xs:string')  # Default to string
        use = attrs.get('use', 'optional')
        default = attrs.get('default')
        fixed = attrs.get('fixed')

        # Map XSD use to Schemera DftType
        if use == 'required':
            dft_type = DftType.REQUIRED
        elif fixed:
            dft_type = DftType.FIXED
        else:
            dft_type = DftType.IMPLIED

        if name:  # Global attribute
            attr_def = AttrDef(
                elemNS=self.context.target_namespace,
                elemName=None,  # Global - not tied to specific element
                attrNS=self.context.target_namespace,
                attrName=name,
                attrType=self._resolve_type_name(type_ref),
                attrDft=dft_type,
                literal=default or fixed,
                ownerSchema=self.document_type
            )

            self.global_attributes[name] = attr_def

        else:  # Local attribute
            ref = attrs.get('ref')
            if ref and self.context.current_complex_type:
                # Attribute reference
                self.pending_type_refs[ref].append(
                    ('attribute_ref', self.context.current_complex_type))
            elif self.context.current_complex_type and name:
                # Local attribute declaration
                attr_def = AttrDef(
                    elemNS=self.context.target_namespace,
                    elemName=None,  # Will be set when attached to element
                    attrNS=self.context.target_namespace,
                    attrName=name,
                    attrType=self._resolve_type_name(type_ref),
                    attrDft=dft_type,
                    literal=default or fixed,
                    ownerSchema=self.document_type
                )

                # Add to current complex type
                attr_key = AttrKey(
                    self.context.target_namespace, None,
                    self.context.target_namespace, name
                )
                self.context.current_complex_type.attrDefs[attr_key] = attr_def

    def _handle_restriction(self, attrs: Dict[str, str]) -> None:
        """Handle xs:restriction"""
        base = attrs.get('base')

        if self.context.current_simple_type:
            self.context.current_simple_type.baseType = self._resolve_type_name(base)
        elif self.context.current_complex_type:
            self.context.current_complex_type.baseType = self._resolve_type_name(base)

    def _handle_extension(self, attrs: Dict[str, str]) -> None:
        """Handle xs:extension"""
        base = attrs.get('base')

        if self.context.current_simple_type:
            self.context.current_simple_type.baseType = self._resolve_type_name(base)
        elif self.context.current_complex_type:
            self.context.current_complex_type.baseType = self._resolve_type_name(base)

    # Constraint/facet handlers for simple types

    def _handle_enumeration(self, attrs: Dict[str, str]) -> None:
        """Handle xs:enumeration facet"""
        if self.context.current_simple_type:
            value = attrs.get('value')
            if 'enumeration' not in self.context.current_simple_type.restrictions:
                self.context.current_simple_type.restrictions['enumeration'] = []
            self.context.current_simple_type.restrictions['enumeration'].append(value)

    def _handle_pattern(self, attrs: Dict[str, str]) -> None:
        """Handle xs:pattern facet"""
        if self.context.current_simple_type:
            value = attrs.get('value')
            self.context.current_simple_type.restrictions['pattern'] = value

    def _handle_minInclusive(self, attrs: Dict[str, str]) -> None:
        """Handle xs:minInclusive facet"""
        if self.context.current_simple_type:
            value = attrs.get('value')
            self.context.current_simple_type.restrictions['minInclusive'] = value

    def _handle_maxInclusive(self, attrs: Dict[str, str]) -> None:
        """Handle xs:maxInclusive facet"""
        if self.context.current_simple_type:
            value = attrs.get('value')
            self.context.current_simple_type.restrictions['maxInclusive'] = value

    def _handle_minExclusive(self, attrs: Dict[str, str]) -> None:
        """Handle xs:minExclusive facet"""
        if self.context.current_simple_type:
            value = attrs.get('value')
            self.context.current_simple_type.restrictions['minExclusive'] = value

    def _handle_maxExclusive(self, attrs: Dict[str, str]) -> None:
        """Handle xs:maxExclusive facet"""
        if self.context.current_simple_type:
            value = attrs.get('value')
            self.context.current_simple_type.restrictions['maxExclusive'] = value

    def _handle_minLength(self, attrs: Dict[str, str]) -> None:
        """Handle xs:minLength facet"""
        if self.context.current_simple_type:
            value = attrs.get('value')
            self.context.current_simple_type.restrictions['minLength'] = int(value)

    def _handle_maxLength(self, attrs: Dict[str, str]) -> None:
        """Handle xs:maxLength facet"""
        if self.context.current_simple_type:
            value = attrs.get('value')
            self.context.current_simple_type.restrictions['maxLength'] = int(value)

    def _handle_length(self, attrs: Dict[str, str]) -> None:
        """Handle xs:length facet"""
        if self.context.current_simple_type:
            value = attrs.get('value')
            self.context.current_simple_type.restrictions['length'] = int(value)

    # Utility methods

    def _make_repetition(self, min_occurs: int, max_occurs: int) -> RepType:
        """Create appropriate RepType for occurrence constraints"""
        if min_occurs == 1 and max_occurs == 1:
            return RepType.NOREP
        elif min_occurs == 0 and max_occurs == 1:
            return RepType.QUEST
        elif min_occurs == 0 and max_occurs == -1:
            return RepType.STAR
        elif min_occurs == 1 and max_occurs == -1:
            return RepType.PLUS
        else:
            # Custom bounds - use X_BOUNDS
            rep = RepType.X_BOUNDS
            rep.setBounds(min_occurs, max_occurs)
            return rep

    def _resolve_type_name(self, type_ref: str) -> str:
        """Resolve type reference to actual type name"""
        if ':' in type_ref:
            prefix, local_name = type_ref.split(':', 1)
            if prefix == 'xs' or prefix == 'xsd':
                # Built-in XSD type
                return local_name

        # Local type or unqualified built-in
        return type_ref

    def _resolve_pending_references(self) -> None:
        """Resolve forward references after parsing is complete"""
        for type_name, references in self.pending_type_refs.items():
            resolved_type = self.defined_types.get(type_name)
            if not resolved_type:
                lg.warning("Could not resolve type reference: %s", type_name)
                continue

            for ref_type, target in references:
                if ref_type == 'element_type' and isinstance(target, ElementDef):
                    if isinstance(resolved_type, ComplexType):
                        target.model = resolved_type.model
                        target.attrDefs = resolved_type.attrDefs
                    # For simple types, the element content is just text

                elif ref_type == 'attribute_ref' and isinstance(target, ComplexType):
                    # Add referenced global attribute to complex type
                    if type_name in self.global_attributes:
                        attr = self.global_attributes[type_name]
                        attr_key = AttrKey(
                            self.context.target_namespace, None,
                            attr.attrNS, attr.attrName
                        )
                        target.attrDefs[attr_key] = attr


def load_xsd_file(filepath: str, document_type: Optional[DocumentType] = None) -> DocumentType:
    """Convenience function to load an XSD file"""
    loader = XSDLoader(document_type)
    return loader.load_from_file(filepath)


def load_xsd_string(xsd_content: Union[str, bytes],
    document_type: Optional[DocumentType] = None) -> DocumentType:
    """Convenience function to load XSD from string"""
    loader = XSDLoader(document_type)
    return loader.load_from_string(xsd_content)


# Example usage:
if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python xsdloader.py <xsd_file>")
        sys.exit(1)

    logging.basicConfig(level=logging.INFO)

    try:
        doc_type = load_xsd_file(sys.argv[1])
        print(f"Loaded schema with {len(doc_type.elementDefs)} elements")
        print(f"Elements: {list(doc_type.elementDefs.keys())}")

        # Print some details
        for elemName, elem_def in doc_type.elementDefs.items():
            print(f"\nElement: {elemName}")
            if elem_def.model:
                print(f"  Model: {elem_def.model.tostring()}")
            if elem_def.attrDefs:
                print(f"  Attributes: {list(elem_def.attrDefs.keys())}")

    except Exception as e0:
        lg.error("Failed to load XSD: %s", e0)
        import traceback
        traceback.print_exc()
        sys.exit(1)
