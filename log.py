import supybot.log as log
from include import plugin_name

logger = log.getPluginLogger(plugin_name)

def debug(*args):
	logger.debug(*args, exc_info=True)

def info(*args):
	logger.info(*args, exc_info=False)

def warn(*args):
	logger.warning(*args, exc_info=False)

def error(*args):
        logger.error(*args, exc_info=True)

def critical(*args):
	logger.critical(*args, exc_info=True)

def exception(*args):
	logger.exception(*args, exc_info=True)
