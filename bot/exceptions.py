class FrompsBotException(Exception):
    def __init__(self, message, reply_on_private=False):
        super().__init__(message)
        self.reply_on_private = reply_on_private
