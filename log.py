import supybot.log as log
from include import plugin_name

logger = getPluginLogger(plugin_name)

def debug(*args):
	logger.debug(*args, exec_info=True)

def info(*args):
	logger.info(*args, exec_info=False)

def warning(*args):
	logger.warning(*args, exec_info=False)

def error(*args):
        logger.error(*args, exec_info=True)

def critical(*args):
	logger.critical(*args, exec_info=True)

def exception(*args):
	logger.exception(*args, exec_info=True)
