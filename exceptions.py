class SeedBotException(Exception):
    def __init__(self, message, *, send_reply=True, delete_origin=False, reply_on_private=False):
        self.send_reply = send_reply
        self.delete_origin = delete_origin
        self.reply_on_private = reply_on_private

        super().__init__(message)
