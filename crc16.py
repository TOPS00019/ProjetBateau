class CRC16:
    def __init__(self) -> None:
        """Simple CRC-16 helper using polynomial 0x8005.

        The class currently holds no state but provides two convenience
        methods: compute_crc() to compute a 16-bit CRC for a bitstring
        and verify_crc() to compare an expected CRC with a payload.
        """
        pass


    def compute_crc(self, bits: str) -> str:
        """Compute a 16-bit CRC for a binary string.

        The function treats the input as a sequence of bits (characters
        '0' or '1') and performs a left-shifting CRC algorithm using the
        polynomial 0x8005. The returned value is a 16-character string of
        '0'/'1' representing the computed CRC.

        Parameters
        ----------
        bits : str
            String with characters '0' or '1'.

        Returns
        -------
        str
            16-bit binary string with the CRC value.
        """
        poly = 0x8005
        init_crc = 0x0000
        bits = [int(bit) for bit in bits]
        crc = init_crc
        for bit in bits:
            msb = (crc >> 15) & 1
            crc = ((crc << 1) & 0xFFFF) | bit
            if msb:
                crc ^= poly
        return format(crc, "016b")


    def verify_crc(self, bits: str, crc: str) -> bool:
        """Verify that the provided crc matches the computed CRC.

        Parameters
        ----------
        bits : str
            Payload bitstring used to compute the CRC.
        crc : str
            Expected CRC represented as a 16-character bitstring.
        """
        return self.compute_crc(bits) == crc
