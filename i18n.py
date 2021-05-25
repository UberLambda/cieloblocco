import gettext
from pathlib import Path

# TODO: Search the system-wide, /usr/share/locale if installed?
locale_dir = Path(__file__).parent() / 'locale'
gettext.bindtextdomain('cieloblocco', locale_dir)
gettext.textdomain('cieloblocco')

tr = gettext.gettext
trn = gettext.ngettext
