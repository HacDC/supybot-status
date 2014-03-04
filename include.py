
import urllib2

plugin_name = 'Status'
default_msg = 'HacDC is %s since %s'

class StatusPluginException(Exception):
	pass

# tuple of exceptions which should be caught in the update loop
CatchAllExceptions = (ZeroDivisionError,urllib2.URLError, IOError, urllib2.HTTPError)

''' Notes on what not to catch
-- should fail --
callbacks.
	ArgumentError
	Error
	ProcessTimeoutError

dbi.
	InvalidDBError

plugins.
	NoSuitableDatabase

registry.
	RegistryException
	InvalidRegistryFile
	InvalidRegistryName
	InvalidRegistryValue

utils.
	web.
		Error
	error.
		Error
dbi.
	Error
	InvalidDBError

__builtin__.
	TypeError
	ValueError
	KeyError
	SyntaxError
	ImportError
	KeyboardInterrupt
	SystemExit

-- should never see --
plugins.
	Alias.
		plugin.
			AliasError
	AutoMode.
		plugin.
			Continue
	ShrinkUrl.
		plugin.
			ShrinkError
	Math.
		local.
			convertcore.
				UnitDataError

-- maybe --
depends on if anything in update.py might throw it without breaking anything.
__builtin__.
	IOError
'''
