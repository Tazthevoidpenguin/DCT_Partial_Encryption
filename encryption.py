from dataclasses import dataclass
from typing import Tuple,Optional
import numpy as np

@dataclass
class EncryptConfig:
    mode: str = "hybrid"
    ac_count: int = 5
    dc_bitplanes: int = 7
    dc_bit_width: int = 7
    channels: Tuple [str,...] =  ("Y",)
    nguongT: Optional[int] = None


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

def _block_mask(heso: np.ndarray, block_mask: np.ndarray | None) -> np.ndarray:
    expected_shape = (heso.shape[1] // 8, heso.shape[2] // 8)
    if block_mask is None:
        return np.ones(expected_shape, dtype=bool)
    mask = np.asarray(block_mask, dtype=bool)
    if mask.shape != expected_shape:
        raise ValueError(f"block mask shape must be {expected_shape}, got {mask.shape}")
    return mask
"""
Hàm trên đánh dấu các block mình chọn để mã hóa, nếu ko có gì (none) thì nó mặc định là mã hóa tất
"""

def AC_sign_flip(heso: np.ndarray, config: EncryptConfig, rng: np.random.Generator, block_mask: np.ndarray|None):
    AC_positions=ZIGZAG[1:config.ac_count+1] #vị trí những AC sẽ đảo
    blockR,blockC=np.nonzero(block_mask) #lấy những ô cần mã hóa
    for tmp in config.channels:
        idx={"Y":0,"Cb":1,"Cr":2} [tmp] #lấy kênh mã hóa
        channel= heso[idx] #Cái này tạo tham chiếu tới mảng heso
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
        signs=np.sign(values)
        duong=np.abs(values)

        low_bit =duong&low_cnt #mảng các lowbits
        high_bit=duong>>config.dc_bit_width #mảng các highbits

        for i in range(config.dc_bitplanes):
            bits= (low_bit>>i)&1 #bit_plane thu i
            scramble_bits= rng.permutation(bits)

            low_bit= low_bit & ~(1<<i) #xoa bit thu i cu
            low_bit= low_bit | (scramble_bits<<i) #gan bit thu i moi

        """
        Ví dụ trong tài liệu có nói tới sửa 2 bit cao nhất thì nó sẽ như này:
        for i in range(config.dc_bit_width - 2, config.dc_bit_width):
        """
        rs= signs*((high_bit<<config.dc_bit_width) | low_bit)
        DC_all[blockR,blockC]=rs

def split(heso: np.ndarray, config: EncryptConfig, rng: np.random.Generator, block_mask: np.ndarray|None):
    return 




def call_enc(heso: np.ndarray,config: EncryptConfig, block_mask: np.ndarray|None, rng: np.random.Generator|None) -> np.ndarray:
    rs= heso.copy()
    Mask=_block_mask(rs,block_mask)
    if config.mode == "ac_sign":
        AC_sign_flip(rs,config,rng,Mask)
    elif config.mode == "dc_bitplane":
        DC_bitplane_scramble(rs,config,rng,Mask)
    elif config.mode == "hybrid":
        AC_sign_flip(rs,config,rng,Mask)
        DC_bitplane_scramble(rs,config,rng,Mask)
    elif config.mode == "threshold":
        split(rs,config,rng,Mask)
    return rs
        