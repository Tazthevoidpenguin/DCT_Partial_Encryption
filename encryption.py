from dataclasses import dataclass
from typing import Tuple,Optional
import numpy as np
import hashlib
import hmac
import secrets
import json
from pathlib import Path



@dataclass
class EncryptConfig:
    mode: str = "hybrid"
    ac_count: int = 5
    dc_bitplanes: int = 7
    dc_bit_width: int = 7
    channels: Tuple [str,...] =  ("Y",)


def zigzag_order()->tuple:
    lst=[]
    for sum in range (15):
        if(sum%2==0):
            for i in range (min(sum,7),max(0,sum-7)-1,-1):
                lst.append((i,sum-i))
        else:
            for i in range(max(0,sum-7),min(sum,7)+1):
                lst.append((i,sum-i))
    return tuple(lst)

ZIGZAG=zigzag_order()


def derive_seed(key: bytes, nonce: bytes, label: str) -> int:
    rs_digest= hmac.new(key,nonce+label.encode("utf-8"),hashlib.sha256).digest()
    #tra ve gia tri bam 32 byte
    return int.from_bytes(rs_digest[:16],'big') #tra ve so nguyen dang big-endian


def _block_mask(heso: np.ndarray, mode: int,rng: np.random.Generator) -> np.ndarray:
    block_shape = (heso.shape[1] // 8, heso.shape[2] // 8)
    if mode==1:
        return np.ones(block_shape, dtype=bool)
    elif mode == 2: #tham khao code mang @@, no se lan dan tu trung tam ra ben canh
        block_rows, block_cols = block_shape
        total_blocks = block_rows * block_cols
        min_count = max(1, total_blocks // 4)
        max_count = max(min_count, total_blocks // 2)
        selected_count = int(
            rng.integers(min_count, max_count + 1)
        )
        center_row = (block_rows - 1) / 2
        center_col = (block_cols - 1) / 2
        rows, cols = np.indices(block_shape)
        distances = (
            (rows - center_row) ** 2
            + (cols - center_col) ** 2
        )
        order = np.argsort(distances, axis=None)
        rs = np.zeros(total_blocks, dtype=bool)
        rs[order[:selected_count]] = True
        return rs.reshape(block_shape)

    elif mode==3:
        rs=np.zeros(block_shape,dtype=bool)   
        for i in range(block_shape[0]):
            for j in range(block_shape[1]):
                if (i+j)%2==0:
                    rs[i,j]=True
        return rs.reshape(block_shape)
    
    elif mode==4:
        sum_block=block_shape[0]*block_shape[1]
        max_cnt = max(1,sum_block//2)
        random_blocks=rng.choice(sum_block,size=max_cnt,replace=False) #lay ngau nhien index cac block, replace = false de ko trung nhau

        rs = np.zeros(sum_block,dtype=bool)
        rs[random_blocks]=True
        return rs.reshape(block_shape)
    

def AC_sign_flip(heso: np.ndarray, config: EncryptConfig, rng: np.random.Generator, block_mask: np.ndarray|None):
    AC_positions=ZIGZAG[1:config.ac_count+1] #vị trí những AC sẽ đảo
    blockR,blockC=np.nonzero(block_mask) #lấy những ô cần mã hóa
    for tmp in config.channels:
        idx={"Y":0,"Cb":1,"Cr":2} [tmp] #lấy kênh mã hóa
        channel= heso[idx] #Tạo tham chiếu tới mảng heso 
        for i,j in AC_positions:
            Row_idx=blockR*8+i
            Col_idx=blockC*8+j
            coeffs=channel[Row_idx,Col_idx] #Lưu tất cả cặp (row,col) thành mảng hệ số
            nonzero_mask= (coeffs!=0)
            cnt= np.count_nonzero(nonzero_mask)
            if(cnt==0):
                continue
            random= rng.integers(0,2,size=cnt)
            signs = (-1)**random
            channel[Row_idx[nonzero_mask],Col_idx[nonzero_mask]]*=signs


def DC_bitplane_scramble(heso: np.ndarray, config: EncryptConfig, rng: np.random.Generator, block_mask: np.ndarray|None):
    low_cnt= (1<<config.dc_bit_width) -1 #Số bit để tách
    blockR,blockC=np.nonzero(block_mask)
    for tmp in config.channels:
        idx={"Y":0,"Cb":1,"Cr":2} [tmp]
        DC_all=heso[idx,0::8,0::8] #lấy bit DC của từng block
        values=DC_all[blockR,blockC].astype(np.int64)
        signs=np.sign(values) #AI phat hien neu DC_dau la so am ma nho qua -> DC_cuoi=0 thi se mat dau ->decode no bi thung lo cho, de nghien cuu sua sau =)))
        duong=np.abs(values)

        low_bit =duong&low_cnt #mảng các lowbits
        high_bit=duong>>config.dc_bit_width #mảng các highbits
        
        for i in range(config.dc_bitplanes):
            bits= (low_bit>>i)&1 #bit_plane thu i
            perm = rng.permutation(len(bits))
            scrambled_bits = bits[perm]
            low_bit= low_bit & ~(1<<i) #xoa bit thu i cu
            low_bit= low_bit | (scrambled_bits<<i) #gan bit thu i moi

        """
        Ví dụ trong tài liệu có nói tới sửa 2 bit cao nhất thì nó sẽ như này:
        for i in range(config.dc_bit_width - 2, config.dc_bit_width):
        
        for i in range(config.dc_bitplanes):
        """
        rs= signs*((high_bit<<config.dc_bit_width) | low_bit)
        DC_all[blockR,blockC]=rs

def DC_bitplane_reverse(heso: np.ndarray, config: EncryptConfig, rng: np.random.Generator, block_mask: np.ndarray|None):
    low_cnt= (1<<config.dc_bit_width) -1 #Số bit để tách
    blockR,blockC=np.nonzero(block_mask)
    for tmp in config.channels:
        idx={"Y":0,"Cb":1,"Cr":2} [tmp]
        DC_all=heso[idx,0::8,0::8] #lấy bit DC của từng block
        values=DC_all[blockR,blockC].astype(np.int64)
        signs=np.sign(values) #AI phat hien neu DC_dau=-1 -> DC_cuoi=0 thi se mat dau, chua biet cach sua
        duong=np.abs(values)

        low_bit =duong&low_cnt #mảng các lowbits
        high_bit=duong>>config.dc_bit_width #mảng các highbits
        
        for i in range(config.dc_bitplanes):
            bits= (low_bit>>i)&1 #bit_plane thu i
            perm = rng.permutation(len(bits))
            reverse_perm = np.argsort(perm)
            reversed_bits = bits[reverse_perm]
            low_bit= low_bit & ~(1<<i) #xoa bit thu i cu
            low_bit= low_bit | (reversed_bits<<i) #gan bit thu i moi

        rs= signs*((high_bit<<config.dc_bit_width) | low_bit)
        DC_all[blockR,blockC]=rs

def stegno(heso: np.ndarray, config: EncryptConfig, rng: np.random.Generator, block_mask: np.ndarray|None) -> np.ndarray:
    return 




def call_enc(heso: np.ndarray,config: EncryptConfig, block_mask_mode:int, pub_data: dict, key:bytes) -> np.ndarray:
    rs= heso.copy()
    nonce= secrets.token_bytes(16) #sinh random tu OS nen cham hon nhung bao mat hon va hoan toan random, ko the doan duoc seed
    pub_data["Nonce"]=nonce

    seed_ac = derive_seed(key,nonce,"ac")
    seed_dc = derive_seed(key,nonce,"dc")
    seed_stegno = derive_seed(key, nonce,"steg")
    seed_mask = derive_seed(key,nonce,"mask")
    rng_ac = np.random.default_rng(seed_ac)
    rng_dc = np.random.default_rng(seed_dc)
    rng_steg = np.random.default_rng(seed_stegno)
    rng_mask = np.random.default_rng(seed_mask)

    Mask=_block_mask(rs,block_mask_mode,rng_mask)

    if config.mode == "ac_sign":
        AC_sign_flip(rs,config,rng_ac,Mask)
    elif config.mode == "dc_bitplane":
        DC_bitplane_scramble(rs,config,rng_dc,Mask)
    elif config.mode == "hybrid":
        AC_sign_flip(rs,config,rng_ac,Mask)
        DC_bitplane_scramble(rs,config,rng_dc,Mask)
    elif config.mode == "stegno":
        stegno(rs,config,rng_steg,Mask)
    return rs
        

def call_dec(path_inp:str,key: bytes) -> Tuple[np.ndarray,np.ndarray,Tuple[int,int],np.array]:
    base = Path(path_inp)
    metadata_inp = base.with_suffix(".json")
    payload_inp = base.with_suffix(".payload.npz")
    with open(metadata_inp,"r",encoding="utf-8") as f:
            metadata=json.load(f)
    ori_size=tuple(metadata["ori_size"])
    config=EncryptConfig(**metadata["encryption"])
    """
    Doan nay sua khong hieu lam, codex bao la neu de nguyen EncryptConfig(metadata["encryption"]) 
    thi se bi ep tat ca vao thuoc tinh mode nen phai bung ra bang dau **
    """
    key_id=metadata["key_id"]
    nonce=bytes.fromhex(metadata["Nonce"])
    #ko can quality vi da luu 2 table

    with np.load(payload_inp,allow_pickle=False) as payload:
        enc_heso=payload["heso"].copy()
        luma=payload["luma_table"]
        chroma=payload["chroma_table"]
        mask_mode=payload["block_mask_mode"]
        if "alpha" in payload.files:
            alpha = payload["alpha"].copy()
        else:
            alpha = None
    q_table=[luma,chroma,chroma]


    seed_ac = derive_seed(key,nonce,"ac")
    seed_dc = derive_seed(key,nonce,"dc")
    seed_stegno = derive_seed(key, nonce,"steg")
    seed_mask = derive_seed(key, nonce,"mask")
    rng_ac = np.random.default_rng(seed_ac)
    rng_dc = np.random.default_rng(seed_dc)
    rng_steg = np.random.default_rng(seed_stegno)
    rng_mask = np.random.default_rng(seed_mask)

    Mask=_block_mask(enc_heso,mask_mode,rng_mask)

    if config.mode == "ac_sign":
        AC_sign_flip(enc_heso,config,rng_ac,Mask)
    elif config.mode == "dc_bitplane":
        DC_bitplane_reverse(enc_heso,config,rng_dc,Mask)
    elif config.mode == "hybrid":
        DC_bitplane_reverse(enc_heso,config,rng_dc,Mask)
        AC_sign_flip(enc_heso,config,rng_ac,Mask)
    #elif config.mode == "stegno":
    #   split(enc_heso,config,rng_T,Mask)
    
    return enc_heso,q_table,ori_size,alpha
