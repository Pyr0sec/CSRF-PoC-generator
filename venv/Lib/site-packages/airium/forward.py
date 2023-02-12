from dataclasses import dataclass, field
from types import TracebackType
from typing import List, Optional, Type


@dataclass
class Airium:
    base_indent: str = '  '
    current_level: int = 0
    source_minify: bool = False
    source_line_break_character: str = "\n"

    _doc_elements: List[str] = field(default_factory=list, repr=False)
    _most_recent: List['Tag'] = field(default_factory=list, repr=False)

    def __str__(self) -> str:
        self.flush_()
        return self.source_line_break_character.join(self._doc_elements)

    def __bytes__(self) -> bytes:
        return str(self).encode('utf-8')

    def __call__(self, text_str: str) -> None:
        self.flush_()
        self.append(text_str)

    def __getattr__(self, tag_name: str) -> Type['Tag']:
        self.flush_()
        return self.get_tag_(tag_name)

    def get_tag_(self, tag_name: str) -> Type['Tag']:
        doc = self  # avoid local name aliasing
        tag_name = Tag.TAG_NAME_SUBSTITUTES.get(tag_name, tag_name)  # e.g. 'del'

        if tag_name.strip() in doc.SINGLE_TAGS:

            class SingleTag(Tag):
                """E.g. '<img src="src.png" alt="alt text" />"""

                def __init__(self, *p: str, _t: str = None, **k: str):
                    super().__init__(tag_name, doc)
                    self.root.append(f'<{self.tag_name}{self._make_xml_args(*p, **k)} />{_t or ""}')

                def __enter__(self) -> None:
                    raise AttributeError(f"The tag: {self.tag_name!r} is a single tag, cannot be used with contexts.")

                def __exit__(
                    self,
                    exc_type: Optional[Type[BaseException]],
                    exc_value: Optional[BaseException],
                    traceback: Optional[TracebackType],
                ) -> None:  # pragma: no cover
                    """Cannot ever run exit since enter raises."""

                def __getattr__(self, tag_name: str) -> Type['Tag']:
                    raise AttributeError(f"{self.tag_name!r} is a single tag, creating its children is forbidden.")

            SingleTag.__name__ += f'_{tag_name}'  # for debug reasons
            return SingleTag

        else:
            class PairedTag(Tag):
                """E.g. '<div klass='panel'>...</div>"""

                def __init__(self, *p: str, _t: str = None, **k: str):
                    super().__init__(tag_name, doc)
                    self.root.append(f'<{self.tag_name}{self._make_xml_args(*p, **k)}>{_t or ""}')
                    self.root._most_recent.append(self)

                def __enter__(self) -> None:
                    self.entered = True
                    self.root.current_level += 1
                    self.opened = True

                def __exit__(
                    self,
                    exc_type: Optional[Type[BaseException]],
                    exc_value: Optional[BaseException],
                    traceback: Optional[TracebackType],
                ) -> None:
                    self.root.flush_()
                    self.finalize()
                    assert self.root._most_recent.pop() is self

                def __getattr__(self, tag_name: str) -> Type['Tag']:
                    """Chaining, e.g. ``a.ul().li().strong(_t='foo')``"""
                    return doc.get_tag_(tag_name)

                def finalize(self) -> None:
                    if self.opened:
                        self.root.current_level -= 1
                    self.root.append(f'</{self.tag_name}>', self.opened)

            PairedTag.__name__ += f'_{tag_name}'  # for debug reasons
            return PairedTag

    def flush_(self) -> None:
        """Close most recent opened tags.
        In case when we use a contextmanager without entering the context
        i.e.: regular call 'doc.div()` instead of `with doc.div():`
        there could be dangling unclosed tags. So we call the flush_ before each
        new tag or text creation."""
        while self._most_recent and not self._most_recent[-1].entered:
            self._most_recent.pop().finalize()

    def append(self, element: str, new_line: bool = True) -> None:
        is_pre = self._most_recent and self._most_recent[-1].tag_name.lower() == "pre"
        if is_pre or self.source_minify or not new_line:
            self._append_no_whitespaces(element)
        else:
            self._append_with_whitespaces(element)

    def _append_with_whitespaces(self, element: str) -> None:
        self._doc_elements.append(f"{self.base_indent * self.current_level}{element}")

    def _append_no_whitespaces(self, element: str) -> None:
        if not self._doc_elements:
            self._doc_elements.append(str(element))
        else:
            self._doc_elements[-1] += str(element)

    def break_source_line(self) -> "Airium":
        """To be used with self.source_minify=True if you would like to manualy split line.
        If you never call this function, your html code will most probably be contained in single-line."""
        self.flush_()
        self._doc_elements.append("")
        return self

    SINGLE_TAGS = [
        # You may change this list after import by overriding it, like this:
        # Airium.SINGLE_TAGS = ['hr', 'br', 'foo', 'ect']
        # or by extend or append:
        # Airium.SINGLE_TAGS.extend(['foo', 'ect'])
        'input', 'hr', 'br', 'img', 'area', 'link',
        'col', 'meta', 'base', 'param', 'wbr',
        'keygen', 'source', 'track', 'embed',
    ]


@dataclass
class Tag:
    tag_name: str
    root: Airium

    entered: bool = field(default=False, repr=False)
    opened: bool = field(default=False, repr=False)
    children_count: int = field(default=0, repr=False)

    def __post_init__(self) -> None:
        if self.root._most_recent:
            most_recent = self.root._most_recent[-1]
            if not most_recent.opened:
                self.root.current_level += 1
                most_recent.opened = True

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.tag_name!r})"

    def finalize(self) -> None:
        """Intentionally does nothing"""

    @classmethod
    def _make_xml_args(cls, *p: str, **k: str) -> str:
        ret = ''
        for positional in p:
            ret += f' {positional}'

        for key, value in k.items():
            key = str(key)  # sanity reasons
            value = str(value)  # sanity reasons
            normalized_key = cls.ATTRIBUTE_NAME_SUBSTITUTES.get(key, key)
            normalized_value = cls.ATTRIBUTE_VALUE_SUBSTITUTES.get(value, value)
            normalized_value = cls.escape_quotes(normalized_value)
            ret += ' {}="{}"'.format(normalized_key, normalized_value)

        return ret

    @staticmethod
    def escape_quotes(str_value: str) -> str:
        return str_value.replace('"', '&quot;')

    TAG_NAME_SUBSTITUTES = {
        'del_': 'del',
        'Del': 'del',
    }

    ATTRIBUTE_NAME_SUBSTITUTES = {
        # html tags colliding with python keywords
        'klass': 'class',
        'Class': 'class',
        'class_': 'class',
        'async_': 'async',
        'Async': 'async',
        'for_': 'for',
        'For': 'for',
        'In': 'in',
        'in_': 'in',

        # from XML
        'xmlns_xlink': 'xmlns:xlink',

        # from SVG ns
        'fill_opacity': 'fill-opacity',
        'stroke_width': 'stroke-width',
        'stroke_dasharray': ' stroke-dasharray',
        'stroke_opacity': 'stroke-opacity',
        'stroke_dashoffset': 'stroke-dashoffset',
        'stroke_linejoin': 'stroke-linejoin',
        'stroke_linecap': 'stroke-linecap',
        'stroke_miterlimit': 'stroke-miterlimit',

        # you may add translations to this dict after importing Tag class:
        # Tag.ATTRIBUTE_NAME_SUBSTITUTES.update({
        #   # e.g.
        #   'clas': 'class',
        #   'data_img_url_small': 'data-img_url_small',
        # })
    }

    ATTRIBUTE_VALUE_SUBSTITUTES = {
        'True': 'true',
        'False': 'false',
        'None': 'null',
    }
