import numpy as np
from typing import Tuple

"""
Công thức ITU-R BT.601:
Y  = 0.299*R + 0.587*G + 0.114*B
Cb = -0.1687*R - 0.3313*G + 0.5*B + 128
Cr = 0.5*R - 0.4187*G - 0.0813*B + 128
-> Đây là công thức chuẩn để chuyển đổi từ RGB sang YCbCr dạng ảnh.
Công thức ngược của nó là:
R = Y + 1.402*(Cr - 128)
G = Y - 0.3441*(Cb - 128) - 0.7141*(Cr - 128)
B = Y + 1.772*(Cb - 128)
"""
def rgb_to_ycbcr(rgb: np.ndarray) -> np.ndarray:
    R=rgb[:,:,0]
    G=rgb[:,:,1]
    B=rgb[:,:,2]
    Y=0.299*R + 0.587*G + 0.114*B
    Cb = -0.1687*R - 0.3313*G + 0.5*B + 128
    Cr = 0.5*R - 0.4187*G - 0.0813*B + 128
    return np.stack((Y,Cb,Cr),axis=-1)

def ycbcr_to_rgb(ycbcr: np.ndarray) -> np.ndarray:
    Y=ycbcr[0,:,:]
    Cb=ycbcr[1,:,:]
    Cr=ycbcr[2,:,:]
    R = Y + 1.402*(Cr - 128)
    G = Y - 0.3441*(Cb - 128) - 0.7141*(Cr - 128)
    B = Y + 1.772*(Cb - 128)
    return np.stack((R,G,B),axis=-1)

"""
Cả hai hàm trên đều trả về dạng  [ , , 3]
"""

def pad_anh(anh: np.ndarray) -> Tuple[np.ndarray, Tuple[int, int]]:
    H,W,C=anh.shape
    pad_H = (8 - H % 8) % 8
    pad_W = (8 - W % 8) % 8
    padded_anh = np.pad(anh, ((0, pad_H), (0, pad_W), (0, 0)), mode='edge')
    return padded_anh, (H, W)
    """
    Đắp padding vào ảnh cả 2 chiều để chia hết cho 8 chia chunk cho dễ =)))
    """
"""
Công thức DCT-II:
    F(u,v) = alpha(u)*alpha(v) * sum(x=0..7) sum(y=0..7) f(x,y) * cos((2x+1)*u*pi/16) * cos((2y+1)*v*pi/16)
    alpha(0) = sqrt(1/8)
    alpha(k>0) = sqrt(2/8)
    Hoặc có thể viết thành dạng: 
    T(u,x) = alpha(u) * cos((2x+1)*u*pi/16)
    Dùng cái trên để thành ma trận 1 chiều, sau đó khi có các block cần lượng tử hóa thì sẽ nhân theo kiểu DCT_2D = T @ block @ T.T (ma trân chuyển vị của T)
Làm thế nào để chứng minh thì xem tại math_in_project.md

"""

def get_DCT_1D() -> np.ndarray:
    rs = np.zeros((8, 8), dtype=np.float64)
    for u in range (8):
            if u==0:
                alpha = np.sqrt(1/8)
            else:
                alpha = np.sqrt(2/8)
            for x in range (8):
                    rs[u,x] = alpha * np.cos((2*x+1)*u*np.pi/16)
    return rs

#tính ma trận DCT 8x8
DCT_matrix = get_DCT_1D()

LUMA_BASE = np.array(
    [
        [16, 11, 10, 16, 24, 40, 51, 61],
        [12, 12, 14, 19, 26, 58, 60, 55],
        [14, 13, 16, 24, 40, 57, 69, 56],
        [14, 17, 22, 29, 51, 87, 80, 62],
        [18, 22, 37, 56, 68, 109, 103, 77],
        [24, 35, 55, 64, 81, 104, 113, 92],
        [49, 64, 78, 87, 103, 121, 120, 101],
        [72, 92, 95, 98, 112, 100, 103, 99],
    ],
    dtype=np.float64,
)
#Bảng chuẩn cho kênh sáng Y

CHROMA_BASE = np.array(
    [
        [17, 18, 24, 47, 99, 99, 99, 99],
        [18, 21, 26, 66, 99, 99, 99, 99],
        [24, 26, 56, 99, 99, 99, 99, 99],
        [47, 66, 99, 99, 99, 99, 99, 99],
        [99, 99, 99, 99, 99, 99, 99, 99],
        [99, 99, 99, 99, 99, 99, 99, 99],
        [99, 99, 99, 99, 99, 99, 99, 99],
        [99, 99, 99, 99, 99, 99, 99, 99],
    ],
    dtype=np.float64,
)
#Bảng chuẩn cho kênh màu Cb,Cr

def scale_table(base_table: np.ndarray, quality: int) -> np.ndarray:
    if quality<50:
        scale=5000/quality
    else:
        scale=200-2*quality 
    scaled_table=np.floor((base_table*scale+50)/100)
    scaled_table.clip(1,255,out=scaled_table)
    return scaled_table.astype(np.uint8)

def get_scaled_tables(quality: int) -> Tuple[np.ndarray, np.ndarray]:
    if quality>100:
        quality=100
    elif quality<1:
        quality=1
    luma_table = scale_table(LUMA_BASE, quality)
    chroma_table = scale_table(CHROMA_BASE, quality)
    return luma_table, chroma_table

"""
Theo tài liệu và mấy vid tôi xem thì mấy bảng này sẽ được scale dựa theo 1 số quality, quality càng cao thì số scale càng nhỏ nên ảnh sẽ bị làm mờ ít đi, tham khảo thêm tại đây:
https://www.youtube.com/watch?v=Q2aEzeMDHMA&t=12s
https://www.youtube.com/watch?v=DS8N8cFVd-E

"""

def dct_xuoi(anh: np.ndarray, quan_table: np.ndarray) -> np.ndarray:
    anh=anh-128.0
    rs=np.zeros_like(anh, dtype=np.int32)
    for block_x in range(0, anh.shape[0], 8):
        for block_y in range(0, anh.shape[1], 8):
            block = anh[block_x:block_x+8, block_y:block_y+8]
            DCT_2D= DCT_matrix @ block @ DCT_matrix.T

            quantized = np.rint(DCT_2D / quan_table).astype(np.int32)
            #Chia rồi làm tròn và ép kiểu về int32

            rs[block_x:block_x+8, block_y:block_y+8] = quantized
    return rs.astype(np.int32)

def dct_nguoc(rs: np.ndarray, quan_table: np.ndarray) -> np.ndarray:
    anh=np.zeros_like(rs, dtype=np.float64)
    for block_x in range(0, rs.shape[0], 8):
        for block_y in range(0, rs.shape[1], 8):
            block = rs[block_x:block_x+8, block_y:block_y+8]
            dequantized = block * quan_table
            #Nhân lại với bảng lượng tử hóa

            DCT_2D = DCT_matrix.T @ dequantized @ DCT_matrix
            anh[block_x:block_x+8, block_y:block_y+8] = DCT_2D
    anh=anh+128.0
    return anh.astype(np.float64)

#Chú ý là theo đại số thì thứ tự nhân ma trận là quan trọng á.
