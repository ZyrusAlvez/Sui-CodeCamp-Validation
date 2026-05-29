from clean import clean
from validate import validate

INPUT_FILE = "test.csv"
CLEANED_FILE = "cleaned.csv"
RESULTS_FILE = "results.csv"

clean(INPUT_FILE, CLEANED_FILE)
validate(CLEANED_FILE, RESULTS_FILE)
