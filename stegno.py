from dataclasses import dataclass
from encryption import zigzag_order,derive_seed
import numpy as np
import secrets

@dataclass
class StegnoConfig:
    delta: int=3 #de xac dinh cac khoang dua he so carrier ve gan nhat thuoc ho chan hay ho le
    """
    Công thức tính họ chẵn/lẻ là:
    bit 0: 0, 2*delta, 4*delta, ...
    bit 1: delta, 3*delta, 5*delta,...
    """
    ac_start: int=5
    ac_end: int=15

ZIGZAG=zigzag_order()

def build_carriers(heso: np.ndarray, config: StegnoConfig)->np.ndarray:
    ac_pos=ZIGZAG[config.ac_start:config.ac_end]
    rows=heso.shape[1]//8
    cols=heso.shape[2]//8

    carriers=[]
    for row in range(rows):
        for col in range(cols):
            for u,v in ac_pos:
                i=row*8+u
                j=col*8+v
                carriers.append((i,j))
    return np.asarray(carriers, dtype=np.int32)

def cal_AC(ac: int, delta: int, bit: np.uint8)->int:
    dau=1
    if ac<0:
        dau=-1
    tmp=round(abs(ac)/delta)
    if tmp%2!=bit:
        giam=tmp-1
        tang=tmp+1
        if giam<0:
            tmp=tang
        elif abs(abs(ac)-giam*delta)<=abs(abs(ac)-tang*delta):
            tmp=giam
        else:
            tmp=tang
    return tmp*delta*dau
    
    
def embed(heso: np.ndarray, config: StegnoConfig, key: bytes, pub_data: dict, inp:str):
    nonce=secrets.token_bytes(16)
    seed=derive_seed(key,nonce,"steg")
    rng_steg=np.random.default_rng(seed)


    rs=heso.copy()
    carriers=build_carriers(rs,config)
    order=rng_steg.permutation(len(carriers))
    carriers=carriers[order] #tron carriers

    payload=inp.encode("utf-8")
    pub_data["payload_len"]=len(payload)
    payload_bits=np.unpackbits(np.frombuffer(payload,dtype=np.uint8))
    if len(payload_bits)>len(carriers):
        raise ValueError("Payload qua dai")

    for idx in range(len(payload_bits)):
        row,col=carriers[idx]
        rs[0,row,col]=cal_AC(rs[0,row,col],config.delta,payload_bits[idx])


    pub_data["mode"]="stegno"
    pub_data["nonce"]=nonce
    pub_data["delta"]=config.delta
    pub_data["ac_start"]=config.ac_start
    pub_data["ac_end"]=config.ac_end

    return rs

def extract(heso: np.ndarray,config: StegnoConfig, key: bytes, nonce:bytes, payload_len:int) ->bytes:
    seed=derive_seed(key,nonce,"steg")
    rng_steg=np.random.default_rng(seed)
    rs=heso.copy()
    carriers=build_carriers(rs,config)   
    order=rng_steg.permutation(len(carriers))
    carriers=carriers[order] 



    if payload_len*8 > len(carriers):
        raise ValueError("Payload qua dai")

    bits=[]
    for idx in range(payload_len*8):
        row,col=carriers[idx]
        bits.append(round(abs(rs[0,row,col])/config.delta)%2)
    payload_bytes=np.packbits(bits).tobytes()
    return payload_bytes

