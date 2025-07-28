def greet(name):
    """Greets the given name."""
    return f"Hello, {name}!"

class Greeter:
    """A class to handle greetings.
    """
    def __init__(self, greeting_word="Hello"):
        self.greeting_word = greeting_word

    def say_hello(self, name):
        """Says hello to the given name."""
        return f"{self.greeting_word}, {name}!"

def main():
    user_name = "Alice"
    message = greet(user_name)
    print(message)

    my_greeter = Greeter("Hi")
    class_message = my_greeter.say_hello("Bob")
    print(class_message)

if __name__ == "__main__":
    main()
