import re
import json
import pyttsx3
import logging
import sqlite3
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from rich.console import Console
from difflib import SequenceMatcher


console = Console()

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.level = logging.DEBUG

DB_PATH = 'jeopardyStore.db'
CSV_PATH = 'jeopardy.csv'
JSON_PATH = 'jeopardyjson.json'


class SQLite:

    def __init__(self, file="") -> None:
        self.file = file

    def __enter__(self):
        self.conn = sqlite3.connect(self.file)
        return self.conn, self.conn.cursor()

    def __exit__(self, type, value, traceback):
        self.conn.close()


class SpeechSynthesizer:

    def __init__(self) -> None:
        self.engine = pyttsx3.init()

        # optional config
        # self.voices = self.engine.getProperty('voices')
        # self.engine.setProperty('voice', self.voices[0].id)

    def say(self, phrase: str) -> None:
        self.engine.say(phrase)
        self.engine.runAndWait()


def fill_db_with_json():
    try:
        with SQLite(DB_PATH) as (connection, cursor):
            cursor.execute(
                """CREATE TABLE Jeopardy (category VARCHAR(255), question VARCHAR(255), answer VARCHAR(255))""")
            cursor.execute(
                """CREATE INDEX Jeopardy_ques_ans ON Jeopardy(question, answer)""")
            with open(JSON_PATH, 'r') as json_data:
                games = json.load(json_data)
                for game in games:
                    data = (game['category'], game['question'], game['answer'])
                    cursor.execute(
                        "INSERT INTO Jeopardy VALUES (?,?,?);", data)
            connection.commit()
            logger.debug(
                "[*] Data has been successfully restored from jeopardy.")
            connection.close()
    except Exception as e:
        logger.warning("[*] Couldn't restore data from jeopardy")
        print(e)


def similar(a: str, b: str):
    return SequenceMatcher(None, a, b).ratio()


def contains_url(string: str):
    regex = r"(<a .*>)"
    url = re.findall(regex, string)
    if len(url) > 1:
        print("Found a url")
        return True
    else:
        return False


def cosine_similarity(x: str, y: str):

    # Tokenization
    x_list = word_tokenize(x.lower())
    y_list = word_tokenize(y.lower())

    # Remove stop words
    stop_words = stopwords.words('english')
    l1 = []
    l2 = []
    x_set = {word for word in x_list if not word in stop_words}
    y_set = {word for word in y_list if not word in stop_words}

    rvector = x_set.union(y_set)
    for w in rvector:
        if w in x_set:
            l1.append(1)
        else:
            l1.append(0)
        if w in y_set:
            l2.append(1)
        else:
            l2.append(0)

    c = 0
    for i in range(len(rvector)):
        c += l1[i] * l2[i]

    cosine = c / float((sum(l1) * sum(l2)) ** 0.5)
    return cosine


def get_question():
    query_list = []
    sql = "SELECT category, question, answer FROM Jeopardy ORDER BY RANDOM() LIMIT 1;"
    with SQLite(DB_PATH) as (connection, cursor):
        try:
            cursor.execute(sql)
            query_list = cursor.fetchall()
        except:
            connection.rollback()

        if contains_url(str(query_list[0][1])):
            try:
                cursor.execute(sql)
                query_list = cursor.fetchall()
            except:
                connection.rollback()

        # insert result into the json data object
        if len(query_list) > 0:
            category = str(query_list[0][0])
            question = str(query_list[0][1])
            answer = str(query_list[0][2])
        else:
            question = 'Something went wrong. I cannot ask questions right now.'

        return category, question, answer


stt = SpeechSynthesizer()


def main():
    keep_playing = True

    while keep_playing:
        category, question, answer = get_question()
        console.print(
            f"""Category: [bold][green]{category}[/][/] | Question: [yellow]{question.strip("'")}[/]""")
        stt.say(f"Category, {category}")
        stt.say(question)
        print("")
        user_answer = input("Enter your answer: ")
        print("")

        if user_answer == 'exit':
            keep_playing = False
        elif len(user_answer) < 2:
            user_answer = input("Enter a proper answer: ")

        similarity = similar(user_answer, answer)
        if similarity > 0.5:
            console.print("Right, the answer is", answer)
            stt.say(f"Right, the answer is {answer}")
            print("")
        else:
            console.print("Wrong, the answer is", answer)
            stt.say(f"Wrong, the answer is {answer}")
            print("")


if __name__ == "__main__":
    main()
