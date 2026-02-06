id_card_reader
=============
Python driver for DESKO IDenty chrom
link <https://www.desko.com/site/assets/files/2782/desko_identy-chrom.pdf>
Extracts user data from passport or ID card MRZ (Machine Readable Zone) via USB HID.

Works on Windows, macOS, and Linux.

### Requirements
- Python >= 3.7
- [hidapi](https://pypi.org/project/hidapi/)

### Installation
In your virtual environment install dependencies:
```
pip install -r requirement.txt
```

### Usage
Run the example script:
```
python example.py
```

Or import in your own code:
```python
from idcardreader_package.idcardreader import get_user_data

customer_data, error_code = get_user_data()
```

The script will print "Ready - please scan a document..." and wait up to 60 seconds for a scan.

### Error codes
- `0` - Success
- `1` - Parsing error (regex could not parse the MRZ data)
- `2` - System error (reader not connected, read timeout, communication failure)

### Output format
On success `customer_data` is a dictionary:

**Passport:**
```
{
    "document_type": "P",
    "issuing_country": ...,
    "last_name": ...,
    "first_name": ...,
    "document_id": ...,
    "date_birth": ...,
    "sex": ...,
    "date_expiration": ...,
    "country": ...,
    "personal_id": ...,
}
```

**ID card:**
```
{
    "document_type": "I",
    "issuing_country": ...,
    "document_id": ...,
    "personal_id": ...,
    "date_birth": ...,
    "sex": ...,
    "date_expiration": ...,
    "country": ...,
    "last_name": ...,
    "first_name": ...,
}
```

`date_birth` and `date_expiration` are `datetime` objects. All other fields are strings.
