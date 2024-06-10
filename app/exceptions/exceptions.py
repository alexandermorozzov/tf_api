class BaseError(KeyError):
    def __init__(self, *args):
        if args:
            self.message = args[0]
        else:
            self.message = None

class TimeOutError(BaseError):
    def __str__(self):
        if self.message:
            return "TimeOutError, {0} ".format(self.message)
        else:
            return (
                "Timeout time exceeded:("
            )
        
class NoDataError(BaseError):
    def __str__(self):
        if self.message:
            return "No existing data in DB for: {0} ".format(self.message)
        else:
            return (
                "No Data in DB"
            )
        
class OutOfBoundaryError(BaseError):
    def __str__(self):
        if self.message:
            return "Starting point is out of city boundary: {0} ".format(self.message)
        else:
            return (
                "Bad starting point location"
            )