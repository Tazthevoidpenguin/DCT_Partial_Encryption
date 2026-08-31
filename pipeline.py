from dataclasses import dataclass,asdict
from typing import Dict, Tuple
import numpy as np
import json
from encryption import call_enc, EncryptConfig, call_dec
from dct_core import (
    rgb_to_ycbcr,ycbcr_to_rgb,pad_anh,get_scaled_tables,dct_xuoi,dct_nguoc
)
from PIL import Image
from pathlib import Path

def handle_bytes(obj):
    if isinstance(obj, bytes):
        return obj.hex()
    raise TypeError



@dataclass
class PipelineConfig:
    quality: int=75
    encryp: EncryptConfig = None

class PipelineRun:
    def __init__(self,config: PipelineConfig):
        self.config = config

    def encode(self,path_inp:str,out_name:str,key:bytes,key_id:str):
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
        pub_data = {}
        pub_data["ori_size"]=ori_size
        pub_data["quality"]=self.config.quality
        pub_data["encryption"]=asdict(self.config.encryp)
        pub_data["key_id"]=key_id
        if self.config.encryp:
            enc_heso=call_enc(heso,self.config.encryp,block_mask=None,pub_data=pub_data,key=key)
        else:
            enc_heso=heso.copy()

        #chuyen nguoc ve de preview
        enc_channel= np.stack([dct_nguoc(enc_heso[i],q_table[i]) for i in range(3)])
        enc_rgb= ycbcr_to_rgb(enc_channel[0:3,:ori_size[0],:ori_size[1]])
        enc_rgb= np.clip(np.rint(enc_rgb),0,255).astype(np.uint8) #clip ve he so tu 0-255 dang uint8

        enc_img= Image.fromarray(enc_rgb,mode="RGB")
        if Alpha is not None:
            enc_img.putalpha(Image.fromarray(Alpha,mode="L"))

        base = Path(out_name)

        img_path = base
        data_path = base.with_suffix(".json")
        payload_path = base.with_suffix(".payload.npz")
        pub_data["output_mahoa"]=str(img_path)

        enc_img.save(img_path)
        with open(data_path,"w",encoding="utf-8") as f:
            json.dump(pub_data,f,default=handle_bytes,indent=4)
        if Alpha is not None:
            np.savez_compressed(payload_path,heso=enc_heso,luma_table=luma_scaled,chroma_table=chroma_scaled,alpha=Alpha)
        else:
            np.savez_compressed(payload_path,heso=enc_heso,luma_table=luma_scaled,chroma_table=chroma_scaled)

    def decode(self,path_inp:str,path_out:str,key:bytes):
        decoded_channels=call_dec(path_inp=path_inp,key=key,block_mask=None)








