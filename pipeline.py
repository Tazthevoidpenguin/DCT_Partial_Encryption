from dataclasses import dataclass
from typing import Dict, Tuple, Optional
import numpy as np
from encryption import call_enc, EncryptConfig
from dct_core import (
    rgb_to_ycbcr,ycbcr_to_rgb,pad_anh,get_scaled_tables,dct_xuoi,dct_nguoc
)
from PIL import Image


@dataclass
class PipelineConfig:
    quality: int=75
    encryp: EncryptConfig = None
    seed: Optional[int] = None

class PipelineRun:
    def __init__(self,config: PipelineConfig):
        self.config = config
        if config.seed!= None:
            self.rng = np.random.default_rng(config.seed)
        else:
            self.rng = np.random.default_rng()
    def encode(self,path_inp:str,path_out:str):
        with Image.open(path_inp) as img:
            rgb=np.array(img.convert("RGB"),dtype=np.uint8) 
            Alpha= np.array(img.getchannel("A"),dtype=np.uint8) if "A" in img.getbands() else None
        #pillow dung kieu du lieu mang khac numpy nen phai chuyen ve dang numpy
        #lay he so Alpha la he so trong suot

        YCbCr=rgb_to_ycbcr(rgb)
        padded_img, ori_size=pad_anh(YCbCr)

        luma_scaled, chroma_scaled = get_scaled_tables(self.config.quality)
        q_table=[luma_scaled,chroma_scaled,chroma_scaled]

        heso=np.stack([dct_xuoi(padded_img[:,:,i],q_table[i]) for i in range(3)]) #lay he so xuoi
        #nay no tra ve (3,H,W)

        if self.config.encryp:
            enc_heso=call_enc(heso,self.config.encryp,block_mask=None,rng=self.rng)
        else:
            enc_heso=heso.copy()

        #chuyen nguoc ve de preview
        enc_channel= np.stack([dct_nguoc(enc_heso[i],q_table[i]) for i in range(3)])
        enc_rgb= ycbcr_to_rgb(enc_channel[0:3,:ori_size[0],:ori_size[1]])
        enc_rgb= np.clip(np.rint(enc_rgb),0,255).astype(np.uint8) #clip ve he so tu 0-255 dang uint8

        enc_img= Image.fromarray(enc_rgb,mode="RGB")
        if Alpha is not None:
            enc_img.putalpha(Image.fromarray(Alpha,mode="L"))
        enc_img.save(path_out)





