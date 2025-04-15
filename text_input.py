# text_input.py
import logging

class TextInput:
    """Handles getting text input from the user."""

    def __init__(self, prompt: str = "Enter text to search for an image (or type 'quit' to exit): "):
        """
        Initializes the text input handler.

        Args:
            prompt (str): The message to display to the user.
        """
        self.prompt = prompt

    def get_text(self) -> str:
        """
        Prompts the user and returns the entered text.

        Returns:
            str: The text entered by the user.
        """
        try:
            user_input = input(self.prompt)
            return user_input.strip()
        except EOFError:
            logging.warning("EOF received, treating as quit.")
            return "quit" # Handle Ctrl+D or piped input ending