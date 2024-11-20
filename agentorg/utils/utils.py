import os
import sys
import json
import logging
from logging.handlers import RotatingFileHandler

import tiktoken
import Levenshtein

logger = logging.getLogger(__name__)


def init_logger(log_level=logging.INFO, filename=None):
	handlers = [logging.StreamHandler(sys.stdout)]
	if filename is not None:
		directory_name, _ = os.path.split(filename)
		if not os.path.exists(directory_name):
			os.makedirs(directory_name)
		rfh = RotatingFileHandler(
			filename=filename, 
			mode='a',
			maxBytes=50*1024*1024,
			backupCount=20,
			encoding=None,
			delay=0
		)
		# handlers.append(logging.FileHandler(filename=filename))
		handlers.append(rfh)
	logging.basicConfig(
		datefmt="%m/%d/%Y %H:%M:%S",
		level=log_level,
		format="[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s",
		handlers=handlers,
	)
	logging.getLogger("transformers.tokenization_utils").setLevel(logging.ERROR)
	logging.getLogger("transformers.tokenization_utils_base").setLevel(logging.ERROR)
	return logging.getLogger(__name__)


def chunk_string(text, tokenizer, max_length, from_end=True):
    # Initialize the tokenizer
	encoding = tiktoken.get_encoding(tokenizer)
	tokens = encoding.encode(text)
	if from_end:
		chunks = encoding.decode(tokens[-max_length:])
	else:
		chunks = encoding.decode(tokens[:max_length])
	return chunks

def normalize(lst):
		return [float(num)/sum(lst) for num in lst]

def str_similarity(string1, string2):
	try:
		distance = Levenshtein.distance(string1, string2)
		max_length = max(len(string1), len(string2))
		similarity = 1 - (distance / max_length)
	except Exception as err:
		print(err)
		similarity = 0
	return similarity


def postprocess_json(raw_code):
	valid_phrases = ['"', '{', '}', '[', ']']

	valid_lines = []
	for line in raw_code.split('\n'):
		if len(line) == 0:
			continue
		# If the line not starts with any of the valid phrases, skip it
		should_skip = not any([line.strip().startswith(phrase) for phrase in valid_phrases])
		if should_skip:
			continue
		valid_lines.append(line)

	try:
		generated_result = "\n".join(valid_lines)
		result = json.loads(generated_result)
	except json.JSONDecodeError as e:
		logger.error(f"Error decoding generated JSON - {generated_result}")
		logger.error(f"raw result: {raw_code}")
		logger.error(f"Error: {e}")
		result = None
	return result