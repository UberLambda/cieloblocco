import gettext
from pathlib import Path

# TODO: Search the system-wide, /usr/share/locale if installed?
locale_dir = Path(__file__).parent / 'locale'
gettext.bindtextdomain('cieloblocco', locale_dir)
gettext.textdomain('cieloblocco')


def tr(key: str, *args, **kwargs) -> str:
    return gettext.gettext(key).format(*args, **kwargs)


def trn(singular: str, plural: str, *args, **kwargs) -> str:
    return gettext.ngettext(singular, plural).format(*args, **kwargs)
