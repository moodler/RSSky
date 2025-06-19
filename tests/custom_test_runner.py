import unittest
import sys

class CustomTestResult(unittest.TextTestResult):
    """A custom test result class for colorful output."""
    
    GREEN = '\033[92m'
    RED = '\033[91m'
    RESET = '\033[0m'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.success_char = f"{self.GREEN}✅{self.RESET}"
        self.failure_char = f"{self.RED}❌{self.RESET}"

    def addSuccess(self, test):
        super().addSuccess(test)
        self.stream.writeln(f"{self.success_char} {self.getDescription(test)} ... {self.GREEN}ok{self.RESET}")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.stream.writeln(f"{self.failure_char} {self.getDescription(test)} ... {self.RED}FAIL{self.RESET}")

    def addError(self, test, err):
        super().addError(test, err)
        self.stream.writeln(f"{self.failure_char} {self.getDescription(test)} ... {self.RED}ERROR{self.RESET}")

    def printErrors(self):
        self.stream.writeln()
        self.printErrorList('ERROR', self.errors)
        self.printErrorList('FAIL', self.failures)

class CustomTestRunner(unittest.TextTestRunner):
    """A custom test runner that uses CustomTestResult."""
    
    resultclass = CustomTestResult

    def run(self, test):
        result = super().run(test)
        self.stream.writeln("-" * 70)
        
        # Custom summary line
        if result.wasSuccessful():
            summary = f"{CustomTestResult.GREEN}✅ All {result.testsRun} tests passed successfully.{CustomTestResult.RESET}"
        else:
            summary = f"{CustomTestResult.RED}❌ {len(result.failures) + len(result.errors)} of {result.testsRun} tests failed.{CustomTestResult.RESET}"
            
        self.stream.writeln(summary)
        return result