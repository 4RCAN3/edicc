import tweepy
import os
from dotenv import load_dotenv
from fandom.error import PageError
import openai
from openai.error import InvalidRequestError
import fetch
from fetch import NoChar
import re

load_dotenv()
BEARER_TOKEN = os.environ.get('BEARER')
global WORKERS
WORKERS = {}
openai.api_key = os.environ.get("OPENAI_API_KEY")


class CharacterAi():

    def __init__(self, Question: str, author: str, **kwrgs) -> None:
        """
        CharacterAi: creates a response for a prompt fetched through the WORKERS

        Args:
            Question (str): The original text to create a response for
            author (str): The author of the question to fetch the prompt

        Optional Params:
            Creativity: A number between 0 and 0.9
        """

        self.char = WORKERS[author][0]
        self.prompt = WORKERS[author][1]
        self.question = Question
        self.author = author
        self.temp = kwrgs.get('Creativity', 0.9)

    def filterPrompt(self) -> str:
        """
        Reduces the length of the prompt to satisfy the maximum numbr of tokens
        """

        prompt = self.prompt
        currLength = len(prompt)
        prompt = prompt[:16000] if currLength > 16000 else prompt[:currLength-100]
        self.prompt = prompt  # Sets the original prompt to the reduced prompt

        return self.getResponse()

    def getResponse(self) -> str:
        """
        Tweets out the response to the question -> self.question
        """

        try:
            response = openai.Completion.create(
                model="text-davinci-002",
                prompt=f"""The following is a conversation with {self.char}.
{self.prompt}

YOU: {self.question}""",

                temperature=self.temp,
                max_tokens=70,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0.6,
                stop=[" YOU:", f" {self.char}:"]
            )
            WORKERS[self.author][1] = self.prompt

            text = ' '.join(response['choices'][0]['text'].split(':')[1:])

            return text

        except InvalidRequestError:
            """
            Reduce the prompt length if maximum tokens reached
            """

            return self.filterPrompt()


class Stream(tweepy.StreamingClient):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        """__init__( \
            bearer_token, *, return_type=Response, wait_on_rate_limit=False, \
            chunk_size=512, daemon=False, max_retries=inf, proxy=None, \
            verify=True \
        )
        """

        API_KEY = os.environ.get('API_KEY')
        API_SECRET_KEY = os.environ.get('API_SECRET_KEY')
        ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')
        ACCESS_TOKEN_SECRET = os.environ.get('ACCESS_TOKEN_SECRET')

        self.client = tweepy.Client(BEARER_TOKEN, API_KEY, API_SECRET_KEY,
                                    ACCESS_TOKEN, ACCESS_TOKEN_SECRET, wait_on_rate_limit=True)

    def on_connect(self):
        print('Stream started')

    def on_errors(self, errors):
        print(errors)

    def on_tweet(self, tweet):
        """
        Works on the tweet that has mentioned the account
        Args:
            tweet (obj): tweet object that is fetched
        """

        author = tweet.author_id

        # Passes bot replies
        if str(author) == '1574513358568505345':
            return None

        print('found tweet')
        client = self.client

        tweetText = tweet.data['text']

        # Creating the prompt
        if re.search('create', tweetText, re.IGNORECASE):
            if author not in WORKERS.keys():
                Character = ' '.join(tweetText.split(' ')[2:])
                try:
                    prompt = fetch.fetch(Character)
                    WORKERS[author] = [Character, prompt]
                    response = f"""Congratulations. A prompt for the character - {Character} has been created.
You can now converse with the bot. Happy chatting!"""
                    client.create_tweet(
                        text=response, in_reply_to_tweet_id=tweet.id)
                except NoChar:
                    response = f"""Hello, Either the following character ({Character}) is not present in the database, or the format for creating a character is not correct. 
Please refer https://marvelcinematicuniverse.fandom.com/wiki/Marvel_Cinematic_Universe_Wiki to get a list of creatable characters. Thank you"""
                    client.create_tweet(
                        text=response, in_reply_to_tweet_id=tweet.id)
            else:
                response = f"""Hello, It seems like you have already created a character. You can only create one character per user.
Please destroy the previous character before creating a new one. Thank you."""
                client.create_tweet(
                    text=response, in_reply_to_tweet_id=tweet.id)

        #Destroying the prompt
        elif re.search('destroy', tweetText, re.IGNORECASE):
            if author in WORKERS.keys():
                del WORKERS[author]
                response = """We have deleted the character you created. This character is probably dead in the mcu anyways."""
                client.create_tweet(
                    text=response, in_reply_to_tweet_id=tweet.id)

            else:
                response = """Hello, It seems like you haven't created a character yet. To destroy a being, you must create one!
Now, go ahead, create a new character. Have a little fun with it. Then destroy it. Thank you."""
                client.create_tweet(
                    text=response, in_reply_to_tweet_id=tweet.id)

        #Replying to the text using the prompt
        else:
            tweetText = tweetText.replace('eDicc_NotAnAi', '')
            tweetText, temp = (' '.join(tweetText.split(' ')[:-2]),
                               tweetText.split(' ')[-1]) if re.search('creativity', tweetText, re.IGNORECASE) else (tweetText, 0.9)
            AI = CharacterAi(Question=tweetText, author=author,
                             Client=client, Creativity=float(temp), id=tweet.id)

            response = AI.getResponse()
            print(response)
            client.create_tweet(text=response, in_reply_to_tweet_id=tweet.id)
            pass


if __name__ == '__main__':
    """
    Start streaming of tweets
    """    
    stream = Stream(bearer_token=BEARER_TOKEN, wait_on_rate_limit=True)
    stream.delete_rules([1574519705590591489])
    rule = '@eDicc_NotAnAi'
    stream.add_rules(tweepy.StreamRule(rule))

    print(stream.get_rules())
    stream.filter(tweet_fields=['conversation_id', 'referenced_tweets'], user_fields=[
                  'username'], expansions=['author_id'])
