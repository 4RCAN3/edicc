import fandom
from fandom import FandomPage
from fandom.error import FandomException, PageError
import copy
from bs4 import BeautifulSoup, NavigableString, Tag
import re

WIKI = ""
LANG = ""


class FandomPageOverride(FandomPage):
    """
    Overrides the FandomPage class
    """

    def __init__(self, wiki, language, title=None, pageid=None, redirect=True, preload=False):
        super().__init__(wiki, language, title, pageid, redirect, preload)

    @property
    def content(self):
        """
        Text content of each section of the page, excluding images, tables,
        and other data. The content is returned as dict, imitating the section and
        subsection structure of the page.

        .. note::
          If you just want the plain text of the page without the section structure, you can use FandomPage.plain_text

        :returns: :class:`dict`
        """

        def clean(content):
            keys = list(content.keys())
            if 'sections' in content:
                keys.remove('sections')

            for key in keys:
                if content[key] != "":
                    content[key] = re.sub(u'\xa0', ' ', content[key])
                    content[key] = re.sub(r'\[.*?\]', '', content[key])
                    content[key] = re.sub(' +', ' ', content[key])
                    content[key] = re.sub('\n+', '\n', content[key])
                    if content[key] == "\n":
                        content[key] = ""
                    else:
                        content[key] = content[key][1:] if content[key][0] == '\n' else content[key]
                        content[key] = content[key][:-
                                                    1] if content[key][-1] == '\n' else content[key]

            if 'sections' in content:
                for s in content['sections']:
                    s = clean(s)

            return content

        if not getattr(self, '_content', False):
            html = self.html
            soup = BeautifulSoup(html, 'html.parser')

            page_content = copy.copy(
                soup.find('div', class_="mw-parser-output"))

            infoboxes = page_content.find_all(
                'aside', class_="portable-infobox")
            infobox_content = ""
            for box in infoboxes:
                infobox_content += box.text
                box.decompose()

            toc = page_content.find('div', id='toc')
            if toc:
                toc.decompose()

            message_boxes = page_content.find_all('table', class_="messagebox")
            for box in message_boxes:
                box.decompose()

            captions = page_content.find_all('p', class_="caption")
            for caption in captions:
                caption.decompose()

            nav_boxes = page_content.find_all('table', class_="navbox")
            for box in nav_boxes:
                box.decompose()

            content = {'title': self.title}
            level_tree = [content]
            current_level = 1

            next_node = page_content.contents[0]
            while isinstance(next_node, NavigableString) or next_node.name in ["div", "figure", "table"]:
                next_node = next_node.nextSibling

            section_text = ""
            while True:
                if next_node is None:
                    level_tree[-1]['content'] = section_text
                    break
                elif isinstance(next_node, Tag):
                    if next_node.name[0] == 'h':
                        level_tree[-1]['content'] = section_text
                        header = next_node.text
                        header_level = int(next_node.name[1])
                        if header_level > current_level:
                            level_dif = header_level - current_level
                            for _ in range(level_dif):
                                level_tree[-1]['sections'] = [
                                    {'title': header}]
                                level_tree.append(
                                    level_tree[-1]['sections'][0])
                        elif header_level == current_level:
                            level_tree[-2]['sections'].append(
                                {'title': header})
                            level_tree[-1] = level_tree[-2]['sections'][-1]
                        else:
                            level_dif = header_level - current_level
                            level_tree = level_tree[:level_dif]
                            level_tree[-2]['sections'].append(
                                {'title': header})
                            level_tree[-1] = level_tree[-2]['sections'][-1]

                        section_text = ""
                        current_level = header_level
                    # elif next_node.name == 'div':
                    elif (not next_node.has_attr('class')) or (next_node['class'] != "printfooter"):
                        section_text += "\n"+next_node.get_text()
                next_node = next_node.nextSibling

            if infobox_content != "":
                content['infobox'] = infobox_content

            self._content = clean(content)
        return self._content


def pageOverride(title: str = "", pageid: int = -1, wiki: str = WIKI, language: str = LANG, redirect: bool = True, preload: bool = False):
    """
    Get a FandomPage object for the page in the sub fandom with title or the pageid (mutually exclusive).

    :param title: - the title of the page to load
    :param pageid: The numeric pageid of the page to load
    :param wiki: The wiki to search (defaults to the global wiki variable. If the global wiki variable is not set, defaults to "runescape")
    :param language: The language to search in (defaults to the global language variable. If  the global language variable is not set, defaults to english)
    :param redirect: Allow redirection without raising RedirectError
    :param preload: Load content, summary, images, references, and links during initialization
    :type title: str
    :type pageid: int
    :type wiki: str
    :type language: str
    :type redirect: bool
    :type preload: bool
    """

    wiki = wiki if wiki != "" else (WIKI if WIKI != "" else "runescape")
    language = language if language != "" else (LANG if LANG != "" else "en")

    if title != "":
        return FandomPageOverride(wiki, language, title=title, redirect=redirect, preload=preload)
    elif pageid != -1:
        return FandomPageOverride(wiki, language, pageid=pageid, preload=preload)
    else:
        raise ValueError("Either a title or a pageid must be specified")


class NoChar(FandomException):
    """
    No. of tries exceeded after page refresh.
    """

    def __init__(self, error):
        super().__init__(error)

    def __unicode__(self):
        return super().__unicode__()


def fetch(char, ReFetch=False):
    """
    Returns the character profile of the requested Character

    :char: - The character name to get the prompt for
    """

    char = '-'.join([word.capitalize() for word in char.split('-')]
                    ) if '-' in char else ' '.join([word.capitalize() for word in char.split(' ')])
    print(char)
    try:
        fandom.page = pageOverride
        summ = fandom.page(char, wiki='marvelcinematicuniverse')
        prompt = summ.plain_text

        return prompt

    except PageError:
        if ReFetch:
            raise NoChar(PageError)
        else:
            char = char.replace(
                ' ', '-') if '-' in char else char.replace(' ', '-')
            print(char)
            return fetch(char, ReFetch=True)
