import os
from dotenv import load_dotenv
from ollama import chat

load_dotenv()

NUM_RUNS_TIMES = 5

# TODO: Fill this in!
YOUR_SYSTEM_PROMPT = "You are a text processing assistant that can process input text according to user requirements " \
                     "and output text that meets the requirements. The output text does not have to be legal words or " \
                     "sentences, as long as it complies with the user's requests."

USER_PROMPT = """
Reverse the order of letters in the following word. Only output the reversed word, no other text:

httpstatus

Verify the output to ensure the original input word is fully recovered by reversing the output a second time.
Here are some examples:
<example>
Given original word "wonderful",return reversed word "lufrednow".
</example>

<example>
Given original word "help",return reversed word "pleh".
</example>

<example>
Given original word "ftp",return reversed word "ptf".
</example>
"""

#"""
#Reverse the order of letters in the following word. Only output the reversed word, no other text:
#
#httpstatus
#

# Here are some examples:
# <example>
# Given original word "wonderful",return reversed word "lufrednow".
# Given original word "Help",return reversed word "pleH*".
# Given original word "Help",return reversed word "pleH*".
# </example>"""


EXPECTED_OUTPUT = "sutatsptth"


def test_your_prompt(system_prompt: str) -> bool:
    """Run the prompt up to NUM_RUNS_TIMES and return True if any output matches EXPECTED_OUTPUT.

    Prints "SUCCESS" when a match is found.
    """
    for idx in range(NUM_RUNS_TIMES):
        print(f"Running test {idx + 1} of {NUM_RUNS_TIMES}")
        response = chat(
            model="mistral-nemo:12b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": USER_PROMPT},
            ],
            options={"temperature": 0.3},
        )
        output_text = response.message.content.strip()
        if output_text.strip() == EXPECTED_OUTPUT.strip():
            print("SUCCESS")
            return True
        else:
            print(f"Expected output: {EXPECTED_OUTPUT}")
            print(f"Actual output: {output_text}")
    return False


if __name__ == "__main__":
    test_your_prompt(YOUR_SYSTEM_PROMPT)