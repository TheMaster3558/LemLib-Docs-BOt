from markdownify import MarkdownConverter


class MarkdownConverterLocalLinks(MarkdownConverter):
    current_page_url: str

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def convert(self, html: str, current_page_url: str = '') -> str:
        self.current_page_url = current_page_url
        return super().convert(html)

    def convert_a(self, el: str, text: str, convert_as_inline: bool) -> str:
        # replace links to local pages like "#classlemlib_1_1Chassis" with the full link
        text = super().convert_a(el, text, convert_as_inline)
        text = text.replace('#', self.current_page_url + '#')
        return text
