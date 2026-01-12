import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("automl-llm")


# this is the initial module of your app
# this is executed whenever some client-code is calling `import automl-llm` or `from automl-llm import ...`
# put your main classes here, eg:
class MyClass:
    def my_method(self):
        return "Hello World"


def main():
    # this is the main module of your app
    # it is only required if your project must be runnable
    # this is the script to be executed whenever some users writes `python -m automl-llm` on the command line, eg.
    x = MyClass().my_method()
    print(x)


# let this be the last line of this file
logger.info("automl-llm loaded")
