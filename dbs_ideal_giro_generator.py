'''An object-oriented wrapper around the DBS Interbank GIRO File Format.

Supports the `pickle` and `json` modules' loads()/dumps() interface.

The serialisation/deserialisation is based on the DBS Interbank GIRO File Format v1.7. This document is referred to later in the documentation as the 'specification'.

I am not responsible if you use this module and all your money disappears.

DBS and DBS IDEAL are registered trademarks of The Development Bank of Singapore Limited.

This module is (C) 2017 Nikos Chan and Terence Tan

Quick start:

    import dbs_ideal_giro_parser as giro
    from datetime import datetime
    
    header = BatchHeader(
        creation_datetime=datetime.now(),
        sender_co_id='S3ND3RID',
        value_date=datetime.now().date(),
        orig_ac='0259001103',
        orig_name='Foo Chinese Kitchen Pte Ltd',
        batch_id='00001'
    )
    
    details = [
        DetailsRecord(
            payment_type='20',
            beneficiary_ref='Free money',
            recv_bank_bic='DBSSSGSGXXX',
            recv_ac='1234567890',
            recv_ac_name='Bar Breweries Pte Ltd',
            purpose_code='SALA',
            amt_in_cents=6900
        ),
        DetailsRecord(
            payment_type='20',
            beneficiary_ref='Come get it',
            recv_bank_bic='UOVBSGSGXXX',
            recv_ac='9876543210',
            recv_ac_name='Baz Appliances Ltd',
            purpose_code='COMM',
            amt_in_cents=29400
        )
        # ... more data ...
    ]
    
    batch = GiroBatch(header=header, details=details)
    batch.set_trailer_values()
    with open('result.txt', 'wb') as f:
        dump(batch, f)


Standard field name abbrevations:
- co: company
- ac: account, account number
- ref: reference
- amt: amount
- ult: ultimate
- orig: originating, originator
- recv: receiving, receiver

'''
import re

from djcopybook.fixedwidth import Record
from djcopybook.fixedwidth.fields import *

class RegexMatchMixin():
    '''Enforces regex match on to_record().
    
    Pass in an additional regex kwarg to the constructor, which is a string containing the appropriate regex pattern. ^...$ isn't required as a fullmatch() is performed. 
    '''
    _re_debug = False
    
    def __init__(self, *args, regex=None, **kwargs):
        if regex is not None:
            # Obviously the more performant approach is to store a compiled regex, but this conflicts with some deep copy in djcopybook
            self.regex = regex
            #self.pattern = re.compile(regex)
        super(RegexMatchMixin, self).__init__(*args, **kwargs)
    
    #def to_record(self, val):
    #    if not self._pattern.fullmatch(val):
    #        raise ValueError('Regex match failed', {'pattern': self._pattern, 'val': val})
    #    else:
    #        print('Regex matched: {0} with {1}'.format(self._pattern, val))
    #        return super(RegexMatchMixin, self).to_record(val)
    
    def to_record(self, val):
        if val is None:
            raise ValueError('Regex field contents is None')
            
        if not re.fullmatch(self.regex, val):
            raise ValueError('Regex match failed', {'regex': self.regex, 'val': val})
        else:
            if self._re_debug:
                print('Regex matched: /{0}/ with "{1}"'.format(self.regex, val))
            return super(RegexMatchMixin, self).to_record(val)

class StringWithRegexField(RegexMatchMixin, StringField):
    '''This StringField variant will enforce a regex match when it is written to a record.
    '''
    pass

class BatchHeader(Record):
    '''Represents a Batch Header record. See section 1.3 of the specification.
    
    creation_datetime is defined as two separate fields in the spec, but putting them together makes converting between the forms easier.
    sender_co_id should be uppercase letters and digits only.
    value_date is the effective date of this batch (as opposed to creation_datetime).
    batch_id is not verified here, make sure that it is unique with value_date and that it is in [00001, 89999].
    
    Do not assign values to filler_1 or filler_2. 
    '''
    # this is not entirely correct... date and time are meant to be separate
    creation_datetime = DateTimeField(length=14, format='%d%m%Y%H%M%S')
    sender_co_id = StringWithRegexField(length=8, regex=r'[A-Z0-9 ]{8}')
    value_date = DateField(length=8, format='%d%m%Y')
    orig_ac = StringWithRegexField(length=34, regex=r'[a-zA-Z0-9]+')
    orig_name = StringWithRegexField(length=140, regex=r'[a-zA-Z0-9 ]+')
    filler_1 = StringField(length=34)
    batch_id = IntegerField(length=5)
    batch_ref = StringField(length=35)
    filler_2 = StringField(length=722, default='C{0}01'.format(' '*719))

class DetailsRecord(Record):
    '''Represents a Details record. See section 1.4 of the specification.
    
    recv_bank_bic must be 11 characters, uppercase or digits. This might be a bit overzealous.
    dda_ref is not necessary if you are not taking money from somebody else's bank account.
    
    Do not assign values to bulk_transfer_currency, priority_indicator, filler_1, or record_type.
    '''
    payment_type = StringWithRegexField(length=2, regex=r'(20|22|30)')
    beneficiary_ref = StringWithRegexField(length=35, regex=r'[a-zA-Z0-9 ]+')
    recv_bank_bic = StringWithRegexField(length=35, regex=r'[A-Z0-9]{11}')
    recv_ac = StringWithRegexField(length=34, regex=r'[a-zA-Z0-9]+')
    recv_ac_name = StringWithRegexField(length=140, regex=r'[a-zA-Z0-9 ]+')
    purpose_code = StringWithRegexField(length=4, regex=r'[A-Z ]{4}')
    bulk_transfer_currency = StringField(length=3, default='SGD')
    amt_in_cents = IntegerField(length=11)
    dda_ref = StringField(length=35)
    payment_details = StringField(length=140)
    priority_indicator = StringField(length=1, default='N')
    ult_orig_name = StringField(length=140)
    ult_recv_name = StringField(length=140)
    filler_1 = StringField(length=278)
    record_type = StringField(length=2, default='10')
    
class BatchTrailer(Record):
    '''Represents a Batch Trailer record. See section 1.5 of the specification.
    
    Do not assign values to filler_1, ac_hash_total (this is computed automatically when you use dump() or dumps()), filler_2, or record_type.
    
    You can create this automatically with set_trailer_values().
    '''
    total_credit_txn = IntegerField(length=11)
    total_credit_amt = IntegerField(length=18)
    total_debit_txn = IntegerField(length=11)
    total_debit_amt = IntegerField(length=18)
    filler_1 = StringField(length=26)
    ac_hash_total = IntegerField(length=11)
    filler_2 = StringField(length=903)
    record_type = StringField(length=2, default='20')

def ac_string_transform(ac_str):
    '''Transform an account number into a string, as per the DBS specification, used for calculating the trailer hash.
    '''
    chars = list(ac_str[:11])
    for i, ch in enumerate(chars):
        if ch.isalpha():
            chars[i] = '0'
    return ''.join(chars).ljust(11, '0')

class GiroBatch():
    '''GiroBatch(): empty batch
    
    GiroBatch(header=<BatchHeader>, details=[<DetailsRecord>, <DetailsRecord>, ...], trailer=<BatchTrailer>): create a new GiroBatch with these records
    
    Members:
    - batch_header: <BatchHeader instance>
    - batch_details: [<DetailsRecord>, <DetailsRecord>, ...]
    - batch_trailer: <BatchTrailer instance>
    '''
    def __init__(self, header=None, details=None, trailer=None):
        self.batch_header = header or BatchHeader()
        self.batch_details = details or [DetailsRecord()]
        self.batch_trailer = trailer or BatchTrailer()
        
    def compute_ac_hash_total(self):
        '''Compute the hash in the trailer.
        '''
        # Step 1a
        orig_ac_int = int(ac_string_transform(self.batch_header.orig_ac))
        recv_ac_ints = [int(ac_string_transform(record.recv_ac)) for record in self.batch_details]
        
        # Step 1b
        results = [abs(recv_ac - orig_ac_int) for recv_ac in recv_ac_ints]
        
        # Step 2
        result = sum(results)
        
        # Step 3 (the padding part is handled by IntegerField)
        return int(str(result)[:11])
    
    def compute_trailer_values(self):
        '''Compute the trailer based on the header and entries.
        '''
        credit_types = ('20', '22')
        debit_types = ('30',)
        
        total_credit_txn = 0
        total_credit_amt = 0
        total_debit_txn = 0
        total_debit_amt = 0
        
        for record in self.batch_details:
            if record.payment_type in credit_types:
                total_credit_txn += 1
                total_credit_amt += record.amt_in_cents
            elif record.payment_type in debit_types:
                total_debit_txn += 1
                total_debit_amt += record.amt_in_cents
            else:
                raise ValueError('Unknown payment_type', record)
        
        trailer = BatchTrailer()
        trailer.total_credit_txn = total_credit_txn
        trailer.total_credit_amt = total_credit_amt
        trailer.total_debit_txn = total_debit_txn
        trailer.total_debit_amt = total_debit_amt
        
        # Also compute and set the hash
        trailer.ac_hash_total = self.compute_ac_hash_total()
        
        return trailer
    
    def set_ac_hash_total(self):
        self.batch_trailer.ac_hash_total = self.compute_ac_hash_total()
    
    def set_trailer_values(self):
        '''Automatically create and assign a trailer based on the existing header and entries. Call this before writing the record.
        '''
        self.batch_trailer = self.compute_trailer_values()
    
    def to_rows(self):
        '''Arrange the individual records into a list, in the order that they appear in the output.
        '''
        rows = []
        rows.append(self.batch_header)
        rows.extend(self.batch_details)
        rows.append(self.batch_trailer)
        return rows

row_separator = b'\r\n'

def loads(ascii, raise_exc=True):
    '''Deserialise bytes into Python objects.
    
    raise_exc: If False, suppresses ValueError when there is a hash mismatch.
    '''
    # Split into lines
    rows = ascii.split(row_separator)
    
    if len(rows) < 3:
        raise ValueError('Not enough records')
    
    # Convert into str
    rows = [row.decode('ascii') for row in rows]
    
    kwargs = {
        'header': BatchHeader.from_record(rows.pop(0)),
        'trailer': BatchTrailer.from_record(rows.pop()),
        'details': [DetailsRecord.from_record(row) for row in rows]
    }
    
    batch = GiroBatch(**kwargs)

    # Perform verification
    if batch.batch_trailer.ac_hash_total != batch.compute_ac_hash_total():
        if raise_exc:
            raise ValueError('ac_hash_total mismatch')
        else:
            print('ac_hash_total mismatch')
    

    return batch

def load(fd):
    '''Read bytes from a *binary* file object. Works like pickle/json.
    
    Recommended usage:
    
    >>> with open('path/to/file.txt', 'rb') as f:
    ...    batch = load(f)
    '''
    return loads(fd.read())

def dumps(batch, max_transactions=5000):
    '''Serialise a GiroBatch into bytes suitable for uploading to DBS IDEAL. You must call batch.set_trailer_values() first, if you want automatic trailer generation.
    
    max_transactions: Limit of entries in batch_details.
    '''    
    # Compute the hash
    batch.set_ac_hash_total()
    
    # 5000 transactions limit
    if len(batch.batch_details) > max_transactions:
        raise ValueError('Too many transactions in batch')
    
    # Serialise each row and encode into ASCII
    rows = [row.to_record().encode('ascii') for row in batch.to_rows()]
    
    # Insert CRLFs
    return row_separator.join(rows)
    
def dump(obj, fd):
    '''Write bytes from a *binary* file object. Works like pickle/json.
    
    Recommended usage:
    
    >>> with open('path/to/file.txt', 'wb') as f:
    ...    dump(batch, f)
    '''
    return fd.write(dumps(obj))

def demo():
    from datetime import datetime
    
    header = BatchHeader(
        creation_datetime=datetime.now(),
        sender_co_id='S3ND3RID',
        value_date=datetime.now().date(),
        orig_ac='0259001103',
        orig_name='Foo Chinese Kitchen Pte Ltd',
        batch_id='00001'
    )
    
    details = [
        DetailsRecord(
            payment_type='20',
            beneficiary_ref='Free money',
            recv_bank_bic='DBSSSGSGXXX',
            recv_ac='1234567890',
            recv_ac_name='Bar Breweries Pte Ltd',
            purpose_code='SALA',
            amt_in_cents=6900
        ),
        DetailsRecord(
            payment_type='20',
            beneficiary_ref='Come get it',
            recv_bank_bic='UOVBSGSGXXX',
            recv_ac='9876543210',
            recv_ac_name='Baz Appliances Ltd',
            purpose_code='COMM',
            amt_in_cents=29400
        )
        # ... more data ...
    ]
    
    batch = GiroBatch(header=header, details=details)
    batch.set_trailer_values()
    with open('result.txt', 'wb') as f:
        dump(batch, f)
    
    return batch
