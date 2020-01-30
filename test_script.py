import dbs_ideal_giro_parser as giro
from datetime import datetime

header = giro.BatchHeader(
    creation_datetime=datetime.now(),
    sender_co_id='ABCDEFGH',
    value_date=datetime.now().date(),
    orig_ac='0150250208',
    orig_name='SUNMICRO FA PTE LTD',
    batch_id='00001'
)

details = [
    giro.DetailsRecord(
        payment_type='20',
        beneficiary_ref='giro test',
        recv_bank_bic='DBSSSGSGXXX',
        recv_ac='198904163',
        recv_ac_name='Terence Tan Wei Jie',
        purpose_code='SALA',
        amt_in_cents=1
    )
]

batch = giro.GiroBatch(header=header, details=details)
batch.set_trailer_values()
with open('test_result.txt', 'wb') as f:
    giro.dump(batch, f)