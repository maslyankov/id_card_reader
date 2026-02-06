import queue
import re
import sys
from datetime import datetime
from time import sleep

import hid

q = queue.Queue()
q.put([])

# On Windows, hidapi includes the report ID byte in read(); on macOS/Linux it does not.
# The original pywinusb data was 33 bytes (report ID + 32 bytes report data).
# The payload starts after the report ID (1 byte) + 2 header bytes = offset 3 on Windows.
# On macOS/Linux, there's no report ID, so the offset is 2.
if sys.platform == 'win32':
    _HEADER_SIZE = 3
else:
    _HEADER_SIZE = 2


DESKO_VENDOR_ID = 0x0744
DESKO_PRODUCT_ID = 0x001d


def _try_read_device(device, timeout_seconds, debug):
    """Attempt to read MRZ data from an opened HID device.
    Returns (success, error_code) where success indicates data was read."""
    got_data = False
    max_iterations = timeout_seconds * 2  # 500ms per iteration while waiting
    exit_counter = 0

    while exit_counter < max_iterations:
        exit_counter += 1
        # Use shorter timeout once data starts arriving to capture the full burst
        timeout_ms = 100 if got_data else 500
        data = device.read(64, timeout_ms=timeout_ms)

        if debug and exit_counter <= 5:
            print(f"[DEBUG] read #{exit_counter}: data={list(data) if data else None} (len={len(data) if data else 0})")

        if not data:
            if got_data:
                if debug:
                    print(f"[DEBUG] Data burst finished after {exit_counter} reads")
                break
            continue

        data_list = list(data)
        payload = data_list[_HEADER_SIZE:]

        # Skip empty/status reports (payload is all zeros)
        if not any(payload):
            if debug:
                print(f"[DEBUG] Skipping empty report: {data_list}")
            continue

        if debug:
            print(f"[DEBUG] Got data report: {data_list}")

        got_data = True
        queue_data = q.get()
        queue_data.append(payload)
        q.put(queue_data)

    return got_data


def get_raw_data(timeout_seconds=60, debug=False):
    error_code = 0
    all_hids = hid.enumerate(DESKO_VENDOR_ID, DESKO_PRODUCT_ID)

    if not all_hids:
        print("There's not any non system HID class device available")
        return 2

    if debug:
        print(f"[DEBUG] Found {len(all_hids)} HID interface(s) for DESKO device:")
        for i, dev_info in enumerate(all_hids):
            print(f"[DEBUG]   #{i}: usage_page=0x{dev_info.get('usage_page', 0):04x} "
                  f"usage=0x{dev_info.get('usage', 0):04x} "
                  f"interface={dev_info.get('interface_number', -1)} "
                  f"path={dev_info.get('path')}")

    # Try each HID interface until one works (devices often expose multiple)
    for idx, dev_info in enumerate(all_hids):
        device = None
        try:
            device = hid.device()
            device.open_path(dev_info['path'])

            if debug:
                print(f"[DEBUG] Opened interface #{idx}, testing read...")

            # Test read to check if this interface supports reading
            test_data = device.read(64, timeout_ms=200)
            if debug:
                print(f"[DEBUG] Test read OK: {list(test_data) if test_data else None}")

            print("Ready - please scan a document...")

            got_data = _try_read_device(device, timeout_seconds, debug)

            if not got_data:
                error_code = 2
            return error_code

        except Exception as e:
            if debug:
                print(f"[DEBUG] Interface #{idx} failed: {e}")
            continue
        finally:
            if device:
                device.close()

    # All interfaces failed
    if debug:
        print("[DEBUG] All HID interfaces failed")
    return 2


class IDScanner:
    def __init__(self, raw_data):
        self.raw_data = raw_data
        self.user_data = {}
        self.error_code = 0

    def converttostring(self, row):
        result = ""
        for chars in row:
            result += chr(chars)
        return result

    def parser_row1_P(self, row_string):
        try:

            match_group = re.search(r'[P][\w<]([\w<]{3})(\w*)<<(\w*).*', row_string)

            issuing_country = match_group.group(1).replace('<', '')
            last_name = match_group.group(2).replace('<', '')
            first_name = match_group.group(3).replace('<', '')

            self.user_data['issuing_country'] = issuing_country
            self.user_data['last_name'] = last_name
            self.user_data['first_name'] = first_name

        except Exception as e:
            raise

    def parser_row2_P(self, row_string):
        try:
            match_group = re.search(r'([\w<]{9})[\d]([\w<]{3})([\d]{6})[\d]([MF<])([\d]{6})[\d]([\d]*).*', row_string)

            document_id = match_group.group(1).replace('<', '')
            country = match_group.group(2).replace('<', '')
            date_birth = match_group.group(3).replace('<', '')
            sex = match_group.group(4).replace('<', '')
            date_expiration = match_group.group(5).replace('<', '')
            personal_id = match_group.group(6).replace('<', '')

            date_birth_datetime = datetime.strptime(date_birth, '%y%m%d')
            date_expiration_datetime = datetime.strptime(date_expiration, '%y%m%d')

            self.user_data['document_id'] = document_id
            self.user_data['date_birth'] = date_birth_datetime
            self.user_data['sex'] = sex
            self.user_data['date_expiration'] = date_expiration_datetime
            self.user_data['country'] = country
            self.user_data['personal_id'] = personal_id

        except Exception as e:
            print(e)
            raise

    def parser_row1_ID(self, row_string):
        try:

            match_group = re.search(r'[IAC][\w<]([\w<]{3})([\w<]{9})[\d<]([\w<]{10}).*', row_string)

            issuing_country = match_group.group(1).replace('<', '')
            document_id = match_group.group(2).replace('<', '')
            personal_id = match_group.group(3).replace('<', '')

            self.user_data['issuing_country'] = issuing_country
            self.user_data['document_id'] = document_id
            self.user_data['personal_id'] = personal_id


        except Exception as e:
            print(e)
            raise

    def parser_row2_ID(self, row_string):
        try:
            match_group = re.search(r'([\d]{6})\d([MF<])([\d]{6})[\d<]([\w<]{3}).*', row_string)

            date_birth = match_group.group(1).replace('<', '')
            sex = match_group.group(2).replace('<', '')
            date_expiration = match_group.group(3).replace('<', '')
            country = match_group.group(4).replace('<', '')

            date_birth_datetime = datetime.strptime(date_birth, '%y%m%d')
            date_expiration_datetime = datetime.strptime(date_expiration, '%y%m%d')

            self.user_data['date_birth'] = date_birth_datetime
            self.user_data['sex'] = sex
            self.user_data['date_expiration'] = date_expiration_datetime
            self.user_data['country'] = country

        except Exception as e:
            print(e)
            raise

    def parser_row3_ID(self, row_string):
        try:

            match_group = re.search(r'(\w*)<<(\w*).*', row_string)

            last_name = match_group.group(1).replace('<', '')
            first_name = match_group.group(2).replace('<', '')

            self.user_data['last_name'] = last_name
            self.user_data['first_name'] = first_name

        except Exception as e:
            raise

    def parse_data(self):
        try:
            row1 = self.raw_data[1]
            row2 = self.raw_data[2]

            document_type = row1[0]
            self.user_data['document_type'] = document_type

            if document_type == "P":
                # PASSPORT
                self.parser_row1_P(row1)
                self.parser_row2_P(row2)

            elif document_type == "I":
                # ID
                row3 = self.raw_data[3]

                self.parser_row1_ID(row1)
                self.parser_row2_ID(row2)
                self.parser_row3_ID(row3)
            else:
                self.error_code = 1

        except Exception as e:
            self.error_code = 1

    def get_data(self):
        return self.user_data

    def get_error_code(self):
        return self.error_code


def createBoudle(raw_data):
    result = []

    for data in raw_data:
        result += data

    return result


def getImportantData(raw_data):
    start_text = raw_data.index(2) + 1
    end_text = raw_data.index(3)

    return raw_data[start_text:end_text]


def splitToLineAndConvert(raw_data):
    result = {}
    line = ""
    counter = 1

    for char in raw_data:
        if char == 13:
            result[counter] = line
            counter += 1
            line = ""
            continue
        line += chr(char)

    return result


def decodeRawData(raw_data):
    raw_data = createBoudle(raw_data)
    raw_data = getImportantData(raw_data)
    lined_data = splitToLineAndConvert(raw_data)

    return lined_data


def get_user_data(debug=False):
    data = {}
    try:
        error_value = get_raw_data(debug=debug)

        if error_value == 0:
            raw_data = q.get()

            result = decodeRawData(raw_data)

            id_scanner = IDScanner(result)
            id_scanner.parse_data()

            error_value = id_scanner.get_error_code()
            data = id_scanner.get_data()

    except Exception as e:
        print("ERROR {}".format(e))
        error_value = 2

    return data, error_value
