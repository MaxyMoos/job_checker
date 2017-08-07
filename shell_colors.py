class ANSIColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    ALL_COLORS = (OKBLUE, OKGREEN, WARNING, FAIL, BOLD, UNDERLINE)

    @staticmethod
    def wrap(text, color):
        if color in ANSIColors.ALL_COLORS:
            return color + text + ANSIColors.ENDC
        else:
            raise Exception("Color not supported")
