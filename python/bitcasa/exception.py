class BitcasaException(Exception):
    def __init__(self, code, *args, **kwargs):
        self.code = code
        super(BitcasaException, self).__init__(*args, **kwargs)
