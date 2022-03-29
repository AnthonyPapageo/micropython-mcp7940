class MCP7940:
    """
        Example usage:

            # Read time
            mcp = MCP7940(i2c)
            time = mcp.time # Read time from MCP7940
            is_leap_year = mcp.is_leap_year() # Is the year in the MCP7940 a leap year?

            # Set time
            ntptime.settime() # Set system time from NTP
            mcp.time = utime.localtime() # Set the MCP7940 with the system time
    """
    ADDRESS = 0x6F
    RTCSEC = 0x00  # RTC seconds register
    ST = 7  # Status bit
    RTCWKDAY = 0x03  # RTC Weekday register
    VBATEN = 3  # External battery backup supply enable bit
    ALM0EN = 4
    ALM1EN = 5
    ALM0WKDAY = 0xD
    ALM1WKDAY = 0x14
    CONTROL = 0x07
    OUTPUT = 8
    ALMPOL = 7

    def __init__(self, bus, status=True, battery_enabled=True):
        self._bus = bus
        self.clear_output()
        self.battery_backup_enable(1)

    def start(self):
        self._set_bit(MCP7940.RTCSEC, MCP7940.ST, 1)

    def stop(self):
        self._set_bit(MCP7940.RTCSEC, MCP7940.ST, 0)

    def clear_output(self):
        self._bus.write_byte_data(MCP7940.ADDRESS, MCP7940.CONTROL, 0x00)

    def is_started(self):
        return self._read_bit(MCP7940.RTCSEC, MCP7940.ST)

    def battery_backup_enable(self, enable):
        self._set_bit(MCP7940.RTCWKDAY, MCP7940.VBATEN, enable)

    def is_battery_backup_enabled(self):
        return self._read_bit(MCP7940.RTCWKDAY, MCP7940.VBATEN)

    def _set_bit(self, register, bit, value):
        """ Set only a single bit in a register. To do so, need to read
            the current state of the register and modify just the one bit.
        """
        mask = 1 << bit
        current = self._bus.read_byte_data(MCP7940.ADDRESS, register)
        updated = (current & ~mask) | ((value << bit) & mask)
        self._bus.write_byte_data(MCP7940.ADDRESS, register, updated)

    def _read_bit(self, register, bit):
        register_val = self._bus.read_byte_data(MCP7940.ADDRESS, register)
        return (register_val[0] & (1 << bit)) >> bit

    @property
    def time(self):
        return self._get_time()

    @time.setter
    def time(self, t):
        year, month, date, hours, minutes, seconds, weekday, yearday, _ = t
        # Reorder
        time_reg = [seconds, minutes, hours, weekday + 1, date, month, year % 100]

        # Add ST (status) bit

        # Add VBATEN (battery enable) bit

        reg_filter = (0x7F, 0x7F, 0x3F, 0x07, 0x3F, 0x3F, 0xFF)
        # t = bytes([MCP7940.bcd_to_int(reg & filt) for reg, filt in zip(time_reg, reg_filter)])
        t = [(MCP7940.int_to_bcd(reg) & filt) for reg, filt in zip(time_reg, reg_filter)]
        # Note that some fields will be overwritten that are important!
        # fixme!
        self._bus.write_i2c_block_data(MCP7940.ADDRESS, 0x00, t)

    def alarm1(self):
        return self._get_time(start_reg=0x0A)

    def alarm1(self, t):
        year, month, date, hours, minutes, seconds, weekday, yearday, _ = t  # Don't need year or yearday
        # Reorder
        time_reg = [seconds, minutes, hours, weekday + 1, date, month]
        reg_filter = (0x7F, 0x7F, 0x3F, 0x07, 0x3F, 0x3F)  # No year field for alarms
        t = [(MCP7940.int_to_bcd(reg) & filt) for reg, filt in zip(time_reg, reg_filter)]
        self._bus.write_i2c_block_data(MCP7940.ADDRESS, 0x0A, t)
        self._set_bit(MCP7940.CONTROL,MCP7940.ALM0EN,1)
        register_val = self._bus.read_byte_data(MCP7940.ADDRESS, MCP7940.ALM0WKDAY)
        register_val = register_val | 0x70 #set MSK
        register_val = register_val & 0xF7 #clear previous alarm flag
        self._bus.write_byte_data(MCP7940.ADDRESS,MCP7940.ALM0WKDAY,register_val)

    def alarm2(self):
        return self._get_time(start_reg=0x11)

    def alarm2(self, t):
        year, month, date, hours, minutes, seconds, weekday, yearday, _ = t  # Don't need year or yearday
        # Reorder
        time_reg = [seconds, minutes, hours, weekday + 1, date, month]
        reg_filter = (0x7F, 0x7F, 0x3F, 0x07, 0x3F, 0x3F)  # No year field for alarms
        t = [(MCP7940.int_to_bcd(reg) & filt) for reg, filt in zip(time_reg, reg_filter)]
        self._bus.write_i2c_block_data(MCP7940.ADDRESS, git, t)
        self._set_bit(MCP7940.CONTROL,MCP7940.ALM1EN,1)
        register_val = self._bus.read_byte_data(MCP7940.ADDRESS, MCP7940.ALM1WKDAY)
        register_val = register_val | 0x70 #set MSK
        register_val = register_val & 0xF7 #clear previous alarm flag
        self._bus.write_byte_data(MCP7940.ADDRESS,MCP7940.ALM1WKDAY,register_val)

    def bcd_to_int(bcd):
        """ Expects a byte encoded wtih 2x 4bit BCD values. """
        # Alternative using conversions: int(str(hex(bcd))[2:])
        return (bcd & 0xF) + (bcd >> 4) * 10

    def int_to_bcd(i):
        return (i // 10 << 4) + (i % 10)

    def is_leap_year(year):
        """ https://stackoverflow.com/questions/725098/leap-year-calculation """
        if (year % 4 == 0 and year % 100 != 0) or year % 400 == 0:
            return True
        return False

    def set_alarm_polarity(self, pol):
        self._set_bit(MCP7940.ALM0WKDAY,MCP7940.ALMPOL,pol)


    def _get_time(self, start_reg = 0x00):
        num_registers = 7 if start_reg == 0x00 else 6
        time_reg = self._bus.read_i2c_block_data(MCP7940.ADDRESS, start_reg, num_registers)  # Reading too much here for alarms
        reg_filter = (0x7F, 0x7F, 0x3F, 0x07, 0x3F, 0x3F, 0xFF)[:num_registers]
        t = [MCP7940.bcd_to_int(reg & filt) for reg, filt in zip(time_reg, reg_filter)]
        # Reorder
        t2 = (t[5], t[4], t[2], t[1], t[0], t[3] - 1)
        t = (t[6] + 2000,) + t2 + (0,) if num_registers == 7 else t2
        print(t)
        return t

